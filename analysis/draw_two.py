"""Drawing two defenders and freeing a teammate (2026-11-08; docs/GAME_VARIABLES_PLAN.md study 9, a first measure of
"elite players move the computer's skaters": the carrier pulls defenders onto himself so a teammate is left open).

The recorded games with a person on each side (both systems). A possession: a person's carrier with the puck in his
attacking zone (89 or more past centre), from when he has it until he loses it, passes or shoots. It "drew two" when
at some moment two or more of the other team's skaters were within 50 (about 17 ft) of him while a teammate in the
zone had none within 50. For each: the expected goals of his team's attempts (not blocked) from the possession's start
to 2 s after it ends. Then per team-game: how often its person drew two (per possession), and that against the
game's expected-goal difference (does the one who does it more make the better chances?).

python analysis/draw_two.py"""
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from export_match import own_end  # noqa: E402
from share_game import load_js_object  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
NEAR = 50


def main():
    out = defaultdict(lambda: {"drew": [0, 0.0], "not": [0, 0.0]})
    games = defaultdict(list)
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season" or p.stem.endswith(".heat") or not (HOME / "captures" / p.stem).is_dir():
            continue
        m = json.loads(load_js_object(p))
        if not (m.get("pad") and m.get("pad2") and {m.get("padTeam"), m.get("pad2Team")} == {0, 1}):
            continue
        sysn = m.get("system", "genesis")
        t, owner, pos, role, ctrl = m["t"], m["owner"], m["pos"], m["role"], m["ctrl"]
        N = len(t)
        P = lambda f, k: (pos[(f * 12 + k) * 2], pos[(f * 12 + k) * 2 + 1])
        shots = [s for s in m.get("shotList", []) if s.get("team") in (0, 1) and s["result"] != "blocked" and s.get("xg") is not None]
        per_team = [[0, 0], [0, 0]]
        i = 0
        while i < N:
            k = owner[i]
            if k is None or k < 0 or k >= 12 or role[i * 12 + k] not in "12345" or not ctrl[i] >> k & 1:
                i += 1
                continue
            team = k // 6
            e = own_end(m, i, team)                       # his own end: the attacking zone is the other side
            if P(i, k)[1] * e > -89:
                i += 1
                continue
            j, drew = i, False
            while j < N and owner[j] == k and P(j, k)[1] * e <= -89:
                if j % 2 == 0:
                    x, y = P(j, k)
                    opp = [P(j, d) for d in range(6 * (1 - team), 6 * (1 - team) + 6) if role[j * 12 + d] in "12345"]
                    if sum(1 for o in opp if math.dist(o, (x, y)) < NEAR) >= 2:
                        for mate in range(6 * team, 6 * team + 6):
                            if mate == k or role[j * 12 + mate] not in "12345":
                                continue
                            q = P(j, mate)
                            if q[1] * e <= -89 and all(math.dist(o, q) >= NEAR for o in opp):
                                drew = True
                                break
                j += 1
            if t[min(j, N - 1)] - t[i] >= 100:
                end = t[min(j, N - 1)] + 2000
                xg = sum(s["xg"] for s in shots if s["team"] == team and t[i] <= t[s["f"]] <= end)
                o = out[sysn]["drew" if drew else "not"]
                o[0] += 1
                o[1] += xg
                dur = t[min(j, N - 1)] - t[i]
                b = 0 if dur < 1000 else 1 if dur < 2000 else 2 if dur < 4000 else 3
                lb = out[sysn].setdefault(("len", b, drew), [0, 0.0])
                lb[0] += 1
                lb[1] += xg
                per_team[team][0] += 1
                per_team[team][1] += drew
            i = max(j, i + 1)
        xd = sum(s["xg"] for s in shots if s["team"] == 0) - sum(s["xg"] for s in shots if s["team"] == 1)
        if min(per_team[0][0], per_team[1][0]) >= 10:
            games[sysn].append((per_team[0][1] / per_team[0][0] - per_team[1][1] / per_team[1][0], xd))
    for sysn in sorted(out):
        d, n = out[sysn]["drew"], out[sysn]["not"]
        print(f"{sysn.upper()}: {d[0] + n[0]} possessions by a person's carrier in the attacking zone")
        print(f"  drew two with a teammate open: {d[0]} ({d[0] / (d[0] + n[0]):.0%}), xG after {d[1] / max(1, d[0]):.3f} each; "
              f"the rest {n[1] / max(1, n[0]):.3f} each")
        for b, name in enumerate(("under 1 s", "1-2 s", "2-4 s", "4 s and more")):
            a, c = out[sysn].get(("len", b, True), [0, 0.0]), out[sysn].get(("len", b, False), [0, 0.0])
            if a[0] and c[0]:
                print(f"    possessions {name} (real): drew two {a[0]}, xG {a[1] / a[0]:.3f}; the rest {c[0]}, xG {c[1] / c[0]:.3f}")
        g = games[sysn]
        if len(g) > 3:
            print(f"  per game ({len(g)}): the difference in how often each person drew two, against the xG difference: "
                  f"correlation {st.correlation([a for a, _ in g], [b for _, b in g]):+.2f}")


if __name__ == "__main__":
    main()
