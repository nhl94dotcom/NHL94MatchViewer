"""What makes an SNES deke go in, from the recorded games (2026-11-26, the user: dekes decide SNES games between
people, docs/WHAT_WINS.md; make it something a player can practise).

Every deke (the converter's shot `move` == "deke": within 80 units of the goal line, not a slapshot, the facing swung
two or more steps of 8 in the last 0.6 s real) by a person in the recorded SNES games, with the state at the release
from the match file: where (out from the goal line, across), the shooter's speed and which way he was moving (in
toward the net, across, away), how far his facing swung and when the swing ended, the goalie (out from his line,
across against the puck, off the shot line, person or computer), the aim, the net (top / bottom). For each the
goal rate by band against the deke's expected goals, the groups furthest apart, and the dekes scored and missed
listed for picking replays.

python analysis/snes_deke_study.py [--list]"""
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
DIG = "0123456789abcdefghijklmnopqrstuvwxyz"


def load(p):
    t = p.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def features(m, s):
    t, pos, ros, fac, role = m["t"], m["pos"], m["roster"], m["facing"], m["role"]
    f, team = s["f"], s["team"]
    k = next((k for k in range(team * 6, team * 6 + 6) if ros[f * 12 + k] in DIG and DIG.index(ros[f * 12 + k]) == s["idx"]), None)
    if k is None:
        return None
    xy = lambda q, r: (pos[(q * 12 + r) * 2], pos[(q * 12 + r) * 2 + 1])  # noqa: E731
    gl = 264 if s["y"] > 0 else -264
    sg = 1 if gl > 0 else -1
    a = max(0, f - 6)
    dt = max(1, (t[f] - t[a]) / (1000 / 60))
    vx, vy = (xy(f, k)[0] - xy(a, k)[0]) / dt, (xy(f, k)[1] - xy(a, k)[1]) / dt
    sp = math.hypot(vx, vy)
    toward = vy * sg                                   # + skating at the goal line
    acrossmid = -vx * (1 if s["x"] > 0 else -1)        # + skating toward the middle
    back = [q for q in range(max(0, f - 60), f + 1) if t[f] - t[q] <= 600 and fac[q * 12 + k].isdigit()]
    fs = [int(fac[q * 12 + k]) for q in back]
    swing = max(min((x - y) % 8, (y - x) % 8) for x in fs for y in fs) if fs else 0
    last = next((t[f] - t[q] for q in reversed(back[:-1]) if fac[q * 12 + k] != fac[f * 12 + k]), 600)
    gk = next((r for r in range((1 - team) * 6, (1 - team) * 6 + 6) if role[f * 12 + r] == "0"), None)
    gout = gacross = None
    if gk is not None:
        gx, gy = xy(f, gk)
        gout = abs(gl) - abs(gy)
        gacross = (s["x"] - gx) * (1 if s["x"] >= 0 else -1)   # + the puck farther out to its side than the goalie
    ctrl = m.get("ctrl")
    gperson = bool(ctrl and gk is not None and ctrl[f] >> gk & 1)
    return dict(out=264 - abs(s["y"]), across=abs(s["x"]), speed=sp, toward=toward, tomid=acrossmid, swing=swing, last=last,
                gout=gout, gacross=gacross, goff=s.get("gOff"), gperson=gperson, gtake="gTake" in s,
                aim=(s.get("aim") or {}).get("d"), net="top" if gl > 0 else "bottom", xg=s.get("xg") or 0.0,
                goal=s["result"] == "goal", game=m["name"], t=t[f], f=f, period=m["period"][f], clock=m["clock"][f])


BANDS = {
    "out from the goal line": ("out", (0, 20, 35, 50, 65, 81)),
    "across from the middle": ("across", (0, 10, 20, 35, 200)),
    "speed (units a frame)": ("speed", (0, 1.0, 2.0, 3.0, 9)),
    "skating at the goal line (+) or away": ("toward", (-9, -0.5, 0.5, 1.5, 9)),
    "skating toward the middle (+) or out": ("tomid", (-9, -0.5, 0.5, 1.5, 9)),
    "facing swing (steps of 8)": ("swing", (2, 3, 4, 5)),
    "since the last turn (ms real)": ("last", (0, 50, 100, 200, 601)),
    "goalie out from his line": ("gout", (-99, 6, 12, 20, 99)),
    "puck past the goalie to its side (+)": ("gacross", (-99, -5, 5, 15, 99)),
    "goalie off the shot line": ("goff", (0, 3, 6, 10, 99)),
}


def band(v, cuts):
    if v is None:
        return "?"
    for lo, hi in zip(cuts, cuts[1:]):
        if lo <= v < hi:
            return f"{lo}-{hi}"
    return f"{cuts[-1]}+"


def main():
    D = []
    for p in sorted((HOME / "matches").glob("20*.js")):
        m = load(p)
        if m.get("system") != "snes" or m.get("bot"):
            continue
        for s in m.get("shotList", []):
            if s.get("move") == "deke" and s.get("human") and s.get("result") != "blocked":
                d = features(m, s)
                if d:
                    D.append(d)
    g = sum(d["goal"] for d in D)
    x = sum(d["xg"] for d in D)
    print(f"SNES dekes by people: {len(D)} in {len({d['game'] for d in D})} games; {g} goals ({100 * g / len(D):.0f}%), xG {x:.1f}")
    for name, (key, cuts) in list(BANDS.items()) + [("goalie in net", ("gperson", None)), ("goalie taken over mid-shot", ("gtake", None)),
                                                     ("aim", ("aim", None)), ("net", ("net", None))]:
        agg = defaultdict(lambda: [0, 0, 0.0])
        for d in D:
            b = band(d[key], cuts) if cuts else str(d[key])
            a = agg[b]
            a[0] += 1
            a[1] += d["goal"]
            a[2] += d["xg"]
        print(f"\n{name}:")
        for b, (n, gg, xx) in sorted(agg.items(), key=lambda kv: (len(kv[0]), kv[0])):
            se = math.sqrt(max(gg, 1) * (n - gg) / n) / n if n else 0
            print(f"   {b:12s} dekes {n:4d}  scored {gg:4d} ({100 * gg / n:3.0f}% ± {100 * math.sqrt((gg / n) * (1 - gg / n) / n):2.0f})  xG {100 * xx / n:3.0f}%")
    if "--list" in sys.argv:
        for d in sorted(D, key=lambda d: (not d["goal"], -d["xg"]))[:60]:
            print(json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items()}))


if __name__ == "__main__":
    main()
