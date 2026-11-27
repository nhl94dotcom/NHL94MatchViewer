"""Where a win comes from in the recorded people's games, with the shot quality the league databases can't see
(2026-11-26, stage 4 of the "why people win" plan; docs/WHAT_WINS.md "The leagues" for stages 1-3).

The recorded games (the season summaries: finished, recorded from the start, a person on both sides, no bot) have
expected goals. Each decided game's margin, for the winner, split exactly into four parts:
    more attempts        (his attempts, blocked too, - the loser's) x the games' mean xG per attempt
    better chances       his xG - the loser's xG, less the part above (the xG each attempt was worth)
    finishing            his goals - his xG
    keeping them out     the loser's xG - the loser's goals (on the Genesis the person plays goal; on the SNES the
                         computer does, and the part is the shots he let the other take as much as the saves)
(goals here are the goals from unblocked attempts, as the xG; the few others are left aside). Printed: each part's
mean for the winner, how often it favoured him, and how much of the margin's spread across games each part carries;
then what goes with better chances (xG per attempt) across team-games: high-danger, rush, one-timer, rebound,
breakaway and odd-man shares, and giveaways that led to a shot against; and how well each part repeats for the same
pad's team across a series (split-half), the test of skill against chance.

python analysis/recorded_what_wins.py [genesis|snes]"""
import ast
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")


def val(v):
    if isinstance(v, str) and v[:1] in "[{TF0123456789-":
        try:
            return ast.literal_eval(v)
        except (ValueError, SyntaxError):
            return v
    return v


def games(system):
    s = (HOME / "matches" / "season.js").read_text(encoding="utf-8")
    d = json.loads(s[s.index("{"):s.rindex("}") + 1])
    out = []
    for g in d["games"]:
        if g["system"] != system or g.get("bot"):
            continue
        if val(g.get("finished")) is not True or val(g.get("fromStart")) is not True:
            continue
        hum = val(g.get("humans"))
        if not (isinstance(hum, list) and all(hum)):
            continue
        teams = val(g["teams"])
        if not all("xg" in t for t in teams):
            continue
        out.append(dict(name=g["name"], abbr=val(g["abbr"]), teams=teams))
    return out


def parts(t, o, q):
    """The four parts for team t against o; q the mean xG per unblocked attempt."""
    xf, gf, xa, ga = t["xg"]
    af = t["att"] - (t.get("hd") or [0])[0] * 0                       # attempts (unblocked share unknown: att as a whole)
    aa = o["att"]
    vol = (af - aa) * q
    qual = (xf - xa) - vol
    return dict(vol=vol, qual=qual, fin=gf - xf, keep=xa - ga, margin=gf - ga, xgd=xf - xa)


def main():
    system = sys.argv[1] if len(sys.argv) > 1 else "genesis"
    G = games(system)
    q = sum(t["xg"][0] for g in G for t in g["teams"]) / max(1, sum(t["att"] for g in G for t in g["teams"]))
    print(f"{system}: {len(G)} recorded games between two people with xG; mean xG per attempt {q:.3f}")
    rows = []
    for g in G:
        a, b = g["teams"]
        pa = parts(a, b, q)
        if pa["margin"] == 0:
            continue
        w = pa if pa["margin"] > 0 else {k: -v for k, v in pa.items()}
        rows.append(w)
    n = len(rows)
    print(f"decided games {n}; the winner's margin (goals from unblocked attempts) {np.mean([r['margin'] for r in rows]):+.2f} a game, split:")
    names = dict(vol="more attempts", qual="better chances (xG per attempt)", fin="finishing (goals - xG)", keep="keeping them out (xG against - goals against)")
    M = np.array([r["margin"] for r in rows])
    for k, lab in names.items():
        v = np.array([r[k] for r in rows])
        print(f"  {lab:46s} mean {v.mean():+.2f}  ({100 * v.mean() / M.mean():3.0f}% of the margin)  favoured the winner in {100 * np.mean(v > 0):.0f}% of games")
    xgw = np.mean([r["xgd"] > 0 for r in rows])
    print(f"  the winner had more xG in {100 * xgw:.0f}% of games; so {100 * (1 - xgw):.0f}% were won by the side with less xG")
    # over all games (both signs), how much of the margin's spread each part carries (covariance share)
    allp = []
    for g in G:
        a, b = g["teams"]
        allp.append(parts(a, b, q))
    Mv = np.array([p["margin"] for p in allp])
    print("  share of the margin's spread across games each part carries (covariance with the margin / its variance):")
    for k, lab in names.items():
        v = np.array([p[k] for p in allp])
        print(f"    {lab:46s} {100 * np.cov(v, Mv)[0, 1] / np.var(Mv, ddof=1):4.0f}%")
    # what goes with better chances: across team-games, xG per attempt against each stat (share of the team's attempts)
    T = []
    for g in G:
        for i, t in enumerate(g["teams"]):
            o = g["teams"][1 - i]
            if t["att"] < 5:
                continue
            att = t["att"]
            T.append(dict(q=t["xg"][0] / att, hd=t["hd"][0] / att, rush=t["origin"][0] / att, zone=t["origin"][1] / att,
                          ot=t.get("oneTimerTried", 0) / att, reb=t["reb"][0] / att, brk=t.get("breakTried", 0) / att,
                          odd=t["oddMan"][0], given=o["toShot"][0], assisted=t.get("assisted", 0) / att,
                          passes=t.get("passMade", 0), entries_shot=t["entries"][4] / max(1, t["entries"][0])))
    print(f"\nwhat goes with better chances ({len(T)} team-games; rank correlation with xG per attempt):")
    qv = np.array([r["q"] for r in T])

    def sp(x, y):
        rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
        return float(np.corrcoef(rx, ry)[0, 1])
    lab = dict(hd="high-danger share of attempts", ot="one-timers tried a attempt", brk="breakaways a attempt", rush="rush share of attempts",
               zone="sustained-pressure share", reb="rebound share", assisted="share off a pass (assisted)", odd="odd-man rushes",
               given="the other's giveaways that led to a shot", passes="passes completed", entries_shot="entries that led to an attempt (share)")
    for k in sorted(lab, key=lambda k: -abs(sp(np.array([r[k] for r in T]), qv))):
        print(f"  {lab[k]:44s} {sp(np.array([r[k] for r in T]), qv):+.2f}")
    # repeat for the same team across games (split-half over the pad team's games in each pair of teams)
    by = defaultdict(list)
    for g in G:
        key = tuple(sorted(g["abbr"]))
        a, b = g["teams"]
        first = g["abbr"].index(key[0])
        p = parts(g["teams"][first], g["teams"][1 - first], q)
        by[key].append(p)
    pairs = [v for v in by.values() if len(v) >= 4]
    print(f"\nthe same two teams across a series ({len(pairs)} series of 4+ games, {sum(len(v) for v in pairs)} games): odd against even games, "
          f"correlation of each part's mean (1 skill, 0 chance; few series, so rough):")
    for k, lab2 in list(names.items()) + [("margin", "the margin itself")]:
        a = np.array([np.mean([p[k] for p in v[0::2]]) for v in pairs])
        b = np.array([np.mean([p[k] for p in v[1::2]]) for v in pairs])
        r = float(np.corrcoef(a, b)[0, 1]) if len(pairs) > 2 else float("nan")
        print(f"  {lab2:46s} {r:+.2f}")


if __name__ == "__main__":
    main()
