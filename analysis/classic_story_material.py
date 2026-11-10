"""Everything for writing a league's season story in one print (2026-11-10): the league report's brief, standings,
groups, notable games and good words; classic_season_extras' best games, rivalries, home / away and ratings; the
top six's records week by week (W-L, and ties when there are any) with their first and last game days; shutouts by goalie; the most body checks and the
top scorers. Names real people: prints only, to the terminal.

python analysis/classic_story_material.py LEAGUE"""
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classic_season_report as S  # noqa: E402


def section(text, start, stop):
    out, on = [], False
    for line in text.splitlines():
        if line.startswith(start):
            on = True
        elif on and stop and line.startswith(stop):
            break
        if on:
            out.append(line[:420])
    return out


def main():
    league = sys.argv[1]
    rep = (S.OUT / f"{league}_league.md").read_text(encoding="utf-8")
    for start, stop in (("## The season in brief", "## League numbers"), ("## Standings", "Ordered"),
                        ("## The groups", "## Every coach"), ("Most body checks", None), ("## Notable games", None)):
        print("\n".join(section(rep, start, stop)[:60]))
        if start == "Most body checks":
            print("\n".join(section(rep, "## Skaters", "Most body")[:7]))
    subprocess.run([sys.executable, str(Path(__file__).with_name("classic_season_extras.py")), league])
    system, games = S.load(league)
    per = defaultdict(list)
    for r in games:
        for g in S.sides(r):
            per[g["coach"]].append(g)
    first = date.fromisoformat(min(r["DateTime"] for r in games)[:10])
    last = date.fromisoformat(max(r["DateTime"] for r in games)[:10])
    weeks = [first + timedelta(days=7 * k + 6) for k in range((last - first).days // 7 + 1)]
    pct = lambda c: sum(g["us"]["Score"] > g["them"]["Score"] for g in per[c]) / len(per[c])
    print("== weeks ending", [w.isoformat()[5:] for w in weeks])
    for c in sorted(per, key=pct, reverse=True)[:6]:
        line = []
        for wk in weeks:
            gs = [g for g in per[c] if g["when"][:10] <= wk.isoformat()]
            wins = sum(g["us"]["Score"] > g["them"]["Score"] for g in gs)
            losses = sum(g["us"]["Score"] < g["them"]["Score"] for g in gs)
            ties = len(gs) - wins - losses  # a tie is its own column, not a loss (review 2026-11-10)
            line.append(f"{wins}-{losses}" + (f"-{ties}" if ties else ""))
        gs = sorted(per[c], key=lambda g: g["when"])
        print(f"  {c[:16]:16s}", " ".join(x.rjust(6) for x in line), "first", gs[0]["when"][:10], "last", gs[-1]["when"][:10])
    sh = Counter()
    for c, gs in per.items():
        for g in gs:
            if g["them"]["Score"] == 0 and not S.is_copy(g):
                for q in g["us"]["Goalies"]:
                    sh[(q[1], c)] += 1
    print("== shutouts by goalie:", sh.most_common(6))
    copies = [r for r in games if r["_copy"]]
    print(f"== copied rows ({len(copies)}: results count, no single-game claims):", "; ".join(
        f"{r['HomePlayer']} {r['HomeScore']}-{r['AwayScore']} {r['AwayPlayer']} {r['DateTime'][:10]}" for r in copies))


if __name__ == "__main__":
    main()
