"""Press or sit back on the SNES (retail ROM, snes_harness; 2026-10-30): posture_run.py's test, the same rushes and
postures, on the SNES. Read posture_run's docstring first; the differences:
- the attack: the carrier is the home centre (object 2, pad 1; Shot Power and Accuracy 13, as the one-timer study);
  he shoots with A (tapped 3 frames, the aim held); the pass is B held 4 frames with the d-pad at the teammate
  (the SNES loop reads pads every other frame: ot_harness), the one-timer A held 2 frames with the far side held (the
  SNES aims the strike by the d-pad held through the swing);
- no "deke" attack (the SNES deke runner's moves built from scratch aren't tuned: snes_deke_run.py), and on both
  systems a "slot" attack (the lone carrier going on to 35 out before he shoots);
- the defender (pad 2: cont2team, teampads, padside, c1playernum and playerpad for pad 2, pflags bit 3) is the away
  left defenceman, object 10, with the state's ratings; he pokes with B and checks with A (the SNES buttons, SNES_MECHANICS
  "Buttons");
- the shot and the pass are triggered by the puck's distance out, not the carrier's (an SNES carrier skating
  straight has the puck up to 24 ahead of him; triggered by his own, the puck reached the goalie first);
- shots are found by the game's shotplayer ($0D29) changing, the strike frame replayed with SEEDS release seeds.
Penalties are off in the states (OptPen $34C4 = 0), as in the user's league.
python snes_posture_run.py PLAN RUN [minutes]   -> paths.RUNS / RUN / snes_posture_<PLAN>.jsonl   (plans: pilot, full)"""
import itertools
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool

import snes_harness as H
from lowload import WORKERS, breathe, gentle
from paths import RUNS, SNES_STATE_TOP, SNES_STATE_BOTTOM
from posture_run import (direction, CREEP, GOAL_Y, POSTURES, KEYS, REACT, MATE_X, SHOOT_OUT, SLOT_OUT, PASS_OUT,
                         START_OUT, DEF_OUT, SPEED)

MOMENTS = int(os.environ.get("NHL94_POSTURE_MOMENTS") or 24)
SEEDS = 4
DEF, MATE, PUCK, SHOOTER, GOALIE = 10, 0, 14, H.SHOOTER, H.GOALIE
ATTR, FACING, PFLAGS = 0x0E03, 0x1163, 0x1283
SHOTPLAYER = 0x0D29
CONT2TEAM, TEAMPADS, PLAYERPAD, C1PLAYERNUM, PADSIDE = 0x1C86, 0x19D0, 0x19D4, 0x19EC, 0x19F6
DIRPAD = H.DIRPAD
OT_AIM = os.environ.get("NHL94_SPOSTURE_OTAIM") or "none"     # the best of five in the pilot (none 64%, near 51%,
# far 24-28% with no defender)


def o(k):
    return 2 * k


class PostureHarness(H.Harness):
    def_spot = mate_spot = None
    pin = True

    def park(self, keep_shooter=True):
        keep = {GOALIE}
        if keep_shooter:
            keep.add(SHOOTER)
        if self.def_spot:
            keep.add(DEF)
        if self.mate_spot and keep_shooter:
            keep.add(MATE)
        for k in range(12):
            if k not in keep:
                self.put(k, -100 + 18 * k, self.park_y)
        if not self.pin:
            return
        sg = 1 if self.top else -1
        for k, spot in ((DEF, self.def_spot), (MATE, self.mate_spot)):
            if spot:
                self.put(k, *spot)
                self.e.setw(H.YVEL + o(k), (-sg if k == DEF else sg) * CREEP & 0xFFFF)


def plan_jobs(plan):
    jobs = []
    for net, hand in itertools.product(("top", "bottom"), ("L", "R")):
        lanes = [(a, x) for a in ("solo", "slot") for x in (-50, 0, 50)] + [("2on1", x) for x in (-50, 50)]
        if plan == "pilot":
            lanes = [("solo", 0), ("slot", 50), ("2on1", 50)]
            if (net, hand) != ("top", "L"):
                continue
        for (attack, lane), posture in itertools.product(lanes, POSTURES):
            jobs.append((attack, net, hand, lane, posture))
    if plan not in ("pilot", "full"):
        raise SystemExit(f"unknown plan {plan}")
    return jobs


_h = {}


def _init():
    gentle()
    top = PostureHarness(state=SNES_STATE_TOP, top=True)
    _h["top"], _h["bottom"] = top, PostureHarness(state=SNES_STATE_BOTTOM, top=False, emu=top.e)


def job(args):
    attack, net, hand, x0, posture = args
    h = _h[net]
    e = h.e
    top = net == "top"
    sg = 1 if top else -1
    gl = sg * GOAL_Y
    rnd = random.Random(zlib.crc32(json.dumps(args).encode()))
    shoot_out = SLOT_OUT if attack == "slot" else SHOOT_OUT

    def scr(x, out):
        return round(sg * x), round(sg * (GOAL_Y - out))

    def xy(k):
        return h.sw(H.XPOS + o(k)), h.sw(H.YPOS + o(k))

    def out_of(y):
        return GOAL_Y - sg * y

    def far_side(px):
        a = 6 if sg * px > 0 else 2
        return a if top else (a + 4) % 8

    def ot_aim(far):                                     # the one-timer's d-pad from the far side's (OT_AIM)
        side = 1 if far in (2, 6) and (far == 6) == top else -1    # +1: the far side is screen left at the top net
        return {"far": far, "near": (far + 4) % 8, "farlow": (far + (1 if far == 6 else -1)) % 8 if top else
                (far + (1 if far == 2 else -1)) % 8, "farhigh": (far - (1 if far == 6 else -1)) % 8 if top else
                (far - (1 if far == 2 else -1)) % 8, "none": 8}[OT_AIM]

    res = dict(n=0, shot=0, lost=0, loose=0, none=0, goals=0.0, poked=0, release=[0.0, 0.0], frames=0.0, ddist=0.0,
               onetimer=0, react=0, moments=[])
    for p in range(MOMENTS):
        clock, settle = 590 - p % 8, 80 + (p * 7) % 15
        h.def_spot = None if posture == "none" else scr(x0 / 2, DEF_OUT)
        h.mate_spot = scr(MATE_X if x0 < 0 else -MATE_X, START_OUT) if attack == "2on1" else None
        h.pin = True
        h.setup(*scr(x0, START_OUT), settle=settle, clock=clock, seed=rnd.getrandbits(32))
        for k in (SHOOTER, MATE):
            e.setw(H.SHOTSPD + o(k), 13)
            e.setw(H.SHOTACC + o(k), 13)
        w = e.w(ATTR + o(SHOOTER))
        e.setw(ATTR + o(SHOOTER), (w | 0x800) if hand == "R" else (w & ~0x800))
        e.setw(FACING + o(SHOOTER), 0 if top else 4)
        e.setw(H.XVEL + o(SHOOTER), 0)
        e.setw(H.YVEL + o(SHOOTER), round(sg * SPEED * 4096) & 0xFFFF)
        if attack == "2on1":
            e.setw(FACING + o(MATE), 0 if top else 4)
            e.setw(H.YVEL + o(MATE), round(sg * SPEED * 4096) & 0xFFFF)
        if posture != "none":                             # pad 2 on the away team, on the defender
            e.setw(CONT2TEAM, 2)
            e.setw(TEAMPADS + 2, 1)
            e.setw(PADSIDE + 2, 2)
            e.setw(C1PLAYERNUM + 2, o(DEF))
            e.setw(PLAYERPAD + o(DEF), 2)
            e.setw(PFLAGS + o(DEF), e.w(PFLAGS + o(DEF)) | 8)
            e.setw(FACING + o(DEF), 4 if top else 0)
            e.setw(H.YVEL + o(DEF), round(sg * SPEED * 4096) & 0xFFFF)     # skating back with the rush
        e.setw(SHOTPLAYER, 0xFFFF)
        h.pin = False
        mate_y0 = h.mate_spot[1] if h.mate_spot else None
        pre = None
        passed = poked = lost = False
        bt = bcool = ccool = 0
        pressing = posture in ("press", "presscheck")
        pass_t = c_from = None
        shooter, aim = SHOOTER, 8
        for f in range(300):
            c = e.w(H.PUCKC)
            carrier = None if c & 0x8000 else c // 2
            px, py = xy(PUCK)
            if carrier is not None and 6 <= carrier <= 11:
                lost = True
                break
            if carrier in (SHOOTER, MATE):
                shooter = carrier
            if pass_t is not None and carrier != SHOOTER:
                passed = True                             # the puck leaves while B is still held
            if attack == "2on1" and not passed:
                h.put(MATE, h.mate_spot[0], round(mate_y0 + sg * SPEED * f))
                e.setw(H.YVEL + o(MATE), round(sg * SPEED * 4096) & 0xFFFF)
            # --- pad 1
            pad1, btn = [], []
            if carrier == SHOOTER and not passed:
                sx, sy = xy(SHOOTER)
                so = out_of(py)                           # by the puck: it runs up to 24 ahead of an SNES carrier
                dfx, dfy = xy(DEF) if posture != "none" else (9999, 9999)
                blocked = math.hypot(dfx - sx, dfy - sy) <= REACT and out_of(dfy) < out_of(sy) + 5
                if attack == "2on1" and (so <= PASS_OUT or blocked and so <= 150):
                    if pass_t is None:
                        pass_t = f
                    mx, my = xy(MATE)
                    pad1 = DIRPAD[direction(mx - sx, my - sy)]
                    if f < pass_t + 4:
                        btn = ["B"]
                    else:
                        passed = True
                else:
                    tx, ty = scr(x0 * 0.4, 20 if attack == "slot" else 45)
                    d = direction(tx - sx, ty - sy)
                    if c_from is None and (so <= shoot_out or blocked and so <= 150):
                        c_from, aim = f, far_side(px)
                        res["react"] += blocked
                    pad1 = DIRPAD[aim if c_from is not None else d]
            elif carrier == MATE:                         # took it on his stick: shoot at once
                if c_from is None:
                    c_from, aim = f, far_side(px)
                pad1 = DIRPAD[aim]
            elif passed and carrier is None:
                mx, my = xy(MATE)
                if c_from is None:                        # A as soon as the pass is away (ot_harness "early")
                    c_from, aim = f, ot_aim(far_side(mx))
                if c_from is not None:
                    pad1 = DIRPAD[aim]
            if c_from is not None and f < c_from + (2 if passed else 3):
                btn = ["A"]
            elif carrier is None and not passed and pass_t is None and f > 2:
                poked = True
            # --- pad 2
            pad2 = []
            if posture != "none":
                dx, dy = xy(DEF)
                vx, vy = h.sw(H.XVEL + o(PUCK)) / 4096, h.sw(H.YVEL + o(PUCK)) / 4096
                cx, cy = xy(shooter)
                if posture == "sitpress" and not pressing and math.hypot(cx - dx, cy - dy) <= 30:
                    pressing = True
                if pressing:
                    tx, ty = px + 6 * vx, py + 6 * vy
                    pad2 = DIRPAD[direction(tx - dx, ty - dy)]
                    if posture == "presscheck":
                        if ccool == 0 and math.hypot(cx - dx, cy - dy) <= 40:
                            pad2, ccool = pad2 + ["A"], 30
                    else:
                        if bt == 0 and bcool == 0 and math.hypot(px - dx, py - dy) <= 28:
                            bt, bcool = 3, 20
                        if bt > 1:
                            pad2 = pad2 + ["B"]
                else:
                    L = math.hypot(-px, gl - py) or 1
                    k = min(45, L)
                    tx, ty = px + (-px) * k / L, py + (gl - py) * k / L
                    if out_of(ty) < 30:
                        ty = sg * (GOAL_Y - 30)
                    if attack == "2on1":
                        tx *= 0.5
                    if math.hypot(tx - dx, ty - dy) > 6:
                        pad2 = DIRPAD[direction(tx - dx, ty - dy)]
                bt, bcool, ccool = max(0, bt - 1), max(0, bcool - 1), max(0, ccool - 1)
            st = e.serialize()
            h.park()
            e.run(1, hold=btn + pad1, hold2=pad2)
            if e.w(SHOTPLAYER) != 0xFFFF:
                pre, ot = st, passed and carrier is None
                break
            breathe()
        res["n"] += 1
        res["poked"] += poked
        if pre is None:
            c = e.w(H.PUCKC)
            kind = "lost" if lost else "loose" if c & 0x8000 else "none"
            res[kind] += 1
            res["moments"].append([kind])
            continue
        e.unserialize(pre)
        sx, sy = xy(shooter)
        px, py = xy(PUCK)
        dx, dy = xy(DEF)
        ddist = math.hypot(sx - dx, sy - dy) if posture != "none" else None
        goals = 0
        for _ in range(SEEDS):
            h.fire(pre, aim, rnd.getrandbits(32))
            g, _f = h.decide()
            goals += g
            breathe()
        rate = goals / SEEDS
        res["shot"] += 1
        res["goals"] += rate
        res["onetimer"] += ot
        res["release"][0] += sg * px
        res["release"][1] += out_of(py)
        res["frames"] += f
        res["ddist"] += ddist or 0
        res["moments"].append(["shot", rate, round(sg * px), round(out_of(py)), f,
                               None if ddist is None else round(ddist)])
    if res["shot"]:
        res["release"] = [round(v / res["shot"], 1) for v in res["release"]]
        for k in ("frames", "ddist"):
            res[k] = round(res[k] / res["shot"], 1)
    return dict(zip(KEYS, args), **res)


def main():
    plan, run = sys.argv[1], sys.argv[2]
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    path = RUNS / run / f"snes_posture_{plan}.jsonl"
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
            for a in [a for a in pending if a.ready()]:
                pending.remove(a)
                f.write(json.dumps(a.get()) + "\n")
                f.flush()
                finished += 1
    print(f"chunk over: {finished} jobs in {(time.time() - t0) / 60:.1f} minutes; {len(todo) - finished} left", flush=True)


if __name__ == "__main__":
    main()
