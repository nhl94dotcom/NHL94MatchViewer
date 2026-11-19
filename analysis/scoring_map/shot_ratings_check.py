"""Shot Power and Shot Accuracy in play (Genesis NHL '94, 2026-11-18, for NOSE4Web's roster-page rewrite):
sniping_test's set-up (live state, the home centre at a spot with the puck, everyone else parked), the shooter's
working rating set every frame.

  acc ROM [SEEDS]   working Shot Accuracy ($6D) 0-30 in steps: C tapped from SPOTS (94-174 from the top net's aim
                    point, within doshot's 200), SEEDS seeds each; the share exact (sniping_test's measure: an exact
                    shot leaves a spot the same way every time, so the share of a spot's shots on its most common
                    velocity) against the code's (ShA + 1) / (ShA + 16)
  power ROM [SEEDS] working Shot Power ($6C): C held through the whole wind-up (WIND frames) and let go, from the slot;
                    the highest passspeed ($BEDE: doshot's speed before x 68) and the puck's speed the frame after
                    the release (sqrt of the three speed words; a puck at 23,000 is about 78 mph)

  ends ROM [SEEDS]  NOSE4Web's Down-goal question (doshot halves the scatter along the ice when the aim's dy < 0): the
                    same shot at both ends: spots 219-271 from the aim point (never perfect) and 114-150 (the slot: a
                    perfect roll told by the spot's most common release velocity, kept apart), the same shooter (home
                    record 2, working ShA 15, ShP 20) and the same goalie (the away goalie, record 11): at the top net
                    in the live state (period 1), at the bottom in that game run on into period 2 (the same goalie
                    defends it; the spots mirrored; a period flipped by hand left the goalie not defending); C tapped with nothing, Left or
                    Right held (the same aim point at either end); NHL94_SHOT_HOLD frames of C (3 a wrist shot,
                    20 a slapshot). Each shot to 210 frames:
                    goal (the score, rebounds too), save (the goalie took it or the puck turned within 30 of him),
                    else where it crossed the goal line (wide past 24) or other; how fast it left

python shot_ratings_check.py acc|power|ends ROM [SEEDS]"""
import math
import random
import sys
from collections import Counter

from blind_ring_test import park, SHOOTER
from bot import rec, PUCKC
from bot_scenario import live_state
from emu import Emu
from sniping_test import SPOTS

SHP, SHA, PASSSPEED, WIND = 0x6C, 0x6D, 0xBEDE, 90


def shoot(e, base, x, y, seed, rating, value, hold):
    e.unserialize(base)
    e.setw(0xC468, 250)
    e.setl(0xD066, seed)
    for k in range(6):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setb(rec(SHOOTER) + 0x62, e.b(rec(SHOOTER) + 0x62) | 8)
    e.setw(0xC320, SHOOTER)
    for _ in range(60):
        e.setw(rec(SHOOTER), x & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x14, y & 0xFFFF)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(SHOOTER) + off, 0)
        e.setb(rec(SHOOTER) + rating, value)
        park(e)
        e.setw(PUCKC, SHOOTER)
        e.run(1)
    e.setl(0xD066, seed)
    for f in range(hold + 60):
        park(e)
        e.setb(rec(SHOOTER) + rating, value)
        e.run(1, hold=["C"] if f < hold else [])
        if e.w(PUCKC) >= 0x8000:
            return e.w(PASSSPEED), (e.sw(rec(14) + 0x28), e.sw(rec(14) + 0x2A), e.sw(rec(14) + 0x2C))
    return None


GOALIE_AWAY, GSP, HOME_SCORE = 11, 0xC466, 0xC6DA
import os
HOLD = int(os.environ.get("NHL94_SHOT_HOLD", "3"))   # frames C is held: 3 a wrist shot, 20 a slapshot
END_SPOTS = [(x, y) for x in (-60, -30, 0, 30, 60) for y in (0, 45, 120, 150)]


def period2_state(e, base):
    """bot_scenario's live state (period 1) run on into period 2: its clock set to 2 s, START tapped through the
    intermission (once the clock has stood 8 s, as cvc_record), until the clock runs in period 2 (cached beside the live state)."""
    from bot_scenario import WORK
    p = WORK / "bot_live_p2.state"
    if p.exists():
        return p.read_bytes()
    e.unserialize(base)
    e.setw(0xC468, 2)
    clocks, still, last = [], 0, None
    for f in range(40000):
        if f % 60 == 0:                              # START only once the clock has stood 8 s (cvc_record's way)
            c = e.w(0xC468)
            still = still + 1 if c == last else 0
            last = c
        e.run(1, hold=["START"] if still >= 8 and f % 60 < 4 else [])
        if e.w(GSP) == 1 and e.b(0xFFF7) == 0:
            clocks = (clocks + [e.w(0xC468)])[-150:]
            if len(clocks) == 150 and clocks[-1] < clocks[0] and e.w(PUCKC) < 12:
                p.write_bytes(e.serialize())
                return p.read_bytes()
    raise SystemExit("period 2 not reached")


def end_shot(e, base, x, y, seed, bottom, aim=()):
    """One shot at the top net (bottom False: period 1's state) or its mirror at the bottom net (period 2's state, where
    the same away goalie defends the bottom net and the same home shooter attacks it)."""
    e.unserialize(base)
    e.setw(0xC468, 250)
    e.setl(0xD066, seed)
    sy = -y if bottom else y
    for k in range(6):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setb(rec(SHOOTER) + 0x62, e.b(rec(SHOOTER) + 0x62) | 8)
    e.setw(0xC320, SHOOTER)
    for f in range(60):
        e.setw(rec(SHOOTER), x & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x14, sy & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x54, 4 if bottom else 0)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(SHOOTER) + off, 0)
        e.setb(rec(SHOOTER) + SHA, 15)
        e.setb(rec(SHOOTER) + SHP, 20)
        for k in range(12):                              # the rest well away, at the far blue line
            if k in (SHOOTER, GOALIE_AWAY) or e.b(rec(k) + 0x35) == 0:
                continue
            e.setw(rec(k), (-110 + 20 * k) & 0xFFFF)
            e.setw(rec(k) + 0x14, (100 if bottom else -100) & 0xFFFF)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(rec(k) + off, 0)
        if f < 30:
            e.setw(rec(GOALIE_AWAY), 0)
            e.setw(rec(GOALIE_AWAY) + 0x14, (-250 if bottom else 250) & 0xFFFF)
            home_g = next(k for k in range(6) if e.b(rec(k) + 0x35) == 0)
            e.setw(rec(home_g), 0)                       # the other goalie in the other crease
            e.setw(rec(home_g) + 0x14, (250 if bottom else -250) & 0xFFFF)
        e.setw(PUCKC, SHOOTER)
        e.run(1)
    e.setl(0xD066, seed)
    score0 = (e.w(HOME_SCORE), e.w(0xCA3E))
    gy = -264 if bottom else 264
    rel, vel, cross, goal, touched, out = None, None, None, False, False, False
    prev = None
    for f in range(210):
        e.setb(rec(SHOOTER) + SHA, 15)
        e.setb(rec(SHOOTER) + SHP, 20)
        e.run(1, hold=["C", *aim] if f < HOLD else [])
        pc = e.w(PUCKC)
        px, py = e.sw(rec(14)), e.sw(rec(14) + 0x14)
        vx, vy = e.sw(rec(14) + 0x28), e.sw(rec(14) + 0x2A)
        if rel is None:
            if pc >= 0x8000:
                rel, vel = f, (vx, vy, e.sw(rec(14) + 0x2C))
                prev = (px, py, vx, vy)
            continue
        if (e.w(HOME_SCORE), e.w(0xCA3E)) != score0:       # either score: the game may credit the net's usual team
            goal = True
            break
        if abs(py) > 300 or abs(px) > 140:             # out of the rink (over the glass)
            out = "out of the rink"
            break
        if e.b(0xC2EA) & 1:                            # the clock stopped: a whistle (a freeze, the puck out of play)
            out = "whistle"
            break
        gx, gyy = e.sw(rec(GOALIE_AWAY)), e.sw(rec(GOALIE_AWAY) + 0x14)
        if pc == GOALIE_AWAY or (math.hypot(vx - prev[2], vy - prev[3]) > 3000 and math.hypot(px - gx, py - gyy) < 30):
            touched = True
        if cross is None and not touched and (prev[1] - gy) * (py - gy) <= 0 and py != prev[1]:
            cross = prev[0] + (px - prev[0]) * (gy - prev[1]) / (py - prev[1])
        prev = (px, py, vx, vy)
    result = ("goal" if goal else "save" if touched else out if out
              else ("wide" if cross is not None and abs(cross) > 24 else "other"))
    return rel, vel, cross, result


def main():
    mode, rom = sys.argv[1], sys.argv[2]
    seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    e = Emu(rom)
    base = live_state(e, 0)
    if mode == "ends":
        for bottom in (False, True):
            by_band = {}
            b = period2_state(e, base) if bottom else base
            for x, y in END_SPOTS:
              for aim in ((), ("LEFT",), ("RIGHT",)):
                shots = [end_shot(e, b, x, y, random.Random(f"{x},{y},{aim},{sd}").getrandbits(32), bottom, aim)
                         for sd in range(seeds)]
                shots = [r for r in shots if r[0] is not None]
                if not shots:
                    continue
                modal = Counter(r[1] for r in shots).most_common(1)[0]
                for r in shots:
                    perfect = y >= 100 and r[1] == modal[0] and modal[1] > 1
                    by_band.setdefault(("slot, not perfect" if y >= 100 else "219-271 out") if not perfect else "slot, perfect",
                                       []).append(r)
            for band, rows in sorted(by_band.items()):
                res = Counter(r[3] for r in rows)
                xs = [r[2] for r in rows if r[2] is not None]
                sp = [math.hypot(*r[1][:2]) for r in rows]
                n = len(rows)
                mx = sum(xs) / len(xs) if xs else 0
                sdx = (sum((v - mx) ** 2 for v in xs) / len(xs)) ** 0.5 if xs else 0
                print(f"{'bottom (Down)' if bottom else 'top (Up)'} {band:18s}: {n:4d} shots; goals {res['goal']:3d} ({res['goal'] / n:5.1%}), "
                      f"saves {res['save']:3d} ({res['save'] / n:5.1%}), wide {res['wide']:3d}, out of the rink {res['out of the rink']:3d}, whistle {res['whistle']:3d}, "
                      f"other {res['other']:3d}; untouched across the line "
                      f"{len(xs)}: |x| <= 20 {sum(abs(v) <= 20 for v in xs)}, x sd {sdx:.1f}; speed {sum(sp) / max(1, n):,.0f} "
                      f"(sd {(sum((v - sum(sp) / n) ** 2 for v in sp) / n) ** 0.5:,.0f})", flush=True)
        return
    if mode == "acc":
        for sha in (0, 5, 10, 15, 20, 25, 30):
            exact = total = 0
            for x, y in SPOTS:
                vs = [shoot(e, base, x, y, random.Random(f"{x},{y},{s}").getrandbits(32), SHA, sha, 3) for s in range(seeds)]
                vs = [v[1] for v in vs if v]
                if vs:
                    exact += Counter(vs).most_common(1)[0][1]
                    total += len(vs)
            print(f"ShA {sha:2d}: exact {exact} of {total} ({exact / max(1, total):.1%}); the code's (ShA + 1) / (ShA + 16) "
                  f"{(sha + 1) / (sha + 16):.1%}", flush=True)
    else:
        for shp in (10, 15, 16, 17, 19, 20, 21, 25, 30):
            best = None
            for s in range(seeds):
                r = shoot(e, base, 0, 120, random.Random(f"p{s}").getrandbits(32), SHP, shp, WIND)
                if r and (best is None or r[0] > best[0] or (r[0] == best[0] and math.hypot(*r[1]) > math.hypot(*best[1]))):
                    best = r
            if best:
                sp = math.hypot(*best[1])
                print(f"ShP {shp:2d}: highest passspeed {best[0]}, puck speed {sp:,.0f} (about {sp * 78 / 23000:.0f} mph)", flush=True)


if __name__ == "__main__":
    main()
