"""What skaters do when the puck crosses a blue line, and the "step out and come back" move (the user's league plays
with offsides off: carry the puck out of the attacking zone for a moment, drawing the defenders up, then turn and carry
it straight back in). Finds every carry out of the attacking zone that comes back in within REENTRY_MS with the other
team never touching the puck, and compares the defenders there with ordinary carried entries from the neutral zone.
Both systems. python analysis/blue_line_study.py"""
import math
import statistics as st
import sys
from collections import defaultdict

sys.path.insert(0, "tools")
from goalie_study import games, role, pos  # noqa: E402
from export_match import own_end  # noqa: E402

K = 12
BLUE = 88
REENTRY_MS = 4000
GAP_MS = 500   # a pass or a bobble inside the move: the puck may be loose this long


def team_of(k):
    return 0 if k < 6 else 1


def u(m, f, k, e):
    """Distance up the ice toward the net the attacking team (own end e) attacks."""
    return pos(m, f, k)[1] * -e


def puck_u(m, f, e):
    return m["puck"][f * 3 + 1] * -e


def possession_runs(m):
    """Stretches (team, first, last) where one team has the puck, gaps with it loose up to GAP_MS allowed."""
    t, own = m["t"], m["owner"]
    runs, cur, start, last = [], None, None, None
    for f, k in enumerate(own):
        if 0 <= k <= 11:
            tm = team_of(k)
            if tm != cur or t[f] - t[last] > GAP_MS or m["puck"][f * 3 + 2] < -100:
                if cur is not None:
                    runs.append((cur, start, last))
                cur, start = tm, f
            last = f
        elif cur is not None and (t[f] - t[last] > GAP_MS or m["puck"][f * 3 + 2] < -100):
            runs.append((cur, start, last))
            cur = None
    if cur is not None:
        runs.append((cur, start, last))
    return runs


def defenders(m, f, team, e):
    """The defending team's skaters at sample f: {role letter: [(depth from their goal line, x, record)]}."""
    out = defaultdict(list)
    for k in range((1 - team) * 6, (1 - team) * 6 + 6):
        r = role(m, f, k)
        if r in "0x":
            continue
        name = {"1": "D", "2": "D", "3": "W", "5": "W", "4": "C"}.get(r)
        if name:
            out[name].append((264 - u(m, f, k, e), pos(m, f, k)[0] * -e, k))
    return out


def snapshot(m, f, team, e):
    """Defenders' mean depth by position, the puck's depth, and how many defending skaters are between the puck and
    their net (closer to their goal line than the puck)."""
    d = defenders(m, f, team, e)
    pd = 264 - puck_u(m, f, e)
    return {"D": st.mean(v[0] for v in d["D"]) if d["D"] else None,
            "W": st.mean(v[0] for v in d["W"]) if d["W"] else None,
            "C": st.mean(v[0] for v in d["C"]) if d["C"] else None,
            "puck": pd,
            "between": sum(1 for vs in d.values() for v in vs if v[0] < pd - 5)}


def outcome(m, team, f, until_ms=4000):
    t = m["t"]
    shots = [s for s in m["shotList"] if s["team"] == team and 0 <= t[s["f"]] - t[f] <= until_ms]
    goals = [g for g in m["goals"] if g["team"] == team and 0 <= t[g["f"]] - t[f] <= until_ms + 2000]
    return bool(shots), bool(goals)


def study(system):
    moves, plain = [], []
    for n, m in games(system):
        t = m["t"]
        for team, a, b in possession_runs(m):
            e = own_end(m, a, team)
            if e is None:
                continue
            # walk the run: zone state of the puck, out (exit) and back in (re-entry)
            inside = puck_u(m, a, e) > BLUE
            exit_f = None
            for f in range(a, b + 1):
                pu = puck_u(m, f, e)
                if inside and pu < BLUE - 5:
                    inside, exit_f = False, f
                elif not inside and pu > BLUE:
                    inside = True
                    if exit_f is not None and t[f] - t[exit_f] <= REENTRY_MS:
                        turn = min(range(exit_f, f + 1), key=lambda q: puck_u(m, q, e))
                        moves.append(dict(n=n, m=m, team=team, e=e, exit=exit_f, turn=turn, entry=f,
                                          before=max(a, exit_f - 1)))
                    elif exit_f is None:
                        plain.append(dict(n=n, m=m, team=team, e=e, entry=f))
                    exit_f = None
    return moves, plain


def fmt(v):
    return "  -  " if v is None else f"{v:5.0f}"


def main():
    for system in ("genesis", "snes"):
        moves, plain = study(system)
        print(f"== {system}: {len(moves)} carries out of the attacking zone and back in within {REENTRY_MS // 1000} s; "
              f"{len(plain)} entries from the neutral zone with no such exit")
        rows = defaultdict(list)
        for mv in moves:
            m, team, e = mv["m"], mv["team"], mv["e"]
            for lab in ("before", "turn", "entry"):
                rows[lab].append(snapshot(m, mv[lab], team, e))
            rows["entry+0.5s"].append(snapshot(m, min(len(m["t"]) - 1, mv["entry"] + 30), team, e))
        for p in plain:
            rows["plain entry"].append(snapshot(p["m"], p["entry"], p["team"], p["e"]))
        print("  defenders' depth from their own goal line (median units; the blue line is 176 out):")
        print("  moment            D      W      C    puck   skaters between puck and net (mean)")
        for lab in ("before", "turn", "entry", "entry+0.5s", "plain entry"):
            R = rows[lab]
            if not R:
                continue
            med = lambda key: st.median([r[key] for r in R if r[key] is not None]) if any(r[key] is not None for r in R) else None
            print(f"  {lab:14} {fmt(med('D'))}  {fmt(med('W'))}  {fmt(med('C'))}  {fmt(med('puck'))}   {st.mean(r['between'] for r in R):.2f}")
        for lab, L in (("step out and back in", moves), ("ordinary carried entry", plain)):
            oc = [outcome(x["m"], x["team"], x["entry"]) for x in L]
            if oc:
                print(f"  {lab:24} shot attempt within 4 s {sum(a for a, _ in oc)}/{len(oc)} ({100 * sum(a for a, _ in oc) / len(oc):.0f}%),"
                      f" goal within 6 s {sum(b for _, b in oc)}")
        for mv in moves[:40]:
            m = mv["m"]
            out_ms = m["t"][mv["entry"]] - m["t"][mv["exit"]]
            depth = 264 - puck_u(m, mv["turn"], mv["e"])
            c = m["clock"][mv["entry"]]
            print(f"    {mv['n'][:24]:24} P{m['period'][mv['entry']] + 1} {c // 60}:{c % 60:02d}  out {out_ms} ms, turned {depth:.0f} out")


if __name__ == "__main__":
    main()
