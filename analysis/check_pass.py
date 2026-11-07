"""Passing out of a check, Genesis (2026-11-06, the user: "I often play to induce a check and then pass the puck to a
teammate (or at least attempt to) before the check lands. Occasionally, the defender just intercepts the pass
immediately ... and occasionally I press B too late").

A check on the carrier: an opposing skater (the person's or a computer skater) starts a burst (the lunge animation) while a
person's skater has the puck, with the carrier within REACH and CONE of his facing (check_outcomes.py's test). Contact:
the first sample the two are under CONTACT apart, or the game counting a check by him on the carrier, whichever is
first, within RESULT_MS of the burst. What the carrier did from the burst until contact (or the window's end):
- passed it away: a pass (export_match's passes: B starts the pass animation within 1-3 samples, and the puck leaves
  on that sample) released before contact. Its result: reached a teammate (completed or one-timed), picked off by
  the checker himself, picked off by another opponent (skater or goalie), or reached nobody (export_match's 'failed':
  nobody had it within 3 s, or the passer got it back);
- shot it before contact;
- caught: contact came first and he lost the puck within LOST_MS. Split by his B (a rising edge on his controller)
  in the first JUST_MS after contact (the user: a B press 0.2 s or more after the check is ignored here; B without the
  puck also switches skaters): B a moment too late, the pass started (his pass animation began, but the puck was
  knocked loose before it left); B a moment too late, no pass came off (the puck was already gone); or no B in time;
- held on through contact: contact came first and he still had it LOST_MS later (a failed check);
- the check missed: no contact, and what he did then (kept it, passed later, lost it).
Two bursts at the same carrier that end in the same pass, shot or lost puck count once (the later burst).
Timing: the pass's lead, from its release to the contact that followed (or to the checker's closest approach when
he never got there), and the checker's distance at the release. What followed: the passing team's attempts and
xG within FOLLOW_MS while it kept the puck; after a pass picked off, the other team's within FOLLOW_MS.
The carrier's buttons come from the match file's controller words (pad / pad2 with padTeam / pad2Team); a team with
no known controller has no B timing.

python analysis/check_pass.py <match> ...          the named games, a table per team, and every event with its time
python analysis/check_pass.py --all [ABBR]         every recorded Genesis game, per person-side (ABBR: also that team's
                                                    person on its own)   -> reports/check_pass*.md"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import systems  # noqa: E402
import slot_defence as SD  # noqa: E402

K, REACH, CONE, CONTACT = 12, 70, 35, 18
RESULT_MS, LOST_MS, JUST_MS, FOLLOW_MS = 1000, 400, 200, 5000
PAD_B = 16
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
OUTCOMES = ["passed: reached a teammate", "passed: picked off by the checker", "passed: picked off by another opponent",
            "passed: reached nobody", "shot before contact", "caught: B a moment too late, the pass started",
            "caught: B a moment too late, the puck already gone", "caught: no B in time",
            "held on through contact", "check missed: kept it or passed later", "check missed: lost it"]


def measure(m):
    t, pos, role, owner, puck, N = m["t"], m["pos"], m["role"], m["owner"], m["puck"], len(m["t"])
    acts = systems.of_match(m).ACTIONS
    lunge = acts["lunge"]
    P = lambda f, k: (pos[(f * K + k) * 2], pos[(f * K + k) * 2 + 1])
    an = lambda f, k: m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4]
    roster = lambda f, k: DIGITS.index(m["roster"][f * K + k]) if m["roster"][f * K + k] in DIGITS else -1
    skaters = lambda f, team: [k for k in range(team * 6, team * 6 + 6) if role[f * K + k] in "12345"]
    teamof = lambda k: None if k is None or k < 0 or k >= 12 else k // 6
    pads = {}
    if m.get("pad") and m.get("padTeam", -1) in (0, 1):
        pads[m["padTeam"]] = m["pad"]
    if m.get("pad2") and m.get("pad2Team", -1) in (0, 1):
        pads[m["pad2Team"]] = m["pad2"]
    shots = m.get("shotList", [])
    passes = sorted(m.get("passes", []), key=lambda p: p["f"])

    def until(ms_from, f):
        q = f
        while q < N - 1 and t[q] - t[f] < ms_from:
            q += 1
        return q

    def follow(f, team):
        """The team's attempts and xG from f for FOLLOW_MS while it keeps the puck (loose pucks don't end it)."""
        end = until(FOLLOW_MS, f)
        stop = next((q for q in range(f, end) if teamof(owner[q]) == 1 - team), end)
        got = [s for s in shots if s["team"] == team and f <= s["f"] <= stop]
        return len(got), sum(s.get("xg") or 0 for s in got), any(s["result"] == "goal" for s in got)

    events = []
    for f in range(1, N - 1):
        c = owner[f]
        if teamof(c) is None or role[f * K + c] not in "12345" or not m["ctrl"][f] >> c & 1 or puck[3 * f + 2] < -100:
            continue
        A = c // 6
        for o in skaters(f, 1 - A):
            if an(f, o) not in lunge or an(f - 1, o) in lunge:
                continue
            x, y = P(f, o)
            a = math.radians(45 * int(m["facing"][f * K + o]))
            dx, dy = P(f, c)[0] - x, P(f, c)[1] - y
            d = math.hypot(dx, dy)
            if d >= REACH or math.degrees(math.acos(max(-1, min(1, (math.sin(a) * dx + math.cos(a) * dy) / (d or 1))))) > CONE:
                continue
            ro, rc = roster(f, o), roster(f, c)
            end = until(RESULT_MS, f)
            hit = next((h for h in m.get("hits", []) if h["team"] == 1 - A and h["by"] == ro and h["on"] == rc
                        and f <= h["f"] <= end), None)
            contact, closest, closest_q = None, d, f
            for q in range(f, end + 1):
                dq = math.dist(P(q, o), P(q, c))
                if dq < closest:
                    closest, closest_q = dq, q
                if dq < CONTACT or (hit and q >= hit["f"]):
                    contact = q
                    break
            # the carrier's pass or shot from the burst until contact (or the window's end)
            stop = contact if contact is not None else end
            pas = next((p for p in passes if p["team"] == A and p["idx"] == rc and f <= p["f"] <= stop), None)
            sh = next((s for s in shots if s["team"] == A and s["idx"] == rc and f <= s["f"] <= stop), None)
            ev = {"f": f, "team": A, "carrier": rc, "checker": ro, "checker_person": bool(m["ctrl"][f] >> o & 1),
                  "dist0": d, "zone": None, "pass": pas, "contact": contact, "hit": bool(hit)}
            ny = 268 if any(role[f * K + k] == "0" and P(f, k)[1] > 0 for k in range(A * 6, A * 6 + 6)) else -268
            yy = P(f, c)[1] * (1 if ny > 0 else -1)
            ev["zone"] = "own" if yy >= 89 else "their" if yy <= -89 else "neutral"
            if pas and (not sh or pas["f"] <= sh["f"]):
                rel = pas["f"]
                ev["lead"] = (t[contact] - t[rel]) / 1000 if contact is not None else None
                ev["to_closest"] = (t[closest_q] - t[rel]) / 1000
                ev["dist_rel"] = math.dist(P(rel, o), P(rel, c))
                if pas["result"] in ("completed", "one-timer"):
                    ev["out"] = OUTCOMES[0]
                elif pas["result"] == "intercepted":
                    taker = next((owner[q] for q in range(rel, min(N, rel + 240)) if teamof(owner[q]) == 1 - A), None)
                    ev["out"] = OUTCOMES[1] if taker == o else OUTCOMES[2]
                elif pas["result"] == "pass shot":
                    ev["out"] = OUTCOMES[0]
                else:
                    ev["out"] = OUTCOMES[3]
                    ev["deep"] = pas.get("toZone") == "att"
                n_, xg_, g_ = follow(rel, A) if ev["out"] in (OUTCOMES[0], OUTCOMES[3]) else (0, 0.0, False)
                ev["for"] = (n_, xg_, g_)
                if ev["out"] in (OUTCOMES[1], OUTCOMES[2]):
                    ev["against"] = follow(rel, 1 - A)
            elif sh:
                ev["out"] = OUTCOMES[4]
                ev["for"] = (1, sh.get("xg") or 0, sh["result"] == "goal")
            elif contact is not None:
                later = until(LOST_MS, contact)
                kept = any(owner[q] == c for q in range(later, min(N, later + 3)))
                if kept:
                    ev["out"] = OUTCOMES[8]
                else:
                    # when the puck left him, and whether he had started a pass by then (B with the puck starts the pass
                    # animation within 1-3 samples); a B press after the puck has gone can be a late pass or a switch
                    # to the skater nearest the puck, so only the first JUST_MS after the loss is called a late pass
                    loss = next((q for q in range(contact, N) if owner[q] != c), contact)
                    pad = pads.get(A)
                    just = until(JUST_MS, contact)
                    if t[just] - t[contact] >= JUST_MS:
                        just -= 1
                    started = next((q for q in range(f, min(N, loss + 2, just + 1)) if an(q, c) in acts["pass"]), None)
                    press = None if pad is None else next((q for q in range(contact, just + 1)
                                                           if pad[q] & PAD_B and not pad[q - 1] & PAD_B), None)
                    ev["loss"] = (t[loss] - t[contact]) / 1000
                    if started is not None:
                        ev["out"] = OUTCOMES[5]
                        ev["b_late"] = (t[started] - t[contact]) / 1000
                    elif press is not None:
                        ev["out"] = OUTCOMES[6]
                        ev["b_late"] = (t[press] - t[contact]) / 1000
                    else:
                        ev["out"] = OUTCOMES[7]
                        ev["no_pad"] = pad is None
                    ev["against"] = follow(contact, 1 - A)
            else:
                kept = owner[end] == c or any(p["team"] == A and p["idx"] == rc and end < p["f"] <= until(500, end) for p in passes)
                ev["out"] = OUTCOMES[9] if kept or teamof(owner[end]) == A else OUTCOMES[10]
            ev["key"] = (("pass", pas["f"]) if ev["out"].startswith("passed") else ("shot", sh["f"]) if ev["out"] == OUTCOMES[4]
                         else ("loss", A, loss) if ev["out"].startswith("caught") else None)
            events.append(ev)
    # two bursts at the same carrier can end in the same pass, shot or lost puck: count it once, with the last burst
    last = {}
    for i, ev in enumerate(events):
        if ev["key"] is not None:
            last[ev["key"]] = i
    return [ev for i, ev in enumerate(events) if ev["key"] is None or last[ev["key"]] == i]


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
        ("... their attempts within 5 s / xG / goals", lambda es: "{} / {:.1f} / {}".format(
            *(lambda v: (sum(x[0] for x in v), sum(x[1] for x in v), sum(x[2] for x in v)))([e["for"] for e in es if e["out"] == OUTCOMES[0]]))),
        ("picked off: attempts against within 5 s / xG / goals", lambda es: "{} / {:.1f} / {}".format(
            *(lambda v: (sum(x[0] for x in v), sum(x[1] for x in v), sum(x[2] for x in v)))([e["against"] for e in es if "against" in e and e["out"].startswith("passed")]))),
        ("caught: attempts against within 5 s / xG / goals", lambda es: "{} / {:.1f} / {}".format(
            *(lambda v: (sum(x[0] for x in v), sum(x[1] for x in v), sum(x[2] for x in v)))([e["against"] for e in es if "against" in e and e["out"].startswith("caught")]))),
        ("median lead of the pass before contact (s)", lambda es: f"{sorted(v := [e['lead'] for e in passed(es) if e.get('lead') is not None])[len(v) // 2]:.2f}"),
        ("passes where the checker never reached him", lambda es: f"{sum(e.get('lead') is None for e in passed(es))}"),
        ("median checker distance at the release (ft)", lambda es: f"{sorted(v := [e['dist_rel'] / 3 for e in passed(es)])[len(v) // 2]:.0f}"),
        ("B a moment too late, the pass started: median start after contact (s)", lambda es: f"{sorted(v := [e['b_late'] for e in es if e['out'] == OUTCOMES[5]])[len(v) // 2]:+.2f}"),
        ("checks by the person's skater / computer skaters", lambda es: f"{sum(e['checker_person'] for e in es)} / {sum(not e['checker_person'] for e in es)}"),
    ]
    for lab, fn in lines:
        L.append(f"| {lab} | " + " | ".join(cell(rows_by[c], fn) for c in cols) + " |")
    return L


def by_lead(es):
    """Outcome of passes out of a check by how long before contact they left."""
    bins = [("checker never got there", lambda e: e.get("lead") is None), ("under 0.10 s before contact", lambda e: e.get("lead") is not None and e["lead"] < 0.10),
            ("0.10-0.25 s", lambda e: e.get("lead") is not None and 0.10 <= e["lead"] < 0.25),
            ("0.25-0.50 s", lambda e: e.get("lead") is not None and 0.25 <= e["lead"] < 0.50),
            ("0.50 s or more", lambda e: e.get("lead") is not None and e["lead"] >= 0.50)]
    L = ["| Pass left | passes | reached a teammate | picked off by the checker | by another opponent | reached nobody |", "|---|---|---|---|---|---|"]
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
            if m.get("system", "genesis") != "genesis" or "abbr" not in m:
                continue
            games += 1
            for e in measure(m):
                rows["every person"].append(e)
                if you and m["abbr"][e["team"]] == you:
                    rows[f"{you}'s person"].append(e)
                elif you:
                    rows[f"{you}'s opponents"].append(e)
        cols = list(rows)
        out += [f"# Passing out of a check: every recorded Genesis game ({games} games)", "",
                "How it is measured: analysis/check_pass.py. A person's carrier, an opposing skater bursting at him.", ""]
        out += table(rows, cols) + [""] + detail(rows, cols) + ["", "**When the pass left, every person**", ""] + by_lead(rows["every person"])
        if you:
            out += ["", f"**When the pass left, {you}'s person**", ""] + by_lead(rows[f"{you}'s person"])
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
        out += ["# Passing out of a check: " + ", ".join(args), "", "How it is measured: analysis/check_pass.py.", ""]
        out += table(rows, cols) + [""] + detail(rows, cols)
        for c in cols:
            out += ["", f"**When the pass left, {c}**", ""] + by_lead(rows[c])
        out += ["", "**Every check on a carrier** (the time opens the viewer 2 s before the burst: viewer.html?match=<game>&t=<s>)", "",
                "| Game | t | Clock | Carrier | Checker | Zone | Outcome | Lead / B late |", "|---|---|---|---|---|---|---|---|"]
        for name, m, e in listing:
            f, A = e["f"], e["team"]
            nm = lambda team, i: m["rosters"][team][i]["name"].split()[-1] if 0 <= i < len(m["rosters"][team]) else "?"
            c = m["clock"][f]
            extra = (f"{e['lead']:.2f} s" if e.get("lead") is not None else "never reached") if e["out"].startswith("passed") else \
                (f"pass began {e['b_late']:.2f} s after contact" if e["out"] == OUTCOMES[5] else f"B {e['b_late']:.2f} s after contact" if "b_late" in e else "")
            out.append(f"| {name[11:]} | {max(0, m['t'][f] // 1000 - 2)} | P{m['period'][f] + 1} {c // 60}:{c % 60:02d} | {m['abbr'][A]} {nm(A, e['carrier'])} | "
                       f"{nm(1 - A, e['checker'])}{' (person)' if e['checker_person'] else ''} | {e['zone']} | {e['out']} | {extra} |")
        path = Path("reports") / f"check_pass_{'-'.join(cols)}_{args[0][:10]}.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
