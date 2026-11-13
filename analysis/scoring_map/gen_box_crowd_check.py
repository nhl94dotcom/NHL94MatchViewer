"""Three of a team's players sitting in the box at once (2026-11-12, for NOSE4Web): does the original game lose a skater
when the goalie, the skaters its tmap allows and three boxed players (who keep their sort objects) need more than the
team's six objects? Found in the 3-on-3 overtime build (STUDY_NOTES); this sets the case up on any ROM in regulation.

Each game: power-on, Game Setup, then in RAM penalties On Except Off-sides (OptPen $D056 = 2), line changes off
(OptLine $D058 = 1), 5-minute periods; into play, the computer on both sides, the seed from the game's number. The
away team's skaters are held at Aggression AGR (default 38: checkagr's roll range 13, so their checks are called most
of the time) so its penalties pile up; the home team plays as rated. At every faceoff drop (the clock starting): for
each team, the players in its box (tmpdst > 0), those of them holding an object (position $FF, pnum one of them), its
tmap and the skaters on the ice; a "crowded" draw is one with three or more boxed players holding objects. Printed:
per game the crowded draws and how many of them were a skater short (skaters on the ice < tmap - 1 with the goalie in).

python gen_box_crowd_check.py ROM GAMES OUT.jsonl"""
import json
import os
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

OPTPEN, OPTLINE, PERLEN, SEED = 0xD056, 0xD058, 0xD050, 0xD066
CONT1, CONT2, GSP, CLOCK, SCREEN, GMODE = 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7, 0xC2EA
TEAMS, TMAP, TMPDST = (0xC6CE, 0xCA32), 0x24, 0x66
BASE, SZ = 0xB04A, 0x80
POS = {1: "LD", 2: "RD", 3: "LW", 4: "C", 5: "RW", 6: "EA"}
AGR = int(os.environ.get("NHL94_AGR", "38"))


def team_state(e, t):
    b = TEAMS[t]
    boxed = [i + 1 for i in range(26) if 0 < e.w(b + TMPDST + 2 * i) < 0x8000]
    held = [e.b(BASE + SZ * k + 0x66) + 1 for k in range(6 * t, 6 * t + 6)
            if e.b(BASE + SZ * k + 0x35) == 0xFF and e.b(BASE + SZ * k + 0x66) + 1 in boxed]
    on = sorted(POS.get(e.b(BASE + SZ * k + 0x35), "?") for k in range(6 * t, 6 * t + 6)
                if 1 <= e.b(BASE + SZ * k + 0x35) <= 6)
    goalie = any(e.b(BASE + SZ * k + 0x35) == 0 for k in range(6 * t, 6 * t + 6))
    return {"tmap": e.w(b + TMAP), "boxed": boxed, "boxed_with_objects": held, "on_ice": on, "goalie_on": goalie}


def game(rom, n, tmp):
    e = Emu(rom)
    G.to_setup(e, tmp)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1)
    e.setw(PERLEN, 0)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    draws, crowded, f, was_stopped, still, last = 0, [], 0, True, 0, None
    while e.w(GSP) < 3 and f < 60 * 60 * 40:
        if f % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if f % 3600 == 0:
                lowload.breathe()
        for k in range(6, 12):
            if 1 <= e.b(BASE + SZ * k + 0x35) <= 6:
                e.setb(BASE + SZ * k + 0x73, AGR)
        e.run(2, hold=["START"] if still >= 8 and f % 60 < 4 else [])
        f += 2
        if e.b(SCREEN) != 0:
            continue
        stopped = bool(e.b(GMODE) & 1)
        if was_stopped and not stopped:
            draws += 1
            for t in (0, 1):
                st = team_state(e, t)
                if len(st["boxed_with_objects"]) >= 3:
                    want = st["tmap"] - 1 if st["goalie_on"] else st["tmap"]
                    crowded.append(dict(st, team=t, period=e.w(GSP), clock=e.w(CLOCK), short=len(st["on_ice"]) < want))
        was_stopped = stopped
    return {"game": n, "draws": draws, "crowded": crowded, "crowded_short": sum(c["short"] for c in crowded)}


def main():
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    lowload.gentle()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "_boot"
    tmp.mkdir(parents=True, exist_ok=True)
    for n in range(games):
        r = game(rom, n, tmp)
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(json.dumps({k: r.get(k) for k in ("game", "draws", "crowded_short", "error")},),
              "crowded draws:", len(r.get("crowded", [])), flush=True)


if __name__ == "__main__":
    main()
