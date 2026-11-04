"""The Classic draft guide: docs/DRAFT_GUIDE_CLASSIC.md, which teams and players give more than their reputation (2026-11-04, the user, to hand out). Aggregates only; no coach is named.
Takes strength, Elo adjustment, level and Expected from the "All teams" tables of the team guides, and players from reports/classic_players.json (classic_player_guide.py), so it agrees with both;
run those first. The databases hold no draft order, so demand is estimated: how often a team has been used in the last three years, and Expected (in the Classic drafts the people thought weaker
pick first, so a team that goes early tends to have a low Expected).
python analysis/classic_draft_guide.py"""
import ast
import csv
import json
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from league_player_study import DATA  # noqa: E402

ROOT = HERE.parent
CLASSIC = ("classic_spring", "classic_summer", "classic_fall")
SYSTEMS = (("Genesis", "All_Games_GENS.csv", "TEAM_GUIDE_GENESIS.md", "PLAYER_GUIDE_GENESIS.md"), ("SNES", "All_Games_SNES.csv", "TEAM_GUIDE_SNES.md", "PLAYER_GUIDE_SNES.md"))
RECENT_YEARS = 3
GAP = 4                 # places between value and demand or Ovr for a team to be called out
MIN_SKATER = 150        # games for a skater to be called out


def number(text):
    return float(text.replace("−", "-").replace("*", "").replace("+", "").replace("%", "").replace(",", ""))


def team_table(guide):
    """The team guide's "All teams" rows."""
    text = (ROOT / "docs" / guide).read_text(encoding="utf-8")
    body = text[text.index("## All teams"):]
    body = body[:body.index("\n## 1.")]
    rows = []
    for line in body.splitlines():
        m = re.match(r"\| \d+ \| \[(.+?) \((\w+)\)\]\(.+?\) \| (\w+) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$", line)
        if m:
            name, abbr, overall, best, sure, now, ever, elo, record, win, expected = m.groups()
            rows.append({"name": name, "abbr": abbr, "overall": overall, "best": best, "sure": sure, "now": number(now), "ever": number(ever), "elo": number(elo), "few": "*" in elo, "record": record, "win": number(win), "expected": number(expected)})
    return rows


def recent_use(csv_name):
    """Appearances by team in the last RECENT_YEARS years, and the date of the last game."""
    csv.field_size_limit(10 ** 9)
    rows = []
    with open(DATA / csv_name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") != "1" and r["League"].lower().startswith(CLASSIC):
                y, m, d = r["DateTime"].split()[0].split("-")
                rows.append((date(int(y), int(m), int(d)), r["HomeTeamAbbrev"].strip(), r["AwayTeamAbbrev"].strip()))
    last = max(x[0] for x in rows)
    cut = last - timedelta(days=int(365.25 * RECENT_YEARS))
    use = Counter()
    for when, h, a in rows:
        if when >= cut:
            use[h] += 1
            use[a] += 1
    return use, cut, last


def rank(rows, key, reverse=True):
    """{abbr: place}, ties sharing the better place."""
    order = sorted(rows, key=key, reverse=reverse)
    out, place, prev = {}, 0, None
    for i, r in enumerate(order, 1):
        v = key(r)
        if v != prev:
            place, prev = i, v
        out[r["abbr"]] = place
    return out


def signed(v, d=1):
    return f"{v:+.{d}f}".replace("-", "−")


def section(label, csv_name, guide, player_guide, players):
    rows = team_table(guide)
    use, cut, last = recent_use(csv_name)
    total = sum(use.values())
    sk = players["skaters"]
    for r in rows:
        r["share"] = 100 * use[r["abbr"]] / total
        mine = sorted((s for s in sk if s["team"] == r["abbr"]), key=lambda s: -s["n"])[:5]
        keepers = sorted((g for g in players["goalies"] if g["team"] == r["abbr"]), key=lambda g: -g["sa"])[:1]
        ovrs = [s["ovr"] for s in mine] + [g["ovr"] for g in keepers]
        r["ovr"] = sum(ovrs) / len(ovrs) if ovrs else 0
        r["goalie"] = keepers[0] if keepers else None
    strength = rank(rows, lambda r: r["now"])
    elo = rank(rows, lambda r: r["elo"])
    used = rank(rows, lambda r: r["share"])
    early = rank(rows, lambda r: r["expected"], reverse=False)
    ovr = rank(rows, lambda r: round(r["ovr"], 1))
    for r in rows:
        a = r["abbr"]
        r["demand"] = (used[a] + early[a]) / 2
    demand = rank(rows, lambda r: r["demand"], reverse=False)
    for r in rows:
        a = r["abbr"]
        r["vs_demand"] = demand[a] - strength[a]
        r["vs_ovr"] = ovr[a] - strength[a]
        r["agree"] = abs(elo[a] - strength[a]) <= GAP and not r["few"]
    out = [f"## {label}", "", f"Recent use counts {cut.isoformat()} to {last.isoformat()}. Details on each team are in [TEAM_GUIDE_{label.upper()}.md]({guide}), and on each player in [PLAYER_GUIDE_{label.upper()}.md]({player_guide}).", "",
           "| Team | Strength now | Elo adj. | Overall | Best for | Used lately | Expected | Demand place | Strength place | Stronger than demand by | Lineup Ovr | Ovr place | Stronger than Ovr by |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in sorted(rows, key=lambda r: strength[r["abbr"]]):
        a = r["abbr"]
        out.append(f"| {r['name']} ({a}) | {signed(r['now'])} | {signed(r['elo'], 0)}{'*' if r['few'] else ''} | {r['overall']} | {r['best']} | {r['share']:.1f}% | {r['expected']:.1f}% | {demand[a]} | {strength[a]} | {signed(r['vs_demand'], 0)} | {r['ovr']:.0f} | {ovr[a]} | {signed(r['vs_ovr'], 0)} |")
    out.append("")

    def note(r):
        a = r["abbr"]
        bits = []
        if r["agree"]:
            bits.append("Strength and Elo agree")
        else:
            bits.append(f"Strength place {strength[a]}, Elo place {elo[a]}, so treat with care" if not r["few"] else "Elo rests on few games, so treat with care")
        if r["best"] in ("High-level", "Low-level"):
            bits.append(f"{r['best'].lower()} coaches get more from it ({r['sure'].lower()})")
        return "; ".join(bits)

    value = sorted((r for r in rows if r["vs_demand"] >= GAP and r["overall"] != "Poor"), key=lambda r: -r["vs_demand"])
    soft = sorted((r for r in rows if r["vs_demand"] >= GAP and r["overall"] == "Poor"), key=lambda r: -r["vs_demand"])
    dear = sorted((r for r in rows if r["vs_demand"] <= -GAP), key=lambda r: r["vs_demand"])
    out += ["### Teams that give more than their demand", ""]
    out += [f"- **{r['name']}:** strength place {strength[r['abbr']]}, demand place {demand[r['abbr']]}. {note(r)}." for r in value] or ["- None that aren't also Poor."]
    out.append("")
    if soft:
        out += ["### Cheap, and better than demand, but still below the average team", ""]
        out += [f"- **{r['name']}:** strength {signed(r['now'])}, place {strength[r['abbr']]}; demand place {demand[r['abbr']]}. {note(r)}." for r in soft]
        out.append("")
    out += ["### Teams in more demand than their results", ""]
    out += [f"- **{r['name']}:** demand place {demand[r['abbr']]}, strength place {strength[r['abbr']]}. {note(r)}." for r in dear] or ["- None."]
    out.append("")
    over = sorted((r for r in rows if r["vs_ovr"] >= GAP), key=lambda r: -r["vs_ovr"])
    under = sorted((r for r in rows if r["vs_ovr"] <= -GAP), key=lambda r: r["vs_ovr"])
    out += ["### Against the roster ratings", "", "For anyone drafting from the rosters:", ""]
    out += [f"- **Better than the ratings look:** " + (", ".join(f"{r['name']} (Ovr place {ovr[r['abbr']]}, strength place {strength[r['abbr']]})" for r in over) or "none") + "."]
    out += [f"- **Worse than the ratings look:** " + (", ".join(f"{r['name']} (Ovr place {ovr[r['abbr']]}, strength place {strength[r['abbr']]})" for r in under) or "none") + "."]
    out.append("")
    good = sorted((s for s in sk if s["diff"] is not None and s["n"] >= MIN_SKATER and s["diff"] > 2 * s["se"]), key=lambda s: -s["diff"])[:15]
    weak = sorted((s for s in sk if s["diff"] is not None and s["n"] >= MIN_SKATER and -s["diff"] > 2 * s["se"]), key=lambda s: s["diff"])[:10]
    out += ["### Skaters who score more than their ratings suggest", "", "| Skater | Team | Pos | Games | Ovr | Points a game | Above expected |", "| --- | --- | --- | --- | --- | --- | --- |"]
    out += [f"| {s['name']} | {s['team']} | {s['pos']} | {s['n']:.0f} | {s['ovr']} | {s['p']:.2f} | {signed(s['diff'], 2)} |" for s in good]
    out += ["", "### Skaters who score less than their ratings suggest", "", "| Skater | Team | Pos | Games | Ovr | Points a game | Below expected |", "| --- | --- | --- | --- | --- | --- | --- |"]
    out += [f"| {s['name']} | {s['team']} | {s['pos']} | {s['n']:.0f} | {s['ovr']} | {s['p']:.2f} | {signed(s['diff'], 2)} |" for s in weak]
    out.append("")
    bigger = sorted((g for g in players["goalies"] if g["sa"] >= 400 and g["diff"] > 2 * g["se"]), key=lambda g: -g["diff"])[:8]
    out += ["### Goalies who stop more than is usual for their Agility", "", "| Goalie | Team | Shots against | Agl | Ovr | Save % | Above usual |", "| --- | --- | --- | --- | --- | --- | --- |"]
    out += [f"| {g['name']} | {g['team']} | {g['sa']:,} | {g['agl']} | {g['ovr']} | {100 * g['sv']:.1f} | {signed(100 * g['diff'])} |" for g in bigger]
    out.append("")
    print(label, "value", [r["abbr"] for r in value], "soft", [r["abbr"] for r in soft], "dear", [r["abbr"] for r in dear], "ovr+", [r["abbr"] for r in over], "ovr-", [r["abbr"] for r in under])
    return out


def main():
    players = json.loads((ROOT / "reports" / "classic_players.json").read_text(encoding="utf-8"))
    out = ["# Classic draft guide", "",
           "Which Classic teams and players give more than people seem to expect, on both systems. No coach is named. The team numbers come from the team guides, and the player numbers from the player guides.", "",
           "**Jump to:** [How to read this guide](#how-to-read-this-guide) · [Genesis](#genesis) · [SNES](#snes)", "",
           "## How to read this guide", "",
           "The result files hold no draft order, so **demand here is an estimate**. It averages two places:", "",
           "- **How much a team has been used lately.** A team nobody takes wasn't wanted.",
           "- **How early it seems to go.** In the Classic drafts the people thought weaker pick first, so a team that goes early tends to end up with weaker coaches, which shows as a low Expected.", "",
           "A team's real draft position could say this better. Treat any call here as a place to start, not a verdict.", "",
           "**The columns**", "",
           "- **Strength now:** how much the team adds, in points of win chance, with recent games counting more. From the team guide.",
           "- **Elo adj.:** points to add to a coach's Elo for using this team. From the team guide. An asterisk marks one resting on few games.",
           "- **Overall:** from strength now. Good is +1.5 or better, Poor is −1.5 or worse.",
           "- **Best for:** which level of player gets more from this team. From the team guide, where the confidence is given.",
           "- **Used lately:** the team's share of all appearances in the last three years.",
           "- **Expected:** the win % the team's coaches, home ice and opponents predict if it were the average team, over all years. Low means it has tended to go to weaker coaches.",
           "- **Demand place:** the team's place on the average of its Used lately place and its Expected place, 1 being most in demand.",
           "- **Strength place:** its place by strength now.",
           "- **Stronger than demand by:** Demand place minus Strength place. Plus means the team has done better than its demand suggests.",
           "- **Lineup Ovr:** the mean roster Overall of the team's five most used skaters and most used goalie.",
           "- **Ovr place:** its place by Lineup Ovr.",
           "- **Stronger than Ovr by:** Ovr place minus Strength place. Plus means it has done better than its ratings look.", "",
           f"A team is called out when a gap is {GAP} or more places. A place isn't a fixed distance: near the middle of the table, teams can be a point or less apart.", "",
           "**What to keep in mind**", "",
           "- **Results show what happened, not why.** A team can look better than its demand because a few coaches did well with it.",
           "- **Cheap teams rest on fewer games,** so their values are less certain, and the pull toward average makes them look less extreme than their records.",
           "- **SNES team values repeat far less well than Genesis ones.** Random halves of the leagues agree at 0.73 on the Genesis and 0.35 on the SNES, so SNES calls are softer.",
           "- **Skaters come with their team.** Classic teams are drafted whole, so the skater lists help you to judge a team and to choose lines, not to pick a player alone. \"Above expected\" compares teammates, so it says who people get the most from, not that a skater has a hidden rating.",
           "- **Goalies depend on who plays in front of them.** Save % isn't adjusted for shot quality.", ""]
    for label, csv_name, guide, player_guide in SYSTEMS:
        out += section(label, csv_name, guide, player_guide, players[label])
    (ROOT / "docs" / "DRAFT_GUIDE_CLASSIC.md").write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
