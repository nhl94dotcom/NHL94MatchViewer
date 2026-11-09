"""What an injury looks like in NHL '94 (Genesis), in the game (2026-11-08, for NOSE4Web's plan to bring NHLPA '93's
head blood back).

Injuries are rare (a puck carrier knocked onto his back, facing up or down the rink, with a random draw against the
hit's impact: FallDown), so a scratch copy of nhl94.bin is patched to make every fall of a puck carrier an injury (the
SPAfallback test at $1440E, the facing test at $1441A and the draw's `bgt.w .22` at $14436 NOP'd) and, for `game`, to make every injury a game injury (setInjuryType's `tst.w d0 / bne.w
.not0` at $14506 becomes `bra.w .injurygame`); the boot's ROM check (jsr $FFAC0 at $300) NOP'd, as in NOSE4Web's builds. `period` to make every injury a period
injury (the `bne.w .not0` at $14508 NOP'd: the $FFFD path). Pad 1 on the home team, no presses (its skater stands still and gets hit). From the
first frame a player's animation is SPAinjuryfall ($145C) or SPAinjury1 ($1AF4): sflags7 ($C2FC, bit 5 the game
injury), the injured player's animation word and sprite frame every 10 frames and a screenshot every 40, until the
next faceoff's play.

python gen_injury_check.py ROM OUT [game|period]"""
import sys
from pathlib import Path

import menu_shots as M
from gen_score_logo_check import Watch, GSP, CLOCK

SFLAGS7 = 0xC2FC
FALL, INJ1 = 0x145C, 0x1AF4
REC = 0xB04A


def patched(rom, out, game):
    data = bytearray(Path(rom).read_bytes())
    assert data[0x14432:0x1443A].hex() == "b06a00326e00005c" and data[0x14506:0x1450C].hex() == "4a4066000012"
    for at in (0x1440E, 0x1441A, 0x14436):                            # the fall-back, facing and random tests
        data[at:at + 4] = bytes.fromhex("4e714e71")
    if game:
        data[0x14506:0x1450C] = bytes.fromhex("600000324e71")          # bra.w .injurygame ($1453A)
    else:
        data[0x14508:0x1450C] = bytes.fromhex("4e714e71")              # bne.w .not0 gone: always the period path
    assert data[0x300:0x306].hex() == "4eb9000ffac0"
    data[0x300:0x306] = bytes.fromhex("4e714e714e71")                  # the boot's ROM check ($FFAC0), as NOSE4Web's builds
    p = out / ("inj_game.bin" if game else "inj_period.bin")
    p.write_bytes(data)
    return str(p)


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    mode = sys.argv[3] if len(sys.argv) > 3 else "game"
    out.mkdir(parents=True, exist_ok=True)
    g = Watch(patched(rom, out, mode == "game"), out)
    e = g.e
    M.play(e, "w900 START w120 START w120 DOWN*7 RIGHT w60", out)       # penalties on, line changes off
    for _ in range(40):
        if e.b(0xFFF7) == 0:
            break
        e.run(4, hold=["START"])
        e.run(200)
    g.wait_play()
    who = None
    for f in range(60 * 60 * 20):
        e.run(1)
        for k in range(12):
            if e.w(0xFF0000 | REC + k * 0x80 + 0x58) in (FALL, INJ1):
                who = k
                break
        if who is not None:
            break
        if f % 600 == 0 and not g.in_play():
            e.run(4, hold=["START"])
    if who is None:
        print("no injury")
        return
    a = REC + who * 0x80
    print(f"injury: record {who} ({'home' if who < 6 else 'away'}), period {g.w(GSP) + 1}, clock {g.w(CLOCK)}")
    last, shot = None, 0
    for t in range(0, 60 * 60, 10):
        st = (e.w(0xFF0000 | a + 0x58), e.w(0xFF0000 | a + 0x06), g.b(SFLAGS7) & 0x20 != 0, g.b(0xFFF7),
              g.w(CLOCK))
        if st != last:
            print(f"  +{t:5d} frames: animation ${st[0]:04X} sprite frame {st[1]} game-injury bit {st[2]} screen "
                  f"{st[3]} clock {st[4]}")
            last = st
        if t % 40 == 0 and shot < 40:
            e.screenshot(out / f"{mode}_{t:05d}.png")
            shot += 1
        e.run(10)
        if t > 600 and g.in_play() and e.w(0xFF0000 | a + 0x58) not in (FALL, INJ1) and g.w(CLOCK) != st[4]:
            print(f"  play on again at +{t} frames")
            break


if __name__ == "__main__":
    main()
