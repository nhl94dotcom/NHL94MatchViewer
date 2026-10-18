"""Passing on the Genesis: catches, bobbles and interceptions against the game's stick rule (checkpuckcoll / puckstick):
a skater's stick plays a puck that is low (height 5 or under, not rising fast) within 14 units of his blade
(analysis/stick_spot.py: HotList, x negated when mirrored, y negated); slower than 13000 + 350 x his Stick Handling
(13000 flat while the "shot taken" flag stands) he takes it, faster it bounces off at random. The puck is followed
between samples (the path from one sample to the next, against the blade moving the same way), since it moves several
units a frame. python analysis/passing_study.py"""
import glob
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, "analysis")
from share_game import load_js_object  # noqa: E402
from stick_spot import hot, K  # noqa: E402

REACH = 14


def closest(a0, a1, b0, b1):
    """Closest approach of two points moving in straight lines over the same moment (a from a0 to a1, b from b0 to b1):
    (distance, share of the way)."""
    rx, ry = a0[0] - b0[0], a0[1] - b0[1]
    vx, vy = (a1[0] - a0[0]) - (b1[0] - b0[0]), (a1[1] - a0[1]) - (b1[1] - b0[1])
    vv = vx * vx + vy * vy
    s = 0 if vv == 0 else max(0.0, min(1.0, -(rx * vx + ry * vy) / vv))
    return math.hypot(rx + s * vx, ry + s * vy), s


def blade(m, q, k):
    fr = int(m["frame"][(q * K + k) * 3:(q * K + k) * 3 + 3], 16)
    x, y = m["pos"][(q * K + k) * 2], m["pos"][(q * K + k) * 2 + 1]
    if fr <= 0:
        return x, y
    hx, hy = hot(fr)
    if m["mirror"][q * K + k] == "1":
        hx = -hx
    return x + hx, y - hy


def stick_rating(m, team, k, q):
    c = m["roster"][q * K + k]
    if c == "x" or int(c, 36) >= len(m["rosters"][team]):
        return None
    p = m["rosters"][team][int(c, 36)]
    hc = p.get("hc") if isinstance(p.get("hc"), int) else 0
    return max(0, min(30, 5 * p["a"][8] + hc))  # Stick Handling nibble x 5 + hot / cold (Genesis, one value)


def flight(m, e, until_ms=2500):
    """Samples of a pass's flight: from the release until someone has the puck, or until_ms."""
    t, own = m["t"], m["owner"]
    q = e["f"] + 1
    out = []
    while q < len(t) and t[q] - t[e["f"]] < until_ms:
        out.append(q)
        if own[q] >= 0:
            break
        q += 1
    return out


def main():
    files = {}
    for p in glob.glob("matches/*.js") + glob.glob(str(Path.home() / "Documents/NHL94 Viewer/matches/*.js")):
        if not p.endswith(".summary.json") and Path(p).name not in ("season.js", "shot_study.json"):
            files.setdefault(Path(p).name, p)
    tally = defaultdict(Counter)
    lists = defaultdict(list)
    for name, p in sorted(files.items()):
        try:
            m = json.loads(load_js_object(Path(p)))
        except Exception:
            continue
        if m.get("system", "genesis") != "genesis" or m.get("rom") != "9438f5dd" or "passes" not in m:
            continue
        P, V, own, t = m["puck"], m["puckV"], m["owner"], m["t"]
        for e in m["passes"]:
            if e.get("result") == "pass shot":
                continue
            team = e["team"]
            others = range(6, 12) if team == 0 else range(6)
            mates = [k for k in (range(6) if team == 0 else range(6, 12))]
            fl = flight(m, e)
            if len(fl) < 2:
                continue
            length = math.hypot(e["x1"] - e["x0"], e["y1"] - e["y0"])
            band = "short (<60)" if length < 60 else "medium (60-120)" if length < 120 else "long (120+)"
            tally[band]["passes"] += 1
            tally[band][e["result"]] += 1
            # the first stick it passes (either team's, not the passer's), low or high, along the flight
            passer_k = next((k for k in mates if m["roster"][e["f"] * K + k] != "x" and int(m["roster"][e["f"] * K + k], 36) == e["idx"]), None)
            first = None
            highest_near = 0
            for a, b in zip(fl, fl[1:]):
                if own[a] >= 0:
                    break
                for k in range(12):
                    if k == passer_k or m["role"][a * K + k] in "0x":
                        continue
                    d, s = closest((P[3 * a], P[3 * a + 1]), (P[3 * b], P[3 * b + 1]), blade(m, a, k), blade(m, b, k))
                    if d <= REACH:
                        z = P[3 * a + 2] + s * (P[3 * b + 2] - P[3 * a + 2])
                        if k in others:
                            highest_near = max(highest_near, z)
                        if z <= 5 and first is None:
                            first = (a, k, d, z)
                if first:
                    break
            if first is None:
                tally[band]["no stick reached it low"] += 1
                if any(k in others for k in range(12)) and highest_near > 5:
                    tally[band]["went over an opponent's stick"] += 1
                continue
            a, k, d, z = first
            speed = math.hypot(V[2 * a] * 100, V[2 * a + 1] * 100)
            stk = stick_rating(m, 0 if k < 6 else 1, k, a)
            limit = 13000 + 350 * (stk or 0)
            side = "opponent" if k in others else "teammate"
            got = next((own[q] for q in range(a, min(len(t), a + 6)) if own[q] >= 0), -1)
            outcome = "took it" if got == k else "bounced off"
            key = f"first low stick: {side}, {'under' if speed < limit else 'over'} his catch limit"
            tally["rule"][key + f" -> {outcome}"] += 1
            if side == "opponent":
                lists["interception distance from passer"].append(math.hypot(P[3 * a] - e["x0"], P[3 * a + 1] - e["y0"]))
        for b in m.get("bobbles", []):
            pass
    for band in ("short (<60)", "medium (60-120)", "long (120+)"):
        c = tally[band]
        print(f"{band:16}: {c['passes']} passes; completed {c['completed']}, one-timer {c['one-timer']}, intercepted {c['intercepted']}, "
              f"failed {c['failed']}; no stick reached it low {c['no stick reached it low']} (over an opponent's stick {c[chr(119) + 'ent over an opponent' + chr(39) + 's stick']})")
    print("\nThe first stick a pass met while low (the game's rule says: under the limit he takes it, over it bounces off):")
    for k, v in sorted(tally["rule"].items()):
        print(f"  {k}: {v}")
    d = sorted(lists["interception distance from passer"])
    if d:
        print(f"\ninterceptions: distance from the passer, median {d[len(d) // 2]:.0f}; quartiles {d[len(d) // 4]:.0f} / {d[3 * len(d) // 4]:.0f}")


if __name__ == "__main__":
    main()
