"""What makes a Genesis one-timer go in, from the recorded games (2026-11-27, the user: the Genesis half of the deke
guide; chance quality, above all one-timers, decides Genesis games between people, docs/WHAT_WINS.md).

Every one-timer a person took in the recorded Genesis games (not blocked; bot games left out), with its pass (the
converter's `passes` entry with result "one-timer" and `to` the shooter) and the state at the release from the match
file: the shooter's spot (out from the goal line, across), the pass (its length, how far across the ice it moved,
whether it crossed the middle, the time it took (real), the passer's spot: behind the goal line, low, the point), the
goalie (off the line from the puck to his net, out from his line, how far he had to slide across from the passer's
side to the shooter's, how fast he was sliding at the release), the shot's speed and aim, who was in net. For each the
goal rate by band against the shots' expected goals; then winners' one-timers against losers' in the decided games
between two people.

python analysis/gen_one_timer_study.py [--list]"""
import ast
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import xg  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
GOAL_LINE = 264


def load(p):
    t = p.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def val(v):
    if isinstance(v, str) and v[:1] in "[{TF0123456789-":
        try:
            return ast.literal_eval(v)
        except (ValueError, SyntaxError):
            return v
    return v


def features(m, s, passes):
    t, pos, role = m["t"], m["pos"], m["role"]
    f, team = s["f"], s["team"]
    p = next((e for e in reversed(passes) if e["team"] == team and e.get("to") == s["idx"] and e["f"] <= f
              and e.get("result") == "one-timer" and f - e["f"] < 120), None)
    gl = GOAL_LINE if xg.attacks_top(m, f, team) else -GOAL_LINE    # the goal line attacked
    xy = lambda q, r: (pos[(q * 12 + r) * 2], pos[(q * 12 + r) * 2 + 1])  # noqa: E731
    gk = next((r for r in range((1 - team) * 6, (1 - team) * 6 + 6) if role[f * 12 + r] == "0"), None)
    gout = gslide = gneed = None
    if gk is not None:
        gx, gy = xy(f, gk)
        a = max(0, f - 6)
        dt = max(1, (t[f] - t[a]) / (1000 / 60))
        gout = abs(gl) - abs(gy)
        gslide = abs(gx - xy(a, gk)[0]) / dt
        if p is not None:
            pf = max(0, min(len(t) - 1, p["f"]))
            gneed = abs(s["x"] - xy(pf, gk)[0])          # how far across he had to go since the pass left
    # One-timers whose pass the converter didn't match (4 of 220 on 2026-11-27) keep their shot and goalie figures,
    # with the pass's as None ("?" in the tables)
    pout = None if p is None else (gl - p["y0"]) * (1 if gl > 0 else -1)   # out from the attacked goal line; < 0 behind it
    return dict(out=abs(gl - s["y"]), across=abs(s["x"]),
                plen=None if p is None else math.hypot(p["x1"] - p["x0"], p["y1"] - p["y0"]),
                pacross=None if p is None else abs(p["x1"] - p["x0"]),
                pcross=None if p is None else (p["x0"] > 0) != (p["x1"] > 0) and abs(p["x0"]) > 8 and abs(p["x1"]) > 8,
                ptime=None if p is None else t[min(f, len(t) - 1)] - t[max(0, min(len(t) - 1, p["f"]))], pout=pout,
                pfrom=None if p is None else "behind the net" if pout < 0 else "low (under 80)" if pout < 80 else "high (80+)",
                goff=s.get("gOff"), gout=gout, gslide=gslide, gneed=gneed, speed=s.get("speed"),
                aim=(s.get("aim") or {}).get("d"), gctl=s.get("gctl"), net="top" if gl > 0 else "bottom",
                xg=s.get("xg") or 0.0, goal=s["result"] == "goal", result=s["result"], game=m["name"], t=t[f], team=team)


BANDS = {
    "out from the goal line": ("out", (0, 40, 70, 100, 140, 400)),
    "across from the middle": ("across", (0, 15, 30, 50, 200)),
    "pass length": ("plen", (0, 60, 100, 150, 600)),
    "pass across the ice": ("pacross", (0, 30, 60, 100, 300)),
    "pass time (ms real)": ("ptime", (0, 300, 500, 800, 5000)),
    "goalie off the shot line": ("goff", (0, 3, 6, 10, 99)),
    "goalie out from his line": ("gout", (-99, 6, 12, 20, 99)),
    "goalie's slide needed (from the pass)": ("gneed", (0, 20, 40, 70, 400)),
    "goalie sliding at the release (a frame)": ("gslide", (0, 0.5, 1.5, 3, 99)),
    "shot speed": ("speed", (0, 14000, 17000, 20000, 99999)),
}


def band(v, cuts):
    if v is None:
        return "?"
    if v < cuts[0]:
        return f"<{cuts[0]}"
    for lo, hi in zip(cuts, cuts[1:]):
        if lo <= v < hi:
            return f"{lo}-{hi}"
    return f"{cuts[-1]}+"


def collect():
    s = (HOME / "matches" / "season.js").read_text(encoding="utf-8")
    games = {g["name"]: g for g in json.loads(s[s.index("{"):s.rindex("}") + 1])["games"]}
    D = []
    for p in sorted((HOME / "matches").glob("20*.js")):
        g = games.get(p.stem)
        if not g or g["system"] != "genesis" or g.get("bot"):
            continue
        m = load(p)
        hum = val(g.get("humans"))
        sc = val(g.get("score"))
        both = (isinstance(hum, list) and all(hum) and val(g.get("finished")) is True
                and val(g.get("fromStart")) is True)              # as finishing_by_move / recorded_what_wins
        win = (0 if sc[0] > sc[1] else 1) if both and sc[0] != sc[1] else None
        passes = m.get("passes", [])
        for x in m["shotList"]:
            if x["kind"] == "one-timer" and x.get("human") and x.get("result") != "blocked":
                d = features(m, x, passes)
                if d:
                    d["side"] = None if win is None else ("winner" if x["team"] == win else "loser")
                    D.append(d)
    return D


def table(D, name, key, cuts):
    agg = defaultdict(lambda: [0, 0, 0.0])
    for d in D:
        b = band(d[key], cuts) if cuts else str(d[key])
        a = agg[b]
        a[0] += 1
        a[1] += d["goal"]
        a[2] += d["xg"]
    print(f"\n{name}:")
    order = (lambda kv: (kv[0] == "?", float(kv[0].split("-")[0].rstrip("+")) if kv[0][:1].isdigit() else 0, kv[0])) if cuts else (lambda kv: kv[0])
    for b, (n, gg, xx) in sorted(agg.items(), key=order):
        print(f"   {b:16s} one-timers {n:4d}  scored {gg:4d} ({100 * gg / n:3.0f}% ± {100 * math.sqrt((gg / n) * (1 - gg / n) / n):2.0f})  xG {100 * xx / n:3.0f}%")


def main():
    D = collect()
    g = sum(d["goal"] for d in D)
    print(f"Genesis one-timers by people: {len(D)} in {len({d['game'] for d in D})} games; {g} goals ({100 * g / len(D):.0f}%), xG {sum(d['xg'] for d in D):.1f}")
    for name, (key, cuts) in BANDS.items():
        table(D, name, key, cuts)
    for name, key in (("pass crossed the middle", "pcross"), ("pass from", "pfrom"), ("goalie", "gctl"), ("aim", "aim"), ("net", "net")):
        table(D, name, key, None)
    for side in ("winner", "loser"):
        A = [d for d in D if d["side"] == side]
        if not A:
            continue
        n = len(A)
        f = lambda k, test: 100 * sum(1 for d in A if d[k] is not None and test(d[k])) / n  # noqa: E731
        print(f"\n{side}s (decided games between people): {n} one-timers, scored {100 * sum(d['goal'] for d in A) / n:.0f}%, xG "
              f"{100 * sum(d['xg'] for d in A) / n:.0f}% | pass crossed the middle {f('pcross', bool):.0f}% | goalie 10+ off the "
              f"line {f('goff', lambda v: v >= 10):.0f}% | his slide needed 40+ {f('gneed', lambda v: v >= 40):.0f}% | shot from "
              f"under 70 out {f('out', lambda v: v < 70):.0f}% | pass from behind the net {f('pfrom', lambda v: v == 'behind the net'):.0f}%")
    if "--list" in sys.argv:
        for d in sorted(D, key=lambda d: (not d["goal"], -d["xg"])):
            print(json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items()}))


if __name__ == "__main__":
    main()
