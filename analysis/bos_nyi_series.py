"""BOS-NYI series, measured the same way for both teams (2026-10-21, the user: go deeper, without inventing).
A defending in your own zone (the other team carrying the puck there): where your controlled skater is, whether a person
has your goalie, how many of your skaters are goal-side; B cross-ice passes in the attacking zone and what follows;
C shot locations; D own-zone giveaways and what follows; E goaltending against expected goals.
python analysis/bos_nyi_series.py"""
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
from export_match import own_end  # noqa: E402

K = 12
SERIES = [("P", "2026-10-21_1137_NYI-BOS"), ("P", "2026-10-21_1147_NYI-BOS"), ("P", "2026-10-21_1156_BOS-NYI")]
CONTRAST = [("D", "2026-10-21_1054_BOS-NYI"), ("D", "2026-10-21_1121_BOS-NYI")]
BASE = {"D": Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches")), "P": Path("matches")}


def pos(m, f, k):
    return m["pos"][(f * K + k) * 2], m["pos"][(f * K + k) * 2 + 1]


def on_ice(m, f, k):
    return m["role"][f * K + k] in "12345"


def measure(m, team):
    """The numbers for `team` in match m."""
    t, N, opp = m["t"], len(m["t"]), 1 - team
    mine = range(team * 6, team * 6 + 6)
    theirs = range(opp * 6, opp * 6 + 6)
    r = {"dz_s": 0.0, "behind_s": 0.0, "goalie_person_s": 0.0, "ctrl_dist": 0.0, "goal_side": 0.0}
    for f in range(N - 1):
        dt = min(100, t[f + 1] - t[f]) / 1000
        o = m["owner"][f]
        if o not in theirs or m["puck"][3 * f + 2] < -100:
            continue
        end = own_end(m, f, team)
        if end is None:
            continue
        net_y = 268 * end
        px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
        if abs(py - net_y) > 180:            # not in my defensive zone
            continue
        r["dz_s"] += dt
        c = m["ctrl"][f]
        ck = next((k for k in mine if c >> k & 1), None)
        if ck is not None and m["role"][f * K + ck] == "0":
            r["goalie_person_s"] += dt
        elif ck is not None:
            x, y = pos(m, f, ck)
            r["ctrl_dist"] += dt * math.hypot(x - px, y - py)
            if abs(y - net_y) > abs(py - net_y):
                r["behind_s"] += dt
        r["goal_side"] += dt * sum(1 for k in mine if on_ice(m, f, k) and abs(pos(m, f, k)[1] - net_y) < abs(py - net_y))
    skater_s = max(1e-9, r["dz_s"] - r["goalie_person_s"])
    out = {"defending in own zone (s)": round(r["dz_s"]),
           "· person has the goalie": f"{100 * r['goalie_person_s'] / max(1e-9, r['dz_s']):.0f}%",
           "· person's skater behind the puck": f"{100 * r['behind_s'] / skater_s:.0f}%",
           "· person's skater to the puck (avg)": f"{r['ctrl_dist'] / skater_s:.0f}",
           "· skaters goal-side of the puck (avg)": f"{r['goal_side'] / max(1e-9, r['dz_s']):.1f}"}
    # B cross-ice passes in the attacking zone
    cross = [p for p in m.get("passes", []) if p["team"] == team and p.get("zone") == "att" and p["x0"] * p["x1"] < 0 and abs(p["x1"] - p["x0"]) >= 60]
    shots = [s for s in m.get("shotList", []) if s["team"] == team]
    after = [p for p in cross if any(0 <= t[s["f"]] - t[p["f"]] <= 2000 for s in shots)]
    goals_after = [p for p in cross if any(0 <= t[s["f"]] - t[p["f"]] <= 2000 and s["result"] == "goal" for s in shots)]
    out["cross-ice passes in the attacking zone"] = len(cross)
    out["· with an attempt within 2 s / a goal"] = f"{len(after)} / {len(goals_after)}"
    # C shot locations
    def dist(s):
        e = own_end(m, s["f"], opp)
        return math.hypot(s["x"], 268 * (e or 1) - s["y"])
    out["attempts: slot (within 60) / 60-120 / 120+"] = "/".join(str(sum(1 for s in shots if lo <= dist(s) < hi)) for lo, hi in ((0, 60), (60, 120), (120, 999)))
    out["goals: slot / 60-120 / 120+"] = "/".join(str(sum(1 for s in shots if lo <= dist(s) < hi and s["result"] == "goal")) for lo, hi in ((0, 60), (60, 120), (120, 999)))
    # D own-zone giveaways
    own_zone = []
    for g in m.get("turnovers", []):
        if g["from"] != team:
            continue
        e = own_end(m, g["f"], team)
        if e is not None and abs(g["y"] - 268 * e) < 180:
            own_zone.append(g)
    opp_shots = [s for s in m.get("shotList", []) if s["team"] == opp]
    led = [g for g in own_zone if any(0 <= t[s["f"]] - t[g["f"]] <= 5000 for s in opp_shots)]
    led_goal = [g for g in own_zone if any(0 <= t[s["f"]] - t[g["f"]] <= 8000 and s["result"] == "goal" for s in opp_shots)]
    out["own-zone turnovers -> shot against / goal against"] = f"{len(own_zone)} -> {len(led)} / {len(led_goal)}"
    # E goaltending (shots the other team took at us)
    xs = [s for s in opp_shots if s.get("xg") is not None and s["result"] != "blocked"]
    ga = sum(s["result"] == "goal" for s in xs)
    out["goals against vs expected (shots with xG)"] = f"{ga} vs {sum(s['xg'] for s in xs):.1f}"
    return out


def team_index(m, abbr):
    names = {"BOS": "Boston", "NYI": "New York"}
    return 0 if m["team1"] == names[abbr] else 1


for label, games in (("SERIES (NYI won all three)", SERIES), ("CONTRAST (the two Boston wins earlier that day)", CONTRAST)):
    print(f"\n==================== {label}")
    for w, n in games:
        m = json.loads(load_js_object(BASE[w] / f"{n}.js"))
        res = {ab: measure(m, team_index(m, ab)) for ab in ("BOS", "NYI")}
        print(f"\n--- {n}")
        keys = list(res["BOS"])
        wdt = max(len(k) for k in keys)
        print(f"{'':{wdt}}  {'BOS':>12} {'NYI':>12}")
        for k in keys:
            print(f"{k:{wdt}}  {str(res['BOS'][k]):>12} {str(res['NYI'][k]):>12}")
