"""NHL '94 on the Super Nintendo, in RetroArch with the Snes9x core. Not working yet: this holds what is known so far
(CLAUDE.md, "SNES version"), in the shape genesis.py has, to be filled in as the rest is found.

Known: the team stats and the scoring summary (from the user's save-state parser), the object arrays, clock,
period and controller (from the NHL94SNES disassembly, github.com/abdulahmad/NHL94SNES, checked on save states),
and the ROM's teams (read_teams). Not known yet: who has the puck, the screen state (menus, pause), per-player
stats, the animation words, the sprites, and how to find work RAM inside the running Snes9x core.
"""
import math
import struct
from pathlib import Path

NAME = "snes"
RAM_SIZE = 0x20000  # work RAM, bank $7E-$7F
BYTE_SWAP = 0       # Snes9x keeps work RAM as plain bytes; words are little-endian, as on the SNES
ROM_GLOB = "*.smc"
# The animation words (SPA, addresses in bank $9D) the analysis needs, by name. Found on the first SNES recording
# (snes_2026-10-15_1755) from what the controlled skater started within 0.35 s of a button press (controller 1 drove
# Toronto: 210 answers against Pittsburgh's 100), how fast the puck left at a release, and the Genesis animations'
# timing patterns and order: A with the puck shoots ($ED4A: the puck leaves at a median 15500, up to 27000; $EE5C the
# other side), A without it bursts ($F342) or checks; $F196 is A's swing at a pass (always without the puck: a
# one-timer); B passes ($EC66, $ECD8; the goalie's $E34E) or poke-checks ($F208).
ACTIONS = {
    # $EF6E and $F020: one-timer swings (never with the puck; found from the user's review of bobbled passes in
    # 2026-10-16_1540_CHI-TOR, where every "led to a one-timer" pass met one; Larmer's $F020 there hit the post)
    "shoot": {"ed4a", "ee5c", "f196", "ef6e", "f020"},
    "pass": {"ec66", "ecd8"},
    "goalie_pass": {"e34e"},
    "poke": {"f208"},
    "hook": {"f864"},                 # SPAhook (Y without the puck; $F3D8 SPAhook2 follows), named in the disassembly
    "lunge": {"f342"},
    "down": {"f49c", "f54e"},         # falling forward, backward
    "dive": {"e4b6"},
    "goalie_save": set(),
}
# The goalie's save moves by the disassembly's names (GoalieSaveList: SPAgglover / l, SPAgstickr / l, SPAgstackr / l,
# SPAgsprawlr / l, SPAgbutterfly; SPAgdive). Until 2026-10-17 these were guessed from the Genesis order and three were
# wrong (a stick save read as a glove save, a pad stack as a stick save, the sprawls and butterfly missing).
SAVE_MOVES = {"e1e2": "glove", "e214": "glove", "e246": "stick", "e278": "stick", "e2aa": "pad stack", "e2fc": "pad stack",
              "e862": "sprawl", "e7d0": "sprawl", "e73e": "butterfly", "e4b6": "dive"}
CHECK_MOVES = {"f27a": "shoulder", "f2ac": "shoulder", "f2de": "hip", "f310": "hip"}
HIT_OUTCOMES = {"f49c": "knocked down", "f54e": "knocked down", "f6c0": "upended"}
CLOCK_STOPPED = 0x15D6  # gmclock: nonzero while the game clock is stopped (71% of stoppage samples, 1% of play)

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
# ram94s.asm; checked on the 445 save states: positions in the Genesis units (goalies at about +/-243, the
# nets at +/-268), exactly one joystick-controlled skater per team.
OBJ_X, OBJ_Y = 0x0D55, 0x0DB7     # integer positions (signed)
# Shot aiming (doshot in the NHL94SNES disassembly): passdir, the stick's screen direction (0 up, 1 up-right ... 7
# up-left, 8 none; it matched the controller at every person's shot in the helper's recordings), indexes `shotsets`
# ($9E:E43F; the same in NHL94, NHL94_Classic and SDL16): a point across the net (posts at +/-15) and a height row (12
# high, 6 middle, 0 along the ice), before the game's random scatter.
PASS_DIR = 0x0D03
AIM_TABLE = [(0, 12), (15, 12), (15, 6), (15, 0), (0, 0), (-15, 0), (-15, 6), (-15, 12), (0, 6)]
PUCK_Z, PUCK_Z_FRAC = 0x0DF9, 0x0DFD  # the puck's height (puckz) and its fraction, from the disassembly
PUCK_VX, PUCK_VY = 0x0EDF, 0x0EFF
OBJ_POSITION = 0x0F43             # 0 G, 1 LD, 2 RD, 3 LW, 4 C, 5 RW, negative = off the ice (the Genesis codes)
OBJ_FACING = 0x1163               # 0-7
OBJ_ANIM = 0x11A3                 # current animation (offset into the animation data), as the Genesis +$58
OBJ_ANIM_STEP = 0x11C3
OBJ_FRAME = 0x0D97                # the sprite frame shown, as the Genesis record's +$06: all values real frames in the
                                  # first recording. Looking it up from the animation, step and facing instead
                                  # turned right-handed skaters the wrong way: the game looks up direction (8 - d)
                                  # for them and then mirrors the picture, as the Genesis does
OBJ_FLAGS = 0x1283                # bit $0008: joystick controlled (as the Genesis +$62 bit $08)
OBJ_ROSTER = 0x12A3               # roster place (low byte)
OBJ_TEAM = 0x1503                 # 0 Home, else Away
PERIOD, CLOCK = 0x1630, 0x1632    # period from 0; clock in seconds left
PAD1 = 0x0776                     # controller 1, held (SNES bits: B $8000, Y $4000, Start $1000, Up $0800, Down
                                  # $0400, Left $0200, Right $0100, A $0080, X $0040)
PAD2 = 0x0778                     # controller 2: its presses answered by Pittsburgh's skater 149 times to 75 in the
                                  # online match (controller 1: Toronto 210 to 100)
# The match file keeps buttons in the Genesis layout the analysis uses ($80 Start, $40 A, $20 C, $10 B, $08 Right,
# $04 Left, $02 Down, $01 Up), by what they do: SNES B passes or poke-checks like the Genesis B, SNES A shoots or checks
# like the Genesis C, Y (the flip with the puck, a hook or hold without) like the Genesis A. PAD_LABELS names them.
# The SNES's own words are kept too (`padSnes`, every change: [frame, controller 1, controller 2]) for the buttons the
# Genesis has no counterpart for, as doinput reads them: X takes the goalie (with manual goalie on), L and R take the
# defenceman on the left / right of the screen (with defence control on), Select opens the line-change box.
PAD_MAP = ((0x8000, 0x10), (0x0080, 0x20), (0x4000, 0x40), (0x1000, 0x80),
           (0x0800, 0x01), (0x0400, 0x02), (0x0200, 0x04), (0x0100, 0x08))
SNES_BUTTONS = {"A": 0x0080, "B": 0x8000, "X": 0x0040, "Y": 0x4000, "L": 0x0020, "R": 0x0010, "Select": 0x2000, "Start": 0x1000}
PAD_LABELS = {"A": "Y", "B": "B", "C": "A"}


def genesis_pad(word):
    out = 0
    for s_bit, g in PAD_MAP:
        if word & s_bit:
            out |= g
    return out
GAME_FLAGS2 = 0x15D8              # sflags: bit $0001 paused (the pause menu; replays are watched from it), $0800
                                  # an instant replay playing (the user's two replays in snes_2026-10-15_1755)
PAUSED = 0x0801
LAST_TOUCH = 0x179A               # per team: the last player to touch the puck
PUCK_HOLDER = 0x0AE7              # the object that has the puck, 15 = nobody (see read_match)
# Penalties (from the first SNES recording: Toronto's Interference in P1, both teams in P3, two penalty shots):
PEN_BUFFER = 0x15DE   # (penalty number, object) byte pairs, 0 = free: an entry appears at the foul (play may go on,
                      # a delayed penalty), gets bit 7 of the object byte at the whistle, and is cleared once listed
BOX_STATE = 0x1852    # a word per roster place, Home's 26 then Away's: $FFFE bench, $FFFF ice, $FFFD out, $FFFC no
                      # player; else seconds left in the penalty box (120 for a minor)
PERIOD_LENGTH = 0x1C82  # seconds
PENALTY_SHOT = 0x24   # the penalty number of a penalty shot (rule 18); its object is the player who fouled
# Per-player stats: a byte per roster place, Home's 26 then Away's 26, in the Genesis order (checked on the first
# recording against what happened: Lemieux 3 goals, Murphy 2 assists, Potvin faced 12 shots and let in 5, ...).
PLAYER_GOALS, PLAYER_ASSISTS, PLAYER_SHOTS, PLAYER_PIM = 0x18EE, 0x1922, 0x1956, 0x198A  # goalies: against
# Checks thrown per player in NHL94_Classic (a hack that tracks them): at each rise of a team's checks the slot of a
# player of that team who was checking rose (49 of 54 times). Other ROMs may keep something else there, so it is
# used only where its totals equal the team's checks.
PLAYER_CHECKS = 0x168E
PLAYER_ENERGY = 0x17EA  # a word per roster place (Home's 26, then Away's): energy in the high byte, 16 = fresh


def strip_header(data):
    """The ROM without a copier's 512-byte header. Told by where the internal header is (its checksum and complement
    at $7FDC / $7FDE add up to $FFFF), as Snes9x does: the league ROMs SDL15 and SDL16 have a header and extra code
    past the first megabyte, so their size is not 512 past a multiple of 1024. Else by the size."""
    def internal_header(at):
        h = data[at + 0x7FC0:at + 0x7FE0]
        return len(h) == 32 and (h[0x1C] | h[0x1D] << 8) ^ (h[0x1E] | h[0x1F] << 8) == 0xFFFF
    if internal_header(0):
        return data
    return data[512:] if internal_header(512) or len(data) % 1024 == 512 else data


# ------------------------------------------------------------------------------------------------------ the ROM
# From the NHL94SNES disassembly (github.com/abdulahmad/NHL94SNES), which rebuilds NHL94.smc byte for byte:
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


def read_rules(rom):
    """Penalty names and minutes by penalty number, from the ROM's rule table (the Genesis layout: a table of word
    offsets, rule N at table + offset N; each rule: minutes, a byte, then a length-prefixed name). Penalty number =
    2 x rule number. In NHL94_Classic.smc the table is at $53EB; it is found by its rule 1, "Period Over"."""
    at = rom.find(b"Period Over")
    if at < 4:
        return {}
    entry = at - 4
    base = next((b for b in range(entry - 2, max(0, entry - 0x400), -1) if struct.unpack_from("<H", rom, b + 2)[0] == entry - b), None)
    if base is None:
        return {}
    rules = {}
    for number in range(1, 32):
        rule = base + struct.unpack_from("<H", rom, base + 2 * number)[0]
        length = struct.unpack_from("<H", rom, rule + 2)[0]
        if 2 < length < 30 and rule + 2 + length <= len(rom):
            rules[2 * number] = {"name": rom[rule + 4:rule + 2 + length].decode("latin-1"), "min": rom[rule] if rom[rule] <= 10 else 0}
    return rules


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


class Emulator:
    """NHL '94 loaded in Snes9x (snes9x_libretro.dll): its work RAM and cartridge, read-only.

    Found through Snes9x's memory map (in the core's writable data; see Finder.find), which points at work RAM
    then pointers to RAM, ROM, SRAM, VRAM ... (allocated elsewhere). Found by looking for a pointer whose cartridge
    has "NHL" in the LoROM title ($7FC0) or HiROM title ($FFC0); the pointer before it is work RAM (128 KB, plain
    bytes)."""
    system = NAME
    module_prefix = "snes9x"

    def __init__(self, attached):
        self.p = attached

    @classmethod
    def attach(cls):
        from . import process

        class Finder(process.Attached):
            module_prefix = "snes9x"

            def find(self, start, end):
                # Snes9x's memory map: one pointer per 4 KB of the SNES's address space (entry = bank << 4 |
                # address >> 12). Bank $7E is work RAM's first 64 KB (16 equal entries), $7F the next (16 entries
                # 64 KB on). Bank $80 at $8000 is the cartridge (LoROM: the entry points $8000 before it).
                for base, data in self.writable_regions(start, end):
                    n = len(data) // 8
                    q = struct.unpack_from("<%dQ" % n, data)
                    for i in range(n - 32):
                        ram = q[i]
                        if ram <= 0x10000 or (i and q[i - 1] == ram) or q[i + 15] != ram or q[i + 16] != ram + 0x10000:
                            continue
                        if not (all(q[i + j] == ram for j in range(16)) and all(q[i + 16 + j] == ram + 0x10000 for j in range(16))):
                            continue
                        entry = base + 8 * i - 0x7E0 * 8  # the map's first entry
                        rom_entry = self.raw(entry + 0x808 * 8, 8)
                        rom = struct.unpack("<Q", rom_entry)[0] + 0x8000 if rom_entry else 0
                        if b"NHL" in (self.raw(rom + 0x7FC0, 21) or b"") and self.raw(ram + RAM_SIZE - 16, 16) is not None:
                            return ram, rom
                return None

        found = Finder.attach()
        return cls(found) if found else None

    @property
    def pid(self):
        return self.p.pid  # RetroArch's process (the helper names the loaded ROM from its folder)

    @property
    def ram(self):
        return self.p.ram

    @property
    def rom(self):
        return self.p.rom

    def read(self, offset, size):
        return self.p.read(offset, size)

    def word(self, offset):
        return self.p.word(offset)

    def byte(self, offset):
        data = self.read(offset, 1)
        return data[0] if data else None

    def dump_rom(self):
        """Copy the cartridge out of the emulator into roms/<fingerprint>.smc (once per ROM), so the converter finds
        the ROM that was played: (path, fingerprint), path None if it could not be copied. Its size from the LoROM
        header's size byte ($7FD7: 1 KB << n), at least 1 MB."""
        from .common import ROOT
        fp = self.rom_fingerprint()
        if not fp:
            return None, None
        path = ROOT / "roms" / f"{fp}.smc"
        if not path.exists():
            code = (self.p.raw(self.rom + 0x7FD7, 1) or b"\x0a")[0]
            size = max(0x100000, min(0x400000, 1024 << code if code < 13 else 0))
            data = self.p.raw(self.rom, size)
            if not data:
                return None, fp
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(data)
        return path, fp

    def rom_fingerprint(self):
        """crc32 of the cartridge's first megabyte, as the ROM file has it without a copier header."""
        import zlib
        data = self.p.raw(self.rom, 0x100000)
        return f"{zlib.crc32(data):08x}" if data else None

    def close(self):
        self.p.close()


DEFAULT_ROM = Path.home() / "RetroArch-1.17-Win64/ROMs/SNES/NHL94.smc"


def find_rom(capture):
    """The ROM a recording was played on: by the fingerprint in capture.json (crc32 of the first megabyte of the
    ROM without header, as Emulator.rom_fingerprint gives it),
    looked for in roms/ and RetroArch's SNES folder; else the original game."""
    import json
    import zlib
    from .common import ROOT
    layout = capture / "capture.json"
    stored = json.loads(layout.read_text()).get("rom_crc32") if layout.exists() else None
    if not stored:
        return DEFAULT_ROM, "assumed; this recording does not say which ROM was played"
    for path in sorted((ROOT / "roms").glob(ROM_GLOB)) + sorted(DEFAULT_ROM.parent.glob(ROM_GLOB)):
        if f"{zlib.crc32(strip_header(path.read_bytes())[:0x100000]):08x}" == stored:
            return path, "matched to the recording"
    return DEFAULT_ROM, "assumed; no ROM matches the one that was recorded"


# ------------------------------------------------------------------------------------------- what the helper reads
BLOCKS = [(0x0000, 0x4000)]  # what each sample keeps: the objects, the stats, the scoring summary (work RAM $0000-$3FFF)


class View:
    """What the game is doing, from one read of the recorded block (as genesis.View): the period, clock, score and
    teams, whether players are on the ice (their roster bytes read $FF before the opening faceoff and at
    intermissions, as on the Genesis), whether the game is paused or showing a replay (GAME_FLAGS2), and whether it
    is back at the menus (the teams and score cleared). At the final horn the SNES game moves the period on to 4 and
    resets the clock to the period length; the clock is given as 0 then, as the Genesis game shows it, so the
    helper's end-of-game test serves both."""

    def __init__(self, emu):
        block = emu.read(*BLOCKS[0])
        if block is None:
            raise ConnectionError("the emulator went away")
        self.blocks = [block]
        word = lambda a: struct.unpack_from("<H", block, a)[0]
        self.period, self.clock = word(PERIOD), word(CLOCK)
        if self.period >= 4:
            self.clock = 0
        self.score = (word(STAT_ADDRESSES["goals"]), word(STAT_ADDRESSES["goals"] + 2))
        self.teams = (word(TEAM_IDS[0]), word(TEAM_IDS[1]))
        # A line-up on the ice: each team's places hold different players ($FF = nobody). At the menus they can all
        # read 0 (2026-10-16_1528: the helper took the menus' MTL vs LA for a game under way, a second before the
        # real teams were picked). Players parked off the ice (x = -240: the penalty box, everyone but the shooter and
        # goalie in a penalty shot) don't count: in a penalty shot two of them can share a place, which had stopped
        # the recording for every SNES penalty shot (2026-10-18_1934_BOS-PIT: Jagr's penalty-shot goal not recorded).
        x = lambda k: (lambda v: v - 0x10000 if v >= 0x8000 else v)(word(OBJ_X + 2 * k))
        rosters = [block[OBJ_ROSTER + 2 * k] if x(k) != -240 else 0xFF for k in range(12)]
        lineup = lambda places: (lambda on: bool(on) and len(set(on)) == len(on))([r for r in places if r != 0xFF])
        self.on_ice = lineup(rosters[:6]) and lineup(rosters[6:])
        self.screen = word(GAME_FLAGS2)
        self.in_menus = self.teams[0] >= 28 or self.teams[1] >= 28 or (self.teams == (0, 0) and self.score == (0, 0)
                                                                          and self.period == 0 and self.clock == 0)
        self.in_game = not self.in_menus and not self.screen & PAUSED

    @property
    def live(self):
        return self.in_game and self.on_ice

    def describe(self):
        return f"P{min(self.period, 2) + 1} {self.clock // 60}:{self.clock % 60:02d}, {self.score[0]}-{self.score[1]}"


def attach():
    """The running Snes9x with an NHL '94 ROM loaded, or None."""
    return Emulator.attach()


ANIM_BANK = 0x9D0000    # the animation word (SPA) is an address in bank $9D: 8 direction pointers to (frame, time)
# Working ratings per object (a word each), set when a player comes on the ice: weight, Agility (legstr), Speed
# (legspd), Defensive Awareness as a reaction time (aidef), Shot Power (shotspd), Shot Accuracy (shotacc). Kept as
# match["work"] for the expected-goals model, as the Genesis reader keeps its record's +$67-$6D.
OBJ_WORK = (0x12C3, 0x12E3, 0x1303, 0x1343, 0x1363, 0x1383)
OBJ_ATTRIBUTE = 0x0E03  # bit $0800 set for every right-handed skater (777 of 777 in the save states, no left-hander):
                        # his picture is drawn mirrored, as on the Genesis


def animation_frame(rom, spa, step, facing):
    """The sprite frame an object shows: the frame word in its animation's list for its facing, `step` bytes in
    (4 per frame and time pair). None if that is not an animation (off the ice, between animations). On the 445
    save states this gives a frame for 98% of skaters and nearly every goalie."""
    if spa < 0x8000:
        return None
    ptr = struct.unpack_from("<H", rom, file_offset(ANIM_BANK | spa) + 2 * (facing & 7))[0]
    if ptr < 0x8000:
        return None
    frame = struct.unpack_from("<H", rom, file_offset(ANIM_BANK | ptr) + step)[0]
    return frame if frame < 976 else None


def animation_lists(rom, spa):
    """An animation's frames for each of the 8 facings (the viewer turns players with them, as the Genesis 'anims')."""
    dirs = []
    for d in range(8):
        ptr = struct.unpack_from("<H", rom, file_offset(ANIM_BANK | spa) + 2 * d)[0]
        if ptr < 0x8000:
            return None
        frames, at = [], file_offset(ANIM_BANK | ptr)
        while len(frames) < 64:
            frame, time = struct.unpack_from("<Hh", rom, at)
            if frame >= 976:
                return None
            frames.append(frame)
            at += 4
            if time < 0:
                break
        dirs.append(frames)
    return dirs


HOT_COLD = 0x1A12        # 12 bytes per player: (roster place + 26 for Away) x 12 + rating number
HOT_COLD_RAISED = 0x19CE  # non-zero while a loud crowd has raised four bytes of each entry by 2
HOT_COLD_RATINGS = (1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13)  # roster index of rating number 0-11 (Agl ... Agr / glove)


def add_hot_cold(cap, match):
    """Each player's hot / cold bonuses as play uses them (docs/SNES_MECHANICS.md 2.2), into his roster entry as "hcs":
    a value per rating in roster order: a number added to the working rating (0-15 scale: the byte / 4), or "max" where
    the byte is negative, which the game's sign bug turns into the highest rating."""
    if not match.get("rosters"):
        return
    calm = [i for i in range(cap.count // 4, cap.count, max(1, cap.count // 50)) if cap.word(i, HOT_COLD_RAISED) == 0]
    i = calm[0] if calm else cap.count // 2
    for team in (0, 1):
        for place, player in enumerate(match["rosters"][team]):
            values = [0] * 14
            for n, a in enumerate(HOT_COLD_RATINGS):
                byte = cap.byte(i, HOT_COLD + (place + 26 * team) * 12 + n)
                values[a] = "max" if byte > 127 else byte >> 2
            player["hcs"] = values


class _Kept:
    """The live-play samples read so far (as LivePlay, but keep and times grow as the reader goes)."""

    def __init__(self, cap, keep, times):
        self.cap, self.keep, self.times = cap, keep, times

    @property
    def count(self):
        return len(self.keep)

    def ms(self, i):
        return self.times[i]

    def word(self, i, address):
        return self.cap.word(self.keep[i], address)

    def byte(self, i, address):
        return self.cap.byte(self.keep[i], address)

    def raw(self, i, address, length):
        return self.cap.raw(self.keep[i], address, length) if hasattr(self.cap, "raw") else None


class MatchReader:
    """read_match in pieces: feed() reads samples as a recording grows (the live broadcast gives it the new ones only);
    result() makes the match file's contents from what has been read so far (copies: the reader goes on)."""

    def __init__(self, cap, rom_path):
        from .common import PLAYERS, STAT_FIELDS
        self.rom = strip_header(rom_path.read_bytes())
        self.teams = read_teams(rom_path)
        self.match = {"version": 21, "name": None, "system": NAME, "positions": ["G", "LD", "RD", "LW", "C", "RW"],
                      "t": [], "clock": [], "period": [], "score": [], "shots": [], "puck": [], "puckV": [], "lights": [],
                      "pos": [], "ctrl": [], "owner": [], "posts": [], "nets": [], "aim": [], "delayed": [], "penalties": [],
                      "pad": [], "pad2": [], "padLabels": PAD_LABELS, "padSnes": [], "work": []}
        # work: [frame, object, weight, Agility, Speed, aidef, Shot Power, Shot Accuracy]
        self.last_work = [None] * PLAYERS
        self.facing, self.roster, self.role, self.anim, self.frame, self.mirror, self.puck_frame, self.spas = [], [], [], [], [], [], [], set()
        self.stats = {"f": [], "home": [], "away": [], "n": len(STAT_FIELDS), "p": 8, "x": "PIM"}
        self.last_vectors, self.last_stat_ms, self.last_post = None, -10_000, -10_000
        self.ice = [0] * 52  # game seconds on the ice, by roster place (Home's 26, then Away's)
        self.checks_known = False
        self.frames, self.next = [], 0           # raw samples: frame counters, the next to look at
        self.keep, self.times = [], []           # live-play samples: raw index, time with pauses closed up
        self.skipped_pause = False               # a paused sample since the last one kept
        self.view = _Kept(cap, self.keep, self.times)
        self.libraries = False

    def checks_real(self, cap, i):
        """Is the per-player checks array real (NHL94_Classic)? Its totals equal the teams' checks at sample i."""
        return all(sum(cap.byte(i, PLAYER_CHECKS + 26 * side + j) for j in range(26))
                   == cap.word(i, STAT_ADDRESSES["checks"] + 2 * side) for side in (0, 1))

    def feed(self, cap, final=True, count=None, checks_known=None):
        """Read the raw samples not read yet, up to `count`. Paused and replay samples are left out (the research
        recorder keeps them), and the timeline closes over them, as the helper records the Genesis game: only live
        play. Netplay's rollback (and RetroArch's run-ahead) runs the game a few frames ahead on guessed input, then
        rewinds and replays them: a read made while it was ahead shows everyone a few frames on, and the next one back
        again (the user saw skaters jump and jump back in 2026-10-16_1540_CHI-TOR, about 240 times a game). The frame
        counter (FRAME_COUNTER) going back a few frames within the next half second, or showing the same frame again
        (replayed with the real input), says that sample was ahead of time: it is left out. (Only a few frames: the
        counter also jumps or restarts between screens.) So a sample is read once the half second after it is in (all
        of them when `final`)."""
        n = cap.count if count is None else count
        self.frames += [cap.word(i, FRAME_COUNTER) for i in range(len(self.frames), n)]
        frames, limit = self.frames, n
        if not final:
            while limit > self.next and cap.ms(n - 1) - cap.ms(limit - 1) <= 500:
                limit -= 1
        if limit <= self.next:
            return
        self.checks_known = self.checks_real(cap, limit - 1) if checks_known is None else checks_known
        for raw in range(self.next, limit):
            if any((frames[raw] - frames[j]) & 0xFFFF <= ROLLBACK_FRAMES
                   for j in range(raw + 1, min(n, raw + 32)) if cap.ms(j) - cap.ms(raw) <= 500):
                continue
            if cap.word(raw, GAME_FLAGS2) & PAUSED:
                self.skipped_pause = True
                continue
            if self.keep:
                gap = cap.ms(raw) - cap.ms(self.keep[-1])
                self.times.append(self.times[-1] + (min(gap, 17) if self.skipped_pause else gap))
            else:
                self.times.append(0)
            self.keep.append(raw)
            self.skipped_pause = False
            self._sample(self.view, len(self.keep) - 1)
        self.next = limit

    def _sample(self, cap, i):
        signed = lambda i, a: (lambda v: v - 0x10000 if v >= 0x8000 else v)(cap.word(i, a))
        from .common import DIGITS, PLAYERS, STAT_FIELDS
        # This sample's work RAM, read once ($0000-$3FFF, all the addresses read here): picking values out of it is
        # several times faster than asking the recording for each (tens of millions of reads a game, which the live
        # broadcast does every few seconds). Save states (no raw) are read value by value.
        whole = getattr(cap, "raw", None)
        mem = whole(i, 0, 0x4000) if whole else None
        if mem is not None:
            w = lambda a, m=mem: m[a] | (m[a + 1] << 8)
            b = lambda a, m=mem: m[a]
        else:
            w = lambda a, i=i: cap.word(i, a)
            b = lambda a, i=i: cap.byte(i, a)
        sg = lambda a: (lambda v: v - 0x10000 if v >= 0x8000 else v)(w(a))
        self.match["t"].append(cap.ms(i))
        self.match["period"].append(w(PERIOD))
        self.match["clock"].append(w(CLOCK))
        self.match["score"] += [w(STAT_ADDRESSES["goals"]), w(STAT_ADDRESSES["goals"] + 2)]
        self.match["shots"] += [sum(w(a + side) for a in SHOTS_BY_PERIOD) for side in (0, 2)]
        # The puck's height is not read; while the clock is stopped it is given as -256, as the Genesis game hides
        # the puck from a whistle to the faceoff, which the analysis uses to tell stretches of play apart.
        stopped = w(CLOCK_STOPPED) != 0
        px, py = sg(OBJ_X + 28), sg(OBJ_Y + 28)
        vx, vy = sg(PUCK_VX), sg(PUCK_VY)
        # The puck's height: puckz (integer) and its fraction (the NHL94SNES disassembly's ram94s.asm), as the
        # Genesis record's +$24. Shots on goal reach 1-18.
        pz = sg(PUCK_Z) + w(PUCK_Z_FRAC) / 65536
        self.match["puck"] += [px, py, -256 if stopped else round(max(0.0, pz), 1)]
        self.match["puckV"] += [round(vx / 100), round(vy / 100)]
        # A post, by the Genesis rule: the loose puck turning back out of the end zone right beside a post.
        if i and b(PUCK_HOLDER) >= 12 and cap.ms(i) - self.last_post > 1000:
            fresh = (vx, vy) != (signed(i - 1, PUCK_VX), signed(i - 1, PUCK_VY))
            if (fresh and 14 <= abs(px) <= 28 and 252 <= abs(py) <= 268 and vy * py < 0 and abs(vx) + abs(vy) >= 1500
                # and not a puck coming out from behind the net past its side (2026-10-18: four of those had read as posts in
                # CHI-LA): behind the goal line (268) in the half second before
                and not any(abs(self.match["puck"][3 * q + 1]) > 268 for q in range(max(0, len(self.match["t"]) - 31), len(self.match["t"]) - 1))):
                self.match["posts"].append(len(self.match["t"]) - 1)
                self.last_post = cap.ms(i)
        # Team stat snapshots, in common.STAT_FIELDS order (no per-player values yet), when they change and each
        # second, as the Genesis reader keeps them.
        vector = [sum(w(a) for a in SHOTS_BY_PERIOD)] + [w(STAT_ADDRESSES[f]) for f in STAT_FIELDS[1:]]
        vector2 = [sum(w(a + 2) for a in SHOTS_BY_PERIOD)] + [w(STAT_ADDRESSES[f] + 2) for f in STAT_FIELDS[1:]]
        # then 8 values per roster place, as the Genesis reader: goals, assists, shots, penalty minutes ('x' = PIM),
        # checks thrown (where known), ice time (the game keeps none that was found: counted here, each second the
        # clock ticks off going to everyone on the ice), energy, penalty word ($00ss serving ss seconds, $FFFF none;
        # the delayed flag is not known)
        clock = w(CLOCK)
        if i and w(PERIOD) == cap.word(i - 1, PERIOD) and 0 < cap.word(i - 1, CLOCK) - clock <= 3:
            for k in range(12):
                code = sg(OBJ_POSITION + 2 * k)
                place = b(OBJ_ROSTER + 2 * k)
                if 0 <= code < 6 and place < 26:
                    self.ice[26 * (k // 6) + place] += cap.word(i - 1, CLOCK) - clock
        if mem is not None:
            goals, assists, shots, pim = (mem[a:a + 52] for a in (PLAYER_GOALS, PLAYER_ASSISTS, PLAYER_SHOTS, PLAYER_PIM))
            checks = mem[PLAYER_CHECKS:PLAYER_CHECKS + 52]
            energy, boxes = mem[PLAYER_ENERGY:PLAYER_ENERGY + 104], mem[BOX_STATE:BOX_STATE + 104]
        else:
            goals, assists, shots, pim, checks = ([b(a + at) for at in range(52)] for a in
                                                  (PLAYER_GOALS, PLAYER_ASSISTS, PLAYER_SHOTS, PLAYER_PIM, PLAYER_CHECKS))
            energy = [v for at in range(52) for v in (w(PLAYER_ENERGY + 2 * at) & 255, w(PLAYER_ENERGY + 2 * at) >> 8)]
            boxes = [v for at in range(52) for v in (w(BOX_STATE + 2 * at) & 255, w(BOX_STATE + 2 * at) >> 8)]
        for side, vec in ((0, vector), (1, vector2)):
            for idx in range(26):
                at = 26 * side + idx
                box = boxes[2 * at] | (boxes[2 * at + 1] << 8)
                vec += [goals[at], assists[at], shots[at], pim[at], checks[at] if self.checks_known else 0, self.ice[at],
                        energy[2 * at + 1], min(box, 255) if 0 < box < 0x1000 else 0xFFFF]
        if (vector, vector2) != self.last_vectors or cap.ms(i) - self.last_stat_ms >= 1000:
            self.stats["f"].append(len(self.match["t"]) - 1)
            self.stats["home"].append(vector)
            self.stats["away"].append(vector2)
            self.last_vectors, self.last_stat_ms = (vector, vector2), cap.ms(i)
        f = w(OBJ_FRAME + 28)
        self.puck_frame.append(f"{f if f < 976 else 0:03x}")
        # Who has the puck: $0AE7, an object number (15 = nobody), checked on the first SNES recording: it names the
        # player the puck moves with in all 608 clearly carried moments and reads 15 in 456 of 457 clearly loose
        # ones. Counted only with the puck within 30 of him (at stoppages it stays on the goalie who held it).
        holder = b(PUCK_HOLDER)
        near = holder < 12 and math.hypot(sg(OBJ_X + 28) - sg(OBJ_X + 2 * holder),
                                          sg(OBJ_Y + 28) - sg(OBJ_Y + 2 * holder)) <= 30
        self.match["owner"].append(holder if near else -1)
        # Where a shot is aimed (passdir, the stick's screen direction the shot code reads), whenever it changes
        v = b(PASS_DIR)
        if not self.match["aim"] or self.match["aim"][-1][1] != v:
            self.match["aim"].append([len(self.match["t"]) - 1, v])
        # The nets (objects 12, 13), whenever either moves: a skater can knock one off its spot (the faceoff then
        # comes out of the zone). [frame, top net x, y, bottom net x, y]
        nets = [sg(OBJ_X + 24), sg(OBJ_Y + 24), sg(OBJ_X + 26), sg(OBJ_Y + 26)]
        if not self.match["nets"] or self.match["nets"][-1][1:] != nets:
            self.match["nets"].append([len(self.match["t"]) - 1] + nets)
        mask = 0
        for k in range(PLAYERS):
            work = [w(a + 2 * k) for a in OBJ_WORK]
            if work != self.last_work[k]:
                self.match["work"].append([len(self.match["t"]) - 1, k] + work)
                self.last_work[k] = work
            self.match["pos"] += [sg(OBJ_X + 2 * k), sg(OBJ_Y + 2 * k)]
            face = w(OBJ_FACING + 2 * k) & 7
            spa, step = w(OBJ_ANIM + 2 * k), w(OBJ_ANIM_STEP + 2 * k)
            f = w(OBJ_FRAME + 2 * k)  # the game's own picture (the Genesis +$06)
            if spa >= 0x8000:
                self.spas.add(spa)
            self.facing.append(str(face))
            self.roster.append(DIGITS[min(b(OBJ_ROSTER + 2 * k), 35)])
            code = sg(OBJ_POSITION + 2 * k)
            self.role.append(str(code) if 0 <= code < 6 else "x")
            self.anim.append(f"{spa:04x}")
            self.frame.append(f"{f if f < 976 else 0:03x}")
            self.mirror.append("1" if w(OBJ_ATTRIBUTE + 2 * k) & 0x0800 else "0")
            if w(OBJ_FLAGS + 2 * k) & 0x0008:
                mask |= 1 << k
        self.match["ctrl"].append(mask)
        self.match["pad"].append(genesis_pad(w(PAD1)))
        self.match["pad2"].append(genesis_pad(w(PAD2)))
        words = [w(PAD1), w(PAD2)]
        if not self.match["padSnes"] or self.match["padSnes"][-1][1:] != words:
            self.match["padSnes"].append([len(self.match["t"]) - 1] + words)

    def result(self, cap, rom_path, name, home=None, away=None):
        """The match so far (fresh lists: the reader keeps its own)."""
        import zlib
        teams, rom = self.teams, self.rom
        match = {k: (list(v) if isinstance(v, list) else v) for k, v in self.match.items()}
        match["name"] = name
        stats = dict(self.stats, f=list(self.stats["f"]), home=[list(v) for v in self.stats["home"]],
                     away=[list(v) for v in self.stats["away"]])
        facing, roster, role, anim, frame, mirror, puck_frame = (self.facing, self.roster, self.role, self.anim,
                                                                  self.frame, self.mirror, self.puck_frame)
        spas = self.spas
        cap = _Kept(self.view.cap, list(self.keep), list(self.times))
        count = cap.count
        # The SNES puck leaves the stick for a moment hundreds of times a game while a player skates with it (the
        # byte drops to 15): gaps under 0.15 s with the same player before and after are taken as his.
        own, t = match["owner"], match["t"]
        i = 1
        while i < len(own):
            if own[i] < 0 <= own[i - 1]:
                j = i
                while j < len(own) and own[j] < 0 and t[j] - t[i - 1] < 150:
                    j += 1
                if j < len(own) and own[j] == own[i - 1]:
                    for q in range(i, j):
                        own[q] = own[j]
                i = j
            i += 1
        match.update(facing="".join(facing), roster="".join(roster), role="".join(role), anim="".join(anim),
                     frame="".join(frame), mirror="".join(mirror), puckFrame="".join(puck_frame))
        # The teams shown for most of the recording (at its very end the game may already have gone back to the menus).
        from collections import Counter
        home_id, away_id = Counter((cap.word(i, TEAM_IDS[0]), cap.word(i, TEAM_IDS[1]))
                                   for i in range(0, cap.count, max(1, cap.count // 200))).most_common(1)[0][0]
        match["team1"], match["team2"] = home or "Home", away or "Away"
        if home_id < len(teams) and away_id < len(teams):
            match["team1"], match["team2"] = home or teams[home_id]["name"], away or teams[away_id]["name"]
            match["abbr"] = [teams[home_id]["abbr"], teams[away_id]["abbr"]]
            match["rosters"] = [teams[home_id]["players"], teams[away_id]["players"]]
            match["palettes"] = [teams[home_id]["palettes"][0], teams[away_id]["palettes"][1]]
            add_hot_cold(cap, match)
        # Goals from the game's own scoring summary. The game raises the byte count before it has written the entry, so
        # each goal's moment is where the count first covers it, and its contents are read where the summary is
        # longest (the last such sample: complete, and before the game goes back to the menus and clears it). A goal is
        # a penalty-shot goal when that team's penalty-shot goals (STAT_ADDRESSES psGoals) went up within 3 s of it.
        counts = [cap.byte(i, SCORING_COUNT) for i in range(cap.count)]
        valid = [c if c % 6 == 0 and c <= 240 else -1 for c in counts]
        longest = max(valid) if valid else 0
        final = max((i for i, c in enumerate(valid) if c == longest), default=0)
        goals, tally = [], {}
        for at in range(0, longest, 6):
            i = next(i for i, c in enumerate(valid) if c > at)
            e = bytes(cap.byte(final, SCORING_LIST + at + j) for j in range(6))
            team = e[2] >> 7
            people = [e[3]] + [a for a in e[4:6] if a != 0xFF]
            for n, idx in enumerate(people):
                tally[(team, idx, n > 0)] = tally.get((team, idx, n > 0), 0) + 1
            strength = STRENGTH.get(e[2] & 0x7F, "?")
            kinds = [k for k in (strength,) if k in ("PPG", "SHG")] + (["5 on 3"] if strength == "PP2" else ["3 on 5"] if strength == "SH2" else [])
            ps = STAT_ADDRESSES["psGoals"] + 2 * team
            later = next((j for j in range(i, cap.count) if cap.ms(j) - cap.ms(i) > 3000), cap.count - 1)
            earlier = next((j for j in range(i, -1, -1) if cap.ms(i) - cap.ms(j) > 3000), 0)
            if cap.word(later, ps) > cap.word(earlier, ps):
                kinds.append("penalty shot")
            goals.append({"f": i, "team": team, "period": match["period"][i], "clock": match["clock"][i], "scorer": e[3],
                          "goals": tally[(team, e[3], False)], "assists": [[a, tally[(team, a, True)]] for a in people[1:]],
                          "kinds": kinds, "strength": strength})
        match["goals"] = goals
        match["stats"] = stats
        match["rules"] = read_rules(rom)
        match["penalties"], match["delayed"] = read_penalties(cap, count, match, match["rules"])
        match["rom"] = f"{zlib.crc32(rom):08x}"
        match["anims"] = {f"{spa:04x}": lists for spa in spas if (lists := animation_lists(rom, spa))}
        try:
            build_sprites(rom)
        except (struct.error, IndexError) as problem:
            print(f"no game sprites for {rom_path.name}: {problem}")
        build_sounds(rom)
        return match




def read_match(cap, rom_path, name, home=None, away=None):
    """The match file's contents from samples of SNES work RAM (cap: anything with count, ms(i), word(i, address),
    byte(i, address): a recording, or save states for a still picture). Positions, the puck, who is controlled,
    roster places, positions, facing, animations and their sprite frames, clock, period, score and shots, stats,
    goals and penalties."""
    reader = MatchReader(cap, rom_path)
    # The game ends where its numbers last stood: a research recording runs on into the menus, where the score and the
    # stats are cleared. Whether the per-player checks array is real is judged there (the most goals and shots).
    totals = [cap.word(i, STAT_ADDRESSES["goals"]) + cap.word(i, STAT_ADDRESSES["goals"] + 2)
              + sum(cap.word(i, a) + cap.word(i, a + 2) for a in SHOTS_BY_PERIOD) for i in range(cap.count)]
    end = max(range(cap.count), key=lambda i: (totals[i], i)) if cap.count else 0
    peak = max(totals) if totals else 0
    count = max(i for i, v in enumerate(totals) if v == peak) + 1 if peak else cap.count
    reader.feed(cap, final=True, count=count, checks_known=reader.checks_real(cap, end) if cap.count else False)
    return reader.result(cap, rom_path, name, home, away)


def read_penalties(cap, count, match, rules):
    """Penalties as the Genesis reader lists them: [{f (listed: the player went to the box), called (the foul),
    period, secs (into the period), team, code, idx}], and penalty shots awarded as 'delayed' flags with no penalty
    ({f, end, team: the team awarded it}) for the viewer's banner.
    A buffer entry (penalty number, object) appears at the foul; the player's box state turns into seconds when he
    is listed. In snes_2026-10-15_1755: Toronto Interference (P1 3:55), Toronto Interference and Pittsburgh Cross
    Check (P3 2:45, after one whistle), and the two penalty shots, all as the user saw them."""
    calls, open_calls, penalties, delayed = [], {}, [], []
    roster = lambda i, k: cap.byte(i, OBJ_ROSTER + 2 * k)
    in_box = [False] * 52
    for i in range(count):
        seen = set()
        for slot in range(0, 64, 2):
            code, obj = cap.byte(i, PEN_BUFFER + slot), cap.byte(i, PEN_BUFFER + slot + 1)
            if not code:
                continue
            key = (slot, code, obj & 0x7F)
            seen.add(key)
            if key not in open_calls and (obj & 0x7F) < 12 and code in rules and (rules[code]["min"] or code == PENALTY_SHOT):
                k = obj & 0x7F
                open_calls[key] = {"f": i, "code": code, "team": 0 if k < 6 else 1, "idx": roster(i, k)}
        for key in [k for k in open_calls if k not in seen]:
            call = open_calls.pop(key)
            call["end"] = i
            calls.append(call)
        for j in range(52):
            state = cap.word(i, BOX_STATE + 2 * j)
            boxed = 0 < state < 0x1000
            if boxed and not in_box[j]:
                team, idx = (0, j) if j < 26 else (1, j - 26)
                call = next((c for c in reversed(calls + list(open_calls.values())) if c["team"] == team and c["idx"] == idx
                             and c["code"] != PENALTY_SHOT and c["f"] <= i and not c.get("used")), None)
                if call:
                    call["used"] = True
                secs = cap.word(i, PERIOD_LENGTH) - match["clock"][i]
                penalties.append({"f": i, "period": match["period"][i], "secs": max(0, secs), "team": team,
                                  "code": call["code"] if call else 0x30, "idx": idx,
                                  **({"called": call["f"]} if call and call["f"] < i else {})})
            in_box[j] = boxed
    for call in calls + list(open_calls.values()):
        if call["code"] == PENALTY_SHOT:
            delayed.append({"f": call["f"], "end": call.get("end", count - 1), "team": 1 - call["team"]})
    return penalties, delayed


FRAME_COUNTER = 0x0764  # work RAM word counting frames (up 1-3 between the helper's reads, 92% of samples)
ROLLBACK_FRAMES = 30    # how far back a rollback can take the counter


class LivePlay:
    """Some of a recording's samples (live play), with the time between them closed up where paused samples were left
    out (`closed`: those samples; None = any left out)."""

    def __init__(self, cap, keep, closed=None):
        self.cap, self.keep, self.count = cap, keep, len(keep)
        self.times, t = [], 0
        for n, i in enumerate(keep):
            if n:
                gap = cap.ms(i) - cap.ms(keep[n - 1])
                skipped = range(keep[n - 1] + 1, i)
                close = any(q in closed for q in skipped) if closed is not None else bool(skipped)
                t += min(gap, 17) if close else gap
            self.times.append(t)

    def ms(self, i):
        return self.times[i]

    def word(self, i, address):
        return self.cap.word(self.keep[i], address)

    def byte(self, i, address):
        return self.cap.byte(self.keep[i], address)

    def raw(self, i, address, length):
        return self.cap.raw(self.keep[i], address, length) if hasattr(self.cap, "raw") else None


class SaveStates:
    """RetroArch Snes9x save states as samples of work RAM, a second apart: a still picture of the game from each, to
    check the SNES reading without a recording (tools/snes_preview.py)."""
    RAM = 68505 + 16  # the RAM block's data in a RetroArch state (a 16-byte wrapper, then the Snes9x snapshot)

    def __init__(self, paths):
        self.rams = [Path(p).read_bytes()[self.RAM:self.RAM + RAM_SIZE] for p in paths]
        self.count = len(self.rams)

    def ms(self, i):
        return 1000 * i

    def word(self, i, address):
        return struct.unpack_from("<H", self.rams[i], address)[0]

    def byte(self, i, address):
        return self.rams[i][address]


# ------------------------------------------------------------------------------------------------------- sprites
# The sprite set DrawSprite draws players, goalies, the puck and the nets from (SpriteFrames in the disassembly): a
# table of 4-byte offsets from $828000 (high word = banks on, low word = address in that bank - $8000; the first
# offset ends the table: 976 frames), then the frames through bank $8E. A frame: piece count, flags (bit 7 16x16
# tiles), tile count (8x8 tiles), four words (its box: left, right, top, bottom), two transfer sizes (the tiles of the
# upper and the lower tile row in video memory), the tiles' offset from the frame, four bytes, then 7-byte pieces
# (x, y: signed words from the player's position, y down; a word of tile number (bits 0-8: column = tile % 16, row
# = tile // 16, so a 16x16 piece is tiles N, N+1, N+16, N+17), palette (bits 9-11), h/v flip (bits 14, 15); a size
# byte, $FF 16x16 else 8x8), then the tiles, 32 bytes each in the SNES's planar 4-bit format. Earlier pieces are in
# front. Palette 4 is the team's uniform (Home's colours in palette 4, Away's in 5: DrawSprite flips the bit), used by
# 3945 of 4253 pieces; 2 is fixed (the puck and nets, frames 373-394; in the ROM at $D50B6 and the same in all 445
# save states); 0 and 1 change during play (goal light, logos ...), taken here as their most common colours there.
SPRITE_FRAMES = 0x828000
FIXED_PALETTES = (  # sprite palettes 2, 0, 1, as the library's fixed slots 1, 2, 3
    ["#c5e6ff", "#eeeeff", "#d5eeff", "#dedede", "#000000", "#b4b4b4", "#6a6a6a", "#4a4a4a", "#deb4b4", "#ff9494", "#de4a6a", "#6a94de", "#deb420", "#94b4ff", "#202020", "#94deff"],
    ["#411800", "#00ee00", "#299c00", "#ff9c00", "#520008", "#180831", "#6a0829", "#941808", "#b40808", "#000000", "#10b400", "#52cd00", "#000000", "#ee1008", "#ffe600", "#b4cd00"],
    ["#000000", "#ffffff", "#000000", "#000000", "#310000", "#000000", "#000000", "#000000", "#000000", "#080000", "#180000", "#080000", "#bdff4a", "#ac2000", "#000000", "#080000"],
)
PALETTE_SLOT = {4: 0, 5: 0, 2: 1, 0: 2, 1: 3}  # the library's slot 0 is the team's colours
# The puck's frames are stored with palette 0 but drawn with palette 2 (black puck, white shine, blue edge and shadow
# on the ice; with palette 0's colours they came out green and red). Frame 396 is its shadow, 397 the puck lying on
# the ice (the Genesis's 394 and 395: SNES frame 394 is the instant replay's crosshair corners, which the viewer drew
# under the puck until the library said which frames these are).
PUCK_FRAMES = range(395, 409)  # and the nets, 406-408 (406 a net seen from the front, 407 from behind): white and red
                               # in palette 2, green and orange in palette 0
PUCK_SHADOW_FRAME, PUCK_ON_ICE_FRAME = 396, 397


def sprite_frame(rom, n):
    """Frame n's picture: (left, top, rows of (slot, colour) pairs), offsets from the player's position."""
    base = file_offset(SPRITE_FRAMES)
    off = struct.unpack_from("<I", rom, base + 4 * n)[0]
    at = base + (off >> 16) * 0x8000 + (off & 0xFFFF)
    count = rom[at]
    upper, _, tiles_at = struct.unpack_from("<3H", rom, at + 12)
    upper //= 32  # tiles in the upper row
    pieces = [struct.unpack_from("<hhHB", rom, at + 22 + 7 * k) for k in range(count)]

    def tile(number):
        index = number % 16 + (upper if number // 16 else 0)
        data = rom[at + tiles_at + 32 * index:at + tiles_at + 32 * index + 32]
        return [[((data[2 * y] >> (7 - x)) & 1) | (((data[2 * y + 1] >> (7 - x)) & 1) << 1) |
                 (((data[16 + 2 * y] >> (7 - x)) & 1) << 2) | (((data[17 + 2 * y] >> (7 - x)) & 1) << 3) for x in range(8)]
                for y in range(8)]

    drawn = []
    for x, y, word, size in pieces:
        big = size == 0xFF
        n0 = word & 0x1FF
        side = 16 if big else 8
        rows = [[0] * side for _ in range(side)]
        for ty in range(2 if big else 1):
            for tx in range(2 if big else 1):
                t = tile(n0 + tx + 16 * ty)
                for yy in range(8):
                    rows[ty * 8 + yy][tx * 8:tx * 8 + 8] = t[yy]
        if word & 0x4000:
            rows = [r[::-1] for r in rows]
        if word & 0x8000:
            rows = rows[::-1]
        palette = 2 if n in PUCK_FRAMES else (word >> 9) & 7
        drawn.append((x, y, side, PALETTE_SLOT.get(palette, 1), rows))
    if not drawn:
        return 0, 0, [[(0, 0)]]
    left, top = min(d[0] for d in drawn), min(d[1] for d in drawn)
    right, bottom = max(d[0] + d[2] for d in drawn), max(d[1] + d[2] for d in drawn)
    canvas = [[(0, 0)] * (right - left) for _ in range(bottom - top)]
    for x, y, side, slot, rows in reversed(drawn):  # earlier pieces in front
        for yy in range(side):
            for xx in range(side):
                if rows[yy][xx]:
                    canvas[y - top + yy][x - left + xx] = (slot, rows[yy][xx])
    return left, top, canvas


def build_sprites(rom):
    """This ROM's sprite library (sprites/<crc32 of the ROM without a copier header>.js), in the Genesis library's
    format, so the viewer draws SNES players the same way."""
    import json
    import zlib
    from .common import ROOT
    rom = strip_header(rom)
    out = ROOT / "sprites" / f"{zlib.crc32(rom):08x}.js"
    if out.exists():
        return out
    count = struct.unpack_from("<I", rom, file_offset(SPRITE_FRAMES))[0] // 4
    frames = {}
    for n in range(count):
        left, top, canvas = sprite_frame(rom, n)
        frames[f"{n:03x}"] = {"x": left, "y": top, "w": len(canvas[0]), "h": len(canvas),
                             "p": "".join(chr(48 + 16 * slot + v) for row in canvas for slot, v in row)}
    library = {"version": 2, "system": NAME, "frames": frames, "fixed": [list(p) for p in FIXED_PALETTES],
               "puck": {"shadow": f"{PUCK_SHADOW_FRAME:03x}", "onIce": f"{PUCK_ON_ICE_FRAME:03x}"}}
    out.parent.mkdir(exist_ok=True)
    out.write_text("window.NHL94_SPRITES = " + json.dumps(library, separators=(",", ":")) + ";\n", encoding="utf-8")
    return out


# -------------------------------------------------------------------------------------------------------- sounds
# The sound chip's upload blocks (the NHL94SNES disassembly's tools/extract.py lists them): each is a 4-byte header
# and then one sample in the SNES's BRR format (9-byte blocks: a header byte of range, filter, loop and end bits, then
# 16 4-bit samples); all 45 decode as complete samples (3 of them tiny). They have no names in the disassembly, so
# they are numbered here; SOUND_ROLES says which plays for what once they are identified by ear.
SOUND_BLOCKS = [
    0x8ED897, 0x8F8000, 0x8FBB26, 0x90A120, 0x90E08C, 0x918000, 0x9199D2, 0x91C7A7, 0x91F2F9, 0x928000, 0x9293F3,
    0x92BB61, 0x92CECD, 0x92F18A, 0x9390FA, 0x93A18D, 0x93C20B, 0x93D187, 0x93DFAD, 0x93FAB1, 0x948D6F, 0x94A662,
    0x94B287, 0x94BEAC, 0x94CABF, 0x94E225, 0x94ED96, 0x958000, 0x958ABD, 0x959490, 0x959E48, 0x95B15C, 0x95C376,
    0x95CBEA, 0x95D3F2, 0x95EA63, 0x968000, 0x969190, 0x9696E3, 0x96AA64, 0x96DE60, 0x9782F8,
]
# Which plays for what, as the user identified them by ear (2026-10-15): 3 booing, 4 oooh, 8 cheer, 9 a pass or shot,
# 17 the puck off a post, 23 a check into the boards, 26 a big hit, 32 a slapshot, 35 the whistle, 11 probably the
# puck off the boards (34 is skating, not used).
SOUND_ROLES = {"crowdboo": "s03", "oooh": "s04", "crowdcheer": "s08", "pass": "s09", "shotfh": "s09", "shotbh": "s09",
               "slapshot": "s32", "post": "s17", "playerwall": "s23", "hithigh": "s26", "check": "s26", "check2": "s26",
               "whistle": "s35", "puckwall": "s11"}
SOUND_RATE = 11000  # samples a second: the user's setting by ear


def decode_brr(data):
    """BRR blocks -> signed 16-bit samples (the SNES's own filters), up to the block with the end bit."""
    out, p1, p2 = [], 0, 0
    for at in range(0, len(data) - 8, 9):
        header = data[at]
        shift, filt = header >> 4, (header >> 2) & 3
        for byte in data[at + 1:at + 9]:
            for nibble in (byte >> 4, byte & 15):
                s = nibble - 16 if nibble >= 8 else nibble
                s = (s << shift) >> 1 if shift <= 12 else (-2048 if s < 0 else 0)
                if filt == 1:
                    s += p1 + (-p1 >> 4)
                elif filt == 2:
                    s += 2 * p1 + ((-3 * p1) >> 5) - p2 + (p2 >> 4)
                elif filt == 3:
                    s += 2 * p1 + ((-13 * p1) >> 6) - p2 + ((3 * p2) >> 4)
                s = max(-32768, min(32767, s))
                p2, p1 = p1, s
                out.append(s)
        if header & 1:
            break
    return out


def build_sounds(rom):
    """sounds/<crc32 of the ROM without header>.js, in the Genesis sound library's format (8-bit PCM, base64)."""
    import base64
    import json
    import zlib
    from .common import ROOT
    rom = strip_header(rom)
    out = ROOT / "sounds" / f"{zlib.crc32(rom):08x}.js"
    if out.exists():
        return out
    samples = {}
    for n, address in enumerate(SOUND_BLOCKS, 1):
        at = file_offset(address)
        length = struct.unpack_from(">H", rom, at + 2)[0]
        pcm = decode_brr(rom[at + 4:at + 4 + length])
        peak = max(1, max(abs(v) for v in pcm))
        scale = min(1.0, 30000 / peak) / 256  # to 8 bits, louder samples kept from clipping
        samples[f"s{n:02d}"] = base64.b64encode(bytes(max(0, min(255, 128 + round(v * scale))) for v in pcm)).decode("ascii")
    out.parent.mkdir(exist_ok=True)
    out.write_text("window.NHL94_SOUNDS = " + json.dumps({"rate": SOUND_RATE, "format": "u8", "samples": samples, "roles": SOUND_ROLES},
                                                         separators=(",", ":")) + ";\n", encoding="utf-8")
    return out
