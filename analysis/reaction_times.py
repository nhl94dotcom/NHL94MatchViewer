"""Reaction times in the recorded Genesis games (2026-11-14; the user, after a top community member's list of what
wins: game knowledge, mechanics, decisions, execution, reaction time, luck).

Games with a person on both sides (season summaries' humans; the bot's games left out), both pads recorded
(controller 1 / 2: $BEEF / $BEF1, held buttons: $08 Right, $04 Left, $02 Down, $01 Up; each pad's team padTeam /
pad2Team). Each pad's skater: the record of its team in ctrl (one bit per person-controlled record), not a goalie
(role 0). Live play only (the clock running between the two samples). Times in real seconds (split-second timings:
the recordings' own clock, about 60 samples a second, not frame-locked: +-17 ms).

  loose      the puck comes loose (owner -1 after a carrier) and stays loose 0.3 s or more: from then until the pad's
             direction points within 45 degrees of the puck from its skater (held 3 samples). Only when it didn't
             already point there when the puck came loose, and the puck is within 150 units of the skater.
  turnover   the converter's turnovers (the other team's carrier has the puck, from the pad's team): from then until
             the pad points within 45 degrees of the new carrier (held 3 samples); the same conditions.
  shot       an opponent's shot (shotList, attempts on goal and wide): until the defending pad's input first changes
             (any button or direction): for a person who takes the goalie, the reaction to the shot.
Each reaction capped at 1.5 s (longer: counted as no reaction). Per side-game: the median of each. Then: the user's
side ("you" in the summary) against the opponents, and each measure's medians on the winning side against the
losing side of the same game (paired).

python analysis/reaction_times.py [--list]"""
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import season  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
CAP, HOLD, NEAR, CONE = 1.5, 3, 150, 45


def direction(pad):
    x = (1 if pad & 8 else 0) - (1 if pad & 4 else 0)
    y = (1 if pad & 1 else 0) - (1 if pad & 2 else 0)
    return (x, y) if (x or y) else None


def within(d, vx, vy):
    if d is None or (vx == 0 and vy == 0):
        return False
    a = math.degrees(math.atan2(d[1], d[0]) - math.atan2(vy, vx))
    a = (a + 180) % 360 - 180
    return abs(a) <= CONE


def games():
    for f in sorted((HOME / "matches").glob("*.summary.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        if s.get("system", "genesis") != "genesis" or s.get("bot") or not all(s.get("humans", [False, False])):
            continue
        js = f.with_name(f.name.replace(".summary.json", ".js"))
        if js.exists():
            yield js, s


def side_reactions(m):
    """{team: {measure: [seconds]}} for both pads of one game."""
    t = m["t"]
    N = len(t)
    if not m.get("pad") or not m.get("pad2"):
        return None
    P = np.array(m["pos"], float).reshape(N, 12, 2)
    K = np.array(m["puck"], float).reshape(N, 3)
    owner, ctrl, clock = m["owner"], m["ctrl"], m["clock"]
    roles = m.get("role", "")
    pads = {m["padTeam"]: m["pad"], m["pad2Team"]: m["pad2"]}
    if len(pads) < 2:
        return None
    # live play: the clock reads differently 30 samples (about half a second) before and after (a game second is
    # 24 frames: it ticks within any such window while it runs)
    running = [clock[max(0, i - 30)] != clock[min(N - 1, i + 30)] for i in range(N)]

    def skater(team, i):
        bits = [k for k in range(6 * team, 6 * team + 6) if ctrl[i] >> k & 1]
        bits = [k for k in bits if not (len(roles) == 12 and roles[k] == "0") and P[i, k, 0] < 300]
        return bits[0] if bits else None

    def react(team, i0, target):
        """seconds from sample i0 until the pad points at target(i) (from its skater) for HOLD samples."""
        pad = pads[team]
        k = skater(team, i0)
        if k is None:
            return None
        tx, ty = target(i0)
        vx, vy = tx - P[i0, k, 0], ty - P[i0, k, 1]
        if math.hypot(vx, vy) > NEAR or within(direction(pad[i0]), vx, vy):
            return None
        run = 0
        for i in range(i0 + 1, N):
            if t[i] - t[i0] > CAP * 1000 or not running[i]:
                return None
            k = skater(team, i) or k
            tx, ty = target(i)
            if within(direction(pad[i]), tx - P[i, k, 0], ty - P[i, k, 1]):
                run += 1
                if run >= HOLD:
                    return (t[i - HOLD + 1] - t[i0]) / 1000
            else:
                run = 0
        return None

    out = {0: defaultdict(list), 1: defaultdict(list)}
    for i in range(1, N - 1):
        if not running[i]:
            continue
        o0, o1 = owner[i - 1], owner[i]
        if o0 >= 0 and o1 == -1:
            j = i
            while j < N and owner[j] == -1 and t[j] - t[i] < 300:
                j += 1
            if j < N and owner[j] == -1:
                for team in (0, 1):
                    r = react(team, i, lambda q: (K[q, 0], K[q, 1]))
                    if r is not None:
                        out[team]["loose"].append(r)
    for tv in m.get("turnovers", []):                  # the converter's turnovers: f, the new carrier's sample
        i, lost = tv["f"], tv.get("from")
        if lost not in (0, 1) or i >= N or not running[i] or owner[i] < 0:
            continue
        r = react(lost, i, lambda q, c=owner[i]: (P[q, c, 0], P[q, c, 1]))
        if r is not None:
            out[lost]["turnover"].append(r)
    for s in m.get("shotList", []):
        i0 = s["f"]
        if s.get("result") not in ("goal", "save", "wide", "post") or i0 + 1 >= N:
            continue
        team = 1 - s["team"]
        pad = pads[team]
        for i in range(i0 + 1, N):
            if t[i] - t[i0] > CAP * 1000:
                break
            if pad[i] != pad[i0]:
                out[team]["shot"].append((t[i] - t[i0]) / 1000)
                break
    return out


def main():
    rows = []
    for js, s in games():
        try:
            m = season.load_match(js)
        except Exception:
            continue
        r = side_reactions(m)
        if r is None:
            continue
        gf = [tm["gf"] for tm in s["teams"]]
        for team in (0, 1):
            rows.append({"game": js.stem, "team": team, "you": s.get("you") == team,
                         "won": gf[team] > gf[1 - team], "lost": gf[team] < gf[1 - team],
                         **{k: (float(np.median(v)) if len(v) >= 5 else None) for k, v in r[team].items()},
                         **{f"n_{k}": len(v) for k, v in r[team].items()}})
    measures = ("loose", "turnover", "shot")
    print(f"{len(rows) // 2} games with a person on each side and both pads recorded\n")
    print("| median reaction (s, real) | you | opponents |\n|---|---|---|")
    for k in measures:
        a = [r[k] for r in rows if r.get(k) is not None and r["you"]]
        b = [r[k] for r in rows if r.get(k) is not None and not r["you"]]
        print(f"| {k} | {np.median(a):.3f} ({len(a)} games) | {np.median(b):.3f} ({len(b)} games) |" if a and b else f"| {k} | - | - |")
    print("\nThe same game's two sides (paired): the winner's median minus the loser's (negative: the winner reacted faster)")
    by = defaultdict(dict)
    for r in rows:
        by[r["game"]][r["team"]] = r
    for k in measures:
        d = []
        for g in by.values():
            if len(g) == 2:
                w = next((x for x in g.values() if x["won"]), None)
                l = next((x for x in g.values() if x["lost"]), None)
                if w and l and w.get(k) is not None and l.get(k) is not None:
                    d.append(w[k] - l[k])
        if d:
            d = np.array(d)
            se = d.std(ddof=1) / math.sqrt(len(d)) if len(d) > 1 else float("nan")
            faster = np.mean(d < 0)
            print(f"  {k}: {len(d)} games, mean {d.mean():+.3f} s (+-{se:.3f}), the winner faster in {faster:.0%}")
    if "--list" in sys.argv:
        for r in rows:
            print(r)


if __name__ == "__main__":
    main()
