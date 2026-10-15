"""NHL '94 on the Sega Genesis, in RetroArch with the Genesis Plus GX core: where things are in the game's memory and
ROM, how to find that memory in the running emulator, and how to turn a recording into a match file.

Everything here was worked out on the Genesis version; CLAUDE.md has how each fact was found and checked.
The analysis that follows (shots, passes, turnovers ... in export_match.py) and the viewer are shared with other
systems, and only see the match file this module builds.
"""
import json
import re
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

from .common import DIGITS, PLAYERS, ROOT, overall
from . import process

NAME = "genesis"
RAM_SIZE = 0x10000  # work RAM, $FF0000-$FFFFFF
BYTE_SWAP = 1       # the emulator keeps each 16-bit word in host order: the byte at Genesis address A is at A ^ 1
ROM_GLOB = "*.bin"

FULL = 8 + 0x10000  # one full.bin snapshot
OLD_BLOCKS = [[0xB000, 0x900], [0xC400, 0x800]]  # fast.bin layout before capture.json existed
BASE, SIZE = 0xB04A, 0x80  # record 0 start, record size
PLAYERS, PUCK = 12, 14
FRAME, X, Y, Z, ROLE, FACING, ANIM, FLAGS, ROSTER, HAND = 0x06, 0x1C, 0x20, 0x24, 0x35, 0x55, 0x58, 0x62, 0x66, 0x76
OWNED, OWNER = 0x60, 0x61  # puck record: $00 while a player has it, and that player's record number
HOME_TEAM, AWAY_TEAM = 0xC6F6, 0xCA5A
# Each team's stat block ($364 bytes, cleared before a game). Team words, then byte arrays by roster index.
STAT_BLOCKS = (0xC6CE, 0xCA32)  # Home, Away
# shots, goals, faceoffs won, checks, passes tried, passes made, attack-zone seconds,
# breakaways tried, breakaway goals, one-timers tried, one-timer goals, penalty shots tried, penalty-shot goals,
# power-play goals, power plays, penalties, penalty minutes, shorthanded goals. The power-play, penalty and
# shorthanded offsets come from the user's old save-state parser (reference/genesis_savestate_stats.txt), which also confirms the rest.
TEAM_STATS = (0x00, 0x0C, 0x0E, 0x10, 0x12, 0x14, 0x0A, 0x358, 0x35A, 0x35C, 0x35E, 0x360, 0x362, 0x02, 0x04, 0x06, 0x08, 0x356)
GOALS, ASSISTS, SHOTS, CHECKS_OR_PIM, HITS_TAKEN = 0xB4, 0xCE, 0xE8, 0x102, 0x11C  # one byte per roster index
ICE_TIME, ENERGY = 0x136, 0x32  # one word per roster index: game seconds played; energy 0-16 in the high byte
PENALTY = 0x66  # one word per roster index: $FFxx = not penalized; else high byte $20 = called, play still on
                # (delayed), $00 = serving; low byte = seconds left to serve
DELAYED = 0x26  # stat-block byte: $FF while this team has a delayed penalty coming (the other side has fouled)
PENALTY_LIST, RULES = 0xC5DC, 0x18E0C  # work RAM penalty summary; ROM table of rule messages (penalty names)
PIM_CODE = 0x12302  # the game adds penalty minutes here; smozROM's checks hack replaces it with two NOPs
PAD1 = 0xBEEF  # controller 1, held buttons: $80 Start, $40 A, $20 C, $10 B, $08 Right, $04 Left, $02 Down, $01 Up
TEAM_TABLE = 0x30E
RINK_LOGO_TABLE_POINTER = 0xFEA5A  # holds the address of a table of one logo address per team
DEFAULT_ROM = Path(r"C:\Users\USER\RetroArch-1.17-Win64\ROMs\Genesis\nhl94.bin")

# The animation words (record +$58) the analysis needs, by name (see the table in CLAUDE.md).
ACTIONS = {
    "shoot": {"07fc", "092e"},        # C with the puck (two animations, rules the same)
    "pass": {"0718", "078a"},         # B with the puck
    "goalie_pass": {"0366"},          # B as the goalie with the puck
    "poke": {"0b24"},                 # B without the puck, near the carrier
    "hook": {"1122"},                 # A without the puck
    "lunge": {"0c5e"},                # C without the puck: speed burst / body-check lunge
    "down": {"0dd8", "0d26"},         # knocked down
    "dive": {"02f4"},                 # A as the goalie
    "goalie_save": {"148e"},          # a save attempt (also C while controlling the goalie)
}


def fixed(data, pos):
    """A 16.16 position in host order (the integer word first), rounded to a tenth."""
    whole, frac = struct.unpack_from("<hH", data, pos)
    return round(whole + frac / 65536, 1)


# ----------------------------------------------------------------------------------------- the running emulator
class Emulator(process.Attached):
    """NHL '94 (or any Genesis game) loaded in Genesis Plus GX: its work RAM and its cartridge, read-only.

    Found by scanning the core's writable data for the 68000 memory map: 32 consecutive 40-byte entries ($E0-$FF)
    sharing one base pointer (work RAM), confirmed by the cartridge header ("ESAG", byte-swapped "SEGA") behind
    entry 0. Host memory keeps each 16-bit word in native order, so a single byte at Genesis address A is at offset
    A XOR 1, and a little-endian word read gives the Genesis value."""
    system = NAME
    module_prefix = "genesis_plus_gx"

    def find(self, start, end):
        for base, data in self.writable_regions(start, end):
            for i in range(0xE0 * 40, len(data) - 40 * 32 + 1, 8):
                p = struct.unpack_from("<Q", data, i)[0]
                if not start <= p < end:
                    continue
                if all(struct.unpack_from("<Q", data, i + 40 * k)[0] == p for k in range(1, 32)):
                    rom = struct.unpack_from("<Q", data, i - 0xE0 * 40)[0]
                    if self.raw(rom + 0x100, 4) == b"ESAG":
                        return p, rom
        return None

    def byte(self, offset):
        data = self.read(offset ^ 1, 1)
        return data[0] if data else None

    def rom_fingerprint(self):
        """CRC-32 of the cartridge's first and second megabytes as the ROM file has them (the emulator keeps each
        pair of bytes swapped), as the recorder stores it so the converter can find the ROM file."""
        out = []
        for part in range(2):
            data = self.raw(self.rom + part * 0x100000, 0x100000)
            if data is None:
                return None
            swapped = bytearray(len(data))
            swapped[0::2], swapped[1::2] = data[1::2], data[0::2]
            out.append(f"{zlib.crc32(bytes(swapped)):08x}")
        return out

    def dump_rom(self):
        """Copy the cartridge out of the emulator into roms/<fingerprint>.bin (once per ROM): (path, fingerprint),
        path None if it could not be copied."""
        fp = self.rom_fingerprint()
        if not fp:
            return None, None
        path = ROOT / "roms" / f"{fp[0]}_{fp[1]}.bin"
        if not path.exists():
            header = self.raw(self.rom + 0x1A0, 8)
            if not header:
                return None, fp
            swapped = bytes(header[i ^ 1] for i in range(8))
            start, end = struct.unpack(">II", swapped)
            size = min(max(end + 1, 0x100000), 0x400000)
            data = self.raw(self.rom, size)
            if not data:
                return None, fp
            rom = bytearray(size)
            rom[0::2], rom[1::2] = data[1::2], data[0::2]
            if zlib.crc32(bytes(rom[:0x100000])) != int(fp[0], 16):
                return None, fp
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(bytes(rom))
        return path, fp


def attach():
    """The running emulator with a Genesis game loaded, or None."""
    return Emulator.attach()


# ------------------------------------------------------------------------------------------- what the helper reads
BLOCKS = [(0xB000, 0x1000), (0xC400, 0xA00)]  # what each sample keeps, as tools/nhl94_record.ps1 does
SCREEN = 0xFFF7          # 0 = the game itself; 15 menus; 80 pause menu; 100 instant replay
MENUS = (1, 15)
PERIOD, CLOCK = 0xC466, 0xC468
HOME_SCORE, AWAY_SCORE = 0xC6DA, 0xCA3E
HOME_TEAM_ID, AWAY_TEAM_ID = 0xC6F7, 0xCA5B


class View:
    """What the game is doing, from one read of the blocks we record plus the screen byte."""

    def __init__(self, emu):
        self.blocks = [emu.read(start, length) for start, length in BLOCKS]
        screen = emu.read(SCREEN ^ 1, 1)
        if any(b is None for b in self.blocks) or screen is None:
            raise ConnectionError("the emulator went away")
        self.screen = screen[0]
        a, c = self.blocks
        word = lambda block, offset: struct.unpack_from("<H", block, offset)[0]
        self.period, self.clock = word(c, PERIOD - 0xC400), word(c, CLOCK - 0xC400)
        self.score = (word(c, HOME_SCORE - 0xC400), word(c, AWAY_SCORE - 0xC400))
        self.teams = (c[(HOME_TEAM_ID ^ 1) - 0xC400], c[(AWAY_TEAM_ID ^ 1) - 0xC400])
        rosters = [a[((BASE + SIZE * k + ROSTER) ^ 1) - 0xB000] for k in range(12)]
        self.on_ice = any(r != 0xFF for r in rosters[:6]) and any(r != 0xFF for r in rosters[6:])
        self.in_menus = self.screen in MENUS
        self.in_game = self.screen == 0  # play, whistles, intermissions (not the pause menu or a replay)

    @property
    def live(self):
        return self.in_game and self.on_ice

    def describe(self):
        return f"P{min(self.period, 2) + 1} {self.clock // 60}:{self.clock % 60:02d}, {self.score[0]}-{self.score[1]}"


# ------------------------------------------------------------------------------------------------------ the ROM
def colour(word):
    """Genesis colour word (0000BBB0GGG0RRR0) -> #rrggbb."""
    r, g, b = (((word >> shift) & 0xE) * 255 // 14 for shift in (0, 4, 8))
    return f"#{r:02x}{g:02x}{b:02x}"


def find_rom(capture):
    """The ROM a capture was played on, by the fingerprint the recorder stored, looked for beside the default ROM."""
    layout = capture / "capture.json"
    stored = json.loads(layout.read_text()).get("rom_crc32") if layout.exists() else None
    if not stored:
        return DEFAULT_ROM, "assumed; this capture does not say which ROM was played"
    first, second = (int(part, 16) for part in stored)
    # The helper copies the ROM out of the emulator into roms/ (named by its fingerprint); then RetroArch's ROM folder.
    candidates = sorted((ROOT / "roms").glob("*.bin")) + (sorted(DEFAULT_ROM.parent.glob(ROM_GLOB)) if DEFAULT_ROM.parent.exists() else [])
    for path in candidates:
        data = path.read_bytes()
        # The recorder fingerprints the first megabyte and the second; a one-megabyte ROM has no second.
        if zlib.crc32(data[:0x100000]) == first and (len(data) <= 0x100000 or zlib.crc32(data[0x100000:0x200000]) == second):
            return path, "matched to the recording"
    return DEFAULT_ROM, f"assumed; no ROM in {DEFAULT_ROM.parent} matches the one that was recorded"


def team_count(rom):
    """28 for the original game, 30 for the 30-team hack, 64 for NHL 94: EVO (as the NOSE editor tells them apart)."""
    if rom[0x120:0x12B] == b"NHL 94: EVO":
        return 64
    code = re.match(r"GM T-50656( -|-F)([03])", rom[0x180:0x18E].decode("latin-1"))
    return 30 if code and code.group(2) == "3" else 28



def rink_logo(rom, team):
    """A team's centre-ice logo: 6 x 4 tiles of colour indices into its home palette, as one hex digit per pixel."""
    block = struct.unpack_from(">I", rom, struct.unpack_from(">I", rom, RINK_LOGO_TABLE_POINTER)[0] + 4 * team)[0]
    tiles = block + 10
    if not 0 < block and tiles + 24 * 32 <= len(rom):
        return None
    rows = [[0] * 48 for _ in range(32)]
    for t in range(24):
        for y in range(8):
            for x in range(4):
                v = rom[tiles + 32 * t + y * 4 + x]
                rows[(t // 6) * 8 + y][(t % 6) * 8 + 2 * x] = v >> 4
                rows[(t // 6) * 8 + y][(t % 6) * 8 + 2 * x + 1] = v & 15
    return {"w": 48, "h": 32, "p": "".join(f"{v:x}" for row in rows for v in row)}


def read_teams(rom_path):
    """Team names, rosters, palettes and logos from the ROM. Roster order matches the index in each player record."""
    rom = rom_path.read_bytes()
    teams = []
    for k in range(team_count(rom)):
        team = struct.unpack_from(">I", rom, TEAM_TABLE + 4 * k)[0]
        players_off, _, names_off = struct.unpack_from(">3H", rom, team)
        # The first players on a roster are its goalies, up to the last of four goalie values that is not zero.
        nibbles = [n for byte in rom[team + 0x50:team + 0x52] for n in (byte >> 4, byte & 15)]
        goalies = max((i + 1 for i, n in enumerate(nibbles) if n), default=0)
        players, off = [], team + players_off
        while True:
            length = struct.unpack_from(">H", rom, off)[0]
            if not 2 < length <= 40:
                break
            name = rom[off + 2:off + length].decode("latin-1").rstrip("\x00")
            # After the name: the jersey number as decimal digits, then fourteen ratings of 0-15, two to a byte.
            attrs = [n for byte in rom[off + length + 1:off + length + 8] for n in (byte >> 4, byte & 15)]
            goalie = len(players) < goalies
            players.append({"name": name, "num": int(f"{rom[off + length]:02x}"), "a": attrs, "g": goalie, "ovr": overall(attrs, goalie)})
            off += length + 8
        length = struct.unpack_from(">H", rom, team + names_off)[0]
        # Two 16-colour palettes per team, as the game loads them: +$0C when playing at home, +$2C when away.
        palettes = [[colour(struct.unpack_from(">H", rom, team + start + 2 * i)[0]) for i in range(16)] for start in (0x0C, 0x2C)]
        try:
            logo = rink_logo(rom, k)
        except (struct.error, IndexError):
            logo = None  # a ROM that keeps its logos somewhere this does not know
        teams.append({"name": rom[team + names_off + 2:team + names_off + length].decode("latin-1").rstrip("\x00"), "players": players,
                      "palettes": palettes, "logo": logo, "abbr": team_abbr(rom, team + names_off + length)})
    return teams


def team_abbr(rom, at):
    """The team's abbreviation (BOS, STL): the second of its length-prefixed name strings (city, abbreviation,
    nickname, arena), starting at `at`. Empty if it does not look like one."""
    length = struct.unpack_from(">H", rom, at)[0]
    return rom[at + 2:at + length].decode("latin-1").rstrip("\x00") if 2 < length < 12 else ""


def animation_table(rom):
    """The game's animation scripts, which the player record's animation word (+$58) is an offset into. Each starts
    with 8 word offsets (from the script's start), one per direction faced, to a list of (frame, duration) word pairs
    ended by a negative duration. The table is found by the standing animation ($050C): frames 1, 6, 11 ... 36, one
    pair per direction, so its offsets read 18, 22 ... 46. Returns {word as 4 hex digits: 8 lists of frames}, used by
    the viewer to redraw a player facing another way when the view is turned; {} if the table is not there."""
    word = lambda a: struct.unpack_from(">H", rom, a)[0]
    base = next((b for b in range(0, len(rom) - 0x2000, 2)
                 if all(word(b + 0x50C + 2 * e) == 18 + 4 * e for e in range(8)) and word(b + 0x50C + 18) == 1), None)
    if base is None:
        return {}

    def script(v):
        offsets = [word(base + v + 2 * e) for e in range(8)]
        if min(offsets) != 18 or max(offsets) > 0x600 or any(o % 2 for o in offsets):
            return None
        dirs = []
        for o in offsets:
            at, frames = base + v + o, []
            while True:
                frame, duration = word(at), struct.unpack_from(">h", rom, at + 2)[0]
                if not 0 < frame < 900 or len(frames) >= 64:
                    return None
                frames.append(frame)
                at += 4
                if duration < 0:
                    break
            dirs.append(frames)
        return dirs

    return {f"{v:04x}": dirs for v in range(2, 0x2000, 2) if (dirs := script(v))}


def build_sprites(rom):
    """This ROM's sprite library (sprites/<crc32>.js), built the first time it is seen."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import extract_sprites
    if not extract_sprites.library_path(rom).exists():
        extract_sprites.build(rom)


# ------------------------------------------------------------------------------------ a recording -> a match file
def read_match(cap, rom_path, name, home=None, away=None):
    """The match file's contents from a recording (cap: export_match.Capture) and the ROM it was played on. The
    shared analysis (shots, passes, goals ...) is added afterwards by export_match.main."""
    has_pad = cap.offset(PAD1) is not None

    match = {"version": 21, "name": name, "positions": ["G", "LD", "RD", "LW", "C", "RW"],
             "t": [], "clock": [], "period": [], "score": [], "shots": [], "puck": [], "puckV": [], "lights": [], "pos": [], "ctrl": [], "owner": []}
    if has_pad:
        match["pad"] = []
    facing, roster, anim, role, frame, mirror, puck_frame = [], [], [], [], [], [], []
    match["posts"] = []  # frames where the puck came off a goal post
    # Stat snapshots: whenever a counted stat changes, and once a second for ice time and energy.
    stats = {"f": [], "home": [], "away": []}
    last_counts, last_stat_ms = None, -10_000
    penalties = []
    delayed, open_delayed = [], [None, None]
    last_post = -10_000
    team_ids = Counter()
    previous = None
    for i in range(cap.count):
        # Identical consecutive samples (a paused game, or two reads of one frame) are stored once.
        key = (cap.raw(i, BASE, SIZE * 16), cap.raw(i, 0xC466, 4), cap.byte(i, PAD1) if has_pad else 0)
        if key == previous:
            continue
        previous = key
        team_ids[(cap.word(i, HOME_TEAM) & 0xFF, cap.word(i, AWAY_TEAM) & 0xFF)] += 1
        match["t"].append(cap.ms(i))
        match["period"].append(cap.word(i, 0xC466))
        match["clock"].append(cap.word(i, 0xC468))
        match["score"] += [cap.word(i, 0xC6DA), cap.word(i, 0xCA3E)]
        match["shots"] += [cap.word(i, 0xC6CE), cap.word(i, 0xCA32)]
        puck = BASE + SIZE * PUCK
        match["puck"] += [cap.fixed(i, puck + X), cap.fixed(i, puck + Y), cap.fixed(i, puck + Z)]
        # The puck's picture (frames 395-404 of the sprite table; 395 and 399 on the ice, the rest tumbling in the air).
        # Its height reads -256 while the game hides it, at stoppages before the faceoff.
        puck_frame.append(f"{cap.word(i, puck + FRAME) & 0xFFF:03x}")
        # Its speed words (+$28 X, +$2A Y, signed, same directions as the position), in hundreds: wrist shots peak at
        # about 11400-13700, slapshots 15000-23600.
        speed_x, speed_y = struct.unpack("<hh", cap.raw(i, puck + 0x28, 4))
        match["puckV"] += [round(speed_x / 100), round(speed_y / 100)]
        # Record 15, the puck's shadow, becomes the goal light after a goal: frames 563-576 (a red lamp, its flash and
        # then its beam turning), for 7-9 seconds, at the end boards behind the net or in the net.
        light = BASE + SIZE * 15
        light_frame = cap.word(i, light + FRAME) & 0xFFF
        if 563 <= light_frame <= 576:
            match["lights"] += [len(match["t"]) - 1, cap.fixed(i, light + X), cap.fixed(i, light + Y),
                                cap.fixed(i, light + Z), light_frame]
        owner = cap.byte(i, puck + OWNER)
        match["owner"].append(owner if cap.byte(i, puck + OWNED) == 0 and owner < PLAYERS else -1)
        # A post: the loose puck turns back out of the end zone right beside a post (about 20 units either side of
        # the middle, on the goal line). Found from a post shot the user saw in capture5_league30 at 2:57 of period 1;
        # across all captures the rule fires only three times.
        if i and cap.byte(i, puck + OWNED) != 0 and cap.ms(i) - last_post > 1000:
            px, py, vx, vy = struct.unpack("<hxxhxxxxxxhh", cap.raw(i, puck + X, 16))
            before = struct.unpack("<hh", cap.raw(i - 1, puck + 0x28, 4))
            fresh = (vx, vy) != before or cap.byte(i - 1, puck + OWNED) == 0
            if fresh and 14 <= abs(px) <= 28 and 252 <= abs(py) <= 272 and vy * py < 0 and abs(vx) + abs(vy) >= 1500:
                match["posts"].append(len(match["t"]) - 1)
                last_post = cap.ms(i)
        if has_pad:
            match["pad"].append(cap.byte(i, PAD1))
        mask = 0
        for k in range(PLAYERS):
            rec = BASE + SIZE * k
            match["pos"] += [cap.fixed(i, rec + X), cap.fixed(i, rec + Y)]
            facing.append(str(cap.byte(i, rec + FACING) & 7))
            roster.append(DIGITS[min(cap.byte(i, rec + ROSTER), 35)])
            anim.append(f"{cap.word(i, rec + ANIM):04x}")
            frame.append(f"{cap.word(i, rec + FRAME) & 0xFFF:03x}")
            mirror.append("0" if cap.byte(i, rec + HAND) & 1 else "1")
            code = cap.byte(i, rec + ROLE)
            role.append(str(code) if code < 6 else "x")
            if cap.byte(i, rec + FLAGS) & 0x08:
                mask |= 1 << k
        match["ctrl"].append(mask)
        vectors, counts = [], []
        for block in STAT_BLOCKS:
            vector = [cap.word(i, block + o) for o in TEAM_STATS]
            for idx in range(26):
                vector += [cap.byte(i, block + GOALS + idx), cap.byte(i, block + ASSISTS + idx), cap.byte(i, block + SHOTS + idx),
                           cap.byte(i, block + CHECKS_OR_PIM + idx), cap.byte(i, block + HITS_TAKEN + idx),
                           cap.word(i, block + ICE_TIME + 2 * idx), cap.byte(i, block + ENERGY + 2 * idx),
                           cap.word(i, block + PENALTY + 2 * idx)]
            vectors.append(vector)
            n = len(TEAM_STATS)
            counts.append([v for j, v in enumerate(vector) if j < n or (j - n) % 8 not in (5, 6)])
        # The penalty summary: a byte count, then 4 bytes per penalty in the order called:
        # (period << 14 | seconds into the period), team ($80 = Away) | rule code, roster index.
        # Delayed penalties: the benefiting team's flag goes up at the moment of the foul, and down when play
        # resumes. The offender is only written to the summary after the whistle; it is matched up below.
        for team, block in enumerate(STAT_BLOCKS):
            up = cap.byte(i, block + DELAYED) == 0xFF
            if up and open_delayed[team] is None:
                open_delayed[team] = {"f": len(match["t"]) - 1, "team": team}
            elif not up and open_delayed[team] is not None:
                open_delayed[team]["end"] = len(match["t"]) - 1
                delayed.append(open_delayed[team])
                open_delayed[team] = None
        listed = cap.word(i, PENALTY_LIST)
        if listed < 4 * len(penalties) or listed > 240:
            penalties.clear()  # a new game started, or the list is not set up yet
        while listed >= 4 * (len(penalties) + 1):
            at = PENALTY_LIST + 2 + 4 * len(penalties)
            when = (cap.byte(i, at) << 8) | cap.byte(i, at + 1)
            code = cap.byte(i, at + 2)
            # f = -1 marks penalties already listed when the recording began
            penalties.append({"f": len(match["t"]) - 1 if len(match["t"]) > 1 else -1, "period": when >> 14, "secs": when & 0x3FFF,
                              "team": code >> 7, "code": code & 0x7F, "idx": cap.byte(i, at + 3)})
        if counts != last_counts or cap.ms(i) - last_stat_ms >= 1000:
            stats["f"].append(len(match["t"]) - 1)
            stats["home"].append(vectors[0])
            stats["away"].append(vectors[1])
            last_counts, last_stat_ms = counts, cap.ms(i)
    match["facing"] = "".join(facing)
    match["roster"] = "".join(roster)  # one base-36 digit per player per frame: index into that team's roster
    match["role"] = "".join(role)  # one character per player per frame: index into "positions", or x when off the ice
    for team in (0, 1):
        if open_delayed[team] is not None:
            delayed.append({**open_delayed[team], "end": len(match["t"]) - 1})
    # A penalty listed while the other team's delayed flag was up was called when that flag went up.
    for p in penalties:
        for d in delayed:
            if d["team"] == 1 - p["team"] and d["f"] <= p["f"] <= d["end"] and not d.get("matched"):
                p["called"], d["matched"] = d["f"], True
                break
    match["delayed"] = delayed
    match["penalties"] = penalties
    match["frame"] = "".join(frame)  # three hex digits per player per frame: the animation frame, for the sprite library
    match["puckFrame"] = "".join(puck_frame)  # three hex digits per frame: the puck's picture
    match["mirror"] = "".join(mirror)  # 1 where the game draws that frame mirrored left-to-right
    match["anim"] = "".join(anim)  # four hex digits per player per frame: the animation word at record +$58

    home_id, away_id = team_ids.most_common(1)[0][0]
    match["team1"], match["team2"] = home or "Home", away or "Away"
    if rom_path.exists():
        teams = read_teams(rom_path)
        if home_id < len(teams) and away_id < len(teams):
            match["team1"], match["team2"] = home or teams[home_id]["name"], away or teams[away_id]["name"]
            match["abbr"] = [teams[home_id]["abbr"], teams[away_id]["abbr"]]
            match["rosters"] = [teams[home_id]["players"], teams[away_id]["players"]]
            match["palettes"] = [teams[home_id]["palettes"][0], teams[away_id]["palettes"][1]]
            # Stats per snapshot: the team values, then 8 per player (goals, assists, shots, checks or PIM, hits taken,
            # ice time, energy, penalty word) for each roster place.
            sizes = (len(TEAM_STATS) + 8 * len(teams[home_id]["players"]), len(TEAM_STATS) + 8 * len(teams[away_id]["players"]))
            stats["n"], stats["p"] = len(TEAM_STATS), 8
            rom_bytes = rom_path.read_bytes()
            # Penalty names and lengths: the rule-message table (the NOSE editor's rulesOffset). A code is twice the
            # rule number; each rule starts with two bytes, the second being the minutes, then its name.
            rules = {}
            for number in range(1, 31):
                at = RULES + struct.unpack_from(">H", rom_bytes, RULES + 2 * number)[0]
                length = struct.unpack_from(">H", rom_bytes, at + 2)[0]
                if 2 < length < 30:
                    minutes = rom_bytes[at + 1]
                    rules[2 * number] = {"name": rom_bytes[at + 4:at + 2 + length].decode("latin-1").rstrip("\x00"),
                                         "min": minutes if minutes <= 10 else 0}
            match["rules"] = rules
            stats["home"] = [v[:sizes[0]] for v in stats["home"]]
            stats["away"] = [v[:sizes[1]] for v in stats["away"]]
            rom_bytes = rom_path.read_bytes()
            stats["x"] = "Checks" if rom_bytes[PIM_CODE:PIM_CODE + 4] == bytes.fromhex("4e714e71") else "PIM"
            match["stats"] = stats
            if teams[home_id]["logo"]:
                match["logo"] = teams[home_id]["logo"]  # drawn at centre ice in the home palette
        # Players are drawn from this ROM's own sprites; build its library the first time it is seen.
        rom = rom_path.read_bytes()
        match["rom"] = f"{zlib.crc32(rom):08x}"
        match["anims"] = animation_table(rom)
        try:
            build_sprites(rom)
        except ValueError as problem:
            print(f"no game sprites for {rom_path.name}: {problem}")
    else:
        print(f"ROM not found at {rom_path}; exporting without player names")
    return match
