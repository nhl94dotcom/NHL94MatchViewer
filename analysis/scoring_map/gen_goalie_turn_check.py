"""NOSE4Web's goalie turning guard (2026-11-18, read from the code, not built): AdjustFacingDirection (goalies only:
the computer goalie's positioning and goalieacc's ready stance) runs its "don't turn through your own net" test only
from facings 1 and 6 (btst d1,#$42), the forbidden facings being 7, 0, 1 ($83) for the top goalie (pfgoal clear) and
3, 4, 5 ($38) for the bottom one (pfgoal set). A half-turn (wanted - current = 4) always steps +1, so the top goalie
needs the test from 6 (6 -> 7: there) and the bottom one from 2 (2 -> 3: missing); from 1 it never matters. Suggested
fix $42 -> $44 (NHL '94 $DB89, NHL '95 / W18 $80447).

  make ROM OUT          a scratch copy with the byte at $44, the header checksum made good and (NHL '94) the boot's
                        ROM check jsr at $300 NOPped as in NOSE4Web's builds (the sum alone didn't boot)
  case ROM ...          the case read from the code, placed: the bottom goalie facing 2 (right) and a loose puck
                        sliding right to left along or behind his goal line (5 lines x 3 speeds): his facings
  live 94|95 FRAMES GAMES ROM STATE [ROM STATE ...]   the computer on both sides (gen_centre_defence_check's set-up:
                        NHL '94 STATE - from power-on, cvc_record's matchups; NHL '95 / W18 a live state); every frame each
                        goalie (position 0) not controlled by a pad: his facing (+$55) and end; a turn through his own
                        net = a run of forbidden facings entered from one side (2 or 6) and left to the other

python gen_goalie_turn_check.py case ROM ... | make ROM OUT [MASK hex, default 44] | live 94|95 FRAMES GAMES ROM STATE ..."""
import struct
import sys
from collections import Counter
from pathlib import Path

GUARD = {"94": 0xDB89, "95": 0x80447}


def make(rom, out, value=0x44):
    b = bytearray(Path(rom).read_bytes())
    at = GUARD["94"] if len(b) <= 0x100000 else GUARD["95"]
    assert b[at - 3:at + 5] == bytes.fromhex("033c004267000022"), b[at - 3:at + 5].hex()
    b[at] = value
    if len(b) <= 0x100000 and b[0x300:0x306] == bytes.fromhex("4eb9000ffac0"):
        b[0x300:0x306] = bytes.fromhex("4e714e714e71")     # the boot's ROM check NOPped, as NOSE4Web's builds do
    s = sum(struct.unpack(f">{(len(b) - 0x200) // 2}H", bytes(b[0x200:]))) & 0xFFFF
    b[0x18E:0x190] = struct.pack(">H", s)
    Path(out).write_bytes(b)
    print(out, "byte", hex(at), "->", hex(value), "checksum", hex(s))


def live(game, rom, state, frames, n=0):
    import lowload
    from emu import Emu
    from gen_centre_defence_check import GAMES
    BASE, SZ = GAMES[game]["base"], 0x80
    if game == "94":
        import gen_ot_check as G
        from cvc_record import teams_for
        e = Emu(rom)
        G.to_setup(e, Path(__file__).parent)
        h, a = teams_for(n)
        for addr, v in ((0xC330, h), (0xC332, a), (0xD050, 0), (0xD056, 2), (0xD058, 1)):
            e.setw(addr, v)
        if not G.into_play(e):
            return Counter()
        e.setl(0xD066, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
        pads = (0xC328, 0xC32A)
    else:
        import gen95_organ_resume_check as O
        r = O.R(rom, state)
        e = r.e
        e.unserialize(r.base)
        pads = (0xBF4C, 0xBF4E)
    out, still, last = Counter(), 0, None
    run = {}                                              # goalie record -> (entered from, length) of a forbidden run
    prev = {}
    for f in range(frames):
        if f % 60 == 0:
            for a in pads:
                e.setw(a, 0)
            for k in range(12):
                e.setb(BASE + k * SZ + 0x62, e.b(BASE + k * SZ + 0x62) & ~8)
            if game == "94":
                c = e.w(0xC468)
                still = still + 1 if c == last else 0
                last = c
        e.run(1, hold=["START"] if game == "94" and still >= 8 and f % 60 < 4 else [])
        for k in range(12):
            a = BASE + k * SZ
            if e.b(a + 0x35) != 0:
                continue
            bottom = bool(e.b(a + 0x62) & 0x80)           # pfgoal set: shooting at the top, his net at the bottom
            bad = {3, 4, 5} if bottom else {7, 0, 1}
            fd = e.b(a + 0x55) & 7
            side = "bottom" if bottom else "top"
            out[f"{side} goalie frames"] += 1
            p = prev.get(k)
            prev[k] = fd
            if fd in bad:
                out[f"{side} goalie frames facing his net"] += 1
                if k not in run:
                    run[k] = [p, 0]
                run[k][1] += 1
            elif k in run:
                came, length = run.pop(k)
                if came in (2, 6) and fd in (2, 6) and came != fd:
                    out[f"{side} turns through his net from {came} to {fd}"] += 1
                    out[f"{side} turn-through frames"] += length
        if f % 3000 == 2999:
            lowload.breathe()
    return out


def case(rom, out_rows=None):
    """The case read from the code, placed (bot_scenario's live state, period 1: the home goalie defends the bottom
    net, pfgoal set): every skater parked at centre ice, the home goalie in his crease (0, -248) facing 2 (right), a
    loose puck sliding right to left (x +100 -> -100) at Y along or behind the bottom goal line (-264), speed VX; each
    frame his facing for 120 frames. Turning through the net: facings 3-5 before 6."""
    from bot import rec, PUCKC
    from bot_scenario import live_state
    from emu import Emu
    e = Emu(rom)
    base = live_state(e, 0)
    tot = Counter()
    for y in (-240, -256, -264, -272, -284):
        for vx in (-8000, -12000, -16000):
            e.unserialize(base)
            e.setw(0xC468, 250)
            g = next(k for k in range(6) if e.b(rec(k) + 0x35) == 0)
            seq = []
            for f in range(120):
                for k in range(12):
                    if e.b(rec(k) + 0x35) != 0:
                        e.setw(rec(k), (-60 + 11 * k) & 0xFFFF)
                        e.setw(rec(k) + 0x14, 0)
                        for off in (0x28, 0x2A, 0x2C):
                            e.setw(rec(k) + off, 0)
                if f == 0:
                    e.setw(rec(g), 0)
                    e.setw(rec(g) + 0x14, -248 & 0xFFFF)
                    e.setw(rec(g) + 0x54, 2)
                    e.setw(rec(14), 100)
                    e.setw(rec(14) + 0x14, y & 0xFFFF)
                    e.setw(rec(14) + 0x18, 0)
                    e.setw(rec(14) + 0x28, vx & 0xFFFF)
                    e.setw(rec(14) + 0x2A, 0)
                    e.setw(rec(14) + 0x2C, 0)
                    e.setw(PUCKC, 0xFFFF)
                e.run(1)
                seq.append(e.b(rec(g) + 0x55) & 7)
            first6 = next((i for i, v in enumerate(seq) if v == 6), None)
            via = seq[:first6] if first6 is not None else seq
            through = any(v in (3, 4, 5) for v in via) and first6 is not None
            tot["cases"] += 1
            tot["reached 6 through 3-5 (his net)"] += through
            tot["reached 6 by 1-0-7"] += first6 is not None and not through
            tot["frames facing 3-5"] += sum(v in (3, 4, 5) for v in seq)
            if out_rows is not None:
                out_rows.append((y, vx, "".join(map(str, seq))))
    return tot


def main():
    import lowload
    if sys.argv[1] == "case":
        for rom in sys.argv[2:]:
            rows = []
            t = case(rom, rows)
            print("==", Path(rom).name, dict(t), flush=True)
            for r in rows[:15]:
                print("  ", r)
        return
    if sys.argv[1] == "make":
        make(sys.argv[2], sys.argv[3], int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x44)
        return
    lowload.gentle()
    game, frames, games = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    args = sys.argv[5:]
    for rom, state in zip(args[0::2], args[1::2]):
        tot = Counter()
        for n in range(games):
            tot += live(game, rom, state, frames, n)
        print("==", Path(rom).name, flush=True)
        for k in sorted(tot):
            print(f"  {k}: {tot[k]}", flush=True)


if __name__ == "__main__":
    main()
