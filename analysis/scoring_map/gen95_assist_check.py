"""NHL '95 (Genesis): NOSE4Web's three assist fixes played (2026-11-16; NHL '94's: gen_assist_repro.py, whose plays
these are, ported to NHL '95's RAM). NHL '95's a2touchpuck is NHL '94's line for line (the touch list at team struct
+$18 / +$1A / +$1C, tmflast bit 3 of +$30); its records, puck and pads lie $3E8 lower (SortCords $FFAC62, puckc
$FFB3C2), the home team struct at $FFC288 (NHL '94 $C6CE), the away one $366 after it.

From a live state per ROM (STATE: a Regular Game, pad 1 on home record 1, period 1 a moment after the opening faceoff,
home attacking up), the game's own code doing every pickup, pass, one-timer and goal; only a loose puck is placed by
hand, everyone else parked:
- regain (the bug): home A picks the puck up; away D picks it up; A picks it back up; A passes to B; the puck on
  into the empty net (B's goal). Retail: the assist list is wiped when D touches it, so A's pass earns nothing.
- regain-control: the same with teammate C winning it back.
- giveandgo: A to C, C to B, B back to C, C's goal: assists B and A (retail drops A: C twice in the list).
- onetimer: A picks it up, passes to C; C passes to B with C pressed while it travels: B's one-timer: assists C, A;
  again with the receiver made the last touch as the swing starts (his stick touched the pass first; NHL '94's
  case): retail's onetimershot pushes him again (B, B, C) and no assist is credited.
Goals by roster place at team struct +$B6, assists +$D0, shots +$EA (read from these goals).
At the goal, every byte of both team structs that went up (goals and assists by roster place, totals).

python gen95_assist_check.py OUT ROM STATE [ROM STATE ...]"""
import json
import sys
from pathlib import Path

from emu import Emu

BASE, SZ = 0xAC62, 0x80
TEAM, TMSIZE = 0xC288, 0x366
A, B, C, D, AWAYG = 2, 3, 1, 7, 11


def rec(k):
    return BASE + k * SZ


PUCK = rec(14)


def touch(e):
    sw = lambda v: v - 0x10000 if v >= 0x8000 else v  # noqa: E731
    return [sw(e.w(TEAM + 0x18)), sw(e.w(TEAM + 0x1A)), sw(e.w(TEAM + 0x1C))], int(bool(e.b(TEAM + 0x30) & 8))


def struct_bytes(e):
    return [e.b(TEAM + i) for i in range(2 * TMSIZE)]


class Play:
    def __init__(self, e, base, spots, log):
        self.e, self.base, self.spots, self.log = e, base, dict(spots), log
        self.keep = set(spots)
        self.park_y = -230
        e.unserialize(base)
        self.pnum = {k: e.b(rec(k) + 0x66) for k in (A, B, C, D)}
        log.append(("roster places", {n: self.pnum[k] for n, k in (("A", A), ("B", B), ("C", C), ("D", D))}))
        for _ in range(20):
            self.frame()

    def park(self):
        e = self.e
        for k in range(12):
            if k in self.keep or k == AWAYG:
                continue
            e.setw(rec(k), -100 + 18 * k)
            e.setw(rec(k) + 0x14, self.park_y)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(rec(k) + off, 0)

    def hold(self, ks):
        e = self.e
        for k in ks:
            x, y = self.spots[k]
            e.setw(rec(k), x)
            e.setw(rec(k) + 0x14, y)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(rec(k) + off, 0)
            e.setb(rec(k) + 0x55, 0)

    def frame(self, held=(), hold=None):
        self.park()
        self.hold(self.keep if hold is None else hold)
        self.e.run(1, hold=list(held))

    def holder(self):
        e = self.e
        return e.b(PUCK + 0x61) if e.b(PUCK + 0x60) == 0 else None

    def pick_up(self, k, label):
        e = self.e
        st = e.serialize()
        x, y = self.spots[k]
        for dx, dy in ((0, 20), (10, 18), (-10, 18), (16, 8), (-16, 8), (0, -20), (18, 0), (-18, 0), (12, -14), (-12, -14)):
            e.unserialize(st)
            e.setw(PUCK, x + dx)
            e.setw(PUCK + 0x14, y + dy)
            e.setw(PUCK + 0x18, 0)
            e.setw(PUCK + 0x28, (-dx * 40) & 0xFFFF)
            e.setw(PUCK + 0x2A, (-dy * 40) & 0xFFFF)
            e.setw(PUCK + 0x2C, 0)
            e.setb(PUCK + 0x60, 0xFF)
            e.setw(PUCK + 0x5E, 0)
            for o in self.keep:
                e.setw(rec(o) + 0x5E, 0 if o == k else 30)
            for f in range(40):
                self.frame()
                if self.holder() == k:
                    for _ in range(10):
                        self.frame()
                    self.log.append((label, "picked up") + touch(e))
                    return True
                if self.holder() is not None:
                    break
        e.unserialize(st)
        self.log.append((label, "NOT picked up") + touch(e))
        return False

    def pass_to(self, passer, receiver, label, one_timer=False, maxf=90, way="UP"):
        e = self.e
        rp = self.pnum[receiver]
        for f in range(maxf):
            held = [way] + (["B"] if 2 <= f < 5 else []) + (["C"] if one_timer and 8 <= f < 11 else [])
            self.frame(held, hold=[k for k in self.keep if k not in (passer, receiver)] + ([receiver] if f < 2 else []))
            if touch(e)[0][0] == rp:
                break
        held_by = None
        if touch(e)[0][0] == rp:
            for g in range(60):
                self.frame(hold=[k for k in self.keep if k != receiver])
                if self.holder() == receiver:
                    held_by = g
                    break
        self.log.append((label, "receiver's touch after %d frames, %s" % (
            f, "he has it" if held_by is not None else "he never held it")) + touch(e))
        return touch(e)[0][0] == rp and held_by is not None

    def into_net(self, label):
        e = self.e
        s0 = struct_bytes(e)
        st = e.serialize()
        scored = False
        for y, vy in ((250, 3000),):
            e.unserialize(st)
            for f in range(90):
                self.keep.clear()
                self.park()
                e.setw(rec(AWAYG), 120)
                e.setw(rec(AWAYG) + 0x14, 0)
                if f == 0:
                    e.setw(PUCK, 0)
                    e.setw(PUCK + 0x14, y)
                    e.setw(PUCK + 0x18, 0)
                    e.setw(PUCK + 0x28, 0)
                    e.setw(PUCK + 0x2A, vy & 0xFFFF)
                    e.setb(PUCK + 0x60, 0xFF)
                e.run(1)
                if goal_seen(e, s0):
                    scored = True
                    break
        self.result(label, scored, s0)

    def result(self, label, scored, s0):
        e = self.e
        e.run(30)
        s1 = struct_bytes(e)
        up = [(f"{'home' if i < TMSIZE else 'away'} +${i % TMSIZE:03X}", s0[i], s1[i]) for i in range(len(s0)) if s1[i] > s0[i]]
        self.log.append((label, "goal" if scored else "no goal", "bytes up: %s" % up))


GOALS_OFF = None             # the home score's offset, found from the first goal (the byte that went 0 -> 1 first)


def goal_seen(e, s0):
    """A goal: the home struct's score word (NHL '94 +$0C) up."""
    return e.w(TEAM + 0x0C) != (s0[0x0C] << 8 | s0[0x0D])


def regain(e, base, log, retaker):
    p = Play(e, base, {A: (0, 0), B: (0, 90), C: (-70, 0), D: (70, 0)}, log)
    if not (p.pick_up(A, "A picks it up") and p.pick_up(D, "D (away) picks it up")
            and p.pick_up(retaker, ("A" if retaker == A else "C") + " picks it back up")):
        return
    rs = p.spots[retaker]
    p.spots[B] = (rs[0], rs[1] + 50)
    if p.pass_to(retaker, B, "pass to B"):
        p.into_net("into the empty net")


def giveandgo(e, base, log):
    p = Play(e, base, {A: (0, -50), C: (0, 0), B: (0, 50), D: (110, -220)}, log)
    if not p.pick_up(A, "A picks it up"):
        return
    for passer, rc, way, lab in ((A, C, "UP", "A to C"), (C, B, "UP", "C to B"), (B, C, "DOWN", "B back to C")):
        if not p.pass_to(passer, rc, lab, way=way):
            return
        for _ in range(10):
            p.frame()
    p.into_net("C's goal into the empty net")


def onetimer(e, base, log, touched=False):
    p = Play(e, base, {A: (0, 110), C: (0, 150), B: (0, 200), D: (110, -220)}, log)
    if not p.pick_up(A, "A picks it up"):
        return
    if not p.pass_to(A, C, "A to C"):
        return
    for _ in range(10):
        p.frame()
    st = e.serialize()
    s0 = struct_bytes(e)
    for press in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 26):
        e.unserialize(st)
        scored = False
        ot = set()
        for f in range(150):
            ot.add(e.w(0xBB72))                   # onetimerplayer: set while a one-timer is on
            held = ["UP"] + (["B"] if 2 <= f < 5 else []) + (["C"] if press <= f < press + 3 else [])
            e.setw(rec(AWAYG), 120)
            e.setw(rec(AWAYG) + 0x14, 0)
            if touched and f == press:            # the receiver's stick touched the pass first: a2touchpuck's list
                e.setw(TEAM + 0x18, p.pnum[B])    # (B last, then C, A) as NHL '94's test made it before the strike
                e.setw(TEAM + 0x1A, p.pnum[C])
                e.setw(TEAM + 0x1C, p.pnum[A])
            p.frame(held, hold=[k for k in p.keep if k not in (C, B)] + ([B] if f < 2 else []))
            if goal_seen(e, s0):
                scored = B in ot                  # a one-timer only (onetimerplayer held B's record): a caught
                break                             # pass shot in is another play
        if scored:
            p.log.append(("C to B, C pressed at frame %d" % press, "goal", "onetimerplayer seen %s" % sorted(ot)) + touch(e))
            p.result("the one-timer", True, s0)
            return
    p.log.append(("C to B with C pressed", "no goal at any timing") + touch(e))


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    pairs = list(zip(sys.argv[2::2], sys.argv[3::2]))
    res = {}
    for rom, state in pairs:
        e = Emu(rom)
        base = Path(state).read_bytes()
        name = Path(rom).name
        plays = [("regain: A wins it back (the bug)", lambda log: regain(e, base, log, A)),
                 ("regain: C wins it back (control)", lambda log: regain(e, base, log, C)),
                 ("give-and-go", lambda log: giveandgo(e, base, log)),
                 ("one-timer", lambda log: onetimer(e, base, log)),
                 ("one-timer, the receiver touched it first", lambda log: onetimer(e, base, log, True))]
        for lab, fn in plays:
            log = []
            fn(log)
            res[f"{name}: {lab}"] = log
            print(f"== {name}: {lab}")
            for row in log:
                print("  ", row, flush=True)
        del e
    (out / "assist95.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
