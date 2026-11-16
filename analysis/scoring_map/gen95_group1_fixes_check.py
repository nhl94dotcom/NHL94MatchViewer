"""NHL '95 (Genesis): NOSE4Web's group 1 fixes played (2026-11-16, a54ed4e: NHL '94's runaway speed, computer goalie
pull, pulled-goalie sniping and penalty shot fixes at NHL '95's places), and the C-then-B check. NHL '94's tests
(runaway_fix_test, goalie_pull_test, sniping_test, ps_table_test, ps_fixes_test) ported to NHL '95's RAM (ram95.asm
gives each NHL '94 address), from one live state per ROM (gen95_assist_check's: a Regular Game, pad 1 home, period 1
just after the opening faceoff, home attacking up), each trial seeded so the two ROMs play the same moments.

Modes (python gen95_group1_fixes_check.py MODE OUT ROM STATE [ROM STATE ...] [N]); results to OUT/<mode>_<rom>.jsonl
and a summary printed:
  pull     third period, 50 s left, the computer (Away) with the puck in its attacking half, behind by 0-3; 300 frames:
           does Away's tmgoalie ($FFC614) go negative (CPgoalie's st)
  snipe    the home shooter (pad 1) alone with the puck at spots 94-174 from the top net's aim point, C tapped, each
           spot from N seeds, Home's tmgoalie ($FFC2AE) as it is or $FF00: the share of a spot's shots leaving at the
           most common speeds (an exact shot leaves the same way every time)
  runaway  takeover (pass, B again: control to the receiver, who stays clear of the puck), boards (a person's carrier
           checked into the boards by pad 2's burst, until he is up), whiff (pass, C at once: the receiver's one-timer
           swings long before the puck; then he is pad 1's), onetimer (a real one-timer: the shot's speed, the same on
           both ROMs?). After each: deceleration-off (pflags bit 0) on him, then a glide (the pad held away from the
           puck 20 frames, released: speed then and 30 frames later), and from the same moment two bursts (C) and his
           speed 0.6 s after the last.
  pstable  breakaways (the computer's carrier across the blue line, a chaser close behind: the computer's, or pad 2
           pressing C, B or holding B); each foul called, and the penalty shot it gave (the frame played again with
           "pending", BA_PS_flags bit 3, set, so PenShotChk leaves the foul's own code)
  psfix    a penalty shot awarded as in pstable, then: whistle (an out-of-play PenBuf entry 10-60 frames into the live
           attempt: a retake from centre, or a faceoff) and ghost (the puck given pfnc at the award whistle: still on
           as the attempt goes live? the puck out of the rink?)
  cb       a person's burst check (pad 1, C) on the computer's carrier, the same moment played three ways: kept
           (pad 1's at contact), switched (pfjoycon moved to a teammate 3 frames before contact, as B does), pressB
           (B pressed 3 frames before contact): the carrier knocked down?"""
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from emu import Emu
import lowload

BASE, SZ = 0xAC62, 0x80
PUCKC, C1P, C2P, CONT1, CONT2 = 0xB3C2, 0xBF44, 0xBF46, 0xBF4C, 0xBF4E
GSP, CLOCK, GMODE, SEED, OPTPEN = 0xC020, 0xC022, 0xBEF0, 0xCC6A, 0xCC5A
HOME, AWAY = 0xC288, 0xC5EE
HM_GOALIE, AW_GOALIE = HOME + 0x26, AWAY + 0x26
BA_PS, BA_SKTR, PSPEN, PENBUF = 0xBEF8, 0xD00A, 0xD014, 0xBFCE
UNDERWAY, PENDING = 0x0400, 0x0800
POS, PFL, PFL3 = 0x35, 0x62, 0x64
DIRS = ["UP", ["UP", "RIGHT"], "RIGHT", ["DOWN", "RIGHT"], "DOWN", ["DOWN", "LEFT"], "LEFT", ["UP", "LEFT"]]
NAMES = {0x12: "roughing (injury)", 0x14: "no text (injury)", 0x16: "charging", 0x18: "slashing", 0x1A: "roughing",
         0x1C: "cross check", 0x1E: "hooking", 0x20: "tripping", 0x22: "interference", 0x24: "holding",
         0x2E: "hooking PS", 0x30: "tripping PS", 0x34: "interference PS", 0x36: "roughing PS", 0x38: "charging PS",
         0x3A: "cross check PS", 0x3C: "slashing PS"}
RIGHT = {0x16: 0x38, 0x18: 0x3C, 0x1A: 0x36, 0x1C: 0x3A, 0x1E: 0x2E, 0x20: 0x30}


def rec(k):
    return BASE + k * SZ


def sw(v):
    return v - 0x10000 if v >= 0x8000 else v


def pad(d):
    v = DIRS[d % 8]
    return list(v) if isinstance(v, list) else [v]


def dir_to(dx, dy):
    return round(math.degrees(math.atan2(dx, dy)) / 45) % 8


def pos(e, k):
    return sw(e.w(rec(k))), sw(e.w(rec(k) + 0x14))


def speed(e, k):
    return math.hypot(sw(e.w(rec(k) + 0x28)), sw(e.w(rec(k) + 0x2A)))


def put(e, k, x, y, vx=0.0, vy=0.0, face=0):
    r = rec(k)
    e.setw(r, round(x) & 0xFFFF); e.setw(r + 2, 0)
    e.setw(r + 0x14, round(y) & 0xFFFF); e.setw(r + 0x16, 0); e.setw(r + 0x18, 0)
    e.setl(r + 0x1C, (round(x) & 0xFFFF) << 16); e.setl(r + 0x20, (round(y) & 0xFFFF) << 16)
    e.setw(r + 0x28, round(vx * 4096) & 0xFFFF); e.setw(r + 0x2A, round(vy * 4096) & 0xFFFF); e.setw(r + 0x2C, 0)
    e.setw(r + 0x54, face % 8)


def fresh(e, k):
    """A placed player's leftovers cleared: impacts, the animation lock, flags 3; a new assignment."""
    r = rec(k)
    for a in range(0x2E, 0x34):
        e.setb(r + a, 0)
    e.setw(r + 0x5E, 0)
    e.setb(r + PFL, (e.b(r + PFL) & 0xC8) | 0x02)
    e.setb(r + PFL3, 0)


def control(e, pad_no, k, team_side):
    """Pad 1 or 2 on record k (team_side 1 home / 2 away); the side's other skaters the computer's."""
    e.setw(CONT1 if pad_no == 1 else CONT2, team_side)
    rng = range(6) if team_side == 1 else range(6, 12)
    for j in rng:
        e.setb(rec(j) + PFL, e.b(rec(j) + PFL) & ~8)
    if k is not None:
        e.setb(rec(k) + PFL, e.b(rec(k) + PFL) | 8)
        e.setw(C1P if pad_no == 1 else C2P, k)


def penbuf(e):
    out = []
    for i in range(8):
        v = e.w(PENBUF + 2 * i)
        if v == 0:
            break
        out.append(v)
    return out


def stopped(e):
    return bool(e.w(GMODE) & 0x0100)


# ---------------------------------------------------------------- pull
def pull(e, base, n):
    rows = []
    for s in range(n):
        for deficit in range(4):
            e.unserialize(base)
            e.setl(SEED, random.Random(s * 31 + 7).getrandbits(32))
            e.setw(GSP, 2); e.setw(CLOCK, 50)
            e.setw(HOME + 0x0C, 3 + deficit); e.setw(AWAY + 0x0C, 3)
            e.setw(CONT2, 0)
            k = next(k for k in range(6, 12) if e.b(rec(k) + POS) == 4)
            up = bool(e.b(rec(k) + PFL) & 0x80)
            y = 60 if up else -60
            put(e, k, 0, y); put(e, 14, 0, y)
            e.setw(PUCKC, k)
            r = dict(deficit=deficit, seed=s, pulled=False)
            for f in range(300):
                e.run(1)
                if e.w(AW_GOALIE) & 0x8000:
                    r.update(pulled=True, frame=f)
                    break
            rows.append(r)
            lowload.breathe()
    return rows


def pull_report(rows):
    by = defaultdict(list)
    for r in rows:
        by[r["deficit"]].append(r["pulled"])
    return ", ".join(f"{d} down: pulled {sum(v)} of {len(v)}" for d, v in sorted(by.items()))


# ---------------------------------------------------------------- snipe
SHOOTER, GOALIE_AW = 2, 11
SPOTS = [(x, y) for x in (-40, 0, 40) for y in (93, 133, 173)]   # 94-174 from the top net's aim point (0, 267)


def park(e, keep=()):
    for k in range(12):
        if k == GOALIE_AW or k in keep:
            continue
        e.setw(rec(k), (-100 + 18 * k) & 0xFFFF)
        e.setw(rec(k) + 0x14, -230 & 0xFFFF)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(k) + off, 0)


def release(e, base, x, y, seed, pulled):
    e.unserialize(base)
    e.setw(CLOCK, 250)
    control(e, 1, SHOOTER, 1)
    for _ in range(60):
        e.setw(rec(SHOOTER), x & 0xFFFF); e.setw(rec(SHOOTER) + 0x14, y & 0xFFFF)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(SHOOTER) + off, 0)
        park(e, (SHOOTER,))
        e.setw(PUCKC, SHOOTER)
        if pulled:
            e.setw(HM_GOALIE, 0xFF00)
        e.run(1)
    if e.w(PUCKC) != SHOOTER:
        return None
    e.setl(SEED, seed)
    for f in range(60):
        park(e, (SHOOTER,))
        if pulled:
            e.setw(HM_GOALIE, 0xFF00)
        e.run(1, hold=["C"] if f < 3 else [])
        if e.w(PUCKC) >= 0x8000:
            return sw(e.w(rec(14) + 0x28)), sw(e.w(rec(14) + 0x2A)), sw(e.w(rec(14) + 0x2C))
    return None


def snipe(e, base, n):
    rows = []
    for pulled in (False, True):
        for x, y in SPOTS:
            for s in range(n):
                v = release(e, base, x, y, random.Random(f"{x},{y},{s}").getrandbits(32), pulled)
                rows.append(dict(pulled=pulled, x=x, y=y, s=s, v=v))
            lowload.breathe()
    return rows


def snipe_report(rows):
    out = []
    for pulled in (False, True):
        exact = total = 0
        for x, y in SPOTS:
            vs = [tuple(r["v"]) for r in rows if r["pulled"] == pulled and (r["x"], r["y"]) == (x, y) and r["v"]]
            if vs:
                exact += Counter(vs).most_common(1)[0][1]; total += len(vs)
        out.append(f"own goalie {'pulled' if pulled else 'in'}: exact {exact} of {total} ({exact / max(1, total):.0%})")
    return "; ".join(out)


# ---------------------------------------------------------------- runaway
A, B, C, D = 2, 3, 1, 7
SPA_BURST2, SPA_CHECKS, SPA_FALLS = 0x11AE, (0xDAC, 0xDDE, 0x2530, 0x254A), (0xFAA, 0x109C)


class Play:
    """gen95_assist_check's plays: the named skaters at spots, everyone else parked (the away goalie stays)."""
    def __init__(self, e, base, spots, seed):
        self.e, self.spots = e, dict(spots)
        e.unserialize(base)
        e.setw(CLOCK, 250)
        e.setl(SEED, seed)
        for _ in range(10):
            self.frame()

    def frame(self, held=(), hold=None, held2=()):
        e = self.e
        park(e, tuple(self.spots))
        for k in (self.spots if hold is None else hold):
            x, y = self.spots[k]
            e.setw(rec(k), x & 0xFFFF); e.setw(rec(k) + 0x14, y & 0xFFFF)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(rec(k) + off, 0)
        e.run(1, hold=list(held), hold2=list(held2))

    def holder(self):
        return self.e.b(rec(14) + 0x61) if self.e.b(rec(14) + 0x60) == 0 else None

    def give(self, k):
        """The puck laid at k's stick until he has it."""
        e = self.e
        x, y = self.spots[k]
        for f in range(40):
            if f % 10 == 0 and self.holder() != k:
                put(e, 14, x, y + 10, 0, -0.3)
                e.setb(rec(14) + 0x60, 0xFF); e.setw(rec(14) + 0x5E, 0); e.setw(rec(k) + 0x5E, 0)
            self.frame()
            if self.holder() == k:
                for _ in range(8):
                    self.frame()
                return True
        return False


def flag(e, k):
    return e.b(rec(k) + PFL) & 1


def away_dir(e, k):
    kx, ky = pos(e, k)
    px, py = pos(e, 14)
    return dir_to(kx - px, ky - py)


def after(e, k, p):
    """From now: how long deceleration-off stays on with no pad (to 120 frames); from the same moment a glide (the pad
    held away 60 frames, released: speed then and 30 frames later); and again two bursts (C, 0.5 s apart)."""
    st = e.serialize()
    res = dict(flag=flag(e, k))
    touched = False
    on = 0
    for f in range(120):
        if not flag(e, k):
            break
        p.frame(hold=())
        on += 1
    res["flag_frames"] = on
    e.unserialize(st)
    for f in range(90):
        p.frame(held=pad(away_dir(e, k)) if f < 60 else [], hold=())
        touched = touched or e.w(PUCKC) == k
        if f == 59:
            res["at_release"] = round(speed(e, k))
    res["glide30"] = round(speed(e, k))
    e.unserialize(st)
    peak = late = 0
    for f in range(100):
        p.frame(held=pad(away_dir(e, k)) + (["C"] if f in (2, 3, 32, 33) else []), hold=())
        touched = touched or e.w(PUCKC) == k
        peak = max(peak, speed(e, k))
        if f >= 70:
            late = max(late, speed(e, k))
    res.update(peak=round(peak), late=round(late), touched=touched)
    return res


def pass_and(e, p, passer, receiver, extra):
    """passer (pad 1's, with the puck) passes up to receiver (B); extra(f, release) then gives the presses ("done"
    ends). The receiver is held at his spot until the release. Returns the release frame or None."""
    rel = None
    for f in range(120):
        if rel is None:
            held = ["UP"] + (["B"] if 2 <= f < 5 else [])
        else:
            held = extra(f, rel)
            if held == "done":
                return rel
        p.frame(held=held, hold=[] if rel is not None else [k for k in p.spots if k != passer])
        if rel is None and f >= 2 and p.holder() != passer:
            rel = f
    return rel


def takeover(e, base, seed, xs):
    p = Play(e, base, {A: (xs, 0), B: (xs, 110), D: (110, -220)}, seed)
    control(e, 1, A, 1)
    if not p.give(A):
        return dict(res="no pickup")
    st = {"sw": None}

    def extra(f, rel):
        if st["sw"] is None:
            if e.w(C1P) == B and e.b(rec(B) + PFL) & 8:
                st["sw"] = f
            return ["B"] if rel + 2 <= f < rel + 4 else ([] if f < rel + 14 else "done")
        return "done"
    rel = pass_and(e, p, A, B, extra)
    if rel is None:
        return dict(res="no pass")
    if st["sw"] is None:
        return dict(res="no switch")
    for _ in range(4):
        p.frame(held=pad(away_dir(e, B)), hold=())
    r = after(e, B, p)
    r["res"] = "touched" if r["touched"] else "ok"
    return r


def boards(e, base, seed, xs):
    """A person's carrier (A) a little off the left boards, pad 2's skater (D) 70-110 away skating at him, C pressed
    once within 22-38: a fall into the boards sets deceleration-off with the fall flag (collide95 .22)."""
    rnd = random.Random(seed)
    x0, y0 = -rnd.uniform(126, 140), rnd.uniform(-60, 60)
    gap, trig = rnd.uniform(70, 110), rnd.choice((22, 30, 38))
    p = Play(e, base, {A: (round(x0), round(y0)), D: (round(x0 + gap), round(y0 + rnd.uniform(-10, 10))),
                       B: (60, -150)}, seed)
    control(e, 1, A, 1)
    if not p.give(A):
        return dict(res="no pickup")
    control(e, 2, D, 2)
    fell = up = c = None
    plain = False
    for f in range(400):
        ax, ay = pos(e, A)
        kx, ky = pos(e, D)
        if c is None and math.hypot(ax - kx, ay - ky) < trig:
            c = f
        p.frame(held2=(["C"] if c is not None and f < c + 3 else []) + (pad(dir_to(ax - kx, ay - ky)) if fell is None else []),
                hold=[B] + ([A] if c is None else []))
        plain = plain or e.w(rec(A) + 0x58) in SPA_FALLS
        if fell is None and e.b(rec(A) + PFL3) & 0x20:
            fell = f
            res_flag = flag(e, A)
        if fell is not None and not e.b(rec(A) + PFL3) & 0x20:
            up = f
            break
        if c is None and f > 150:
            return dict(res="never close")
    if fell is None:
        return dict(res="plain fall" if plain else "no fall")
    if not res_flag:
        return dict(res="boards fall, flag off")
    if up is None:
        return dict(res="not up")
    control(e, 1, A, 1)
    r = after(e, A, p)
    r["res"] = "touched" if r["touched"] else "ok"
    r["fall_frames"] = up - fell
    return r


def whiff(e, base, seed, xs, real=False, delay=1):
    p = Play(e, base, {A: (xs, 110), C: (xs, 160), D: (110, -220)}, seed)
    control(e, 1, A, 1)
    if not p.give(A):
        return dict(res="no pickup")
    st = {"c": None, "ot": set()}

    def extra(f, rel):
        st["ot"].add(e.w(0xBB72))
        if not real:
            return ["C"] if rel + delay <= f < rel + delay + 2 else ([] if f < rel + 40 else "done")
        mx, my = pos(e, C)
        px, py = pos(e, 14)
        if st["c"] is None and math.hypot(mx - px, my - py) < 40:
            st["c"] = f
        if st["c"] is not None and f < st["c"] + 3:
            return ["C"]
        if st["c"] is not None and f > st["c"] + 12:
            return "done"
        return [] if f < rel + 80 else "done"
    rel = pass_and(e, p, A, C, extra)
    if rel is None:
        return dict(res="no pass")
    r = dict(onetimer=C in st["ot"], shooter_flag=flag(e, C))
    if real:
        r.update(res="ok" if st["c"] is not None else "no swing", vx=sw(e.w(rec(14) + 0x28)),
                 vy=sw(e.w(rec(14) + 0x2A)), vz=sw(e.w(rec(14) + 0x2C)))
        return r
    control(e, 1, C, 1)
    r.update(after(e, C, p))
    r["res"] = "touched" if r["touched"] else "ok"
    return r


RUNAWAY = dict(takeover=takeover, boards=boards, whiff=whiff, whiff4=lambda *a: whiff(*a, delay=4),
               whiff8=lambda *a: whiff(*a, delay=8), onetimer=lambda *a: whiff(*a, real=True))


def runaway(e, base, n):
    rows = []
    for i in range(n):
        xs = (-60, -30, 0, 30, 60)[i % 5]
        for case, fn in RUNAWAY.items():
            r = fn(e, base, random.Random(900 + i).getrandbits(32), xs)
            r.update(i=i, case=case)
            rows.append(r)
        lowload.breathe()
    return rows


def runaway_report(rows):
    out = []
    for case in RUNAWAY:
        rs = [r for r in rows if r["case"] == case]
        ok = [r for r in rs if r["res"] == "ok"]
        s = f"\n    {case}: {len(rs)} trials {dict(Counter(r['res'] for r in rs))}"
        if ok and "flag" in ok[0]:
            med = lambda key: sorted(r[key] for r in ok)[len(ok) // 2]  # noqa: E731
            s += (f"; flag on {sum(r['flag'] for r in ok)} of {len(ok)}, frames it stays on (no pad) median {med('flag_frames')}"
                  f" max {max(r['flag_frames'] for r in ok)}; glide: speed at release median {med('at_release')},"
                  f" 30 frames later median {med('glide30')} (max {max(r['glide30'] for r in ok)}); bursts: peak median"
                  f" {med('peak')}, 0.6 s after the last median {med('late')} (max {max(r['late'] for r in ok)})")
        if ok and "vx" in ok[0]:
            s += f"; one-timers {sum(r['onetimer'] for r in ok)}, shooter's flag on after {sum(r['shooter_flag'] for r in ok)}"
        out.append(s)
    return "".join(out)


# ---------------------------------------------------------------- penalty shots
MODES = ("cpu", "C", "B", "Bhold")


def ps_setup(e, base, rnd):
    e.unserialize(base)
    e.setw(CLOCK, 250)
    e.setl(SEED, rnd.getrandbits(32))
    e.setw(OPTPEN, 1)
    e.setw(PENBUF, 0)
    e.setw(BA_PS, 0)
    roles = {k: e.b(rec(k) + POS) for k in range(12)}
    carrier = next(k for k in range(6, 12) if roles[k] == 4)         # the computer's (Away) carrier
    up = 1 if e.b(rec(carrier) + PFL) & 0x80 else -1
    face = 0 if up > 0 else 4
    x0, y0 = rnd.uniform(-60, 60), up * rnd.uniform(55, 82)
    v = rnd.uniform(1.0, 2.0)
    put(e, carrier, x0, y0, 0, up * v, face)
    them = [k for k in range(6) if roles[k] not in (0, 0xFF)]
    chaser = rnd.choice(them)
    put(e, chaser, x0 + rnd.uniform(-10, 10), y0 - up * rnd.uniform(8, 28), 0, up * (v + rnd.uniform(0.3, 1.2)), face)
    for k in them:
        if k != chaser:
            put(e, k, rnd.uniform(-90, 90), y0 - up * rnd.uniform(70, 160), 0, up * 1.0, face)
    for k in range(6, 12):
        if roles[k] not in (0, 0xFF, 4):
            put(e, k, rnd.uniform(-90, 90), y0 - up * rnd.uniform(40, 140), 0, up * 1.0, face)
    for k in range(12):
        if roles[k] <= 5:
            fresh(e, k)
    control(e, 2, None, 0)
    mode = rnd.choice(MODES)
    control(e, 1, chaser if mode != "cpu" else None, 1 if mode != "cpu" else 0)
    put(e, 14, x0, y0 + up * 4)
    e.setw(PUCKC, carrier)
    return carrier, chaser, up, mode


def ps_holds(e, carrier, chaser, mode, f):
    if mode == "cpu":
        return []
    cx, cy = pos(e, carrier)
    kx, ky = pos(e, chaser)
    d = pad(dir_to(cx - kx, cy - ky))
    if mode == "C":
        return d + (["C"] if f % 12 in (0, 1) else [])
    if mode == "B":
        return d + (["B"] if f % 10 in (0, 1) else [])
    return d + ["B"]


def ps_trial(e, base, rnd):
    carrier, chaser, up, mode = ps_setup(e, base, rnd)
    broke = False
    before = penbuf(e)
    hist = []
    for f in range(150):
        h1 = ps_holds(e, carrier, chaser, mode, f)
        hist = (hist + [(e.serialize(), h1, e.w(BA_PS))])[-4:]
        e.run(1, hold=h1)
        broke = broke or bool(e.b(rec(carrier) + PFL3) & 2)
        now = penbuf(e)
        if now != before:
            new = [v for v in now if v not in before]
            if not new:
                before = now
                continue
            code, who = new[0] >> 8, new[0] & 0xFF
            if code < 0x12:
                return dict(res="whistle %02x" % code, mode=mode, brk=broke)
            out = dict(res="foul", mode=mode, frame=f, code=code, who=who, carrier=carrier, chaser=chaser, brk=broke,
                       ps_flags=e.w(BA_PS), shooter=e.w(BA_SKTR), pspenalty=e.w(PSPEN), plain=code, plain_who=who)
            if code >= 0x2E:
                start = next((j for j in range(len(hist)) if not hist[j][2] & PENDING and
                              (hist[j + 1][2] if j + 1 < len(hist) else e.w(BA_PS)) & PENDING), None)
                if start is None:
                    out.update(plain=None, plain_who=None, note="pending earlier")
                    return out
                real = e.serialize()
                e.unserialize(hist[start][0])
                e.setw(BA_PS, e.w(BA_PS) | PENDING)
                again = []
                for _, a1, _ in hist[start:] + [(None, h1, None)] * 2:
                    e.run(1, hold=a1)
                    again = [v for v in penbuf(e) if v not in before]
                    if again:
                        break
                out["plain"] = again[0] >> 8 if again else None
                out["plain_who"] = again[0] & 0xFF if again else None
                e.unserialize(real)
            return out
        if stopped(e):
            return dict(res="stoppage", mode=mode, brk=broke)
    return dict(res="none", mode=mode, brk=broke)


def pstable(e, base, n):
    rows = []
    for i in range(n):
        r = ps_trial(e, base, random.Random(1000 + i))
        r["i"] = i
        rows.append(r)
        if i % 20 == 19:
            lowload.breathe()
    return rows


def pstable_report(rows):
    s = f"{len(rows)} trials, {dict(Counter(r['res'] for r in rows))}; breakaway flag seen {sum(r['brk'] for r in rows)}"
    pairs = Counter((r["plain"], r["code"], r["who"] == r["plain_who"],
                     r["shooter"] == r["carrier"] if r["code"] >= 0x2E else None) for r in rows if r["res"] == "foul")
    for (plain, code, same, shooter), c in sorted(pairs.items(), key=lambda t: (t[0][0] or 0, t[0][1])):
        ok = "" if code < 0x2E else (" right" if RIGHT.get(plain) == code else " WRONG")
        s += (f"\n    {NAMES.get(plain, plain)!s:18} -> {NAMES.get(code, hex(code)):18} {c:4}{ok}"
              f"{'' if same else ' (other player)'}{'' if shooter in (None, True) else ' (shooter not the carrier)'}")
    return s


def run_until(e, test, frames):
    for f in range(frames):
        e.run(1)
        if test():
            return f
    return None


def award(e, base, rnd):
    for _ in range(60):
        r = ps_trial(e, base, rnd)
        if r["res"] == "foul" and r["code"] >= 0x2E:
            return r
    return None


def ps_whistle(e, base, rnd):
    r = award(e, base, rnd)
    if r is None:
        return dict(res="no award")
    if run_until(e, lambda: e.w(BA_PS) & UNDERWAY, 3000) is None:
        return dict(res="no attempt")
    shooter = e.w(BA_SKTR)
    if run_until(e, lambda: e.w(PUCKC) == shooter, 1500) is None:
        return dict(res="no carry")
    for _ in range(rnd.randint(10, 60)):
        e.run(1)
        if not e.w(BA_PS) & UNDERWAY or e.w(GMODE) & 0x0400 or penbuf(e):
            return dict(res="ended first", code=r["code"])
    e.setw(PENBUF, 0x06 << 8 | shooter)
    e.setw(PENBUF + 2, 0)
    if run_until(e, lambda: e.w(GMODE) & 0x0400, 30) is None:
        return dict(res="whistle not called")
    if run_until(e, lambda: not e.w(GMODE) & 0x0400, 3000) is None:
        return dict(res="stoppage never ends")
    for f in range(90):
        e.run(1)
        if not e.w(BA_PS) & UNDERWAY:
            return dict(res="faceoff", code=r["code"], frames=f)
        if pos(e, 14) == (0, 0):
            return dict(res="retake", code=r["code"], frames=f)
    return dict(res="neither", code=r["code"], flags=e.w(BA_PS), gmode=e.w(GMODE))


def ps_ghost(e, base, rnd):
    r = award(e, base, rnd)
    if r is None:
        return dict(res="no award")
    pf = rec(14) + PFL
    e.setb(pf, e.b(pf) | 4)
    if run_until(e, lambda: e.w(BA_PS) & UNDERWAY, 3000) is None:
        return dict(res="no attempt")
    shooter = e.w(BA_SKTR)
    if run_until(e, lambda: e.w(PUCKC) == shooter, 1500) is None:
        return dict(res="no carry")
    nc_start = bool(e.b(pf) & 4)
    out, nc = False, 0
    for f in range(1500):
        e.run(1)
        nc += bool(e.b(pf) & 4)
        x, y = pos(e, 14)
        out = out or abs(x) > 165 or abs(y) > 300          # NHL 95's boards: x about 152
        if not e.w(BA_PS) & UNDERWAY:
            break
    return dict(res="ok", code=r["code"], nc_start=nc_start, nc_frames=nc, out_of_rink=out, frames=f)


def psfix(e, base, n):
    rows = []
    for i in range(n):
        for case, fn in (("whistle", ps_whistle), ("ghost", ps_ghost)):
            r = fn(e, base, random.Random(5000 + 97 * i))
            r.update(i=i, case=case)
            rows.append(r)
            lowload.breathe()
    return rows


def psfix_report(rows):
    w = [r for r in rows if r["case"] == "whistle"]
    g = [r for r in rows if r["case"] == "ghost" and r["res"] == "ok"]
    return (f"whistle during the attempt: {dict(Counter(r['res'] for r in w))}; ghost: {len(g)} attempts, no-collision"
            f" on as the attempt goes live {sum(r['nc_start'] for r in g)}, the puck out of the rink"
            f" {sum(r['out_of_rink'] for r in g)}; {dict(Counter(r['res'] for r in rows if r['case'] == 'ghost'))}")


# ---------------------------------------------------------------- C-then-B
def cb_trial(e, base, rnd, how):
    """Home's skater 2 on pad 1 skates at the computer's carrier from 70-110 away and presses C within 22-38; then
    kept (his at contact), switched (pfjoycon moved to skater 4 once he is in SPAburst2 within 34, as B does) or
    pressB (B pressed then). The contact: his check animation (CCStart's SetSPA); down: the carrier falls."""
    e.unserialize(base)
    e.setw(CLOCK, 250)
    e.setl(SEED, rnd.getrandbits(32))
    e.setw(OPTPEN, 0)
    roles = {k: e.b(rec(k) + POS) for k in range(12)}
    carrier = next(k for k in range(6, 12) if roles[k] == 4)
    checker, mate = 2, 4
    x0, y0 = rnd.uniform(-60, 60), rnd.uniform(-80, 80)
    ang = rnd.uniform(0, 2 * math.pi)
    dist, trig = rnd.uniform(70, 110), rnd.choice((22, 30, 38))
    put(e, carrier, x0, y0)
    put(e, checker, x0 + dist * math.sin(ang), y0 + dist * math.cos(ang))
    put(e, mate, -100, -200)
    for k in range(12):
        if roles[k] not in (0, 0xFF) and k not in (carrier, checker, mate):
            put(e, k, (-100 + 18 * k), 230 if k < 6 else -230)
        if roles[k] <= 5:
            fresh(e, k)
    put(e, 14, x0, y0 + 4)
    e.setw(PUCKC, carrier)
    control(e, 2, None, 0)
    control(e, 1, checker, 1)
    c = contact = person = None
    fell = False
    for f in range(200):
        cx, cy = pos(e, carrier)
        kx, ky = pos(e, checker)
        d = math.hypot(cx - kx, cy - ky)
        hold = []
        if contact is None:
            if c is None and d < trig:
                c = f
            hold = pad(dir_to(cx - kx, cy - ky)) + (["C"] if c is not None and f < c + 3 else [])
            near = d < 34 and e.w(rec(checker) + 0x58) == SPA_BURST2 and e.b(rec(checker) + PFL) & 8
            if near and how == "switched":
                e.setb(rec(checker) + PFL, e.b(rec(checker) + PFL) & ~8)
                e.setb(rec(mate) + PFL, e.b(rec(mate) + PFL) | 8)
                e.setw(C1P, mate)
            if near and how == "pressB":
                hold = ["B"]
        e.run(1, hold=hold)
        if contact is None and e.w(rec(checker) + 0x58) in SPA_CHECKS:
            contact, person = f, bool(e.b(rec(checker) + PFL) & 8)
        if contact is not None and (e.b(rec(carrier) + PFL3) & 0x20 or e.w(rec(carrier) + 0x58) in SPA_FALLS):
            fell = True
        if contact is not None and f > contact + 30:
            break
    return dict(how=how, contact=contact, person_at_contact=person, fell=fell)


def cb(e, base, n):
    rows = []
    for i in range(n):
        for how in ("kept", "switched", "pressB"):
            r = cb_trial(e, base, random.Random(7000 + i), how)
            r["i"] = i
            rows.append(r)
        if i % 10 == 9:
            lowload.breathe()
    return rows


def cb_report(rows):
    out = []
    for how in ("kept", "switched", "pressB"):
        rs = [r for r in rows if r["how"] == how and r["contact"] is not None]
        pers = [r for r in rs if r["person_at_contact"]]
        cpu = [r for r in rs if not r["person_at_contact"]]
        out.append(f"\n    {how}: {len(rs)} contacts; a person's at contact {len(pers)}, knocked down {sum(r['fell'] for r in pers)}"
                   f"; the computer's at contact {len(cpu)}, knocked down {sum(r['fell'] for r in cpu)}")
    both = defaultdict(dict)
    for r in rows:
        if r["contact"] is not None:
            both[r["i"]][r["how"]] = r
    pair = [(v["kept"], v["switched"]) for v in both.values() if "kept" in v and "switched" in v
            and v["kept"]["person_at_contact"] and not v["switched"]["person_at_contact"]]
    out.append(f"\n    paired (the same moment, kept a person's / switched to the computer): {len(pair)}; down kept "
               f"{sum(a['fell'] for a, _ in pair)}, switched {sum(b['fell'] for _, b in pair)}")
    return "".join(out)


MODES_RUN = dict(pull=(pull, pull_report, 40), snipe=(snipe, snipe_report, 30), runaway=(runaway, runaway_report, 40),
                 pstable=(pstable, pstable_report, 2000), psfix=(psfix, psfix_report, 44), cb=(cb, cb_report, 150))


def main():
    mode, out = sys.argv[1], Path(sys.argv[2])
    args = sys.argv[3:]
    n = None
    if len(args) % 2:
        n = int(args.pop())
    fn, rep, dflt = MODES_RUN[mode]
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    for rom, state in zip(args[::2], args[1::2]):
        e = Emu(rom)
        e.run(1500)                                    # powered on first: states leave out save RAM
        base = Path(state).read_bytes()
        rows = fn(e, base, n or dflt)
        name = Path(rom).stem
        with open(out / f"{mode}_{name}.jsonl", "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        print(f"== {name} {mode}: {rep(rows)}", flush=True)
        del e


if __name__ == "__main__":
    main()
