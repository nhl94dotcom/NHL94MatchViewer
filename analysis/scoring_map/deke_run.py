"""Dekes and floaters in the real game (Genesis test ROM), 2026-10-24: the user's close-in moves against the computer
goalie, as in the 2026-10-23 BOS-LA games (PROJECT_NOTES "Examples in the 2026-10-23 BOS-LA games"). Every move is
the same few inputs, read from those recordings: the skater comes in carrying the puck on one side (his facing a step
to that side), and close to the goalie holds the d-pad the other way: his facing swings two steps, the puck crosses
in front of him in about 15 frames while his skating barely changes, and he taps C (a wrist shot) with that direction
still held, so the shot is aimed at that side.
- deke (straight in: Neely's 1-0s; near-post deke, Neely's 9-0: coming in off the middle, drifting toward it, the
  puck pulled back out away from the middle)
- floater (Juneau's 3-0, Sweeney's 4-0: up and across on a diagonal, the puck swung back the other way and floated
  toward the far post from 45-55 out)
- best (each move's best set-up, 2026-10-24: for comparing goalies and shooters)
- deke2 (the user's refinements, 2026-10-24: start 30 / 45 / 60 to the side, swing 50-72 from the goalie, shoot with
  the swing's side held, straight Up, or Up and toward the swing's side)
- dekebh (the deke on the backhand, and the same for the forehand to compare: C once the puck is 4-16 units across
  on the swing's side, not at a set time, since a left-hander's puck takes about 8 frames longer to cross; the swing
  begun 72-115 from the goalie; kept: his facing at the release and whether it was a backhand by the game's rule)
- floaterbh (the floater on the backhand: across from the backhand side, swung back to the backhand; a wider timing
  grid, aimed at that side or up and toward it)
A move: start (x, y), velocity (units a frame), first facing, the d-pad held coming in, the d-pad of the swing, the
goalie distance at which the swing starts, frames from the swing to C, frames C is held; all in the attacker's view
(x + his right, y toward the net, facing 0 toward the net, clockwise), turned for the bottom net. The shooter's hand
is set in attribute bit 3 (+$04: set = right-handed, the flipped picture), which is what the game reads (Findhittype,
the stick's hot points), and in +$76 bit 0 to match (before 2026-10-24 11:00 only +$76 was set, which the game
ignores: every shooter was the test skater's own left hand). NHL94_DEKE_HANDS="R" plays one hand. MOMENTS moments
(clock, settle) x SEEDS seeds after the release, played out (harness.decide).
Chunked and resumable; gentle mode.
python deke_run.py PLAN RUN [minutes]   -> paths.RUNS / RUN / deke_<PLAN>.jsonl"""
import itertools
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool

from harness import Harness, decide, rec, DIRPAD, E, SHOOTER, GOALIE, PUCKC, SCORE_HOME
from lowload import WORKERS, breathe, gentle
from mapper import set_ratings
from paths import RUNS, STATE_TOP, STATE_BOTTOM

MOMENTS, SEEDS = int(os.environ.get("NHL94_DEKE_MOMENTS") or 12), 4
GOAL_Y = 264
# Shot Power, Shot Accuracy: the map's usual shooter; NHL94_SMAP_RATINGS="shp,sha" for others
RATINGS = tuple(map(int, os.environ.get("NHL94_SMAP_RATINGS", "20,15").split(",")))
HANDS = os.environ.get("NHL94_DEKE_HANDS", "L,R").split(",")
SKATE = os.environ.get("NHL94_DEKE_SKATE")     # "agl,spd": the shooter's working Agility and Speed (else the state's)
KEYS = ("plan", "net", "hand", "x0", "side", "D", "lag", "hold", "var")
PAD = {"U": 0, "UR": 1, "R": 2, "DR": 3, "D": 4, "DL": 5, "L": 6, "UL": 7}


def screen_dir(d, top):
    return d if top else (d + 4) % 8


def plan_jobs(plan):
    """(plan, net, hand, x0, side, D, lag, hold, var): side +1 = carried on his right coming in, swung to his left;
    var: "side" (C with the swing's side held: aimed at that side, middle height), "low" (that side along the ice),
    "still" (the control: no swing, the puck kept where it was, the same shot at the same moment)."""
    jobs = []
    if plan == "best":                # each move's best set-up (deke2, dekebh, floater, floaterbh), to compare goalies
        for net in ("top", "bottom"):  # (NHL94_GOALIE) and shooters (NHL94_SMAP_RATINGS, NHL94_DEKE_SKATE)
            jobs += [("deke2", net, "L", -45, 1, 60, 10, 4, "side"), ("deke2", net, "R", -45, 1, 60, 13, 4, "side"),
                     ("deke2", net, "R", 60, -1, 72, 22, 4, "side"), ("deke2", net, "L", 45, -1, 72, 22, 4, "upside"),
                     ("dekebh", net, "L", 45, -1, 85, 8, 4, "side"), ("dekebh", net, "R", -30, 1, 72, 8, 4, "side"),
                     ("floater", net, "L", -50, 1, 95, 18, 6, "side"), ("floater", net, "R", 35, -1, 110, 22, 9, "side"),
                     ("floaterbh", net, "L", 50, -1, 110, 26, 9, "side"),
                     ("floaterbh", net, "R", -50, 1, 95, 14, 9, "side")]
        return jobs
    if plan == "deke2":               # the user's refinements (2026-10-24): from further out to the side, closer in,
        for net, hand, side, X, D, lag, var in itertools.product(        # the stick up (U) or up and across
                ("top", "bottom"), HANDS, (1, -1), (30, 45, 60), (50, 60, 72), (10, 13, 16, 19, 22),
                ("side", "up", "upside")):
            jobs.append((plan, net, hand, -side * X, side, D, lag, 4, var))
        return jobs
    if plan == "dekebh":              # the deke on the backhand, shot once the puck is across (the user, 2026-10-24):
        for net, hand, side, X, D, T, var in itertools.product(           # lag = how far across (units) the puck
                ("top", "bottom"), HANDS, (1, -1), (15, 30, 45), (72, 85, 100, 115), (4, 8, 12, 16),
                ("side", "up", "upside")):                             # must be on the swing's side before C
            jobs.append((plan, net, hand, -side * X, side, D, T, 4, var))
        return jobs
    if plan == "floaterbh":           # the floater on the backhand: across from the backhand side, swung back to it
        for net, hand, X, D, lag, hold, var in itertools.product(
                ("top", "bottom"), HANDS, (35, 50), (80, 95, 110, 125), (10, 14, 18, 22, 26, 30), (3, 6, 9),
                ("side", "upside")):
            side = -1 if hand == "L" else 1
            jobs.append((plan, net, hand, -side * X, side, D, lag, hold, var))
        return jobs
    for net, hand, side, var in itertools.product(("top", "bottom"), HANDS, (1, -1), ("side", "low", "still")):
        if plan == "deke":
            for x0, D, lag in itertools.product((-30, -15, 0, 15, 30), (60, 72, 85), (4, 7, 10, 13, 16, 19)):
                jobs.append((plan, net, hand, x0, side, D, lag, 4, var))
        elif plan == "floater":       # side +1: from his left going right (Juneau, Sweeney), -1 the mirror
            for x0, D, lag, hold in itertools.product((50, 35), (80, 95, 110), (6, 10, 14, 18, 22), (3, 6, 9)):
                jobs.append((plan, net, hand, -side * x0, side, D, lag, hold, var))
    return jobs


def move(plan, x0, side):
    """Start y, velocity (x, y), first facing, d-pad coming in, d-pad of the swing, the swing's side (attacker's
    view). The swing is held on the diagonal (straight to the side, he keeps turning and faces across, and C then
    drops the puck instead of shooting)."""
    if plan in ("deke", "deke2", "dekebh"):
        drift = -0.5 if x0 > 0 else 0.5 if x0 < 0 else 0.0     # off the middle: drifting toward it (Neely's 9-0)
        return 140, (drift, 2.1), (1 if side > 0 else 7), ("UR" if side > 0 else "UL"), ("UL" if side > 0 else "UR")
    # floater: up and across at about 2 a frame, facing the way he goes, the puck on his leading side
    return 105, (1.5 * side, 1.5), (1 if side > 0 else 7), ("UR" if side > 0 else "UL"), ("UL" if side > 0 else "UR")


AIM = {("side", 1): "L", ("side", -1): "R", ("low", 1): "DL", ("low", -1): "DR",
       ("up", 1): "U", ("up", -1): "U", ("upside", 1): "UL", ("upside", -1): "UR"}


_h = {}


def _init():
    gentle()
    top = Harness(state=STATE_TOP, top=True)
    _h["top"], _h["bottom"] = top, Harness(state=STATE_BOTTOM, top=False, emu=top.e)


def job(args):
    plan, net, hand, x0, side, D, lag, hold, var = args
    h = _h[net]
    e = h.e
    top = net == "top"
    sg = 1 if top else -1
    rnd = random.Random(zlib.crc32(json.dumps(args).encode()))
    y0, (vx, vy), face, pad_in, pad_swing = move(plan, x0, side)
    if var == "still":
        pad_swing, aim = pad_in, ("L" if side > 0 else "R")
    else:
        aim = AIM[(var, side)]
    din, dsw, dam = (screen_dir(PAD[k], top) for k in (pad_in, pad_swing, aim))
    res = dict(GOAL=0, NO=0, noshot=0, lost=0, carried=0, n=0, release=[0.0, 0.0], gdist=0.0, goff=0.0, pside=0.0,
               gmove=0.0, faces={}, backhand=0)
    for p in range(MOMENTS):
        clock, settle = 590 - (p * 3) % 8, 80 + (p * 7) % 15
        h.setup(sg * x0, sg * y0, settle=settle, clock=clock)
        set_ratings(h, *RATINGS)
        if SKATE:
            for off, v in zip((0x68, 0x69), map(int, SKATE.split(","))):
                e.setb(rec(SHOOTER) + off, v)
        b, a = e.b(rec(SHOOTER) + 0x76), e.b(rec(SHOOTER) + 4)     # the game reads the hand from attribute bit 3
        e.setb(rec(SHOOTER) + 0x76, (b | 1) if hand == "L" else (b & ~1))      # (set: right-handed, drawn flipped)
        e.setb(rec(SHOOTER) + 4, (a & ~8) if hand == "L" else (a | 8))
        e.setb(rec(SHOOTER) + 0x55, screen_dir(face, top))
        e.setw(rec(SHOOTER) + 0x28, round(sg * vx * 4096) & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x2A, round(sg * vy * 4096) & 0xFFFF)
        n0, swing, pre, g0, trig = e.w(E["n"]), None, None, None, None
        for f in range(200):
            sx, sy = e.sw(rec(SHOOTER)), e.sw(rec(SHOOTER) + 0x14)
            gx, gy = e.sw(rec(GOALIE)), e.sw(rec(GOALIE) + 0x14)
            if e.w(PUCKC) != SHOOTER:
                break
            if swing is None and math.hypot(sx - gx, sy - gy) <= D:
                swing, g0 = f, gx
            if plan == "dekebh":                 # C once the puck is `lag` across toward the swing's side
                across = -side * sg * (e.sw(rec(14)) - sx)
                if trig is None and swing is not None and (across >= lag or var == "still" and f >= swing + 16):
                    trig = f
                c = trig is not None
                d = din if swing is None else dam if c else dsw
                c = c and f < trig + hold
            else:
                c = swing is not None and f >= swing + lag
                d = din if swing is None else dam if c else dsw
                c = c and f < swing + lag + hold
            st = e.serialize()
            h.park()
            e.run(1, hold=(["C"] if c else []) + DIRPAD[d])
            if e.w(E["n"]) != n0:
                pre = st
                break
        if pre is None:
            if swing is not None:                # the puck gone before any shot: lost, or carried into the net by
                s0 = e.w(SCORE_HOME)             # the skater himself (a goal: found 2026-10-25 with fast skaters)
                for _ in range(60):
                    h.park()
                    e.run(1)
                res["carried" if e.w(SCORE_HOME) != s0 else "lost"] += 1
            else:
                res["noshot"] += 1
            continue
        e.unserialize(pre)
        sx, sy = e.sw(rec(SHOOTER)), e.sw(rec(SHOOTER) + 0x14)
        gx, gy = e.sw(rec(GOALIE)), e.sw(rec(GOALIE) + 0x14)
        px, py = e.sw(rec(14)), e.sw(rec(14) + 0x14)
        gl = sg * GOAL_Y
        L = math.hypot(-px, gl - py) or 1
        res["n"] += 1
        res["release"][0] += sg * sx
        res["release"][1] += GOAL_Y - sg * sy
        res["gdist"] += math.hypot(sx - gx, sy - gy)
        res["goff"] += abs((gx - px) * (gl - py) - (gy - py) * (-px)) / L     # goalie off the puck's line to the net
        res["pside"] += sg * (px - sx)                                         # where the puck was, across (his right +)
        res["gmove"] += sg * (gx - g0)                                         # how far the goalie moved since the swing
        f_rel = (e.b(rec(SHOOTER) + 0x55) - (0 if top else 4)) % 8            # his facing, attacker's view
        res["faces"][str(f_rel)] = res["faces"].get(str(f_rel), 0) + 1
        # a backhand by the game's rule (Findhittype): the net 45-180 degrees round to his backhand side
        to_net = round(math.degrees(math.atan2(sg * -sx, sg * (gl - sy))) / 45) % 8      # the net's direction
        rel = (f_rel - to_net) % 8
        res["backhand"] += (rel in (4, 5, 6, 7)) if hand == "R" else (rel in (1, 2, 3, 4))
        for _ in range(SEEDS):
            e.unserialize(pre)
            e.setl(0xD066, rnd.getrandbits(32))
            h.park()
            e.run(1, hold=DIRPAD[dam])
            g, _f = decide(h)
            res["GOAL" if g else "NO"] += 1
            breathe()
    if res["n"]:
        res["release"] = [round(v / res["n"], 1) for v in res["release"]]
        for k in ("gdist", "goff", "pside", "gmove"):
            res[k] = round(res[k] / res["n"], 1)
    return dict(zip(KEYS, args), **res)


def main():
    plan, run = sys.argv[1], sys.argv[2]
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    path = RUNS / run / f"deke_{plan}.jsonl"
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
            for a in [a for a in pending if a.ready()]:
                pending.remove(a)
                f.write(json.dumps(a.get()) + "\n")
                f.flush()
                finished += 1
    print(f"chunk over: {finished} jobs in {(time.time() - t0) / 60:.1f} minutes; {len(todo) - finished} left", flush=True)


if __name__ == "__main__":
    main()
