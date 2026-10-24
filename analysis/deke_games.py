"""Dekes and floaters in the recorded Genesis games (2026-10-24): how often a person's close-in wrist shot scores
when the puck was swung across in front of the shooter just before the release (the move scoring_map/deke_run.py
plays in the game: PROJECT_NOTES "Examples in the 2026-10-23 BOS-LA games"), against the same kind of shot without a
swing. A swing: the puck's place across the shooter's skating line (his right +) changed by SWING units or more, from
one side to the other, within SWING_FRAMES samples before the release. Shots: a person's wrist shots (`human`) at a
computer goalie (`gctl` cpu), the shooter within NEAR of the goalie at the release; sorted by how far out
(deke: within 45 of the goalie; floater range: 45-70), by the shooter's sideways speed (a floater crosses) and by
which side of him the puck was on at the release (his forehand side: a right-hander's right).
python analysis/deke_games.py [match ...]   (default: every Genesis match in the game folders)"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import play_by_play as P  # noqa: E402

SWING, SWING_FRAMES = 20, 40
NEAR = 70


def shots(name):
    g = P.Game(name)
    m = g.m
    if m.get("system", "genesis") != "genesis":
        return []
    out = []
    for s in m["shotList"]:
        if s.get("type") != "wrist shot" or not s.get("human") or s.get("gctl") != "cpu" or s.get("kind") != "shot":
            continue
        f, t = s["f"], s["team"]
        k = next((k for k in range(t * 6, t * 6 + 6) if g.roster(f, k) == s["idx"]), None)
        gk = g.goalie(f, 1 - t)
        if k is None or gk is None or f < SWING_FRAMES + 5:
            continue
        up = g.up(f, t)
        sx, sy = g.pos(f, k)
        gx, gy = g.pos(f, gk)
        dist = math.hypot(sx - gx, sy - gy)
        if dist > NEAR:
            continue
        ox, oy = g.pos(f - 10, k)
        vx, vy = (sx - ox) / 10, (sy - oy) / 10
        sp = math.hypot(vx, vy) or 1
        across = []                                   # the puck's place across his skating line (his right +)
        for ff in range(f - SWING_FRAMES, f + 1):
            ax, ay = g.pos(ff, k)
            px, py = m["puck"][ff * 3], m["puck"][ff * 3 + 1]
            if sp > 0.3:
                across.append(((px - ax) * vy - (py - ay) * vx) / sp)
            else:                                     # standing: across the ice, his right +
                across.append((px - ax) * up)
        rh = m["mirror"][f * P.K + k] == "1"          # right-handed (drawn mirrored): his forehand is his right
        last = across[-1]                             # released on one side, earlier at least 5 on the other
        swing = abs(last) > 3 and any(abs(v) >= 5 and (v < 0) != (last < 0) and abs(v - last) >= SWING
                                      for v in across)
        out.append(dict(match=name, clock=g.clock(f), shooter=g.full(t, s["idx"]), goal=s.get("result") == "goal",
                        xg=s.get("xg") or 0, dist=round(dist), swing=swing, side_speed=round(abs(vx * up), 2),
                        x=round(sx * up), y=round(sy * up), puck_across=round(across[-1], 1),
                        hand="R" if rh else "L", forehand=(last > 0) == rh))
    return out


def main(names):
    if not names:
        names = sorted({p.stem for d in P.DIRS for p in Path(d).glob("*.js") if p.stem != "season"})
    rows = []
    for n in names:
        try:
            rows += shots(n)
        except Exception as ex:  # a match without positions or of the other system
            print("skipped", n, ex, file=sys.stderr)
    groups = defaultdict(list)
    for r in rows:
        rng = "close (deke range, within 45)" if r["dist"] <= 45 else "45-70 (floater range)"
        mv = "crossing" if r["side_speed"] >= 1.0 else "straight in"
        side = "to forehand" if r["forehand"] else "to backhand"
        groups[(rng, mv, ("swing " if r["swing"] else "no swing, ") + side)].append(r)
    print(f"{len(rows)} wrist shots by a person at a computer goalie within {NEAR} of him, in {len(names)} games")
    print("| Range | Skating | Puck | Shots | Goals | Rate | xG rate |")
    print("|---|---|---|---|---|---|---|")
    for k in sorted(groups):
        v = groups[k]
        n, gl = len(v), sum(r["goal"] for r in v)
        print(f"| {k[0]} | {k[1]} | {k[2]} | {n} | {gl} | {gl / n:.0%} | {sum(r['xg'] for r in v) / n:.0%} |")
    return rows


if __name__ == "__main__":
    rows = main(sys.argv[1:])
    if "--list" in sys.argv:
        pass
    Path(__file__).resolve().parents[1].joinpath("reports").mkdir(exist_ok=True)
    json.dump(rows, open(Path(__file__).resolve().parents[1] / "reports" / "deke_games.json", "w"), indent=0)
