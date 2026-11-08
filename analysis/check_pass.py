"""Passing out of a check, Genesis and SNES (2026-11-06, the user: "I often play to induce a check and then pass the puck to a
teammate (or at least attempt to) before the check lands. Occasionally, the defender just intercepts the pass
immediately ... and occasionally I press B too late").
Since 2026-11-08 the measure is the converter's (export_match.find_check_passes, the match files' `checkPasses`, in the
viewer's team stats); the rules below are its rules.

A check on the carrier: an opposing skater (the person's or a computer skater) starts a burst (the lunge animation) while a
person's skater has the puck, with the carrier within REACH and CONE of his facing (check_outcomes.py's test). Contact:
the first sample the two are under CONTACT apart, or the game counting a check by him on the carrier, whichever is
first, within RESULT_MS of the burst. What the carrier did from the burst until contact (or the window's end):
- passed it away: a pass (export_match's passes: B starts the pass animation within 1-3 samples on the Genesis, 3-4
  on the SNES, and the puck leaves then or 2 samples later) released before contact, or after contact while the puck
  was still his until it left (the bodies met but the check didn't knock it loose first: "after contact").
  On the SNES the checker's check animation (check_outcomes.SNES_CHECKS) also counts as contact. Its result: reached a teammate (completed or one-timed), picked off by
  the checker himself, picked off by another opponent (skater or goalie), or reached nobody (export_match's 'failed':
  nobody had it within 3 s, or the passer got it back);
- shot it before contact;
- caught: contact came first and he lost the puck within LOST_MS. Split by his B (a rising edge on his controller)
  in the first JUST_MS after contact (the user: a B press 0.2 s (real) or more after the check is ignored here; B without the
  puck also switches skaters): B a moment too late, the pass started (his pass animation began, but the puck was
  knocked loose before it left); B a moment too late, no pass came off (the puck was already gone); or no B in time;
- held on through contact: contact came first and he still had it LOST_MS later (a failed check);
- the check missed: no contact, and what he did then (kept it, passed later, lost it).
Two bursts at the same carrier that end in the same pass, shot or lost puck count once (the later burst).
Timing (real seconds: these are split-second, so they stay in real time, marked "(real)"; the follow-up windows
are shown in game seconds, FOLLOW_MS = 12.5 game s): the pass's lead, from its release to the contact that followed (or to the checker's closest approach when
he never got there), and the checker's distance at the release. What followed: the passing team's attempts and
xG within FOLLOW_MS while it kept the puck; after a pass picked off, the other team's within FOLLOW_MS.
The carrier's buttons come from the match file's controller words (pad / pad2 with padTeam / pad2Team); a team with
no known controller has no B timing.

python analysis/check_pass.py <match> ...          the named games, a table per team, and every event with its time
python analysis/check_pass.py --all [ABBR]         every recorded game, per system and person-side (ABBR: also that team's
                                                    person on its own)   -> reports/check_pass*.md"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_defence as SD  # noqa: E402
from export_match import find_check_passes, CHECK_PASS_OUTCOMES as OUTCOMES  # noqa: E402  (the rules are the converter's)

def measure(m):
    return find_check_passes(m)


def table(rows_by, cols):
    """rows_by: col -> list of events. Lines of a markdown table of outcomes."""
    L = ["| Outcome | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for o in OUTCOMES:
        L.append(f"| {o} | " + " | ".join(f"{sum(e['out'] == o for e in rows_by[c])} "
                                          f"({100 * sum(e['out'] == o for e in rows_by[c]) / max(1, len(rows_by[c])):.0f}%)" for c in cols) + " |")
    L.append("| checks on the carrier | " + " | ".join(str(len(rows_by[c])) for c in cols) + " |")
    return L


def detail(rows_by, cols):
    L = ["| | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]

    def cell(es, fn):
        try:
            return fn(es)
        except (ZeroDivisionError, IndexError):
            return "-"
    passed = lambda es: [e for e in es if e["out"].startswith("passed")]
    lines = [
        ("passes out of a check: reached a teammate", lambda es: f"{sum(e['out'] == OUTCOMES[0] for e in passed(es))} of {len(passed(es))}"),
        ("... their attempts within 12.5 game s / xG / goals", lambda es: "{} / {:.1f} / {}".format(
            *(lambda v: (sum(x[0] for x in v), sum(x[1] for x in v), sum(x[2] for x in v)))([e["for"] for e in es if e["out"] == OUTCOMES[0]]))),
        ("picked off: attempts against within 12.5 game s / xG / goals", lambda es: "{} / {:.1f} / {}".format(
            *(lambda v: (sum(x[0] for x in v), sum(x[1] for x in v), sum(x[2] for x in v)))([e["against"] for e in es if "against" in e and e["out"].startswith("passed")]))),
        ("caught: attempts against within 12.5 game s / xG / goals", lambda es: "{} / {:.1f} / {}".format(
            *(lambda v: (sum(x[0] for x in v), sum(x[1] for x in v), sum(x[2] for x in v)))([e["against"] for e in es if "against" in e and e["out"].startswith("caught")]))),
        ("median lead of the pass before contact (s, real)", lambda es: f"{sorted(v := [e['lead'] for e in passed(es) if e.get('lead') is not None and e['lead'] >= 0])[len(v) // 2]:.2f}"),
        ("passes where the checker never reached him", lambda es: f"{sum(e.get('lead') is None for e in passed(es))}"),
        ("median checker distance at the release (ft)", lambda es: f"{sorted(v := [e['dist_rel'] / 3 for e in passed(es)])[len(v) // 2]:.0f}"),
        ("B a moment too late, the pass started: median start after contact (s, real)", lambda es: f"{sorted(v := [e['b_late'] for e in es if e['out'] == OUTCOMES[5]])[len(v) // 2]:+.2f}"),
        ("checks by the person's skater / computer skaters", lambda es: f"{sum(e['checker_person'] for e in es)} / {sum(not e['checker_person'] for e in es)}"),
    ]
    for lab, fn in lines:
        L.append(f"| {lab} | " + " | ".join(cell(rows_by[c], fn) for c in cols) + " |")
    return L


def by_lead(es):
    """Outcome of passes out of a check by how long before contact they left."""
    bins = [("checker never got there", lambda e: e.get("lead") is None), ("just after contact, still his", lambda e: e.get("lead") is not None and e["lead"] < 0),
            ("under 0.10 s (real) before contact", lambda e: e.get("lead") is not None and 0 <= e["lead"] < 0.10),
            ("0.10-0.25 s", lambda e: e.get("lead") is not None and 0.10 <= e["lead"] < 0.25),
            ("0.25-0.50 s", lambda e: e.get("lead") is not None and 0.25 <= e["lead"] < 0.50),
            ("0.50 s or more", lambda e: e.get("lead") is not None and e["lead"] >= 0.50)]
    L = ["| Pass left (real time) | passes | reached a teammate | picked off by the checker | by another opponent | reached nobody |", "|---|---|---|---|---|---|"]
    ps = [e for e in es if e["out"].startswith("passed")]
    for lab, fn in bins:
        sel = [e for e in ps if fn(e)]
        n = len(sel) or 1
        L.append(f"| {lab} | {len(sel)} | " + " | ".join(f"{sum(e['out'] == o for e in sel)} ({100 * sum(e['out'] == o for e in sel) / n:.0f}%)" for o in OUTCOMES[:4]) + " |")
    return L


def main():
    args = sys.argv[1:]
    out = []
    if args and args[0] == "--all":
        you = args[1] if len(args) > 1 else None
        from coach_models import matches
        rows = defaultdict(list)
        games = 0
        for p in matches():
            m = SD.json.loads(SD.load_js_object(p))
            if "abbr" not in m or "pos" not in m:
                continue
            games += 1
            sy = "SNES" if m.get("system") == "snes" else "Genesis"
            for e in measure(m):
                rows[f"every person, {sy}"].append(e)
                if you and m["abbr"][e["team"]] == you:
                    rows[f"{you}'s person, {sy}"].append(e)
                elif you:
                    rows[f"{you}'s opponents, {sy}"].append(e)
        cols = sorted(rows, key=lambda c: (c.split(", ")[-1], c))
        out += [f"# Passing out of a check: every recorded game ({games} games)", "",
                "How it is measured: analysis/check_pass.py. A person's carrier, an opposing skater bursting at him. Split-second timings are real seconds; the follow-up windows are game seconds (1 game second = 0.4 s of real time).", ""]
        out += table(rows, cols) + [""] + detail(rows, cols)
        for c in cols:
            if not c.startswith(f"{you}'s opponents"):
                out += ["", f"**When the pass left, {c}**", ""] + by_lead(rows[c])
        path = Path("reports") / (f"check_pass_all_{you}.md" if you else "check_pass_all.md")
    else:
        rows = defaultdict(list)
        listing = []
        for name in args:
            m = SD.load(name)
            ab = m["abbr"]
            for e in measure(m):
                rows[ab[e["team"]]].append(e)
                listing.append((name, m, e))
        cols = sorted(rows)
        out += ["# Passing out of a check: " + ", ".join(args), "", "How it is measured: analysis/check_pass.py. Split-second timings are real seconds; the follow-up windows are game seconds (1 game second = 0.4 s of real time).", ""]
        out += table(rows, cols) + [""] + detail(rows, cols)
        for c in cols:
            out += ["", f"**When the pass left, {c}**", ""] + by_lead(rows[c])
        out += ["", "**Every check on a carrier** (the time opens the viewer 2 s before the burst: viewer.html?match=<game>&t=<s>)", "",
                "| Game | t | Clock | Carrier | Checker | Zone | Outcome | Lead / B late |", "|---|---|---|---|---|---|---|---|"]
        for name, m, e in listing:
            f, A = e["f"], e["team"]
            nm = lambda team, i: m["rosters"][team][i]["name"].split()[-1] if 0 <= i < len(m["rosters"][team]) else "?"
            c = m["clock"][f]
            extra = (f"{e['lead']:.2f} s (real)" if e.get("lead") is not None else "never reached") if e["out"].startswith("passed") else \
                (f"pass began {e['b_late']:.2f} s (real) after contact" if e["out"] == OUTCOMES[5] else f"B {e['b_late']:.2f} s (real) after contact" if "b_late" in e else "")
            out.append(f"| {name[11:]} | {max(0, m['t'][f] // 1000 - 2)} | P{m['period'][f] + 1} {c // 60}:{c % 60:02d} | {m['abbr'][A]} {nm(A, e['carrier'])} | "
                       f"{nm(1 - A, e['checker'])}{' (person)' if e['checker_person'] else ''} | {e['zone']} | {e['out']} | {extra} |")
        path = Path("reports") / f"check_pass_{'-'.join(cols)}_{args[0][:10]}.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
