"""The scoring map, one worker of many: python map_run.py WORKER WORKERS RUN [budget] [shp sha] [GOALIES.json]
(results in paths.RUNS / RUN / w<WORKER>.jsonl; a worker restarted with the same arguments carries on).
Each job is a spot (x, y), a wind-up (3 = wrist shot, 20 = full slapshot) and a net (top: period 1, live.state;
bottom: period 2, live_p2.state). The 120 release moments are set up once per job (the aim doesn't change them:
checked on 1,600 launches) and every aim is sampled from them (mapper.cell's method). One JSON line per job."""
import json
import random
import sys
import time

from harness import Harness, fire, decide, rec, SHOOTER, GOALIE
from paths import RUNS, STATE_TOP, STATE_BOTTOM
from mapper import CLOCKS, SETTLES, set_ratings
from shotport import launch, perfect_chance, scatter_ranges
from lowload import breathe, gentle

gentle()

worker, workers = int(sys.argv[1]), int(sys.argv[2])
(RUNS / sys.argv[3]).mkdir(parents=True, exist_ok=True)
out = RUNS / sys.argv[3] / f"w{worker}.jsonl"
budget = int(sys.argv[4]) if len(sys.argv) > 4 else 800
shp, sha = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else (20, 15)
# with GOALIES.json (xg.goalie_states' output), every launch first puts the goalie where a recorded computer goalie was
# at a shot's release, relative to his set spot, and moving as he was ("as in games"); without it he is set
GOALIES = json.load(open(sys.argv[7]))["cpu"] if len(sys.argv) > 7 else None

XS = range(-110, 111, 10)
YS = range(100, 251, 10)
jobs = [(net, hold, x, y) for net in ("top", "bottom") for hold in (3, 20) for y in YS for x in XS]
done = set()
try:
    for line in open(out):
        r = json.loads(line)
        done.add((r["net"], r["hold"], r["x"], r["y"]))
except FileNotFoundError:
    pass

_top = Harness(state=STATE_TOP, top=True)
harness = {"top": _top, "bottom": Harness(state=STATE_BOTTOM, top=False, emu=_top.e)}


def prepare(h, x, y, hold):
    h.e.unserialize(h.base)
    set_ratings(h, shp, sha)
    rated, saved = h.e.serialize(), h.base
    pres, info = [], dict(backhand=0, stack=0, failed=0, puck=[0, 0], goalie=[0, 0])
    for c in CLOCKS:
        for s in SETTLES:
            h.base = rated
            h.setup(x, y, settle=s, clock=c)
            h.base = saved
            pre, f = h.shoot(8, hold)
            if pre is None:
                info["failed"] += 1
                continue
            en = h.entry()
            h.e.unserialize(pre)
            info["backhand"] += h.e.w(rec(SHOOTER) + 0x58) == 0x092E
            info["stack"] += en["gspa"] in (0x250, 0x2A2)
            for k, v in (("puck", (en["px"], en["py"])), ("goalie", (h.e.sw(rec(GOALIE)), h.e.sw(rec(GOALIE) + 0x14)))):
                info[k] = [a + b for a, b in zip(info[k], v)]
            pres.append((pre, dict(px=en["px"], py=en["py"], pout=en["pout"], sha=en["sha"], top=en["top"],
                                   vz0=0, gspa=en["gspa"])))
    for k in ("puck", "goalie"):        # mean over the moments, at the release
        info[k] = [round(v / max(1, len(pres)), 1) for v in info[k]]
    return pres, info




def pick(rng):
    return GOALIES[rng.randrange(len(GOALIES))] if GOALIES else None


with open(out, "a") as fo:
    for j, (net, hold, x, y) in enumerate(jobs):
        if j % workers != worker or (net, hold, x, y) in done:
            continue
        t0 = time.time()
        h = harness[net]
        yy = y if net == "top" else -y
        pres, info = prepare(h, x, yy, hold)
        row = dict(net=net, hold=hold, x=x, y=y, shp=shp, sha=sha, phases=len(pres), goalies="games" if GOALIES else "set",
                   **info, aims=[])
        if pres:
            rng = random.Random(hash((net, hold, x, y, shp, sha)) & 0xFFFFFFFF)
            row["pout"] = pres[0][1]["pout"]
            for aim in range(9):
                inps = [(pre, dict(i, dir=aim)) for pre, i in pres]
                p = float(perfect_chance(inps[0][1]))
                n_p = max(int(budget * p), len(inps)) if p else 0
                n_s = max(budget - n_p, 120) if p < 1 else 0
                gp = gs = 0
                for k in range(n_p):
                    pre, i = inps[k] if k < len(inps) else inps[rng.randrange(len(inps))]
                    fire(h, pre, launch(i, True), post_seed=rng.getrandbits(32), goalie=pick(rng))
                    gp += decide(h)[0]
                    breathe()
                for _ in range(n_s):
                    pre, i = inps[rng.randrange(len(inps))]
                    adj, yadj, zr, d3 = scatter_ranges(i)
                    v = launch(i, False, rng.randrange(-adj, adj) if adj else 0,
                               rng.randrange(-yadj, yadj) if yadj else 0, rng.randrange(zr) if zr else 0)
                    fire(h, pre, v, post_seed=rng.getrandbits(32), goalie=pick(rng))
                    gs += decide(h)[0]
                    breathe()
                perf = gp / n_p if n_p else 0.0
                sc = gs / n_s if n_s else 0.0
                var = (p * p * perf * (1 - perf) / n_p if n_p else 0) + \
                      ((1 - p) ** 2 * sc * (1 - sc) / n_s if n_s else 0)
                adj, _, _, d3 = scatter_ranges(inps[0][1])
                row["aims"].append(dict(aim=aim, chance=p * perf + (1 - p) * sc, se=var ** 0.5, p=p, perfect=perf,
                                        scatter=sc, n_p=n_p, n_s=n_s, adj=adj, d3=d3))
        row["secs"] = round(time.time() - t0, 1)
        fo.write(json.dumps(row) + "\n")
        fo.flush()
