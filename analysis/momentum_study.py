"""Momentum in the ROM? (2026-11-08, a community member: "Take the first half of shots for each team in a game and calculate
the shooting percentage (goals/shot) and then compare to the second half of shots taken in the game.")

Every recorded game in the game folder (both systems apart). For each team in each game, its shots in the order taken,
split into a first half and a second half (an odd count: the middle shot left out), and:
- shooting % over all the first halves against all the second halves;
- the correlation, over team-games, between a team's first-half and second-half shooting %. A team that is "hot" early
  staying hot would make it positive, but so would a team or goalie simply being better that game. So the test of
  momentum is the order: the same shots shuffled within each team-game (SHUFFLES times) give what the correlation and
  the first / second difference look like when order means nothing; the real figures are compared with that.
- shooting % on the next 3 shots after the team scored, against its other shots (a hot hand right after a goal).
Two shot sets: shots on goal (the game's count: counted saves, posts it counted and goals) and all attempts.
Aggregates only.

python analysis/momentum_study.py"""
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
SHUFFLES = 2000


def games():
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season":
            continue
        for _ in range(3):
            try:
                yield json.loads(load_js_object(p))
                break
            except (ValueError, OSError):       # being rewritten
                import time
                time.sleep(2)


def corr(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sx = sum((a - mx) ** 2 for a in xs) ** 0.5
    sy = sum((b - my) ** 2 for b in ys) ** 0.5
    return sxy / (sx * sy) if sx and sy else 0.0


def halves(seqs):
    """seqs: one 0/1 list (goal or not) per team-game. First / second half goals and shots, and the per-team-game rates."""
    g1 = s1 = g2 = s2 = 0
    r1, r2 = [], []
    for q in seqs:
        h = len(q) // 2
        if h < 3:
            continue
        a, b = q[:h], q[len(q) - h:]
        g1, s1, g2, s2 = g1 + sum(a), s1 + h, g2 + sum(b), s2 + h
        r1.append(sum(a) / h)
        r2.append(sum(b) / h)
    return g1, s1, g2, s2, corr(r1, r2), len(r1)


def report(name, seqs):
    g1, s1, g2, s2, c, n = halves(seqs)
    rnd = random.Random(94)
    diffs, cors = [], []
    for _ in range(SHUFFLES):
        sh = [rnd.sample(q, len(q)) for q in seqs]
        a1, b1, a2, b2, cc, _ = halves(sh)
        diffs.append(a2 / b2 - a1 / b1)
        cors.append(cc)
    d = g2 / s2 - g1 / s1
    p_d = sum(abs(x) >= abs(d) for x in diffs) / SHUFFLES
    p_c = sum(x >= c for x in cors) / SHUFFLES
    lo, hi = sorted(cors)[int(0.025 * SHUFFLES)], sorted(cors)[int(0.975 * SHUFFLES)]
    print(f"  {name}: {n} team-games")
    print(f"    first half {g1}/{s1} = {100 * g1 / s1:.1f}%   second half {g2}/{s2} = {100 * g2 / s2:.1f}%   "
          f"(difference {100 * d:+.1f} points; shuffled order gives one this big {100 * p_d:.0f}% of the time)")
    print(f"    team-game correlation, first-half % with second-half %: {c:+.3f}; shuffled order: "
          f"{sum(cors) / SHUFFLES:+.3f} (95% {lo:+.3f} to {hi:+.3f}); real at or above shuffled {100 * p_c:.0f}% of the time")
    # after a goal: against the same shots in a shuffled order (a team that scores a lot that game has more shots
    # after a goal, so "after a goal" is higher even with no momentum)
    def after_goal(qs):
        after, other = [0, 0], [0, 0]
        for q in qs:
            since = 99
            for x in q:
                box = after if since < 3 else other
                box[0] += x
                box[1] += 1
                since = 0 if x else since + 1
        return after, other
    after, other = after_goal(seqs)
    gap = after[0] / max(1, after[1]) - other[0] / max(1, other[1])
    gaps = []
    for _ in range(SHUFFLES):
        a_, o_ = after_goal([rnd.sample(q, len(q)) for q in seqs])
        gaps.append(a_[0] / max(1, a_[1]) - o_[0] / max(1, o_[1]))
    gaps.sort()
    print(f"    the next 3 shots after a goal: {after[0]}/{after[1]} = {100 * after[0] / max(1, after[1]):.1f}%;   "
          f"other shots {other[0]}/{other[1]} = {100 * other[0] / max(1, other[1]):.1f}%;   gap {100 * gap:+.1f} points, "
          f"shuffled order {100 * sum(gaps) / SHUFFLES:+.1f} (95% {100 * gaps[int(.025 * SHUFFLES)]:+.1f} to {100 * gaps[int(.975 * SHUFFLES)]:+.1f})")


def main():
    by = {}
    for m in games():
        system = m.get("system", "genesis")
        shots = sorted((s for s in m.get("shotList", []) if s.get("team") in (0, 1)), key=lambda s: s["f"])
        for team in (0, 1):
            mine = [s for s in shots if s["team"] == team]
            on = [int(s["result"] == "goal") for s in mine if s["result"] == "goal" or s.get("counted")]
            att = [int(s["result"] == "goal") for s in mine]
            by.setdefault(system, {"on": [], "att": [], "games": 0})
            by[system]["on"].append(on)
            by[system]["att"].append(att)
        by[system]["games"] += 1
    for system, v in sorted(by.items()):
        print(f"{system.upper()}: {v['games']} games")
        report("shots on goal", v["on"])
        report("all attempts", v["att"])


if __name__ == "__main__":
    main()
