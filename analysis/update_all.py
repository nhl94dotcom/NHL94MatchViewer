"""Rebuild everything that comes from the league result databases, in the right order (2026-11-04, the user). Put fresh All_Games_GENS.csv and All_Games_SNES.csv in %USERPROFILE%\\NHL94_League_Data first.
Stops at the first step that fails, and says how to pick up from there. Every step runs in gentle mode. It ends with tests/check_league_outputs.py. It commits nothing: read `git diff`, then commit.

The team Elo adjustments are refitted and printed as dicts for the league's Elo code, but nothing changes that code. Pasting them in, if you want them, is your call.

python analysis/update_all.py                everything
python analysis/update_all.py --list         the steps
python analysis/update_all.py --from NAME    from that step on, after a failure
python analysis/update_all.py --tests        also the slower tests of the method (K and the bonus, coach eras and the pull, fairness between levels, Glicko)"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent / "scoring_map"))
from lowload import breathe, gentle  # noqa: E402

STEPS = (("ratings", "the all-leagues coach ratings", ["analysis/coach_rating.py"]),
         ("groups", "ratings by league group", ["analysis/coach_rating.py", "groups"]),
         ("levels", "Classic teams by level of player", ["analysis/coach_team_levels.py"]),
         ("elo", "team Elo adjustments, on the league's method", ["analysis/league_team_elo.py"]),
         ("team_guides", "the team guides", ["analysis/classic_team_guide.py"]),
         ("graphics", "the Elo number lines", ["analysis/make_elo_line.py"]),
         ("logos", "the same with logos, outside the repository", ["analysis/make_elo_line_logos.py"]),
         ("bands", "the shaded Elo graphics: plain ones for the guides, logo ones outside the repository", ["analysis/make_elo_bands.py"]),
         ("player_guides", "the player guides", ["analysis/classic_player_guide.py"]),
         ("draft_guide", "the draft guide", ["analysis/classic_draft_guide.py"]),
         ("history", "each coach's Rating on past dates, private", ["analysis/coach_history.py", "fresh"]),
         ("league_ratings", "the league ratings", ["analysis/league_ratings.py"]),
         ("coach_guides", "the coach pages, private", ["analysis/coach_guide.py"]),
         ("coach_reports", "the coach reports, private", ["analysis/coach_reports.py"]),
         ("checks", "checks on all of it", ["tests/check_league_outputs.py"]))
SLOW = (("k_test", "K and the coasting bonus tested", ["analysis/league_elo_k.py"]),
        ("strength_test", "coach eras and the pull on teams tested", ["analysis/team_strength_checks.py"]),
        ("level_test", "whether the league's Elo is fair between levels", ["analysis/league_elo_levels.py"]),
        ("glicko_test", "Glicko against the league's Elo", ["analysis/league_glicko.py"]))
ORDER = ("CHI", "MTL", "WPG", "DET", "EDM", "TOR", "DAL", "BOS", "PHI", "QUE", "VAN", "LA", "BUF", "PIT", "CGY", "WSH", "NYI", "HFD", "TB", "NYR", "STL", "SJ", "NJ", "ANH", "OTW", "FLA")


def dicts():
    """The adjustments as the league's Elo code holds them: to the nearest 5, and teams with under 100 Classic games at the lowest of the well-used ones."""
    data = json.loads((ROOT / "reports" / "classic_team_elo.json").read_text(encoding="utf-8"))
    for label, var in (("Genesis", "gensTeamRatingsDict"), ("SNES", "snesTeamRatingsDict")):
        teams = data[label]["teams"]
        low = 5 * round(min(v["adj"] for v in teams.values() if v["games"] >= 300) / 5)
        vals = {t: 5 * round(teams[t]["adj"] / 5) if t in teams and teams[t]["games"] >= 100 else low for t in ORDER}
        print(f"    {var} = {{" + ",".join(f'"{t}": {int(vals[t])}' for t in ORDER) + "}")


def main():
    args = sys.argv[1:]
    steps = STEPS[:-1] + (SLOW if "--tests" in args else ()) + STEPS[-1:]
    if "--list" in args:
        for name, what, _ in steps:
            print(f"{name:15} {what}")
        return
    if "--from" in args:
        start = args[args.index("--from") + 1]
        names = [s[0] for s in steps]
        if start not in names:
            sys.exit(f"No step called {start}. Steps: {', '.join(names)}")
        steps = steps[names.index(start):]
    gentle()
    began = time.time()
    for name, what, command in steps:
        t0 = time.time()
        print(f"\n=== {name}: {what}", flush=True)
        log = ROOT / "reports" / f"update_{name}.log"
        with open(log, "w", encoding="utf-8") as fh:
            done = subprocess.run([sys.executable, *command], cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
        print(f"    {time.time() - t0:.0f} s; output in reports/update_{name}.log", flush=True)
        if done.returncode:
            print(log.read_text(encoding="utf-8")[-1500:])
            sys.exit(f"\n{name} failed. After fixing it: python analysis/update_all.py --from {name}")
        breathe()
    print(f"\nFinished in {(time.time() - began) / 60:.0f} minutes. New dicts for the league's Elo code, if you want them:")
    dicts()
    print("\nRead `git diff`, then commit. Nothing has been committed or changed in the Elo code.")


if __name__ == "__main__":
    main()
