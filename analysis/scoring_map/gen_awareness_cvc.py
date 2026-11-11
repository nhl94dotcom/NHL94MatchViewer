"""RATING_VALUES chunk C (Genesis, 2026-11-11): what Offensive and Defensive Awareness do to goals, the computer against
itself. Awareness is only a reaction timer (GENESIS_MECHANICS 12.1): the working bytes aioff (+$6A) and aidef (+$6B)
are the frames a computer player waits between decisions (rating 6 about 8, rating 1 about 14; 9-12 in an ordinary
game). Each game: power-on to Game Setup, the same team on both sides (Opt1team $D04C = Opt2team $D04E), 5-minute
periods (Optperlen $D050 = 0), penalties on except offsides (OptPen $D056 = 2), line changes off (OptLine $D058 = 1),
START into play, the seed ($D066) from the game's number, the computer on both sides (as gen_injury_baseline). Every
2 frames, for every skater (not the goalies, position +$35 = 0): the rating under test set to HIGH on one team and LOW
on the other, the other Awareness rating MID on both. Game n tests aioff for even n, aidef for odd; the HIGH team is
home for n // 2 even, away otherwise (the home bonus cancels). Saved per game: goals, shots, the period reached.

python gen_awareness_cvc.py ROM GAMES OUT.jsonl [HIGH LOW MID] [START]  (resumes: games already in OUT are skipped)"""
import json
import subprocess
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

TEAM1, TEAM2, PERLEN, OPTPEN, OPTLINE = 0xD04C, 0xD04E, 0xD050, 0xD056, 0xD058
SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
BASE, SZ, AIOFF, AIDEF, POS = 0xB04A, 0x80, 0x6A, 0x6B, 0x35
GOALS, SHOTS = (0xC6DA, 0xCA3E), (0xC6CE, 0xCA32)


def game(rom, n, out, high, low, mid):
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(TEAM2, e.w(TEAM1))
    e.setw(PERLEN, 0)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    test, other = (AIOFF, AIDEF) if n % 2 == 0 else (AIDEF, AIOFF)
    high_home = (n // 2) % 2 == 0
    frame, still, last = 0, 0, None
    while e.w(GSP) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
        for k in range(12):
            r = BASE + SZ * k
            if e.b(r + POS) == 0:
                continue
            e.setb(r + test, high if (k < 6) == high_home else low)
            e.setb(r + other, mid)
        e.run(2, hold=["START"] if still >= 8 and frame % 60 < 2 else [])
        frame += 2
    hi, lo = (0, 1) if high_home else (1, 0)
    g, s = [e.w(a) for a in GOALS], [e.w(a) for a in SHOTS]
    return {"game": n, "rating": "OfA" if test == AIOFF else "DfA", "high_home": high_home, "frames": frame,
            "periods": e.w(GSP), "team": e.w(TEAM1), "levels": [high, low, mid],
            "goals_high": g[hi], "goals_low": g[lo], "shots_high": s[hi], "shots_low": s[lo]}


def main():
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    levels = sys.argv[4:7] if len(sys.argv) >= 7 else ["8", "14", "11"]
    start = int(sys.argv[7]) if len(sys.argv) >= 8 else 0
    lowload.gentle()
    done = {json.loads(line)["game"] for line in out.read_text().splitlines()} if out.exists() else set()
    for n in range(start, games):
        if n in done:
            continue
        r = subprocess.run([sys.executable, __file__, "--one", rom, str(n), str(out.parent / "_boot"), *levels],
                           capture_output=True, text=True)          # one emulator per process
        line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else json.dumps({"game": n, "error": r.stderr[-300:]})
        with out.open("a") as fh:
            fh.write(line + "\n")
        print(line, flush=True)
        lowload.breathe()


if __name__ == "__main__":
    if sys.argv[1] == "--one":
        p = Path(sys.argv[4])
        p.mkdir(parents=True, exist_ok=True)
        print(json.dumps(game(sys.argv[2], int(sys.argv[3]), p, *map(int, sys.argv[5:8]))))
    else:
        main()
