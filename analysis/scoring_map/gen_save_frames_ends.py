"""Every NHL '94 Genesis save move's stick at the two nets (2026-11-19, the user: do the save animations differ between
the Up and the Down net the way the ready stances do?). From the ROM, no emulator.

What a save move can change: the goalie's body test (checkpuckcoll .chkgoalie) is a circle of 12-15 by Agility round
his centre, the same at both nets, so the only thing a frame changes is its stick point (HotList $A44C8, one x / y
byte pair per sprite frame; GetHot negates x for a goalie drawn mirrored and always negates y), and a low puck (height
5 or less, not rising) meets the stick first: within 8 of the blade it's played, 8-14 it passes untouched and the body
isn't tested that frame (the blind ring), else the body (the per-frame rule of xg.play_out and
make_diagrams.stick_cover_result, body 13 here).

Which frame the game uses (goaliesave): the side is the direction from the goalie to where the puck will cross his goal
line, against his facing (0 his right, 1 his left; flipped for a goalie drawn mirrored), so for a puck to the same
screen side the bottom goalie (facing up) plays his right-hand move and the top goalie (facing down) his left-hand one;
the pad stack's side is set by his end, his side of the net and his hand, the same way round. Two ways to lay one net
on the other:
- mirror (the replays' and NOSE4Web's fix's: the bottom net flipped top to bottom, screen x kept): a bottom frame
  (move r, direction d) against the top's (move l, direction 4 - d);
- rotate (the rink turned half round, as the league's play maps: each wing stays on its own side of the attack): a
  bottom frame (move r, d) against the top's (move r, d + 4), the side negated.
For each move and stance (square, turned to the screen's right, turned left), both frames' blades as (side, out) in
the bottom net's terms, their distance, and the share of low shots stopped at each point across the goal mouth
(goalie still 19 out, the shooter where the stance faces, 6 speeds x 8 phases), top against bottom: the share of the
mouth where only one stops it.

python analysis/scoring_map/gen_save_frames_ends.py [ROM]   (default %USERPROFILE%/NHL94_scoring_map/nhl94_retail.bin)
python analysis/scoring_map/gen_save_frames_ends.py mirror-rom IN OUT   (a copy with every bottom save frame's point
    set from its top partner, mirror pairing; the header sum fixed, the boot ROM check at $300 NOPped)"""
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from make_diagrams import stick_cover_result  # noqa: E402

HOT = 0xA44C8
G = 407
STACK = {0: 0, 1: 2, 2: 2, 3: 4, 4: 6, 5: 8, 6: 8, 7: 10}


def moves():
    """{move: (r frames by direction, l frames by direction)}: each a list of 8 tuples of the frames it shows."""
    one = lambda base, step: [(base + step * d,) for d in range(8)]  # noqa: E731
    two = lambda base, step: [(base + step * d, base + step * d + 1) for d in range(8)]  # noqa: E731
    stack = lambda base: [(base + STACK[d], base + STACK[d] + 1) for d in range(8)]  # noqa: E731
    return {
        "ready": (one(G, 3), one(G, 3)),
        "glove (blocker / glove)": (one(G + 1, 3), one(G + 2, 3)),
        "kick / butterfly (gstickr / l)": (one(G + 64, 2), one(G + 65, 2)),
        "pad stack": (stack(G + 40), stack(G + 52)),
        "high shoulder": (one(658, 2), one(659, 2)),
        "stick save (gstick2r / l)": ([(674 + 4 * d, 675 + 4 * d) for d in range(8)], [(676 + 4 * d, 677 + 4 * d) for d in range(8)]),
        "dive": (two(519, 2), two(519, 2)),
    }


STANCES = (("square", 0, (0, 110)), ("turned right", 1, (70, 90)), ("turned left", 7, (-70, 90)))


def hot(rom, fr):
    return struct.unpack_from(">bb", rom, HOT + 2 * fr)


def cover(blade, start, depth=19):
    out = []
    for ci in range(-40, 40):
        c = (ci + 0.5) / 2
        n = s = 0
        for sp in (3.0, 3.5, 4.0, 4.5, 5.0, 5.5):
            for ph in range(8):
                r = stick_cover_result(blade[0], depth + blade[1], start, c, sp, ph / 8)
                n += 1
                s += r in ("stick", "body")
        out.append(s / n)
    return out


def pairs():
    """(move, stance, bottom frame, top frame, symmetry) for every frame of every move."""
    for name, (R, L) in moves().items():
        for stance, d, start in STANCES:
            for k in range(len(R[d])):
                yield name, stance, start, R[d][k], L[(4 - d) % 8][k], "mirror"
                yield name, stance, start, R[d][k], R[(d + 4) % 8][k], "rotate"


def report(rom):
    print(f"{'move':32s} {'stance':13s} {'sym':6s} {'bottom':>13s} {'top':>13s} {'apart':>5s}  stopped bot / top  only one")
    summary = {}
    for name, stance, start, fb, ft, sym in pairs():
        bx, by = hot(rom, fb)
        tx, ty = hot(rom, ft)
        b = (bx, -by)
        t = (tx, ty) if sym == "mirror" else (-tx, ty)
        st = (start[0], start[1]) if sym == "mirror" else start
        cb, ct = cover(b, st), cover(t, st)
        only = sum(abs(p - q) for p, q in zip(cb, ct)) / len(cb)
        apart = math.dist(b, t)
        summary.setdefault((name, sym), []).append((apart, only))
        print(f"{name:32s} {stance:13s} {sym:6s} {fb:4d} {str(b):>8s} {ft:4d} {str(t):>8s} {apart:5.1f}  "
              f"{100 * sum(cb) / len(cb):5.1f} / {100 * sum(ct) / len(ct):5.1f}   {100 * only:5.1f}%")
    print("\nby move: the blades' mean distance apart; the goal mouth's mean share stopped at one net only")
    for (name, sym), v in summary.items():
        print(f"  {name:32s} {sym:6s} apart {sum(a for a, _ in v) / len(v):5.1f}   one net only {100 * sum(o for _, o in v) / len(v):5.1f}%")


def mirror_rom(src, dst):
    rom = bytearray(Path(src).read_bytes())
    done = set()
    for name, (R, L) in moves().items():
        for d in range(8):
            if d in (2, 3, 4, 5, 6):        # bottom frames: the goalie facing up the screen (0, 1, 7)
                continue
            for side_b, side_t in ((R, L), (L, R)):
                for fb, ft in zip(side_b[d], side_t[(4 - d) % 8]):
                    if fb in done:
                        continue
                    tx, ty = hot(rom, ft)
                    struct.pack_into(">bb", rom, HOT + 2 * fb, tx, -ty)
                    done.add(fb)
    rom[0x300:0x306] = bytes.fromhex("4E714E714E71")
    s = sum(struct.unpack_from(">H", rom, i)[0] for i in range(0x200, len(rom), 2)) & 0xFFFF
    struct.pack_into(">H", rom, 0x18E, s)
    Path(dst).write_bytes(bytes(rom))
    print(f"{len(done)} bottom frames set -> {dst}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "mirror-rom":
        mirror_rom(sys.argv[2], sys.argv[3])
    else:
        rom = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin").read_bytes()
        report(rom)
