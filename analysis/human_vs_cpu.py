"""How people play NHL '94, and how their skaters differ from the computer's (2026-11-11, the user). Every recorded game
in Documents\\NHL94 Viewer (people on both sides), per system. Each sample's `ctrl` marks the records a person controls;
the converter's events carry `human` (shots, passes, hits) and `gctl` (the goalie at a shot: a person or the computer).
The person's skater versus his five computer teammates, in the same games:

- Possession: of the time a team has the puck, the share with a person's skater carrying it.
- Shots, passes, hits: the share by a person's skater; shots' xG, goals, kinds and distance; passes completed.
- Skating: each skater's speed (from his position over 6 samples, about 0.1 s), the person's against the computer teammates'
  (skaters on the ice, play running: the clock moving); the share of time at a sprint (over 1.25 x the median).
- Defence: while the other team carries the puck, the distance from the carrier to the person's skater and to the
  nearest and the average computer teammate; how often the person's skater is the nearest of his team.
- Goalies: shots faced with a person in net against the computer, goals against xG.
- How people attack: shots a game, the share that are one-timers, slapshots, from rushes; xG a shot.

Prints the tables; names nobody (the games are the user's league's, but no coach is named).

python analysis/human_vs_cpu.py"""
import json
import math
import os
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

MATCHES = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents" / "NHL94 Viewer")) / "matches"


def load():
    for f in sorted(MATCHES.glob("*.js")):
        if f.name == "season.js":
            continue
        t = f.read_text(encoding="utf-8")
        try:
            m = json.loads(t[t.index("{"):t.rindex("}") + 1])
        except ValueError:
            continue
        if len(m.get("t", [])) > 3000:
            yield f.stem, m


def main():
    S = {s: defaultdict(Counter) for s in ("genesis", "snes")}
    speeds = {s: {"p": [], "c": []} for s in S}
    dists = {s: {"p": [], "near": [], "avg": [], "p_nearest": 0, "n": 0} for s in S}
    xg = {s: {"p": [], "c": []} for s in S}
    shotd = {s: {"p": [], "c": []} for s in S}
    games = Counter()
    for name, m in load():
        s = m.get("system", "genesis")
        games[s] += 1
        N, P, ctrl, own, roles, clock = len(m["t"]), m["pos"], m["ctrl"], m["owner"], m.get("role", ""), m["clock"]
        T = m["t"]
        on = lambda i, k: roles[i * 12 + k] not in ("x", "g") if isinstance(roles, str) and len(roles) >= N * 12 else True
        goalie = lambda i, k: isinstance(roles, str) and len(roles) >= N * 12 and roles[i * 12 + k] == "g"
        xy = lambda i, k: (P[(i * 12 + k) * 2], P[(i * 12 + k) * 2 + 1])
        c = S[s]["poss"]
        for i in range(1, N):
            if clock[i] == clock[i - 1] and i % 30:
                pass
            o = own[i]
            if o >= 0:
                c["person" if ctrl[i] >> o & 1 else "computer"] += 1
            # skating speed and defence, every 6th sample with the clock running
            if i % 6 or clock[i] == clock[max(0, i - 30)]:
                continue
            # over 6 samples (about 0.1 s): the SNES game moves its objects every other frame
            dt = (T[i] - T[i - 6]) / 1000
            if not 0.05 < dt < 0.25:
                continue
            for k in range(12):
                if goalie(i, k) or not on(i, k):
                    continue
                (x0, y0), (x1, y1) = xy(i - 6, k), xy(i, k)
                v = math.hypot(x1 - x0, y1 - y0) / dt
                if v < 2000:
                    speeds[s]["p" if ctrl[i] >> k & 1 else "c"].append(v)
            if o >= 0:
                cx, cy = xy(i, o)
                defend = range(6, 12) if o < 6 else range(0, 6)
                pers = [k for k in defend if ctrl[i] >> k & 1 and not goalie(i, k)]
                comp = [k for k in defend if not ctrl[i] >> k & 1 and not goalie(i, k) and on(i, k)]
                if len(pers) == 1 and comp:
                    d = lambda k: math.hypot(xy(i, k)[0] - cx, xy(i, k)[1] - cy)
                    dp, dc = d(pers[0]), [d(k) for k in comp]
                    dists[s]["p"].append(dp)
                    dists[s]["near"].append(min(dc))
                    dists[s]["avg"].append(sum(dc) / len(dc))
                    dists[s]["p_nearest"] += dp < min(dc)
                    dists[s]["n"] += 1
        for x in m.get("shotList", []):
            who = "p" if x.get("human") else "c"
            S[s]["shots"][who] += 1
            S[s]["goals"][who] += x.get("result") == "goal"
            S[s]["kinds_" + who][x.get("kind") if x.get("kind") != "shot" else x.get("type", "shot")] += 1
            if isinstance(x.get("xg"), (int, float)):
                xg[s][who].append(x["xg"])
            shotd[s][who].append(math.hypot(x["x"], (x["y"] if x["y"] >= 0 else -x["y"]) - 264))
            S[s]["origin"][x.get("origin")] += 1
            g = x.get("gctl")
            if g:
                S[s]["gshots"][g] += 1
                S[s]["ggoals"][g] += x.get("result") == "goal"
                if isinstance(x.get("xg"), (int, float)):
                    S[s]["gxg"][g] += x["xg"]
        for p in m.get("passes", []):
            who = "p" if p.get("human") else "c"
            S[s]["passes"][who] += 1
            S[s]["completed"][who] += p.get("result") == "completed"
        for h in m.get("hits", []):
            S[s]["hits"]["p" if h.get("human") else "c"] += 1
            S[s]["downs"]["p" if h.get("human") else "c"] += h.get("outcome") in ("knocked down", "upended", "into the boards", "into the bench")
    for s in ("genesis", "snes"):
        if not games[s]:
            continue
        D = S[s]
        pc = lambda a, b: f"{100 * a / b:.1f}%" if b else "-"
        print(f"\n===== {s}: {games[s]} recorded games (people on both sides)")
        poss = D["poss"]
        print(f"Possession: the puck carried by a person's skater {pc(poss['person'], poss['person'] + poss['computer'])} of the time")
        sh = D["shots"]
        print(f"Shots (attempts): person {sh['p']}, computer teammates {sh['c']} ({pc(sh['p'], sh['p'] + sh['c'])} by people); "
              f"goals {D['goals']['p']} / {D['goals']['c']}")
        for who, lab in (("p", "person"), ("c", "computer")):
            if xg[s][who]:
                print(f"  {lab}: xG a shot {st.mean(xg[s][who]):.3f}; median distance {st.median(shotd[s][who]):.0f}; kinds "
                      + ", ".join(f"{k} {v}" for k, v in D['kinds_' + who].most_common(5)))
        o = D["origin"]
        print("  shot origins (all): " + ", ".join(f"{k} {pc(v, sum(o.values()))}" for k, v in o.most_common(6)))
        pa = D["passes"]
        print(f"Passes: person {pa['p']} ({pc(D['completed']['p'], pa['p'])} completed), computer {pa['c']} "
              f"({pc(D['completed']['c'], pa['c'])} completed)")
        hi = D["hits"]
        print(f"Hits (knockdowns counted by the game): person {hi['p']}, computer {hi['c']} ({pc(hi['p'], hi['p'] + hi['c'])} by people)")
        sp = speeds[s]
        if sp["p"] and sp["c"]:
            med = st.median(sp["p"] + sp["c"])
            print(f"Skating speed (units a second, clock running): person median {st.median(sp['p']):.0f}, computer "
                  f"{st.median(sp['c']):.0f}; at a sprint (> {1.25 * med:.0f}): person {pc(sum(v > 1.25 * med for v in sp['p']), len(sp['p']))}, "
                  f"computer {pc(sum(v > 1.25 * med for v in sp['c']), len(sp['c']))}; standing (< 50): person "
                  f"{pc(sum(v < 50 for v in sp['p']), len(sp['p']))}, computer {pc(sum(v < 50 for v in sp['c']), len(sp['c']))}")
        d = dists[s]
        if d["n"]:
            print(f"Defending (the other team carrying): the person's skater to the carrier median {st.median(d['p']):.0f}, the "
                  f"nearest computer teammate {st.median(d['near']):.0f}, the average one {st.median(d['avg']):.0f}; the person's "
                  f"skater the nearest of his team {pc(d['p_nearest'], d['n'])} of the time")
        gs, gg, gx = D["gshots"], D["ggoals"], D["gxg"]
        for g in sorted(gs):
            print(f"Goalie '{g}': {gs[g]} shots faced, {gg[g]} goals against xG {gx[g]:.1f}")
        print(f"Per game: shot attempts {sum(sh.values()) / games[s] / 2:.1f} a team, passes {sum(pa.values()) / games[s] / 2:.1f}, "
              f"hits {sum(hi.values()) / games[s] / 2:.1f}")


if __name__ == "__main__":
    main()
