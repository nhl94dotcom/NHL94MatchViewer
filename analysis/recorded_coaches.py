"""Each recorded game's two coaches' strengths (2026-11-11, for a bot that plays as an expert does: the strong
coaches' side of recorded games). A recorded game (Documents\\NHL94 Viewer matches/*.summary.json: date, team
abbreviations, score) is matched to the league database (%USERPROFILE%\\NHL94_League_Data\\All_Games_GENS.csv or
_SNES.csv) by the teams, the final score and the date (the same day or the next, a game near midnight), and each side's
coach to coach_ratings_<SYSTEM>.csv's win_chance_vs_average (the chance against an average coach, %). Names stay in
memory: the module gives ratings only, and the command prints counts.

ratings(system) -> {summary stem: [home rating or None, away rating or None]}
python analysis/recorded_coaches.py [genesis|snes]   -> how many games matched, the ratings' spread"""
import csv
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

PEOPLE = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents" / "NHL94 Viewer")) / "matches"
DATA = Path.home() / "NHL94_League_Data"


def ratings(system="genesis"):
    tag = "GENS" if system == "genesis" else "SNES"
    rate = {}
    with open(DATA / f"coach_ratings_{'GENESIS' if system == 'genesis' else 'SNES'}.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rate[r["coach"].strip().lower()] = float(r["win_chance_vs_average"])
    games = {}
    with open(DATA / f"All_Games_{tag}.csv", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            try:
                d = date.fromisoformat("-".join(f"{int(x):02d}" for x in r["DateTime"].split()[0].split("-")))
                key = (r["HomeTeamAbbrev"].upper(), r["AwayTeamAbbrev"].upper(), int(r["HomeScore"]), int(r["AwayScore"]))
            except (ValueError, KeyError):
                continue
            games.setdefault(key, []).append((d, r["HomePlayer"].strip().lower(), r["AwayPlayer"].strip().lower()))
    out = {}
    for f in sorted(PEOPLE.glob("*.summary.json")):
        s = json.loads(f.read_text())
        if s.get("system") != system:
            continue
        try:
            d = date.fromisoformat(s["date"][:10])
            key = (s["abbr"][0].upper(), s["abbr"][1].upper(), int(s["score"][0]), int(s["score"][1]))
        except (KeyError, ValueError, TypeError, IndexError):
            continue
        hits = [g for g in games.get(key, []) if g[0] in (d, d + timedelta(days=1))]
        if len(hits) == 1:
            _, h, a = hits[0]
            out[f.name.replace(".summary.json", "")] = [rate.get(h), rate.get(a)]
    return out


def main():
    system = sys.argv[1] if len(sys.argv) > 1 else "genesis"
    r = ratings(system)
    total = sum(1 for f in PEOPLE.glob("*.summary.json") if json.loads(f.read_text()).get("system") == system)
    vals = sorted(v for pair in r.values() for v in pair if v is not None)
    print(f"{system}: {len(r)} of {total} recorded games matched; {len(vals)} rated sides")
    if vals:
        q = lambda p: vals[int(p * (len(vals) - 1))]
        print(f"ratings (win chance against an average coach, %): min {vals[0]}, quartiles {q(.25)} / {q(.5)} / {q(.75)}, max {vals[-1]}")
        print("sides rated 75+:", sum(v >= 75 for v in vals), " 80+:", sum(v >= 80 for v in vals))


if __name__ == "__main__":
    main()
