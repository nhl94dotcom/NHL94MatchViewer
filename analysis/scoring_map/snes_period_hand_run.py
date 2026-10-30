"""Two SNES questions played in the game (2026-10-30): python snes_period_hand_run.py RUN [phases seeds] [conditions]
-> paths.RUNS / RUN / snes_period_hand.json

1. The second period. The leagues' results show about 5% fewer SNES goals a shot in period 2 for both teams
   (LEAGUE_RESULTS, "Game-wide patterns"). In periods 1-2 the code reads the period number (gsp) only for the
   records; what changes in period 2 is the direction of play (gmode bit gmdir, each player's pfgoal: PeriodOver,
   setupice), and each net has one team attacking it in every period. So each real state is played again with only
   the period number changed: p1top v p1top_as_p2 (gsp 0 -> 1), p2bottom v p2bottom_as_p1 (gsp 1 -> 0). If play never
   reads it, the pairs come out the same shot for shot. (A first try turned the teams round by hand, as PeriodOver
   does, to put period 2 at the top net: the moved goalie stayed in his ready stance rather than his set one, and
   the shooter kept his old facing, so those states weren't like the real ones; dropped.)
2. The catching hand (SNES_SHOOTING 5.3): Montreal's goalie with his mirrored bit (attribute $0800, set by setplayer
   for a right-hander) flipped, as a goalie who catches with the other hand: p1top_hand, p2bottom_hand. The 4.8 lane
   (past his right-side saves, the shooter's left) should move to the shooter's right.

The shooter's working Shot Power and Shot Accuracy are 13 / 13, as in the map. Each condition: shooter spots
x -60..60 (steps of 10), y 80..200 from centre ice (steps of 20), a wrist shot and a full slapshot at each of
the nine aims; `phases` moments x `seeds` release seeds (default 8 x 2), the draws the same in every condition for a spot (paired; each shot's result is kept in order, "r": 1 goal, 0 not, - invalid, x no
shot, so the conditions can be compared shot by shot). Validity as snes_map_run. Gentle mode (lowload.py);
resumable (saved after every spot)."""
import json
import random
import sys
import zlib
from multiprocessing import Pool

from paths import RUNS, SNES_STATE_TOP, SNES_STATE_BOTTOM
import snes_harness as H
from lowload import WORKERS, breathe, gentle

XS = range(-60, 61, 10)
YS = range(80, 201, 20)
SHOTS = {"wrist": 3, "slap": 40}
MIN_PUCK = 24
GSP, ATTR = 0x1630, 0x0E03
SHP = SHA = 13                                 # the map's shooter (snes_map_run)
# condition: (state, top net?, period number to set (None: as saved), flip the goalie's hand?)
CONDS = {"p1top": (SNES_STATE_TOP, True, None, False), "p1top_as_p2": (SNES_STATE_TOP, True, 1, False),
         "p2bottom": (SNES_STATE_BOTTOM, False, None, False), "p2bottom_as_p1": (SNES_STATE_BOTTOM, False, 0, False),
         "p1top_hand": (SNES_STATE_TOP, True, None, True), "p2bottom_hand": (SNES_STATE_BOTTOM, False, None, True)}

_h = {}


def make(cond, emu=None):
    state, top, gsp, hand = CONDS[cond]
    h = H.Harness(state=state, top=top, emu=emu)
    e = h.e
    e.unserialize(h.base)
    g = H.o(H.GOALIE)
    if gsp is not None:
        e.setw(GSP, gsp)
    e.setw(H.SHOTSPD + H.o(H.SHOOTER), SHP)
    e.setw(H.SHOTACC + H.o(H.SHOOTER), SHA)
    if hand:
        e.setw(ATTR + g, e.w(ATTR + g) ^ 0x0800)
    h.base = e.serialize()
    return h


def _init(conds):
    gentle()
    e = None
    for c in conds:
        _h[c] = make(c, e)
        e = _h[c].e


def job(args):
    cond, x, y, phases, seeds = args
    h = _h[cond]
    sg = 1 if h.top else -1
    rnd = random.Random(zlib.crc32(f"{x},{y}".encode()))   # the same draws in every condition (paired)
    out = {}
    for p in range(phases):
        h.setup(x, sg * y, settle=80 + (p * 7) % 15, clock=590 - p % 8, seed=rnd.getrandbits(32))
        settled = h.e.serialize()
        for kind, hold in SHOTS.items():
            for aim in range(9):
                fire_seeds = [rnd.getrandbits(32) for _ in range(seeds)]
                c = out.setdefault(f"{kind},{aim}", dict(n=0, g=0, valid=0, noshot=0, r=""))
                h.e.unserialize(settled)
                pre, _f = h.shoot(aim, hold)
                if pre is None:
                    c["noshot"] += 1
                    c["r"] += "x" * seeds
                    continue
                e = h.e
                e.unserialize(pre)
                g, s = H.o(H.GOALIE), H.o(H.SHOOTER)
                gx, gy = h.sw(H.XPOS + g), h.sw(H.YPOS + g)
                px, py = h.sw(H.XPOS + H.o(H.PUCK)), h.sw(H.YPOS + H.o(H.PUCK))
                sx, sy = h.sw(H.XPOS + s), h.sw(H.YPOS + s)
                dp = ((px - gx) ** 2 + (py - gy) ** 2) ** 0.5
                ds = ((sx - gx) ** 2 + (sy - gy) ** 2) ** 0.5
                if not (dp >= MIN_PUCK and ds >= 16 and sg * py < sg * gy):
                    c["r"] += "-" * seeds
                    continue
                c["valid"] += 1
                for fs in fire_seeds:
                    h.fire(pre, aim, fs)
                    r, _f = h.decide()
                    c["n"] += 1
                    c["g"] += r
                    c["r"] += str(r)
                    breathe()
    return f"{cond},{x},{y}", out


def main():
    run = sys.argv[1]
    phases, seeds = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (8, 2)
    conds = sys.argv[4].split(",") if len(sys.argv) > 4 else list(CONDS)
    limit = int(sys.argv[5]) if len(sys.argv) > 5 else None          # at most this many spots this time (a chunk)
    path = RUNS / run / "snes_period_hand.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    res = json.load(open(path)) if path.exists() else {"meta": dict(phases=phases, seeds=seeds)}
    jobs = [(c, x, y, phases, seeds) for y in YS for x in XS for c in conds]
    jobs = [j for j in jobs if f"{j[0]},{j[1]},{j[2]}" not in res][:limit]
    with Pool(min(WORKERS, max(1, len(jobs))), initializer=_init, initargs=(conds,)) as pool:
        for i, (k, v) in enumerate(pool.imap_unordered(job, jobs)):
            res[k] = v
            json.dump(res, open(path, "w"))
            print(i + 1, "of", len(jobs), k, flush=True)
    print("done")


if __name__ == "__main__":
    main()
