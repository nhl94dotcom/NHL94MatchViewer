"""The lost-assist bug reproduced on purpose, and assist fixes checked (Genesis, 2026-11-09, for NOSE4Web;
analysis/assist_loss_study.py found the bug in the recordings). On the scoring-map test ROM's state (the game's own
code; only a loose puck is placed by hand, and every pickup, pass, one-timer and goal is the game's), with everyone
else parked. Plays:
- regain (the bug): home A picks the puck up; away D picks it up (puckglue: Home's assists wiped, tmflast set); A
  picks it back up; A passes to B (B pressed, UP held); the puck goes on into the empty net (B's goal).
- regain-control: the same with teammate C winning it back and passing.
- giveandgo: C, A, B, then A again pick the puck up (each a pickup through puckglue / a2touchpuck, as a pass
  reception is); A's goal into the empty net: retail drops C's second assist (A appears twice in the list).
- onetimer: C, then A pick it up; A passes to B in the slot and C is pressed while the pass travels: B's one-timer
  into the open net (the away goalie moved aside).
Each step logs the home touch list (team struct $C6CE +$18 / +$1A / +$1C) and tmflast (byte +$30 bit 3); at the goal,
the roster places whose goals (+$B4) and assists (+$CE) went up.

python gen_assist_repro.py OUT [ROM ...]   (no ROMs: the test ROM and a scratch copy with the regain fix: the 8 bytes
at $10176 -> `jsr $FFF00` / `nop`, and at $FFF00 `cmp.w $18(a0),d0` / `bne.s +12` / `bclr #3,$30(a0)` /
`move.l #$101A4,(sp)` / `rts`)"""
import json
import sys
from pathlib import Path

import harness as H
from paths import ROM

TEAM = 0xC6CE
A, B, C, D, AWAYG = 2, 3, 1, 7, H.GOALIE
PUCK = H.PUCK
FIX_AT, FIX_CODE = 0xFFF00, "b0680018660c08a8000300302ebc000101a44e75"


def fixed_rom(out):
    d = bytearray(Path(ROM).read_bytes())
    assert d[0x10176:0x1017E] == bytes.fromhex("b068001867000028"), d[0x10176:0x1017E].hex()
    code = bytes.fromhex(FIX_CODE)
    assert d[FIX_AT:FIX_AT + len(code)] == b"\xff" * len(code)
    d[FIX_AT:FIX_AT + len(code)] = code
    d[0x10176:0x1017E] = bytes.fromhex("4eb9000fff004e71")
    p = out / "assist_fix.bin"
    p.write_bytes(d)
    return str(p)


def touch(e):
    sw = lambda v: v - 0x10000 if v >= 0x8000 else v
    return [sw(e.w(TEAM + 0x18)), sw(e.w(TEAM + 0x1A)), sw(e.w(TEAM + 0x1C))], int(bool(e.b(TEAM + 0x30) & 8))


class Play:
    def __init__(self, h, spots, log):
        self.h, self.e, self.spots, self.log = h, h.e, dict(spots), log
        self.keep = set(spots)
        self.e.unserialize(h.base)
        self.pnum = {k: self.e.b(H.rec(k) + 0x66) for k in (A, B, C, D)}
        log.append(("roster places", {n: self.pnum[k] for n, k in (("A", A), ("B", B), ("C", C), ("D", D))}))
        for _ in range(20):
            self.frame()

    def park(self):
        e = self.e
        for k in range(12):
            if k in self.keep or k == AWAYG:
                continue
            e.setw(H.rec(k), -100 + 18 * k)
            e.setw(H.rec(k) + 0x14, self.h.park_y)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(H.rec(k) + off, 0)

    def hold(self, ks):
        e = self.e
        for k in ks:
            x, y = self.spots[k]
            e.setw(H.rec(k), x)
            e.setw(H.rec(k) + 0x14, y)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(H.rec(k) + off, 0)
            e.setb(H.rec(k) + 0x55, 0)        # facing up the screen

    def frame(self, held=(), hold=None):
        self.park()
        self.hold(self.keep if hold is None else hold)
        self.e.run(1, hold=list(held))

    def holder(self):
        e = self.e
        return e.b(PUCK + 0x61) if e.b(PUCK + 0x60) == 0 else None

    def pick_up(self, k, label):
        """The loose puck slid onto k's stick from one side or another until the game gives it to him."""
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
            for o in self.keep:                # the last holder can't simply take it back: a short no-touch
                e.setw(H.rec(o) + 0x5E, 0 if o == k else 30)
            for f in range(40):
                self.frame()
                if self.holder() == k:
                    for _ in range(10):        # he carries it a moment (pucknorm's a2touchpuck each frame)
                        self.frame()
                    self.log.append((label, "picked up") + touch(e))
                    return True
                if self.holder() is not None:
                    break
        e.unserialize(st)
        self.log.append((label, "NOT picked up") + touch(e))
        return False

    def pass_to(self, passer, receiver, label, one_timer=False, maxf=90, way="UP"):
        """Pad 1's skater (the passer, who has the puck: the pad follows the carrier) passes with B, `way` held,
        to the receiver that way; with one_timer, C is pressed while the pass travels. Returns when the receiver
        touches it (or after maxf)."""
        e = self.e
        rp = self.pnum[receiver]
        for f in range(maxf):
            held = [way] + (["B"] if 2 <= f < 5 else []) + (["C"] if one_timer and 8 <= f < 11 else [])
            self.frame(held, hold=[k for k in self.keep if k not in (passer, receiver)] + ([receiver] if f < 2 else []))
            if touch(e)[0][0] == rp:
                break
        held_by = None
        if touch(e)[0][0] == rp:
            for g in range(60):                # let him gain control of it (a hard pass can come off his stick)
                self.frame(hold=[k for k in self.keep if k != receiver])
                if self.holder() == receiver:
                    held_by = g
                    break
        self.log.append((label, "receiver's touch after %d frames, %s" % (
            f, "he has it" if held_by is not None else "he never held it")) + touch(e))
        return touch(e)[0][0] == rp and held_by is not None

    def into_net(self, label):
        """The puck (loose, nobody else touching it) sent on into the net Home attacks; the goalie aside."""
        e = self.e
        g0 = [e.b(TEAM + 0xB4 + i) for i in range(26)]
        a0 = [e.b(TEAM + 0xCE + i) for i in range(26)]
        st = e.serialize()
        scored = False
        for y, vy in ((250, 3000), (-250, -3000)):
            e.unserialize(st)
            s0 = e.w(H.SCORE_HOME)
            for f in range(90):
                self.keep.clear()
                self.park()
                e.setw(H.rec(AWAYG), 120)
                e.setw(H.rec(AWAYG) + 0x14, 0)
                if f == 0:
                    e.setw(PUCK, 0)
                    e.setw(PUCK + 0x14, y)
                    e.setw(PUCK + 0x18, 0)
                    e.setw(PUCK + 0x28, 0)
                    e.setw(PUCK + 0x2A, vy & 0xFFFF)
                    e.setb(PUCK + 0x60, 0xFF)
                e.run(1)
                if e.w(H.SCORE_HOME) != s0:
                    scored = True
                    break
            if scored:
                break
        self.result(label, scored, g0, a0)

    def result(self, label, scored, g0, a0):
        e = self.e
        e.run(30)
        goals = [i for i in range(26) if e.b(TEAM + 0xB4 + i) > g0[i]]
        assists = [i for i in range(26) if e.b(TEAM + 0xCE + i) > a0[i]]
        self.log.append((label, "goal" if scored else "no goal", "goal: place %s, assists: places %s" % (goals, assists)))


def regain(h, log, retaker):
    p = Play(h, {A: (0, 0), B: (0, 90), C: (-70, 0), D: (70, 0)}, log)
    if not (p.pick_up(A, "A picks it up") and p.pick_up(D, "D (away) picks it up")
            and p.pick_up(retaker, ("A" if retaker == A else "C") + " picks it back up")):
        return
    rs = p.spots[retaker]
    p.spots[B] = (rs[0], rs[1] + 50)
    if p.pass_to(retaker, B, "pass to B"):
        p.into_net("into the empty net")


def giveandgo(h, log):
    """A (pad 1) picks it up and passes up to C, C up to B, B back down to C (real passes; the pad follows the
    carrier), C's goal: assists B and A; retail drops A, the second assist, as C appears twice in the list."""
    p = Play(h, {A: (0, -50), C: (0, 0), B: (0, 50), D: (110, -220)}, log)
    if not p.pick_up(A, "A picks it up"):
        return
    for passer, rec, way, lab in ((A, C, "UP", "A to C"), (C, B, "UP", "C to B"), (B, C, "DOWN", "B back to C")):
        if not p.pass_to(passer, rec, lab, way=way):
            return
        for _ in range(10):
            p.frame()
    p.into_net("C's goal into the empty net")


def onetimer(h, log):
    """In the attacking zone: A (pad 1) picks it up and passes up to C; C passes up to B and C is pressed while it
    travels: B's one-timer at the open net (the goalie aside); assists C and A. The C press is tried at several
    moments from the same state until the swing connects."""
    sgn = 1 if h.top else -1
    p = Play(h, {A: (0, sgn * 110), C: (0, sgn * 150), B: (0, sgn * 200), D: (110, -sgn * 220)}, log)
    way = "UP" if h.top else "DOWN"
    if not p.pick_up(A, "A picks it up"):
        return
    if not p.pass_to(A, C, "A to C", way=way):
        return
    for _ in range(10):
        p.frame()
    e = p.e
    st = e.serialize()
    g0 = [e.b(TEAM + 0xB4 + i) for i in range(26)]
    a0 = [e.b(TEAM + 0xCE + i) for i in range(26)]
    s0 = e.w(H.SCORE_HOME)
    for press in (6, 9, 12, 15, 18, 22, 26):
        e.unserialize(st)
        scored = False
        for f in range(150):
            held = [way] + (["B"] if 2 <= f < 5 else []) + (["C"] if press <= f < press + 3 else [])
            e.setw(H.rec(AWAYG), 120)
            e.setw(H.rec(AWAYG) + 0x14, 0)
            p.frame(held, hold=[k for k in p.keep if k not in (C, B)] + ([B] if f < 2 else []))
            if e.w(H.SCORE_HOME) != s0:
                scored = True
                break
        if scored:
            p.log.append(("C to B, C pressed at frame %d" % press, "goal") + touch(e))
            p.result("the one-timer", True, g0, a0)
            return
    p.log.append(("C to B with C pressed", "no goal at any timing") + touch(e))


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    roms = sys.argv[2:] or [ROM, fixed_rom(out)]
    res = {}
    for rom in roms:
        h = H.Harness(rom=rom)
        name = Path(rom).name
        plays = [("regain: A wins it back (the bug)", lambda log: regain(h, log, A)),
                 ("regain: C wins it back (control)", lambda log: regain(h, log, C)),
                 ("give-and-go", lambda log: giveandgo(h, log)),
                 ("one-timer", lambda log: onetimer(h, log))]
        for lab, fn in plays:
            log = []
            fn(log)
            res[f"{name}: {lab}"] = log
            print(f"== {name}: {lab}")
            for row in log:
                print("  ", row, flush=True)
    (out / "assist_repro.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
