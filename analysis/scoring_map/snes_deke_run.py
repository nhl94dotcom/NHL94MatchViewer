"""SNES dekes in the real game (retail ROM, snes_harness), 2026-10-25: the two moves of the user's 2v2 game
(`2026-10-25_1951_MTL-LA`, SNES_MECHANICS 4.10), played by d-pad inputs from a standing start, as a person skates them.
- "cut" (the near-post cut): in down one side, wide (x0 across); from CUT_OUT out cut toward the middle holding
  up-and-in; at TURN out hold up-and-out (he turns to face up the ice: the recording turned at about 90-100 out, 0.7 s
  before the shot); tap A once he is OA out, with the aim held: "high" (Up on the d-pad, always high, and the near side) or "mid" (the near side only). Going down the
  screen, high is the d-pad *away* from the net.
- "deke" (from his own side): in on one side, wide, skating up the ice, then up and in toward the middle for the last
  40 out before SW; at SW out hold sideways back toward his own side (the swing) for LAG frames, then tap A with the aim held (high or mid at the near post).
Attacker's view: across + is his right, out from the goal line (264); side +1 = in from his right. Both hands
(attribute bit $0800: set, right-handed), both nets. Each job: MOMENTS moments (the goalie's random seed, the clock,
the settle frames), each shot fired with SEEDS release seeds. Outcomes per moment: a shot (then goals of SEEDS),
no shot (the puck still his at the end), lost (the puck gone before the shot), carried (into the net himself).
The recorded reference: top net, in from the right, left-handers: 6 goals in 11.
"replay": the user's own tries from the recording, frame by frame: the skater put where he was 1.5 s before the shot
(position, speed, facing; the goalie where he was), then the recorded d-pad and A. Each try at its own net and
turned round at the other (the same move, mirrored on the screen), by a left- and a right-hander, with the aim as
played or, from the A press, "high" / "mid" at the near post. The match: NHL94_SDEKE_MATCH (a match file's name in
Documents/NHL94 Viewer/matches), default the 2v2 game.
Checked 2026-10-25: replayed with the recorded skater's and goalie's working ratings, the skater follows the recorded
path to within about 5 units, and the 11 top-net cuts score 37% (the user: 6 of 11); tries released 26-35 out mostly
score, from 40+ out mostly not. "test" and "near" (inputs built from scratch, the harness's own skater) are not yet
tuned: their cut bends far less than the recorded one.
Plans: "test" (the cut only: top net, from the right, left-handed, high), "near" (both moves, the grid), "replay".
python snes_deke_run.py PLAN RUN [minutes]   -> paths.RUNS / RUN / snes_deke_<PLAN>.jsonl   (gentle mode, chunked)"""
import itertools
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool

from pathlib import Path

import snes_harness as H
from lowload import WORKERS, breathe, gentle
from paths import RUNS, SNES_STATE_TOP, SNES_STATE_BOTTOM

MOMENTS = int(os.environ.get("NHL94_SDEKE_MOMENTS") or 24)
SEEDS = 4
GOAL_Y = 264
ATTR, FACING = 0x0E03, 0x1163
WORK = (0x12C3, 0x12E3, 0x1303, 0x1343, 0x1363, 0x1383)   # working ratings (the match file's "work", same order)
START_OUT, CUT_OUT = 230, 175          # standing start; the cut begins once he is CUT_OUT out
KEYS = ("move", "net", "side", "hand", "x0", "a", "b", "aim")
MATCH = os.environ.get("NHL94_SDEKE_MATCH") or "2026-10-25_1951_MTL-LA"
LEAD = 90                              # replay: frames before the shot
# the user's tries in the 2v2 game (SNES_MECHANICS 4.10): (period-clock, move, side); team 0 (MTL, pad 1)
TRIES = [(k, "cut", 1) for k in ("P1-2:31", "P1-1:53", "P1-1:26", "P3-4:02", "P3-3:51", "P3-3:07", "P3-2:59",
                                 "P3-2:18", "P3-1:42", "P3-0:57", "P3-0:11", "P2-2:25", "P2-1:54", "P2-0:57",
                                 "P2-0:13")]
TRIES += [(k, "deke", -1) for k in ("P1-1:43", "P1-1:00", "P1-0:07", "P3-4:51", "P3-4:11", "P2-4:47", "P2-4:08",
                                    "P2-3:40", "P2-3:20", "P2-2:44", "P2-1:13")]
_h, _rec = {}, {}


def plan_jobs(plan):
    if plan == "test":
        return [("cut", "top", 1, "L", x0, turn, oa, "high") for x0 in (60, 80) for turn in (85, 100, 115)
                for oa in (45, 55, 65)]
    if plan == "replay":
        return [("replay", net, side, hand, k, move, 0, aim) for k, move, side in TRIES for net in ("top", "bottom")
                for hand in ("L", "R") for aim in ("played", "high", "mid")]
    if plan == "near":
        cut = itertools.product(("cut",), ("top", "bottom"), (1, -1), ("L", "R"), (60, 80), (85, 100, 115),
                                (45, 55, 65), ("high", "mid"))
        deke = itertools.product(("deke",), ("top", "bottom"), (1, -1), ("L", "R"), (60, 80), (80, 100, 120),
                                 (8, 16, 24), ("high", "mid"))
        return list(cut) + list(deke)
    raise SystemExit(f"unknown plan {plan}")


def _init():
    gentle()
    top = H.Harness(state=SNES_STATE_TOP, top=True)
    _h["top"], _h["bottom"] = top, H.Harness(state=SNES_STATE_BOTTOM, top=False, emu=top.e)


def recorded(key):
    """A try from the match file: its net, the skater's and goalie's start (screen: x, y, vx, vy; facing) LEAD frames
    before the shot, and the pad (pad 1) for each frame from there."""
    if "m" not in _rec:
        f = Path.home() / "Documents" / "NHL94 Viewer" / "matches" / f"{MATCH}.js"
        t = open(f, encoding="utf-8").read()
        _rec["m"] = json.loads(t[t.index("{"):t.rindex("}") + 1])
    m = _rec["m"]
    if key in _rec:
        return _rec[key]
    T = m["t"]
    sh = next(s for s in m["shotList"] if s["team"] == 0 and
              f"P{m['period'][s['f']] + 1}-{m['clock'][s['f']] // 60}:{m['clock'][s['f']] % 60:02d}" == key)
    i = sh["f"]
    k = i
    while m["owner"][k] == -1:
        k -= 1
    sc = m["owner"][k]
    gk = next(r for r in range(6, 12) if m["role"][i * 12 + r] == "0")

    def at(ms):
        return max(q for q in range(i - 400, i + 40) if T[q] <= ms)
    t0 = T[i] - LEAD * 1000 / 60
    s0, s1 = at(t0), at(t0 + 100)                              # the speed over about 6 frames
    dt = max(1.0, (T[s1] - T[s0]) * 60 / 1000)

    def obj(r):
        return (m["pos"][s0 * 24 + 2 * r], m["pos"][s0 * 24 + 2 * r + 1],
                (m["pos"][s1 * 24 + 2 * r] - m["pos"][s0 * 24 + 2 * r]) / dt,
                (m["pos"][s1 * 24 + 2 * r + 1] - m["pos"][s0 * 24 + 2 * r + 1]) / dt)
    ev = sorted(m["padSnes"])

    def pad1(q):
        v = 0
        for x in ev:
            if x[0] > q:
                break
            v = x[1]
        return v
    pads = [pad1(at(t0 + f * 1000 / 60)) for f in range(LEAD + 30)]
    work = lambda r: next(w[2:] for w in reversed(m["work"]) if w[1] == r and w[0] <= i)   # working ratings
    _rec[key] = dict(top=sh["y"] > 0, sk=obj(sc), face=int(m["facing"][s0 * 12 + sc]), g=obj(gk), pads=pads,
                     work=(work(sc), work(gk)))
    return _rec[key]


BITS = [(0x800, "UP"), (0x400, "DOWN"), (0x200, "LEFT"), (0x100, "RIGHT"), (0x80, "A")]
FLIP = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT", "A": "A"}


def replay(args):
    """One recorded try (plan "replay"): see the module notes."""
    _move, net, side, hand, key, _kind, _z, aim = args
    h = _h[net]
    e = h.e
    sg = 1 if net == "top" else -1
    r = recorded(key)
    fl = 1 if (sg > 0) == r["top"] else -1                     # turned round when played at the other net
    s, g = H.o(H.SHOOTER), H.o(H.GOALIE)
    rnd = random.Random(zlib.crc32(json.dumps(args).encode()))
    res = dict(shots=0, goals=0, n=0, noshot=0, lost=0, carried=0, moments=0, release=[0.0, 0.0], gslide=0.0,
               gx=0.0, face={})

    def att(k):
        return sg * h.sw(H.XPOS + k), GOAL_Y - sg * h.sw(H.YPOS + k)
    for p in range(MOMENTS):
        res["moments"] += 1
        out, pre, last, gpath = approach(h, r, fl, hand, side, sg, aim, p, rnd)
        if out != "shot":
            res[out] += 1
        breathe()
        if pre is None:
            continue
        e.unserialize(pre)
        res["shots"] += 1
        px, pout = att(H.o(H.PUCK))
        res["release"][0] += side * px
        res["release"][1] += pout
        res["gx"] += side * gpath[-1]
        res["gslide"] += side * (gpath[max(0, len(gpath) - 61)] - gpath[-1])
        fc = str(e.w(FACING + s) if sg > 0 else (e.w(FACING + s) + 4) % 8)
        res["face"][fc] = res["face"].get(fc, 0) + 1
        aimd = screen_dir(last)
        for _ in range(SEEDS):
            h.fire(pre, aimd, rnd.getrandbits(32))
            q, _f = h.decide()
            res["n"] += 1
            res["goals"] += q
        breathe()
    if res["shots"]:
        res["release"] = [round(v / res["shots"], 1) for v in res["release"]]
        res["gx"], res["gslide"] = round(res["gx"] / res["shots"], 1), round(res["gslide"] / res["shots"], 1)
    return dict(zip(KEYS, args), **res)


def approach(h, r, fl, hand, side, sg, aim, p, rnd):
    """One moment of a recorded try up to the shot: set up (the moment's settle, clock and seed from rnd), the hand,
    the recorded working ratings, speed and facing, the goalie where he was, then the recorded pads (turned round when
    fl is -1; from the A press the aim's when aim is not "played"). Returns (outcome: "shot" / "carried" / "lost" /
    "noshot", the state just before the release frame, the last d-pad held, the goalie's path across)."""
    e = h.e
    s, g = H.o(H.SHOOTER), H.o(H.GOALIE)
    x, y, vx, vy = r["sk"]
    h.setup(round(fl * x), round(fl * y), settle=80 + (p * 7) % 15, clock=590 - p % 8, seed=rnd.getrandbits(32))
    w = e.w(ATTR + s)
    e.setw(ATTR + s, (w | 0x800) if hand == "R" else (w & ~0x800))
    for k, wk in ((s, r["work"][0]), (g, r["work"][1])):     # the recorded skater's and goalie's working ratings
        for a, v in zip(WORK, wk):
            e.setw(a + k, v)
    e.setw(FACING + s, r["face"] if fl > 0 else (r["face"] + 4) % 8)
    e.setw(H.XVEL + s, round(fl * vx * 4096) & 0xFFFF)
    e.setw(H.YVEL + s, round(fl * vy * 4096) & 0xFFFF)
    gx0, gy0, _gvx, _gvy = r["g"]
    h.put(H.GOALIE, round(fl * gx0), round(fl * gy0))
    s0 = e.w(H.SCORE_HOME)
    gpath, pressed, last = [], None, []
    for f, v in enumerate(r["pads"]):
        gpath.append(sg * h.sw(H.XPOS + g))
        d = [b for bit, b in BITS if v & bit]
        if fl < 0:
            d = [FLIP[b] for b in d]
        if "A" in d and pressed is None:
            pressed = f
        if pressed is not None and aim != "played":
            d = (["A"] if "A" in d else []) + aim_pad(aim, side, sg)
        st = e.serialize()
        h.park()
        e.run(1, hold=d)
        last = [b for b in d if b != "A"]
        if e.w(H.SCORE_HOME) != s0:
            return "carried", None, last, gpath
        if e.w(H.PUCKC) != s:
            if pressed is not None and e.w(H.PUCKC) & 0x8000:
                return "shot", st, last, gpath
            return "lost", None, last, gpath
    return "noshot", None, last, gpath


def pad(ax, ay, sg):
    """The d-pad for an attacker's-view direction (ax: + his right, ay: + toward the goal), as screen buttons."""
    sx, sy = sg * ax, sg * ay
    return (["UP"] if sy > 0 else ["DOWN"] if sy < 0 else []) + (["RIGHT"] if sx > 0 else ["LEFT"] if sx < 0 else [])


def aim_pad(aim, near, sg):
    """The shot's d-pad: the near side (screen) and, for "high", screen Up whichever way he attacks."""
    side = ["RIGHT"] if sg * near > 0 else ["LEFT"]
    return (["UP"] if aim == "high" else []) + side


def screen_dir(buttons):
    dx = ("RIGHT" in buttons) - ("LEFT" in buttons)
    dy = ("UP" in buttons) - ("DOWN" in buttons)
    return 8 if dx == dy == 0 else round(math.degrees(math.atan2(dx, dy)) / 45) % 8


def job(args):
    move, net, side, hand, x0, a, b, aim = args
    if move == "replay":
        return replay(args)
    h = _h[net]
    e = h.e
    sg = 1 if net == "top" else -1
    s, g = H.o(H.SHOOTER), H.o(H.GOALIE)
    rnd = random.Random(zlib.crc32(json.dumps(args).encode()))
    res = dict(shots=0, goals=0, n=0, noshot=0, lost=0, carried=0, moments=0, release=[0.0, 0.0], gslide=0.0,
               gx=0.0, face={})
    att = lambda k: (sg * h.sw(H.XPOS + k), GOAL_Y - sg * h.sw(H.YPOS + k))       # attacker's view (across, out)
    for p in range(MOMENTS):
        h.setup(sg * side * x0, sg * (GOAL_Y - START_OUT), settle=80 + (p * 7) % 15, clock=590 - p % 8,
                seed=rnd.getrandbits(32))
        w = e.w(ATTR + s)
        e.setw(ATTR + s, (w | 0x800) if hand == "R" else (w & ~0x800))
        res["moments"] += 1
        s0 = e.w(H.SCORE_HOME)
        gpath, phase, pressed, pre, k = [], 0, None, None, 0
        for f in range(420):
            ax, out = att(s)
            gpath.append(att(g)[0])
            if move == "cut":
                if phase == 0 and out <= CUT_OUT:
                    phase = 1
                if phase == 1 and out <= a:
                    phase = 2
                if phase in (1, 2) and out <= b and pressed is None:
                    pressed = f
                d = (pad(0, 1, sg) if phase == 0 else pad(-side, 1, sg) if phase == 1 else pad(side, 1, sg))
            else:
                if phase < 2 and out <= a:
                    phase, k = 2, f
                elif phase == 0 and out <= a + 40:
                    phase = 1
                if phase == 2 and f >= k + b and pressed is None:
                    pressed = f
                d = pad(0, 1, sg) if phase == 0 else pad(-side, 1, sg) if phase == 1 else pad(side, 0, sg)
            if pressed is not None:
                d = aim_pad(aim, side, sg)
            st = e.serialize()
            h.park()
            e.run(1, hold=(["A"] if pressed is not None and f < pressed + 3 else []) + d)
            if e.w(H.SCORE_HOME) != s0:
                res["carried"] += 1
                break
            if e.w(H.PUCKC) != s:
                if pressed is not None and e.w(H.PUCKC) & 0x8000:
                    pre = st
                else:
                    res["lost"] += 1
                break
        else:
            res["noshot"] += 1
        breathe()
        if pre is None:
            continue
        e.unserialize(pre)
        res["shots"] += 1
        px, pout = att(H.o(H.PUCK))
        res["release"][0] += side * px                                    # + toward his own side
        res["release"][1] += pout
        res["gx"] += side * gpath[-1]                                     # + toward his own side
        res["gslide"] += side * (gpath[max(0, len(gpath) - 61)] - gpath[-1])   # the last second, + toward the middle
        fc = str(e.w(FACING + s) if sg > 0 else (e.w(FACING + s) + 4) % 8)
        res["face"][fc] = res["face"].get(fc, 0) + 1
        aimd = screen_dir(aim_pad(aim, side, sg))
        for _ in range(SEEDS):
            h.fire(pre, aimd, rnd.getrandbits(32))
            r, _f = h.decide()
            res["n"] += 1
            res["goals"] += r
        breathe()
    if res["shots"]:
        res["release"] = [round(v / res["shots"], 1) for v in res["release"]]
        res["gx"], res["gslide"] = round(res["gx"] / res["shots"], 1), round(res["gslide"] / res["shots"], 1)
    return dict(zip(KEYS, args), **res)


def main():
    plan, run = sys.argv[1], sys.argv[2]
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    path = RUNS / run / f"snes_deke_{plan}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        for line in open(path):
            d = json.loads(line)
            done.add(tuple(d[k] for k in KEYS))
    todo = [j for j in plan_jobs(plan) if j not in done]
    print(f"{plan}: {len(done)} jobs done before, {len(todo)} to go; this chunk: up to {minutes:g} minutes", flush=True)
    t0, deadline, finished = time.time(), time.time() + 60 * minutes, 0
    with Pool(WORKERS, initializer=_init) as pool, open(path, "a") as f:
        pending, queue = [], list(todo)
        while queue or pending:
            while queue and len(pending) < WORKERS and time.time() < deadline:
                pending.append(pool.apply_async(job, (queue.pop(0),)))
            if not pending:
                break
            time.sleep(1)
            for r in [r for r in pending if r.ready()]:
                pending.remove(r)
                f.write(json.dumps(r.get()) + "\n")
                f.flush()
                finished += 1
    print(f"chunk over: {finished} jobs in {(time.time() - t0) / 60:.1f} minutes; {len(todo) - finished} left", flush=True)


if __name__ == "__main__":
    main()
