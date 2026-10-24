"""Moving shooters in the real game (Genesis test ROM), in chunks (2026-10-23, the user's ways of scoring against
people: across the crease, a soft wrist shot into the far side before the goalie gets there; in on a diagonal, the
near post as the goalie starts for the far one). Each job: a play, a start, the point of release, a net. For each of
MOMENTS moments (the clock and the frames the goalie settles) the shooter waits with the puck while the computer
goalie sets himself, then skates off at SPEED with the d-pad held his way and, on reaching the release point, takes a
wrist shot (C tapped) with each of the nine aims; the shot frame is replayed with SEEDS random seeds and played out
(harness.decide). Kept per aim, with where he released and how far the goalie was off the puck's line to the net.
Plans: "cross" (from 90 to one side, 25 / 35 / 45 out from the goal line, skating across; released at -40, -20, 0, 20,
40 across, signed so negative is before the middle), "diag" (from 130 to one side and 130 out, skating at 45 degrees
straight for the net's middle, so released at 100, 80, 60, 45 out he is as far to the side). Chunked and resumable like ot_run.py; gentle mode.
python mv_run.py PLAN RUN [minutes]   -> paths.RUNS / RUN / mv_<PLAN>.jsonl"""
import json
import math
import random
import sys
import time
import zlib
from multiprocessing import Pool

from harness import Harness, decide, rec, DIRPAD, E, SHOOTER, GOALIE, PUCKC
from lowload import WORKERS, breathe, gentle
from paths import RUNS, STATE_TOP, STATE_BOTTOM

MOMENTS, SEEDS, SPEED = 16, 4, 8000
GOAL_Y = 264


def plan_jobs(plan):
    jobs = []
    for net in ("top", "bottom"):
        for side in (-1, 1):
            if plan == "cross":
                for out in (25, 35, 45):
                    for rel in (-40, -20, 0, 20, 40):
                        jobs.append((plan, net, side, out, rel))
            elif plan == "diag":
                for rel in (100, 80, 60, 45):
                    jobs.append((plan, net, side, 130, rel))
    return jobs


_h = {}


def _init():
    gentle()
    top = Harness(state=STATE_TOP, top=True)
    _h["top"], _h["bottom"] = top, Harness(state=STATE_BOTTOM, top=False, emu=top.e)


def travel(plan, side, sg):
    """The d-pad direction he skates (0 up the screen, clockwise) and his velocity (units x 4096 a frame)."""
    if plan == "cross":
        d = 6 if side > 0 else 2                       # from the right going left, or from the left going right
        return d, (-SPEED * side, 0)
    vx, vy = -SPEED * side * 0.7071, SPEED * sg * 0.7071   # toward the middle and toward the net
    d = (7 if side > 0 else 1) if sg > 0 else (5 if side > 0 else 3)
    return d, (round(vx), round(vy))


def reached(plan, side, sg, x, y, rel):
    if plan == "cross":
        return -side * x >= rel                        # past `rel` across, in his direction of travel
    return GOAL_Y - sg * y <= rel                      # as close as `rel` out


def job(args):
    plan, net, side, out, rel = args
    h = _h[net]
    e = h.e
    sg = 1 if net == "top" else -1
    rnd = random.Random(zlib.crc32(f"{plan},{net},{side},{out},{rel}".encode()))
    d, (vx, vy) = travel(plan, side, sg)
    x0 = 90 * side if plan == "cross" else 130 * side      # diag: on the 45-degree line to the net's middle
    y0 = sg * (GOAL_Y - out)
    res = {str(a): {"GOAL": 0, "NO": 0, "noshot": 0, "rel": [0, 0], "off": 0.0, "n": 0} for a in range(9)}
    for p in range(MOMENTS):
        clock, settle = 590 - (p * 3) % 8, 80 + (p * 7) % 15
        h.setup(x0, y0, settle=settle, clock=clock)
        e.setb(rec(SHOOTER) + 0x55, d)                 # facing his way (else he turns as he goes, and curves in)
        e.setw(rec(SHOOTER) + 0x28, vx & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x2A, vy & 0xFFFF)
        go = None
        for f in range(150):                           # skate to the release point
            x, y = e.sw(rec(SHOOTER)), e.sw(rec(SHOOTER) + 0x14)
            if e.w(PUCKC) != SHOOTER:
                break                                  # lost it (the goalie poked it, or it slid off)
            if reached(plan, side, sg, x, y, rel):
                go = e.serialize()
                break
            h.park()
            e.run(1, hold=DIRPAD[d])
        if go is None:
            for a in range(9):
                res[str(a)]["noshot"] += 1
            continue
        for a in range(9):
            e.unserialize(go)
            n0, pre = e.w(E["n"]), None
            for f in range(40):                        # the wrist shot: C tapped, the aim held, his skating kept up
                st = e.serialize()
                h.park()
                e.run(1, hold=(["C"] if f < 3 else []) + DIRPAD[a] + (DIRPAD[d] if a == 8 else []))
                if e.w(E["n"]) != n0:
                    pre = st
                    break
            c = res[str(a)]
            if pre is None:
                c["noshot"] += 1
                continue
            e.unserialize(pre)
            sx, sy = e.sw(rec(SHOOTER)), e.sw(rec(SHOOTER) + 0x14)
            gx, gy = e.sw(rec(GOALIE)), e.sw(rec(GOALIE) + 0x14)
            gl = sg * GOAL_Y
            L = math.hypot(-sx, gl - sy) or 1
            off = abs((gx - sx) * (gl - sy) - (gy - sy) * (-sx)) / L
            c["rel"][0] += sx
            c["rel"][1] += GOAL_Y - sg * sy
            c["off"] += off
            c["n"] += 1
            for _ in range(SEEDS):
                e.unserialize(pre)
                e.setl(0xD066, rnd.getrandbits(32))
                h.park()
                e.run(1, hold=DIRPAD[a])
                g, _f = decide(h)
                c["GOAL" if g else "NO"] += 1
                breathe()
    for c in res.values():                             # averages: where he released, the goalie off the line
        if c["n"]:
            c["rel"] = [round(v / c["n"], 1) for v in c["rel"]]
            c["off"] = round(c["off"] / c["n"], 1)
    return {"plan": plan, "net": net, "side": side, "out": out, "rel": rel, "aims": res}


def main():
    plan, run = sys.argv[1], sys.argv[2]
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    path = RUNS / run / f"mv_{plan}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        for line in open(path):
            d = json.loads(line)
            done.add((d["plan"], d["net"], d["side"], d["out"], d["rel"]))
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
