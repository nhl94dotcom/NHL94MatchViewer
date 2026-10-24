"""What goes with winning in the video archive (2026-10-24): every Genesis game video_game.py found (exhibitions
included: the user), whole games only (7-14 minutes of video, not tied: a tie is a game cut off or an overtime split
off). What the video can say per team: goals, time with the play in its attacking zone (the camera's position; only
while the clock runs), zone entries, goals off the rush (within RUSH_S of the entry) or after time in the zone, when
each goal went in. For each measure, how often the team with more of it won, and how well it lines up with the goal
difference; then the leads (scoring first, leading after 1 and 2 periods). No measure is per person: the video shows
the teams only. Writes reports/video_wins.md (git-ignored).
python analysis/video/video_wins.py <work folder>"""
import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "reports" / "video_wins.md"


def load(work):
    games = []
    for f in sorted(Path(work).glob("*.games.json")):
        for g in json.load(open(f)):
            mins = (g["end_t"] - g["start_t"]) / 60
            if 7 <= mins <= 14 and g["away"] != g["home"] and sum(g["zone_s"].values()) > 0:
                g["file"] = f.name
                games.append(g)
    return games


def sides(g):
    """Both teams' rows, winner first: (winner, loser) of dicts of measures."""
    rows = {}
    for s, o in (("home", "away"), ("away", "home")):
        zs = g["zone_s"][s] + g["zone_s"][o]
        rows[s] = {"goals": g[s], "zone share": g["zone_s"][s] / zs if zs else 0.5, "zone s": g["zone_s"][s],
                   "entries": g["entries"][s], "rush goals": g["goals_rush"][s], "zone goals": g["goals_zone"][s],
                   "goals per zone minute": g[s] / (g["zone_s"][s] / 60) if g["zone_s"][s] else 0,
                   "goals per entry": g[s] / g["entries"][s] if g["entries"][s] else 0,
                   "home": s == "home"}
    w = "home" if g["home"] > g["away"] else "away"
    return rows[w], rows["away" if w == "home" else "home"]


def leads(g):
    """Who led: the first goal's team, and the leader at the end of periods 1 and 2 (None when level)."""
    first = g["goals"][0]["team"] if g["goals"] else None
    out = {"first": first}
    for p in (1, 2):
        h = sum(1 for x in g["goals"] if x["team"] == "home" and x["period"] <= p)
        a = sum(1 for x in g["goals"] if x["team"] == "away" and x["period"] <= p)
        out[p] = "home" if h > a else "away" if a > h else None
    return out


def main(work):
    games = load(work)
    L = [f"# What goes with winning: {len(games)} whole Genesis games from the video archive", "",
         "From the video alone (the score box and the camera). Zone time is the play's position by the camera, while "
         "the clock runs; an entry is the play crossing the blue line after a second outside and staying a second.", ""]
    pairs = [sides(g) for g in games]
    L += ["| Measure | Winner's average | Loser's average | Team with more won | Games with a difference |",
          "|---|---|---|---|---|"]
    for m in ("zone share", "zone s", "entries", "rush goals", "zone goals", "goals per zone minute", "goals per entry"):
        w = np.array([p[0][m] for p in pairs], float)
        lo = np.array([p[1][m] for p in pairs], float)
        diff = w != lo
        won = (w > lo)[diff].mean() if diff.any() else float("nan")
        fmt = "{:.2f}" if m in ("zone share", "goals per zone minute", "goals per entry") else "{:.1f}"
        L.append(f"| {m} | {fmt.format(w.mean())} | {fmt.format(lo.mean())} | {won:.0%} | {diff.sum()} |")
    home_wins = np.mean([p[0]["home"] for p in pairs])
    L += ["", f"Home team won {home_wins:.0%}.", ""]

    # how much of the goal difference each lines up with (one row per game, home minus away)
    gd = np.array([g["home"] - g["away"] for g in games], float)
    cols = {"zone time (s)": [g["zone_s"]["home"] - g["zone_s"]["away"] for g in games],
            "entries": [g["entries"]["home"] - g["entries"]["away"] for g in games]}
    L += ["Correlation with the goal difference (home minus away, per game):", ""]
    for k, v in cols.items():
        L.append(f"- {k}: {np.corrcoef(np.array(v, float), gd)[0, 1]:+.2f}")

    # finishing vs territory: which one goes with the result more
    fin_w = sum(1 for w, lo in pairs if w["goals per zone minute"] > lo["goals per zone minute"])
    ter_w = sum(1 for w, lo in pairs if w["zone s"] > lo["zone s"])
    both = sum(1 for w, lo in pairs if w["zone s"] < lo["zone s"] and w["goals per zone minute"] > lo["goals per zone minute"])
    L += ["", f"Won with less zone time but more goals per zone minute (out-finished the other side): {both} of "
          f"{len(pairs)}. The winner had more zone time in {ter_w} and finished better in {fin_w}.", ""]

    # rush vs zone goals overall
    rush = sum(g["goals_rush"]["home"] + g["goals_rush"]["away"] for g in games)
    zone = sum(g["goals_zone"]["home"] + g["goals_zone"]["away"] for g in games)
    unk = sum(g["goals_unknown"]["home"] + g["goals_unknown"]["away"] for g in games)
    L += [f"Goals: {rush} off the rush (within 5 s of entering the zone), {zone} after time in the zone, {unk} "
          f"not timed ({rush / max(1, rush + zone):.0%} of the timed goals off the rush).", ""]

    # leads
    first = [lead for lead in (leads(g) for g in games)]
    rows = []
    for name, k in (("Scored first", "first"), ("Led after period 1", 1), ("Led after period 2", 2)):
        n = [(lv[k], "home" if g["home"] > g["away"] else "away") for lv, g in zip(first, games) if lv[k]]
        won = sum(1 for a, b in n if a == b)
        rows.append(f"| {name} | {won} of {len(n)} | {won / max(1, len(n)):.0%} |")
    L += ["| The leading team | Won | |", "|---|---|---|"] + rows + [""]

    # comebacks by deficit after 2
    L += ["Margin after 2 periods and how often the trailing team came back to win:", ""]
    by = {}
    for g in games:
        h = sum(1 for x in g["goals"] if x["team"] == "home" and x["period"] <= 2)
        a = sum(1 for x in g["goals"] if x["team"] == "away" and x["period"] <= 2)
        if h == a:
            continue
        lead = "home" if h > a else "away"
        win = "home" if g["home"] > g["away"] else "away"
        by.setdefault(abs(h - a), [0, 0])
        by[abs(h - a)][0] += 1
        by[abs(h - a)][1] += win != lead
    for m in sorted(by):
        L.append(f"- down {m}: {by[m][1]} of {by[m][0]} came back")

    # goals by period
    per = {p: sum(1 for g in games for x in g["goals"] if x["period"] == p) for p in (1, 2, 3, 4)}
    L += ["", "Goals by period: " + ", ".join(f"{p}: {n}" for p, n in per.items()), ""]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1])
