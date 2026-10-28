"""EA Special attempts in the recorded Genesis games, measured the way the scoring map's EA runs set them up:
python analysis/ea_real.py [matches folder]   (default: Documents\\NHL94 Viewer\\matches)

An attempt is a shot the converter marked `flip` (export_match.add_shot_context: a person's forehand wrist shot from
the side at a goalie in position, not a follow-up); the follow-up is the team's `afterFlip` shot. For each: the net
(top = shooting up the screen), the hand, where it was released in the EA runs' terms (out = from the goal line,
GOAL_Y 264; side = from the middle; 3 units a foot), forehand attempts (the match files' `flip`) and backhand ones (the
same rule from the backhand side, export_match.EA_BACKHAND), what came of each (outcome), the shooter's skating speed over the quarter second before the
release in units a game frame (60 a second), his working Agility / Speed at the time (the match file's `work`) and his
full speed holding the d-pad from them (TOP_SPEED, measured in the scoring-map harness 2026-10-26: Agility / Speed
10 1.75, 13 1.85, 18 2.0, 20 2.05, 30 2.35, in between by straight lines), the aim held and what came of it.
The EA runs had the skater at 2.5 (beyond any skater), then at 1.7 (the user: a little below full speed, tapping the
d-pad) and found the bottom net's best at 20 ft out (SCORING_GENESIS_EA "Skating speed and a person's slop")."""
import copy
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import export_match  # noqa: E402

GOAL_Y = 264
K = 12
TOP_SPEED = [(10, 1.75), (13, 1.85), (18, 2.0), (20, 2.05), (30, 2.35)]
AIMS = ["Up", "Up-Right", "Right", "Down-Right", "Down", "Down-Left", "Left", "Up-Left", "none"]


def top_speed(r):
    r = min(max(r, TOP_SPEED[0][0]), TOP_SPEED[-1][0])
    for (a, va), (b, vb) in zip(TOP_SPEED, TOP_SPEED[1:]):
        if a <= r <= b:
            return va + (vb - va) * (r - a) / (b - a)


def load(p):
    text = p.read_text(encoding="utf-8")
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def backhand(m):
    """The same match with the converter's EA Special rule applied to backhand attempts (from the backhand side)
    instead of forehand ones (export_match.EA_BACKHAND; the match files mark forehand ones only)."""
    b = copy.deepcopy(m)
    for s in b.get("shotList", []):
        for key in ("flip", "afterFlip", "eaDive"):
            s.pop(key, None)
    export_match.EA_BACKHAND = True
    try:
        export_match.add_shot_context(b)
    finally:
        export_match.EA_BACKHAND = False
    return b


def outcome(m, sh, follow):
    """What came of an attempt in the 2.5 s after it: a goal (by the shooter on his follow-up, by a teammate, in off a
    defender who had the puck, or in a scramble with no follow-up shot), else who got the puck first (the goalie, a
    defending skater, his own team), or a follow-up that was stopped."""
    t, own = m["t"], m["owner"]
    f, team = sh["f"], sh["team"]
    end = next((q for q in range(f, len(t)) if t[q] - t[f] > 2500), len(t) - 1)
    defenders = range((1 - team) * 6, (1 - team) * 6 + 6)
    goal = next((g for g in m.get("goals", []) if g["team"] == team and f < g["f"] <= end), None)
    first = next((own[q] for q in range(f + 1, end + 1) if own[q] >= 0), None)
    if goal:
        if follow and follow["result"] == "goal":
            return "goal: shooter" if follow["idx"] == sh["idx"] else "goal: teammate"
        if any(own[q] in defenders and m["role"][q * K + own[q]] != "0" for q in range(f + 1, goal["f"] + 1)):
            return "goal: in off a defender"
        return "goal: scramble"
    if follow:
        return "follow-up stopped"
    if first is None:
        return "loose"
    if first in defenders:
        return "goalie held" if m["role"][f * K + first] == "0" else "defender claimed"
    return "own team, no shot"


def attempts(m, kind="forehand"):
    t, pos = m["t"], m["pos"]
    shots = m.get("shotList", [])
    for i, sh in enumerate(shots):
        if not sh.get("flip"):
            continue
        f = sh["f"]
        k = next(k for k in range(sh["team"] * 6, sh["team"] * 6 + 6) if int(m["roster"][f * K + k], 36) == sh["idx"])
        q0 = next((q for q in range(f, -1, -1) if t[f] - t[q] >= 250), 0)
        dist = math.hypot(pos[(f * K + k) * 2] - pos[(q0 * K + k) * 2], pos[(f * K + k) * 2 + 1] - pos[(q0 * K + k) * 2 + 1])
        speed = dist / ((t[f] - t[q0]) / 1000 or 1) / 60
        work = [w for w in m.get("work", []) if w[1] == k and w[0] <= f]
        agl, spd = (work[-1][3], work[-1][4]) if work else (None, None)
        top = sh["y"] > 0
        follow = next((s for s in shots[i + 1:] if s.get("afterFlip") and s["team"] == sh["team"]
                       and 0 < t[s["f"]] - t[f] <= 2000), None)
        aim = (sh.get("aim") or {}).get("d", 8)
        fside = None
        if follow:                                   # the follow-up's aim against the side he shoots it from (screen
            fd = (follow.get("aim") or {}).get("d", 8)   # x): near post, far post or the middle
            fd = 8 if fd is None else fd
            across = 1 if fd in (1, 2, 3) else -1 if fd in (5, 6, 7) else 0
            fside = "middle" if across == 0 else "near" if across * follow["x"] > 0 else "far"
            fside += "-" + ("high" if fd in (7, 0, 1) else "low" if fd in (3, 4, 5) else "mid")
        yield dict(game=m["name"], f=f, team=sh["team"], kind=kind, outcome=outcome(m, sh, follow), period=m["period"][f] + 1, clock=m["clock"][f], net="top" if top else "bottom",
                   hand="right" if m["mirror"][f * K + k] == "1" else "left", out=round(GOAL_Y - abs(sh["y"])),
                   side=round(abs(sh["x"])), speed=round(speed, 2), agl=agl, spd=spd,
                   full=round(top_speed(spd), 2) if spd is not None else None, aim=AIMS[aim if aim is not None else 8],
                   result=sh["result"], dive=bool(sh.get("eaDive")),
                   follow=follow["result"] if follow else None, follow_aim=fside,
                   follow_kind=follow.get("kind") if follow else None,
                   follow_gap=round((t[follow["f"]] - t[f]) / 1000, 2) if follow else None,
                   ea_goal=bool(follow and follow["result"] == "goal"))


def main():
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.environ["USERPROFILE"]) / "Documents" / "NHL94 Viewer" / "matches"
    rows, games = [], 0
    for p in sorted(d.glob("*.js")):
        if p.name == "season.js":
            continue
        m = load(p)
        if m.get("system", "genesis") != "genesis":
            continue
        games += 1
        rows += list(attempts(m)) + list(attempts(backhand(m), "backhand"))
    print(f"{len(rows)} attempts in {games} Genesis games")
    print("game                       P clock kind net    hand  out side speed  A/S   full  aim         result   follow   follow aim  after EA")
    for r in rows:
        print(f"{r['game'][:26]:26} {r['period']} {r['clock'] // 60:2}:{r['clock'] % 60:02} {r['kind'][:4]} {r['net']:6} {r['hand']:5} "
              f"{r['out']:4} {r['side']:4} {r['speed']:5.2f} {r['agl']}/{r['spd']} {r['full'] or 0:5.2f} {r['aim']:11} "
              f"{r['result']:8} {str(r['follow']):8} {str(r['follow_aim']):11} {str(r['follow_gap']):5} {r['outcome']}")
    for kind in ("forehand", "backhand"):
        for net in ("top", "bottom"):
            rs = [r for r in rows if r["kind"] == kind and r["net"] == net]
            if rs:
                print(f"{kind} {net}: {len(rs)}", dict(Counter(r["outcome"] for r in rs).most_common()))
    for net in ("top", "bottom"):
        rs = [r for r in rows if r["net"] == net and r["kind"] == "forehand"]
        if rs:
            print(f"{net}: {len(rs)} attempts, {sum(r['ea_goal'] for r in rs)} scored on the follow-up; speed "
                  f"{min(r['speed'] for r in rs):.2f}-{max(r['speed'] for r in rs):.2f} a frame, "
                  f"{sum(r['speed'] / r['full'] for r in rs if r['full']) / max(1, sum(1 for r in rs if r['full'])):.0%} "
                  f"of his full speed on average; out {min(r['out'] for r in rs)}-{max(r['out'] for r in rs)}")


if __name__ == "__main__":
    main()
