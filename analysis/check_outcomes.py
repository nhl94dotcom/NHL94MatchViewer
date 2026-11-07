"""What a person's check attempts lead to (2026-11-03, the user: what a failed or whiffed check costs, whoever else is back: a
miss usually puts the skater out of position, and the covering teammate isn't always much help). Genesis and SNES.

A check attempt: the person's skater starts a burst (C on the Genesis, A on the SNES: the `lunge` animation) while the other
team has the puck, with an opposing skater within 70 and 35 degrees of his facing (coach_report's test). Its result, within
RESULT_MS:
- hit: the game counted a check by him (knocked down or stayed up, as `find_hits` reads it);
- failed: he reached a man (under CONTACT apart), or the SNES shows his check animation, and the game counted nothing: a check
  that lost its roll, or a burst that only shoved him. The man keeps skating;
- whiff: he got within NEAR (about 10 feet) of a man but never touched anyone.
A burst that never gets within NEAR of an opponent isn't counted at all (the user: a burst is often just to reposition a defender).
What follows, within AFTER_MS, as long as his team hasn't had the puck and there has been no faceoff: the other team's shot
attempts, their xG, their goals. The skater goal-side of the puck (nearer his own net) at the burst, and BEHIND_MS later.
Last man: no other skater of his was goal-side at the burst. The baseline: the same counts from moments when the other team
had the puck and nobody on his team was trying a check, every half second, in the same zones. Holding off: those of the moments
with his skater goal-side and the carrier within reach, the fair comparison for a check tried from goal-side: he could have
tried one and didn't. A burst under LATE_MS before the goal's shot is marked: too late to have cost anything.

A goal after a miss doesn't prove the miss caused it: compare with the hit and baseline rows. Dodged and badly aimed misses
aren't told apart. Goals are rare, so one set of games says little: `--all` totals every recorded game.

python analysis/check_outcomes.py <match> ...      a table per team, and each miss followed by a goal
python analysis/check_outcomes.py --all            every recorded game with a person on the checking side, per system"""
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import systems  # noqa: E402
from export_match import own_end  # noqa: E402
import slot_defence as SD  # noqa: E402
import gametime as GT  # noqa: E402

K, REACH, CONE, CONTACT, NEAR, ZONE_LINE = 12, 70, 35, 18, 30, 89
RESULT_MS, AFTER_MS, BEHIND_MS, BASE_STEP_MS, QUIET_MS, LATE_MS = 1000, 6000, 1000, 500, 1000, 1000
RESULTS = ("hit", "failed", "whiff")
ZONES = ("own", "neutral", "their")
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
SNES_CHECKS = {"f27a", "f2ac", "f2de", "f310"}       # the check animations (snes_burst_contact_study.py)


def measure(m):
    """(events, baseline, hold). events: one dict per check attempt. baseline, hold: (team, zone) -> [moments, shots, xG, goals]."""
    t, pos, role, owner, puck, N = m["t"], m["pos"], m["role"], m["owner"], m["puck"], len(m["t"])
    lunge = systems.of_match(m).ACTIONS["lunge"]
    snes = m.get("system") == "snes"
    P = lambda f, k: (pos[(f * K + k) * 2], pos[(f * K + k) * 2 + 1])
    an = lambda f, k: m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4]
    skaters = lambda f, team: [k for k in range(team * 6, team * 6 + 6) if role[f * K + k] in "12345"]
    roster = lambda f, k: DIGITS.index(m["roster"][f * K + k]) if m["roster"][f * K + k] in DIGITS else -1
    has = lambda f, team: owner[f] is not None and 0 <= owner[f] < 12 and (owner[f] < 6) == (team == 0)
    faceoffs = sorted(fo["f"] for fo in m.get("faceoffs", []))
    shots = sorted((s for s in m.get("shotList", []) if s["team"] in (0, 1)), key=lambda s: s["f"])

    def goal_side(f, k, e):
        ny = 264 * e
        return math.hypot(*P(f, k)[:1], ny - P(f, k)[1]) < math.hypot(puck[3 * f], ny - puck[3 * f + 1])

    def zone(f, e):
        y = puck[3 * f + 1] * e
        return "own" if y >= ZONE_LINE else "their" if y <= -ZONE_LINE else "neutral"

    def after(f, team):
        """The other team's shots after frame f until the window ends, his team has the puck or a faceoff comes."""
        out = []
        stop = next((x for x in faceoffs if x > f), N)
        q = f
        for s in shots:
            if s["f"] <= f or s["team"] == team:
                continue
            if t[s["f"]] - t[f] > AFTER_MS or s["f"] >= stop:
                break
            while q < s["f"]:
                if has(q, team):
                    return out
                q += 1
            out.append(s)
        return out

    events, tried = [], defaultdict(list)
    for team in (0, 1):
        them = 1 - team
        for f in range(1, N - 1):
            if not has(f, them) or puck[3 * f + 2] < -100:
                continue
            k = next((j for j in range(team * 6, team * 6 + 6) if m["ctrl"][f] >> j & 1 and role[f * K + j] in "12345"), None)
            if k is None or an(f, k) not in lunge or an(f - 1, k) in lunge:
                continue
            x, y = P(f, k)
            a = math.radians(45 * int(m["facing"][f * K + k]))
            fx, fy = math.sin(a), math.cos(a)
            target = None
            for o in skaters(f, them):
                dx, dy = P(f, o)[0] - x, P(f, o)[1] - y
                d = math.hypot(dx, dy)
                if d < REACH and math.degrees(math.acos(max(-1, min(1, (fx * dx + fy * dy) / (d or 1))))) <= CONE:
                    if target is None or o == owner[f] or d < target[0] and target[1] != owner[f]:
                        target = (d, o)
            if target is None:
                continue
            e = own_end(m, f, team)
            if e is None:
                continue
            who = roster(f, k)
            hit = next((h for h in m.get("hits", []) if h["team"] == team and h["by"] == who and 0 <= t[h["f"]] - t[f] <= RESULT_MS), None)
            thrown, closest = False, 10 ** 9
            q = f
            while q < N and t[q] - t[f] <= RESULT_MS:
                thrown = thrown or (snes and an(q, k) in SNES_CHECKS)
                closest = min([closest] + [math.dist(P(q, k), P(q, o)) for o in skaters(q, them)])
                q += 1
            if not (hit or thrown) and closest >= NEAR:
                continue                                  # never got near anyone: a burst to reposition, not a check
            tried[team].append(f)
            result = "hit" if hit else "failed" if closest < CONTACT or thrown else "whiff"
            later = next((q for q in range(f, N) if t[q] - t[f] >= BEHIND_MS), N - 1)
            back = [o for o in skaters(f, team) if o != k and goal_side(f, o, e)]
            sh = after(f, team)
            goal = next((s for s in sh if s["result"] == "goal"), None)
            events.append({
                "f": f, "team": team, "by": who, "on": roster(f, target[1]), "carrier": target[1] == owner[f], "result": result,
                "outcome": hit["outcome"] if hit else None, "thrown": thrown, "zone": zone(f, e), "last": not back, "back": len(back),
                "side0": goal_side(f, k, e), "side1": goal_side(later, k, e), "won": any(has(q, team) for q in range(f, min(N, later + 60))),
                "shots": len(sh), "xg": sum(s.get("xg") or 0 for s in sh if s["result"] != "blocked"), "goal": goal,
                "late": bool(goal) and t[goal["f"]] - t[f] < LATE_MS, "goal_f": goal["f"] if goal else None})
    baseline = defaultdict(lambda: [0, 0, 0.0, 0])
    hold = defaultdict(lambda: [0, 0, 0.0, 0])
    for team in (0, 1):
        last = -10 ** 9
        for f in range(1, N - 1):
            if t[f] - last < BASE_STEP_MS or not has(f, 1 - team) or puck[3 * f + 2] < -100:
                continue
            if any(abs(t[g] - t[f]) < QUIET_MS for g in tried[team]):
                continue
            e = own_end(m, f, team)
            if e is None:
                continue
            last = t[f]
            sh = after(f, team)
            k = next((j for j in range(team * 6, team * 6 + 6) if m["ctrl"][f] >> j & 1 and role[f * K + j] in "12345"), None)
            near = k is not None and goal_side(f, k, e) and math.dist(P(f, k), P(f, owner[f])) < REACH
            for b in [baseline[(team, zone(f, e))]] + ([hold[(team, zone(f, e))]] if near else []):
                b[0] += 1
                b[1] += len(sh)
                b[2] += sum(s.get("xg") or 0 for s in sh if s["result"] != "blocked")
                b[3] += any(s["result"] == "goal" for s in sh)
    return events, baseline, hold


def rows(events, baseline=None):
    """Table rows (label, attempts, won the puck, goal-side after, shots, xG, goals), by result."""
    out = []
    for res in RESULTS:
        v = [e for e in events if e["result"] == res]
        if v:
            out.append((res, len(v), sum(e["won"] for e in v), sum(e["side0"] for e in v), sum(e["side1"] for e in v),
                        sum(e["shots"] for e in v), sum(e["xg"] for e in v), sum(bool(e["goal"]) for e in v)))
    return out


def lines(m, events, baseline, team):
    """The report's lines for one team."""
    ab, Rs, T, PD, CL = m["abbr"], m["rosters"], m["t"], m["period"], m["clock"]
    mine = [e for e in events if e["team"] == team]
    L = [f"**{ab[team]}**: {len(mine)} check attempts.", "",
         "| Result | Attempts | Won the puck | Goal-side before / 2.5 game s after | Shots against in 15 game s | xG | Goals |",
         "|---|---|---|---|---|---|---|"]
    for r in rows(mine):
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} / {r[4]} | {r[5]} | {r[6]:.1f} | {r[7]} |")
    n = sum(baseline[(team, z)][0] for z in ZONES)
    if n:
        L.append(f"| no attempt (per moment) | {n} | | | {sum(baseline[(team, z)][1] for z in ZONES) / n:.2f} | "
                 f"{sum(baseline[(team, z)][2] for z in ZONES) / n:.2f} | {100 * sum(baseline[(team, z)][3] for z in ZONES) / n:.1f}% |")
    L.append("")
    missed = {e["goal_f"] for e in mine if e["goal"] and e["result"] != "hit" and not e["late"]}
    if missed:
        L.extend([f"Goals within 15 game s of a miss (not counting bursts under 2.5 game s before the shot): {len(missed)}.", ""])
    for e in sorted((e for e in mine if e["goal"] and e["result"] != "hit"), key=lambda e: e["f"]):
        f, s = e["f"], e["goal"]
        L.append(f"- P{PD[f] + 1} {CL[f] // 60}:{CL[f] % 60:02}: {Rs[team][e['by']]['name']} {'whiffed on' if e['result'] == 'whiff' else 'failed to knock off'} "
                 f"{Rs[1 - team][e['on']]['name']}{' (the carrier)' if e['carrier'] else ''} "
                 f"{ {'own': 'in his own end', 'neutral': 'in the neutral zone', 'their': 'in the other end'}[e['zone']] }; "
                 f"{'last man back' if e['last'] else str(e['back']) + ' teammate' + ('s' if e['back'] != 1 else '') + ' goal-side'}; "
                 f"{'goal-side' if e['side0'] else 'not goal-side'} before, {'goal-side' if e['side1'] else 'not goal-side'} 2.5 game s after; "
                 f"{Rs[1 - team][s['idx']]['name']} scored {GT.gsec(T[s['f']] - T[f]):.1f} game s later (xG {s.get('xg') or 0:.2f})"
                 f"{'; too late to have cost anything' if e['late'] else ''}.")
    L.append("")
    return L


def combined(all_events, all_base, all_hold, label):
    print(f"\n{label}: {len(all_events)} check attempts")
    print(f"  {'':9}{'n':>6}{'won puck':>10}{'side before':>13}{'side 2.5 gs after':>18}{'shots/att':>11}{'xG/att':>8}{'goal rate':>11}")
    for zone_name, sel in [("all", lambda e: True)] + [(z, lambda e, z=z: e["zone"] == z) for z in ZONES]:
        v = [e for e in all_events if sel(e)]
        print(f" {zone_name}:")
        for r in rows(v):
            print(f"  {r[0]:9}{r[1]:6}{100 * r[2] / r[1]:9.0f}%{100 * r[3] / r[1]:12.0f}%{100 * r[4] / r[1]:15.0f}%{r[5] / r[1]:11.2f}{r[6] / r[1]:8.2f}{100 * r[7] / r[1]:10.1f}%")
        keys = ZONES if zone_name == "all" else (zone_name,)
        n, sh, xg, gl = (sum(all_base[z][i] for z in keys) for i in range(4))
        if n:
            print(f"  {'baseline':9}{n:6}{'':10}{'':13}{'':16}{sh / n:11.2f}{xg / n:8.2f}{100 * gl / n:10.1f}%")
    print("  tried from goal-side against holding off, by zone (a check tried: hit and miss together):")
    for z in ZONES:
        v = [e for e in all_events if e["zone"] == z and e["side0"]]
        n, sh, xg, gl = (all_hold[z][i] for i in range(4))
        if v and n:
            print(f"   {z:8} tried {len(v):4}: shots {sum(e['shots'] for e in v) / len(v):.2f} xG {sum(e['xg'] for e in v) / len(v):.2f} goal {100 * sum(bool(e['goal']) for e in v) / len(v):4.1f}% "
                  f"(hit {sum(e['result'] == 'hit' for e in v)}, won the puck {100 * sum(e['won'] for e in v) / len(v):.0f}%); held off {n:5} moments: shots {sh / n:.2f} xG {xg / n:.2f} goal {100 * gl / n:4.1f}%")
    miss = [e for e in all_events if e["result"] != "hit"]
    print(f"  different goals within 15 game s of a miss, not counting bursts under 2.5 game s before the shot: {len({(e.get('game'), e['goal_f']) for e in miss if e['goal'] and not e['late']})}")
    print("  a miss, by who else was back:")
    for lab, sel in (("last man", lambda e: e["last"]), ("1 teammate goal-side", lambda e: e["back"] == 1), ("2+", lambda e: e["back"] >= 2)):
        v = [e for e in miss if sel(e)]
        if v:
            print(f"   {lab:22}{len(v):5}  shots/att {sum(e['shots'] for e in v) / len(v):.2f}  xG/att {sum(e['xg'] for e in v) / len(v):.2f}  goal {100 * sum(bool(e['goal']) for e in v) / len(v):.1f}%")
    print("  a miss when goal-side at the burst:")
    v = [e for e in miss if e["side0"]]
    if v:
        lost = [e for e in v if not e["side1"]]
        print(f"   {len(v)} attempts; beaten (not goal-side 2.5 game s later) {len(lost)} ({100 * len(lost) / len(v):.0f}%): goal {100 * sum(bool(e['goal']) for e in lost) / max(1, len(lost)):.1f}%; "
              f"still goal-side: goal {100 * sum(bool(e['goal']) for e in v if e['side1']) / max(1, len(v) - len(lost)):.1f}%")


def main():
    args = sys.argv[1:]
    if args == ["--all"]:
        sys.path.insert(0, str(Path(__file__).resolve().parent / "scoring_map"))
        from lowload import breathe, gentle
        gentle()
        names = [p.stem for p in sorted(SD.DIRS[1].glob("*.js")) if p.stem != "season" and "_" in p.stem]
        totals = defaultdict(list)
        base = defaultdict(lambda: defaultdict(lambda: [0, 0, 0.0, 0]))
        holds = defaultdict(lambda: defaultdict(lambda: [0, 0, 0.0, 0]))
        for g in names:
            try:
                m = SD.load(g)
            except (FileNotFoundError, ValueError):
                continue
            if "owner" not in m:
                continue
            s = m.get("system", "genesis")
            ev, bl, hd = measure(m)
            for e in ev:
                e["game"] = g
            totals[s] += ev
            for into, src in ((base[s], bl), (holds[s], hd)):
                for (team, z), v in src.items():
                    for i in range(4):
                        into[z][i] += v[i]
            breathe()
        for s, ev in totals.items():
            combined(ev, base[s], holds[s], s)
        return
    ev_all, base_all = defaultdict(list), defaultdict(lambda: defaultdict(lambda: [0, 0, 0.0, 0]))
    hold_all = defaultdict(lambda: defaultdict(lambda: [0, 0, 0.0, 0]))
    for g in args:
        m = SD.load(g)
        ev, bl, hd = measure(m)
        for e in ev:
            e["game"] = g
        ab = m["abbr"]
        print(f"\n## {g}")
        for team in (0, 1):
            print("\n".join(lines(m, ev, bl, team)))
            ev_all[ab[team]] += [e for e in ev if e["team"] == team]
            for z in ZONES:
                for i in range(4):
                    base_all[ab[team]][z][i] += bl[(team, z)][i]
                    hold_all[ab[team]][z][i] += hd[(team, z)][i]
    for ab, ev in ev_all.items():
        combined(ev, base_all[ab], hold_all[ab], ab)


if __name__ == "__main__":
    main()
