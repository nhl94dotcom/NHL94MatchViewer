"""The Genesis one-timer assist bug and a fix (2026-11-09, for NOSE4Web).

onetimershot (onetimer94.asm) pushes the shooter onto his team's touch list (tmtouch1 the scorer, tmtouch2 / tmtouch3
the assists, team struct +$18 / +$1A / +$1C) without a2touchpuck's checks: a player already the last touch changes
nothing, tmflast (the other team had the puck) overwrites instead of shifting, a second assist equal to the new last
touch is cleared. When the receiver's stick has touched the pass first (a touch, not a catch: a2touchpuck makes him
the last touch) and the one-timer then fires, the list reads shooter, shooter, passer and the goal code (assist 1 =
scorer) credits no assist: in the recorded games 3 of 71 one-timer goals (DAL-BOS P3 2:16, HFD-EDM P3 1:30, BOS-VAN
P1 3:40, each traced in the recording's touch words).

The fix: at $F6CE4 (`move.w tmtouch2(a0),tmtouch3(a0) / move.w tmtouch1(a0),tmtouch2(a0) / move.w d0,tmtouch1(a0)`,
16 bytes) a jsr to 42 bytes of a2touchpuck's own list update (FIX below), NOPs after; the code at $FFB14 (the ROM's
free $FF run starts at $FFB10). `patch` writes it into a copy, turns off the boot's ROM sum (jsr $FFAC0 at $300,
as NOSE4Web's builds do: it sums the ROM below $FFAC0 against a fixed total) and fixes the header checksum.

The test: the one-timer harness (ot_harness, the scoring-map test ROM and its states, nobody else on the ice),
cross-slot one-timers; just before the strike frame the touch list is either left as the game has it (the passer
last) or set as the bug finds it (the receiver last, the passer, a third player); 8 frames after the strike the list
is read, and the play is followed to a goal (the team's assists, +$CE a byte per player). On the original and on the
test ROM with the fix.

python gen_onetimer_assist_test.py patch ROM OUT
python gen_onetimer_assist_test.py test
python gen_onetimer_assist_test.py builds RETAIL BUILD ...   (NOSE4Web's builds laid over the test ROM: test_builds)"""
import os
import struct
import sys
from pathlib import Path

HOOK_AT, CODE_AT = 0xF6CE4, 0xFFB14
ORIGINAL = bytes.fromhex("3168001a001c31680018001a31400018")
FIX = bytes.fromhex(
    "b0680018"          # cmp.w  tmtouch1(a0),d0      already the last touch?
    "6722"              # beq.s  done
    "08a800030030"      # bclr   #tmflast,tmflags(a0)
    "660c"              # bne.s  st                    the other team had it: overwrite only
    "3168001a001c"      # move.w tmtouch2(a0),tmtouch3(a0)
    "31680018001a"      # move.w tmtouch1(a0),tmtouch2(a0)
    "31400018"          # st:    move.w d0,tmtouch1(a0)
    "b068001c"          # cmp.w  tmtouch3(a0),d0       also the second assist?
    "6604"              # bne.s  done
    "50e8001c"          # st     tmtouch3(a0)
    "4e75")             # done:  rts
HOME = 0xC6CE
TOUCH, ASSISTS = 0x18, 0xCE


def patch(rom, out):
    r = bytearray(Path(rom).read_bytes())
    assert r[HOOK_AT:HOOK_AT + 16] == ORIGINAL, "not the original onetimershot"
    assert r[CODE_AT - 4:CODE_AT + len(FIX)] == b"\xff" * (len(FIX) + 4), "no free room at $FFB10"
    r[CODE_AT:CODE_AT + len(FIX)] = FIX
    r[HOOK_AT:HOOK_AT + 16] = bytes.fromhex("4eb9") + struct.pack(">I", CODE_AT) + bytes.fromhex("4e71") * 5
    if r[0x300:0x306].hex() == "4eb9000ffac0":     # the boot's ROM sum (ValidationRoutine, longs below $FFAC0, against
        r[0x300:0x306] = bytes.fromhex("4e71") * 3  # a fixed total) fails on any change there: off, as NOSE4Web's builds
    total = sum(struct.unpack_from(">H", r, a)[0] for a in range(0x200, len(r), 2)) & 0xFFFF
    struct.pack_into(">H", r, 0x18E, total)
    Path(out).write_bytes(r)


def test():
    import harness
    from ot_harness import OneTimer, PASSER, RECEIVER
    from paths import ROM
    work = Path(os.environ.get("TEMP", ".")) / "smap94_onetimer_fix.bin"
    patch(ROM, work)
    setups = [((0, 213), (60, 213)), ((0, 213), (-60, 213)), ((30, 213), (-30, 213)), ((-30, 213), (30, 213)),
              ((0, 238), (60, 238)), ((0, 238), (-60, 238))]
    results = {}
    for name, rom in (("original", ROM), ("fix", str(work))):
        harness.Harness.__init__.__defaults__ = (rom,) + harness.Harness.__init__.__defaults__[1:]
        ot = OneTimer("genesis")
        e, s = ot.e, ot.s
        pn = lambda k: e.b(s.rec(k) + 0x66)
        lst = lambda: tuple(e.w(HOME + TOUCH + 2 * i) for i in range(3))
        rows = []
        for R, P in setups:
            for p in range(4):
                ot.setup("top", P, R, p, None)
                press, info = ot.pass_to_press("early", by=2 + p)
                if press is None:
                    continue
                pre, frames = ot.swing(press, None)
                if pre is None:
                    continue
                for case in ("as played", "receiver touched first"):
                    e.unserialize(pre)
                    r, q = pn(RECEIVER), pn(PASSER)
                    if case == "receiver touched first":
                        for i, v in enumerate((r, q, 0)):
                            e.setw(HOME + TOUCH + 2 * i, v)
                    before = lst()
                    assists0 = [e.b(HOME + ASSISTS + i) for i in range(26)]
                    s.set_seed(0x1234567 + p)              # ot.strike without reloading the state (keeps the list)
                    ot.run()
                    for _ in range(8):
                        ot.run()
                    after = lst()
                    out = ot.play_out()
                    assists = [e.b(HOME + ASSISTS + i) - assists0[i] for i in range(26)]
                    rows.append(dict(R=R, P=P, p=p, case=case, receiver=r, passer=q, before=before, after=after,
                                     outcome=out, assists_credited={i: a for i, a in enumerate(assists) if a}))
        results[name] = rows
    return results


def overlay(build, retail, base, out):
    """The test ROM (base) with a NOSE4Web build's changes against retail laid over it: every changed range but the
    header checksum and the boot's ROM-sum call ($300: the test ROM has it off already)."""
    a, b, r = Path(retail).read_bytes(), Path(build).read_bytes(), bytearray(Path(base).read_bytes())
    i = 0
    while i < len(a):
        if a[i] != b[i]:
            j = i
            while j < len(a) and any(a[q] != b[q] for q in range(j, min(j + 4, len(a)))):
                j += 1
            if not (i < 0x200 or 0x300 <= i < 0x306):
                r[i:j] = b[i:j]
            i = j
        else:
            i += 1
    Path(out).write_bytes(r)


def test_builds(builds):
    """The cases on the test ROM and on each build laid over it. One-timers (cross-slot, as test()), the touch list
    set just before the strike: "as played"; "receiver touched first" (receiver, passer, a third: the bug); "give and
    go" (passer, receiver, a third C: the receiver had passed to the passer, who passes back). And "give and go,
    caught": the same list, the pass taken (no one-timer: a2touchpuck's path). The list 8 frames after the strike /
    the catch, and each one-timer played out (the assists credited at a goal)."""
    import harness
    from ot_harness import OneTimer, PASSER, RECEIVER
    from paths import ROM
    roms = [("test ROM", ROM)]
    for build in builds:
        out = Path(os.environ.get("TEMP", ".")) / ("smap94_" + Path(build).name)
        overlay(build, RETAIL, ROM, out)
        roms.append((Path(build).name, str(out)))
    setups = [((0, 213), (60, 213)), ((0, 213), (-60, 213)), ((30, 213), (-30, 213)), ((-30, 213), (30, 213))]
    third = 7
    res = {}
    for name, rom in roms:
        harness.Harness.__init__.__defaults__ = (rom,) + harness.Harness.__init__.__defaults__[1:]
        ot = OneTimer("genesis")
        e, s = ot.e, ot.s
        pn = lambda k: e.b(s.rec(k) + 0x66)
        lst = lambda: tuple(e.w(HOME + TOUCH + 2 * i) for i in range(3))
        rows = []
        for R, P in setups:
            for p in range(3):
                ot.setup("top", P, R, p, None)
                start = e.serialize()
                r, q = pn(RECEIVER), pn(PASSER)
                cases = {"receiver touched first": (r, q, third), "give and go": (q, r, third)}
                # caught: the pass played with no press until the receiver has the puck
                e.unserialize(start)
                for i, v in enumerate(cases["give and go"]):
                    e.setw(HOME + TOUCH + 2 * i, v)
                d = __import__("ot_harness").DIRS[__import__("ot_harness").direction(ot.R[0] - ot.P[0], ot.R[1] - ot.P[1])]
                got = None
                for f in range(90):
                    ot.run([s.pass_button] + d if f < 4 else d)
                    if s.carrier() == RECEIVER:
                        for _ in range(5):                  # the list changes a frame after the catch
                            ot.run(d)
                        got = lst()
                        break
                rows.append(dict(R=R, P=P, p=p, case="give and go, caught", receiver=r, passer=q, after=got))
                e.unserialize(start)
                press, info = ot.pass_to_press("early", by=2 + p)
                if press is None:
                    continue
                pre, frames = ot.swing(press, None)
                if pre is None:
                    continue
                for case in ("as played", "receiver touched first", "give and go"):
                    e.unserialize(pre)
                    if case in cases:
                        for i, v in enumerate(cases[case]):
                            e.setw(HOME + TOUCH + 2 * i, v)
                    assists0 = [e.b(HOME + ASSISTS + i) for i in range(26)]
                    s.set_seed(0x1234567 + p)
                    ot.run()
                    for _ in range(8):
                        ot.run()
                    after = lst()
                    out = ot.play_out()
                    assists = [e.b(HOME + ASSISTS + i) - assists0[i] for i in range(26)]
                    rows.append(dict(R=R, P=P, p=p, case=case, receiver=r, passer=q, after=after, outcome=out,
                                     assists_credited={i: a for i, a in enumerate(assists) if a}))
        res[name] = rows
    return res


RETAIL = os.environ.get("NHL94_RETAIL", "")


def main():
    if sys.argv[1] == "patch":
        patch(sys.argv[2], sys.argv[3])
        return
    if sys.argv[1] == "builds":                 # python gen_onetimer_assist_test.py builds RETAIL BUILD ...
        import json
        global RETAIL
        RETAIL = sys.argv[2]
        for name, rows in test_builds(sys.argv[3:]).items():
            print("==", name)
            for r in rows:
                print(json.dumps(r))
        return
    import json
    res = test()
    for name, rows in res.items():
        print("==", name)
        for r in rows:
            print(json.dumps(r))


if __name__ == "__main__":
    main()
