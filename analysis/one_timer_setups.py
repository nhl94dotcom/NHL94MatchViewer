"""How people set up one-timers (2026-11-11, chunk 3: the bot's one-timer offer, open_mate, rarely finds the safe
receiver it wants: 1.4 tries a game against the expert coaches' 5.0; the user: "we humans are more willing to accept
suboptimal circumstances when deciding whether to attempt a one-timer"). Every pass in the recorded Genesis games
(people on both sides) that the converter calls a one-timer (`result` 'one-timer': the receiver swung at it), by a
person's skater, at the sample of the pass, in the attacking team's view (the net it attacks at +264):
- the passer's and the receiver's spots (across, out from the goal line), the pass's length and how far across;
- the receiver's nearest opponent (how covered), the lane gap (the nearest opponent skater to the line from the
  passer to the receiver, in between), the receiver's speed toward the net;
- how it ended: the one-timer shot that followed (goal, xG) or nothing.
Then the share of them the bot's open_mate (versions 41-47: the receiver 15-100 out, within 70 of the middle, the pass
39-110 across and under 130; no opponent within OPEN of him, none within LANE of the lane) would have allowed, for
OPEN / LANE as 20 / 15 (41-46) and 35 / 20 (47); and the goal rate by how covered the receiver was.

python analysis/one_timer_setups.py"""
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from export_match import own_end  # noqa: E402

PEOPLE = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents" / "NHL94 Viewer")) / "matches"
NET_Y = 264


def load(f):
    t = f.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def setups(m):
    N, P, ros = len(m["t"]), m["pos"], m["roster"]
    xy = lambda q, k: (P[(q * 12 + k) * 2], P[(q * 12 + k) * 2 + 1])
    shots = [s for s in m.get("shotList", []) if s.get("kind") == "one-timer"]
    out = []
    for p in m.get("passes", []):
        if p.get("result") != "one-timer" or not p.get("human"):
            continue
        i, team = p["f"], p["team"]
        if not 0 <= i < N:
            continue
        mine = range(6) if team == 0 else range(6, 12)
        theirs = range(6, 12) if team == 0 else range(6)
        rk = next((k for k in mine if int(ros[12 * i + k], 36) == p["to"]), None)
        pk = next((k for k in mine if int(ros[12 * i + k], 36) == p["idx"]), None)
        if rk is None or pk is None:
            continue
        end = next((e for q in range(i, min(N, i + 300)) for e in [own_end(m, q, team)] if e is not None), None)
        if end is None:
            continue
        s = -end                                   # +1: attacking +y
        (px, py), (rx, ry) = xy(i, pk), xy(i, rk)
        L = math.hypot(rx - px, ry - py) or 1
        roles = m.get("role", "")
        on = lambda k: not (isinstance(roles, str) and len(roles) >= N * 12 and roles[i * 12 + k] in ("x", "g"))
        opps = [o for o in theirs if on(o)]
        cover = min(math.hypot(xy(i, o)[0] - rx, xy(i, o)[1] - ry) for o in opps) if opps else 999
        lane = 999
        for o in opps:
            ox, oy = xy(i, o)
            a = ((ox - px) * (rx - px) + (oy - py) * (ry - py)) / L
            if 0 < a < L:
                lane = min(lane, abs((ox - px) * (ry - py) - (oy - py) * (rx - px)) / L)
        j = min(N - 1, i + 6)
        vy = (xy(j, rk)[1] - ry) * s
        shot = next((x for x in shots if x["team"] == team and i <= x["f"] <= i + 90), None)
        out.append({"pax": s * px, "pay": s * py, "rax": s * rx, "out": NET_Y - s * ry, "len": L,
                    "across": abs(rx - px), "cover": cover, "lane": lane, "rvy": vy,
                    "goal": bool(shot and shot.get("result") == "goal"), "xg": shot.get("xg") if shot else None})
    return out


def allowed(r, open_, lane_):
    return (15 < r["out"] < 100 and abs(r["rax"]) < 70 and 39 < r["across"] < 110 and r["len"] < 130
            and r["cover"] >= open_ and r["lane"] >= lane_)


def main():
    rows = []
    for f in sorted(PEOPLE.glob("*.summary.json")):
        d = json.loads(f.read_text())
        if d.get("system") != "genesis" or (d.get("seconds") or 0) < 600 or not all(d.get("humans") or [False]):
            continue
        js = f.with_name(f.name.replace(".summary.json", ".js"))
        if js.exists():
            rows += setups(load(js))
    n = len(rows)
    print(f"people's one-timer passes: {n}; goals {sum(r['goal'] for r in rows)} ({100 * sum(r['goal'] for r in rows) / n:.0f}%)")
    print("| Median (quartiles) | value |")
    print("|---|---|")
    q = lambda k: sorted(r[k] for r in rows if r[k] is not None and r[k] < 999)
    for k, lab in (("pay", "passer up the ice (264 = the goal line)"), ("pax", "passer across"), ("out", "receiver out from the goal line"),
                   ("rax", "receiver across"), ("len", "pass length"), ("across", "pass across"), ("cover", "receiver's nearest opponent"),
                   ("lane", "lane gap"), ("rvy", "receiver's speed toward the net (6 samples)")):
        v = q(k)
        print(f"| {lab} | {st.median(v):.0f} ({v[len(v) // 4]:.0f}-{v[3 * len(v) // 4]:.0f}) |")
    for o, l, lab in ((20, 15, "open_mate 41-46 (20 / 15)"), (35, 20, "open_mate 47 (35 / 20)"), (0, 0, "the zone limits only")):
        a = [r for r in rows if allowed(r, o, l)]
        print(f"{lab}: allows {len(a)} of {n} ({100 * len(a) / n:.0f}%); goals among them {100 * sum(r['goal'] for r in a) / max(1, len(a)):.0f}%, "
              f"among the rest {100 * sum(r['goal'] for r in rows if r not in a) / max(1, n - len(a)):.0f}%")
    print("By the receiver's nearest opponent: " + "; ".join(
        f"{lo}-{hi}: {sum(1 for r in rows if lo <= r['cover'] < hi)} passes, goals "
        f"{100 * sum(r['goal'] for r in rows if lo <= r['cover'] < hi) / max(1, sum(1 for r in rows if lo <= r['cover'] < hi)):.0f}%"
        for lo, hi in ((0, 15), (15, 25), (25, 35), (35, 50), (50, 999))))
    print("By the lane gap: " + "; ".join(
        f"{lo}-{hi}: {sum(1 for r in rows if lo <= r['lane'] < hi)}, goals "
        f"{100 * sum(r['goal'] for r in rows if lo <= r['lane'] < hi) / max(1, sum(1 for r in rows if lo <= r['lane'] < hi)):.0f}%"
        for lo, hi in ((0, 10), (10, 20), (20, 40), (40, 1000))))


if __name__ == "__main__":
    main()
