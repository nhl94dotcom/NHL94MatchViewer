"""NOSE4Web's recorded shot launches replayed at both nets (2026-11-18: the commissioner's database has a Down factor
of 1.031 in goals; doshot halves the depth scatter when the aim's dy < 0). LAUNCHES.json (NOSE4Web's, from our 38
Genesis captures: per doshot launch ix, iy, dir, P (passspeed), sha, top, the scatter drawn jx / jy / jz, its limits
adj / yadj, exact when the scatter solved uniquely) -> the scoring-map harness (paths.ROM, the test ROM with the doshot
hook; the top net from live.state, period 1; the bottom from live_p2.state, period 2: the same away goalie guards each).

Each exact launch, three replays: at its own net with its own scatter; mirrored (iy negated, the net flipped; ix, dir
kept: shotsets' x offsets don't depend on the end; jy mirrored and rescaled to the other net's range, jx, jz kept);
and, when the shot goes at the bottom net in either, that one again with the bottom net's depth range not halved (the
lsr after `tst.w 4(sp)` taken out). The scatter's depth draw as a share of its range: u = jy / range at the own net
(range = min(adj, 60), halved when dy = goal line - iy < 0); at another net or variant jy = u x that range.
The shooter (home record 2) is set at the puck spot and settles 60 frames with it; the wrist shot's doshot frame is
taken over (harness.fire: the velocity shotport.launch gives for these inputs; the puck put at ix, iy); the goalie
first set where a recorded computer goalie was at a release (GOALIES json "cpu", the same one for every replay of a
launch, mirrored at the bottom net), the random state after the release the same for each replay. Then 150 frames:
goal (either score), save (the goalie took it or it turned within 30 of him), out (beyond the boards), whistle (the
clock stopped), wide (across the goal line beyond 24 of the middle), other.

python updown_replay.py LAUNCHES.json GOALIES.json OUT.jsonl [MINUTES]   (resumable: done replays skipped)
python updown_replay.py report OUT.jsonl"""
import json
import math
import random
import sys
import time
from collections import Counter
from pathlib import Path

GL = 0x108


def ranges(L, top, halved=True):
    full = min(L["adj"], 60)
    dy = (GL if top else -GL) - L["iy_net"]
    return full // 2 if (halved and dy < 0) else full


def replay(h, L, top, jx, jy, jz, goalie, post_seed):
    from harness import fire, rec, SHOOTER, GOALIE, PUCK, PUCKC
    from shotport import launch
    e = h.e
    x, y = L["ix"], L["iy_net"]
    h.setup(x, y, settle=60)
    pre, f = h.shoot(8, 3)
    if pre is None:
        return None
    en = h.entry()
    e.unserialize(pre)
    e.setw(PUCK, x & 0xFFFF)
    e.setw(PUCK + 0x14, y & 0xFFFF)
    pre = e.serialize()
    inp = dict(px=x, py=y, top=top, dir=L["dir"], pout=L["P"], sha=L["sha"], vz0=0, gspa=en["gspa"])
    perfect = jx == 0 and jy == 0 and jz == 0
    v = launch(inp, perfect, jx, jy, jz)
    fire(h, pre, v, goalie=goalie, post_seed=post_seed)
    s0 = (e.w(0xC6DA), e.w(0xCA3E))
    gy = GL if top else -GL
    prev, touched, cross = None, False, None
    result = None
    for f in range(150):
        h.park(keep_shooter=False)
        e.run(1)
        if (e.w(0xC6DA), e.w(0xCA3E)) != s0:
            result = "goal"
            break
        px, py = e.sw(PUCK), e.sw(PUCK + 0x14)
        vx, vy = e.sw(PUCK + 0x28), e.sw(PUCK + 0x2A)
        if abs(py) > 300 or abs(px) > 140:
            result = "out"
            break
        if e.b(0xC2EA) & 1:
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


def run(launches, goalies, out, minutes):
    from harness import Harness
    from paths import STATE_TOP, STATE_BOTTOM
    import lowload
    lowload.gentle()
    L_all = [L for L in json.loads(Path(launches).read_text())
             if L.get("exact") and None not in (L["jx"], L["jy"], L["jz"])]   # 60 exact ones lack a jy or jz
    G = json.loads(Path(goalies).read_text())["cpu"]
    done = set()
    if Path(out).exists():
        for line in open(out):
            r = json.loads(line)
            done.add((r["n"], r["kind"]))
    top_h = Harness(state=STATE_TOP, top=True)
    hs = {True: top_h, False: Harness(state=STATE_BOTTOM, top=False, emu=top_h.e)}
    t0 = time.time()
    with open(out, "a") as fo:
        for n, L in enumerate(L_all):
            if time.time() - t0 > minutes * 60:
                print("time up", flush=True)
                break
            rng = random.Random(n)
            goalie = G[rng.randrange(len(G))]
            post = rng.getrandbits(32) or 1
            own_top = bool(L["top"])
            Lown = dict(L, iy_net=L["iy"])
            Lmir = dict(L, iy_net=-L["iy"])
            r_own = ranges(Lown, own_top)
            u = L["jy"] / r_own if r_own else 0.0
            jobs = [("own", own_top, Lown, L["jy"]),
                    ("mirror", not own_top, Lmir, -round(u * ranges(Lmir, not own_top)))]
            for kind, top, LL, jy in list(jobs):     # the bottom net with the depth range not halved
                if not top and ranges(LL, top, halved=False) != ranges(LL, top):
                    sign = 1 if kind == "own" else -1
                    jobs.append((kind + " no-lsr", top, LL, sign * round(u * ranges(LL, top, halved=False))))
            for kind, top, LL, jy in jobs:
                if (n, kind) in done:
                    continue
                r = replay(hs[top], LL, top, L["jx"], jy, L["jz"], goalie, post)
                if r is None:
                    continue
                row = dict(n=n, kind=kind, top=top, exact_v=None, perfect=L["jx"] == L["jy"] == L["jz"] == 0, human=L.get("human"), **r)
                if kind == "own":
                    row["exact_v"] = r["v"] == [L["vx"], L["vy"], L["vz"]]
                fo.write(json.dumps(row) + "\n")
                fo.flush()
            if n % 50 == 49:
                lowload.breathe()


def report(out):
    rows = [json.loads(line) for line in open(out)]
    by = {}
    for r in rows:
        by.setdefault((r["n"], r["kind"]), r)
    own = [r for r in rows if r["kind"] == "own"]
    print(f"launches replayed {len(own)}; own-net velocity rebuilt exactly {sum(bool(r['exact_v']) for r in own)}")

    def line(name, rs):
        c = Counter(r["result"] for r in rs)
        n = len(rs)
        print(f"  {name:44s} {n:5d}: goals {c['goal']:4d} ({c['goal'] / max(n, 1):5.1%}), saves {c['save']:4d}, wide {c['wide']:4d}, "
              f"out {c['out']:3d}, whistle {c['whistle']:3d}, other {c['other']:3d}")
    for lsr in (True, False):
        print("== with the bottom-net halving" if lsr else "== without it (the lsr taken out)")
        for net_top, name in ((True, "at the top net (Up)"), (False, "at the bottom net (Down)")):
            rs = []
            for r in rows:
                if r["top"] != net_top or r["kind"].endswith("no-lsr"):
                    continue
                if not lsr and not net_top:
                    alt = by.get((r["n"], r["kind"] + " no-lsr"))
                    r = alt or r
                rs.append(r)
            line(name + ", every launch", rs)
            line(name + ", not perfect", [r for r in rs if not r["perfect"]])
    for kind, net_top in (("own", True), ("own", False)):
        pairs = [(r, by.get((r["n"], "mirror"))) for r in own if r["top"] == net_top]
        pairs = [(a, b) for a, b in pairs if b]
        ga = sum(a["result"] == "goal" for a, b in pairs)
        gb = sum(b["result"] == "goal" for a, b in pairs)
        print(f"paired: launches taken at the {'top' if net_top else 'bottom'} net ({len(pairs)}): goals there {ga}, mirrored {gb}")


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2])
    else:
        run(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 1e9)
