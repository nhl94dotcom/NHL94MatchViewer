"""Defence studies from the recorded games (2026-10-25, docs/DEFENCE_PLAN.md studies 1 and 3). Every Genesis game in
the game folder (Documents/NHL94 Viewer/matches, else matches/).
- Study 1, where chances against come from: every shot attempt, traced back to how the attacking team got the puck
  (the start of the possession: a faceoff, a takeaway or giveaway by the defending team and where, the defending
  team's own shot held or cleared, a dump-in or loose puck) and how it got to the shot (the shot's kind, rush or
  sustained pressure, a rebound). Count, xG and goals of each, and the seconds from the start of the possession.
  Late throws (a period's last 5 game-clock seconds, xG under 0.10) are left out, as in coach_report.py.
- Study 2, which defensive habits go with conceding less: per person per game (games with a person on each side), the
  coach report's defensive measures (coach_report.measure) and the habits good players name (the user, 2026-10-25):
  accurate checks (landed, and missed ones as the last man back); anticipation (the other side's passes across the
  slot per minute they held the puck in our end, and how often the person's skater was within LANE of that pass's
  line); staying in the slot (the share of that time his skater was in the slot: within SLOT_X of the middle,
  SLOT_Y0-SLOT_Y1 out from the goal line), with how often they still shot from close in (within CLOSE). Each against
  the xG and goals his team conceded in the game, over the person-games: a correlation,
  so with few games only big effects show, and the opponent's strength is in it too.
- Study 3, what a lost puck costs: every turnover (dump-ins left out), by the zone the puck was lost in (for the team
  that lost it) and how; how often the other team shot within 5 s, the xG of those shots and the goals.
python analysis/defence_games.py [match name ...]   -> reports/defence_games.md"""
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "scoring_map"))
from export_match import own_end, zone_of, ZONE_LINE  # noqa: E402
from share_game import load_js_object  # noqa: E402
import coach_report as CR  # noqa: E402
from coach_models import Models  # noqa: E402
from lowload import gentle  # noqa: E402

DIRS = [Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches")), Path("matches")]
K, END_S, DECENT, AFTER_MS = 12, 5, 0.10, 5000
SLOT_X, SLOT_Y0, SLOT_Y1, LANE, CLOSE, GOAL_Y = 40, 10, 110, 20, 60, 264
ZONES = {"def": "own end", "neu": "neutral zone", "att": "their end"}
WHERE = {"def": "in the defending team's own end", "neu": "in the neutral zone",
         "att": "at the other end (a counter-attack)"}         # where the defending team lost it


def games(names):
    d = next(d for d in DIRS if d.exists() and any(d.glob("*.js")))
    paths = [d / f"{n}.js" for n in names] if names else sorted(p for p in d.glob("*.js") if "season" not in p.name)
    for p in paths:
        m = json.loads(load_js_object(p))
        if m.get("system", "genesis") == "genesis":
            m["name"] = p.stem
            yield m


def team_of(k):
    return -1 if k < 0 else (0 if k < 6 else 1)


def late(m, sh):
    return m["clock"][sh["f"]] <= END_S and (sh.get("xg") or 0) < DECENT


def whistle(m, a, b):
    """A whistle (the puck off the ice, as export_match marks a stoppage) between frames a and b."""
    P = m["puck"]
    return any(P[3 * q + 2] < -100 for q in range(a, b + 1))


def possession_start(m, sh):
    """How the shooting team got the puck before this shot: (label, frame it began)."""
    att, f = sh["team"], sh["f"]
    own = m["owner"]
    q = f
    while q > 0 and team_of(own[q]) != 1 - att and m["period"][q] == m["period"][f]:
        q -= 1
    # q: the last frame the defending team had it (or the period's start)
    fo = next((e for e in reversed(m.get("faceoffs", [])) if q <= e["f"] <= f), None)
    if fo:
        fwd = 1 if own_end(m, fo["f"], att) == -1 else -1
        return "faceoff, " + ZONES[zone_of(fo["y"], fwd)].replace("own end", "defending").replace(
            "their end", "attacking").replace("neutral zone", "neutral") + " zone", fo["f"]
    if team_of(own[q]) != 1 - att:
        return "period start / other", q
    k = own[q]
    D = 1 - att
    lost = q + 1
    if any(s["team"] == D and abs(s["f"] - lost) <= 3 for s in m.get("shotList", [])):
        return "after the defending team's own shot", lost
    if m["role"][q * K + k] == "0":
        return "the defending goalie's clearance", lost
    tv = next((e for e in m.get("turnovers", []) if e["from"] == D and abs(e["lost"] - lost) <= 3), None)
    fwd = 1 if own_end(m, lost, D) == -1 else -1      # the defending team's attacking direction
    zone = WHERE[zone_of(m["puck"][3 * lost + 1], fwd)]
    if tv is None:
        return f"loose puck {zone}", lost
    if tv["kind"] == "dump-in":
        return "the defending team's dump-in", lost
    how = "takeaway" if tv["kind"] == "takeaway" else "giveaway"
    return f"{how} {zone}", lost


def shot_shape(sh):
    if sh.get("rebound"):
        return "rebound"
    kind = sh["kind"]
    if kind == "one-timer":
        return "one-timer"
    if kind == "shot":
        return ("slapshot" if "slap" in sh.get("type", "") else "wrist shot") + f" ({sh.get('origin', '?')})"
    return kind


def study1(ms):
    by = defaultdict(lambda: [0, 0.0, 0, 0.0])        # n, xg, goals, seconds
    shape = defaultdict(lambda: [0, 0.0, 0, 0.0])
    cross = defaultdict(lambda: [0, 0.0, 0, 0.0])
    total = [0, 0.0, 0]
    for m in ms:
        t = m["t"]
        for sh in m.get("shotList", []):
            if late(m, sh):
                continue
            label, f0 = possession_start(m, sh)
            g = sh.get("result") == "goal"
            x = sh.get("xg") or 0
            secs = (t[sh["f"]] - t[f0]) / 1000                # real seconds (t: the recording clock, ms)
            for tab, key in ((by, label), (shape, shot_shape(sh)), (cross, (label, shot_shape(sh)))):
                r = tab[key]
                r[0] += 1; r[1] += x; r[2] += g; r[3] += secs
            total[0] += 1; total[1] += x; total[2] += g
    return by, shape, cross, total


def study3(ms):
    out = defaultdict(lambda: [0, 0, 0.0, 0])         # turnovers, with a shot within 5 s, xG of those shots, goals
    for m in ms:
        t = m["t"]
        for e in m.get("turnovers", []):
            if e["kind"] == "dump-in":
                continue
            L = e["from"]
            fwd = 1 if own_end(m, e["lost"], L) == -1 else -1
            zone = ZONES[zone_of(e["y"], fwd)]
            how = e.get("how", e["kind"])
            shots = [s for s in m.get("shotList", []) if s["team"] == 1 - L and 0 <= t[s["f"]] - t[e["f"]] <= AFTER_MS
                     and not whistle(m, e["f"], s["f"])]
            for key in ((zone, "all"), (zone, e["kind"]), (zone, how)):
                r = out[key]
                r[0] += 1
                r[1] += bool(shots)
                r[2] += sum(s.get("xg") or 0 for s in shots)
                r[3] += any(s.get("result") == "goal" for s in shots)
    return out


def habits(m, team):
    """The user's three habits for one team's person in one game, and what the team conceded."""
    t, N, opp = m["t"], len(m["t"]), 1 - team
    c = dict(defend_s=0.0, slot_s=0.0, across=0, across_lane=0, across_ok=0, close=0, xga=0.0, ga=0, att=0)
    for f in range(1, N):
        if team_of(m["owner"][f]) != opp:
            continue
        e = own_end(m, f, team)
        k = CR.ctrl_skater(m, f, team)
        dt = (t[f] - t[f - 1]) / 1000
        if e is None or k is None or m["puck"][3 * f + 1] * e < ZONE_LINE or dt > 0.2:
            continue
        c["defend_s"] += dt
        x, y = CR.P(m, f, k)
        c["slot_s"] += dt * (abs(x) <= SLOT_X and SLOT_Y0 <= GOAL_Y - y * e <= SLOT_Y1)
    for p in m.get("passes", []):
        if p["team"] != opp:
            continue
        e = own_end(m, p["f"], team)
        k = CR.ctrl_skater(m, p["f"], team)
        if e is None or k is None:
            continue
        if not (p["x0"] * p["x1"] < 0 and min(abs(p["x0"]), abs(p["x1"])) >= 15 and GOAL_Y - p["y1"] * e <= 130):
            continue                                     # not across the slot in our end
        c["across"] += 1
        c["across_ok"] += p["result"] == "completed"
        x, y = CR.P(m, p["f"], k)
        c["across_lane"] += CR.seg_dist(x, y, p["x0"], p["y0"], p["x1"], p["y1"]) <= LANE
    for sh in m.get("shotList", []):
        if sh["team"] != opp or late(m, sh):
            continue
        c["att"] += 1
        c["xga"] += sh.get("xg") or 0
        c["ga"] += sh.get("result") == "goal"
        c["close"] += math.hypot(sh["x"], GOAL_Y - abs(sh["y"])) <= CLOSE
    return c


def ratio(a, b):
    return a / b if b else None


HABITS = [  # (label, value from the coach report's Counter and habits())
    ("checks landed (share of check attempts)", lambda k, h: ratio(k["b_check_landed"], k["b_check"])),
    ("missed check attempts as the last man back (per game)", lambda k, h: k["b_lastman_miss"]),
    ("check attempts (per game)", lambda k, h: k["b_check"]),
    ("their passes across the slot (per game)", lambda k, h: h["across"]),
    ("his skater in the lane of their pass across (share)", lambda k, h: ratio(h["across_lane"], h["across"])),
    ("their passes across completed (share)", lambda k, h: ratio(h["across_ok"], h["across"])),
    ("his skater in the slot (share of time defending in our end)", lambda k, h: ratio(h["slot_s"], h["defend_s"])),
    ("their shots from within 20 ft (share of their attempts)", lambda k, h: ratio(h["close"], h["att"])),
    ("his skater in position (share of time defending)",
     lambda k, h: ratio(k["pos_n_in"], k["pos_n_in"] + k["pos_n_off"] + k["pos_n_up"])),
    ("his skater caught up ice (share of time defending)",
     lambda k, h: ratio(k["pos_n_up"], k["pos_n_in"] + k["pos_n_off"] + k["pos_n_up"])),
    ("switches that took him out of position (share)", lambda k, h: ratio(k["sw_bad"], k["sw"])),
    ("back in position within 2 s of a turnover", lambda k, h: ratio(k["tr_back_quick"], k["tr_back_n"])),
    ("steal pokes that won the puck", lambda k, h: ratio(k["k_steal_won"], k["k_steal"])),
    ("wasted pokes (per game)", lambda k, h: k["k_wasted"]),
    ("recovery bursts that got him goal-side", lambda k, h: ratio(k["b_recover_ok"], k["b_recover"])),
]


def study2(ms):
    M = Models()
    rows = []
    for m in ms:
        if "abbr" not in m:
            continue
        people = [any(m["ctrl"][f] >> k & 1 for f in range(0, len(m["t"]), 30) for k in range(tm * 6, tm * 6 + 6))
                  for tm in (0, 1)]
        if not all(people):
            continue
        for tm in (0, 1):
            h = habits(m, tm)
            if h["defend_s"] >= 30:
                rows.append((m["name"], m["abbr"][tm], CR.measure(m, tm, M), h))
        print(m["name"], flush=True)
    res = []
    for label, fn in HABITS:
        v, xr, gr = [], [], []
        for _, _, k, h in rows:
            a = fn(k, h)
            if a is None:
                continue
            v.append(a)
            xr.append(h["xga"])
            gr.append(h["ga"])
        if len(v) >= 6 and statistics.pstdev(v) > 0:
            res.append((label, statistics.mean(v), statistics.correlation(v, xr), statistics.correlation(v, gr), len(v)))
    return rows, res


def table(rows, head):
    lines = ["| " + " | ".join(head) + " |", "|" + " --- |" * len(head)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def main():
    gentle()
    ms = list(games(sys.argv[1:]))
    by, shape, cross, total = study1(ms)
    tv = study3(ms)
    hrows, hres = study2(ms)
    n, xg, gl = total
    rep = [f"# Defence from the recorded games ({len(ms)} Genesis games)", "",
           "`analysis/defence_games.py`; docs/DEFENCE_PLAN.md studies 1-3.", "",
           f"## 1. Where shot attempts come from ({n} attempts, xG {xg:.1f}, {gl} goals)", "",
           "By how the attacking team got the puck:", ""]
    rows = sorted(by.items(), key=lambda kv: -kv[1][1])
    rep.append(table([(k, v[0], f"{v[1]:.1f}", v[2], f"{v[1] / xg:.0%}", f"{v[2] / max(gl, 1):.0%}",
                       f"{v[1] / v[0]:.3f}", f"{v[3] / v[0]:.1f}") for k, v in rows],
                     ["Start of the possession", "Attempts", "xG", "Goals", "Share of xG", "Share of goals",
                      "xG per attempt", "Seconds to the shot"]))
    rep += ["", "By the shot:", ""]
    rows = sorted(shape.items(), key=lambda kv: -kv[1][1])
    rep.append(table([(k, v[0], f"{v[1]:.1f}", v[2], f"{v[1] / xg:.0%}", f"{v[2] / max(gl, 1):.0%}",
                       f"{v[1] / v[0]:.3f}") for k, v in rows],
                     ["Shot", "Attempts", "xG", "Goals", "Share of xG", "Share of goals", "xG per attempt"]))
    rep += ["", "Goals by start and shot:", ""]
    rows = sorted(((k, v) for k, v in cross.items() if v[2]), key=lambda kv: -kv[1][2])
    rep.append(table([(k[0], k[1], v[0], v[2], f"{v[1]:.1f}") for k, v in rows],
                     ["Start", "Shot", "Attempts", "Goals", "xG"]))
    sd = sum(h["defend_s"] for *_, h in hrows) / 60
    rep += ["", f"## 2. Defensive habits against what was conceded ({len(hrows)} person-games)", "",
            f"Per person per game, against the xG and goals his team conceded in that game (on average "
            f"{sum(h['xga'] for *_, h in hrows) / len(hrows):.1f} xG and {sum(h['ga'] for *_, h in hrows) / len(hrows):.1f} "
            f"goals; the other side held the puck in his end {sd * 60 / len(hrows):.0f} s a game). Negative: more of "
            f"the habit, less conceded. "
            f"With {len(hrows)} person-games a correlation under about {2 / math.sqrt(max(len(hrows), 1)):.2f} could "
            f"easily be chance, and the opponent's strength is in every number.", ""]
    rep.append(table([(lab, f"{mu:.2f}", f"{cx:+.2f}", f"{cg:+.2f}", n) for lab, mu, cx, cg, n in
                      sorted(hres, key=lambda r: r[2])],
                     ["Habit", "Average", "with xG against", "with goals against", "Person-games"]))
    rep += ["", "## 3. What a lost puck costs (shots by the other team within 5 s, no whistle between)", ""]
    rows = sorted(tv.items(), key=lambda kv: (list(ZONES.values()).index(kv[0][0]), kv[0][1] != "all", -kv[1][0]))
    rep.append(table([(k[0], k[1], v[0], f"{v[1] / v[0]:.0%}", f"{v[2] / v[0]:.3f}", v[3]) for k, v in rows],
                     ["Zone lost in (the losing team's view)", "How", "Turnovers", "Shot within 5 s",
                      "xG against per turnover", "Goals"]))
    Path("reports").mkdir(exist_ok=True)
    Path("reports/defence_games.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
