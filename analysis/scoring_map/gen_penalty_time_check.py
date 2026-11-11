"""Penalty box time (2026-11-11, for NOSE4Web bcd4dfb: the box time minutes x N seconds instead of x 60; penalty94 .Sa
`mulu.w #$3C,d2` at $1230C, the word at $12310; test ROMs at N = 30). Computer games, both sides the computer, penalties
on except offsides, 5-minute periods, every skater's Aggression (+$73) at 15 each second (more penalties; goalies left
alone: the byte is their glove side). Every 2 frames each team's tmpdst words (team block +$66, a word per roster place:
the seconds left; $2000 just called, cleared as the penalty starts; $4000 coincidental): each penalty's starting time, the game seconds it then
takes to come out (counted from the clock), and how it ends (served, or the box emptied at a power-play goal by the
other team); the team stats' penalties (+$06), penalty minutes (+$08), power-play goals (+$02) and power-play time (+$352,
seconds) at the end against the penalties seen.

python gen_penalty_time_check.py ROM GAMES OUT.jsonl"""
import json
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

TEAMS = (0xC6CE, 0xCA32)
TMPDST, PENS, PENMIN, PPTIME, PPGOALS = 0x66, 0x06, 0x08, 0x352, 0x02
OPTLINE, PERLEN, OPTPEN, SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD058, 0xD050, 0xD056, 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
BASE, SZ, POS, AGGR = 0xB04A, 0x80, 0x35, 0x73
SCORE = (0xC6DA, 0xCA3E)


def game(rom, n, out):
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(OPTLINE, 1)
    e.setw(PERLEN, 0)
    e.setw(OPTPEN, 2)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    open_ = {}                       # (team, slot) -> record
    done = []
    frame, still, last = 0, 0, None
    clock_ticks = 0
    while e.w(GSP) < 3 and frame < 60 * 60 * 45:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                r = BASE + SZ * k
                e.setb(r + 0x62, e.b(r + 0x62) & ~8)
                if e.b(r + POS) != 0:
                    e.setb(r + AGGR, 15)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
        c0, s0 = e.w(CLOCK), [e.w(a) for a in SCORE]
        e.run(2, hold=["START"] if still >= 8 and frame % 60 < 2 else [])
        frame += 2
        if e.w(CLOCK) != c0 and e.b(SCREEN) == 0:
            clock_ticks += 1
        s1 = [e.w(a) for a in SCORE]
        for t, base in enumerate(TEAMS):
            for s in range(26):
                v = e.w(base + TMPDST + 2 * s)
                key = (t, s)
                # $2000 marks "just called" (InProgress_ap clears it as the penalty starts); then the word is the
                # seconds left, 0 when he comes out
                inbox = v < 0x8000 and (v & 0x2000 or v & 0x7FF)
                if inbox and key not in open_:
                    open_[key] = {"team": t, "slot": s, "start": v & 0x7FF, "coincidental": bool(v & 0x4000),
                                  "ticks0": clock_ticks, "period": e.w(GSP), "clock": e.w(CLOCK)}
                elif key in open_ and not inbox:
                    r = open_.pop(key)
                    r["served_s"] = clock_ticks - r["ticks0"]
                    r["ended_at_goal"] = s1[1 - t] > s0[1 - t]
                    r["left"] = v
                    done.append(r)
    for r in open_.values():
        r["open_at_end"] = True
        done.append(r)
    stats = [{"penalties": e.w(b + PENS), "minutes": e.w(b + PENMIN), "pp_seconds": e.w(b + PPTIME),
              "pp_goals": e.w(b + PPGOALS)} for b in TEAMS]
    return {"game": n, "rom": Path(rom).name, "periods": e.w(GSP), "penalties": done, "stats": stats}


def main():
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    lowload.gentle()
    for n in range(games):
        import subprocess
        r = subprocess.run([sys.executable, __file__, "--one", rom, str(n), str(out.parent / "_boot")],
                           capture_output=True, text=True)
        line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else json.dumps({"game": n, "error": r.stderr[-300:]})
        with out.open("a") as fh:
            fh.write(line + "\n")
        g = json.loads(line)
        for p in g.get("penalties", []):
            print(f"game {n}: team {p['team']} slot {p['slot']}: start {p['start']} s, out after {p.get('served_s')} "
                  f"clock s{' at a goal' if p.get('ended_at_goal') else ''}{' (coincidental)' if p['coincidental'] else ''}"
                  f"{' (open at the end)' if p.get('open_at_end') else ''}", flush=True)
        print(f"game {n}: stats {g.get('stats')}", flush=True)
        lowload.breathe()


if __name__ == "__main__":
    if sys.argv[1] == "--one":
        p = Path(sys.argv[4])
        p.mkdir(parents=True, exist_ok=True)
        print(json.dumps(game(sys.argv[2], int(sys.argv[3]), p)))
    else:
        main()
