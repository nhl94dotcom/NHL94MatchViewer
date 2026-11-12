"""Two bot versions compared, game by game (2026-11-12: 16-game goal averages misled twice the same day; goals vary
by about 2 from game to game). Each version's games are bot_record.py's on the 16 matchups (NHL94_BOT_TEAMS=1: game n
is matchup n % 16 with bot_run's seed n), kept in RUNS/cmp_v<VERSION>/matches and recorded only where missing (two
processes at a time: one a version; the raw captures deleted once converted). Game n of A and game n of B share the seed and the matchup, so the per-game
differences are paired. Printed, for the bot's side: each version's mean (± its standard error) and the paired
difference B - A (± its standard error, and how many standard errors it is) for expected goals (every shot's xG),
goals, shots on goal, penalties, and the expected goals and goals against.

python bot_compare.py A B GAMES   (e.g. 59 60 32)
python bot_compare.py --report A B"""
import json
import math
import os
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from paths import RUNS  # noqa: E402

FOLDER = lambda v: RUNS / f"cmp_v{v}"


def have(v):
    return {int(f.stem.split("_")[-1]) for f in (FOLDER(v) / "matches").glob("bot_genesis_*.js")}


def record(versions, games):
    """Record the missing games of each version, the versions side by side; contiguous runs from the first missing."""
    procs = []
    for v in versions:
        got = have(v)
        missing = [n for n in range(games) if n not in got]
        if not missing:
            continue
        first = missing[0]
        env = dict(os.environ, NHL94_BOT_TEAMS="1", NHL94_BOT_VERSION=str(v))
        log = open(RUNS / f"cmp_v{v}.log", "a")
        procs.append(subprocess.Popen([sys.executable, str(HERE / "bot_record.py"), str(FOLDER(v)), str(games - first), str(first)],
                                      cwd=str(HERE), env=env, stdout=log, stderr=subprocess.STDOUT))
    while any(p.poll() is None for p in procs):
        time.sleep(20)
    for v in versions:                       # the raw captures aren't needed once converted (disk)
        cap = (FOLDER(v) / "captures").resolve()
        if cap.is_dir() and cap.parent == FOLDER(v).resolve() and cap.parent.parent == RUNS.resolve():
            import shutil
            shutil.rmtree(cap)


def per_game(v):
    out = {}
    for f in sorted((FOLDER(v) / "matches").glob("bot_genesis_*.js")):
        t = f.read_text(encoding="utf-8")
        m = json.loads(t[t.index("{"):t.rindex("}") + 1])
        n = int(f.stem.split("_")[-1])
        shots = m.get("shotList", [])
        last = lambda side, k: m["stats"][side][-1][k]
        out[n] = {
            "xG": sum(s.get("xg") or 0 for s in shots if s["team"] == 0),
            "goals": sum(1 for g in m.get("goals", []) if g["team"] == 0 and not g.get("ownGoal")),
            "shots on goal": sum(1 for s in shots if s["team"] == 0 and s.get("counted")),
            "penalties": sum(1 for p in m.get("penalties", []) if p["team"] == 0),
            "xG against": sum(s.get("xg") or 0 for s in shots if s["team"] == 1),
            "goals against": sum(1 for g in m.get("goals", []) if g["team"] == 1 and not g.get("ownGoal")),
        }
    return out


def mse(xs):
    return (st.mean(xs), st.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else float("nan"))


def report(a, b):
    A, B = per_game(a), per_game(b)
    common = sorted(set(A) & set(B))
    print(f"version {a} ({len(A)} games) against version {b} ({len(B)} games); paired on {len(common)} games "
          f"(the same seed and matchup)\n")
    print(f"| Per game | v{a} | v{b} | v{b} - v{a} (paired) | in standard errors |")
    print("|---|---|---|---|---|")
    for k in next(iter(A.values())):
        ma, sa = mse([A[n][k] for n in A])
        mb, sb = mse([B[n][k] for n in B])
        d = [B[n][k] - A[n][k] for n in common]
        md, sd = mse(d) if len(d) > 1 else (float("nan"), float("nan"))
        z = md / sd if sd and sd == sd and sd > 0 else float("nan")
        print(f"| {k} | {ma:.2f} ±{sa:.2f} | {mb:.2f} ±{sb:.2f} | {md:+.2f} ±{sd:.2f} | {z:+.1f} |")
    print("\nA difference within about 2 standard errors is noise; recorded games go on accumulating in "
          f"{FOLDER(a).name} / {FOLDER(b).name}.")


def main():
    if sys.argv[1] == "--report":
        report(int(sys.argv[2]), int(sys.argv[3]))
        return
    a, b, games = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    record((a, b), games)
    report(a, b)


if __name__ == "__main__":
    main()
