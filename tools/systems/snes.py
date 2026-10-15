"""NHL '94 on the Super Nintendo, in RetroArch with the Snes9x core. Not working yet: this holds what is known so far
(CLAUDE.md, "SNES version"), in the shape genesis.py has, to be filled in as the rest is found.

Known: the team stats and the scoring summary (from the user's save-state parser), the object arrays, clock,
period and controller (from the NHL94SNES disassembly, github.com/Mhopkinsinc/NHL94SNES, checked on save states),
and the ROM's teams (read_teams). Not known yet: who has the puck, the screen state (menus, pause), per-player
stats, the animation words, the sprites, and how to find work RAM inside the running Snes9x core.
"""
import struct
from pathlib import Path

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


ANIM_BANK = 0x9D0000    # the animation word (SPA) is an address in bank $9D: 8 direction pointers to (frame, time)
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


def read_match(cap, rom_path, name, home=None, away=None):
    """The match file's contents from samples of SNES work RAM (cap: anything with count, ms(i), word(i, address),
    byte(i, address): a recording, or save states for a still picture). Positions, the puck, who is controlled,
    roster places, positions, facing, animations and their sprite frames, clock, period, score and shots. Not yet:
    who has the puck (owner -1), the puck's height, per-player stats, penalties."""
    import zlib
    from .common import DIGITS, PLAYERS
    rom = strip_header(rom_path.read_bytes())
    teams = read_teams(rom_path)
    signed = lambda i, a: (lambda v: v - 0x10000 if v >= 0x8000 else v)(cap.word(i, a))
    match = {"version": 21, "name": name, "system": NAME, "positions": ["G", "LD", "RD", "LW", "C", "RW"],
             "t": [], "clock": [], "period": [], "score": [], "shots": [], "puck": [], "puckV": [], "lights": [],
             "pos": [], "ctrl": [], "owner": [], "posts": [], "delayed": [], "penalties": []}
    facing, roster, role, anim, frame, mirror, puck_frame, spas = [], [], [], [], [], [], [], set()
    for i in range(cap.count):
        match["t"].append(cap.ms(i))
        match["period"].append(cap.word(i, PERIOD))
        match["clock"].append(cap.word(i, CLOCK))
        match["score"] += [cap.word(i, STAT_ADDRESSES["goals"]), cap.word(i, STAT_ADDRESSES["goals"] + 2)]
        match["shots"] += [sum(cap.word(i, a + side) for a in SHOTS_BY_PERIOD) for side in (0, 2)]
        match["puck"] += [signed(i, OBJ_X + 28), signed(i, OBJ_Y + 28), 0]
        match["puckV"] += [round(signed(i, PUCK_VX) / 100), round(signed(i, PUCK_VY) / 100)]
        f = animation_frame(rom, cap.word(i, OBJ_ANIM + 28), cap.word(i, OBJ_ANIM_STEP + 28), cap.word(i, OBJ_FACING + 28))
        puck_frame.append(f"{f or 0:03x}")
        match["owner"].append(-1)
        mask = 0
        for k in range(PLAYERS):
            match["pos"] += [signed(i, OBJ_X + 2 * k), signed(i, OBJ_Y + 2 * k)]
            face = cap.word(i, OBJ_FACING + 2 * k) & 7
            spa, step = cap.word(i, OBJ_ANIM + 2 * k), cap.word(i, OBJ_ANIM_STEP + 2 * k)
            f = animation_frame(rom, spa, step, face)
            if f is not None:
                spas.add(spa)
            facing.append(str(face))
            roster.append(DIGITS[min(cap.byte(i, OBJ_ROSTER + 2 * k), 35)])
            code = signed(i, OBJ_POSITION + 2 * k)
            role.append(str(code) if 0 <= code < 6 else "x")
            anim.append(f"{spa:04x}")
            frame.append(f"{f or 0:03x}")
            mirror.append("1" if cap.word(i, OBJ_ATTRIBUTE + 2 * k) & 0x0800 else "0")
            if cap.word(i, OBJ_FLAGS + 2 * k) & 0x0008:
                mask |= 1 << k
        match["ctrl"].append(mask)
    match.update(facing="".join(facing), roster="".join(roster), role="".join(role), anim="".join(anim),
                 frame="".join(frame), mirror="".join(mirror), puckFrame="".join(puck_frame))
    last = cap.count - 1
    home_id, away_id = cap.word(last, TEAM_IDS[0]), cap.word(last, TEAM_IDS[1])
    match["team1"], match["team2"] = home or "Home", away or "Away"
    if home_id < len(teams) and away_id < len(teams):
        match["team1"], match["team2"] = home or teams[home_id]["name"], away or teams[away_id]["name"]
        match["abbr"] = [teams[home_id]["abbr"], teams[away_id]["abbr"]]
        match["rosters"] = [teams[home_id]["players"], teams[away_id]["players"]]
        match["palettes"] = [teams[home_id]["palettes"][0], teams[away_id]["palettes"][1]]
    match["rom"] = f"{zlib.crc32(rom):08x}"
    match["anims"] = {f"{spa:04x}": lists for spa in spas if (lists := animation_lists(rom, spa))}
    try:
        build_sprites(rom)
    except (struct.error, IndexError) as problem:
        print(f"no game sprites for {rom_path.name}: {problem}")
    build_sounds(rom)
    return match


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
        drawn.append((x, y, side, PALETTE_SLOT.get((word >> 9) & 7, 1), rows))
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
    library = {"version": 2, "system": NAME, "frames": frames, "fixed": [list(p) for p in FIXED_PALETTES]}
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
SOUND_ROLES = {}   # e.g. {"pass": "s07"}: filled in once the user has listened to them
SOUND_RATE = 16000  # a starting guess; the viewer's sound panel adjusts it


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
