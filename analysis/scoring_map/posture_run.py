"""Press or sit back, played in the real game (Genesis test ROM; 2026-10-29; DEFENCE_STUDY "Pressure or sit back,
played in the game"). The recorded games couldn't separate the two (analysis/defence_posture.py): defenders pick their
posture to suit the play, and there are few games. Here the posture is fixed and the same rushes are played against
each one.

The attack (pad 1, the home centre, record 2; the puck carrier's ratings the map's usual 20 / 15):
- "solo": a lone carrier from the blue line (176 out, coming in at 2 units a frame) in one of three lanes (x0 = -50,
  0, +50 in the attacker's view, + his right), skating at the slot (x0 x 0.4, 45 out) and taking a wrist shot at the
  far side (middle height) once 70 out; if the defender is within 30 of him and in front, he shoots at once (or, in
  the 2-on-1, passes);
- ("slot", the same carrier going on to 35 out before the shot, was tried 2026-10-30 and dropped on the Genesis: with
  no defender the goalie took the puck before the shot in 93% of rushes; the SNES runner keeps it, see there);
- "deke": deke_run's best "deke2" set-up for the hand (from his left, 124 out, drifting in toward the middle, the swing
  60 from the goalie), the defender starting 76 out; the carrier plays the move whatever the defender does;
- "2on1": the same carrier in a side lane, with a teammate (the home right wing, record 0) skating in level with him
  25 off the middle on the other side; at 70 out the carrier passes across (B with the d-pad at him) and the teammate one-times it (C
  as the puck comes within 40 of him; the game aims it), or shoots at once if he takes it on his stick.
The attackers are bots: fixed inputs; all they see of the defender is that reaction.

The defender (pad 2, the away left defenceman, record 10, with his own ratings in the state: a person controls him,
as cont2team / c2playernum / pflags bit 3 say; penalties off as in the user's league) starts at x0 / 2, 120 out,
facing the play and skating back at the carrier's speed, and then each frame:
- "press": skates at the puck (where it will be in 6 frames) and pokes (a B tap: pressed 2 frames, released, then 20
  frames before the next) once within 28 of it;
- "presscheck": skates at the puck the same way and checks (a C press: the burst into him) once within 40 of the
  carrier, then 30 frames before the next;
- "sit": holds the slot between the puck and the net: the point 45 from the puck along its line to the net's centre,
  never deeper than 30 out (against the 2-on-1 halfway to the middle, to cover the pass); no pokes;
- "sitpress": sits until the carrier is within 30 (10 ft) of him, then presses (pokes) for the rest of the play;
- "none": no defender (the baseline).
The game's own skating takes the inputs: his acceleration, turning and the backwards-skating rule (GENESIS_MECHANICS).
Everyone else is off the ice (parked at the far end) but the two goalies.

Each job: MOMENTS moments (clock, settle, random seed); a shot is played out from its release frame with SEEDS seeds
(harness.decide), so the goal rate of a shot is the share of those. Outcomes: shot (with its goal rate, release spot,
frames from the start, the defender's distance from the shooter), lost (the defence has the puck before a shot), loose
(the puck knocked away and no shot by the end), none (no shot, the attack ran out of time). Chunked and resumable;
gentle mode.
python posture_run.py PLAN RUN [minutes]   -> paths.RUNS / RUN / posture_<PLAN>.jsonl   (plans: pilot, full)"""
import itertools
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool

from harness import Harness, decide, rec, DIRPAD, E, SHOOTER, GOALIE, PUCKC
from lowload import WORKERS, breathe, gentle
from mapper import set_ratings
import deke_run as DR
from paths import RUNS, STATE_TOP, STATE_BOTTOM

MOMENTS = int(os.environ.get("NHL94_POSTURE_MOMENTS") or 24)
SEEDS = 4
GOAL_Y = 264
DEF, MATE, PUCK = 10, 0, 14
CREEP = 64
SHOOT_OUT, PASS_OUT, START_OUT, DEF_OUT, SPEED = 70, 70, 176, 120, 2.0
SLOT_OUT = 35                   # "slot": the lone carrier goes on to here before he shoots
REACT = 30                      # a defender this close in front: the carrier shoots (or passes) at once
DEKE_OUT = 124                  # the deke's start (deke_run: 140 up the ice in its own coordinates)
MATE_X = 25                     # the 2-on-1 teammate's lane (the far side of the slot)
DEKE = {"L": (60, 10), "R": (60, 13)}     # the swing's goalie distance, frames from the swing to C (deke_run "best")
C2PLAYERNUM, CONT2TEAM = 0xC322, 0xC32A
POSTURES = ("none", "press", "presscheck", "sit", "sitpress")
KEYS = ("attack", "net", "hand", "lane", "posture")


def direction(dx, dy):
    """The 8-way d-pad direction nearest to (dx, dy), y up the screen; 8 = none."""
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return 8
    return round(math.degrees(math.atan2(dx, dy)) / 45) % 8


class PostureHarness(Harness):
    """Parks everyone but the goalies, the carrier, the defender and (2-on-1) the teammate. While `pin` is set the
    defender and teammate are held at their start spots (a creep of speed so the game's collision list sees them:
    def_run.py)."""
    def_spot = mate_spot = None
    pin = True

    def park(self, keep_shooter=True):
        e = self.e
        keep = {GOALIE}
        if keep_shooter:
            keep.add(SHOOTER)
        if self.def_spot:
            keep.add(DEF)
        if self.mate_spot and keep_shooter:
            keep.add(MATE)
        for k in range(12):
            if k in keep:
                continue
            e.setw(rec(k), -100 + 18 * k)
            e.setw(rec(k) + 0x14, self.park_y)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(rec(k) + off, 0)
        if not self.pin:
            return
        sg = 1 if self.top else -1
        for k, spot in ((DEF, self.def_spot), (MATE, self.mate_spot)):
            if spot:
                e.setw(rec(k), spot[0])
                e.setw(rec(k) + 0x14, spot[1])
                for off in (0x28, 0x2A, 0x2C):
                    e.setw(rec(k) + off, 0)
                e.setw(rec(k) + 0x2A, (-sg if k == DEF else sg) * CREEP & 0xFFFF)


def plan_jobs(plan):
    jobs = []
    for net, hand in itertools.product(("top", "bottom"), ("L", "R")):
        lanes = [("solo", x) for x in (-50, 0, 50)] + [("2on1", x) for x in (-50, 50)] + [("deke", -45)]
        if plan == "pilot":
            lanes = [("solo", 0), ("2on1", 50), ("deke", -45)]
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
    top = PostureHarness(state=STATE_TOP, top=True)
    _h["top"], _h["bottom"] = top, PostureHarness(state=STATE_BOTTOM, top=False, emu=top.e)


def job(args):
    attack, net, hand, x0, posture = args
    h = _h[net]
    e = h.e
    top = net == "top"
    sg = 1 if top else -1
    gl = sg * GOAL_Y
    rnd = random.Random(zlib.crc32(json.dumps(args).encode()))
    if attack == "deke":                                  # deke_run's best deke2 set-up for the hand
        dk_D, dk_lag = DEKE[hand]
        dk_in, dk_sw, dk_aim = (DR.screen_dir(DR.PAD[k], top) for k in ("UR", "UL", "L"))

    def scr(x, out):                                     # attacker's view -> screen
        return round(sg * x), round(sg * (GOAL_Y - out))

    def xy(k):
        return e.sw(rec(k)), e.sw(rec(k) + 0x14)

    def out_of(y):
        return GOAL_Y - sg * y

    res = dict(n=0, shot=0, lost=0, loose=0, none=0, goals=0.0, poked=0, release=[0.0, 0.0], frames=0.0, ddist=0.0,
               onetimer=0, react=0, moments=[])
    for p in range(MOMENTS):
        clock, settle = 590 - (p * 3) % 8, 80 + (p * 7) % 15
        h.def_spot = None if posture == "none" else scr(x0 / 2, DEF_OUT - (START_OUT - DEKE_OUT) * (attack == "deke"))
        h.mate_spot = scr(MATE_X if x0 < 0 else -MATE_X, START_OUT) if attack == "2on1" else None
        h.pin = True
        start = DEKE_OUT if attack == "deke" else START_OUT
        h.setup(*scr(x0, start), settle=settle, clock=clock)
        set_ratings(h, 20, 15)
        b, a = e.b(rec(SHOOTER) + 0x76), e.b(rec(SHOOTER) + 4)       # the hand (deke_run.py)
        e.setb(rec(SHOOTER) + 0x76, (b | 1) if hand == "L" else (b & ~1))
        e.setb(rec(SHOOTER) + 4, (a & ~8) if hand == "L" else (a | 8))
        if attack == "deke":                              # deke_run's start: drifting in toward the middle
            e.setb(rec(SHOOTER) + 0x55, DR.screen_dir(1, top))
            e.setw(rec(SHOOTER) + 0x28, round(sg * 0.5 * 4096) & 0xFFFF)
            e.setw(rec(SHOOTER) + 0x2A, round(sg * 2.1 * 4096) & 0xFFFF)
        else:
            e.setb(rec(SHOOTER) + 0x55, 0 if top else 4)
            e.setw(rec(SHOOTER) + 0x28, 0)
            e.setw(rec(SHOOTER) + 0x2A, round(sg * SPEED * 4096) & 0xFFFF)
        if attack == "2on1":
            e.setb(rec(MATE) + 0x55, 0 if top else 4)
            e.setw(rec(MATE) + 0x2A, round(sg * SPEED * 4096) & 0xFFFF)
        if posture != "none":
            e.setw(CONT2TEAM, 2)                          # pad 2 on the away team, on the defender
            e.setw(C2PLAYERNUM, DEF)
            e.setb(rec(DEF) + 0x62, e.b(rec(DEF) + 0x62) | 8)
            e.setb(rec(DEF) + 0x55, 4 if top else 0)
            e.setw(rec(DEF) + 0x2A, round(sg * SPEED * 4096) & 0xFFFF)     # skating back with the rush
        e.setl(0xD066, rnd.getrandbits(32))
        h.pin = False
        n0 = e.w(E["n"])
        mate_y0 = h.mate_spot[1] if h.mate_spot else None
        pre = None
        passed = poked = False
        bt = ct = 0                                       # pad 2: B tap frames left / cooldown; C cooldown
        bcool = ccool = 0
        pressing = posture in ("press", "presscheck")
        pass_t = c_from = None
        lost = False
        shooter = SHOOTER
        aim = 8
        swing = None
        gx0, gy0 = xy(GOALIE)
        for f in range(300):
            if attack == "deke":
                gx0, gy0 = xy(GOALIE)
            carrier = e.w(PUCKC)
            px, py = xy(PUCK)
            if carrier in range(6, 12):
                lost = True
                break
            if carrier in (SHOOTER, MATE):
                shooter = carrier
            # --- the teammate keeps skating in his lane until the pass nears him
            if attack == "2on1" and not passed:
                mx = h.mate_spot[0]
                my = mate_y0 + sg * SPEED * f
                e.setw(rec(MATE), round(mx))
                e.setw(rec(MATE) + 0x14, round(my))
                e.setw(rec(MATE) + 0x28, 0)
                e.setw(rec(MATE) + 0x2A, round(sg * SPEED * 4096) & 0xFFFF)
            # --- pad 1
            pad1, c = [], False
            if carrier == SHOOTER and not passed:
                sx, sy = xy(SHOOTER)
                o = out_of(sy)
                dfx, dfy = xy(DEF) if posture != "none" else (9999, 9999)
                blocked = (attack != "deke" and math.hypot(dfx - sx, dfy - sy) <= REACT     # in his way: react
                           and out_of(dfy) < o + 5)                # (the deke plays its move regardless)
                if attack == "2on1" and (o <= PASS_OUT or blocked and o <= 150):
                    if pass_t is None:                    # the pass across: B pressed 2 frames, released
                        pass_t = f
                    mx, my = xy(MATE)
                    pad1 = DIRPAD[direction(mx - sx, my - sy)] + (["B"] if f < pass_t + 2 else [])
                    if f >= pass_t + 2:
                        passed = True
                elif attack == "deke" and c_from is None and not blocked:
                    if swing is None and math.hypot(sx - gx0, sy - gy0) <= dk_D:
                        swing = f
                    if swing is not None and f >= swing + dk_lag:
                        c_from = f
                        aim = dk_aim
                    pad1 = DIRPAD[dk_in if swing is None else dk_sw]
                else:
                    tx, ty = scr(x0 * 0.4, 20 if attack == "slot" else 45)
                    d = direction(tx - sx, ty - sy)
                    if c_from is None and (attack == "solo" and o <= SHOOT_OUT or attack == "slot" and o <= SLOT_OUT
                                           or blocked and o <= 150):
                        c_from = f
                        aim = 6 if sg * px > 0 else 2      # the far side: screen Left / Right, top net
                        aim = aim if top else (aim + 4) % 8
                        res["react"] += blocked
                    if c_from is not None:
                        d = aim
                    pad1 = DIRPAD[d]
            elif carrier == MATE:                         # took it on his stick: shoot at once
                if c_from is None:
                    c_from = f
                    aim = 6 if sg * px > 0 else 2
                    aim = aim if top else (aim + 4) % 8
                pad1 = DIRPAD[aim]
            elif passed and carrier & 0xFF00 and c_from is None:
                mx, my = xy(MATE)
                if math.hypot(px - mx, py - my) <= 40:
                    c_from = f
            if c_from is not None and f < c_from + 3:
                c = True
            elif carrier & 0xFF00 and not passed and pass_t is None and f > 2:
                poked = True                              # knocked loose before any pass or shot
            # --- pad 2
            pad2 = []
            if posture != "none":
                dx, dy = xy(DEF)
                vx, vy = e.sw(rec(PUCK) + 0x28) / 4096, e.sw(rec(PUCK) + 0x2A) / 4096
                cx, cy = xy(shooter)
                if posture == "sitpress" and not pressing and math.hypot(cx - dx, cy - dy) <= 30:
                    pressing = True
                if pressing:
                    tx, ty = px + 6 * vx, py + 6 * vy
                    pad2 = DIRPAD[direction(tx - dx, ty - dy)]
                    if posture == "presscheck":
                        if ccool == 0 and math.hypot(cx - dx, cy - dy) <= 40:
                            pad2 = pad2 + ["C"]
                            ccool = 30
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
            e.run(1, hold=(["C"] if c else []) + pad1, hold2=pad2)
            if e.w(E["n"]) != n0:
                pre = st
                break
            breathe()
        res["n"] += 1
        res["poked"] += poked
        if pre is None:
            kind = "lost" if lost else "loose" if (e.w(PUCKC) & 0xFF00) else "none"
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
            e.unserialize(pre)
            e.setl(0xD066, rnd.getrandbits(32))
            h.park()
            e.run(1, hold=DIRPAD[aim] if shooter == SHOOTER or c_from is not None else [])
            g, _f = decide(h)
            goals += g
            breathe()
        rate = goals / SEEDS
        res["shot"] += 1
        res["goals"] += rate
        res["onetimer"] += attack == "2on1" and shooter == MATE and e.w(PUCKC) != MATE
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
    path = RUNS / run / f"posture_{plan}.jsonl"
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
