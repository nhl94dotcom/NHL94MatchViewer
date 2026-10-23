"""The one-timer study, in chunks: python ot_run.py SYSTEM PLAN RUN [minutes] [net]
-> paths.RUNS / RUN / ot_<SYSTEM>_<PLAN>.jsonl, one line per finished job (a receiver spot R and a passer spot P at
one net). A run starts jobs only until `minutes` (default 60) have gone by, then waits for the ones under way and
stops; the next run with the same arguments skips every finished job, so a study is done in as many chunks as wanted
and can be stopped at any time (an unfinished job is simply run again). Gentle mode (lowload.py).

Each job: for each press timing ("early": 2 frames after the pass leaves; "late": about 6 frames before it arrives)
and each of MOMENTS moments (the clock and settle cycles; on the SNES also the goalie's random seed), the pass up to
the press (ot_harness); then for each aim (SNES: the nine d-pad directions, held from the press; Genesis: none, it
aims itself) the swing, and if it strikes the puck, the strike frame replayed with SEEDS random seeds, each played
out. Kept per moment, so the spread
between moments can be measured.

Plans: "pilot" (net top; receivers 68 out in the middle, 38 out to the right, 118 out to the left; passers 60 and 120
from each in 8 directions); "full" (both nets; receivers 7 across, -90 to 90, x 6 distances, 30 to 155 out; passers
60 and 120 away in 8 directions, on the ice; top net first)."""
import json
import math
import random
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

from lowload import WORKERS, breathe
from paths import RUNS

MOMENTS = 32
SEEDS = {"genesis": 8, "snes": 4}
AIMS = {"genesis": [None], "snes": list(range(9))}
TIMINGS = ("early", "late")


def plan_jobs(plan):
    if plan == "pilot":
        jobs = []
        for R in ((0, 200), (40, 230), (-30, 150)):
            for ang in range(0, 360, 45):
                for dist in (60, 120):
                    P = (round(R[0] + dist * math.sin(math.radians(ang))),
                         round(R[1] + dist * math.cos(math.radians(ang))))
                    if abs(P[0]) <= 110 and 10 <= P[1] <= 255:
                        jobs.append(("top", R, P))
        return jobs
    if plan == "full":
        # receivers: 7 across x 6 distances out (30-155 from the goal line); passers 60 and 120 away in 8
        # directions, on the ice; the top net first, then the bottom (so each net is a whole chunk or two)
        jobs = []
        for net in ("top", "bottom"):
            for out in (30, 55, 80, 105, 130, 155):
                for rx in (-90, -60, -30, 0, 30, 60, 90):
                    R = (rx, 268 - out)
                    for ang in range(0, 360, 45):
                        for dist in (60, 120):
                            P = (round(R[0] + dist * math.sin(math.radians(ang))),
                                 round(R[1] + dist * math.cos(math.radians(ang))))
                            if abs(P[0]) <= 110 and 10 <= P[1] <= 255:
                                jobs.append((net, R, P))
        return jobs
    raise ValueError(plan)


_ot = {}


def _init(system):
    from ot_harness import OneTimer
    _ot["ot"] = OneTimer(system)
    _ot["system"] = system


def job(args):
    net, R, P = args
    ot, system = _ot["ot"], _ot["system"]
    t0 = time.time()
    rnd = random.Random(zlib.crc32(f"{system},{net},{R},{P}".encode()))
    out = {"net": net, "R": R, "P": P, "timings": {}}
    for timing in TIMINGS:
        rows = []
        for p in range(MOMENTS):
            ot.setup(net, P, R, p, rnd)
            press, info = ot.pass_to_press(timing)
            if press is None:
                rows.append({"p": p, "passed": False, "why": info})
                breathe()
                continue
            res = {}
            for aim in AIMS[system]:
                pre, frames = ot.swing(press, aim)
                if pre is None:
                    res[str(aim)] = {"hit": False}
                    continue
                c = {"hit": True, "frames": frames, "GOAL": 0, "SAVED": 0, "POST": 0, "MISSED": 0}
                for _ in range(SEEDS[system]):
                    ot.strike(pre, aim, rnd.getrandbits(32))
                    c[ot.play_out()] += 1
                    breathe()
                res[str(aim)] = c
            rows.append({"p": p, "passed": True, "press": info, "res": res})
        out["timings"][timing] = rows
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    system, plan, run = sys.argv[1], sys.argv[2], sys.argv[3]
    minutes = float(sys.argv[4]) if len(sys.argv) > 4 else 60
    only = sys.argv[5] if len(sys.argv) > 5 else None             # one net only (top / bottom)
    path = RUNS / run / f"ot_{system}_{plan}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        for line in open(path):
            d = json.loads(line)
            done.add((d["net"], tuple(d["R"]), tuple(d["P"])))
    todo = [j for j in plan_jobs(plan) if (j[0], tuple(j[1]), tuple(j[2])) not in done and only in (None, j[0])]
    print(f"{system} {plan}: {len(done)} jobs done before, {len(todo)} to go; this chunk: up to {minutes:g} minutes",
          flush=True)
    t0, deadline = time.time(), time.time() + 60 * minutes
    finished = 0
    with Pool(WORKERS, initializer=_init, initargs=(system,)) as pool, open(path, "a") as f:
        pending = []
        queue = list(todo)
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
    left = len(todo) - finished
    print(f"chunk over: {finished} jobs in {(time.time() - t0) / 60:.1f} minutes; {left} left", flush=True)


if __name__ == "__main__":
    main()
