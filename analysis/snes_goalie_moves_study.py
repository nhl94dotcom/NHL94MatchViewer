"""SNES goalies' attacking moves (2026-10-21; SNES_SHOOTING 5.3). Code (assgoalie): a computer goalie pokes
(SPAgpoke $E528) at an opponent carrier within 35 in front of the goal line on a 1-in-25.6 roll, then waits 4 s; he
dives (SPAgdive $E4B6) at a loose puck within 45 with an attacker within 60 of it on a 1-in-32 roll, but only when the
counter puckgoalie sets to 4 on a touch has counted down to exactly 0: one chance per save. Counts each goalie
animation start by person / computer, and the computer's saves that left a rebound a dive could have been tried at.
python analysis/snes_goalie_moves_study.py"""
import json
import math
import sys
from collections import Counter

sys.path.insert(0, "tools")
sys.path.insert(0, "analysis")
from share_game import load_js_object  # noqa: E402
from tangle_study import games  # noqa: E402

K = 12
POKE, DIVE = "e528", "e4b6"


def main():
    starts, minutes, saves, chances = Counter(), 0, 0, 0
    for name, path in games():
        m = json.loads(load_js_object(path))
        if m.get("system") != "snes":
            continue
        t, P, own = m["t"], m["puck"], m["owner"]
        minutes += (t[-1] - t[0]) / 60000
        for k in range(K):
            prev = None
            for i in range(len(t)):
                if m["role"][i * K + k] != "0":
                    prev = None
                    continue
                a = m["anim"][(i * K + k) * 4:(i * K + k) * 4 + 4]
                if a != prev and a in (POKE, DIVE):
                    starts[("poke" if a == POKE else "dive", "person" if m["ctrl"][i] >> k & 1 else "computer")] += 1
                prev = a
        pos = lambda q, k: (m["pos"][(q * K + k) * 2], m["pos"][(q * K + k) * 2 + 1])
        for s in m["shotList"]:
            if s["result"] != "save" or s.get("gctl") != "cpu":
                continue
            saves += 1
            f = s.get("resolved", s["f"])
            q = next((i for i in range(f, min(len(t), f + 60)) if t[i] - t[f] >= 70), None)  # about 4 frames on
            if q is None or own[q] >= 0:
                continue
            g = [k for k in range(K) if m["role"][q * K + k] == "0" and k // 6 != s["team"]]
            if not g:
                continue
            px, py = P[3 * q], P[3 * q + 1]
            if math.dist(pos(q, g[0]), (px, py)) < 45 and any(
                    math.dist(pos(q, k), (px, py)) < 60 for k in range(K) if k // 6 == s["team"] and m["role"][q * K + k] in "12345"):
                chances += 1
    print(f"{minutes:.0f} minutes of SNES play: {dict(starts)}")
    print(f"computer goalies' saves {saves}; a loose rebound within 45 with an attacker within 60 just after: {chances} "
          f"(about {chances / 32:.1f} dives expected at 1 in 32)")


if __name__ == "__main__":
    main()
