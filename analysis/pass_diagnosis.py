"""Why passes fail: people's, the bot's and the computer's, measured at the release (2026-11-11, chunk 3: the bot's
passes complete 43-53% against the expert coaches' 65%). For each pass (the converter's `passes`) by a person's skater
(`human`: people's games and the bot's) or by the computer (computer games), at the sample of the pass and the puck's
first moving samples after it:
- the result (completed, intercepted, one-timer, failed, pass shot);
- the length the puck went (x0, y0 to x1, y1) and its speed;
- the aim: the puck's direction against the direction to each teammate: the angle off to the nearest-in-angle
  teammate (the game picks the receiver from the d-pad's 8 directions, so the bot doesn't choose him outright);
- that teammate's distance and how open he is (the nearest opponent to him), and the lane: the nearest opponent
  skater to the line from the passer to him (in front of the passer, short of the receiver), and how far along;
- pressure on the passer (the nearest opponent to him).
Per group: medians for completed and for intercepted passes, and the interception rate by lane gap and by aim angle.

python analysis/pass_diagnosis.py BOT_MATCHES [BOT_MATCHES ...] --cvc CVC_MATCHES"""
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

PEOPLE = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents" / "NHL94 Viewer")) / "matches"


def load(f):
    t = f.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def measures(m, p):
    N = len(m["t"])
    i = p["f"]
    if not 0 <= i < N - 6:
        return None
    P, V = m["pos"], m["puckV"]
    xy = lambda q, k: (P[(q * 12 + k) * 2], P[(q * 12 + k) * 2 + 1])
    team = p["team"]
    passer = m["owner"][i] if m["owner"][i] is not None and m["owner"][i] >= 0 else None
    if passer is None:
        passer = next((m["owner"][q] for q in range(i - 1, max(0, i - 6), -1) if m["owner"][q] is not None and m["owner"][q] >= 0), None)
    if passer is None or (passer < 6) != (team == 0):
        return None
    v = next(((V[2 * q], V[2 * q + 1]) for q in range(i, min(N, i + 6)) if math.hypot(V[2 * q], V[2 * q + 1]) > 20), None)
    if v is None:
        return None
    px, py = xy(i, passer)
    roles = m.get("role", "")
    on = lambda k: not (isinstance(roles, str) and len(roles) >= N * 12 and roles[i * 12 + k] in ("x", "g"))
    mates = [k for k in (range(6) if team == 0 else range(6, 12)) if k != passer and on(k)]
    opps = [k for k in (range(6, 12) if team == 0 else range(6)) if on(k)]
    if not mates or not opps:
        return None
    va = math.atan2(v[1], v[0])

    def ang(k):
        x, y = xy(i, k)
        d = abs((math.atan2(y - py, x - px) - va + math.pi) % (2 * math.pi) - math.pi)
        return math.degrees(d)
    r = min(mates, key=ang)
    rx, ry = xy(i, r)
    L = math.hypot(rx - px, ry - py) or 1
    lane, along = 999, None
    for o in opps:
        ox, oy = xy(i, o)
        a = ((ox - px) * (rx - px) + (oy - py) * (ry - py)) / L
        if 0 < a < L:
            d = abs((ox - px) * (ry - py) - (oy - py) * (rx - px)) / L
            if d < lane:
                lane, along = d, a / L
    return {"result": p["result"], "length": math.hypot(p["x1"] - p["x0"], p["y1"] - p["y0"]),
            "speed": math.hypot(*v), "aim_off": ang(r), "to_dist": L,
            "open": min(math.hypot(xy(i, o)[0] - rx, xy(i, o)[1] - ry) for o in opps),
            "lane": lane, "along": along,
            "pressure": min(math.hypot(xy(i, o)[0] - px, xy(i, o)[1] - py) for o in opps)}


def report(name, rows):
    rows = [r for r in rows if r]
    if not rows:
        return
    n = len(rows)
    comp = [r for r in rows if r["result"] in ("completed", "one-timer", "pass shot")]
    inter = [r for r in rows if r["result"] == "intercepted"]
    print(f"\n### {name}: {n} passes; completed (with one-timers, pass shots) {100 * len(comp) / n:.0f}%, intercepted "
          f"{100 * len(inter) / n:.0f}%, failed {100 * sum(r['result'] == 'failed' for r in rows) / n:.0f}%")
    print("| Median | completed | intercepted |")
    print("|---|---|---|")
    for k, lab in (("length", "puck travel"), ("speed", "puck speed"), ("aim_off", "aim off the nearest teammate (deg)"),
                   ("to_dist", "to that teammate"), ("open", "his nearest opponent"), ("lane", "lane gap (nearest opponent to the line)"),
                   ("pressure", "pressure on the passer")):
        a = [r[k] for r in comp if r[k] is not None and r[k] < 999]
        b = [r[k] for r in inter if r[k] is not None and r[k] < 999]
        print(f"| {lab} | {st.median(a):.0f} | {st.median(b):.0f} |" if a and b else f"| {lab} | - | - |")
    for k, edges, lab in (("lane", (8, 16, 30, 60), "lane gap"), ("aim_off", (5, 12, 25, 45), "aim off"),
                          ("open", (15, 30, 50, 80), "receiver's nearest opponent")):
        cells = []
        lo = -1
        for hi in list(edges) + [1e9]:
            band = [r for r in rows if r[k] is not None and lo < r[k] <= hi]
            if band:
                cells.append(f"{'<=' + str(hi) if hi < 1e9 else '>' + str(lo)}: {100 * sum(r['result'] == 'intercepted' for r in band) / len(band):.0f}% of {len(band)}")
            lo = hi
        print(f"Intercepted by {lab}: " + "; ".join(cells))


def main():
    args = sys.argv[1:]
    cvc = None
    if "--cvc" in args:
        cvc = Path(args[args.index("--cvc") + 1])
        args = args[:args.index("--cvc")]
    groups = defaultdict(list)
    for f in sorted(PEOPLE.glob("*.summary.json")):
        d = json.loads(f.read_text())
        if d.get("system") != "genesis" or (d.get("seconds") or 0) < 600 or not all(d.get("humans") or [False]):
            continue
        js = f.with_name(f.name.replace(".summary.json", ".js"))
        if js.exists():
            m = load(js)
            groups["people: the person's skater"] += [measures(m, p) for p in m.get("passes", []) if p.get("human")]
    for folder in args:
        for f in sorted(Path(folder).glob("bot_genesis_*.js")):
            m = load(f)
            groups["the bot's skater"] += [measures(m, p) for p in m.get("passes", []) if p.get("human") and p["team"] == 0]
    if cvc:
        for f in sorted(cvc.glob("cvc_genesis_*.js")):
            m = load(f)
            groups["computer games"] += [measures(m, p) for p in m.get("passes", [])]
    for name, rows in groups.items():
        report(name, rows)


if __name__ == "__main__":
    main()
