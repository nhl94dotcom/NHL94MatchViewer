"""The lost-assist bug reproduced on purpose (Genesis, 2026-11-09, for NOSE4Web; analysis/assist_loss_study.py found it
in the recordings). On the scoring-map test ROM's state (the game's own code; only the puck is placed by hand, loose,
and every pickup, the pass and the goal are the game's), with everyone else parked:
  1. the home skater A (record 2, pad 1) picks up a loose puck;
  2. an away skater D (record 7) picks it up (puckglue: Home's assists wiped, tmflast set);
  3. the loose puck is put at ``retaker``'s stick: A again (the bug), or teammate C (record 1, the control);
  4. he passes (B, toward B) to teammate B (record 3), who takes it;
  5. B is put in the slot with the puck and the away goalie moved aside; B shoots (C) into the open net.
Read each step: the home touch list (team struct $C6CE +$18 / +$1A / +$1C), tmflast (byte +$30 bit 3), and at the goal
the roster places whose goals (+$B4) and assists (+$CE) went up. Then the same on a scratch copy with the fix: the 8
bytes at $10176 (`cmp.w tmtouch1(a0),d0` / `beq.w .same`) become `jsr $FFF00` / `nop`, and $FFF00 is
    cmp.w $18(a0),d0 / bne.s +12 / bclr #3,$30(a0) / move.l #$101A4,(sp) / rts
(the same player: clear tmflast and go on at .same; otherwise back to the bclr / shift as before).

python gen_assist_repro.py OUT"""
import json
import sys
from pathlib import Path

import harness as H
from emu import Emu
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


def run(h, retaker, log):
    e = h.e
    e.unserialize(h.base)
    pnum = {k: e.b(H.rec(k) + 0x66) for k in (A, B, C, D)}
    log.append(("positions (+$35) of records 0-5", [e.b(H.rec(k) + 0x35) for k in range(6)]))
    log.append(("roster places", {"A": pnum[A], "B": pnum[B], "C": pnum[C], "D": pnum[D]}))
    spots = {A: (0, 0), B: (0, 90), C: (-70, 0), D: (70, 0)}
    keep = set(spots)

    def park():
        for k in range(12):
            if k in keep or k == AWAYG:
                continue
            e.setw(H.rec(k), -100 + 18 * k)
            e.setw(H.rec(k) + 0x14, h.park_y)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(H.rec(k) + off, 0)

    def hold_spots(ks):
        for k in ks:
            x, y = spots[k]
            e.setw(H.rec(k), x)
            e.setw(H.rec(k) + 0x14, y)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(H.rec(k) + off, 0)
            e.setb(H.rec(k) + 0x55, 0)        # facing up the screen

    def loose_at(k, dx, dy):
        """The puck loose dx, dy from him, sliding onto him (the game only tests objects that move)."""
        x, y = spots[k]
        e.setw(PUCK, x + dx)
        e.setw(PUCK + 0x14, y + dy)
        e.setw(PUCK + 0x18, 0)
        e.setw(PUCK + 0x28, (-dx * 40) & 0xFFFF)
        e.setw(PUCK + 0x2A, (-dy * 40) & 0xFFFF)
        e.setw(PUCK + 0x2C, 0)
        e.setb(PUCK + 0x60, 0xFF)
        e.setw(PUCK + 0x5E, 0)
        e.setw(H.rec(k) + 0x5E, 0)

    def pick_up(k, label):
        st = e.serialize()
        for dx, dy in ((0, 20), (10, 18), (-10, 18), (16, 8), (-16, 8), (0, -20), (18, 0), (-18, 0), (12, -14), (-12, -14)):
            e.unserialize(st)
            loose_at(k, dx, dy)
            for f in range(40):
                park()
                hold_spots(keep)
                e.run(1)
                if e.b(PUCK + 0x60) == 0 and e.b(PUCK + 0x61) == k:
                    for _ in range(10):              # he carries it a moment (pucknorm's a2touchpuck each frame)
                        park()
                        hold_spots(keep)
                        e.run(1)
                    log.append((label, "picked up (puck from %+d, %+d)" % (dx, dy)) + touch(e))
                    return True
                if e.b(PUCK + 0x60) == 0:            # someone else took it: try another approach
                    break
        e.unserialize(st)
        log.append((label, "NOT picked up") + touch(e))
        return False

    for _ in range(20):
        park()
        hold_spots(keep)
        e.run(1)
    if not pick_up(A, "1. A picks it up"):
        return
    if not pick_up(D, "2. D (away) picks it up"):
        return
    if not pick_up(retaker, "3. %s picks it back up" % ("A" if retaker == A else "C")):
        return
    # 4. the pass to B: B pressed with UP held (B is straight up the screen)
    passer_spot = spots[retaker]
    spots[B] = (passer_spot[0], passer_spot[1] + 50)
    got = None
    trace = []
    for f in range(90):
        park()
        hold_spots([k for k in keep if k not in (retaker, B)] + ([B] if f < 2 else []))
        e.run(1, hold=["UP"] + (["B"] if 2 <= f < 5 else []))
        if f % 6 == 0 or f < 8:
            trace.append((f, "puck %02x/%d" % (e.b(PUCK + 0x60), e.b(PUCK + 0x61)), "at %d,%d" % (e.sw(PUCK), e.sw(PUCK + 0x14)),
                          "B at %d,%d" % (e.sw(H.rec(B)), e.sw(H.rec(B) + 0x14)), "ctrl %s" % [k for k in range(12) if e.b(H.rec(k) + 0x62) & 8],
                          "A anim %04x" % e.w(H.rec(retaker) + 0x58)))
        if e.b(PUCK + 0x60) == 0 and e.b(PUCK + 0x61) == B:
            got = f
            break
    log.append(("4. the pass to B", "B has it after %s frames" % got) + touch(e))
    if touch(e)[0][0] != pnum[B]:
        log.extend(trace[:20])
        return
    # 5. the puck from there into the empty net, nobody else touching it (the goal reads the touch list)
    g0 = [e.b(TEAM + 0xB4 + i) for i in range(26)]
    a0 = [e.b(TEAM + 0xCE + i) for i in range(26)]
    st = e.serialize()
    for y, vy in ((250, 3000), (-250, -3000)):
        e.unserialize(st)
        s0 = e.w(H.SCORE_HOME)
        for f in range(90):
            keep.clear()
            park()
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
                break
        if e.w(H.SCORE_HOME) != s0:
            break
    scored = e.w(H.SCORE_HOME) != s0
    e.run(30)
    goals = [i for i in range(26) if e.b(TEAM + 0xB4 + i) > g0[i]]
    assists = [i for i in range(26) if e.b(TEAM + 0xCE + i) > a0[i]]
    log.append(("5. into the empty net", "goal" if scored else "no goal",
                "goal credited to place %s, assists to places %s" % (goals, assists)))


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    res = {}
    for name, rom in (("retail", ROM), ("fixed", None)):
        rom = rom or fixed_rom(out)
        h = H.Harness(rom=rom)
        for retaker, lab in ((A, "A wins it back (the bug)"), (C, "C wins it back (control)")):
            log = []
            run(h, retaker, log)
            res[f"{name}: {lab}"] = log
            print(f"== {name}: {lab}")
            for row in log:
                print("  ", row, flush=True)
    (out / "assist_repro.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
