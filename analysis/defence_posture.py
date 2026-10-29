"""Pressure or sit back? Defending your own end on each system (2026-10-29, the user: winning is mostly about the slot;
on the Genesis it pays to be more proactive in your own end, since slapshots and one-timers go in from farther out; on
the SNES most goals are scored from close in, so it pays to sit back more). Both systems, the recorded games with a
person on each side (dated games in both game folders).

A visit: a stretch with the puck in a team's own end after the other team had it (from the moment the other team has
it there, or brings it in, until the puck leaves the end, the defending team has it, goalie included, or a whistle).
While the attackers have the puck (a carrier), every frame, the defending person's skater (the one he controls; not
the goalie):
- pressure: his distance to the carrier (the visit's mean), and the share of the time he was within PRESS of him;
- the slot: the share of the time he was in the slot (within SLOT_X of the middle, SLOT_Y0-SLOT_Y1 out from the goal
  line: defence_games.py's slot).
What the visit cost: the attackers' shots in it (count, xG, goals), late throws left out as in defence_games.py.
Visits under MIN_S seconds of carrying are left out (nothing to defend). The visits are sorted into thirds by each
measure, per system, and the cost of each third compared; then, for the two together, pressing (the top third by
time within PRESS) against sitting in the slot (the top third by slot share, not pressing).
Cautions: the defender's posture answers the play (on a 2-on-1 he backs off, against a lone carrier he steps up), so
a difference can be the situation as much as the choice; and the attackers' skill is in it.
python analysis/defence_posture.py   -> prints the tables"""
import glob
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from export_match import own_end, whistles, ZONE_LINE  # noqa: E402
from match_report import DIRS  # noqa: E402
from share_game import load_js_object  # noqa: E402

PRESS = 30                     # units (about 10 ft): close enough to poke or check
SLOT_X, SLOT_Y0, SLOT_Y1, GOAL_Y = 40, 10, 110, 264
MIN_S, END_S, DECENT = 1.0, 5, 0.10


def games():
    seen = set()
    for d in DIRS:
        d = d if d.is_absolute() else ROOT / d
        for s in sorted(glob.glob(str(d / "*.summary.json"))):
            name = Path(s).name[:-len(".summary.json")]
            js = Path(s).with_name(name + ".js")
            if name in seen or not js.exists() or not re.match(r"\d{4}-\d\d-\d\d_", name):
                continue
            seen.add(name)
            S = json.load(open(s))
            if all(S.get("humans") or [False]):
                yield name, S, json.loads(load_js_object(js))


def team_of(k):
    return -1 if k < 0 else k // 6


def visits(m, name):
    """Every visit, for each defending team with a person: dict(system, game, team, you, secs, dist, press, slot,
    shots, xg, goals)."""
    t, P, N, own, ctrl = m["t"], m["puck"], len(m["t"]), m["owner"], m["ctrl"]
    stop = set()
    for a, b in whistles(m):
        stop.update(range(a, b + 1))
    shots = defaultdict(list)
    for sh in m.get("shotList", []):
        if sh.get("counted", True) and not (m["clock"][sh["f"]] <= END_S and (sh.get("xg") or 0) < DECENT):
            shots[sh["team"]].append(sh)
    out = []
    for team in (0, 1):
        opp, cur = 1 - team, None
        for f in range(1, N):
            e = own_end(m, f, team)
            in_end = e is not None and f not in stop and P[3 * f + 2] > -100 and P[3 * f + 1] * e >= ZONE_LINE
            k = own[f]
            if cur is not None and (not in_end or team_of(k) == team or m["period"][f] != m["period"][cur["f0"]]):
                cur["f1"] = f
                out.append(cur)
                cur = None
            if not in_end:
                continue
            if cur is None:
                if team_of(k) != opp:
                    continue
                cur = dict(team=team, f0=f, secs=0.0, dsum=0.0, press=0.0, slot=0.0)
            if team_of(k) != opp:
                continue                                   # loose: part of the visit, but no carrier to measure
            dt = (t[f] - t[f - 1]) / 1000
            if dt > 0.2:
                continue
            me = next((j for j in range(team * 6, team * 6 + 6) if ctrl[f] >> j & 1 and m["role"][f * 12 + j] != "0"),
                      None)
            if me is None:
                continue
            x, y = m["pos"][(f * 12 + me) * 2], m["pos"][(f * 12 + me) * 2 + 1]
            cx, cy = m["pos"][(f * 12 + k) * 2], m["pos"][(f * 12 + k) * 2 + 1]
            d = math.hypot(x - cx, y - cy)
            cur["secs"] += dt
            cur["dsum"] += d * dt
            cur["press"] += dt * (d <= PRESS)
            cur["slot"] += dt * (abs(x) <= SLOT_X and SLOT_Y0 <= GOAL_Y - y * e <= SLOT_Y1)
    res = []
    for v in out:
        if v["secs"] < MIN_S:
            continue
        sh = [s for s in shots[1 - v["team"]] if v["f0"] <= s["f"] <= v["f1"]]
        res.append(dict(system=m["system"], game=name, team=v["team"], secs=v["secs"], dist=v["dsum"] / v["secs"],
                        press=v["press"] / v["secs"], slot=v["slot"] / v["secs"], shots=len(sh),
                        xg=sum(s.get("xg") or 0 for s in sh), goals=sum(s["result"] == "goal" for s in sh),
                        hd=sum(s.get("danger") == "high" for s in sh),
                        hd_goals=sum(s.get("danger") == "high" and s["result"] == "goal" for s in sh)))
    return res


def thirds(rows, key):
    rows = sorted(rows, key=lambda r: r[key])
    n = len(rows)
    return [rows[:n // 3], rows[n // 3:2 * n // 3], rows[2 * n // 3:]]


def line(label, rows, key=None):
    n = len(rows)
    if not n:
        return f"  {label:34} none"
    span = f"{min(r[key] for r in rows):.2f}-{max(r[key] for r in rows):.2f}" if key else ""
    return (f"  {label:34} {span:>11} {n:5} {sum(r['secs'] for r in rows) / n:6.1f} s "
            f"{sum(r['shots'] for r in rows) / n:6.2f} {sum(r['xg'] for r in rows) / n:7.3f} "
            f"{sum(r['goals'] for r in rows):5} {100 * sum(r['goals'] for r in rows) / n:6.1f}%")


def main():
    allv = []
    for name, S, m in games():
        allv += visits(m, name)
    head = f"  {'':34} {'range':>11} {'n':>5} {'carried':>8} {'shots':>6} {'xG':>7} {'goals':>5} {'goal/visit':>7}"
    for system in ("genesis", "snes"):
        V = [v for v in allv if v["system"] == system]
        print(f"\n== {system}: {len(V)} visits in {len({v['game'] for v in V})} games (per visit)")
        print(head)
        print(line("all", V))
        for key, names in (("dist", ("closest third (mean distance)", "middle third", "farthest third")),
                           ("press", ("least time within 10 ft", "middle third", "most time within 10 ft")),
                           ("slot", ("least time in the slot", "middle third", "most time in the slot"))):
            for lab, rows in zip(names, thirds(V, key)):
                print(line(lab, rows, key))
        hi_p = sorted(v["press"] for v in V)[2 * len(V) // 3]
        hi_s = sorted(v["slot"] for v in V)[2 * len(V) // 3]
        print(line("pressing (top third, time close)", [v for v in V if v["press"] >= hi_p]))
        print(line("sitting in the slot, not pressing", [v for v in V if v["slot"] >= hi_s and v["press"] < hi_p]))
        print(line("neither", [v for v in V if v["slot"] < hi_s and v["press"] < hi_p]))


if __name__ == "__main__":
    main()
