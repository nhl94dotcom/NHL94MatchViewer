"""The carry-in (the walk-in without the first shot), Genesis and SNES, 2026-10-28: does carrying the puck straight at
the goal mouth make the computer goalie commit, and does a wrist shot at the near post then score?

Both games work out where and when the puck will cross each goal line from its velocity, carried or loose (Genesis
findpc, SNES pucknorm), and the computer goalie goes to that crossing point and then into a save move: Genesis once it
is under 34 frames away and within 24 of the middle, the save under 12 frames (checks94 .18); SNES under 35 and 19
(assgoalie). So a carrier skating at the middle of the goal line looks to him like a shot on the way.

Each job: the net, the start spot (x across, attacker's view, + his right; out from the goal line; a right-hander
from his left, a left-hander from his right, as the EA runs), the shooting distance D (the wrist shot at the near
post, the side he is on, as soon as the puck is within D of the goalie's centre; 0 = never shoot, carry it in). The
walk-in itself (a weak first shot he catches up with) is measured by ea_run.py and snes_ea_run.py's plan "walkin". The
skater starts there with the puck, already skating at the middle of the goal line at the set speed (Genesis 1.7, SNES
1.9 a frame), and holds the d-pad that way. MOMENTS moments (the goalie's settle and the clock; Genesis: the shot's
seed too). Per job: goal, held, saved (touched, not held), missed, lost (the puck taken off him), carried in (a goal
without a shot), and at the shot the goalie's save-move share and his distance across from the middle toward the
shooter's side.
python carry_run.py genesis|snes RUN [minutes]   -> paths.RUNS / RUN / carry_<system>.jsonl   (gentle mode, chunked)"""
import itertools
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool

from lowload import WORKERS, breathe, gentle
from paths import RUNS

SYSTEM = sys.argv[1] if len(sys.argv) > 1 else "genesis"
MOMENTS = int(os.environ.get("NHL94_CARRY_MOMENTS") or 24)
GOAL_Y = 264
KEYS = ("net", "x", "out", "d")
DISTANCES = (0, 12, 16, 20, 24, 28, 32)
GENESIS_SAVES = {0x146, 0x178, 0x250, 0x2A2, 0x1EC, 0x21E, 0x148E, 0x14C0, 0x14F2, 0x1544}   # goaliesave .saveanim
SNES_SAVES = {0xE1E2, 0xE214, 0xE2AA, 0xE2FC, 0xE246, 0xE278, 0xE862, 0xE7D0, 0xE73E}       # GoalieSaveList
_h = {}


def plan_jobs():
    return list(itertools.product(("top", "bottom"), (-80, -70, 70, 80), (52, 64, 76), DISTANCES))


def toward(dx, dy):
    return round(math.degrees(math.atan2(dx, dy)) / 45) % 8


def _init():
    gentle()
    if SYSTEM == "genesis":
        from harness import Harness
        from paths import STATE_TOP, STATE_BOTTOM
        top = Harness(state=STATE_TOP, top=True)
        _h["top"], _h["bottom"] = top, Harness(state=STATE_BOTTOM, top=False, emu=top.e)
    else:
        import snes_harness as H
        from paths import SNES_STATE_TOP, SNES_STATE_BOTTOM
        top = H.Harness(state=SNES_STATE_TOP, top=True)
        _h["top"], _h["bottom"] = top, H.Harness(state=SNES_STATE_BOTTOM, top=False, emu=top.e)


class Genesis:
    """The Genesis test ROM through harness.py (records: x +$00, y +$14, the animation word +$58)."""
    def __init__(self, h):
        import harness as G
        from mapper import set_ratings
        self.G, self.h, self.e = G, h, h.e
        self.s, self.g, self.p = G.SHOOTER, G.GOALIE, 14
        self.set_ratings = set_ratings
        self.power = 20

    def pos(self, k):
        return self.e.sw(self.G.rec(k)), self.e.sw(self.G.rec(k) + 0x14)

    def setup(self, x0, y0, p, rnd, lefty, dx, dy, v):
        G, e = self.G, self.e
        self.h.setup(round(x0), round(y0), settle=80 + (p * 7) % 15, clock=590 - (p * 3) % 8)
        self.set_ratings(self.h, self.power, 20)
        b, a = e.b(G.rec(self.s) + 0x76), e.b(G.rec(self.s) + 4)
        e.setb(G.rec(self.s) + 0x76, (b | 1) if lefty else (b & ~1))
        e.setb(G.rec(self.s) + 4, (a & ~8) if lefty else (a | 8))
        e.setb(G.rec(self.s) + 0x55, toward(dx, dy))
        e.setw(G.rec(self.s) + 0x28, round(dx * v * 4096) & 0xFFFF)
        e.setw(G.rec(self.s) + 0x2A, round(dy * v * 4096) & 0xFFFF)
        self.seed = rnd.getrandbits(32)

    def carrier(self):
        c = self.e.w(self.G.PUCKC)
        return None if c >> 8 == 0xFF else c

    def saving(self):
        return self.e.w(self.G.rec(self.g) + 0x58) in GENESIS_SAVES

    def step(self, hold):
        self.h.park()
        self.e.run(1, hold=hold)

    def shoot_button(self):
        self.e.setl(0xD066, self.seed)                  # the test ROM's doshot draws
        return "C"

    def score(self):
        return self.e.w(self.G.SCORE_HOME)

    def pad(self, d):
        return self.G.DIRPAD[d]


class Snes:
    """The retail SNES ROM through snes_harness.py (word arrays, object k at +2k)."""
    def __init__(self, h):
        import snes_harness as H
        self.H, self.h, self.e = H, h, h.e
        self.s, self.g, self.p = H.SHOOTER, H.GOALIE, H.PUCK
        self.power = 8

    def pos(self, k):
        return self.h.sw(self.H.XPOS + self.H.o(k)), self.h.sw(self.H.YPOS + self.H.o(k))

    def setup(self, x0, y0, p, rnd, lefty, dx, dy, v):
        H, e, s = self.H, self.e, self.H.o(self.s)
        self.h.setup(round(x0), round(y0), settle=80 + (p * 7) % 15, clock=590 - p % 8, seed=rnd.getrandbits(32))
        w = e.w(0x0E03 + s)
        e.setw(0x0E03 + s, (w & ~0x800) if lefty else (w | 0x800))     # a right-hander from his left (mirrored)
        e.setw(H.SHOTSPD + s, self.power)
        e.setw(0x1163 + s, toward(dx, dy))
        e.setw(H.XVEL + s, round(dx * v * 4096) & 0xFFFF)
        e.setw(H.YVEL + s, round(dy * v * 4096) & 0xFFFF)

    def carrier(self):
        c = self.e.w(self.H.PUCKC)
        return None if c & 0x8000 else c // 2

    def saving(self):
        return self.e.w(self.H.SPA + self.H.o(self.g)) in SNES_SAVES

    def step(self, hold):
        self.h.park()
        self.e.run(1, hold=hold)

    def shoot_button(self):
        return "A"

    def score(self):
        return self.e.w(self.H.SCORE_HOME)

    def pad(self, d):
        return self.H.DIRPAD[d]


def shoot(G, sg, s0, side, info):
    """A wrist shot at the near post (the side of the net he is on) and what came of it."""
    gx, gy = G.pos(G.g)
    px, py = G.pos(G.p)
    info.update(saving=G.saving(), dist=round(math.hypot(px - gx, py - gy), 1), across=round(gx * side, 1))
    near, button = G.pad(2 if side > 0 else 6), G.shoot_button()
    for c in range(24):                                  # the button 3 frames (again every 8 if it hasn't gone),
        G.step(([button] if c % 8 < 3 else []) + near)   # the aim held until the puck leaves
        if G.carrier() != G.s:
            break
    if G.carrier() == G.s:
        return "no shot"
    held = 0
    for _ in range(120):
        G.step([])
        if G.score() != s0:
            return "goal"
        held = held + 1 if G.carrier() == G.g else 0
        if held >= 20:
            return "held"
        if sg * G.pos(G.p)[1] > GOAL_Y + 12:
            return "missed"
    return "saved"


def play(G, sg, d):
    """From the start: carry at the middle of the goal line, shoot at the near post within d of the goalie."""
    s0 = G.score()
    info = dict(saving=None, across=None, dist=None)
    for f in range(240):
        sx, sy = G.pos(G.s)
        px, py = G.pos(G.p)
        gx, gy = G.pos(G.g)
        if G.carrier() != G.s:
            return "lost", info
        if d and math.hypot(px - gx, py - gy) <= d:
            return shoot(G, sg, s0, 1 if sx > 0 else -1, info), info
        G.step(G.pad(toward(-sx, sg * GOAL_Y - sy)))
        if G.score() != s0:
            return "carried in", info
    return "no shot", info


def job(args):
    net, x, out, d = args
    h = _h[net]
    G = Genesis(h) if SYSTEM == "genesis" else Snes(h)
    sg = 1 if net == "top" else -1
    v = 1.7 if SYSTEM == "genesis" else 1.9
    rnd = random.Random(zlib.crc32(json.dumps([SYSTEM] + list(args)).encode()))
    res = dict(n=0, saving=0, across=0.0, dist=0.0, shots=0)
    for p in range(MOMENTS):
        x0, y0 = sg * x, sg * (GOAL_Y - out)
        dx, dy = -x0, sg * GOAL_Y - y0                    # screen: at the middle of the goal line
        n = math.hypot(dx, dy)
        G.setup(x0, y0, p, rnd, (x > 0), dx / n, dy / n, v)
        r, info = play(G, sg, d)
        res["n"] += 1
        res[r] = res.get(r, 0) + 1
        if info["dist"] is not None:
            res["shots"] += 1
            res["saving"] += info["saving"]
            res["across"] += info["across"]
            res["dist"] += info["dist"]
        breathe()
    return dict(zip(KEYS, args), **res)


def main():
    run = sys.argv[2]
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    path = RUNS / run / f"carry_{SYSTEM}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        for line in open(path):
            r = json.loads(line)
            done.add(tuple(r[k] for k in KEYS))
    todo = [j for j in plan_jobs() if j not in done]
    print(f"carry {SYSTEM}: {len(done)} done before, {len(todo)} to go", flush=True)
    t0, deadline, finished = time.time(), time.time() + 60 * minutes, 0
    with Pool(WORKERS, initializer=_init) as pool, open(path, "a") as f:
        pending, queue = [], list(todo)
        while queue or pending:
            while queue and len(pending) < WORKERS and time.time() < deadline:
                pending.append(pool.apply_async(job, (queue.pop(0),)))
            if not pending:
                break
            time.sleep(1)
            for r in [r for r in pending if r.ready()]:
                pending.remove(r)
                f.write(json.dumps(r.get()) + "\n")
                f.flush()
                finished += 1
    print(f"chunk over: {finished} jobs in {(time.time() - t0) / 60:.1f} minutes", flush=True)


if __name__ == "__main__":
    main()
