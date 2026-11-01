"""Keeping the other team out of the slot (2026-11-01, the user's hypothesis: the key on defence is keeping the other
team, and above all the puck, out of your slot, more than having your own skaters stand in it). Genesis games named on
the command line. Every quarter second while a team has the puck in the other's end (past the blue line, Y +-89), the
state is classed: the carrier in the slot; else an attacker without the puck in the slot with no defender within 20
(an open one-timer target); else an attacker in the slot but covered; else nobody attacking in the slot. Also counted:
the defenders standing in the slot. The outcome: the attacking team's shots in the next 3 s (blocked ones too), their
xG and goals. Per state and per defending team, and how much of each team's defending time was in each state.
The slot: within 35 of the middle and 100 (about 33 feet) of the goal line.
python analysis/slot_defence.py <match> ...   (matches/ or Documents/NHL94 Viewer/matches)"""
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402

K, ZONE, STEP_MS, AHEAD_MS = 12, 89, 250, 3000
DIRS = [Path("matches"), Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches"))]


def load(name):
    for d in DIRS:
        if (d / f"{name}.js").exists():
            return json.loads(load_js_object(d / f"{name}.js"))
    raise FileNotFoundError(name)



def main():
    games = sys.argv[1:]
    stats = defaultdict(lambda: [0, 0, 0.0, 0])          # (team defending, state) -> samples, shots, xG, goals
    for g in games:
        m = load(g)
        abbr = g.split("_")[2].split("-")                  # home, away
        T, P, R, O = m["t"], m["pos"], m["role"], m["owner"]
        shots = sorted((sh["f"], sh["team"], sh.get("xg") or 0.0, sh["result"] == "goal") for sh in m["shotList"]
                       if sh["team"] in (0, 1))
        last = -STEP_MS
        for f in range(len(T)):
            if T[f] - last < STEP_MS:
                continue
            o = O[f]
            if o is None or o < 0 or o >= 12:
                continue
            a = 0 if o < 6 else 1
            d = 1 - a
            gk = next((k for k in range(d * 6, d * 6 + 6) if R[f * K + k] == "0"), None)
            if gk is None:
                continue
            s = 1 if P[(f * K + gk) * 2 + 1] > 0 else -1       # the defending team's net: +Y or -Y
            xy = lambda k: (P[(f * K + k) * 2], P[(f * K + k) * 2 + 1])
            cx, cy = xy(o)
            if s * cy < ZONE:
                continue
            last = T[f]
            slot = lambda x, y: abs(x) <= 35 and 0 <= 264 - s * y <= 100
            skaters = lambda team: [k for k in range(team * 6, team * 6 + 6) if R[f * K + k] not in ("0", "x")]
            defs = [xy(k) for k in skaters(d)]
            n_def = sum(slot(*p) for p in defs)
            if slot(cx, cy):
                state = "the carrier in the slot"
            else:
                state = "nobody attacking in the slot"
                for k in skaters(a):
                    if k == o or not slot(*xy(k)):
                        continue
                    x, y = xy(k)
                    covered = any(math.hypot(x - px, y - py) <= 20 for px, py in defs)
                    if not covered:
                        state = "an open attacker in the slot (no puck)"
                        break
                    state = "a covered attacker in the slot (no puck)"
            if state == "nobody attacking in the slot":
                state += f", {min(n_def, 2)}{'+' if n_def >= 2 else ''} defender(s) in it"
            st = stats[(abbr[d], state)]
            st[0] += 1
            for sf, team, xg, goal in shots:
                if team == a and f <= sf and T[sf] - T[f] <= AHEAD_MS:
                    st[1] += 1
                    st[2] += xg
                    st[3] += goal
    order = ["the carrier in the slot", "an open attacker in the slot (no puck)",
             "a covered attacker in the slot (no puck)", "nobody attacking in the slot, 0 defender(s) in it",
             "nobody attacking in the slot, 1 defender(s) in it", "nobody attacking in the slot, 2+ defender(s) in it"]
    print(f"Games: {', '.join(games)}\nEvery {STEP_MS} ms with the puck in the defending team's end; outcome: the attackers' "
          f"shots in the next {AHEAD_MS // 1000} s (overlapping windows: a shot counts at every sample before it)\n")
    for team in sorted({k[0] for k in stats}) + ["both"]:
        rows = {st: [sum(v[i] for (t, s_), v in stats.items() if s_ == st and (team == "both" or t == team))
                     for i in range(4)] for st in order}
        total = sum(r[0] for r in rows.values())
        print(f"{team} defending ({total * STEP_MS / 1000:.0f} s with the puck in its end):")
        print(f"  {'state':52} {'time':>6} {'share':>6} {'shots in 3 s':>12} {'xG in 3 s':>9} {'a goal in 3 s':>13}")
        for st in order:
            n, sh, xg, gl = rows[st]
            if n:
                print(f"  {st:52} {n * STEP_MS / 1000:5.0f}s {100 * n / total:5.0f}% {sh / n:12.2f} {xg / n:9.3f} {100 * gl / n:12.1f}%")
        print()


if __name__ == "__main__":
    main()
