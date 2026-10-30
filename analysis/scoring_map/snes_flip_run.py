"""The SNES flip (Y with the puck) played in the real game (retail ROM, snes_harness; 2026-10-30; SNES_MECHANICS 6.3).
The code (assdumpin, DumpInTarget) says where a flip is aimed: from outside the attacking zone, deep in it on the
carrier's side of centre (80 across, 180 up the ice from centre); from inside it, the front of the net (0, 215); with
a random spread of +/-(20-25 + 2 x (15 - Passing)) across and +/-(20-70 + the same) along. This plays it: the home
centre (object 2, pad 1) stands with the puck at a spot facing up the ice (the way the flip needs him: he first turns
to within 45 degrees of it) while the computer goalie sets himself, then taps Y; the puck is followed for 3 s.
Spots (attacker's view: across, + his right; y from centre toward the net he attacks): his own zone (+/-50, -150), the
neutral zone (+/-50, 0), the attacking zone (+/-40, 150); his working Passing 4, 10 or 15; both nets; MOMENTS moments
(the random seed, the clock, the settle frames). Kept per flip: the frames from Y to the release, where the puck first
came down after its peak (and when), its peak height, where it was 3 s on (or where someone took it, and who).
python snes_flip_run.py RUN   -> paths.RUNS / RUN / snes_flip.jsonl   (gentle: one process, resting as it works)"""
import itertools
import json
import os
import random
import sys
import zlib

import snes_harness as H
from lowload import breathe, gentle
from paths import RUNS, SNES_STATE_TOP, SNES_STATE_BOTTOM

MOMENTS = int(os.environ.get("NHL94_FLIP_MOMENTS") or 24)
SHOOTER = H.SHOOTER
FACING, PASSACC = 0x1163, 0x13A3
PUCKZ = 0x0DF9
SPOTS = [(-50, -150), (50, -150), (-50, 0), (50, 0), (-40, 150), (40, 150)]


def o(k):
    return 2 * k


def main():
    run = sys.argv[1]
    gentle()
    top = H.Harness(state=SNES_STATE_TOP, top=True)
    hs = {"top": top, "bottom": H.Harness(state=SNES_STATE_BOTTOM, top=False, emu=top.e)}
    e = top.e
    path = RUNS / run / "snes_flip.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as out:
        for net, (x, y), pa in itertools.product(("top", "bottom"), SPOTS, (4, 10, 15)):
            h = hs[net]
            sg = 1 if net == "top" else -1
            rnd = random.Random(zlib.crc32(json.dumps([net, x, y, pa]).encode()))
            for p in range(MOMENTS):
                h.setup(sg * x, sg * y, settle=80 + (p * 7) % 15, clock=590 - p % 8, seed=rnd.getrandbits(32))
                e.setw(PASSACC + o(SHOOTER), pa)
                e.setw(FACING + o(SHOOTER), 0 if sg > 0 else 4)
                rel = peak = land = taken = None
                zmax = 0
                for f in range(200):
                    h.park()
                    e.run(1, hold=["Y"] if f < 2 else [])
                    c = e.w(H.PUCKC)
                    px, py, pz = h.sw(H.XPOS + o(14)), h.sw(H.YPOS + o(14)), h.sw(PUCKZ)
                    if rel is None:
                        if c & 0x8000:
                            rel = f
                        elif f > 60:
                            break
                        continue
                    if pz > zmax:
                        zmax, peak = pz, f
                    if land is None and peak is not None and pz <= 0:
                        land = (f - rel, sg * px, sg * py)
                    if not c & 0x8000:
                        taken = (f - rel, c // 2, sg * px, sg * py)
                        break
                breathe()
                end = (sg * h.sw(H.XPOS + o(14)), sg * h.sw(H.YPOS + o(14)))
                out.write(json.dumps(dict(net=net, x=x, y=y, pa=pa, p=p, rel=rel, peak=zmax, land=land, taken=taken,
                                          end=end)) + "\n")
                out.flush()


if __name__ == "__main__":
    main()
