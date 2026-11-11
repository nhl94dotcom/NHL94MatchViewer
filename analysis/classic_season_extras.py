"""Extra material for a league's season story (2026-11-10, the user: awards, best single games, rivalries, home and
away, looking ahead). Names real people, so it prints only, to the terminal: nothing is written, and nothing named
goes in the repository.

From the league database (as classic_season_report.py) and coach_history's ratings (Classic for a Classic league, all-leagues for any other):
- best single games: the most goals and points by one player in a game, shutouts, the most shots by a team;
- rivalries: each pair of coaches who met 3+ times, the closest series by goal difference, the most lopsided;
- home and away: every coach's record at home and away, and the biggest gap;
- looking ahead: each coach's rating the day before the league's first game and on the last day of the
  history (after this season; it says so if the history stops before the league's last game day; run late, it
  includes any later games too), as a win chance against the average coach, and the change.

python analysis/classic_season_extras.py LEAGUE [LEVEL]   (LEVEL: A, B ... of a two-level league such as SNES-AB)"""
import math
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classic_season_report as S  # noqa: E402


def main():
    league = sys.argv[1]
    level = sys.argv[2].upper() if len(sys.argv) > 2 else None  # one level of a two-level league (S.LEVELS)
    system, games = S.load(league)
    lv = S.LEVELS.get(league, {})
    if lv and not level:
        raise SystemExit(f"{league} holds levels {', '.join(sorted(set(lv.values())))}: name one")
    per = defaultdict(list)
    for r in games:
        for g in S.sides(r):
            per[g["coach"]].append(g)
    gp = {c: len(v) for c, v in per.items()}
    keep = {c for c in per if gp[c] >= max(5, max(gp.values()) / 4)}
    if level:
        # the level's coaches (their games against the other level included); few-game coaches in it still give
        # single games
        per = {c: v for c, v in per.items() if lv.get(c) == level}
        keep = {c for c in keep if c in per}
    res = lambda g: "W" if g["us"]["Score"] > g["them"]["Score"] else "L" if g["us"]["Score"] < g["them"]["Score"] else "T"

    print("== Best single games")
    best = []
    for c, gs in per.items():
        for g in gs:
            for p in g["us"]["Players"]:
                best.append((p[3], p[5], p[1], c, g["opp"], g["when"][:10], int(g["us"]["Score"]), int(g["them"]["Score"])))
    for lab, key in (("goals", lambda x: (x[0], x[1])), ("points", lambda x: (x[1], x[0]))):
        top = sorted(best, key=key, reverse=True)[:4]
        print(f"  most {lab} by one player:", "; ".join(f"{x[2]} ({x[3]}) {x[0]} G {x[1]} P vs {x[4]} {x[6]}-{x[7]} {x[5]}" for x in top))
    shut = [(c, g["opp"], g["when"][:10], int(g["us"]["Score"]), [q[1] for q in g["us"]["Goalies"]]) for c, gs in per.items()
            for g in gs if g["them"]["Score"] == 0]
    print(f"  shutouts ({len(shut)}):", "; ".join(f"{c} {s}-0 vs {o} ({', '.join(gl)}) {d}" for c, o, d, s, gl in shut))
    shots = sorted(((int(g["us"]["Shots"]), c, g["opp"], g["when"][:10]) for c, gs in per.items() for g in gs), reverse=True)[:3]
    print("  most shots by a team:", "; ".join(f"{c} {n} vs {o} {d}" for n, c, o, d in shots))

    print("== Rivalries (3+ meetings)")
    pairs = {}
    for c, gs in per.items():
        for g in gs:
            o = g["opp"]
            if c < o and c in keep and o in keep:
                v = pairs.setdefault((c, o), Counter())
                v["GP"] += 1
                v[res(g)] += 1
                v["GF"] += g["us"]["Score"]
                v["GA"] += g["them"]["Score"]
    pr = [(k, v) for k, v in pairs.items() if v["GP"] >= 3]
    close = sorted(pr, key=lambda kv: (abs(kv[1]["W"] - kv[1]["L"]), abs(kv[1]["GF"] - kv[1]["GA"]), -kv[1]["GP"]))[:4]
    lop = sorted(pr, key=lambda kv: -abs(kv[1]["W"] - kv[1]["L"]) * 100 - abs(kv[1]["GF"] - kv[1]["GA"]))[:4]
    fmt = lambda kv: f"{kv[0][0]} {kv[1]['W']}-{kv[1]['L']} {kv[0][1]} (goals {int(kv[1]['GF'])}-{int(kv[1]['GA'])})"
    print("  closest:", "; ".join(fmt(kv) for kv in close))
    print("  most lopsided:", "; ".join(fmt(kv) for kv in lop))

    print("== Home and away")
    ha = {}
    for c in sorted(keep, key=lambda c: -sum(res(g) == "W" for g in per[c]) / gp[c]):
        h = Counter(res(g) for g in per[c] if g["home"])
        a = Counter(res(g) for g in per[c] if not g["home"])
        hp, ap = h["W"] / max(1, h["W"] + h["L"]), a["W"] / max(1, a["W"] + a["L"])
        ha[c] = hp - ap
        print(f"  {c}: home {h['W']}-{h['L']} ({hp:.3f}), away {a['W']}-{a['L']} ({ap:.3f})")
    big = max(ha, key=lambda c: abs(ha[c]))
    print(f"  biggest gap: {big} ({ha[big]:+.3f})")

    print(f"== Looking ahead ({'Classic' if S.is_classic(league) else 'all-leagues'} rating as a win chance against the average coach, before the season and after the league)")
    first = S.season_start(league)  # pre-season: before the season's first game on the system
    before, day0 = S.ratings(system, first, league)
    # after: the first rating after the league's last game (an old league's change, not one to today: 2026-11-10)
    last = date.fromisoformat(max(r["DateTime"] for r in games)[:10])
    after, day1 = S.ratings_after(system, date.fromordinal(last.toordinal() + 1), league)
    sig = lambda x: 1 / (1 + math.exp(-x))
    rows = []
    for c in keep:
        b, a = before.get(S.base_name(c).lower()), after.get(S.base_name(c).lower())
        if b is not None and a is not None:
            rows.append((sig(a) - sig(b), c, sig(b), sig(a)))
    print(f"  ({day0} -> {day1})" + ("" if day1 > last else
          f"  NOTE: the latest rating ({day1}) is from before the league's last game day ({last}): rebuild coach_history"))
    for d, c, b, a in sorted(rows, reverse=True):
        print(f"  {c}: {100 * b:.0f}% -> {100 * a:.0f}% ({100 * d:+.0f})")
    new = [c for c in keep if S.newcomer(system, first, c, league)]
    if new:
        print(f"  no rating before the season ({S.first_league(league)}):", ", ".join(new))


if __name__ == "__main__":
    main()
