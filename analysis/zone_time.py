"""Quick attacks against long stays in the attacking zone (2026-10-23, the user: most goals seem to come soon after the
zone entry; how successful are quick possessions against long ones?). Every match file in both game folders, Genesis
and SNES apart. A stay is a zone entry (export_match.find_zone_entries) until the puck is back in the neutral zone, a
whistle or the end of the period. For each stay: how long it lasted, the attempts and xG in it, and how it ended (a
goal for the attackers, a whistle, or the puck back out of the zone). Then:
- stays by length: how often each ended in a goal;
- the rate over time: of the stays still going at 0, 5, 10 ... s, the share with a goal in the next 5 s, and attempts in
  those 5 s (the chance per moment of staying in the zone);
- how often attempts come: attempts per 5 s of zone time in a stay's first 5 s and after;
- attempts off the rush (within 5 s of the entry) against sustained pressure (later in the stay): goals per attempt and
  xG per attempt (the viewer's "Off the rush" and "Sustained pressure" rows, as rates).
python analysis/zone_time.py   -> reports/zone_time.md"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from coach_models import matches  # noqa: E402
from share_game import load_js_object  # noqa: E402

LENGTHS = [(0, 5), (5, 10), (10, 20), (20, 999)]
STEPS = [0, 5, 10, 15, 20, 30]


def study(m, out):
    t, N = m["t"], len(m["t"])
    shots = m.get("shotList", [])
    goals = [[f for f in range(1, N) if m["score"][2 * f + tm] > m["score"][2 * (f - 1) + tm]] for tm in (0, 1)]
    for e in m.get("zoneEntries", []):
        f0, f1, team = e["f"], e.get("end") or e["f"], e["team"]
        if team not in (0, 1):
            continue
        g = next((q for q in goals[team] if f0 <= q <= f1 + 30), None)
        if g is not None:
            f1 = g                                         # the stay ends with the goal (not at the faceoff after it)
        dur = (t[f1] - t[f0]) / 1000
        att = [s for s in shots if s["team"] == team and f0 <= s["f"] <= f1]
        whistle = any(m["puck"][3 * q + 2] < -100 for q in range(max(0, f1 - 5), min(N, f1 + 15)))
        ended = "goal" if g is not None else ("whistle" if whistle else "out")
        gt = (t[g] - t[f0]) / 1000 if g is not None else None
        out["stays"].append((dur, ended, gt, len(att), sum(s.get("xg") or 0 for s in att), e.get("kind")))
        out["early_s"] += min(dur, 5)
        out["late_s"] += max(0.0, dur - 5)
        out["early_att"] += sum(1 for s in att if t[s["f"]] - t[f0] <= 5000)
        out["late_att"] += sum(1 for s in att if t[s["f"]] - t[f0] > 5000)
    for s in shots:
        o = s.get("origin")
        if o in ("rush", "zone"):
            out["att_" + o] += 1
            out["goal_" + o] += s["result"] == "goal"
            out["xg_" + o] += s.get("xg") or 0
            out["xgn_" + o] += s.get("xg") is not None


def report(name, out, lines):
    stays = out["stays"]
    if not stays:
        return
    games = out["games"]
    lines += [f"## {name} ({games} games, {len(stays)} zone stays)", ""]
    allg = sum(1 for s in stays if s[1] == "goal")
    lines += [f"{allg} stays ended in a goal ({100 * allg / len(stays):.1f}%). Goals in a stay, by how long after the entry: "
              + ", ".join(f"{a}-{b if b < 999 else ''} s {sum(1 for s in stays if s[2] is not None and a <= s[2] < b)}" for a, b in LENGTHS) + ".", ""]
    lines += ["**Stays by how long they lasted**", "", "| Length | Stays | Ended in a goal | Attempts per stay | xG per stay | Ended: whistle / back out |",
              "|---|---|---|---|---|---|"]
    for a, b in LENGTHS:
        sub = [s for s in stays if a <= s[0] < b]
        if not sub:
            continue
        n = len(sub)
        gl = sum(1 for s in sub if s[1] == "goal")
        lines.append(f"| {a}-{b if b < 999 else ''} s | {n} | {gl} ({100 * gl / n:.1f}%) | {sum(s[3] for s in sub) / n:.2f} | "
                     f"{sum(s[4] for s in sub) / n:.3f} | {sum(1 for s in sub if s[1] == 'whistle')} / {sum(1 for s in sub if s[1] == 'out')} |")
    lines += ["", "**The chance per moment in the zone**: of the stays still going at that time, the share with a goal in the "
              "next 5 s", "", "| Still in the zone at | Stays | Goal in the next 5 s |", "|---|---|---|"]
    for a in STEPS:
        alive = [s for s in stays if s[0] >= a]
        if len(alive) < 5:
            continue
        gl = sum(1 for s in alive if s[2] is not None and a <= s[2] < a + 5)
        lines.append(f"| {a} s | {len(alive)} | {gl} ({100 * gl / len(alive):.1f}%) |")
    lines += ["", f"**How often attempts come**: {5 * out['early_att'] / max(1, out['early_s']):.2f} attempts per 5 s of zone "
              f"time in a stay's first 5 s, {5 * out['late_att'] / max(1, out['late_s']):.2f} after that.", ""]
    lines += ["", "**Per attempt**", "", "| | Attempts | Goals per attempt | xG per attempt |", "|---|---|---|---|"]
    for o, label in (("rush", "Off the rush (within 5 s of the entry)"), ("zone", "Sustained pressure (later in the stay)")):
        n = out["att_" + o]
        if n:
            xg = f"{out['xg_' + o] / out['xgn_' + o]:.3f}" if out["xgn_" + o] else "-"
            lines.append(f"| {label} | {n} | {100 * out['goal_' + o] / n:.1f}% | {xg} |")
    lines.append("")


def main():
    data = defaultdict(lambda: Counter(stays=None))
    for p in matches():
        m = json.loads(load_js_object(p))
        sysname = m.get("system", "genesis")
        out = data[sysname]
        if out["stays"] is None:
            out["stays"] = []
        out["games"] += 1
        study(m, out)
        print(p.stem, flush=True)
    lines = ["# Quick attacks against long stays in the attacking zone", "",
             "Every recorded game in both game folders. A stay: from a zone entry until the puck is back in the neutral "
             "zone, a whistle or the end of the period (the other team may have the puck during it, until it clears it).", ""]
    for sysname in ("genesis", "snes"):
        if sysname in data:
            report(sysname.upper() if sysname == "snes" else "Genesis", data[sysname], lines)
    path = Path("reports") / "zone_time.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
