"""Checks the season page's inputs (run after re-converting, with tools/season.py run in each folder): every game's
summary is current and in season.js, and agrees with its match file and with itself. season.html adds the summaries up
per team as they are (standings(): every number and list summed), so a summary that is right makes totals that are.

For each match file in a game folder:
- its summary exists, is from this season.py VERSION and not older than the match file, and season.js has it;
- goals for = the final score = that team's goals in the match file's goal list; shot attempts = its shotList entries;
  xG = the sum over its unblocked attempts; checks = its hits (the game's count, tests/check_matches.py);
- the two sides mirror each other (goals, shots on goal, attempts, xG for and against);
- the two teams' abbreviations differ (season.html keys its standings by abbreviation: a game between two copies of one
  team would be added to one row twice).

python tests/check_season.py [folders ...]   (default: the project and Documents/NHL94 Viewer)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402

FOLDERS = [ROOT, Path.home() / "Documents" / "NHL94 Viewer"]
SKIP = ("_live", "snes_NHL94_Classic_state", "snes_SDL", "explore1_menus")  # tests, as tests/check_matches.py skips them


def version():
    for line in (ROOT / "tools" / "season.py").read_text(encoding="utf-8").splitlines():
        if line.startswith("VERSION = "):
            return int(line.split("=")[1].split("#")[0])


def check_folder(folder, v):
    matches = folder / "matches"
    season_js = matches / "season.js"
    problems, n = [], 0
    if not season_js.exists():
        return [f"{folder}: no season.js"], 0
    in_season = {g["name"]: g for g in json.loads(load_js_object(season_js))["games"]}
    for path in sorted(matches.glob("*.js")):
        if path.name == "season.js" or path.name.startswith("_") or path.stem.startswith(SKIP):
            continue
        name, sp = path.stem, matches / f"{path.stem}.summary.json"
        try:
            m = json.loads(load_js_object(path))
        except Exception:
            continue                                    # a broken match file: season.py leaves it out too
        n += 1
        bad = lambda text: problems.append(f"{name}: {text}")
        if not sp.exists():
            bad("no summary")
            continue
        s = json.loads(sp.read_text(encoding="utf-8"))
        if s.get("v") != v:
            bad(f"summary version {s.get('v')}, season.py {v}")
        if sp.stat().st_mtime < path.stat().st_mtime:
            bad("summary older than the match file")
        if name not in in_season:
            bad("not in season.js")
        elif in_season[name].get("teams") != s.get("teams"):
            bad("season.js has a different summary")
        if s["abbr"][0] == s["abbr"][1]:
            bad(f"both teams are {s['abbr'][0]}: season.html adds this game to one row twice")
        T, shots = s["teams"], m.get("shotList", [])
        final = m["score"][-2:]
        for side in (0, 1):
            t, o = T[side], T[1 - side]
            goals = sum(1 for g in m.get("goals", []) if g["team"] == side)
            # a recording begun mid-game (capture1, full_buttons): the score and the checks count from the start
            whole = s.get("fromStart", True)
            if t["gf"] != final[side] or whole and goals != t["gf"]:
                bad(f"side {side} goals: summary {t['gf']}, score {final[side]}, goal list {goals}")
            att = sum(1 for sh in shots if sh["team"] == side)
            if t["att"] != att:
                bad(f"side {side} attempts: summary {t['att']}, shotList {att}")
            xg = round(sum(sh["xg"] for sh in shots if sh["team"] == side and "xg" in sh and sh["result"] != "blocked"), 3)
            if "xg" in t and abs(t["xg"][0] - xg) > 0.002:
                bad(f"side {side} xG: summary {t['xg'][0]}, shots {xg}")
            if whole and "hits" in m and t["checks"] != sum(1 for h in m["hits"] if h["team"] == side):
                bad(f"side {side} checks: summary {t['checks']}, hits {sum(1 for h in m['hits'] if h['team'] == side)}")
            for a, b in (("gf", "ga"), ("sog", "sa"), ("att", "attA")):
                if t[a] != o[b]:
                    bad(f"side {side} {a} {t[a]} but the other side's {b} {o[b]}")
            if "xg" in t and "xg" in o and (abs(t["xg"][0] - o["xg"][2]) > 0.002 or t["xg"][1] != o["xg"][3]):
                bad(f"side {side} xG {t['xg'][:2]} but the other side's against {o['xg'][2:]}")
    for name in sorted(set(in_season) - {p.stem for p in matches.glob("*.js")}):
        problems.append(f"{name}: in season.js with no match file")
    return problems, n


def main():
    folders = [Path(a) for a in sys.argv[1:]] or FOLDERS
    v, total = version(), []
    for folder in folders:
        problems, n = check_folder(folder, v)
        print(f"{folder}: {n} games, {len(problems)} problem(s)")
        for p in problems:
            print("  " + p)
        total += problems
    print(f"\n{len(total)} problem(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
