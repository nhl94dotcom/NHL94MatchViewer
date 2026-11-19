"""NHL '95: NOSE4Web's recorded shot launches replayed at both nets against the computer goalie, any NHL '95 ROM
(2026-11-19; the stick-mirror variants C and B; NHL '94's version is updown_replay.py).

NHL '95 has no test ROM with a doshot hook, so the launch is put in after the game's own: from live states of the
retail game (runs/nhl95/updown/live_p1.state, period 1, home shooting at the top net, pad 1 on home record 1;
live_p2.state, period 2, the bottom net, pad 1 on record 2; the away goalie, record 11, guards both), the pad's
skater stands at the launch spot with the puck for 60 frames (everyone else parked at the far end, the period clock
the launch's random value at both nets), presses C with no aim and is played to the frame the puck comes loose
(puckc $B3C2 $FFxx); on that frame's end the puck is put at the launch spot with the launch's velocity (shotport.launch,
NHL '94's doshot ported: the same launches as the NHL '94 replays, own net and mirrored, the scatter's depth draw
rescaled as there; the halving kept), the random state set to the launch's post seed, the goalie first moved as a
recorded computer goalie was at a release (goalies_genesis.json "cpu", mirrored at the bottom net). Then 150 frames:
goal (either score), save (the goalie has it, or the puck's speed changes by over 3,000 within 30 of him), out,
whistle (the clock stopped 48 frames), wide (across the goal line beyond 24), other.

python gen95_updown.py ROM LAUNCHES.json GOALIES.json OUT.jsonl [MINUTES]   |   report OUT.jsonl [OUT2 ...]"""
import json
import math
import random
import sys
import time
from collections import Counter
from pathlib import Path

from emu import Emu

BASE, SZ, PUCK, GOALIE = 0xAC62, 0x80, 14, 11
PUCKC, CLOCK, GMODE, SEED, SCORES = 0xB3C2, 0xC022, 0xBEF0, 0xCC6A, (0xC294, 0xC5FA)
GL = 0x108
STATES = Path.home() / "NHL94_scoring_map" / "runs" / "nhl95" / "updown"


def rec(k):
    return BASE + SZ * k


class H95:
    def __init__(self, e, state, top):
        self.e, self.top = e, top
        self.base = Path(state).read_bytes()
        e.unserialize(self.base)
        self.shooter = next(k for k in range(6) if e.b(rec(k) + 0x62) & 8)
        self.park_y = -230 if top else 230

    def put(self, k, x, y):
        e, r = self.e, rec(k)
        for off, v in ((0, x), (2, 0), (0x14, y), (0x16, 0), (0x28, 0), (0x2A, 0), (0x2C, 0)):
            e.setw(r + off, v & 0xFFFF)

    def park(self, keep=True):
        for k in range(12):
            if k == GOALIE or (keep and k == self.shooter):
                continue
            self.put(k, -100 + 18 * k, self.park_y)

    def setup(self, x, y, clock, settle=60):
        e = self.e
        e.unserialize(self.base)
        e.setw(CLOCK, clock)
        for _ in range(settle):
            self.put(self.shooter, x, y)
            self.park()
            e.setw(PUCKC, self.shooter)
            e.run(1)

    def shoot(self, hold=3, maxf=90):
        e = self.e
        for f in range(maxf):
            pre = e.serialize()
            self.park()
            e.run(1, hold=["C"] if f < hold else [])
            if e.w(PUCKC) & 0xFF00:
                return pre
        return None


def replay(h, L, top, jx, jy, jz, goalie, post, clock):
    from shotport import launch
    e = h.e
    x, y = L["ix"], L["iy_net"]
    h.setup(x, y, clock)
    pre = h.shoot()
    if pre is None:
        return None
    inp = dict(px=x, py=y, top=top, dir=L["dir"], pout=L["P"], sha=L["sha"], vz0=0, gspa=None)
    v = launch(inp, jx == 0 and jy == 0 and jz == 0, jx, jy, jz)
    e.unserialize(pre)
    if goalie is not None:
        sg = 1 if top else -1
        g = rec(GOALIE)
        dx, dy, gvx, gvy = (sg * q for q in goalie)
        e.setw(g, (e.sw(g) + round(dx)) & 0xFFFF)
        e.setw(g + 0x14, (e.sw(g + 0x14) + round(dy)) & 0xFFFF)
        e.setw(g + 0x28, max(-32768, min(32767, round(gvx * 4096))) & 0xFFFF)
        e.setw(g + 0x2A, max(-32768, min(32767, round(gvy * 4096))) & 0xFFFF)
    h.park()
    e.run(1)                                       # the release frame: the game's own shot
    p = rec(PUCK)
    e.setw(p, x & 0xFFFF)
    e.setw(p + 2, 0)
    e.setw(p + 0x14, y & 0xFFFF)
    e.setw(p + 0x16, 0)
    e.setw(p + 0x28, v[0] & 0xFFFF)
    e.setw(p + 0x2A, v[1] & 0xFFFF)
    e.setw(p + 0x2C, v[2] & 0xFFFF)
    e.setl(SEED, post)
    s0 = tuple(e.w(a) for a in SCORES)
    gy = GL if top else -GL
    prev, cross, touched, result = None, None, False, None
    still, last_clock = 0, e.w(CLOCK)
    for f in range(150):
        h.park(keep=False)
        e.run(1)
        if tuple(e.w(a) for a in SCORES) != s0:
            result = "goal"
            break
        px, py = e.sw(p), e.sw(p + 0x14)
        vx, vy = e.sw(p + 0x28), e.sw(p + 0x2A)
        if abs(py) > 300 or abs(px) > 140:
            result = "out"
            break
        c = e.w(CLOCK)
        still = still + 1 if c == last_clock else 0
        last_clock = c
        if still >= 48:                           # the clock stopped (a game second is about 24 frames)
            result = "whistle"
            break
        gx, gyy = e.sw(rec(GOALIE)), e.sw(rec(GOALIE) + 0x14)
        if e.w(PUCKC) == GOALIE or (prev and math.hypot(vx - prev[2], vy - prev[3]) > 3000 and math.hypot(px - gx, py - gyy) < 30):
            touched = True
        if prev and cross is None and not touched and (prev[1] - gy) * (py - gy) <= 0 and py != prev[1]:
            cross = prev[0] + (px - prev[0]) * (gy - prev[1]) / (py - prev[1])
        prev = (px, py, vx, vy)
    if result is None:
        result = "save" if touched else ("wide" if cross is not None and abs(cross) > 24 else "other")
    return dict(result=result, v=list(v))


def run(rom, launches, goalies, out, minutes):
    import lowload
    from updown_replay import ranges
    lowload.gentle()
    e = Emu(rom)
    hs = {True: H95(e, STATES / "live_p1.state", True), False: H95(e, STATES / "live_p2.state", False)}
    L_all = [L for L in json.loads(Path(launches).read_text()) if L.get("exact") and None not in (L["jx"], L["jy"], L["jz"])]
    G = json.loads(Path(goalies).read_text())["cpu"]
    done = set()
    if Path(out).exists():
        done = {(r["n"], r["kind"]) for r in map(json.loads, open(out))}
    t0 = time.time()
    with open(out, "a") as fo:
        for n, L in enumerate(L_all):
            if time.time() - t0 > minutes * 60:
                print("time up", flush=True)
                break
            rng = random.Random(n)
            goalie = G[rng.randrange(len(G))]
            post = rng.getrandbits(32) or 1
            clock = rng.randrange(240, 580)
            own_top = bool(L["top"])
            Lown, Lmir = dict(L, iy_net=L["iy"]), dict(L, iy_net=-L["iy"])
            r_own = ranges(Lown, own_top)
            u = L["jy"] / r_own if r_own else 0.0
            for kind, top, LL, jy in (("own", own_top, Lown, L["jy"]),
                                      ("mirror", not own_top, Lmir, -round(u * ranges(Lmir, not own_top)))):
                if (n, kind) in done:
                    continue
                r = replay(hs[top], LL, top, L["jx"], jy, L["jz"], goalie, post, clock)
                if r is None:
                    continue
                fo.write(json.dumps(dict(n=n, kind=kind, top=top, perfect=L["jx"] == L["jy"] == L["jz"] == 0, **r)) + "\n")
                fo.flush()
            if n % 50 == 49:
                lowload.breathe()


def paired(path):
    by = {}
    for r in map(json.loads, open(path)):
        by[(r["n"], r["kind"])] = r
    both = a = b = 0
    for (n, k), r in by.items():
        if k != "own" or (n, "mirror") not in by:
            continue
        m = by[(n, "mirror")]
        t, bo = (r, m) if r["top"] else (m, r)
        gt, gb = t["result"] == "goal", bo["result"] == "goal"
        both += gt and gb
        a += gt and not gb
        b += gb and not gt
    return both, a, b


def report(paths):
    for p in paths:
        rows = [json.loads(line) for line in open(p)]
        both, a, b = paired(p)
        print(f"== {p}")
        for top in (True, False):
            c = Counter(r["result"] for r in rows if r["top"] == top)
            n = sum(c.values())
            print(f"  {'top   ' if top else 'bottom'} {n} replays: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
        if a + b:
            z = (b - a) / math.sqrt(a + b)
            print(f"  paired goals top {both + a}, bottom {both + b}: Down/Up {(both + b) / max(both + a, 1):.3f} "
                  f"(one net only: top {a}, bottom {b}, z {z:+.1f})")


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2:])
    else:
        run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]) if len(sys.argv) > 5 else 1e9)
