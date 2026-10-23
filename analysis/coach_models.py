"""League tables for judging decisions with the puck (coach_report.py, 2026-10-23), from every Genesis match file in
both game folders:
- threat: for a team with the puck in its attacking half, the chance it scores within THREAT_S seconds, by where the
  puck is (BIN units across x out from the goal line it attacks), sampled four times a second. "Possession here is
  worth this much."
- after a pass: for a completed pass received in the attacking half, the chance the team scores within THREAT_S s, by
  where it was received (PBIN units; a completed pass, unlike plain possession, often finds a man the goalie hasn't
  squared up to: the one-timer study, SCORING_MAP).
- pass completion: the share of passes completed (or one-timed) by the pass's length and the gap from the pass's line
  to the nearest opposing skater or goalie at the release.
python analysis/coach_models.py   (rebuilds reports/coach_models.json; coach_report.py builds it when missing)"""
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
from export_match import own_end  # noqa: E402

K, BIN, PBIN, THREAT_S = 12, 20, 40, 5.0
LENGTHS, GAPS = (60, 120), (10, 20, 35)
CACHE = Path("reports") / "coach_models.json"
DIRS = [Path("matches"), Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches"))]


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy or 1
    u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + u * dx), py - (ay + u * dy)), u


def cell(x, out):
    return f"{max(-6, min(5, math.floor(x / BIN)))},{max(0, min(13, int(out // BIN)))}"


def recv_cell(x, out):
    return f"{max(-3, min(2, math.floor(x / PBIN)))},{max(0, min(6, int(out // PBIN)))}"


def pass_cell(length, gap):
    return f"{sum(length >= v for v in LENGTHS)},{sum(gap >= v for v in GAPS)}"


def lane_gap(m, f, team, x0, y0, x1, y1):
    """The nearest opposing player (skater or goalie) to the pass's line at frame f."""
    best = 999.0
    for k in range((1 - team) * 6, (1 - team) * 6 + 6):
        if m["role"][f * K + k] == "x":
            continue
        d, _ = seg_dist(m["pos"][(f * K + k) * 2], m["pos"][(f * K + k) * 2 + 1], x0, y0, x1, y1)
        best = min(best, d)
    return best


def matches():
    seen = set()
    for d in DIRS:
        for p in sorted(d.glob("*.js")):
            if p.name == "season.js" or p.stem in seen:
                continue
            seen.add(p.stem)
            yield p


def build():
    threat = defaultdict(lambda: [0, 0])
    passes = defaultdict(lambda: [0, 0])
    after = defaultdict(lambda: [0, 0])
    games = 0
    for p in matches():
        m = json.loads(load_js_object(p))
        if m.get("system", "genesis") != "genesis":
            continue
        games += 1
        t, N, P, own = m["t"], len(m["t"]), m["puck"], m["owner"]
        goals = [[t[f] for f in range(1, N) if m["score"][2 * f + tm] > m["score"][2 * (f - 1) + tm]] for tm in (0, 1)]
        last = -10 ** 9
        for f in range(N):
            o = own[f]
            if o < 0 or t[f] - last < 250 or P[3 * f + 2] < -100:
                continue
            last = t[f]
            team = 0 if o < 6 else 1
            e = own_end(m, f, 1 - team)                 # the net it attacks
            if e is None:
                continue
            ny = 268 * e
            out = abs(ny - P[3 * f + 1])
            if out > 268:
                continue
            c = threat[cell(P[3 * f] if e > 0 else -P[3 * f], out)]   # x as seen attacking up the screen
            c[0] += 1
            c[1] += any(0 < g - t[f] <= THREAT_S * 1000 for g in goals[team])
        for ps in m.get("passes", []):
            if ps.get("result") in ("pass shot", None) or ps["team"] not in (0, 1):
                continue
            gap = lane_gap(m, ps["f"], ps["team"], ps["x0"], ps["y0"], ps["x1"], ps["y1"])
            c = passes[pass_cell(math.hypot(ps["x1"] - ps["x0"], ps["y1"] - ps["y0"]), gap)]
            c[0] += 1
            c[1] += ps["result"] in ("completed", "one-timer")
            e = own_end(m, ps["f"], 1 - ps["team"])
            if ps["result"] in ("completed", "one-timer") and e is not None and abs(268 * e - ps["y1"]) <= 268:
                a = after[recv_cell(ps["x1"] if e > 0 else -ps["x1"], abs(268 * e - ps["y1"]))]
                a[0] += 1
                a[1] += any(0 < g - t[ps["f"]] <= THREAT_S * 1000 for g in goals[ps["team"]])
    out = {"games": games, "bin": BIN, "threat_s": THREAT_S, "lengths": LENGTHS, "gaps": GAPS,
           "threat": {k: v for k, v in threat.items()}, "passes": {k: v for k, v in passes.items()},
           "after": {k: v for k, v in after.items()}}
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(out), encoding="utf-8")
    return out


class Models:
    def __init__(self):
        d = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else build()
        self.d, self.raw = d, d["threat"]

    def threat_at(self, x, out, attacking_up):
        """The chance of a goal within THREAT_S s for the team with the puck here (x as seen on screen); a cell with
        the 3 x 3 block around it, or 5 x 5 when that has fewer than 80 samples."""
        xx = x if attacking_up else -x
        i, j = (int(v) for v in cell(xx, out).split(","))
        n = g = 0
        for r in (1, 2):
            for di in range(-r, r + 1):
                for dj in range(-r, r + 1):
                    c = self.raw.get(f"{i + di},{j + dj}")
                    if c:
                        n, g = n + c[0], g + c[1]
            if n >= 80:
                break
        return g / n if n else 0.0

    def after_pass(self, x, out, attacking_up):
        """The chance of a goal within THREAT_S s after a completed pass received here; a cell with fewer than 30
        passes borrows from the 3 x 3 block around it."""
        i, j = (int(v) for v in recv_cell(x if attacking_up else -x, out).split(","))
        c = self.d["after"].get(f"{i},{j}", [0, 0])
        n, g = c
        if n < 30:
            n = g = 0
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    cc = self.d["after"].get(f"{i + di},{j + dj}")
                    if cc:
                        n, g = n + cc[0], g + cc[1]
        return g / n if n else self.threat_at(x, out, attacking_up)

    def completion(self, length, gap):
        c = self.d["passes"].get(pass_cell(length, gap))
        return c[1] / c[0] if c and c[0] >= 10 else 0.6


if __name__ == "__main__":
    d = build()
    print(d["games"], "games;", sum(v[0] for v in d["threat"].values()), "threat samples;",
          sum(v[0] for v in d["passes"].values()), "passes")
    for k in sorted(d["passes"]):
        n, ok = d["passes"][k]
        print("pass length/gap cell", k, n, f"{ok / n:.2f}")
    for k in sorted(d["after"], key=lambda k: (int(k.split(",")[1]), int(k.split(",")[0]))):
        n, g = d["after"][k]
        print("after a pass received at (x bin, out bin)", k, n, f"{g / n:.2f}")
