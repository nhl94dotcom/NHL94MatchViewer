"""SNES: what a speed burst does when it reaches an opponent, by whether the burster is still in the burst animation
(2026-10-21; SNES_MECHANICS 7.1). Code: checkcheck only considers a check while the hitter's animation is SPAburst
($F342, 24 frames = 0.4 s, drawn as an ordinary skating frame); after that a contact is only checkplcoll's bounce
(speeds shared by weight along the line between them), so a burster still moving fast shoves the other player along
with no check, no fall and no animation, and a carrier keeps the puck. Each burst's first contact with an opponent
skater (under 16 apart) within 1.5 s, classified by the burster's animation then and the outcome.
python analysis/snes_burst_contact_study.py"""
import json
import math
import sys
from collections import Counter

sys.path.insert(0, "tools")
sys.path.insert(0, "analysis")
from share_game import load_js_object  # noqa: E402
from tangle_study import games  # noqa: E402

K = 12
BURST = "f342"
CHECKS = {"f27a", "f2ac", "f2de", "f310"}
DOWN = {"f49c", "f54e", "f6c0", "f7b2"}


def main():
    c = Counter()
    for name, path in games():
        m = json.loads(load_js_object(path))
        if m.get("system") != "snes":
            continue
        t, N = m["t"], len(m["t"])
        an = lambda i, k: m["anim"][(i * K + k) * 4:(i * K + k) * 4 + 4]
        pos = lambda i, k: (m["pos"][(i * K + k) * 2], m["pos"][(i * K + k) * 2 + 1])
        for k in range(K):
            for i in range(1, N):
                if not (an(i, k) == BURST and an(i - 1, k) != BURST and m["role"][i * K + k] in "12345"):
                    continue
                opp = range(6, 12) if k < 6 else range(6)
                hit = None
                for q in range(i, min(N, i + 120)):
                    if t[q] - t[i] > 1500 or m["puck"][3 * q + 2] < -100 or an(q, k) in DOWN:
                        break
                    if q > i and an(q, k) == BURST and an(q - 1, k) != BURST:
                        break
                    j = next((j for j in opp if m["role"][q * K + j] in "12345" and math.dist(pos(q, k), pos(q, j)) < 16), None)
                    if j is not None:
                        hit = (q, j)
                        break
                if not hit:
                    continue
                q, j = hit
                state = ("in the burst animation" if BURST in (an(q, k), an(q - 1, k))
                         else "in a check animation" if an(q, k) in CHECKS else "burst animation over")
                fell = any(an(z, j) in DOWN for z in range(q, min(N, q + 20)))
                chk = any(an(z, k) in CHECKS and an(z - 1, k) not in CHECKS for z in range(q, min(N, q + 4)))
                c[(state, "knocked down" if fell else "check thrown, stays up" if chk else "no check, no fall")] += 1
    for key, v in sorted(c.items()):
        print(f"{key[0]:24} {key[1]:24} {v}")


if __name__ == "__main__":
    main()
