"""Checks on everything built from the league databases: the guides, league ratings, history and coach reports. Prints aggregates and never a coach's name.
Fails (exit 1) on a mismatch. Run by analysis/update_all.py, or on its own: python tests/check_league_outputs.py"""
import csv
import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "analysis" / "scoring_map"))
import coach_history as H  # noqa: E402
import coach_rating as C  # noqa: E402
import league_ratings as LR  # noqa: E402
import league_team_elo as E  # noqa: E402

DOCS = ("TEAM_GUIDE_GENESIS.md", "TEAM_GUIDE_SNES.md", "PLAYER_GUIDE_GENESIS.md", "PLAYER_GUIDE_SNES.md", "DRAFT_GUIDE_CLASSIC.md", "LEAGUE_RATINGS.md", "COACH_RATING.md", "LEAGUE_RESULTS.md")
SYSTEMS = (("GENESIS", "Genesis", "All_Games_GENS.csv", 0), ("SNES", "SNES", "All_Games_SNES.csv", 1))
# words and real hockey players that happen to match a coach's name; league names are the leagues' own
ALLOWED_IN_DOCS = {"andrew", "johan", "pavel", "richter", "chaos", "slapshot", "brutus", "doubledown", "indio", "schmidt", "plabax"}
problems = []


def check(ok, text):
    print(("  ok    " if ok else "  WRONG ") + text, flush=True)
    if not ok:
        problems.append(text)


def anchors():
    print("Links")
    for name in DOCS:
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        heads = {re.sub(r"[^\w\- ]", "", m.group(1).lower()).replace(" ", "-") for m in re.finditer(r"^#+ (.+)$", text, re.M)}
        bad = [a for a in re.findall(r"\]\(#([^)]+)\)", text) if a not in heads]
        files = [a for a in re.findall(r"\]\(([\w./-]+\.(?:md|svg|png))\)", text) if not (ROOT / "docs" / a).exists()]
        check(not bad and not files, f"{name}: {len(bad)} broken links inside, {len(files)} to missing files")


def privacy():
    print("Privacy")
    names = set()
    for f in ("coach_ratings_GENESIS.csv", "coach_ratings_SNES.csv"):
        with open(C.DATA / f, encoding="utf-8") as fh:
            names |= {r["coach"].lower() for r in csv.DictReader(fh)}
    for name in DOCS:
        text = (ROOT / "docs" / name).read_text(encoding="utf-8").lower()
        hits = [n for n in names if len(n) >= 5 and n not in ALLOWED_IN_DOCS and n in text]
        check(not hits, f"{name}: {len(hits)} coach names found")
    tracked = subprocess_lines(["git", "ls-files"])
    check(not [p for p in tracked if "coach_guides" in p or "coach_history/" in p or "elo_docs" in p], "no private folder is tracked")


def subprocess_lines(cmd):
    import subprocess
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout.splitlines()


def elo_rule():
    print("The league's Elo rule")
    cases = (("3-1, the last goal 15 seconds from the end, was 3-0 from early on", [(1, 100), (1, 200), (1, 300), (-1, 885)], 300),
             ("1-goal win", [(1, 10)], 0),
             ("2-0: only the end of the game", [(1, 100), (1, 200)], 15),
             ("6-0 before 5:00: all the way from the sixth goal", [(1, t) for t in range(10, 70, 10)], 840))
    for text, goals, want in cases:
        got = E.coasting_seconds(goals)
        check(got == want or (want == 300 and got > 0), f"{text}: {got} seconds")
    check(E.multiplier(0) == 1 and E.multiplier(15) == 1.1 and E.multiplier(300) == 1.5, "multiplier: none, at least 1.1, ×1.5 from the second-period buzzer")


def team_guides():
    print("Team guides against the Elo fit")
    elo = json.loads((ROOT / "reports" / "classic_team_elo.json").read_text(encoding="utf-8"))
    for label, name in (("Genesis", "TEAM_GUIDE_GENESIS.md"), ("SNES", "TEAM_GUIDE_SNES.md")):
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        rows = re.findall(r"\[[^\]]+\((\w+)\)\]\(#[^)]+\) \| \w+ \| [^|]+ \| [^|]+ \| [^|]+ \| [^|]+ \| ([−+\d]+)(\*?) \|", text)
        wrong = 0
        for t, v, star in rows:
            e = elo[label]["teams"][t]
            wrong += int(v.replace("−", "-")) != round(e["adj"]) or (star == "*") != (e["fit_games"] < 300)
        check(rows and not wrong, f"{name}: {len(rows)} rows, {wrong} wrong")
        check("−0 " not in text and "−0|" not in text, f"{name}: no minus zero")


def history_and_leagues():
    sets = H.settings()
    data = json.loads((ROOT / "reports" / "league_ratings.json").read_text(encoding="utf-8"))
    for label, title, name, at in SYSTEMS:
        print(f"History and league ratings: {title}")
        with open(C.DATA / f"coach_ratings_{label}.csv", encoding="utf-8") as fh:
            pub = {r["coach"]: r for r in csv.DictReader(fh)}
        hist = json.loads((H.OUT / f"{label}_all.json").read_text(encoding="utf-8"))
        last = hist[max(hist, key=int)]
        reg = [p for p, r in pub.items() if int(r["games"]) >= 100 and p in last]
        gap = max(abs(float(LR.rating(last[p][0])) - float(pub[p]["win_chance_vs_average"])) for p in reg)
        check(gap < 0.2, f"latest history against published Ratings: largest gap {gap:.3f} points")
        rows = data[label]
        fit = H.Fit(name, "classic", at, sets)
        r = [x for x in rows if x["classic"] and x["start_rating"] is not None and not x["small"]][-1]
        c = Counter()
        for g in fit.games:
            if g["league"] == r["league"]:
                c[g["hp"]] += 1
                c[g["ap"]] += 1
        field = [p for p, n in c.items() if n >= LR.MIN_GAMES]
        val = fit.as_of(r["start"])
        again = float(np.mean(LR.rating([val[p][0] for p in field])))
        check(abs(again - r["start_rating"]) < 0.01, f"a recent Classic league recounted: {again:.2f}, published {r['start_rating']:.2f}")
        before = fit.y.copy()
        fit.y = fit.y * np.where(fit.days >= r["start"], -1, 1)
        moved = fit.as_of(r["start"])
        fit.y = before
        check(max(abs(val[p][0] - moved[p][0]) for p in field) == 0, "\"at the start\" doesn't use the league's own or later games")
        groups = {}
        for x in rows:
            if x["classic"] and x["level"] and not x["small"]:
                groups.setdefault(x["level"], []).append(x["scale_rating"])
        means = [np.mean(groups[k]) for k in ("A", "B", "C") if k in groups]
        check(means == sorted(means, reverse=True), "Classic levels run tough to easy: " + ", ".join(f"{m:.1f}" for m in means))


def reports():
    print("Coach reports")
    def parts(x):
        return [0, 0, 0] if x == "—" else [int(v) for v in x.split("-")] + [0] * (3 - len(x.split("-")))
    for label, title, _, at in SYSTEMS:
        files = glob.glob(str(C.DATA / "coach_guides" / "reports" / label / "*.md"))
        with open(C.DATA / f"coach_ratings_{label}.csv", encoding="utf-8") as fh:
            big = sum(1 for r in csv.DictReader(fh) if int(r["games"]) >= 100)
        check(len(files) == big, f"{title}: {len(files)} reports for {big} coaches with 100+ games")
        wrong = odd = 0
        means, sizes = [], []
        for f in files:
            t = open(f, encoding="utf-8").read()
            odd += any(s in t for s in ("| nan", " nan%", "ranks under 100", "— (—)"))
            head = re.search(r"\| Rating \| Rank.*?\n\| ---.*?\n\| (.*?) \|\n", t, re.S).group(1).split(" | ")
            total = [a + b for a, b in zip(parts(head[3]), parts(head[5]))]
            sec = t[t.index("## Rating over time"):t.index("## League families")]
            years = [0, 0, 0]
            for line in sec.splitlines():
                c = [x.strip() for x in line.strip("|").split("|")]
                if len(c) == 8 and re.fullmatch(r"\d{4}", c[0]):
                    for cell in (c[2], c[4]):
                        years = [a + b for a, b in zip(years, parts(cell))]
            wrong += years != total
            m = re.search(r"\*\*Teams with 15\+ games\*\*(.*?)\*\*Classic leagues", t, re.S)
            for line in (m.group(1).splitlines() if m else ()):
                c = [x.strip() for x in line.strip("|").split("|")]
                if len(c) == 8 and re.fullmatch(r"[A-Z]{2,3}", c[0]):
                    means.append(float(c[7]))
                    sizes.append(sum(sum(parts(r)[:2]) for r in (c[1], c[3])))
        check(not wrong, f"{title}: years add up to the record in every report ({wrong} don't)")
        check(not odd, f"{title}: no broken values or awkward wording ({odd} reports)")
        avg = float(np.average(means, weights=sizes))
        check(abs(avg) < 1.5, f"{title}: Above averages about zero across coaches ({avg:+.2f})")


def main():
    anchors()
    privacy()
    elo_rule()
    team_guides()
    history_and_leagues()
    reports()
    print(f"\n{len(problems)} problems" + (": " + "; ".join(problems) if problems else ""))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
