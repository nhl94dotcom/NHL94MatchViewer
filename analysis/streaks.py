"""Are the game's dice streaky? (2026-11-08; docs/GAME_VARIABLES_PLAN.md study 4: "Modano missed 4-5 in a row").

The recorded games (both systems). For each kind of roll, each player's results in a game in the order they came:
- shots: a shooter's attempts that weren't blocked, the result (goal 1, else 0) less the shot's expected goals;
- goalies: the shots a goalie faced (not blocked), goal 1 less the expected goals (a positive run = letting them in);
- checks: a person's check attempts that reached a man (export_match's checkAttempts: hit 1, failed 0);
- passes: a player's passes (picked off 1, else 0).
The statistic: over every consecutive pair in a sequence, the product of the two results' distances from the
sequence's own mean, summed (positive = streaky: like follows like). The baseline: the same sequences shuffled, 2,000
times (what the statistic is with order meaning nothing). Also the plain question for shots: after a miss, after two
and after three in a row, the next shot's goals against its expected goals.

python analysis/streaks.py"""
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
SHUFFLES = 2000


def stat(seqs):
    total = 0.0
    for q in seqs:
        if len(q) < 2:
            continue
        mean = sum(q) / len(q)
        total += sum((a - mean) * (b - mean) for a, b in zip(q, q[1:]))
    return total


def test(name, seqs):
    seqs = [q for q in seqs if len(q) >= 2]
    if not seqs:
        return
    real = stat(seqs)
    rnd = random.Random(94)
    base = sorted(stat([rnd.sample(q, len(q)) for q in seqs]) for _ in range(SHUFFLES))
    above = sum(b >= real for b in base) / SHUFFLES
    pairs = sum(len(q) - 1 for q in seqs)
    print(f"  {name}: {len(seqs)} sequences, {pairs} consecutive pairs; statistic {real:+.2f}, shuffled "
          f"{sum(base) / SHUFFLES:+.2f} (95% {base[int(.025 * SHUFFLES)]:+.2f} to {base[int(.975 * SHUFFLES)]:+.2f}); "
          f"shuffles at or above the real one {above:.0%}")


def main():
    data = defaultdict(lambda: defaultdict(list))
    after = defaultdict(lambda: defaultdict(lambda: [0, 0.0, 0]))   # system -> misses in a row -> [goals, xg, shots]
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season" or p.stem.endswith(".heat") or not (HOME / "captures" / p.stem).is_dir():
            continue
        m = json.loads(load_js_object(p))
        sysn = m.get("system", "genesis")
        shots = sorted((s for s in m.get("shotList", []) if s.get("team") in (0, 1) and s["result"] != "blocked"
                        and s.get("xg") is not None), key=lambda s: s["f"])
        by_shooter, by_goalie = defaultdict(list), defaultdict(list)
        for s in shots:
            r = (1 if s["result"] == "goal" else 0) - s["xg"]
            by_shooter[(s["team"], s["idx"])].append((s, r))
            if s.get("goalie") is not None:
                by_goalie[(1 - s["team"], s["goalie"])].append(r)
        for seq in by_shooter.values():
            data[sysn]["shots (goal less xG)"].append([r for _, r in seq])
            run = 0
            for s, r in seq:
                for k in (1, 2, 3):
                    if run >= k:
                        a = after[sysn][k]
                        a[0] += s["result"] == "goal"
                        a[1] += s["xg"]
                        a[2] += 1
                run = 0 if s["result"] == "goal" else run + 1
        for seq in by_goalie.values():
            data[sysn]["goalies (goal less xG faced)"].append(seq)
        chk = defaultdict(list)
        for c in sorted(m.get("checkAttempts", []), key=lambda c: c["f"]):
            if c["result"] in ("hit", "failed"):
                chk[(c["team"], c["by"])].append(1 if c["result"] == "hit" else 0)
        data[sysn]["checks reaching a man (hit 1)"].extend(chk.values())
        pas = defaultdict(list)
        for q in sorted(m.get("passes", []), key=lambda q: q["f"]):
            pas[(q["team"], q["idx"])].append(1 if q["result"] == "intercepted" else 0)
        data[sysn]["passes (picked off 1)"].extend(pas.values())
    for sysn in sorted(data):
        print(sysn.upper())
        for name, seqs in data[sysn].items():
            test(name, seqs)
        for k in (1, 2, 3):
            g, x, n = after[sysn][k]
            if n:
                print(f"  a shooter's next shot after {k}+ misses in a row: {g} goals on {n} shots, expected {x:.1f}")


if __name__ == "__main__":
    main()
