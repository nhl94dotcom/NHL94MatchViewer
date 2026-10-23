"""How the two people played, beyond the box score (2026-10-23, the user: metrics for the people themselves, their
decisions: checking, passing, shot selection, defensive position). Both teams measured the same way over a set of
games between them, totals and per game. Only what the person's own skater (or goalie) did counts; the computer's
teammates are left out except where noted.
- Shot selection: the person's shots, their xG each, how many at a goalie off the shot line (10 or more units: the
  scoring map and the one-timer study, SCORING_MAP, find that is where goals come from) against a set one, and how many
  were low-value (xG under 0.05) or from 120+ (40 feet).
- Passing decisions: the person's passes by zone, completed and picked off; how many led to a shot by his team within
  3 s with the puck kept, and the xG of those shots; passes into the slot (receiver within 60 of the net) and passes
  across the slot (the one-timer study: the pass across is the dangerous one), completed and turned into shots.
- With the puck: carries (person_play): reaching the slot, and what happened there.
- Checking: bursts that landed, missed bursts that let a shot in (person_play); the person's checks: knockdowns and
  how often his team then had the puck within 1.5 s.
- Defence (person_defense): the controlled skater in the shooting lane, near the passing lane, goal-side on carries
  into the slot, the gap at entries, controlling the skater nearest the puck, pokes out of reach.
- The goalie when the person took him: shots faced, xG and goals, how far off the shot line.
python analysis/coach_report.py <TEAM> <TEAM> <match name> ...  -> reports/coach_<first match>.md"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_match import own_end  # noqa: E402
from match_report import find  # noqa: E402
from share_game import load_js_object  # noqa: E402
import person_defense as PD  # noqa: E402
import person_play as PP  # noqa: E402

K = 12


def off_line(m, s, opp_team):
    """The goalie's distance from the line puck -> middle of the net at the release (99 if unknown)."""
    e = own_end(m, s["f"], opp_team)
    if e is None:
        return 99, None
    ny = 268 * e
    g = PD.goalie_xy(m, s["f"], opp_team)
    return (PD.seg_dist(*g, s["x"], s["y"], 0, ny)[0] if g else 99), ny


def measure(m, team):
    t, N, opp = m["t"], len(m["t"]), 1 - team
    mine = range(team * 6, team * 6 + 6)
    c = Counter()
    shots = m.get("shotList", [])
    # ---- shot selection
    for s in shots:
        if s["team"] != team or not s.get("human") or s["kind"] not in ("shot", "one-timer"):
            continue
        off, ny = off_line(m, s, opp)
        if ny is None:
            continue
        d = math.hypot(s["x"], ny - s["y"])
        xg = s.get("xg") or 0
        c["sh"] += 1
        c["sh_xg"] += xg
        c["sh_goal"] += s["result"] == "goal"
        c["sh_ot"] += s["kind"] == "one-timer"
        c["sh_off10"] += off >= 10
        c["sh_off10_xg"] += xg * (off >= 10)
        c["sh_set"] += off < 5
        c["sh_low"] += xg < 0.05
        c["sh_far"] += d >= 120
    # ---- passing decisions
    for p in m.get("passes", []):
        if p["team"] != team or not p.get("human") or p.get("result") == "pass shot":
            continue
        z = p.get("zone", "?")
        ok = p["result"] in ("completed", "one-timer")
        c["pa_" + z] += 1
        c["pa_ok_" + z] += ok
        c["pa_pick_" + z] += p["result"] == "intercepted"
        e = own_end(m, p["f"], opp)
        if e is None:
            continue
        ny = 268 * e
        to_slot = math.hypot(p["x1"], ny - p["y1"]) < 60
        across = z == "att" and p["x0"] * p["x1"] < 0 and abs(p["x1"] - p["x0"]) >= 40 and abs(ny - p["y1"]) < 90
        # a shot by the team within 3 s, the puck not lost in between
        nxt = next((s for s in shots if s["team"] == team and 0 < t[s["f"]] - t[p["f"]] <= 3000), None)
        if nxt and any(m["owner"][q] in range(opp * 6, opp * 6 + 6) for q in range(p["f"], nxt["f"])):
            nxt = None
        if ok and nxt:
            c["pa_shot"] += 1
            c["pa_shot_xg"] += nxt.get("xg") or 0
        if to_slot:
            c["pa_slot"] += 1
            c["pa_slot_ok"] += ok
            c["pa_slot_shot"] += bool(ok and nxt)
        if across:
            c["pa_across"] += 1
            c["pa_across_ok"] += ok
            c["pa_across_shot"] += bool(ok and nxt)
            c["pa_across_xg"] += (nxt.get("xg") or 0) if ok and nxt else 0
    # ---- the person's checks
    for h in m.get("hits", []):
        if h["team"] != team or not h.get("human"):
            continue
        c["hit"] += 1
        c["hit_down"] += h.get("outcome") == "knocked down"
        c["hit_carrier"] += bool(h.get("onCarrier"))
        q = next((q for q in range(h["f"], N) if t[q] - t[h["f"]] > 1500), N - 1)
        c["hit_puck"] += any(m["owner"][r] in mine for r in range(h["f"], q))
    # ---- the baseline for missed bursts: how often any second of defending is followed by a shot against within 4 s
    opp_shots = [t[s["f"]] for s in shots if s["team"] == opp]
    last = -10 ** 9
    for f in range(N):
        if m["owner"][f] in range(opp * 6, opp * 6 + 6) and t[f] - last >= 1000:
            last = t[f]
            c["base_n"] += 1
            c["base_shot"] += any(0 < ts - t[f] <= 4000 for ts in opp_shots)
    # ---- the goalie when the person took him (shots against)
    for s in shots:
        if s["team"] != opp or s["kind"] not in ("shot", "one-timer") or s.get("gctl") != "human":
            continue
        off, ny = off_line(m, s, team)
        if ny is None:
            continue
        c["gk"] += 1
        c["gk_xg"] += s.get("xg") or 0
        c["gk_goal"] += s["result"] == "goal"
        c["gk_off"] += min(off, 60)
    return c


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


def rows(c, pp, pd):
    """The report's rows: (section, label, value, which way is better: + more, - less, '' neither)."""
    sh = c["sh"]
    att = c["pa_att"]
    return [
        ("Shot selection", "the person's shots (one-timers)", f"{sh} ({c['sh_ot']})", ""),
        ("Shot selection", "xG per shot", f"{c['sh_xg'] / max(1, sh):.2f}", "+"),
        ("Shot selection", "goals / xG", f"{c['sh_goal']} / {c['sh_xg']:.1f}", ""),
        ("Shot selection", "at a goalie 10+ off the shot line", f"{c['sh_off10']} ({pct(c['sh_off10'], sh)})", "+"),
        ("Shot selection", "at a set goalie (within 5)", f"{c['sh_set']} ({pct(c['sh_set'], sh)})", "-"),
        ("Shot selection", "low-value (xG under 0.05) / from 40+ ft", f"{c['sh_low']} / {c['sh_far']}", "-"),
        ("Passing", "attacking zone: completed / picked off", f"{c['pa_ok_att']}/{att} / {c['pa_pick_att']}", "+"),
        ("Passing", "neutral zone: completed / picked off", f"{c['pa_ok_neu']}/{c['pa_neu']} / {c['pa_pick_neu']}", "+"),
        ("Passing", "own zone: completed / picked off", f"{c['pa_ok_def']}/{c['pa_def']} / {c['pa_pick_def']}", "+"),
        ("Passing", "passes that set up a shot within 3 s (xG)", f"{c['pa_shot']} ({c['pa_shot_xg']:.1f})", "+"),
        ("Passing", "into the slot: tried / completed / shot", f"{c['pa_slot']} / {c['pa_slot_ok']} / {c['pa_slot_shot']}", "+"),
        ("Passing", "across the slot: tried / completed / shot (xG)",
         f"{c['pa_across']} / {c['pa_across_ok']} / {c['pa_across_shot']} ({c['pa_across_xg']:.1f})", "+"),
        ("With the puck", "carries (avg s)", f"{pp['carries']} ({pp['carry_s'] / max(1, pp['carries']):.1f})", ""),
        ("With the puck", "carries reaching the slot", pct(pp["carry_slot"], pp["carries"]), "+"),
        ("With the puck", "in the slot then: shot / pass / lost", f"{pp['slot_then_shot']} / {pp['slot_then_pass']} / {pp['slot_then_lost']}", ""),
        ("With the puck", "carries ending with the puck lost", pct(pp["carry_lost"], pp["carries"]), "-"),
        ("Checking", "bursts / landed a check", f"{pp['bursts']} / {pp['burst_landed']} ({pct(pp['burst_landed'], pp['bursts'])})", "+"),
        ("Checking", "missed bursts followed by a shot against within 4 s", f"{pp['burst_miss_then_shot']} of {pp['bursts'] - pp['burst_landed']} ({pct(pp['burst_miss_then_shot'], pp['bursts'] - pp['burst_landed'])})", "-"),
        ("Checking", "· any second defending followed by a shot against within 4 s", pct(c["base_shot"], c["base_n"]), ""),
        ("Checking", "the person's checks: knockdowns", f"{c['hit_down']} of {c['hit']}", "+"),
        ("Checking", "checks after which his team had the puck within 1.5 s", f"{c['hit_puck']} ({pct(c['hit_puck'], c['hit'])})", "+"),
        ("Defence", "controls the skater nearest the puck", pct(pp["nearest_s"], pp["def_s"]), "+"),
        ("Defence", "his skater in the shooting lane at the release", pct(pd["sa_lane"], pd["sa"]), "+"),
        ("Defence", "his skater near the passing lane (passes in his zone)", pct(pd["pa_lane"], pd["pa"]), "+"),
        ("Defence", "their carries into his slot: his skater goal-side", f"{pct(pd['cs_goalside'], pd['cs_n'])} of {pd['cs_n']}", "+"),
        ("Defence", "gap at carried entries against (avg)", f"{pp['entry_gap_sum'] / max(1, pp['entry_gap_n']):.0f}", "-"),
        ("Defence", "pokes out of reach (over 30)", f"{pd['poke_far']} of {pd['pokes']}", "-"),
        ("Defence", "passes picked off: by his person / his computer skaters", f"{pd['pick_person']} / {pd['pick_cpu']}", ""),
        ("Goalie", "shots faced with the person in net (goals / xG)", f"{c['gk']} ({c['gk_goal']} / {c['gk_xg']:.1f})", ""),
        ("Goalie", "off the shot line, avg (computer goalies: about 6-8)", f"{c['gk_off'] / max(1, c['gk']):.1f}" if c["gk"] else "-", "-"),
    ]


def main():
    a, b, names = sys.argv[1], sys.argv[2], sys.argv[3:]
    tot = {a: [Counter(), Counter(), Counter()], b: [Counter(), Counter(), Counter()]}
    per = []
    for n in names:
        m = json.loads(load_js_object(find(n)[0]))
        row = {}
        for ab in (a, b):
            ti = m["abbr"].index(ab)
            got = (measure(m, ti), PP.measure(m, ti), PD.measure(m, ti))
            for x, y in zip(tot[ab], got):
                x.update(y)
            row[ab] = rows(*got)
        per.append((n, row))
    ra, rb = rows(*tot[a]), rows(*tot[b])
    out = [f"# How the people played: {a} vs {b}", "", "Games: " + ", ".join(names), "",
           "Both people measured the same way; only their own skater or goalie counts. "
           "+ more is better, - less is better.", ""]
    section = None
    for (sec, label, va, way), (_, _, vb, _) in zip(ra, rb):
        if sec != section:
            out += ["", f"## {sec}", "", f"| | {a} | {b} | |", "|---|---|---|---|"]
            section = sec
        out.append(f"| {label} | {va} | {vb} | {way} |")
    out += ["", "## Per game", ""]
    labels = [r[1] for r in ra]
    for n, row in per:
        out += [f"### {n}", "", f"| | {a} | {b} |", "|---|---|---|"]
        out += [f"| {lab} | {x[2]} | {y[2]} |" for lab, x, y in zip(labels, row[a], row[b])]
        out.append("")
    path = Path("reports") / f"coach_{names[0]}.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
