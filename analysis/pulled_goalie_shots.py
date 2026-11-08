"""Shots taken with the shooter's own goalie off the ice (Genesis; bug 13, delayed-penalty sniping, 2026-11-08). The
Genesis doshot makes every shot within 200 units of its aim point exact when the shooting team's goalie is off
(ReadGoaliePulled; GENESIS_SHOOTING 4.6): pulled for a delayed penalty against the other team, or late in a game.
For every recorded Genesis game in the game folder: the shots whose team had no goalie on the ice at the release,
how many were within 200 of the aim point (the ones the rule makes exact), their goals and xG, and the same for all
other shots within 200 for comparison. Aggregates only.

python analysis/pulled_goalie_shots.py"""
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402
from xg import attacks_top  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")


def main():
    rows = []
    games = 0
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season":
            continue
        try:
            m = json.loads(load_js_object(p))
        except (ValueError, OSError):
            continue
        if m.get("system") != "genesis" or "role" not in m:
            continue
        games += 1
        for s in m.get("shotList", []):
            f, team = s["f"], s["team"]
            own_in = any(m["role"][f * 12 + k] == "0" for k in range(team * 6, team * 6 + 6))
            top = attacks_top(m, f, team)
            aim = s.get("aim") or {}
            gy = 264 if top else -264
            d = math.hypot((aim.get("x", 0)) - s["x"], gy - s["y"])
            rows.append(dict(pulled=not own_in, near=d <= 200, goal=s["result"] == "goal", xg=s.get("xg") or 0,
                             kind=s["kind"], human=s.get("human"), game=p.stem))
    print(f"{games} Genesis games, {len(rows)} shots")
    for label, sel in (("own goalie off the ice", lambda r: r["pulled"]), ("own goalie in", lambda r: not r["pulled"])):
        for near in (True, False):
            g = [r for r in rows if sel(r) and r["near"] == near]
            if not g:
                continue
            goals = sum(r["goal"] for r in g)
            print(f"  {label}, {'within' if near else 'beyond'} 200 of the aim point: {len(g)} shots, {goals} goals "
                  f"({goals / len(g):.1%}), xG {sum(r['xg'] for r in g):.1f}; kinds {dict(Counter(r['kind'] for r in g))}; "
                  f"in {len({r['game'] for r in g})} games")


if __name__ == "__main__":
    main()
