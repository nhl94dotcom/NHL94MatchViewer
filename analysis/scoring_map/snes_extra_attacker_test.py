"""NOSE4Web's extra-attacker fix (the NHL94SNESVault's ExtraAttackerFix, hooked at $9B:8C96), played in the game (SNES,
2026-11-08, the user approved running the patched ROMs). SetLineSlot (Edit Lines) looks for the chosen player only in
one or two neighbouring slots of the cursor's, never in the extra attacker's (the line's sixth slot), so choosing the
extra attacker for a position leaves him in the line twice and drops the player he replaced. The fix searches every
slot and swaps.

From snes_harness's state: START, down to Edit Lines, B (the pad-1 team's lines: the home lines, $1CE4, 8 bytes a
line: goalie, LD, RD, LW, C, RW, extra attacker, 0). Then for each row RD-RW, B, n taps down the player list, B, and
the Best Line read back. Picks that give a player twice are marked.

python snes_extra_attacker_test.py ROM [ROM ...]"""
import sys
from collections import Counter

from paths import SNES_STATE_TOP
from snes_emu import SnesEmu

HOMELINES = 0x1CE4
ROWS = ((1, "RD"), (2, "LW"), (3, "C"), (4, "RW"))


def main():
    for rom in sys.argv[1:]:
        e = SnesEmu(rom)

        def tap(b, wait=30):
            e.run(3, hold=[b])
            e.run(wait)
        e.unserialize(open(SNES_STATE_TOP, "rb").read())
        e.run(30)
        tap("START", 60)
        for b in ("DOWN",) * 4 + ("B",):
            tap(b, 40)
        e.run(150)
        base = e.serialize()
        print(rom, "Best Line (LD RD LW C RW EA):", " ".join("%02x" % e.b(HOMELINES + j) for j in range(1, 7)))
        for row, name in ROWS:
            seen = []
            for n in range(14):
                e.unserialize(base)
                for _ in range(row):
                    tap("DOWN", 15)
                tap("B", 60)
                for _ in range(n):
                    tap("DOWN", 12)
                tap("B", 60)
                line = tuple(e.b(HOMELINES + j) for j in range(1, 7))
                if line in seen:
                    continue
                seen.append(line)
                dup = [p for p, c in Counter(line).items() if c > 1]
                print(f"  {name} pick {n:2}: {' '.join('%02x' % v for v in line)}"
                      f"{'  the same player twice: %s' % dup if dup else ''}")


if __name__ == "__main__":
    main()
