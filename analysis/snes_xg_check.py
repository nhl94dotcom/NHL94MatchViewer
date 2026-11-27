"""Where the SNES xG model is off in the recorded games (2026-11-26, the user: firm up the SNES half of WHAT_WINS).

Every recorded SNES game in the game folder (bot games left out; any build: retail, Classic, the 2 MB and SA-1 builds
the converter gives xG), each unblocked shot / one-timer / pass shot with an xG against what happened: goals against
xG overall and by group (the model's xG band, kind, distance, the angle, who was in net (gctl), a rebound, the shot's
origin, its aim, the goalie off the shot line, the build, and whether the people's games), each with the
difference's standard error (sum of p(1-p)); the groups furthest from their xG first.

python analysis/snes_xg_check.py [--people]   (--people: games with a person on both sides only)"""
import ast
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")


def val(v):
    if isinstance(v, str) and v[:1] in "[{TF0123456789-":
        try:
            return ast.literal_eval(v)
        except (ValueError, SyntaxError):
            return v
    return v


def season():
    s = (HOME / "matches" / "season.js").read_text(encoding="utf-8")
    d = json.loads(s[s.index("{"):s.rindex("}") + 1])
    return {g["name"]: g for g in d["games"]}


def shots(people_only):
    S = season()
    out = []
    for p in sorted((HOME / "matches").glob("20*.js")):
        g = S.get(p.stem)
        if g is None or g["system"] != "snes" or g.get("bot"):
            continue
        hum = val(g.get("humans"))
        both = isinstance(hum, list) and all(hum)
        if people_only and not both:
            continue
        s = p.read_text(encoding="utf-8")
        m = json.loads(s[s.index("{"):s.rindex("}") + 1])
        for x in m.get("shotList", []):
            if x.get("xg") is None or x.get("result") == "blocked" or x.get("kind") not in ("shot", "one-timer", "pass shot"):
                continue
            x = dict(x, game=p.stem, rom=m.get("rom"), people=both)
            out.append(x)
    return out


def dist(x):
    gl = 264 if x["y"] > 0 else -264
    return math.hypot(x["x"], gl - x["y"])


GROUPS = {
    "xG band": lambda x: next(b for b in ("0-5%", "5-15%", "15-30%", "30-50%", "50-70%", "70%+") if x["xg"] < {"0-5%": .05, "5-15%": .15, "15-30%": .30, "30-50%": .50, "50-70%": .70, "70%+": 9}[b]),
    "kind": lambda x: x["kind"],
    "distance": lambda x: next(b for b in ("under 30", "30-60", "60-100", "100-150", "150+") if dist(x) < {"under 30": 30, "30-60": 60, "60-100": 100, "100-150": 150, "150+": 1e9}[b]),
    "angle from the middle": lambda x: next(b for b in ("0-15°", "15-35°", "35-60°", "60°+") if math.degrees(math.atan2(abs(x["x"]), max(1, abs((264 if x["y"] > 0 else -264) - x["y"])))) < {"0-15°": 15, "15-35°": 35, "35-60°": 60, "60°+": 99}[b]),
    "goalie": lambda x: x.get("gctl") or "?",
    "rebound": lambda x: "rebound" if x.get("rebound") else "first shot",
    "origin": lambda x: x.get("origin") or "?",
    "danger": lambda x: x.get("danger") or "?",
    "goalie off the shot line": lambda x: "?" if x.get("gOff") is None else ("under 4" if x["gOff"] < 4 else "4-10" if x["gOff"] < 10 else "10+"),
    "aim (d)": lambda x: str((x.get("aim") or {}).get("d")),
    "ROM": lambda x: x["rom"],
    "game between people": lambda x: "yes" if x["people"] else "no",
    "shooter a person": lambda x: "person" if x.get("human") else "computer",
}


def main():
    people_only = "--people" in sys.argv
    S = shots(people_only)
    g = sum(x["result"] == "goal" for x in S)
    xg = sum(x["xg"] for x in S)
    var = sum(x["xg"] * (1 - x["xg"]) for x in S)
    print(f"SNES recorded shots{' (people on both sides)' if people_only else ''}: {len(S)} in {len({x['game'] for x in S})} games; goals {g}, xG {xg:.1f} "
          f"(goals - xG {g - xg:+.1f} ± {math.sqrt(var):.1f})")
    worst = []
    for name, f in GROUPS.items():
        agg = defaultdict(lambda: [0, 0.0, 0.0, 0])
        for x in S:
            try:
                k = f(x)
            except (KeyError, TypeError, StopIteration):
                k = "?"
            a = agg[k]
            a[0] += x["result"] == "goal"
            a[1] += x["xg"]
            a[2] += x["xg"] * (1 - x["xg"])
            a[3] += 1
        print(f"\n{name}:")
        for k, (gg, xx, vv, n) in sorted(agg.items(), key=lambda kv: str(kv[0])):
            z = (gg - xx) / math.sqrt(vv) if vv > 0 else 0
            print(f"   {str(k):22s} shots {n:4d}  goals {gg:4d}  xG {xx:6.1f}  goals - xG {gg - xx:+6.1f} (z {z:+.1f})  rate {100 * gg / max(1, n):4.1f}% / {100 * xx / max(1, n):4.1f}%")
            if n >= 15:
                worst.append((abs(z), name, k, gg, xx, n))
    print("\nthe groups furthest from their xG (15+ shots):")
    for z, name, k, gg, xx, n in sorted(worst, reverse=True)[:12]:
        print(f"   {name}: {k}: {gg} goals for {xx:.1f} xG on {n} shots (z {z:.1f})")


if __name__ == "__main__":
    main()
