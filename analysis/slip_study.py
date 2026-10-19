"""Pucks slipping under the goalie (Genesis; 2026-10-19, the user: hard low shots and fast passes sometimes go straight
under a goalie in a save move, or one a person pressed C with). checkpuckcoll .ccx tests a low puck (height <= 5, not
rising) against the goalie's stick first: within 14 of his blade it goes to puckstick, which for a goalie plays it only
within 8 and otherwise returns, so the body test (.chkgoalie) is skipped that frame. A low puck 8-14 from his blade
touches nothing, wherever his body is. Save moves put the blade out to one side; this looks at every low shot that
reached the goalie, sample by sample, while it was inside his body reach: was it in that blind ring?
python analysis/slip_study.py"""
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "analysis")
sys.path.insert(0, "tools")
from goalie_study import games, goalie, pos, anim, clock, K  # noqa: E402
import uncounted_study as U  # noqa: E402
import xg  # noqa: E402
from systems import genesis  # noqa: E402

SAVE = {a for a, v in genesis.SAVE_MOVES.items()}


def reach_of(m, rows, f, g, sh):
    w = xg._work(rows, f, g) or [64, 15, 15, 11, 15, 0]
    r = xg.REACH[min(19, (w[1] + 2) >> 1)]
    if (m["ctrl"][f] >> g) & 1:
        r = 15
    if sh["kind"] == "one-timer":
        r = 12
    if anim(m, f, g) in xg.PAD_STACK:
        r = 18
    return r


def main():
    tab = Counter()
    rows_out = []
    for name, m in games("genesis"):
        R = U.rom(m.get("rom"))
        if R is None or not m.get("work"):
            continue
        rows = {}
        for r in m["work"]:
            rows.setdefault(r[1], []).append(r)
        P = m["puck"]
        for sh in m["shotList"]:
            if sh["result"] not in ("goal", "save"):
                continue
            g = goalie(m, sh["f"], 1 - sh["team"])
            if g is None:
                continue
            f1 = min(len(m["t"]) - 2, sh.get("resolved", sh["f"]) + 2)
            inside, blind, stick = 0, 0, 0
            moving = None
            T = m["t"]
            past = False
            for f in range(sh["f"], f1):
                if past:
                    break
                n = max(1, round((T[f + 1] - T[f]) / 16.7))  # game frames between the two samples
                b0 = U.blade(m, R, f, g)
                g0, g1 = pos(m, f, g), pos(m, f + 1, g)
                r = reach_of(m, rows, f, g, sh)
                moving = moving or (anim(m, f, g) if anim(m, f, g) in SAVE else None)
                for j in range(1, n + 1):
                    a_ = j / n
                    px = P[3 * f] + a_ * (P[3 * f + 3] - P[3 * f])
                    py = P[3 * f + 1] + a_ * (P[3 * f + 4] - P[3 * f + 1])
                    pz = P[3 * f + 2] + a_ * (P[3 * f + 5] - P[3 * f + 2])
                    gx, gy = g0[0] + a_ * (g1[0] - g0[0]), g0[1] + a_ * (g1[1] - g0[1])
                    if abs(py) >= 261:  # the net's front: in, or past him (a goal is decided there)
                        past = True
                        break
                    if b0:
                        bx, by = b0[0] + gx - g0[0], b0[1] + gy - g0[1]
                    low = pz <= 5
                    in_box = b0 and abs(bx - px) <= 14 and abs(by - py) <= 14 and (bx - px) ** 2 + (by - py) ** 2 <= 196
                    if low and in_box:
                        if (bx - px) ** 2 + (by - py) ** 2 <= 64:
                            stick += 1
                        elif math.hypot(px - gx, py - gy) <= r:
                            blind += 1
                        continue
                    if pz <= 15 and math.hypot(px - gx, py - gy) <= r:
                        inside += 1
            if not (inside or blind or stick):
                continue
            in_move = moving is not None
            state = "save move" if in_move else "standing"
            who = "person" if (m["ctrl"][sh["f"]] >> g) & 1 else "cpu"
            kind = "touched" if inside or stick else "only the blind ring" if blind else "never in reach"
            tab[(sh["result"], state, kind)] += 1
            if sh["result"] == "goal" and not (inside or stick):
                rows_out.append((name[:22], clock(m, sh["f"]), sh["kind"], sh["speed"], state, who, f"blind frames {blind}"))
    print("Shots that reached the goalie (frame by frame): did any frame touch his body or stick, or only the blind ring?")
    for res in ("goal", "save"):
        for st in ("standing", "save move"):
            c = [tab[(res, st, k)] for k in ("touched", "only the blind ring")]
            print(f"  {res:5} goalie {st:9}: body or stick frames {c[0]:3}, only blind-ring frames {c[1]:3}")
    print("\nGoals that went through his body reach entirely in the blind ring:")
    for r in rows_out:
        print("  ", *r)


if __name__ == "__main__":
    main()
