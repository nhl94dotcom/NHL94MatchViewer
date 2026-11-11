"""Penalty box time on the SNES (2026-11-11, for NOSE4Web bcd4dfb: InProgress's `ldx #$003C` before Mul8U, minutes x N
seconds; test ROMs NHL94_penalty_time_30.smc and nhl94snes_SA1_penalty_time_30.sfc). A game started as
snes_60fps_cvc.game (menus, the computer on both sides, its seed from its number, penalties On, No Offside; the SA-1
build's low RAM through snes_60fps_cvc.Mem), every skater's Aggression ($1443) at 15 every 5 s (real) for more
penalties. Every 2 frames each team's tmpdst words ($1852, the away team +$34; a
word per roster place: the seconds left; $2000 just called, $1000 an injury's time, $4000 coincidental): each
penalty's starting time, the game-clock seconds until he comes out, and whether the other team scored then; at the end
the team stats (word pairs: penalties $174A, penalty minutes $174E, power-play goals $1742, power-play time $1756).

python snes_penalty_time_check.py ROM GAMES OUT.jsonl"""
import json
import subprocess
import sys
from pathlib import Path

import lowload
from snes_60fps_cvc import CLOCK, GSP, computer_only
from snes_ot_goal_check import start

TMPDST, AWAY, PENS, PENMIN, PPGOALS, PPTIME, SCORE = 0x1852, 0x34, 0x174A, 0x174E, 0x1742, 0x1756, 0x178E
POSITION, AGGRESS = 0x0F43, 0x1443          # word arrays by object (x 2): position (0 goalie), aggression


def game(rom, n, out):
    e, m = start(rom, n, out)
    open_, done = {}, []
    frame, still, last, ticks = 0, 0, None, 0
    while m.w(GSP) < 3 and frame < 60 * 60 * 45:
        if frame % 300 == 0:
            computer_only(m)
            for k in range(12):                     # every skater's Aggression at 15: more penalties (goalies left alone)
                if m.w(POSITION + 2 * k) != 0:
                    m.setw(AGGRESS + 2 * k, 15)
            if frame % 3600 == 0:
                lowload.breathe()
        c0, s0 = m.w(CLOCK), (m.w(SCORE), m.w(SCORE + 2))
        e.run(2)
        frame += 2
        c = m.w(CLOCK)
        if c != c0 and c < c0:
            ticks += 1
        still = still + 2 if c == last else 0
        last = c
        if still >= 900:
            e.run(4, hold=["START"])
            still = 0
        s1 = (m.w(SCORE), m.w(SCORE + 2))
        for t in (0, 1):
            for s in range(26):
                v = m.w(TMPDST + AWAY * t + 2 * s)
                key = (t, s)
                inbox = v < 0x8000 and not v & 0x1000 and (v & 0x2000 or v & 0x7FF)
                if inbox and key not in open_:
                    open_[key] = {"team": t, "slot": s, "start": v & 0x7FF, "coincidental": bool(v & 0x4000),
                                  "ticks0": ticks, "period": m.w(GSP), "clock": c}
                elif key in open_ and not inbox:
                    r = open_.pop(key)
                    r.update(served_s=ticks - r["ticks0"], ended_at_goal=s1[1 - t] > s0[1 - t], left=v)
                    done.append(r)
    for r in open_.values():
        r["open_at_end"] = True
        done.append(r)
    stats = [{k: m.w(a + 2 * t) for k, a in (("penalties", PENS), ("minutes", PENMIN), ("pp_goals", PPGOALS),
                                             ("pp_seconds", PPTIME))} for t in (0, 1)]
    return {"game": n, "rom": Path(rom).name, "periods": m.w(GSP), "penalties": done, "stats": stats}


def main():
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    lowload.gentle()
    for n in range(games):
        r = subprocess.run([sys.executable, __file__, "--one", rom, str(n), str(out.parent / "_boot")],
                           capture_output=True, text=True)
        lines = [x for x in r.stdout.splitlines() if x.startswith("{")]      # (the core prints a line of its own)
        line = lines[-1] if lines else json.dumps({"game": n, "error": r.stderr[-300:]})
        with out.open("a") as fh:
            fh.write(line + "\n")
        g = json.loads(line)
        for p in g.get("penalties", []):
            print(f"game {n}: team {p['team']} slot {p['slot']}: start {p['start']} s, out after {p.get('served_s')} "
                  f"clock s{' at a goal' if p.get('ended_at_goal') else ''}{' (coincidental)' if p['coincidental'] else ''}"
                  f"{' (open at the end)' if p.get('open_at_end') else ''}", flush=True)
        print(f"game {n}: stats {g.get('stats', g.get('error'))}", flush=True)
        lowload.breathe()


if __name__ == "__main__":
    if sys.argv[1] == "--one":
        p = Path(sys.argv[4])
        p.mkdir(parents=True, exist_ok=True)
        print(json.dumps(game(sys.argv[2], int(sys.argv[3]), p)))
    else:
        main()
