"""Why some Genesis saves are not counted as shots on goal (2026-10-18). ChkShotStat counts a shot only while sf2shot
(set at the release) still stands; any touch (a2touchpuck), the boards (wallcoll) and a stick deflection clear it. At
the goalie, puckstick comes before the body: a puck at height <= 5 within 8 of his stick blade (GetHot) is the stick's,
caught (and counted, puckglue -> ChkShotStat) when slower than 13000 ($32C8), else deflected at random (a2touchpuck:
not counted). So the test: did the puck reach his blade low before it reached his body, and how fast?
python analysis/uncounted_study.py"""
import math
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "analysis")
from goalie_study import games, goalie, pos, clock, K  # noqa: E402

HOTLIST = 0xA44C8
ROMS = {}


def rom(crc):
    if crc not in ROMS:
        for d in (Path("roms"), Path.home() / "Documents/NHL94 Viewer/roms"):
            hits = sorted(d.glob(f"{crc}*.bin"))
            if hits:
                ROMS[crc] = hits[0].read_bytes()
                break
        else:
            ROMS[crc] = None
    return ROMS[crc]


def blade(m, R, f, k):
    fr = int(m["frame"][(f * K + k) * 3:(f * K + k) * 3 + 3], 16)
    if fr <= 0:
        return None
    hx, hy = struct.unpack_from(">bb", R, HOTLIST + 2 * fr)
    if m["mirror"][f * K + k] == "1":
        hx = -hx
    x, y = pos(m, f, k)
    return x + hx, y - hy


def first_touch(m, R, s):
    """What the puck met first at the goalie: ('stick', speed) / ('body', speed) / None, scanning release to resolve
    (+ a few samples), interpolating between samples in 4 steps."""
    g = goalie(m, s["f"], 1 - s["team"])
    if g is None:
        return None
    P, V = m["puck"], m["puckV"]
    f1 = min(len(m["t"]) - 1, s.get("resolved", s["f"]) + 3)
    for f in range(s["f"], f1):
        b0, b1 = blade(m, R, f, g), blade(m, R, f + 1, g)
        for j in range(4):
            a = j / 4
            px = P[3 * f] + a * (P[3 * f + 3] - P[3 * f])
            py = P[3 * f + 1] + a * (P[3 * f + 4] - P[3 * f + 1])
            pz = P[3 * f + 2] + a * (P[3 * f + 5] - P[3 * f + 2])
            gx, gy = (1 - a) * pos(m, f, g)[0] + a * pos(m, f + 1, g)[0], (1 - a) * pos(m, f, g)[1] + a * pos(m, f + 1, g)[1]
            sp = math.hypot(V[2 * max(s["f"], f - 1)], V[2 * max(s["f"], f - 1) + 1]) * 100
            if pz <= 5 and b0 and b1:
                bx, by = (1 - a) * b0[0] + a * b1[0], (1 - a) * b0[1] + a * b1[1]
                if math.hypot(px - bx, py - by) <= 8:
                    return "stick", sp
            if pz <= 15 and math.hypot(px - gx, py - gy) <= 13:
                return "body", sp
    return "none", 0


def outcome(m, s, g):
    """How the save ended, from the recording: 'clock stopped' (the clock did not run in the 1.2 s after: ChkShotStat
    counts nothing then), 'behind / boards' (the puck crossed the goal line or reached the side boards first: wallcoll
    cleared the flag), 'held' (the goalie had it with no bounce between), 'radial' (it bounced out from his centre
    within 25 degrees: his body, puckgoalie), 'deflected' (it slowed and turned any other way: the random deflection
    of a stick, puckstick -> deflect), or 'unclear'."""
    T, P, V, C, own = m["t"], m["puck"], m["puckV"], m["clock"], m["owner"]
    f0, f1 = s["f"], s.get("resolved", s["f"])
    fe = f1
    while fe < len(T) - 1 and T[fe] - T[f1] < 1200:
        fe += 1
    if C[fe] == C[f1]:
        return "clock stopped"
    for f in range(f0, min(len(T) - 1, f1 + 3)):
        if abs(P[3 * f + 1]) > 268 or abs(P[3 * f]) >= 124:
            return "behind / boards"
    v0 = (V[2 * f0], V[2 * f0 + 1])
    for f in range(f0 + 1, min(len(T) - 1, f1 + 6)):
        if own[f] >= 0:
            return "held"
        vx, vy = V[2 * f], V[2 * f + 1]
        dot = (vx * v0[0] + vy * v0[1]) / (math.hypot(vx, vy) * math.hypot(*v0) + 1e-9)
        if dot < 0.9 or math.hypot(vx, vy) < 0.5 * math.hypot(*v0):
            gx, gy = pos(m, f, g)
            rx, ry = P[3 * f] - gx, P[3 * f + 1] - gy
            c = (rx * vx + ry * vy) / (math.hypot(rx, ry) * math.hypot(vx, vy) + 1e-9)
            return "radial" if c > math.cos(math.radians(25)) else "deflected"
    return "unclear"


def main():
    tab = Counter()
    for name, m in games("genesis"):
        if "puckV" not in m:
            continue
        for s in m["shotList"]:
            if s.get("result") != "save" or s.get("type") == "pass shot":
                continue
            g = goalie(m, s["f"], 1 - s["team"])
            if g is not None:
                tab[(outcome(m, s, g), bool(s.get("counted")))] += 1
    for what in ("clock stopped", "behind / boards", "held", "radial", "deflected", "unclear"):
        c, u = tab[(what, True)], tab[(what, False)]
        print(f"{what:16} counted {c:4}  not counted {u:3}")


if __name__ == "__main__":
    main()
