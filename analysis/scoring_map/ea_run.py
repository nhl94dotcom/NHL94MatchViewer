"""EA Specials in the real game (Genesis test ROM), 2026-10-24. The play (the user): from the side, on his forehand,
a skater takes a wrist shot meant to be bobbled, the save pushing the goalie back; he skates on, claims the loose puck
and at once shoots a wrist shot inside the near post, open because the goalie was pushed back (and may have gone into
a dive trying to smother it). The user: the best shooters are bad at it (their harder wrist shots are caught and held
more), middling shooters' shots are saved but bobbled more. So each job is one shooter (working Shot Power and Shot
Accuracy, roster steps 2-6 = 10-30) at one spot; each aim, each of MOMENTS moments, SEEDS seeds after the release.
Standing or skating toward the net (MOVES). Per play: the first result (goal straight in; held; touched and loose = a bobble; missed), the release speed; for a
bobble the loose puck's speed, how far the goalie went back toward his line, a dive, whether and how fast the shooter
claimed it, and the follow-up (goal, held, none). Spots in the attacker's view on the forehand side (a left-hander:
his right). Gentle mode, chunked.
Plans: "ea" (the first run: 40 / 70 / 100 to the side, standing or skating straight up the ice); "firm" (2026-10-24:
40 to the side only, Shot Accuracy 2 / 4 / 6, for more moments: NHL94_EA_MOMENTS; one set-up's rate over 8 moments
wandered: ea_animate.py); "dots" (the user, 2026-10-24: more EA Specials come from farther to the side, on or near the
end-zone faceoff dot, 70 to the side and about 60 out, with the skater skating toward the goal as he shoots: move
"goal<speed>" sets his speed toward the middle of the goal line and he keeps skating at the goal after the shot);
"angle" (the user, 2026-10-25: the shooter always faces straight across the rink or diagonally toward the goalie
as he shoots, never straight up the ice, so he is placed to claim the rebound: moves "across<speed>" (straight
across toward the middle), "diag<speed>" (45 degrees toward the middle and the goal line) and "goal<speed>"; Shot
Accuracy 4; for the goalie profiles too, NHL94_GOALIE); "xspot" (the user, 2026-10-25, two marked screenshots: the
release level with the faceoff dot across and a little deeper, about 40-44 out against the dot's 62): x and out are
where the puck is released, not where he starts (a move "r<kind><speed>" starts him LEAD frames of skating back, the
wrist shot leaving the stick 4 frames after C); a negative x is his left side, taken by a right-hander (a
left-hander from his right, a right-hander from his left: the user, 2026-10-25); skating at the goal at 1.5 or 2.5 a
frame or in at 45 degrees; each job also gives the mean release spot ("release": across, out).
python ea_run.py RUN [minutes] [plan]   -> paths.RUNS / RUN / ea.jsonl (plan "ea") or ea_<plan>.jsonl"""
import itertools
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool

from harness import Harness, rec, DIRPAD, E, SHOOTER, GOALIE, PUCKC, SCORE_HOME
from lowload import WORKERS, breathe, gentle
from mapper import set_ratings
from paths import RUNS, STATE_TOP, STATE_BOTTOM

MOMENTS, SEEDS = int(os.environ.get("NHL94_EA_MOMENTS") or 8), 2
GOAL_Y = 264
FIRST, FOLLOW = 60, 90         # frames to the first result; frames more for the follow-up
STEPS = (2, 3, 4, 5, 6)        # roster steps (x 5 = working)
PUCK = 14
KEYS = ("net", "x", "out", "shp", "sha", "move")
LEAD = 4                       # frames from C to the release of a wrist shot (measured 2026-10-25)
MOVES = (0.0, 1.5)             # standing, or skating toward the net at 1.5 a frame as he shoots (down the side)


def plan_jobs(plan="ea"):
    if plan == "firm":
        return list(itertools.product(("top", "bottom"), (40,), (60, 90, 120), STEPS, (2, 4, 6), MOVES))
    if plan == "angle":
        return list(itertools.product(("top", "bottom"), (55, 70, 85), (45, 60, 75), (2, 4, 6), (4,),
                                      ("across2.5", "diag2.5", "goal2.5")))
    if plan == "xspot":
        return list(itertools.product(("top", "bottom"), (-75, -70, -65, 65, 70, 75), (38, 42, 46), (2, 4, 6), (4,),
                                      ("rgoal1.5", "rgoal2.5", "rdiag2.5")))
    if plan == "dots":
        return list(itertools.product(("top", "bottom"), (55, 70, 85), (45, 60, 75), STEPS, (2, 4, 6),
                                      ("goal1.5", "goal2.5")))
    return list(itertools.product(("top", "bottom"), (40, 70, 100), (60, 90, 120), STEPS, STEPS, MOVES))


_h = {}


def _init():
    gentle()
    top = Harness(state=STATE_TOP, top=True)
    _h["top"], _h["bottom"] = top, Harness(state=STATE_BOTTOM, top=False, emu=top.e)


def toward(dx, dy):
    """The d-pad direction (0 up the screen, clockwise) nearest to (dx, dy) (screen: +y up the screen)."""
    return round(math.degrees(math.atan2(dx, dy)) / 45) % 8


def park_except(h, keep):
    e = h.e
    for k in range(12):
        if k == GOALIE or k in keep:
            continue
        e.setw(rec(k), -100 + 18 * k)
        e.setw(rec(k) + 0x14, h.park_y)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(k) + off, 0)


DIVE = 0x02F4                  # the goalie's dive animation ($02F4)


def play(h, sg, at_goal=False):
    """From the release (the user's play): the shooter skates on toward the net; once the goalie has touched the puck
    and it is loose, he skates at it, and as soon as he has it taps C aimed at the near post (the side of the net he
    is on: a wrist shot at once). Returns the first result ('goal' straight in, 'held', 'bobble', 'miss') and what
    happened after a bobble."""
    e = h.e
    s0 = e.w(SCORE_HOME)
    touched, pv, info = None, None, dict(back=0.0, dive=False, claim=None, shot=False, follow="none")
    g0 = None
    for f in range(FIRST + FOLLOW):
        park_except(h, (SHOOTER,))
        sx, sy = e.sw(rec(SHOOTER)), e.sw(rec(SHOOTER) + 0x14)
        px, py = e.sw(rec(PUCK)), e.sw(rec(PUCK) + 0x14)
        gx, gy = e.sw(rec(GOALIE)), e.sw(rec(GOALIE) + 0x14)
        if g0 is None:
            g0 = gy
        if e.w(PUCKC) == SHOOTER and touched is not None and not info["shot"]:
            info["claim"], info["shot"] = f - touched, True
            aim = 2 if sx > 0 else 6                     # the near post: the side of the net he is on (screen)
            for c in range(3):
                park_except(h, (SHOOTER,))
                e.run(1, hold=["C"] + DIRPAD[aim])
            continue
        if touched is None or info["shot"]:
            if at_goal:                                  # on at the middle of the goal line
                pad = DIRPAD[toward(-sx, sg * GOAL_Y - sy)]
            else:
                pad = DIRPAD[0 if sg > 0 else 4]         # on toward the net
        else:
            pad = DIRPAD[toward(px - sx, py - sy)]
        e.run(1, hold=pad)
        if e.w(SCORE_HOME) != s0:
            if touched is None:
                return "goal", info
            info["follow"] = "goal" if info["shot"] else "in_off_goalie"
            return "bobble", info
        if e.w(PUCKC) == GOALIE:
            if touched is None or (not info["shot"] and info["claim"] is None and f - touched < 4):
                return "held", info
            info["follow"] = "held"
            return "bobble", info
        vx, vy = e.sw(rec(PUCK) + 0x28), e.sw(rec(PUCK) + 0x2A)
        if touched is None:
            if pv is not None and math.hypot(px - gx, py - gy) < 24 and                     vx * pv[0] + vy * pv[1] < 0.5 * (pv[0] ** 2 + pv[1] ** 2):
                touched = f                              # turned or slowed hard beside the goalie: a save
                info["v"] = round(math.hypot(vx, vy))
            elif sg * py > GOAL_Y + 12 or f >= FIRST:
                return "miss", info
        else:
            if f - touched <= 20:                        # pushed back: toward his goal line, from where he stood
                info["back"] = max(info["back"], round(sg * (gy - g0), 1))
            if e.w(rec(GOALIE) + 0x58) == DIVE:
                info["dive"] = True
        pv = (vx, vy)
    return ("bobble" if touched is not None else "miss"), info


def job(args):
    net, x, out, shp, sha, move = args
    h = _h[net]
    e = h.e
    top = net == "top"
    sg = 1 if top else -1
    rnd = random.Random(zlib.crc32(json.dumps(args).encode()))
    res, rel = {}, [0.0, 0.0, 0]
    at_release = isinstance(move, str) and move.startswith("r")
    for p in range(MOMENTS):
        clock, settle = 590 - (p * 3) % 8, 80 + (p * 7) % 15
        x0, y0 = sg * x, sg * (GOAL_Y - out)
        if isinstance(move, str):                        # skating toward the middle: across, 45 degrees, at the goal
            kind = move.rstrip("0123456789.").lstrip("r")
            sx = 1 if x > 0 else -1                      # the side he is on (attacker's view)
            dx, dy = dict(goal=(-sg * x, sg * out), across=(-sg * sx, 0), diag=(-sg * sx, sg))[kind]
            v = float(move[len(move.rstrip("0123456789.")):]) / math.hypot(dx, dy)
            if at_release:                               # started back along his line, to release at (x, out)
                x0, y0 = round(x0 - LEAD * dx * v), round(y0 - LEAD * dy * v)
        h.setup(x0, y0, settle=settle, clock=clock)
        set_ratings(h, shp * 5, sha * 5)
        b, a = e.b(rec(SHOOTER) + 0x76), e.b(rec(SHOOTER) + 4)      # the hand (as deke_run.job): a left-hander on
        e.setb(rec(SHOOTER) + 0x76, (b | 1) if x > 0 else (b & ~1))   # his right, a right-hander on his left
        e.setb(rec(SHOOTER) + 4, (a & ~8) if x > 0 else (a | 8))
        if isinstance(move, str):
            e.setb(rec(SHOOTER) + 0x55, toward(dx, dy))
            e.setw(rec(SHOOTER) + 0x28, round(dx * v * 4096) & 0xFFFF)
            e.setw(rec(SHOOTER) + 0x2A, round(dy * v * 4096) & 0xFFFF)
        elif move:
            e.setb(rec(SHOOTER) + 0x55, 0 if top else 4)
            e.setw(rec(SHOOTER) + 0x2A, round(sg * move * 4096) & 0xFFFF)
        base = e.serialize()
        for aim in range(9):
            c = res.setdefault(str(aim), dict(n=0, goal=0, held=0, bobble=0, miss=0, noshot=0, speed=0, bob_v=0,
                                              bob_back=0, dive=0, claimed=0, claim_f=0, follow_goal=0,
                                              follow_held=0, follow_none=0, follow_in_off_goalie=0))
            e.unserialize(base)
            pre, _f = h.shoot(aim, 3)
            if pre is None:
                c["noshot"] += 1
                continue
            e.unserialize(pre)
            rel[0] += sg * e.sw(rec(SHOOTER))
            rel[1] += GOAL_Y - sg * e.sw(rec(SHOOTER) + 0x14)
            rel[2] += 1
            for s in range(SEEDS):
                e.unserialize(pre)
                e.setl(0xD066, rnd.getrandbits(32))
                h.park()
                e.run(1, hold=DIRPAD[aim])
                c["speed"] += math.hypot(e.sw(rec(PUCK) + 0x28), e.sw(rec(PUCK) + 0x2A))
                r, info = play(h, sg, at_goal=isinstance(move, str))
                c["n"] += 1
                c[r] += 1
                if r == "bobble":
                    c["bob_v"] += info.get("v", 0)
                    c["bob_back"] += info["back"]
                    c["dive"] += info["dive"]
                    c["claimed"] += info["claim"] is not None
                    c["claim_f"] += info["claim"] or 0
                    c["follow_" + info["follow"]] += 1
                breathe()
    for c in res.values():
        if c["n"]:
            c["speed"] = round(c["speed"] / c["n"])
        if c["bobble"]:
            c["bob_v"] = round(c["bob_v"] / c["bobble"])
            c["bob_back"] = round(c["bob_back"] / c["bobble"], 1)
        if c["claimed"]:
            c["claim_f"] = round(c["claim_f"] / c["claimed"], 1)
    out_ = dict(zip(KEYS, args), aims=res)
    if rel[2]:
        out_["release"] = [round(rel[0] / rel[2], 1), round(rel[1] / rel[2], 1)]
    return out_


def main():
    run = sys.argv[1]
    minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    plan = sys.argv[3] if len(sys.argv) > 3 else "ea"
    path = RUNS / run / ("ea.jsonl" if plan == "ea" else f"ea_{plan}.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        for line in open(path):
            d = json.loads(line)
            done.add(tuple(d[k] for k in KEYS))
    todo = [j for j in plan_jobs(plan) if j not in done]
    print(f"EA Specials: {len(done)} jobs done before, {len(todo)} to go; this chunk: up to {minutes:g} minutes", flush=True)
    t0, deadline, finished = time.time(), time.time() + 60 * minutes, 0
    with Pool(WORKERS, initializer=_init) as pool, open(path, "a") as f:
        pending, queue = [], list(todo)
        while queue or pending:
            while queue and len(pending) < WORKERS and time.time() < deadline:
                pending.append(pool.apply_async(job, (queue.pop(0),)))
            if not pending:
                break
            time.sleep(1)
            for a in [a for a in pending if a.ready()]:
                pending.remove(a)
                f.write(json.dumps(a.get()) + "\n")
                f.flush()
                finished += 1
    print(f"chunk over: {finished} jobs in {(time.time() - t0) / 60:.1f} minutes; {len(todo) - finished} left", flush=True)


if __name__ == "__main__":
    main()
