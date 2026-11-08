"""NOSE4Web's SNES comeback-bonus fix (bug 25), played in the game (2026-11-08, the user approved running the patched
ROMs). setplayer gives a team tied or trailing late in the third period +2 (ThirdPBonus) to Offensive Awareness and
Checking and +4 to the pass / shoot bias, but its clock test (half the period minus the clock, `bpl .6`) is the wrong
way round: on in the first half, off in the second. The fix makes it `bmi`.

setplayer runs at faceoffs. From live play: the third period, the clock in the first half (90% of the period left)
or the second (20%), Home one goal down or one up; an out-of-play whistle (a PenBuf entry), played on until the clock
runs again; then Home's skaters' working Checking ($1483). Trailing minus leading is the bonus.

python snes_comeback_test.py ROM [ROM ...]"""
import sys

from faceoff_fix_test import Snes

GSP, CLOCK, SCORE, PENBUF, GMCLOCK, CHECKING, POS = 0x1630, 0x1632, 0x178E, 0x15DE, 0x15D6, 0x1483, 0x0F43


def checking_after_faceoff(g, base, clock, home, away):
    g.e.unserialize(base)
    g.setw(GSP, 2)
    g.setw(CLOCK, clock)
    g.setw(SCORE, home)
    g.setw(SCORE + 2, away)
    g.setw(PENBUF, 3 << 8 | 0x06)
    g.setw(PENBUF + 2, 0)
    g.setw(GMCLOCK, 0)
    stopped = False
    for f in range(3000):
        g.e.lib.retro_run()
        stopped = stopped or bool(g.w(GMCLOCK))
        if stopped and not g.w(GMCLOCK):
            break
    return [g.w(CHECKING + 2 * k) for k in range(6) if g.w(POS + 2 * k) not in (0, 0xFFFF)]


def main():
    for rom in sys.argv[1:]:
        g = Snes(rom)
        base = g.bases[0]
        g.e.unserialize(base)
        length = 600 if g.w(CLOCK) > 300 else 300                    # the moment's period length (5 or 10 minutes)
        for name, clock in (("first half", int(length * 0.9)), ("second half", int(length * 0.2))):
            trail = checking_after_faceoff(g, base, clock, 0, 1)
            lead = checking_after_faceoff(g, base, clock, 1, 0)
            diff = [a - b for a, b in zip(trail, lead)]
            print(f"{rom.split('/')[-1]}: 3rd period, {name}: Home's Checking trailing minus leading {diff}")


if __name__ == "__main__":
    main()
