"""Keeping the other team out of the slot (2026-11-01, the user's hypothesis: the key on defence is keeping the other
team, and above all the puck, out of your slot, more than having your own skaters stand in it). Genesis games named on
the command line. Every quarter second while a team has the puck in the other's end (past the blue line, Y +-89), the
state is classed: the carrier in the slot; else an attacker without the puck in the slot with no defender within 20
(an open one-timer target); else an attacker in the slot but covered; else nobody attacking in the slot. Also counted:
the defenders standing in the slot. The outcome: the attacking team's shots in the next 3 s (blocked ones too), their
xG and goals. Per state and per defending team, and how much of each team's defending time was in each state.
Also each one-timer: from the slot or not, and whether its receiver was open (no defender skater within 20) when the
pass left (the last sample his team had the puck, up to 1.5 s back).
The slot: within 35 of the middle and 100 (about 33 feet) of the goal line.
python analysis/slot_defence.py <match> ...   (matches/ or Documents/NHL94 Viewer/matches)
python analysis/slot_defence.py --all          (every Genesis game in Documents/NHL94 Viewer/matches)"""
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
    if games == ["--all"]:
        games = []
        for p in sorted(DIRS[1].glob("*.js")):
            if p.stem == "season" or "_" not in p.stem:
                continue
            with open(p, encoding="utf-8") as fh:
                head = fh.read(4000)
            if '"system": "snes"' in head or '"system":"snes"' in head:
                continue
            games.append(p.stem)
    stats = defaultdict(lambda: [0, 0, 0.0, 0])          # (team defending, state) -> samples, shots, xG, goals
    ot = defaultdict(lambda: [0, 0, 0.0])                 # (slot?, open?) -> one-timers, goals, xG
    used = []
    for g in games:
        try:
            m = load(g)
        except (FileNotFoundError, ValueError):
            continue
        if m.get("system") == "snes" or "owner" not in m:
            continue
        used.append(g)
        abbr = [m.get("abbr", ["H", "A"])[0], m.get("abbr", ["H", "A"])[1]] if isinstance(m.get("abbr"), list) else g.split("_")[2].split("-")
        T, P, R, O = m["t"], m["pos"], m["role"], m["owner"]
        shots = sorted((sh["f"], sh["team"], sh.get("xg") or 0.0, sh["result"] == "goal") for sh in m["shotList"]
                       if sh["team"] in (0, 1))
        for sh in m["shotList"]:
            if sh["kind"] != "one-timer" or sh["team"] not in (0, 1):
                continue
            f, team = sh["f"], sh["team"]
            ny = 264 if sh["y"] > 0 else -264
            sl = abs(sh["x"]) <= 35 and abs(ny - sh["y"]) <= 100
            f0 = f
            while f0 > 0 and T[f] - T[f0] < 1500 and not (O[f0] is not None and 0 <= O[f0] < 12 and (O[f0] < 6) == (team == 0)):
                f0 -= 1
            k = min(range(team * 6, team * 6 + 6), key=lambda k: math.hypot(P[(f * K + k) * 2] - sh["x"], P[(f * K + k) * 2 + 1] - sh["y"]))
            x0, y0 = P[(f0 * K + k) * 2], P[(f0 * K + k) * 2 + 1]
            near = min((math.hypot(P[(f0 * K + j) * 2] - x0, P[(f0 * K + j) * 2 + 1] - y0)
                        for j in range((1 - team) * 6, (1 - team) * 6 + 6) if R[f0 * K + j] not in ("0", "x")), default=99)
            o_ = ot[(sl, near > 20)]
            o_[0] += 1
            o_[1] += sh["result"] == "goal"
            o_[2] += sh.get("xg") or 0.0
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
    names = ", ".join(used) if len(used) <= 8 else f"{used[0]} ... {used[-1]}"
    print(f"Games ({len(used)}): {names}")
    print(f"Every {STEP_MS} ms with the puck in the defending team's end; outcome: the attackers' "
          f"shots in the next {AHEAD_MS // 1000} s (overlapping windows: a shot counts at every sample before it)\n")
    teams = sorted({k[0] for k in stats}) if len(used) <= 8 else []
    for team in teams + ["both"]:
        rows = {st: [sum(v[i] for (t, s_), v in stats.items() if s_ == st and (team == "both" or t == team))
                     for i in range(4)] for st in order}
        total = sum(r[0] for r in rows.values())
        print(f"{'all teams' if team == 'both' else team} defending ({total * STEP_MS / 1000:.0f} s with the puck in its end):")
        print(f"  {'state':52} {'time':>6} {'share':>6} {'shots in 3 s':>12} {'xG in 3 s':>9} {'a goal in 3 s':>13}")
        for st in order:
            n, sh, xg, gl = rows[st]
            if n:
                print(f"  {st:52} {n * STEP_MS / 1000:5.0f}s {100 * n / total:5.0f}% {sh / n:12.2f} {xg / n:9.3f} {100 * gl / n:12.1f}%")
        print()

    print("One-timers, the receiver at the pass:")
    for sl in (True, False):
        for op in (True, False):
            n, gl, xg = ot[(sl, op)]
            if n:
                print(f"  from {'the slot' if sl else 'outside the slot':16} receiver {'open' if op else 'covered':7}: {n:4} shots, "
                      f"{gl:3} goals ({100 * gl / n:.0f}%), xG {xg:.1f} ({xg / n:.2f} each)")


if __name__ == "__main__":
    main()
