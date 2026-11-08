"""Loose pucks: who the computer's skaters win them for (2026-11-08; docs/GAME_VARIABLES_PLAN.md study 7: "which team the
AI picks up a loose puck for").

The recorded games with a person on each side (both systems). A loose spell: the puck nobody's (owner -1 or none) for at least 0.1 s with the
clock running, ended by a player taking it within 3 s. Who took it: a person's skater (the person had him just before
he reached it: control moves to the carrier at the pickup), a computer skater, or a goalie, and for which team. Then, for the pucks the computer's skaters won:
- each team's share in each game, against the difference in its skaters' Offensive + Defensive Awareness (the roster
  steps, the ratings the computer's chase and reactions run on: GENESIS_MECHANICS 12, SNES_MECHANICS 12);
- by the score at the time (leading, tied, trailing): a catch-up would show the trailing team's computer winning more.

python analysis/loose_pucks.py"""
import json
import os
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")


def main():
    res = defaultdict(lambda: defaultdict(int))
    pairs = defaultdict(list)          # system -> (awareness difference, share of the computer's wins)
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season" or p.stem.endswith(".heat") or not (HOME / "captures" / p.stem).is_dir():
            continue
        m = json.loads(load_js_object(p))
        sysn = m.get("system", "genesis")
        if not (m.get("pad") and m.get("pad2") and {m.get("padTeam"), m.get("pad2Team")} == {0, 1}):
            continue                                       # a person on each side only (against the computer, its
            # team mostly trails, which would mix the score in)
        t, owner, clock, ctrl, role = m["t"], m["owner"], m["clock"], m["ctrl"], m["role"]
        N = len(t)
        won = [0, 0]
        i = 1
        while i < N:
            if owner[i] is not None and owner[i] >= 0:
                i += 1
                continue
            j = i
            while j < N and (owner[j] is None or owner[j] < 0):
                j += 1
            if j >= N:
                break
            if t[j] - t[i] < 100 or t[j] - t[i] > 3000 or clock[j] == clock[i] and t[j] - t[i] > 1500:
                i = j
                continue
            k = owner[j]
            team = k // 6
            if role[j * 12 + k] == "0":
                who = "goalie"
            elif ctrl[j - 1] >> k & 1:                    # who had him as he reached it (control moves to the
                # carrier the moment his team has the puck, so the bit at the pickup itself says little)
                who = "person"
            else:
                who = "computer"
            res[sysn][who] += 1
            if who == "computer":
                won[team] += 1
                d = m["score"][2 * j + team] - m["score"][2 * j + 1 - team]
                res[sysn]["computer, " + ("leading" if d > 0 else "trailing" if d < 0 else "tied")] += 1
            i = j
        if sum(won) >= 10:
            aw = []
            for team in (0, 1):
                v = [r["a"][3] + r["a"][4] for r in m["rosters"][team] if not r.get("g") and len(r.get("a", [])) > 4]
                aw.append(st.mean(v) if v else 0)
            pairs[sysn].append((aw[0] - aw[1], won[0] / sum(won)))
    for sysn in sorted(res):
        r = res[sysn]
        tot = r["person"] + r["computer"] + r["goalie"]
        print(f"{sysn.upper()}: {tot} loose pucks taken: by a person's skater {r['person']}, a computer skater "
              f"{r['computer']}, a goalie {r['goalie']}")
        c = r["computer"]
        print(f"  the computer's skaters' wins by their team's score: leading {r['computer, leading']} "
              f"({r['computer, leading'] / c:.0%}), tied {r['computer, tied']}, trailing {r['computer, trailing']} "
              f"({r['computer, trailing'] / c:.0%})")
        pr = pairs[sysn]
        if len(pr) > 3:
            shares = [s for _, s in pr]
            print(f"  per game ({len(pr)} games with 10+): the home team's computer won {st.mean(shares):.0%} on average "
                  f"(spread {st.pstdev(shares):.0%}); correlation with the awareness difference {st.correlation([a for a, _ in pr], shares):+.2f}")


if __name__ == "__main__":
    main()
