"""Checks converted match files against the game's own counts (run after changing the converter, on both game folders).
For each match: goals = the score and the game's goal count, each player's goals add up to the team's, shots the game
counted (shotList counted or a goal) = the game's shots on goal, landed checks (hits) = the game's checks, faceoffs won =
the game's count, and counted passes against the game's passes tried (the known small gap is shown, not failed).
python tests/check_matches.py [match files or folders ...]   (default: matches/ and Documents/NHL94 Viewer/matches)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402
from systems.common import STAT_FIELDS  # noqa: E402

F = {name: i for i, name in enumerate(STAT_FIELDS)}
SKIP = ("_live", "snes_NHL94_Classic_state", "snes_SDL", "explore1_menus")  # tests, one-moment save-state previews


def check(m):
    """Problems (list of strings) and notes (the pass gap) for one match."""
    problems, notes = [], []
    st = m.get("stats")
    if not st or not st.get("home"):
        return ["no stat snapshots"], notes
    n, per = st["n"], st.get("p", 0)
    # What the game counted during the recording: the last snapshot less the first (a recording that began mid-game,
    # capture1 or full_buttons, starts from the counts so far)
    first = [st["home"][0], st["away"][0]]
    last = [[b - a for a, b in zip(first[t], (st["home"], st["away"])[t][-1])] for t in (0, 1)]
    abbr = m.get("abbr") or ["H", "A"]
    goals = m.get("goals", [])
    shots = m.get("shotList", [])
    for team in (0, 1):
        row, ab = last[team], abbr[team]
        g_game = row[F["goals"]]
        g_list = sum(1 for g in goals if g["team"] == team)
        if g_list != g_game:
            problems.append(f"{ab} goals: list {g_list}, game {g_game}")
        if per:
            roster = (m.get("rosters") or [[], []])[team]
            # a goalie's goals byte holds his goals against
            g_players = sum(row[n + per * k] for k in range((len(row) - n) // per) if not (k < len(roster) and roster[k].get("g")))
            if g_players != g_game:
                problems.append(f"{ab} goals by player {g_players}, team {g_game}")
        sog = sum(1 for s in shots if s["team"] == team and (s.get("counted") or s["result"] == "goal"))
        # a goal the game did not count as a shot (a pass shot, a SNES penalty-shot goal) is in both; compare the counted ones
        sog_counted = sum(1 for s in shots if s["team"] == team and s.get("counted"))
        if sog_counted != row[F["shots"]]:
            problems.append(f"{ab} shots on goal: list {sog_counted} (with goals {sog}), game {row[F['shots']]}")
        hits = sum(1 for h in m.get("hits", []) if h["team"] == team)
        if "hits" in m and hits != row[F["checks"]]:
            problems.append(f"{ab} checks: hits {hits}, game {row[F['checks']]}")
        fo = m.get("faceoffs")
        if fo is not None:
            won = sum(1 for x in fo if x.get("won") == team)
            if won != row[F["faceoffs"]]:
                problems.append(f"{ab} faceoffs won: list {won}, game {row[F['faceoffs']]}")
        passes = [p for p in m.get("passes", []) if p["team"] == team and p.get("counted")]
        if "passes" in m:
            notes.append(f"{ab} passes counted {len(passes)}/{row[F['passTried']]}")
    score = m.get("score")
    end = [st["home"][-1][F["goals"]], st["away"][-1][F["goals"]]]
    if score and len(score) >= 2 and [score[-2], score[-1]] != end:
        problems.append(f"final score {score[-2:]} vs game goals {end}")
    return problems, notes


def main(args):
    paths = []
    for a in args or [ROOT / "matches", Path.home() / "Documents" / "NHL94 Viewer" / "matches"]:
        a = Path(a)
        paths += sorted(a.glob("*.js")) if a.is_dir() else [a]
    bad = 0
    for p in paths:
        if p.name == "season.js" or any(p.stem.startswith(s) for s in SKIP):
            continue
        try:
            m = json.loads(load_js_object(p))
        except Exception as e:
            print(f"{p}: cannot read ({e})")
            bad += 1
            continue
        problems, notes = check(m)
        bad += bool(problems)
        print(f"{'FAIL' if problems else 'ok  '} {p.parent.parent.name[:12]:12} {p.stem:34} {'; '.join(problems) or ''}  [{'; '.join(notes)}]")
    print(f"\n{bad} match file(s) with problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
