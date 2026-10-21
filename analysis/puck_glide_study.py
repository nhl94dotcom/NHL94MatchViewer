"""How fast a loose puck slows, both systems (2026-10-21). Genesis (updateplayers): on the ice the puck loses 1/512 of
its speed a frame (keeps 0.889 a second), in the air nothing. SNES (updateplayers): the puck goes through the skaters'
friction step, table .21 ($FD/256 a frame: keeps about 0.49 a second) or, with pflags bit 0 (gliding), .22 ($FF/$FE:
about 0.79); in the air nothing. Measured on clean stretches: loose (no owner), not touched (the speed falls smoothly),
on the ice or in the air the whole time, away from the boards, at least 0.4 s; the fraction of speed kept per second.
Both systems' boards (wallcoll) are the same code: the speed into the boards quartered and reversed, along them less
1/64 + 1/128; also measured here (the speed along the boards kept, and off them, at each bounce).
python analysis/puck_glide_study.py"""
import json
import math
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, "tools")
sys.path.insert(0, "analysis")
from share_game import load_js_object  # noqa: E402
from tangle_study import games  # noqa: E402

MIN_MS = 400
SIDE = {"genesis": 112, "snes": 112}  # stay this far inside the side boards (the side boards near x +/-120 to 130)
END = 250                              # and inside the end boards (about +/-290)


def stretches(m):
    """Yield (kind, kept per second) for clean stretches."""
    t, P, V, own = m["t"], m["puck"], m["puckV"], m["owner"]
    N = len(t)
    speed = lambda i: math.hypot(V[2 * i], V[2 * i + 1])
    ok = lambda i: own[i] < 0 and abs(P[3 * i]) < SIDE[m.get("system", "genesis")] and abs(P[3 * i + 1]) < END
    i = 0
    while i < N - 1:
        if not ok(i) or speed(i) < 40:
            i += 1
            continue
        air = P[3 * i + 2] > 0.5
        s = i
        while i + 1 < N and ok(i + 1) and (P[3 * (i + 1) + 2] > 0.5) == air and speed(i + 1) <= speed(i) * 1.001 + 1 \
                and speed(i + 1) > 0.9 * speed(i) and t[i + 1] - t[i] < 60:
            i += 1
        if t[i] - t[s] >= MIN_MS and speed(i) > 12:
            kept = (speed(i) / speed(s)) ** (1000 / (t[i] - t[s]))
            yield ("air" if air else "ice"), kept
        i += 1


def main():
    res = defaultdict(list)
    for name, path in games():
        m = json.loads(load_js_object(path))
        for kind, kept in stretches(m):
            res[(m.get("system", "genesis"), kind)].append(kept)
    for (system, kind), v in sorted(res.items()):
        q = statistics.quantiles(v, n=4) if len(v) > 3 else [0, 0, 0]
        print(f"{system:8} {kind:4} {len(v):4} stretches: keeps a median {statistics.median(v):.3f} a second "
              f"(quartiles {q[0]:.3f} - {q[2]:.3f})")


if __name__ == "__main__":
    main()
