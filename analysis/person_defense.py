"""The person's controlled skater on defence, and decisions, measured the same way for both teams (2026-10-21, the
user: did NYI's coach defend better with his controlled skater: positioning, cutting off passes; and what can be said
about decision making). While the other team has the puck in your zone:
- shots against: was your skater in the shooting lane (between shooter and net, within 12 of the line) at the release,
  how far from the shooter; the attempts' distance and xG;
- passes against in your zone: was your skater near the passing lane (within 15 of the segment) at the release; who
  picked passes off (your person or the computer); passes completed into your slot;
- time: your skater in your slot (within 70 of your net, 45 across), pressing the carrier (within 25 of the puck);
- carries into your slot by the other team.
Decisions: pokes out of reach (over 30 from the puck: they do nothing), passes picked off in your own zone, shots at a
set goalie (within 5 of the puck's line) from 120+, the expected goals of your person's shots.
python analysis/person_defense.py"""
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
from export_match import own_end  # noqa: E402

K = 12
GAMES = [("P", "2026-10-21_1137_NYI-BOS", "series"), ("P", "2026-10-21_1147_NYI-BOS", "series"),
         ("P", "2026-10-21_1156_BOS-NYI", "series"), ("D", "2026-10-21_1054_BOS-NYI", "contrast"),
         ("D", "2026-10-21_1121_BOS-NYI", "contrast")]
BASE = {"D": Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches")), "P": Path("matches")}


def pos(m, f, k):
    return m["pos"][(f * K + k) * 2], m["pos"][(f * K + k) * 2 + 1]


def roster(m, f, k):
    c = m["roster"][f * K + k]
    return int(c, 36) if c not in "x-" else -1


def ctrl_skater(m, f, team):
    c = m["ctrl"][f]
    for k in range(team * 6, team * 6 + 6):
        if c >> k & 1 and m["role"][f * K + k] in "12345":
            return k
    return None


def seg_dist(px, py, ax, ay, bx, by):
    """Distance from (px, py) to the segment a-b, and where along it (0-1)."""
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy or 1
    u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + u * dx), py - (ay + u * dy)), u


def goalie_xy(m, f, team):
    for k in range(team * 6, team * 6 + 6):
        if m["role"][f * K + k] == "0":
            return pos(m, f, k)
    return None


def measure(m, team):
    t, N, opp = m["t"], len(m["t"]), 1 - team
    mine, theirs = range(team * 6, team * 6 + 6), range(opp * 6, opp * 6 + 6)
    c = Counter()
    # time in my zone with their puck
    for f in range(N - 1):
        dt = min(100, t[f + 1] - t[f]) / 1000
        if m["owner"][f] not in theirs or m["puck"][3 * f + 2] < -100:
            continue
        e = own_end(m, f, team)
        if e is None:
            continue
        ny = 268 * e
        px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
        if abs(py - ny) > 180:
            continue
        c["dz_s"] += dt
        k = ctrl_skater(m, f, team)
        if k is None:
            continue
        x, y = pos(m, f, k)
        c["slot_s"] += dt * (math.hypot(x, ny - y) < 70 and abs(x) < 45)
        c["press_s"] += dt * (math.hypot(x - px, y - py) < 25)
    # shots against
    for s in m.get("shotList", []):
        if s["team"] != opp:
            continue
        f = s["f"]
        e = own_end(m, f, team)
        if e is None:
            continue
        ny = 268 * e
        d = math.hypot(s["x"], ny - s["y"])
        c["sa"] += 1
        c["sa_dist"] += d
        c["sa_far"] += d >= 120
        c["sa_slot"] += d < 60
        c["sa_xg"] += s.get("xg") or 0
        k = ctrl_skater(m, f, team)
        if k is None:
            continue
        x, y = pos(m, f, k)
        lane, u = seg_dist(x, y, s["x"], s["y"], 0, ny)
        c["sa_lane"] += lane < 12 and 0.05 < u < 0.95
        c["sa_close"] += math.hypot(x - s["x"], y - s["y"]) < 25
    # passes against in my zone
    for p in m.get("passes", []):
        if p["team"] != opp or p.get("zone") != "att":
            continue
        f = p["f"]
        e = own_end(m, f, team)
        if e is None:
            continue
        ny = 268 * e
        c["pa"] += 1
        k = ctrl_skater(m, f, team)
        if k is not None:
            x, y = pos(m, f, k)
            dl, u = seg_dist(x, y, p["x0"], p["y0"], p["x1"], p["y1"])
            c["pa_lane"] += dl < 15 and 0.1 < u < 0.9
        if p["result"] in ("completed", "one-timer") and math.hypot(p["x1"], ny - p["y1"]) < 60:
            c["pa_slot_ok"] += 1
    for g in m.get("turnovers", []):
        if g["from"] == opp and g["how"].startswith("pass"):
            f = max(0, g.get("lost", g["f"]) - 1)    # control moves to whoever takes the puck: ask just before
            k = next((kk for kk in mine if roster(m, f, kk) == g["taker"]), None)
            if k is not None and m["ctrl"][f] >> k & 1:
                c["pick_person"] += 1
            else:
                c["pick_cpu"] += 1
    # carries into my slot by them
    f = 0
    while f < N:
        o = m["owner"][f]
        if o in theirs:
            s0 = f
            while f < N and m["owner"][f] == o:
                f += 1
            e = own_end(m, s0, team)
            if e is None:
                continue
            ny = 268 * e
            q = next((q for q in range(s0, f) if math.hypot(m["puck"][3 * q], ny - m["puck"][3 * q + 1]) < 60), None)
            if q is not None:
                c["carry_slot"] += 1
                k = ctrl_skater(m, q, team)
                if k is not None:
                    x, y = pos(m, q, k)
                    px, py = m["puck"][3 * q], m["puck"][3 * q + 1]
                    c["cs_dist"] += math.hypot(x - px, y - py)
                    c["cs_goalside"] += abs(y - ny) < abs(py - ny)
                    c["cs_inslot"] += math.hypot(x, ny - y) < 70 and abs(x) < 45
                    c["cs_n"] += 1
            continue
        f += 1
    # decisions: my pokes out of reach, my passes picked off in my zone, my shots at a set goalie from far, my shots' xG
    for f in range(1, N):
        k = ctrl_skater(m, f, team)
        if k is None:
            continue
        a = m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4]
        b = m["anim"][((f - 1) * K + k) * 4:((f - 1) * K + k) * 4 + 4]
        if a == "0b24" and b != "0b24":
            x, y = pos(m, f, k)
            c["pokes"] += 1
            c["poke_far"] += math.hypot(x - m["puck"][3 * f], y - m["puck"][3 * f + 1]) > 30
    for g in m.get("turnovers", []):
        if g["from"] == team and g["how"].startswith("pass"):
            e = own_end(m, g["f"], team)
            if e is not None and abs(g["y"] - 268 * e) < 180:
                c["own_zone_picked"] += 1
    for s in m.get("shotList", []):
        if s["team"] != team or not s.get("human") or s["kind"] not in ("shot", "one-timer"):
            continue
        e = own_end(m, s["f"], opp)
        ny = 268 * (e or 1)
        d = math.hypot(s["x"], ny - s["y"])
        g = goalie_xy(m, s["f"], opp)
        off = seg_dist(*g, s["x"], s["y"], 0, ny)[0] if g else 99
        c["my_shots"] += 1
        c["my_xg"] += s.get("xg") or 0
        c["my_far_set"] += d >= 120 and off < 5
    return c


def team_index(m, abbr):
    return 0 if m["team1"] == {"BOS": "Boston", "NYI": "New York"}[abbr] else 1


def report(c):
    p = lambda a, b: f"{100 * a / b:.0f}%" if b else "-"
    return {
        "their puck in my zone (s)": round(c["dz_s"]),
        "· my skater in my slot": p(c["slot_s"], c["dz_s"]),
        "· my skater pressing the carrier (within 25)": p(c["press_s"], c["dz_s"]),
        "shots against": c["sa"],
        "· avg distance / from 120+ / from the slot": f"{c['sa_dist'] / max(1, c['sa']):.0f} / {c['sa_far']} / {c['sa_slot']}",
        "· xG against (per shot)": f"{c['sa_xg']:.1f} ({c['sa_xg'] / max(1, c['sa']):.2f})",
        "· my skater in the shooting lane at the release": p(c["sa_lane"], c["sa"]),
        "· my skater within 25 of the shooter": p(c["sa_close"], c["sa"]),
        "passes against in my zone": c["pa"],
        "· my skater near the passing lane": p(c["pa_lane"], c["pa"]),
        "· completed into my slot": c["pa_slot_ok"],
        "· picked off by my person / my computer skaters": f"{c['pick_person']} / {c['pick_cpu']}",
        "their carries into my slot": c["carry_slot"],
        "· my skater then: distance / goal-side / in the slot": f"{c['cs_dist'] / max(1, c['cs_n']):.0f} / {p(c['cs_goalside'], c['cs_n'])} / {p(c['cs_inslot'], c['cs_n'])}",
        "my pokes out of reach (over 30)": f"{c['poke_far']} of {c['pokes']}",
        "my passes picked off in my own zone": c["own_zone_picked"],
        "my person's shots: xG each": f"{c['my_xg'] / max(1, c['my_shots']):.2f} ({c['my_shots']} shots)",
        "· from 120+ at a set goalie": c["my_far_set"],
    }


tot = {}
for w, n, grp in GAMES:
    m = json.loads(load_js_object(BASE[w] / f"{n}.js"))
    for ab in ("BOS", "NYI"):
        tot.setdefault((grp, ab), Counter()).update(measure(m, team_index(m, ab)))
        tot.setdefault((n, ab), Counter()).update(measure(m, team_index(m, ab)))
for grp in ("series", "contrast"):
    rb, rn = report(tot[(grp, "BOS")]), report(tot[(grp, "NYI")])
    print(f"\n==== {grp} totals")
    wdt = max(len(k) for k in rb)
    print(f"{'':{wdt}}  {'BOS':>16} {'NYI':>16}")
    for k in rb:
        print(f"{k:{wdt}}  {str(rb[k]):>16} {str(rn[k]):>16}")
print("\nper game: in the shooting lane / near the passing lane / in the slot / pressing, BOS vs NYI")
for w, n, grp in GAMES:
    rb, rn = report(tot[(n, "BOS")]), report(tot[(n, "NYI")])
    keys = ["· my skater in the shooting lane at the release", "· my skater near the passing lane", "· my skater in my slot", "· my skater pressing the carrier (within 25)"]
    print(f"  {n[11:]:14} BOS " + " / ".join(rb[k] for k in keys) + "   NYI " + " / ".join(rn[k] for k in keys))
