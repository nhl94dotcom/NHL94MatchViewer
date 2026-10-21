"""Home / away crossed with up / down the screen (the user, 2026-10-19): every shot and one-timer split into Home-Up,
Home-Down, Away-Up and Away-Down, with each cell's game time so rates can be per 5:00 (Home attacks up in two of the
three regulation periods, so it spends about twice as long going up as down, and Away the reverse). Prints markdown
tables for docs/SHOOTING_STUDY.md, for all teams and for teams a person played. Run analysis/shot_table.py first, from
the project folder: python analysis/home_direction_study.py"""
import json
from collections import Counter
from pathlib import Path

rows = json.load(open(Path("matches") / "shot_study.json"))
periods = json.load(open(Path("matches") / "shot_study_periods.json"))
CELLS = [("Home, up", True, True), ("Home, down", True, False), ("Away, up", False, True), ("Away, down", False, False)]


def cell_stats(shots, secs):
    att = len(shots)
    goals = sum(r["result"] == "goal" for r in shots)
    on_goal = sum(1 for r in shots if r["counted"] or r["result"] == "goal")
    reached = [r for r in shots if r["result"] in ("goal", "save", "post")]
    unc = sum(1 for r in reached if not r["counted"] and r["result"] != "goal")
    xs = [r for r in shots if r["xg"] is not None and r["result"] != "blocked"]
    xg = sum(r["xg"] for r in xs)
    xg_goals = sum(r["result"] == "goal" for r in xs)
    aims = Counter(r["aim"]["z"] for r in shots if r["human"] and r["kind"] == "shot" and r["aim"])
    na = sum(aims.values())
    ex = [r for r in shots if r["human"] and r["kind"] == "shot" and r["perfect"] is not None and r["dist"] < 200]
    per5 = (lambda n: f"{n * 300 / secs:.1f}") if secs else (lambda n: "-")
    return {
        "Game time": f"{secs / 60:.0f} min",
        "Attempts": f"{att} ({per5(att)} per 5:00)",
        "Shots on goal": f"{on_goal} ({per5(on_goal)} per 5:00)",
        "Goals": f"{goals} ({per5(goals)} per 5:00)",
        "Goals per attempt": f"{100 * goals / att:.1f}%" if att else "-",
        "Goals per shot on goal": f"{100 * goals / on_goal:.1f}%" if on_goal else "-",
        "xG per unblocked attempt": f"{xg / len(xs):.2f}" if xs else "-",
        "Goals minus xG": f"{xg_goals - xg:+.1f}" if xs else "-",
        "Uncounted stops": f"{100 * unc / len(reached):.0f}%" if reached else "-",
        "A person's aims high / middle / ice": f"{100 * aims[12] / na:.0f} / {100 * aims[6] / na:.0f} / {100 * aims[0] / na:.0f}%" if na else "-",
        "A person's shots exact (within 200)": f"{100 * sum(r['perfect'] for r in ex) / len(ex):.0f}% of {len(ex)}" if ex else "-",
    }


def table(system, person_only):
    S = [r for r in rows if r["system"] == system and (r["person_team"] or not person_only)]
    P = [p for p in periods if p["system"] == system and (p["person"] or not person_only)]
    cols = []
    for _, home, up in CELLS:
        cols.append(cell_stats([r for r in S if r["home"] == home and r["up"] == up],
                               sum(p["secs"] for p in P if p["home"] == home and p["up"] == up)))
    margins = []
    for test in (lambda x: x["home"], lambda x: not x["home"], lambda x: x["up"], lambda x: not x["up"]):
        margins.append(cell_stats([r for r in S if test(r)], sum(p["secs"] for p in P if test(p))))
    games = len({r["game"] for r in S})
    head = "| | " + " | ".join(c[0] for c in CELLS) + " | All home | All away | All up | All down |"
    out = [f"**{system.upper()}, {'teams a person played' if person_only else 'all teams'}** ({games} games)", "", head,
           "|---" * 9 + "|"]
    for key in cols[0]:
        out.append(f"| {key} | " + " | ".join(c[key] for c in cols) + " | " + " | ".join(m[key] for m in margins) + " |")
    return "\n".join(out)


for system in ("genesis", "snes"):
    for person_only in (False, True):
        print(table(system, person_only))
        print()


def ratio_line(label, a_shots, a_secs, b_shots, b_secs, test):
    """Rate ratio a / b per game second for the shots passing test, with a 95% range (Poisson, log scale)."""
    import math
    na, nb = sum(1 for r in a_shots if test(r)), sum(1 for r in b_shots if test(r))
    if not (na and nb and a_secs and b_secs):
        return f"{label}: -"
    rr = (na / a_secs) / (nb / b_secs)
    se = math.sqrt(1 / na + 1 / nb)
    return f"{label}: {rr:.2f} ({rr * math.exp(-1.96 * se):.2f}-{rr * math.exp(1.96 * se):.2f})"


def comparisons(system, person_only):
    S = [r for r in rows if r["system"] == system and (r["person_team"] or not person_only)]
    P = [p for p in periods if p["system"] == system and (p["person"] or not person_only)]
    sel = lambda f: ([r for r in S if f(r)], sum(p["secs"] for p in P if f(p)))
    pairs = [("Home / Away", lambda x: x["home"], lambda x: not x["home"]),
             ("Up / Down", lambda x: x["up"], lambda x: not x["up"]),
             ("Home: Up / Down", lambda x: x["home"] and x["up"], lambda x: x["home"] and not x["up"]),
             ("Away: Up / Down", lambda x: not x["home"] and x["up"], lambda x: not x["home"] and not x["up"])]
    tests = [("attempts", lambda r: True), ("shots on goal", lambda r: r["counted"] or r["result"] == "goal"),
             ("goals", lambda r: r["result"] == "goal")]
    print(f"{system.upper()} {'person teams' if person_only else 'all teams'}: rate ratios per game minute (95% range)")
    for name, fa, fb in pairs:
        (sa, ta), (sb, tb) = sel(fa), sel(fb)
        print("  " + name + ": " + "; ".join(ratio_line(t, sa, ta, sb, tb, f) for t, f in tests))


for system in ("genesis", "snes"):
    for person_only in (False, True):
        comparisons(system, person_only)
