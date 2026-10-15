"""NHL '94 on the Super Nintendo, in RetroArch with the Snes9x core. Not working yet: this holds what is known so far
(CLAUDE.md, "SNES version"), in the shape genesis.py has, to be filled in as the rest is found.

Known: the team stats and the scoring summary (from the user's save-state parser), the object arrays, clock,
period and controller (from the NHL94SNES disassembly, github.com/Mhopkinsinc/NHL94SNES, checked on save states),
and the ROM's teams (read_teams). Not known yet: who has the puck, the screen state (menus, pause), per-player
stats, the animation words, the sprites, and how to find work RAM inside the running Snes9x core.
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

# Objects, as on the Genesis: 0-5 Home, 6-11 Away, 12 and 13 the nets (0, +/-268), 14 the puck, 15 its shadow. Each
# field is an array of 16 words (index = object * 2), not a record per object. Names from the NHL94SNES disassembly's
# ram94snes.asm; checked on the 445 save states: positions in the Genesis units (goalies at about +/-243, the
# nets at +/-268), exactly one joystick-controlled skater per team.
OBJ_X, OBJ_Y = 0x0D55, 0x0DB7     # integer positions (signed)
PUCK_VX, PUCK_VY = 0x0EDF, 0x0EFF
OBJ_POSITION = 0x0F43             # 0 G, 1 LD, 2 RD, 3 LW, 4 C, 5 RW, negative = off the ice (the Genesis codes)
OBJ_FACING = 0x1163               # 0-7
OBJ_ANIM = 0x11A3                 # current animation (offset into the animation data), as the Genesis +$58
OBJ_ANIM_STEP = 0x11C3
OBJ_FLAGS = 0x1283                # bit $0008: joystick controlled (as the Genesis +$62 bit $08)
OBJ_ROSTER = 0x12A3               # roster place (low byte)
OBJ_TEAM = 0x1503                 # 0 Home, else Away
PERIOD, CLOCK = 0x1630, 0x1632    # period from 0; clock in seconds left
PAD1 = 0x0776                     # controller 1, held
GAME_FLAGS2 = 0x15D8              # high byte: $08 replay playing, $20 power play, $01 faceoff (NHLPA '93 meanings)
LAST_TOUCH = 0x179A               # per team: the last player to touch the puck


def strip_header(data):
    """The ROM without a copier's 512-byte header (files whose size is 512 past a multiple of 1024 have one)."""
    return data[512:] if len(data) % 1024 == 512 else data


# ------------------------------------------------------------------------------------------------------ the ROM
# From the NHL94SNES disassembly (github.com/Mhopkinsinc/NHL94SNES), which rebuilds NHL94.smc byte for byte:
TEAM_LIST = 0x9CA5E7              # a long pointer (address word, bank byte, 0) to each team record, 28 teams
HOME_PALETTES, AWAY_PALETTES = 0x96CD4E, 0x96C9CE  # 16 colours per team (white jerseys at home, dark away)


def file_offset(address):
    """LoROM: bank $80-$FF (or $00-$7F) addresses $8000-$FFFF map to 32 KB pieces of the file."""
    return ((address >> 16) & 0x7F) * 0x8000 + (address & 0x7FFF)


def colour(word):
    """SNES colour word (0BBBBBGGGGGRRRRR) -> #rrggbb."""
    r, g, b = ((word >> shift) & 31 for shift in (0, 5, 10))
    return "#%02x%02x%02x" % tuple(v * 255 // 31 for v in (r, g, b))


def read_teams(rom_path):
    """Team names, rosters and uniform colours from the ROM, as genesis.read_teams gives them. A team record (as the
    Genesis one, lengths little-endian) starts with word offsets to its parts: players, scouting report, names, ...,
    and the eight lines (G, LD, RD, LW, C, RW, extra attacker, 0: player numbers from 1). Players: a length word
    (name length + 2), the name, the jersey number as decimal digits, seven bytes of ratings (two to a byte, in the
    Genesis order); a length of 2 ends the list. Then city, abbreviation, nickname and arena, each length-prefixed.
    Goalies are told by their ratings (below)."""
    from .common import overall
    rom = strip_header(rom_path.read_bytes())
    teams = []
    for k in range(28):
        ptr = rom[file_offset(TEAM_LIST) + 4 * k:file_offset(TEAM_LIST) + 4 * k + 3]
        team = file_offset(ptr[0] | ptr[1] << 8 | ptr[2] << 16)
        players_off, _, names_off = struct.unpack_from("<3H", rom, team)
        players, off = [], team + players_off
        while True:
            length = struct.unpack_from("<H", rom, off)[0]
            if not 2 < length <= 40:
                break
            name = rom[off + 2:off + length].decode("latin-1").rstrip("\x00")
            attrs = [n for byte in rom[off + length + 1:off + length + 8] for n in (byte >> 4, byte & 15)]
            # Goalies have no rating in slots 6, 8 and 9 (skater-only ratings); on the Genesis ROM, which says how
            # many goalies each team has, this picks all 65 and no skater.
            goalie = attrs[6] == attrs[8] == attrs[9] == 0
            players.append({"name": name, "num": int(f"{rom[off + length]:02x}"), "a": attrs, "g": goalie, "ovr": overall(attrs, goalie)})
            off += length + 8
        strings, at = [], team + names_off
        for _ in range(4):
            length = struct.unpack_from("<H", rom, at)[0]
            strings.append(rom[at + 2:at + length].decode("latin-1").rstrip("\x00") if 2 <= length < 40 else "")
            at += length
        palettes = [[colour(struct.unpack_from("<H", rom, file_offset(base) + 32 * k + 2 * i)[0]) for i in range(16)]
                    for base in (HOME_PALETTES, AWAY_PALETTES)]
        teams.append({"name": strings[0], "abbr": strings[1], "nickname": strings[2], "players": players,
                      "palettes": palettes, "logo": None})
    return teams


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
