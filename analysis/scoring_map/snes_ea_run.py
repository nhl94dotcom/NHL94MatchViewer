"""EA Specials on the SNES (retail ROM, snes_harness), 2026-10-26: is there one? The user: on the SNES the EA Special
has been found not to be a thing, or a very rare one; experiment. The Genesis play (ea_run.py): a wrist shot from the
side at a goalie in position, meant to come off him loose; the shooter skates on, claims it and at once shoots inside
the near post. On the SNES the hold rule runs the other way (SNES_SHOOTING 5.4): the goalie holds a puck slower than a
random 8,192-17,000 in each direction, and a harder one bounces straight out from his centre through where it touched,
slowly. So a soft wrist shot is held; a rebound needs a hard shot. Each job: the release spot (x across, attacker's
view, + his right; out from the goal line, 264), Shot Power (working, 0-15), the move ("r<kind><speed>": skating at
the goal or in at 45 degrees, released at (x, out): started LEAD frames back along his line, with the d-pad held along
it), the wind-up (A held: 3 = a wrist shot, longer = a harder half slapshot), the hand (a right-hander from his left,
x < 0, a left-hander from his right, as the Genesis's), and each of the nine aims; MOMENTS moments (the goalie's seed,
the clock, the settle frames) x SEEDS release seeds. After the release (as ea_run.play): he skates on at the goal; once
the goalie has touched the puck and it is loose he skates at it, and as soon as he has it taps A toward the near post
(the side of the net he is on). Per aim: the first result (goal straight in, held, bobble, miss) and, for a bobble,
the follow-up (goal, held, none, in off the goalie), the release speed and the mean release spot.
Skating: SNES full speed is about 2.2 a frame at Speed 15 (cap (20 + Speed) x 261 / 4096, SNES_MECHANICS 3.1), and
most skaters are at 15; the runs use 1.9, a little below it, as people take EA Specials.
Plans: "test" (a few set-ups, to check the release spot and the follow-up), "explore" (both nets, 20-27 ft to either
side, 13-29 ft out, Shot Power 5 / 10 / 15, wrist shot or 12-frame wind-up, both moves).
python snes_ea_run.py PLAN RUN [minutes]   -> paths.RUNS / RUN / snes_ea_<PLAN>.jsonl   (gentle mode, chunked)"""
import itertools
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool

import snes_harness as H
from lowload import WORKERS, breathe, gentle
from paths import RUNS, SNES_STATE_TOP, SNES_STATE_BOTTOM

MOMENTS = int(os.environ.get("NHL94_SEA_MOMENTS") or 24)
SEEDS = 2
GOAL_Y = 264
ATTR, FACING = 0x0E03, 0x1163
FIRST, FOLLOW = 60, 90         # frames to the first result; frames more for the follow-up
LEAD = {3: 6, 12: 12}          # frames of skating before the wind-up starts, by wind-up (from "test": released on
                               # the spot)
KEYS = ("net", "x", "out", "shp", "move", "hold")
_h = {}


def plan_jobs(plan):
    if plan == "test":
        return [("top", -80, 64, p, "rdiag1.9", hold) for p in (5, 15) for hold in (3, 12)] + \
               [("bottom", -80, 64, 15, "rgoal1.9", 3), ("bottom", 80, 64, 15, "rdiag1.9", 12)]
    if plan == "explore":
        return list(itertools.product(("top", "bottom"), (-80, -60, 60, 80), (40, 64, 88), (5, 10, 15),
                                      ("rgoal1.9", "rdiag1.9"), (3, 12)))
    raise SystemExit(f"unknown plan {plan}")


def _init():
    gentle()
    top = H.Harness(state=SNES_STATE_TOP, top=True)
    _h["top"], _h["bottom"] = top, H.Harness(state=SNES_STATE_BOTTOM, top=False, emu=top.e)


def toward(dx, dy):
    """The d-pad direction (0 up the screen, clockwise) nearest to (dx, dy) (screen: +y up the screen)."""
    return round(math.degrees(math.atan2(dx, dy)) / 45) % 8


def play(h, sg):
    """From the release: see the module notes. Returns the first result and what happened after a bobble."""
    e = h.e
    s, g, pk = H.o(H.SHOOTER), H.o(H.GOALIE), H.o(H.PUCK)
    s0 = e.w(H.SCORE_HOME)
    touched, pv, info, shot = None, None, dict(claim=None, follow="none"), False
    for f in range(FIRST + FOLLOW):
        h.park()
        sx, sy = h.sw(H.XPOS + s), h.sw(H.YPOS + s)
        px, py = h.sw(H.XPOS + pk), h.sw(H.YPOS + pk)
        gx, gy = h.sw(H.XPOS + g), h.sw(H.YPOS + g)
        if e.w(H.PUCKC) == s and touched is not None and not shot:
            info["claim"], shot = f - touched, True
            for _ in range(3):
                h.park()
                e.run(1, hold=["A", "RIGHT" if sx > 0 else "LEFT"])
            continue
        if touched is None or shot:
            pad = H.DIRPAD[toward(-sx, sg * GOAL_Y - sy)]
        else:
            pad = H.DIRPAD[toward(px - sx, py - sy)]
        e.run(1, hold=pad)
        if e.w(H.SCORE_HOME) != s0:
            if touched is None:
                return "goal", info
            info["follow"] = "goal" if shot else "in_off_goalie"
            return "bobble", info
        if e.w(H.PUCKC) == g:
            if touched is None or (not shot and info["claim"] is None and f - touched < 4):
                return "held", info
            info["follow"] = "held"
            return "bobble", info
        vx, vy = h.sw(H.XVEL + pk), h.sw(H.YVEL + pk)
        if touched is None:
            if pv is not None and math.hypot(px - gx, py - gy) < 24 and \
                    vx * pv[0] + vy * pv[1] < 0.5 * (pv[0] ** 2 + pv[1] ** 2):
                touched = f                              # turned or slowed hard beside the goalie: a save
                info["v"] = round(math.hypot(*pv))
            elif sg * py > GOAL_Y + 12 or f >= FIRST:
                return "miss", info
        elif shot and f - touched > FOLLOW:
            break
        pv = (vx, vy)
    return ("bobble", info) if touched is not None else ("miss", info)


def job(args):
    net, x, out, shp, move, hold = args
    h = _h[net]
    e = h.e
    sg = 1 if net == "top" else -1
    s = H.o(H.SHOOTER)
    rnd = random.Random(zlib.crc32(json.dumps(args).encode()))
    kind = move.rstrip("0123456789.").lstrip("r")
    v = float(move[len(move.rstrip("0123456789.")):])
    sx_ = 1 if x > 0 else -1
    dx, dy = dict(goal=(-sg * x, sg * out), diag=(-sg * sx_, sg))[kind]      # screen
    n = math.hypot(dx, dy)
    dx, dy = dx / n, dy / n
    back = LEAD[hold] + hold                                   # frames skated before the puck leaves the stick
    res, rel = {}, [0.0, 0.0, 0]
    for p in range(MOMENTS):
        x0, y0 = sg * x - back * dx * v, sg * (GOAL_Y - out) - back * dy * v
        h.setup(round(x0), round(y0), settle=80 + (p * 7) % 15, clock=590 - p % 8, seed=rnd.getrandbits(32))
        w = e.w(ATTR + s)
        e.setw(ATTR + s, (w | 0x800) if x < 0 else (w & ~0x800))       # a right-hander from his left
        e.setw(H.SHOTSPD + s, shp)
        e.setw(FACING + s, toward(dx, dy))
        e.setw(H.XVEL + s, round(dx * v * 4096) & 0xFFFF)
        e.setw(H.YVEL + s, round(dy * v * 4096) & 0xFFFF)
        base = e.serialize()
        skate = H.DIRPAD[toward(dx, dy)]
        for aim in range(9):
            c = res.setdefault(str(aim), dict(n=0, goal=0, held=0, bobble=0, miss=0, noshot=0, speed=0, claimed=0,
                                              follow_goal=0, follow_held=0, follow_none=0, follow_in_off_goalie=0))
            e.unserialize(base)
            pre = None
            for f in range(back + 40):                   # skating, then A held `hold` frames with the aim
                st = e.serialize()
                h.park()
                k = f - LEAD[hold]
                e.run(1, hold=skate if k < 0 else (["A"] if k < hold else []) + H.DIRPAD[aim])
                if e.w(H.PUCKC) & 0x8000:
                    pre = st
                    break
                if e.w(H.PUCKC) != s:
                    break
            if pre is None:
                c["noshot"] += 1
                continue
            e.unserialize(pre)
            rel[0] += sg * h.sw(H.XPOS + s)
            rel[1] += GOAL_Y - sg * h.sw(H.YPOS + s)
            rel[2] += 1
            for _ in range(SEEDS):
                h.fire(pre, aim, rnd.getrandbits(32))
                c["speed"] += math.hypot(h.sw(H.XVEL + H.o(H.PUCK)), h.sw(H.YVEL + H.o(H.PUCK)))
                r, info = play(h, sg)
                c["n"] += 1
                c[r] += 1
                if r == "bobble":
                    c["claimed"] += info["claim"] is not None
                    c["follow_" + info["follow"]] += 1
            breathe()
    for c in res.values():
        if c["n"]:
            c["speed"] = round(c["speed"] / c["n"])
    out_ = dict(zip(KEYS, args), aims=res)
    if rel[2]:
        out_["release"] = [round(rel[0] / rel[2], 1), round(rel[1] / rel[2], 1)]
    return out_


def main():
    plan, run = sys.argv[1], sys.argv[2]
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    path = RUNS / run / f"snes_ea_{plan}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        for line in open(path):
            d = json.loads(line)
            done.add(tuple(d[k] for k in KEYS))
    todo = [j for j in plan_jobs(plan) if j not in done]
    print(f"{plan}: {len(done)} jobs done before, {len(todo)} to go; this chunk: up to {minutes:g} minutes", flush=True)
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
    print(f"chunk over: {finished} jobs in {(time.time() - t0) / 60:.1f} minutes; {len(todo) - finished} left", flush=True)


if __name__ == "__main__":
    main()
