"""The SNES scoring map: python snes_map_run.py RUN [phases seeds] [shp sha] [workers] -> paths.RUNS / RUN / snes_map.json

Every spot (shooter x -110..110, y 90..250 from centre ice, steps of 10) at both nets, a wrist shot (A tapped) and a
full slapshot (A held), each of the nine aims; `phases` moments (a random seed for the goalie's own random draws, the
clock, the frames he has to settle) times `seeds` release seeds (the shot's draws and everything after). The shooter's
working Shot Power and Shot Accuracy default to 13 / 13, the median of the recorded SNES shots. Validity as validity.py:
at the release the puck at least 24 from the goalie's centre and in front of him, the shooter 16 or more from him.
Defaults: all 120 moments (every clock x settle pair) x 4 seeds; run snes1 used 16 x 24, too few moments (the rate
swings about 0.27 from moment to moment: PROJECT_NOTES). Gentle mode (lowload.py).

NHL94_SNES_GOALIES=<file> (xg_snes.goalie_states' output; 2026-11-07): the goalie "as in games", as map_run.py does on
the Genesis: before each release seed he is moved off his spot as a recorded computer goalie was at a shot's release,
relative to his set spot, and given that goalie's speed (as if at the top net; mirrored for the bottom). Validity is
judged with him set, so the cells are the set-goalie map's. NHL94_SMAP_SUBSET=coarse: every other spot (x -100..100,
y 100..240, steps of 20). NHL94_SMAP_MINUTES: stop after this long (a chunk; run again to carry on)."""
import json
import os
import random
import sys
import zlib
from multiprocessing import Pool

from paths import RUNS, SNES_STATE_TOP, SNES_STATE_BOTTOM
import snes_harness as H
from lowload import WORKERS, breathe, gentle

XS = range(-110, 111, 10)
YS = range(90, 251, 10)
SHOTS = {"wrist": 3, "slap": 40}
SUBSET = os.environ.get("NHL94_SMAP_SUBSET")   # slapmid: slapshots only (set here: the workers load this module afresh)
if SUBSET in ("slapmid", "slapcore"):
    SHOTS = {"slap": 40}
MIN_PUCK = 24
GOALIES = json.load(open(os.environ["NHL94_SNES_GOALIES"]))["cpu"] if os.environ.get("NHL94_SNES_GOALIES") else None

_h = {}


def _init(shp, sha):
    gentle()
    e = None
    for net, st, top in (("top", SNES_STATE_TOP, True), ("bottom", SNES_STATE_BOTTOM, False)):
        h = H.Harness(state=st, top=top, emu=e)
        e = h.e
        e.unserialize(h.base)
        e.setw(H.SHOTSPD + H.o(H.SHOOTER), shp)
        e.setw(H.SHOTACC + H.o(H.SHOOTER), sha)
        h.base = e.serialize()
        _h[net] = h


def job(args):
    net, x, y, phases, seeds = args
    h = _h[net]
    sg = 1 if net == "top" else -1
    rnd = random.Random(zlib.crc32(f"{net},{x},{y}".encode()))
    out = {}
    for p in range(phases):
        h.setup(x, sg * y, settle=80 + (p * 7) % 15, clock=590 - p % 8, seed=rnd.getrandbits(32))
        settled = h.e.serialize()
        for kind, hold in SHOTS.items():
            for aim in range(9):
                key = f"{kind},{aim}"
                c = out.setdefault(key, dict(n=0, g=0, valid=0, noshot=0, dp=0.0))
                h.e.unserialize(settled)
                pre, f = h.shoot(aim, hold)
                if pre is None:
                    c["noshot"] += 1
                    continue
                e = h.e
                e.unserialize(pre)
                g, s = H.o(H.GOALIE), H.o(H.SHOOTER)
                gx, gy = h.sw(H.XPOS + g), h.sw(H.YPOS + g)
                px, py = h.sw(H.XPOS + H.o(H.PUCK)), h.sw(H.YPOS + H.o(H.PUCK))
                sx, sy = h.sw(H.XPOS + s), h.sw(H.YPOS + s)
                dp = ((px - gx) ** 2 + (py - gy) ** 2) ** 0.5
                ds = ((sx - gx) ** 2 + (sy - gy) ** 2) ** 0.5
                c["dp"] += dp
                if not (dp >= MIN_PUCK and ds >= 16 and sg * py < sg * gy):
                    continue
                c["valid"] += 1
                for _ in range(seeds):
                    shot_from = pre
                    if GOALIES:
                        dx, dy, vx, vy = (sg * v for v in GOALIES[rnd.randrange(len(GOALIES))])
                        e.unserialize(pre)
                        h.put(H.GOALIE, round(gx + dx), round(gy + dy))
                        e.setw(H.XVEL + g, round(vx * 4096) & 0xFFFF)
                        e.setw(H.YVEL + g, round(vy * 4096) & 0xFFFF)
                        shot_from = e.serialize()
                    h.fire(shot_from, aim, rnd.getrandbits(32))
                    r, _f = h.decide()
                    c["n"] += 1
                    breathe()
                    c["g"] += r
    return f"{net},{x},{y}", out


def main():
    run = sys.argv[1]
    phases, seeds = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (120, 4)
    shp, sha = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (13, 13)
    workers = int(sys.argv[6]) if len(sys.argv) > 6 else WORKERS
    jobs = [(net, x, y, phases, seeds) for net in ("top", "bottom") for y in YS for x in XS]
    if SUBSET == "slapmid":                                 # as map_run.py: slapshots, middle half, 30-55 feet out
        jobs =[j for j in jobs if abs(j[1]) <= 60 and j[1] % 20 == 0 and 100 <= j[2] <= 180 and j[2] % 20 == 0]
    if SUBSET == "slapcore":                                # 9 spots in the middle, for many shooters
        jobs = [j for j in jobs if j[1] in (-40, 0, 40) and j[2] in (120, 140, 160)]
    if SUBSET == "coarse":                                  # every other spot
        jobs = [j for j in jobs if j[1] % 20 == 0 and abs(j[1]) <= 100 and j[2] % 20 == 0 and 100 <= j[2] <= 240]
    path = RUNS / run / "snes_map.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    res = json.load(open(path)) if path.exists() else {"meta": dict(phases=phases, seeds=seeds, shp=shp, sha=sha,
                                                                    goalies="games" if GOALIES else "set")}
    jobs = [j for j in jobs if f"{j[0]},{j[1]},{j[2]}" not in res]       # resumable: saved after every spot
    with Pool(workers, initializer=_init, initargs=(shp, sha)) as pool:
        t0 = __import__("time").time()
        minutes = float(os.environ.get("NHL94_SMAP_MINUTES") or 1e9)
        for i, (k, v) in enumerate(pool.imap_unordered(job, jobs)):
            res[k] = v
            json.dump(res, open(path, "w"))
            if __import__("time").time() - t0 > minutes * 60:
                print("time up", flush=True)
                pool.terminate()
                break
            if i % 10 == 0:
                print(i, "of", len(jobs), flush=True)
    print("done")


if __name__ == "__main__":
    main()
