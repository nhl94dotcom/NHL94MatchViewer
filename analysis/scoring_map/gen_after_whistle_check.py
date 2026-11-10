"""Hits after the whistle on NOSE4Web's Genesis hit option (2026-11-09, b0efcd5, nhl94_hit_option.bin: the knockdown /
hold energy cost and the injury-risk count do nothing while the clock is stopped, gmode bit gmclock).

NOSE4Web's changes laid over a copy of the scoring-map test ROM (gen_hit_energy_check.patched) and played in the
harness against the unchanged test ROM, trial by trial with the same seed (gen_hit_energy_check.trial): the pad
skater's C (body check) and A (hook / hold) at the away carrier, with the clock stopped (gmode $C2EA | $0100 every
frame: CCStart then makes a body check a late hit, impact $100) and with it running. Logged: whether he went down /
flailed, his energy change on both ROMs (the option's cost is the difference), his knockdown count ($FFF000, the away
team +32, by roster place) on the build, the team's checks stat.

python gen_after_whistle_check.py OUT RETAIL_ROM OPTION_ROM"""
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import gen_hit_energy_check as HE
import harness as H
import lowload
from gen_injury_risk_check import count_addr
from paths import ROM

GMODE = 0xC2EA


def run(rom, out, label):
    h = H.Harness(rom=rom)
    res = []
    for stopped in (False, True):
        for button in ("C", "A"):
            for dy in (30, 50, 70):
                for at in (5, 15):
                    for sd in range(4):
                        st = {}

                        def setup(e, st=st, stopped=stopped):
                            if stopped:
                                e.setw(GMODE, e.w(GMODE) | 0x0100)
                            if "c" not in st:
                                st["c"] = e.b(count_addr(e, 6))
                        r = HE.trial(h, button, dy, at, 0x7000 + 53 * sd + dy + at, 0, setup=setup)
                        r["count change"] = h.e.b(count_addr(h.e, 6)) - st["c"]
                        res.append(dict(stopped=stopped, what=button, dy=dy, at=at, seed=sd, **r))
            lowload.breathe()
    (out / f"{label}.json").write_text(json.dumps(res))


def main():
    if sys.argv[1] == "--one":
        run(sys.argv[2], Path(sys.argv[3]), sys.argv[4])
        return
    out, retail, option = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    out.mkdir(parents=True, exist_ok=True)
    test, n = HE.patched(out, option, retail)
    print("bytes laid over the test ROM:", n, flush=True)
    for rom, label in ((str(ROM), "unchanged"), (str(test), "changed")):
        subprocess.run([sys.executable, __file__, "--one", rom, str(out), label], check=True)
    a = json.loads((out / "unchanged.json").read_text())
    b = json.loads((out / "changed.json").read_text())
    table = defaultdict(lambda: defaultdict(int))
    for x, y in zip(a, b):
        event = "he went down" if y["down"] else "he flailed" if y["flail"] else "nothing"
        key = ("clock stopped" if y["stopped"] else "clock running", y["what"], event)
        table[key][f"cost {x['de'] - y['de']:+d}"] += 1
        table[key][f"count {y['count change']:+d}"] += 1
        table[key][f"same event {(x['down'], x['flail']) == (y['down'], y['flail'])}"] += 1
    for key in sorted(table):
        print(f"{key[0]}, {key[1]}, {key[2]}: {dict(table[key])}")


if __name__ == "__main__":
    main()
