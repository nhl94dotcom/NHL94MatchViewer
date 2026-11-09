"""Energy over shifts with line changes on (Genesis, 2026-11-09, for NOSE4Web's "a knockdown costs energy" option:
what a shift costs, to price a knockdown). Power-on to Game Setup (gen_ot_check.to_setup), Line Changes set On in
RAM there (OptLine $D058 = 0, before the game starts), then START into play; the computer on both sides (cont1team
/ cont2team $C328 / $C32A cleared and the person flag, pflags bit 3, taken off every second). Each second: the game
clock, and for every roster slot of both teams its energy (team struct +$32, tmpde) and where he is (+$66, tmpdst:
$FFFF on the ice, $FFFE the bench). A shift is a run of seconds on the ice: its length in game seconds, the energy at
its start and end, and what the computer's line change saw (the line's average when it changed).

python gen_energy_shifts.py OUT [periods]"""
import json
import statistics
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

TEAMS = (0xC6CE, 0xCA32)
TMPDE, TMPDST, OPTLINE, CONT1, CONT2, GSP, CLOCK, SCREEN = 0x32, 0x32 + 52, 0xD058, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
BASE, SZ = 0xB04A, 0x80


def main():
    out = Path(sys.argv[1])
    periods = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    out.mkdir(parents=True, exist_ok=True)
    from paths import ROM
    e = Emu(ROM)
    G.to_setup(e, out)
    e.setw(OPTLINE, 0)
    if not G.into_play(e):
        print("never reached play")
        return
    print("OptLine", e.w(OPTLINE), "period", e.w(GSP), "clock", e.w(CLOCK), flush=True)
    log = []
    last_clock, still = None, 0
    frame = 0
    while e.w(GSP) < periods and frame < 60 * 60 * 25:
        e.setw(CONT1, 0)
        e.setw(CONT2, 0)
        for k in range(12):
            e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
        e.run(60, hold=["START"] if still >= 5 else [])
        frame += 60
        c = e.w(CLOCK)
        still = still + 1 if c == last_clock else 0
        last_clock = c
        if e.b(SCREEN) != 0:
            continue
        log.append({"gsp": e.w(GSP), "clock": c,
                    "teams": [[(e.w(t + TMPDE + 2 * s), e.w(t + TMPDST + 2 * s)) for s in range(26)] for t in TEAMS]})
        if frame % 3600 == 0:
            lowload.breathe()
    (out / "energy_log.json").write_text(json.dumps(log))
    shifts = []
    for t in range(2):
        for s in range(26):
            on, start = False, None
            for i, row in enumerate(log):
                energy, where = row["teams"][t][s]
                ice = where == 0xFFFF
                if ice and not on:
                    on, start = True, i
                elif not ice and on:
                    on = False
                    a, b = log[start], log[i - 1]
                    if a["gsp"] == b["gsp"]:
                        shifts.append({"team": t, "slot": s, "secs": a["clock"] - b["clock"],
                                       "start": a["teams"][t][s][0], "end": b["teams"][t][s][0]})
    skaters = [x for x in shifts if x["secs"] > 0 and x["start"] < 0x1001]
    print(f"{len(log)} samples, {len(skaters)} shifts ended", flush=True)
    if skaters:
        lens = [x["secs"] for x in skaters]
        drops = [x["start"] - x["end"] for x in skaters]
        rate = [d / x["secs"] for d, x in zip(drops, skaters) if x["secs"] >= 20]
        ends = [x["end"] for x in skaters]
        print(f"shift length (game s): median {statistics.median(lens)}, range {min(lens)}-{max(lens)}")
        print(f"energy lost in a shift: median {statistics.median(drops)} of 4096, range {min(drops)}-{max(drops)}")
        print(f"energy at the end of a shift: median {statistics.median(ends)} ({statistics.median(ends) / 40.96:.0f}%)")
        if rate:
            print(f"energy lost a game second on the ice (shifts of 20+ game s): median {statistics.median(rate):.1f}")
    (out / "shifts.json").write_text(json.dumps(shifts))


if __name__ == "__main__":
    main()
