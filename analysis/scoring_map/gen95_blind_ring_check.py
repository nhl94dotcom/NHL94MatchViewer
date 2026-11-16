"""NHL '95 (Genesis): the goalie's blind ring played (2026-11-16, for NOSE4Web). From the code (STUDY_NOTES "NHL '95's
five-hole blind ring"): a low puck inside the goalie's ±$E stick box goes to puckstick, which takes a loose puck only
within 8 of the blade's hot spot and otherwise does nothing; the goalie test (puckgoalie) is tried only outside the box.

1. Shots at the away goalie (record 11, the top net): home's A picks the puck up at spots across the slot and shoots
   (C held, the pad aiming left, middle or right), everyone else parked; the state kept at each new (animation,
   sprite frame) of the goalie's.
2. From each kept state, a slow puck (moving toward the net) put at each point of a grid round the goalie, one frame
   played: touched if he holds it (+$60 = 0, +$61 = 11) or its velocity changed by more than 15%.
The map per state: where the puck is touched, and the untouched points inside the touched area (the blind spots).

python gen95_blind_ring_check.py ROM STATE OUT"""
import json
import math
import sys
from pathlib import Path

from emu import Emu
import gen95_assist_check as G

SPA, FRAME = 0x58, 0x06
GOALIE = 11


def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def park(e):
    for k in range(12):
        if k == GOALIE:
            continue
        e.setw(G.rec(k), -100 + 18 * k)
        e.setw(G.rec(k) + 0x14, -230)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(G.rec(k) + off, 0)


def put_puck(e, x, y, vx, vy):
    P = G.PUCK
    e.setw(P, x & 0xFFFF); e.setw(P + 0x14, y & 0xFFFF); e.setw(P + 0x18, 0)
    e.setw(P + 0x28, vx & 0xFFFF); e.setw(P + 0x2A, vy & 0xFFFF); e.setw(P + 0x2C, 0)
    e.setb(P + 0x60, 0xFF)
    e.setb(P + 0x5E, 0)
    e.setb(G.rec(GOALIE) + 0x5E, 0)


def collect(e, base):
    """Real shots: home's A picks the puck up at a spot in the slot and shoots (C held, released, the pad aiming left,
    middle or right); the goalie's save moves come from the game's own goaliesave."""
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
                    for f in range(90):
                        held = ["UP"] + aim + (["C"] if f < hold else [])
                        p.park()
                        if f < hold:
                            p.hold([G.A])
                        key = (e.w(G.rec(GOALIE) + SPA), e.w(G.rec(GOALIE) + FRAME))
                        if key not in states:
                            states[key] = e.serialize()
                        e.run(1, hold=held)
                        loose = e.b(G.PUCK + 0x60) != 0
                        released = released or loose
                        if released and not loose:           # the shot gone and someone has the puck again
                            break
    return states


def grid(e, st):
    e.unserialize(st)
    gx, gy = s16(e.w(G.rec(GOALIE))), s16(e.w(G.rec(GOALIE) + 0x14))
    out = {}
    for dy in range(-24, 25, 2):
        for dx in range(-32, 33, 2):
            e.unserialize(st)
            park(e)
            v0 = (0, 300)
            put_puck(e, gx + dx, gy + dy, *v0)
            e.run(1)
            held = e.b(G.PUCK + 0x60) == 0 and e.b(G.PUCK + 0x61) == GOALIE
            vx, vy = s16(e.w(G.PUCK + 0x28)), s16(e.w(G.PUCK + 0x2A))
            changed = math.hypot(vx - v0[0], vy - v0[1]) > 0.15 * math.hypot(*v0)
            out[(dx, dy)] = "H" if held else ("T" if changed else ".")
    return (gx, gy), out


def main():
    rom, state, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    base = Path(state).read_bytes()
    states = collect(e, base)
    print(len(states), "goalie (animation, frame) states", flush=True)
    res = {}
    for key, st in sorted(states.items()):
        pos, g = grid(e, st)
        res[f"{key[0]:04X}/{key[1]}"] = dict(pos=pos, grid={f"{dx},{dy}": v for (dx, dy), v in g.items()})
        print(f"{key[0]:04X}/{key[1]}: touched {sum(v != '.' for v in g.values())} of {len(g)}", flush=True)
    (out / "blind.json").write_text(json.dumps(res))


if __name__ == "__main__":
    main()
