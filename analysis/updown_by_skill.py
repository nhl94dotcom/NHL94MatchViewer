"""The Down goal lean split by year, by league kind and by the coaches' strength (2026-11-19, the user: the goalie frames
and the penalties explain only a little of the Genesis's 1.031; is the rest the game or the people?). Aggregates only.

The league databases' goal lists, regulation, real games (no sims, two different coaches). Down / Up balanced as in
STUDY_NOTES "goals by strength": home goals in period 2 against periods 1 and 3 (halved), away the other way round, the
two ratios' geometric mean, so the home edge and the periods' own scoring cancel. Even-strength goals (EV) and all.
Coach strength: each coach's Rating (coach_history.Fit, all leagues) as of 1 January of the game's year, from the games
before it; coaches under 100 games by then are "new". Quartiles of the rated coach-games, for the scoring team's coach
(attack) and the conceding team's (defence: who stands the goalie).

python analysis/updown_by_skill.py [GENS|SNES]"""
import ast
import csv
import math
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coach_history as H  # noqa: E402

csv.field_size_limit(10 ** 9)
DATA = Path.home() / "NHL94_League_Data"


def est(c):
    H1, H2, H3 = c[(1, 1)], c[(1, 2)], c[(1, 3)]
    A1, A2, A3 = c[(0, 1)], c[(0, 2)], c[(0, 3)]
    if min(H2, H1 + H3, A2, A1 + A3) < 20:
        return None
    v = math.sqrt(H2 / ((H1 + H3) / 2) * ((A1 + A3) / 2) / A2)
    se = 0.5 * math.sqrt(1 / H2 + 1 / (H1 + H3) + 1 / A2 + 1 / (A1 + A3))
    return v, v * math.exp(-1.96 * se), v * math.exp(1.96 * se), H1 + H2 + H3 + A1 + A2 + A3


def show(label, c):
    r = est(c)
    if r:
        print(f"  {label:34s} n {r[3]:7d}  {r[0]:.3f} ({r[1]:.3f}-{r[2]:.3f})")


def main():
    sysname = sys.argv[1] if len(sys.argv) > 1 else "GENS"
    fname = f"All_Games_{sysname}.csv"
    rows = []
    for r in csv.DictReader(open(DATA / fname, encoding="utf-8", errors="replace")):
        if r.get("sim") == "1":
            continue
        hp, ap = r["HomePlayer"].strip().lower(), r["AwayPlayer"].strip().lower()
        if not hp or not ap or hp == ap:
            continue
        try:
            y, m, d = (int(x) for x in r["DateTime"].split()[0].split("-"))
            gl = {s: ast.literal_eval(r[s + "Goals"] or "[]") for s in ("Home", "Away")}
        except Exception:
            continue
        rows.append((y, hp, ap, r["League"].startswith("Classic"), r["RegOrPlay"], gl))
    sets = H.settings()
    fit = H.Fit(fname, "all", 0 if sysname == "GENS" else 1, sets)
    rating = {y: fit.as_of(date(y, 1, 1).toordinal()) for y in sorted({row[0] for row in rows})}

    def strength(y, p):
        v = rating[y].get(p)
        return v[0] if v and v[1] >= 100 else None

    vals = sorted(s for y, hp, ap, *_ in rows for s in (strength(y, hp), strength(y, ap)) if s is not None)
    cuts = [vals[len(vals) * k // 4] for k in (1, 2, 3)]
    q = lambda s: "new (<100 games)" if s is None else f"Q{1 + sum(s >= c for c in cuts)}"  # noqa: E731
    B = defaultdict(Counter)
    for y, hp, ap, classic, rp, gl in rows:
        sh, sa = strength(y, hp), strength(y, ap)
        for side, h in (("Home", 1), ("Away", 0)):
            att, dfn = (sh, sa) if h else (sa, sh)
            for g in gl[side]:
                per = g[0]
                if per not in (1, 2, 3):
                    continue
                for strn in ("all", "EV") if str(g[-1]) == "EV" else ("all",):
                    k = (h, per)
                    B[(strn, "year", y)][k] += 1
                    B[(strn, "kind", "Classic" if classic else "other leagues")][k] += 1
                    B[(strn, "kind", "playoffs" if rp == "P" else "regular season")][k] += 1
                    B[(strn, "attack", q(att))][k] += 1
                    B[(strn, "defence", q(dfn))][k] += 1
                    if att is not None and dfn is not None:
                        gap = att - dfn
                        B[(strn, "gap", "attacker stronger by 0.5+" if gap >= 0.5 else
                           "defender stronger by 0.5+" if gap <= -0.5 else "within 0.5")][k] += 1
    print(f"{fname}: {len(rows)} games; quartile cuts (log odds) {[round(c, 2) for c in cuts]}")
    for strn in ("EV", "all"):
        print(f"\n{strn} goals, Down / Up (95%)")
        for part in ("kind", "attack", "defence", "gap", "year"):
            print(f" by {part}")
            for key in sorted(k for k in B if k[0] == strn and k[1] == part):
                show(str(key[2]), B[key])


if __name__ == "__main__":
    main()
