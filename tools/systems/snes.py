"""NHL '94 on the Super Nintendo, in RetroArch with the Snes9x core. Not working yet: this holds what is known so far
(CLAUDE.md, "SNES version"), in the shape genesis.py has, to be filled in as the rest is found.

Known: the team stats and the scoring summary in work RAM (from the user's save-state parser), and that the ROM
stores teams the Genesis way with little-endian lengths. Not known: where the players and the puck are, the clock,
the period, per-player stats, the controller, the screen state, the animation words, the ROM's team table and
sprites, and how to find work RAM inside the running Snes9x core.
"""
import struct

NAME = "snes"
RAM_SIZE = 0x20000  # work RAM, bank $7E-$7F
BYTE_SWAP = 0       # Snes9x keeps work RAM as plain bytes; words are little-endian, as on the SNES
ROM_GLOB = "*.smc"
ACTIONS = {}        # animation words by action name: not found yet

# Team stats: home/away pairs of little-endian words, Away 2 bytes after Home, in the order of
# common.STAT_FIELDS (None where the address is not known yet). Shots come by period only (P1, P2, P3, OT).
STAT_ADDRESSES = {
    "goals": 0x178E, "faceoffs": 0x1792, "checks": 0x17B6, "passTried": 0x17BE, "passMade": 0x17BA,
    "attackZone": 0x1752, "breakTried": 0x17C2, "breakGoals": 0x17C6, "oneTimerTried": 0x17D6,
    "oneTimerGoals": 0x17DA, "psTried": 0x17CA, "psGoals": 0x17CE, "ppGoals": 0x1742, "ppTries": 0x1746,
    "penalties": 0x174A, "pim": 0x174E, "shGoals": 0x1762,
}
SHOTS_BY_PERIOD = (0x176A, 0x176E, 0x1772, 0x1776)
GOALS_BY_PERIOD = (0x177E, 0x1782, 0x1786, 0x178A)
TEAM_IDS = (0x1C98, 0x1C9A)  # Home, Away
# The game's scoring summary: a byte count, then 6 bytes per goal: a word (period << 14 | seconds into the period),
# a byte (bit 7 = Away; low bits 0 two men short, 1 shorthanded, 2 even, 3 power play, 4 two men up), then scorer,
# first and second assist as roster indices ($FF = none).
SCORING_COUNT, SCORING_LIST = 0x313A, 0x313C
STRENGTH = {0: "SH2", 1: "SHG", 2: "EV", 3: "PPG", 4: "PP2"}


def strip_header(data):
    """The ROM without a copier's 512-byte header (files whose size is 512 past a multiple of 1024 have one)."""
    return data[512:] if len(data) % 1024 == 512 else data


def scoring_summary(ram):
    """The goals in the game's own summary, from a copy of work RAM: [{period, secs, team, strength, scorer,
    assists}] (roster indices). Checked on the 446 NHL94_Classic save states: all 3334 goals fit."""
    out = []
    for g in range(ram[SCORING_COUNT] // 6):
        e = ram[SCORING_LIST + 6 * g:SCORING_LIST + 6 * g + 6]
        when = struct.unpack_from("<H", e, 0)[0]
        out.append({"period": when >> 14, "secs": when & 0x3FFF, "team": e[2] >> 7, "strength": STRENGTH.get(e[2] & 0x7F, "?"),
                    "scorer": e[3], "assists": [a for a in e[4:6] if a != 0xFF]})
    return out


def attach():
    """The running Snes9x with NHL '94 loaded: not written yet (how Snes9x keeps work RAM has to be found first)."""
    return None


def read_match(cap, rom_path, name, home=None, away=None):
    raise NotImplementedError("SNES recordings cannot be converted yet")
