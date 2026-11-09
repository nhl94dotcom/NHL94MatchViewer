"""Energy over shifts with line changes on (SNES, 2026-11-09; gen_energy_shifts.py is the Genesis one). The retail
ROM (or one given) boots as snes_60fps_cvc's games do (Montreal at home against Los Angeles, 5-minute periods,
penalties on), Line Changes set On in RAM at Game Setup (OptLine $34C6 = 1, before the game starts), the computer on
both sides (snes_60fps_cvc.computer_only every 5 s). Each second of play: the clock, and for every roster slot of both
teams its energy (tmpde $17EA, the visitors +$34) and where he is (tmpdst $1852: $FFFF on the ice, $FFFE the bench).
Shifts as in gen_energy_shifts.

python snes_energy_shifts.py OUT [ROM] [periods]"""
import json
import statistics
import sys
from pathlib import Path

import lowload
import menu_shots as M
import snes_60fps_cvc as cvc

TMPDE, TMPDST, OPTLINE, GSP, CLOCK, STOPPED = 0x17EA, 0x1852, 0x34C6, 0x1630, 0x1632, 0x15D6


def main():
    out = Path(sys.argv[1])
    from paths import SNES_ROM
    rom = sys.argv[2] if len(sys.argv) > 2 else str(SNES_ROM)
    periods = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    out.mkdir(parents=True, exist_ok=True)
    e = M.emulator(rom)
    m = cvc.Mem(e, rom)
    tmp = out / "_menu"
    M.play(e, "w1500 START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
    m.setw(OPTLINE, 1)
    M.play(e, "START w240 START w200 w2400", tmp)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(STOPPED) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    print("OptLine", m.w(OPTLINE), "period", m.w(GSP), "clock", m.w(CLOCK), flush=True)
    log, still, last, frame = [], 0, None, 0
    while m.w(GSP) < periods and frame < 60 * 60 * 30:
        if frame % 300 == 0:
            cvc.computer_only(m)
        e.run(60, hold=["START"] if still >= 8 else [])
        frame += 60
        c = m.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        log.append({"gsp": m.w(GSP), "clock": c,
                    "teams": [[(m.w(TMPDE + 0x34 * t + 2 * s), m.w(TMPDST + 0x34 * t + 2 * s)) for s in range(26)]
                              for t in range(2)]})
        if frame % 3600 == 0:
            lowload.breathe()
    (out / "energy_log.json").write_text(json.dumps(log))
    shifts = []
    for t in range(2):
        for s in range(26):
            on, start = False, None
            for i, row in enumerate(log):
                ice = row["teams"][t][s][1] == 0xFFFF
                if ice and not on:
                    on, start = True, i
                elif not ice and on:
                    on = False
                    a, b = log[start], log[i - 1]
                    if a["gsp"] == b["gsp"]:
                        shifts.append({"team": t, "slot": s, "secs": a["clock"] - b["clock"],
                                       "start": a["teams"][t][s][0], "end": b["teams"][t][s][0]})
    sk = [x for x in shifts if x["secs"] > 0]
    print(f"{len(log)} samples, {len(sk)} shifts ended", flush=True)
    if sk:
        lens = [x["secs"] for x in sk]
        drops = [x["start"] - x["end"] for x in sk]
        ends = [x["end"] for x in sk]
        rate = [d / x["secs"] for d, x in zip(drops, sk) if x["secs"] >= 20]
        print(f"shift length (game s): median {statistics.median(lens)}, range {min(lens)}-{max(lens)}")
        print(f"energy lost in a shift: median {statistics.median(drops)} of 4096, range {min(drops)}-{max(drops)}")
        print(f"energy at the end of a shift: median {statistics.median(ends)} ({statistics.median(ends) / 40.96:.0f}%)")
        if rate:
            print(f"energy lost a game second on the ice (shifts of 20+ game s): median {statistics.median(rate):.1f}")
    (out / "shifts.json").write_text(json.dumps(shifts))


if __name__ == "__main__":
    main()
