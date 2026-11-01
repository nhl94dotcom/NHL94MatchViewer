"""The SNES model's goalie variants re-scored on the game's own shots that xg_calib.py stored (2026-11-01, SNES_SHOOTING
4.7: the gliding goalie with the save-start push, snes_glide_trace.py, must stay right close in, where the gliding
goalie was made for the dekes). Each stored shot (exact state, no blur) is asked again as xg_calib asks it, with the old
movement, the gliding goalie before the push (xg_snes.SAVE_PUSH off) and with it; per category: shots, the game's
rate, each variant's rate and log loss.
python snes_glide_rescore.py [samples] [run ...]   (default 40 xgsnes_all xgdeke3)"""
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg_snes as XS  # noqa: E402

from lowload import breathe, gentle  # noqa: E402
from paths import RUNS, SNES_ROM  # noqa: E402

VARIANTS = [("old", False, True), ("glide", True, False), ("glide+push", True, True)]


def ask(data, p, samples, rng_tag):
    rng = random.Random(rng_tag)
    gx, gy, gvx, gvy, w, agl, spd, aid = p["goalie"]
    d = p["aim"] if p["aim"] is not None and 0 <= p["aim"] <= 8 else 8
    tx, tz = XS.AIM[d]
    G = XS.Goalie(data, gx, gy, gvx, gvy, p["facing"], p["frame"], w, agl, spd, aid)
    return sum(XS.play_out(p["px"], p["py"], tx, p["gl"], tz, max(1.0, p["speed"] / 136), p["sha"],
                           (p["sha"] + 1) / (p["sha"] + 16), G, rng) == "goal" for _ in range(samples)) / samples


def main():
    samples = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    runs = sys.argv[2:] or ["xgsnes_all", "xgdeke3"]
    gentle()
    data = XS.RomData(SNES_ROM.read_bytes())
    XS.GOALIE_SPREAD = 0.0
    out = defaultdict(lambda: defaultdict(list))     # category -> variant -> (p, goal)
    for run in runs:
        for i, line in enumerate(open(RUNS / run / "xg_calib_snes.jsonl")):
            p = json.loads(line)
            if "px" not in p:
                continue                                  # a summary line, not a shot
            cat = p["cat"] + ("+follow-up" if p.get("ord") else "")
            for name, glide, push in VARIANTS:
                XS.GLIDE_IN_SAVE, XS.SAVE_PUSH = glide, push
                x = ask(data, p, samples, f"{p['tag']}:{p['px']}:{p['py']}:{p['ord']}")
                out[cat][name].append((x, p["goal"]))
            if i % 50 == 49:
                breathe()
    XS.GLIDE_IN_SAVE, XS.SAVE_PUSH = False, True
    ll = lambda v: -sum(g * math.log(max(1e-3, x)) + (1 - g) * math.log(max(1e-3, 1 - x)) for x, g in v) / len(v)
    for cat, d in sorted(out.items()):
        v0 = next(iter(d.values()))
        n, goals = len(v0), sum(g for _, g in v0)
        print(f"{cat:22} {n:5} shots, game {100 * goals / n:5.1f}%   " +
              "   ".join(f"{name} {100 * sum(x for x, _ in v) / n:5.1f}% (log loss {ll(v):.3f})" for name, v in d.items()))


if __name__ == "__main__":
    main()
