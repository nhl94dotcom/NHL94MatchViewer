"""The SNES scoring map: python snes_map_run.py RUN [phases seeds] [shp sha] [workers] -> paths.RUNS / RUN / snes_map.json

Every spot (shooter x -110..110, y 90..250 from centre ice, steps of 10) at both nets, a wrist shot (A tapped) and a
full slapshot (A held), each of the nine aims; `phases` moments (a random seed for the goalie's own random draws, the
clock, the frames he has to settle) times `seeds` release seeds (the shot's draws and everything after). The shooter's
working Shot Power and Shot Accuracy default to 13 / 13, the median of the recorded SNES shots. Validity as validity.py:
at the release the puck at least 24 from the goalie's centre and in front of him, the shooter 16 or more from him.
Defaults: all 120 moments (every clock x settle pair) x 4 seeds; run snes1 used 16 x 24, too few moments (the rate
swings about 0.27 from moment to moment: PROJECT_NOTES). Gentle mode (lowload.py)."""
import json
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
MIN_PUCK = 24

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
                    h.fire(pre, aim, rnd.getrandbits(32))
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
    res = {"meta": dict(phases=phases, seeds=seeds, shp=shp, sha=sha)}
    with Pool(workers, initializer=_init, initargs=(shp, sha)) as pool:
        for i, (k, v) in enumerate(pool.imap_unordered(job, jobs)):
            res[k] = v
            if i % 50 == 0:
                print(i, "of", len(jobs), flush=True)
    (RUNS / run).mkdir(parents=True, exist_ok=True)
    json.dump(res, open(RUNS / run / "snes_map.json", "w"))
    print("done")


if __name__ == "__main__":
    main()
