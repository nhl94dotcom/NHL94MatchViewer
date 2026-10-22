"""Which map spots are real shots: python validity.py RUN -> paths.RUNS / RUN / validity.json
The harness holds the shooter on his spot while the goalie sets himself, and within about 30 units of the net's centre
the goalie's set spot is the puck itself: he skates onto it, and the shooter ends up shooting from inside or behind
him, which no game allows. A spot counts when, at the release, the puck is at least 20 units from the goalie's centre
(beyond any reach, the pad stack's 18 included) and in front of him, and the shooter is beyond the 16 at which
players collide. Measured at one moment per spot (clock 590, 85 frames to settle)."""
import json
import sys

from harness import Harness, rec, SHOOTER, GOALIE
from mapper import set_ratings
from paths import RUNS, STATE_TOP, STATE_BOTTOM

XS = range(-110, 111, 10)
YS = range(100, 251, 10)


def main():
    top = Harness(state=STATE_TOP, top=True)
    hs = {"top": top, "bottom": Harness(state=STATE_BOTTOM, top=False, emu=top.e)}
    out = {}
    for net, h in hs.items():
        sg = 1 if net == "top" else -1
        h.e.unserialize(h.base)
        set_ratings(h, 20, 15)
        h.base = h.e.serialize()
        for hold in (3, 20):
            for y in YS:
                for x in XS:
                    h.setup(x, sg * y, settle=85, clock=590)
                    pre, f = h.shoot(8, hold)
                    if pre is None:
                        out[f"{net},{hold},{x},{y}"] = dict(ok=False, why="no shot")
                        continue
                    en = h.entry()
                    h.e.unserialize(pre)
                    g, s = rec(GOALIE), rec(SHOOTER)
                    gx, gy = h.e.sw(g), h.e.sw(g + 0x14)
                    sx, sy = h.e.sw(s), h.e.sw(s + 0x14)
                    dp = ((en["px"] - gx) ** 2 + (en["py"] - gy) ** 2) ** 0.5
                    ds = ((sx - gx) ** 2 + (sy - gy) ** 2) ** 0.5
                    front = sg * en["py"] < sg * gy
                    ok = dp >= 20 and ds >= 16 and front
                    out[f"{net},{hold},{x},{y}"] = dict(ok=ok, puck=[en["px"], en["py"]], goalie=[gx, gy],
                                                        puck_goalie=round(dp, 1), shooter_goalie=round(ds, 1),
                                                        front=front)
    (RUNS / sys.argv[1]).mkdir(parents=True, exist_ok=True)
    json.dump(out, open(RUNS / sys.argv[1] / "validity.json", "w"))
    print(sum(v["ok"] for v in out.values()), "of", len(out), "spots valid")


if __name__ == "__main__":
    main()
