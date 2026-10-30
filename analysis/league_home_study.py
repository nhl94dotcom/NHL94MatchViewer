"""Home and away, and up and down the screen, in the leagues' own results (2026-10-30). Reads the league result
databases the user keeps outside the repository (%USERPROFILE%\\NHL94_League_Data\\All_Games_GENS.csv, All_Games_SNES.csv:
one row per game, both players, team, goals, shots, goals and shots by period, faceoff wins; simulated games left out)
and prints aggregates only (no player names):
- the home edge: home wins, goals, shots and faceoff wins per game;
- the same player at home and away (players with 20+ games each way), so who tends to be Home can't make the edge;
- Home's share of shots and goals by period: Home attacks up the screen in periods 1 and 3 and down in period 2, so a
  period-2 dip would be the screen direction;
- the team's home bonus in the retail ROM (GENESIS_MECHANICS 13.6), for what it's worth: league ROMs may edit it.
python analysis/league_home_study.py"""
import csv
import math
from collections import defaultdict
from pathlib import Path

DATA = Path.home() / "NHL94_League_Data"
HOME_BONUS_2 = {"BOS", "BUF", "CHI", "MTL", "PHI", "PIT", "STL"}     # retail nhl94.bin home +2
HOME_BONUS_0 = {"CGY", "DAL", "DET", "HFD", "NYI", "QUE", "TB"}      # retail home 0
MIN_GAMES = 20


def num(v):
    try:
        return float(v)
    except ValueError:
        return None


def share(a, b):
    """a / (a + b) with its standard error."""
    n = a + b
    p = a / n if n else 0
    return p, math.sqrt(p * (1 - p) / n) if n else 0


def study(path, label):
    games = []
    csv.field_size_limit(10 ** 9)
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") == "1":
                continue
            g = {k: num(r[k]) for k in r if k.startswith(("Home", "Away")) and k[4:] in (
                "Score", "Shots", "FaceoffWins", "ShotsP1", "ShotsP2", "ShotsP3", "GoalsP1", "GoalsP2", "GoalsP3")
                 or k[4:] in ("Score", "Shots", "FaceoffWins", "ShotsP1", "ShotsP2", "ShotsP3", "GoalsP1", "GoalsP2",
                              "GoalsP3")}
            if None in (g.get("HomeScore"), g.get("AwayScore"), g.get("HomeShots"), g.get("AwayShots")):
                continue
            g["hp"], g["ap"] = r["HomePlayer"].strip().lower(), r["AwayPlayer"].strip().lower()
            g["ht"] = r["HomeTeamAbbrev"].strip()
            if not g["hp"] or not g["ap"] or g["hp"] == g["ap"]:
                continue
            games.append(g)
    n = len(games)
    print(f"\n==================== {label}: {n} games (simulated ones left out)")
    hw = sum(g["HomeScore"] > g["AwayScore"] for g in games)
    aw = sum(g["HomeScore"] < g["AwayScore"] for g in games)
    p, se = share(hw, aw)
    print(f"Home won {hw}, lost {aw}, tied {n - hw - aw}: {100 * p:.1f}% of decided games (+/- {100 * 1.96 * se:.1f})")
    for k in ("Score", "Shots", "FaceoffWins"):
        h = sum(g["Home" + k] or 0 for g in games) / n
        a = sum(g["Away" + k] or 0 for g in games) / n
        print(f"  {k:12}: home {h:.2f} a game, away {a:.2f}  (home / away {h / a:.3f})")
    sh = sum(g["HomeScore"] for g in games) / sum(g["HomeShots"] for g in games if g["HomeShots"])
    sa = sum(g["AwayScore"] for g in games) / sum(g["AwayShots"] for g in games if g["AwayShots"])
    print(f"  goals per shot: home {100 * sh:.1f}%, away {100 * sa:.1f}%")

    # the same player at home and away
    pl = defaultdict(lambda: {True: [0, 0, 0, 0], False: [0, 0, 0, 0]})   # n, shots for, goals for, wins
    for g in games:
        for home, who in ((True, g["hp"]), (False, g["ap"])):
            me, op = ("Home", "Away") if home else ("Away", "Home")
            s = pl[who][home]
            s[0] += 1
            s[1] += g[me + "Shots"]
            s[2] += g[me + "Score"]
            s[3] += g[me + "Score"] > g[op + "Score"]
    both = [d for d in pl.values() if d[True][0] >= MIN_GAMES and d[False][0] >= MIN_GAMES]
    for i, name in ((1, "shots for"), (2, "goals for"), (3, "win rate")):
        diffs = [d[True][i] / d[True][0] - d[False][i] / d[False][0] for d in both]
        m = sum(diffs) / len(diffs)
        sd = math.sqrt(sum((x - m) ** 2 for x in diffs) / (len(diffs) - 1))
        more = sum(x > 0 for x in diffs)
        unit = "%" if i == 3 else " a game"
        f = 100 if i == 3 else 1
        print(f"  same player, home minus away ({len(both)} players with {MIN_GAMES}+ games each way): {name} "
              f"{f * m:+.2f}{unit} (+/- {f * 1.96 * sd / math.sqrt(len(diffs)):.2f}); higher at home for {more} of "
              f"{len(diffs)}")

    # by period: Home attacks up in 1 and 3, down in 2
    print("  Home's share by period (Home goes up the screen in 1 and 3, down in 2):")
    for per in ("P1", "P2", "P3"):
        hs = sum(g["HomeShots" + per] or 0 for g in games)
        as_ = sum(g["AwayShots" + per] or 0 for g in games)
        hg = sum(g["HomeGoals" + per] or 0 for g in games)
        ag = sum(g["AwayGoals" + per] or 0 for g in games)
        ps, ses = share(hs, as_)
        pg, seg = share(hg, ag)
        print(f"    {per}: shots {100 * ps:.1f}% (+/- {100 * 1.96 * ses:.1f}), goals {100 * pg:.1f}% (+/- {100 * 1.96 * seg:.1f})")

    # the retail home bonus (league ROMs may differ)
    for lab, teams in (("home +2 in the retail ROM", HOME_BONUS_2), ("home 0 in the retail ROM", HOME_BONUS_0)):
        sel = [g for g in games if g["ht"] in teams]
        w = sum(g["HomeScore"] > g["AwayScore"] for g in sel)
        l = sum(g["HomeScore"] < g["AwayScore"] for g in sel)
        p, se = share(w, l)
        shots = sum(g["HomeShots"] for g in sel) / max(1, sum(g["AwayShots"] for g in sel))
        print(f"  home teams {lab}: {len(sel)} games, home won {100 * p:.1f}% (+/- {100 * 1.96 * se:.1f}), "
              f"home / away shots {shots:.3f}")


def main():
    study(DATA / "All_Games_GENS.csv", "GENESIS")
    study(DATA / "All_Games_SNES.csv", "SNES")


if __name__ == "__main__":
    main()
