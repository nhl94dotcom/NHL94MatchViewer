"""Luck against skill, game by game (2026-11-08; docs/GAME_VARIABLES_PLAN.md study 1: the forum's "AI factor", +1 / -1
for the game helping or hurting a team, measured instead of guessed).

The recorded games (both systems; each game counted once, whole games only). For each team in each game:
- chances made: its expected goals (xG, the game's own shot and save rules played out: tools/xg.py, xg_snes.py) on its
  attempts that weren't blocked;
- finishing luck: goals from those attempts less their xG (above 0, more went in than the chances say: a hot shooter or
  a poor goalie at the other end);
- the result's luck: the real goal difference less the xG difference.
Over the games: how much of the goal difference the chances explain (the variance of the goal difference split into
the xG difference and the rest), how often the team with the better chances didn't win, and the Deserve to Win meter
(tools/deserve.py) for the winners. Games with an SA-1 SNES build have no xG and are left out.

python analysis/luck_vs_skill.py"""
import json
import os
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from deserve import deserve  # noqa: E402
from share_game import load_js_object  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")


def main():
    by_sys = {}
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season" or p.stem.endswith(".heat") or not (HOME / "captures" / p.stem).is_dir():
            continue
        m = json.loads(load_js_object(p))
        shots = [s for s in m.get("shotList", []) if s.get("team") in (0, 1) and s["result"] != "blocked"]
        if not shots or not all(s.get("xg") is not None for s in shots if s["kind"] in ("shot", "one-timer")):
            continue
        p1 = [c for per, c in zip(m["period"], m["clock"]) if per == 0]
        if m["period"][0] != 0 or m["clock"][0] < max(p1) - 2:        # recorded from the opening faceoff only
            continue
        xgs = [sum(s["xg"] for s in shots if s["team"] == t and s.get("xg") is not None) for t in (0, 1)]
        g_x = [sum(1 for s in shots if s["team"] == t and s.get("xg") is not None and s["result"] == "goal") for t in (0, 1)]
        goals = [m["score"][-2], m["score"][-1]]
        d = deserve(m)
        by_sys.setdefault(m.get("system", "genesis"), []).append(dict(name=p.stem, goals=goals, xg=xgs, gx=g_x,
                                                                      win=d["win"], tie=d["tie"]))
    for system, games in sorted(by_sys.items()):
        n = len(games)
        gd = [g["goals"][0] - g["goals"][1] for g in games]
        xd = [g["xg"][0] - g["xg"][1] for g in games]
        luck = [a - b for a, b in zip(gd, xd)]
        fin = [g["gx"][t] - g["xg"][t] for g in games for t in (0, 1)]
        print(f"{system.upper()}: {n} whole games")
        print(f"  goal difference: variance {st.pvariance(gd):.2f}; the xG difference {st.pvariance(xd):.2f}, the rest "
              f"(luck) {st.pvariance(luck):.2f}; correlation of goal and xG difference {st.correlation(gd, xd):.2f}")
        print(f"  finishing luck per team-game (goals less xG on the same attempts): mean {st.mean(fin):+.2f}, "
              f"spread (sd) {st.pstdev(fin):.2f}; beyond +-1: {sum(abs(x) > 1 for x in fin)} of {len(fin)}, "
              f"beyond +-2: {sum(abs(x) > 2 for x in fin)}")
        better = [(x, a) for x, a in zip(xd, gd) if abs(x) >= 0.25]
        lost = sum(1 for x, a in better if x * a < 0)
        tied = sum(1 for x, a in better if a == 0)
        print(f"  games where one team had clearly better chances (0.25+ xG): {len(better)}; it lost {lost}, tied {tied}")
        winners = [g["win"][0] if g["goals"][0] > g["goals"][1] else g["win"][1] for g in games if g["goals"][0] != g["goals"][1]]
        if winners:
            print(f"  the winners' Deserve to Win: median {st.median(winners):.0%}; under 50% in {sum(w < 0.5 for w in winners)} "
                  f"of {len(winners)} decided games")


if __name__ == "__main__":
    main()
