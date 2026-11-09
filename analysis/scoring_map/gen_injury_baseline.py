"""Injuries, knockdowns and holds a game, the computer against itself with line changes on (Genesis, 2026-11-09):
the "option off" half of the check on NOSE4Web's hit option (a knockdown costs energy and raises the injury chance).
Each game: power-on to Game Setup (gen_ot_check.to_setup), Line Changes On (OptLine $D058 = 0) and 5-minute periods
(Optperlen $D050 = 0) set there, START into play, the random seed ($D066, a long) set from the game's number, the
computer on both sides (cont1team / cont2team cleared, the person flag taken off, every second), three periods (START
on screens that wait). Every 4 frames: a player newly out injured (team struct +$66 tmpdst $FFFD for the period or
$FFFC for the game), a player newly flailing (held or hooked: animation word +$58 = $0CF4). At the end: knockdowns
(the game's team checks, +$10, which FallDown counts), the lowest energy any skater reached, the mean energy of the
players on the ice (each second) and how many times a player went from the ice to the bench (shift ends).

python gen_injury_baseline.py ROM GAMES OUT.jsonl   (resumes: games already in OUT are skipped)"""
import json
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

TEAMS = (0xC6CE, 0xCA32)
TMPDE, TMPDST, CHECKS = 0x32, 0x32 + 52, 0x10
OPTLINE, PERLEN, SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD058, 0xD050, 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
BASE, SZ, FLAIL = 0xB04A, 0x80, 0x0CF4


def game(rom, n, out):
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(OPTLINE, 0)
    e.setw(PERLEN, 0)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    injuries, holds = [], 0
    out_now = set()
    flail = [False] * 12
    low = 0x1000
    ice_sum, ice_n, changes, was_on = 0, 0, 0, set()
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
        e.run(4, hold=["START"] if still >= 8 and frame % 60 < 4 else [])
        frame += 4
        if e.b(SCREEN) != 0:
            continue
        for t, base in enumerate(TEAMS):
            for s in range(26):
                st = e.w(base + TMPDST + 2 * s)
                if st in (0xFFFD, 0xFFFC) and (t, s) not in out_now:
                    out_now.add((t, s))
                    injuries.append({"team": t, "slot": s, "period": e.w(GSP), "clock": e.w(CLOCK),
                                     "game": st == 0xFFFC})
                elif st == 0xFFFF:
                    out_now.discard((t, s))
                    en = e.w(base + TMPDE + 2 * s)
                    low = min(low, en)
                    if frame % 60 == 0:
                        ice_sum += en
                        ice_n += 1
                if frame % 60 == 0:
                    if st == 0xFFFE and (t, s) in was_on:
                        changes += 1
                        was_on.discard((t, s))
                    elif st == 0xFFFF:
                        was_on.add((t, s))
        for k in range(12):
            f = e.w(BASE + SZ * k + 0x58) == FLAIL
            if f and not flail[k]:
                holds += 1
            flail[k] = f
    return {"game": n, "frames": frame, "periods": e.w(GSP), "injuries": injuries, "holds": holds,
            "knockdowns": [e.w(t + CHECKS) for t in TEAMS], "lowest_energy": low,
            "mean_ice_energy": round(ice_sum / ice_n) if ice_n else None, "shift_ends": changes,
            "score": [e.w(0xC6DA), e.w(0xCA3E)]}


def main():
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    lowload.gentle()
    done = {json.loads(line)["game"] for line in out.read_text().splitlines()} if out.exists() else set()
    for n in range(games):
        if n in done:
            continue
        import subprocess
        # one emulator per process
        r = subprocess.run([sys.executable, __file__, "--one", rom, str(n), str(out.parent / "_boot")],
                           capture_output=True, text=True)
        line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else json.dumps({"game": n, "error": r.stderr[-300:]})
        with out.open("a") as fh:
            fh.write(line + "\n")
        print(line, flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "--one":
        p = Path(sys.argv[4])
        p.mkdir(parents=True, exist_ok=True)
        print(json.dumps(game(sys.argv[2], int(sys.argv[3]), p)))
    else:
        main()
