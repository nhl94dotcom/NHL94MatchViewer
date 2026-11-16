"""NHL '94 against NHL '95 (Genesis): how often a puck goes in through the computer goalie (2026-11-16, the user's
question after the blind-ring maps). The same pucks in both games, from a live state with everyone but the top net's
goalie parked: a loose puck from 15 spots in the slot (x -30..30, 60-100 from the goal line) aimed across the goal
mouth (5 points, x -12..12) at 3 speeds (SPEEDS: about 3-6 units a frame), flat (height 0,
not rising) and lifted (rising at 4,000). Per puck: a goal or not; touched by the goalie (he holds it, or its speed
changes by over 20% within 22 of him and in front of the goal line); passed within his body's reach (16) of his
centre. "Through him": a goal, untouched, having passed within 16 of his centre.

These pucks aren't shots, so the goalie doesn't start a save move (he stands, or skates to the puck): it is the
standing / skating goalie the numbers describe.

python slip_compare.py GAME ROM STATE OUT [--shots]   (--shots: real shots by a skater, the goalie's own save moves; GAME 94 or 95; STATE a live state with the home team attacking the top
net; for 94 'make' builds one from power-on)"""
import json
import math
import sys
from pathlib import Path

from emu import Emu

CFG = {"94": dict(base=0xB04A, team=0xC6CE), "95": dict(base=0xAC62, team=0xC288)}
GOALIE, GOAL_Y, REACH = 11, 264, 16
SPEEDS = (12000, 18000, 24000)        # about 3, 4.4 and 6 units a frame: shots to hard passes (2026-11-16: the first run's
                                       # 3,000-6,000, 0.7-1.5 units a frame, was far too slow to skip anything)


def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def run(game, rom, state, out):
    c = CFG[game]
    rec = lambda k: c["base"] + 0x80 * k  # noqa: E731
    P = rec(14)
    e = Emu(rom)
    base = Path(state).read_bytes()

    def park():
        for k in range(12):
            if k == GOALIE:
                continue
            e.setw(rec(k), (-100 + 18 * k) & 0xFFFF)
            e.setw(rec(k) + 0x14, (-230) & 0xFFFF)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(rec(k) + off, 0)

    rows = []
    for lift in (0, 4000):
        for y0 in (164, 184, 204):
            for x0 in (-30, -15, 0, 15, 30):
                for ax in (-12, -6, 0, 6, 12):
                    for sp in SPEEDS:
                        e.unserialize(base)
                        for _ in range(20):
                            park(); e.run(1)
                        dx, dy = ax - x0, GOAL_Y - y0
                        L = math.hypot(dx, dy)
                        vx, vy = int(sp * dx / L), int(sp * dy / L)
                        e.setw(P, x0 & 0xFFFF); e.setw(P + 0x14, y0 & 0xFFFF); e.setw(P + 0x18, 0)
                        e.setw(P + 0x28, vx & 0xFFFF); e.setw(P + 0x2A, vy & 0xFFFF); e.setw(P + 0x2C, lift & 0xFFFF)
                        e.setb(P + 0x60, 0xFF); e.setb(P + 0x5E, 0); e.setb(rec(GOALIE) + 0x5E, 0)
                        s0 = e.w(c["team"] + 0x0C)
                        touched, near, goal, held = False, False, False, False
                        pv = (vx, vy)
                        for f in range(120):
                            park()
                            e.run(1)
                            px, py, pz = s16(e.w(P)), s16(e.w(P + 0x14)), s16(e.w(P + 0x18))
                            gx, gy = s16(e.w(rec(GOALIE))), s16(e.w(rec(GOALIE) + 0x14))
                            v = (s16(e.w(P + 0x28)), s16(e.w(P + 0x2A)))
                            d = math.hypot(px - gx, py - gy)
                            if d <= REACH:
                                near = True
                            if e.b(P + 0x60) == 0:
                                held = e.b(P + 0x61) == GOALIE
                                touched = touched or held
                                break
                            if d <= 22 and py < GOAL_Y - 2 and math.hypot(v[0] - pv[0], v[1] - pv[1]) > 0.2 * max(1, math.hypot(*pv)):
                                touched = True
                            pv = v
                            if e.w(c["team"] + 0x0C) != s0:
                                goal = True
                                break
                        rows.append(dict(lift=lift, x0=x0, y0=y0, ax=ax, sp=sp, goal=goal, touched=touched, held=held, near=near))
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "slip.json").write_text(json.dumps(rows))
    for lift in (0, 4000):
        r = [x for x in rows if x["lift"] == lift]
        g = sum(x["goal"] for x in r)
        thr = sum(x["goal"] and not x["touched"] and x["near"] for x in r)
        print(f"{game} {'flat' if lift == 0 else 'lifted'}: {len(r)} pucks, goals {g} ({g / len(r):.0%}), through him untouched"
              f" {thr} ({thr / len(r):.0%}), saved (touched, no goal) {sum(x['touched'] and not x['goal'] for x in r)}", flush=True)


def make94(rom, out):
    import gen_ot_check as GO
    e = Emu(rom)
    o = Path(out); o.mkdir(parents=True, exist_ok=True)
    GO.to_setup(e, o)
    assert GO.into_play(e)
    e.run(200)
    (o / "live94.state").write_bytes(e.serialize())
    print("state", o / "live94.state")




def shots(game, rom, state, out):
    """Real shots: home's skater A takes the puck at a spot in the slot and shoots with C (held 6 or 14 frames, the pad
    aiming left, middle or right), everyone else parked; the goalie makes the game's own save moves. Per shot: a goal,
    touched by the goalie, the puck within 16 of his centre while at height 5 or less; "through him": a goal, untouched,
    low within 16 of him."""
    import gen95_assist_check as G
    c = CFG[game]
    G.BASE, G.TEAM = c["base"], c["team"]
    G.PUCK = G.rec(14)
    e = Emu(rom)
    base = Path(state).read_bytes()
    rows = []
    for sx in (-50, -30, -10, 10, 30, 50):
        for sy in (150, 180, 205):
            for aim in ([], ["LEFT"], ["RIGHT"]):
                for hold in (6, 14):
                    log = []
                    p = G.Play(e, base, {G.A: (sx, sy)}, log)
                    p.keep = {G.A}
                    if not p.pick_up(G.A, "A"):
                        continue
                    s0 = e.w(c["team"] + 0x0C)
                    shot = touched = near = goal = False
                    pv = None
                    for f in range(150):
                        held = ["UP"] + aim + (["C"] if f < hold else [])
                        p.park()
                        if f < hold:
                            p.hold([G.A])
                        e.run(1, hold=held)
                        P = G.PUCK
                        loose = e.b(P + 0x60) != 0
                        if not shot:
                            shot = loose and f >= hold
                            pv = None
                            continue
                        px, py, pz = s16(e.w(P)), s16(e.w(P + 0x14)), s16(e.w(P + 0x18))
                        gx, gy = s16(e.w(G.rec(GOALIE))), s16(e.w(G.rec(GOALIE) + 0x14))
                        v = (s16(e.w(P + 0x28)), s16(e.w(P + 0x2A)))
                        d = math.hypot(px - gx, py - gy)
                        if d <= REACH and pz <= 5:
                            near = True
                        if not loose:
                            touched = touched or e.b(P + 0x61) == GOALIE
                            break
                        if pv and d <= 22 and py < GOAL_Y - 2 and math.hypot(v[0] - pv[0], v[1] - pv[1]) > 0.2 * max(1, math.hypot(*pv)):
                            touched = True
                        pv = v
                        if e.w(c["team"] + 0x0C) != s0:
                            goal = True
                            break
                    if shot:
                        rows.append(dict(sx=sx, sy=sy, aim=aim, hold=hold, goal=goal, touched=touched, near=near))
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "shots.json").write_text(json.dumps(rows))
    g = sum(x["goal"] for x in rows)
    thr = sum(x["goal"] and not x["touched"] and x["near"] for x in rows)
    print(f"{game} shots: {len(rows)}, goals {g} ({g / max(1, len(rows)):.0%}), in through him untouched {thr}"
          f" ({thr / max(1, len(rows)):.0%}), saved {sum(x['touched'] and not x['goal'] for x in rows)}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "make":
        make94(sys.argv[2], sys.argv[3])
    elif "--shots" in sys.argv:
        shots(*sys.argv[1:5])
    else:
        run(*sys.argv[1:5])
