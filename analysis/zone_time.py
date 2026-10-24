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
Then the same by possession (the user's request: only the time the attackers really had the puck in the zone): a
possession starts when a team has the puck in its attacking zone (|Y| past BLUE at the end it attacks) - carried or
passed in, or won there - and lasts while it has the puck or a pass or shot of its is loose. The other team taking the
puck ends it only if the attackers don't get it back within HOLD_S game-clock seconds (the user: the defence often
claims it and loses it at once, or has it bumped off); it then ends when the defence took it. It also ends when the
puck leaves the zone, at a whistle, or at a goal.
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
BLUE = 83          # the blue lines (|Y|): the neutral zone is inside them
HOLD_S = 3         # game-clock seconds the defence must keep the puck to end a possession (2.5 game s a real s)
K = 12
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
    possessions(m, out)
    for s in shots:
        o = s.get("origin")
        if o in ("rush", "zone"):
            out["att_" + o] += 1
            out["goal_" + o] += s["result"] == "goal"
            out["xg_" + o] += s.get("xg") or 0
            out["xgn_" + o] += s.get("xg") is not None


def possessions(m, out):
    t, N, own, Pk = m["t"], len(m["t"]), m["owner"], m["puck"]
    shots = m.get("shotList", [])
    hold_ms = HOLD_S / 2.5 * 1000
    cur, lost = None, None    # the possession under way [team, start, attack sign, how]; when the defence took it

    def close(f, ended):
        team, f0, sign, how = cur
        att = [s for s in shots if s["team"] == team and f0 <= s["f"] <= f]
        out["poss"].append(((t[f] - t[f0]) / 1000, ended, how, [(t[s["f"]] - t[f0]) / 1000 for s in att],
                            sum(s.get("xg") or 0 for s in att), len(att)))
    for f in range(1, N):
        o = own[f]
        x, y, z = Pk[3 * f], Pk[3 * f + 1], Pk[3 * f + 2]
        if cur:
            team, f0, sign, how = cur
            if m["score"][2 * f + team] > m["score"][2 * f - 2 + team]:
                close(f, "goal")
                cur = None
            elif z < -100 or m["score"][2 * f + 1 - team] > m["score"][2 * f - 2 + 1 - team]:
                close(lost if lost is not None else f, "lost" if lost is not None else "whistle")
                cur = None
            else:
                if o >= 0 and (0 if o < 6 else 1) != team and lost is None:
                    lost = f
                elif o >= 0 and (0 if o < 6 else 1) == team:
                    lost = None                       # got it back in time
                if lost is not None and t[f] - t[lost] > hold_ms:
                    close(lost, "lost")
                    cur = None
                elif y * sign < BLUE:
                    close(lost if lost is not None else f, "lost" if lost is not None else "out")
                    cur = None
            if cur is None:
                lost = None
                continue
        if cur is None and o >= 0 and z > -100:
            team = 0 if o < 6 else 1
            g = next((k for k in range(team * 6, team * 6 + 6) if m["role"][f * K + k] == "0"), None)
            if g is None:
                continue
            sign = -1 if m["pos"][(f * K + g) * 2 + 1] > 0 else 1   # it attacks away from its own goalie
            if y * sign >= BLUE:
                prev_in = Pk[3 * (f - 1) + 1] * sign >= BLUE
                cur, lost = [team, f, sign, "won in the zone" if prev_in else "entered"], None


def report_poss(name, out, lines):
    poss = out["poss"]
    if not poss:
        return
    gl = [p for p in poss if p[1] == "goal"]
    lines += [f"## {name}: by possession ({len(poss)} attacking-zone possessions, {len(gl)} ended in a goal)", "",
              f"Only the time the attackers had the puck in the zone (passes and shots in flight included; a defensive "
              f"touch ends it only if they don't get it back within {HOLD_S} game-clock seconds).", ""]
    lines += ["| Possession length | Possessions | Ended in a goal | Attempts each | xG each | Ended: lost / out / whistle |",
              "|---|---|---|---|---|---|"]
    for a, b in LENGTHS:
        sub = [p for p in poss if a <= p[0] < b]
        if sub:
            n = len(sub)
            g = sum(1 for p in sub if p[1] == "goal")
            lines.append(f"| {a}-{b if b < 999 else ''} s | {n} | {g} ({100 * g / n:.1f}%) | {sum(p[5] for p in sub) / n:.2f} | "
                         f"{sum(p[4] for p in sub) / n:.3f} | {sum(1 for p in sub if p[1] == 'lost')} / "
                         f"{sum(1 for p in sub if p[1] == 'out')} / {sum(1 for p in sub if p[1] == 'whistle')} |")
    lines += ["", "**The chance per moment of possession**: of the possessions still going at that time, a goal in the "
              "next 5 s, and attempts in those 5 s", "",
              "| Still with the puck at | Possessions | Goal in the next 5 s | Attempts per possession in those 5 s |",
              "|---|---|---|---|"]
    for a in STEPS:
        alive = [p for p in poss if p[0] >= a]
        if len(alive) < 5:
            continue
        g = sum(1 for p in alive if p[1] == "goal" and a <= p[0] < a + 5)
        att = sum(sum(1 for at in p[3] if a <= at < a + 5) for p in alive)
        lines.append(f"| {a} s | {len(alive)} | {g} ({100 * g / len(alive):.1f}%) | {att / len(alive):.2f} |")
    lines += ["", "| How it began | Possessions | Ended in a goal | Average length |", "|---|---|---|---|"]
    for how in ("entered", "won in the zone"):
        sub = [p for p in poss if p[2] == how]
        if sub:
            g = sum(1 for p in sub if p[1] == "goal")
            lines.append(f"| {how} | {len(sub)} | {g} ({100 * g / len(sub):.1f}%) | {sum(p[0] for p in sub) / len(sub):.1f} s |")
    lines.append("")


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
            out["stays"], out["poss"] = [], []
        out["games"] += 1
        study(m, out)
        print(p.stem, flush=True)
    lines = ["# Quick attacks against long stays in the attacking zone", "",
             "Every recorded game in both game folders. A stay: from a zone entry until the puck is back in the neutral "
             "zone, a whistle or the end of the period (the other team may have the puck during it, until it clears it).", ""]
    for sysname in ("genesis", "snes"):
        if sysname in data:
            report(sysname.upper() if sysname == "snes" else "Genesis", data[sysname], lines)
            report_poss(sysname.upper() if sysname == "snes" else "Genesis", data[sysname], lines)
    path = Path("reports") / "zone_time.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
