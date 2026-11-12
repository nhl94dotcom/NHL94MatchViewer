"""How often the Genesis matchup screen picks "Lately $ has been playing (extremely) well." (2026-11-12, for NOSE4Web
6806a72: on ROMs whose script lost a line (CDL and others) the "extremely" choice, line 35, is read past the script's
end). ScoutingReport builds its paragraph list (TestList) as $1B, $1D, $1A, $1D, then CompareHotColdTotals' $22 / $23
(the team hot / cold totals apart by $5E / $BD or more) or nothing, then $1E ... The list is found in work RAM by its
opening words once the matchup screen is up; the hot / cold rolls are random, so each run waits a different number of
frames on the title and Game Setup screens first. Teams as the ROM's Game Setup has them (unchanged).

python scouting_hot_rate.py ROM RUNS [FIRST]   -> one line per run, then the counts"""
import sys
from collections import Counter
from pathlib import Path

import lowload
import menu_shots as M

HEAD = bytes.fromhex("1b001d001a001d00")     # the state's words are little-endian


def one(rom, k):
    e = M.emulator(rom)
    e.run(900 + 37 * k)
    e.run(4, hold=["START"])
    e.run(120 + 23 * (k % 11))
    e.run(4, hold=["START"])
    e.run(180)
    e.run(4, hold=["START"])
    e.run(120)
    ram = bytes(e.ram[:0x10000])
    at = ram.find(HEAD)
    if at < 0:
        return None
    nxt = ram[at + 8] | ram[at + 9] << 8
    return {0x22: "34 (well)", 0x23: "35 (extremely)"}.get(nxt, "none")


def main():
    rom, runs = sys.argv[1], int(sys.argv[2])
    first = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    lowload.gentle()
    c = Counter()
    for k in range(first, first + runs):
        r = one(rom, k)
        c[r] += 1
        print(k, r, flush=True)
    print(dict(c))


if __name__ == "__main__":
    main()
