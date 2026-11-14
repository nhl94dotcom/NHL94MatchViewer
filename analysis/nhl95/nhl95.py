"""NHL '95 (Genesis) data, read as NOSE / NOSE4Web read it (2026-11-14, NOSE4Web's request: check its NHL '95 support
against the game). Team table: a long per team at TEAM_TABLE (retail $772, 28 teams; the WN95HL's 34-team ROMs keep the
table there, longer); each team as NHL '94 keeps it (players from +word 0, names from +word 2), a player: a length word,
the name, the number in decimal digits, then fourteen 4-bit values. NOSE4Web's NHL '95 differences: handed / fighting as
NHL '93 (an odd value a left-handed shot), the goalie's glove hand as NHL '92 (0 right, 1 left), stick handling in 16
steps, folded to the 0-6 scale for the overall (0112223334445556).

The overall (NOSE4Web rating.ts, NHL '94's): skaters sum weights [1, 1.5, 1.5, 1, 0.5, 1, 0, 1.5, 1, 0.5, 0, 0.5, 0] x
the 13 values after weight; goalies [2.25, 0, 0, 2.25, 2.25, 0, 0, 0, 0, 0.5, 0.5, 0.5, 0.5] (each odd 2.25-weighted
value less 0.25); then floor(r + max(0, r - 25) + 25).

python analysis/nhl95/nhl95.py ROM [TEAM ...]"""
import struct
import sys
from pathlib import Path

TEAM_TABLE = 0x772
FOLD = [int(c) for c in "0112223334445556"]
SKATER_W = [1, 1.5, 1.5, 1, 0.5, 1, 0, 1.5, 1, 0.5, 0, 0.5, 0]
GOALIE_W = [2.25, 0, 0, 2.25, 2.25, 0, 0, 0, 0, 0.5, 0.5, 0.5, 0.5]


def team_count(rom):
    return 34 if rom[0x180:0x18E].decode("latin-1").strip().endswith("-34") else 28


def overall(a, goalie):
    a = list(a)
    if not goalie:
        a[8] = FOLD[a[8]]
    w = GOALIE_W if goalie else SKATER_W
    r = 0.0
    for i, wt in enumerate(w):
        v = a[i + 1]
        r += v * wt
        if goalie and wt == 2.25 and v % 2 == 1:
            r -= 0.25
    return int(r + max(0.0, r - 25) + 25)


def read_teams(rom):
    teams = []
    for k in range(team_count(rom)):
        team = struct.unpack_from(">I", rom, TEAM_TABLE + 4 * k)[0]
        players_off, _, names_off = struct.unpack_from(">3H", rom, team)
        nibbles = [n for byte in rom[team + 0x50:team + 0x52] for n in (byte >> 4, byte & 15)]
        goalies = max((i + 1 for i, n in enumerate(nibbles) if n), default=0)
        players, off = [], team + players_off
        while True:
            length = struct.unpack_from(">H", rom, off)[0]
            if not 2 < length <= 40:
                break
            name = rom[off + 2:off + length].decode("latin-1").rstrip("\x00")
            attrs = [n for byte in rom[off + length + 1:off + length + 8] for n in (byte >> 4, byte & 15)]
            g = len(players) < goalies
            players.append({"name": name, "num": int(f"{rom[off + length]:02x}"), "a": attrs, "g": g, "ovr": overall(attrs, g)})
            off += length + 8
        length = struct.unpack_from(">H", rom, team + names_off)[0]
        teams.append({"name": rom[team + names_off + 2:team + names_off + length].decode("latin-1").rstrip("\x00"),
                      "players": players, "at": team})
    return teams


if __name__ == "__main__":
    rom = Path(sys.argv[1]).read_bytes()
    print("product code", rom[0x180:0x18E], "teams", team_count(rom))
    for t in read_teams(rom):
        if len(sys.argv) > 2 and not any(x.lower() in t["name"].lower() for x in sys.argv[2:]):
            continue
        print(f"== {t['name']} (${t['at']:X}), {len(t['players'])} players")
        for p in t["players"]:
            print(f"  {'G' if p['g'] else ' '} #{p['num']:2d} {p['name']:24s} ovr {p['ovr']:3d}  {p['a']}")
