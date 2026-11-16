"""NHL '94 against NHL '95 (Genesis): flat pucks at the goalie's middle while he is in a stick save (the kick /
butterfly), the case where the blind ring lets pucks through (2026-11-16, the user's question).

1. collect: real shots (gen95_assist_check's play code, the game's addresses swapped in for NHL '94) make the computer
   goalie of the top net save; the game state is kept at the first frame of each stick save (NHL '95: SPAgstickr /
   SPAgstickl, $1CEA / $1D1C; NHL '94: frames STICK94, SPAgstickr / SPAgstickl's eight directions each).
2. fire: from each kept state, a flat puck (height 0, not rising) put 60 units in front of him in a lane going straight at his net (LANES, SPEEDS).
   Per puck: a goal; touched by him (held, or its speed changed by over 20% within 22 of him in front of the goal
   line); passed within 16 of his centre. "Through him": a goal he never touched.

python slip_save.py GAME ROM STATE OUT    (GAME 94 or 95)

17 lanes a unit apart (8 left to 8 right) at 6 speeds (10,000-24,000): 102 pucks a stick-save start."""
import json
import math
import sys
from pathlib import Path

from emu import Emu
import gen95_assist_check as G
from slip_compare import CFG, GOALIE, GOAL_Y, REACH, s16

SPA, FRAME = 0x58, 0x06
STICK95 = {0x1CEA, 0x1D1C}
STICK94 = set(range(471, 488))           # SPFGoalie + 64 / 65 + 2 x direction (frame 480: the butterfly facing down)
STICKSPA94 = {0x1EC, 0x21E}             # SPAgstickr / SPAgstickl (seen starting frames 479 / 480); other SPAs caught
                                        # on those frames are a save's end, not a stick save
SPEEDS = (10000, 12000, 15000, 18000, 21000, 24000)   # about 2.4 to 6 units a frame
LANES = tuple(range(-8, 9))                          # 8 left of his centre to 8 right, a unit apart


def collect(game, e, base):
    states = {}
    for sx in (-50, -30, -10, 10, 30, 50):
        for sy in (150, 180, 205):
            for aim in ([], ["LEFT"], ["RIGHT"]):
                for hold in (6, 14):
                    log = []
                    p = G.Play(e, base, {G.A: (sx, sy)}, log)
                    p.keep = {G.A}
                    if not p.pick_up(G.A, "A"):
                        continue
                    released = False
                    prev = None
                    for f in range(90):
                        held = ["UP"] + aim + (["C"] if f < hold else [])
                        p.park()
                        if f < hold:
                            p.hold([G.A])
                        e.run(1, hold=held)
                        spa, fr = e.w(G.rec(GOALIE) + SPA), e.w(G.rec(GOALIE) + FRAME)
                        stick = spa in STICK95 if game == "95" else (fr in STICK94 and spa in STICKSPA94)
                        if stick and prev != (spa, fr) and (spa, fr) not in states:
                            states[(spa, fr)] = e.serialize()
                        prev = (spa, fr)
                        loose = e.b(G.PUCK + 0x60) != 0
                        released = released or loose
                        if released and not loose:
                            break
    return states


def fire(game, e, st, team):
    out = []
    for lane in LANES:
        for sp in SPEEDS:
            e.unserialize(st)
            gx, gy = s16(e.w(G.rec(GOALIE))), s16(e.w(G.rec(GOALIE) + 0x14))
            P = G.PUCK
            x0, y0 = gx + lane, gy - 60
            e.setw(P, x0 & 0xFFFF); e.setw(P + 0x14, y0 & 0xFFFF); e.setw(P + 0x18, 0)
            e.setw(P + 0x28, 0); e.setw(P + 0x2A, sp & 0xFFFF); e.setw(P + 0x2C, 0)
            e.setb(P + 0x60, 0xFF); e.setb(P + 0x5E, 0); e.setb(G.rec(GOALIE) + 0x5E, 0)
            s0 = e.w(team + 0x0C)
            touched = near = goal = False
            pv = (0, sp)
            for f in range(90):
                for k in range(12):
                    if k != GOALIE:
                        e.setw(G.rec(k), (-100 + 18 * k) & 0xFFFF); e.setw(G.rec(k) + 0x14, (-230) & 0xFFFF)
                e.run(1)
                px, py = s16(e.w(P)), s16(e.w(P + 0x14))
                gx, gy = s16(e.w(G.rec(GOALIE))), s16(e.w(G.rec(GOALIE) + 0x14))
                v = (s16(e.w(P + 0x28)), s16(e.w(P + 0x2A)))
                d = math.hypot(px - gx, py - gy)
                near = near or d <= REACH
                if e.b(P + 0x60) == 0:
                    touched = touched or e.b(P + 0x61) == GOALIE
                    break
                if d <= 22 and py < GOAL_Y - 2 and math.hypot(v[0] - pv[0], v[1] - pv[1]) > 0.2 * max(1, math.hypot(*pv)):
                    touched = True
                pv = v
                if e.w(team + 0x0C) != s0:
                    goal = True
                    break
            out.append(dict(lane=lane, sp=sp, goal=goal, touched=touched, near=near))
    return out


def main():
    game, rom, state, out = sys.argv[1:5]
    c = CFG[game]
    G.BASE, G.TEAM = c["base"], c["team"]
    G.PUCK = G.rec(14)
    e = Emu(rom)
    base = Path(state).read_bytes()
    states = collect(game, e, base)
    print(f"{game}: {len(states)} stick-save starts (SPA, frame): {sorted((hex(a), b) for a, b in states)}", flush=True)
    res = {}
    for key, st in states.items():
        res[f"{key[0]:04X}/{key[1]}"] = fire(game, e, st, c["team"])
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "slip_save.json").write_text(json.dumps(res))
    rows = [r for v in res.values() for r in v]
    g = sum(r["goal"] for r in rows)
    thr = sum(r["goal"] and not r["touched"] for r in rows)
    print(f"{game}: {len(rows)} flat pucks at a goalie in a stick save: goals {g} ({g / max(1, len(rows)):.0%}), through him untouched"
          f" {thr} ({thr / max(1, len(rows)):.0%}), saved {sum(r['touched'] and not r['goal'] for r in rows)}", flush=True)
    for sp in SPEEDS:
        r = [x for x in rows if x["sp"] == sp]
        print(f"   speed {sp}: through him {sum(x['goal'] and not x['touched'] for x in r)} of {len(r)}", flush=True)


if __name__ == "__main__":
    main()
