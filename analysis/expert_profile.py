"""What expert coaches' teams do in a game, from the league database's own counts (2026-11-11, the user: a bot that
plays as an expert human does). Every league game (%USERPROFILE%\\NHL94_League_Data\\All_Games_GENS.csv or _SNES.csv),
each side with its coach's strength (coach_ratings_<SYSTEM>.csv, win chance against an average coach, %), grouped:
90+ / 85-90 / 80-85 / 70-80 / 60-70 / under 60. Per side and game, the game's own counts: goals, shots, shooting %,
one-timer tries and goals, breakaway tries, checks, penalty minutes, attack-zone time, passes tried and completed,
faceoff wins, power-play tries; the mean per group (games in regulation, both sides' counts there). With BOT_MATCHES
(bot_record.py's match files) the bot's own counts (the stats snapshot's last row, the same counters) beside them.
Aggregates only; names nobody.

python analysis/expert_profile.py [genesis|snes] [BOT_MATCHES]"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

DATA = Path.home() / "NHL94_League_Data"
BANDS = [(90, 101, "90+"), (85, 90, "85-90"), (80, 85, "80-85"), (70, 80, "70-80"), (60, 70, "60-70"), (0, 60, "under 60")]
FIELDS = [("goals", "Score"), ("shots", "Shots"), ("one-timer tries", "OneTimerTries"), ("one-timer goals", "OneTimerGoals"),
          ("breakaway tries", "BreakTries"), ("checks", "Checks"), ("penalty minutes", "PIM"),
          ("attack zone time (s)", "AttackZoneTime"), ("passes tried", "PassTries"), ("passes completed", "PassComps"),
          ("faceoff wins", "FaceoffWins"), ("power plays", "PPTries")]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def league_rows(system):
    tag = "GENS" if system == "genesis" else "SNES"
    rate = {}
    with open(DATA / f"coach_ratings_{'GENESIS' if system == 'genesis' else 'SNES'}.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rate[r["coach"].strip().lower()] = float(r["win_chance_vs_average"])
    rows = {b[2]: [] for b in BANDS}
    with open(DATA / f"All_Games_{tag}.csv", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            for side, other in (("Home", "Away"), ("Away", "Home")):
                v = rate.get((r.get(f"{side}Player") or "").strip().lower())
                if v is None:
                    continue
                vals = {k: num(r.get(side + f)) for k, f in FIELDS}
                if vals["shots"] is None or vals["goals"] is None:
                    continue
                vals["goals against"] = num(r.get(other + "Score"))
                band = next(b[2] for b in BANDS if b[0] <= v < b[1])
                rows[band].append(vals)
    return rows


def bot_rows(folder):
    """The bot's side (Home) in each bot game: the game's own counts from the match's last stats row."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from export_match import STAT_FIELDS  # noqa: E402
    names = {"goals": "goals", "shots": "shots", "one-timer tries": "oneTimerTried", "one-timer goals": "oneTimerGoals",
             "breakaway tries": "breakTried", "checks": "checks", "penalty minutes": "pim",
             "attack zone time (s)": "attackZone", "passes tried": "passTried", "passes completed": "passMade",
             "faceoff wins": "faceoffs", "power plays": "ppTries"}
    out = []
    for f in sorted(Path(folder).glob("bot_*.js")):
        t = f.read_text(encoding="utf-8")
        m = json.loads(t[t.index("{"):t.rindex("}") + 1])
        last = m["stats"]["home"][-1]
        lastb = m["stats"]["away"][-1]
        row = {k: (last[STAT_FIELDS.index(v)] if v in STAT_FIELDS else None) for k, v in names.items()}
        row["goals against"] = lastb[STAT_FIELDS.index("goals")] if "goals" in STAT_FIELDS else None
        out.append(row)
    return out


def main():
    system = sys.argv[1] if len(sys.argv) > 1 else "genesis"
    rows = league_rows(system)
    bots = bot_rows(sys.argv[2]) if len(sys.argv) > 2 else []
    cols = [b[2] for b in BANDS if rows[b[2]]]
    print(f"{system}: a side's game, by its coach's strength (win chance against an average coach)")
    print("| Measure | " + " | ".join(f"{c} ({len(rows[c])})" for c in cols) + (f" | bot ({len(bots)})" if bots else "") + " |")
    print("|---|" + "---|" * (len(cols) + bool(bots)))
    for k in [f[0] for f in FIELDS] + ["goals against"]:
        cells = []
        for c in cols:
            v = [r[k] for r in rows[c] if r.get(k) is not None]
            cells.append(f"{st.mean(v):.1f}" if v else "-")
        if bots:
            v = [r[k] for r in bots if r.get(k) is not None]
            cells.append(f"{st.mean(v):.1f}" if v else "-")
        print(f"| {k} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
