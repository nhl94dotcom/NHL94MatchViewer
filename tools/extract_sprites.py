"""Extracts every animation frame from an NHL '94 ROM into sprites/<ROM crc32>.js, which viewer.html draws players from.

ROM layout (all big-endian):
  $5DE84   tile bank: uncompressed 8x8 tiles, 32 bytes each (4 bits per pixel), numbered from 0
  $9E724   frame table: word N is the offset from $9E724 to frame N's pieces (frame 0 is "nothing"; 845 frames)
           each piece is 8 bytes: x, y (signed, relative to the player's position, y down), first tile number,
           attributes (bits 13-14 palette line, bit 12 vertical flip, bit 11 horizontal flip, bits 0-3 sprite size)
A player record's frame word (+$06) indexes this table directly. The whole picture is mirrored left-to-right
when bit 0 of record +$76 is clear.
"""
import argparse
import json
import os
import struct
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

# Where games, replays, sprites and settings live: the project folder, or NHL94_HOME (the packaged helper sets it to
# a folder in Documents, since a single .exe cannot write beside its own files).
ROOT = Path(os.environ["NHL94_HOME"]) if os.environ.get("NHL94_HOME") else Path(__file__).resolve().parent.parent
DEFAULT_ROM = Path(r"C:\Users\tdemorest\RetroArch-1.17-Win64\ROMs\Genesis\nhl94.bin")
TILES, FRAME_TABLE, FRAME_COUNT = 0x5DE84, 0x9E724, 846  # frames 1-845; the table has one more word, the end
RINK_PALETTE = 0x59924  # from the NOSE editor's game definitions
# Pixels are stored one character each: chr(48 + 16 * slot + colour), where the slot says whose colours to use.
SLOT = {2: 0, 0: 1, 1: 2}  # palette line 2 is replaced by the team's colours; lines 0 and 1 are fixed


def pieces(rom, n):
    start = FRAME_TABLE + struct.unpack_from(">H", rom, FRAME_TABLE + 2 * n)[0]
    end = FRAME_TABLE + struct.unpack_from(">H", rom, FRAME_TABLE + 2 * n + 2)[0]
    return [struct.unpack_from(">hhHH", rom, p) for p in range(start, end, 8)]


def verify(rom):
    """Raises ValueError if this ROM does not keep its frames where the original game does."""
    words = [struct.unpack_from(">H", rom, FRAME_TABLE + 2 * n)[0] for n in range(FRAME_COUNT + 1)]
    steady = all(b > a and (b - a) % 8 == 0 for a, b in zip(words[1:], words[2:]))
    if words[0] != 0 or words[1] != 2 * (FRAME_COUNT + 1) or not steady:
        raise ValueError("its animation frames are not where the original NHL '94 keeps them")
    last_tile = max(tile + (((attr >> 2) & 3) + 1) * ((attr & 3) + 1) for n in range(1, FRAME_COUNT) for _, _, tile, attr in pieces(rom, n))
    if TILES + 32 * last_tile > FRAME_TABLE:
        raise ValueError("its frame table points outside its tile bank")


def piece_pixels(rom, tile, attr):
    """Rows of colour indices for one piece, with its own flips applied."""
    w, h = ((attr >> 2) & 3) + 1, (attr & 3) + 1
    rows = [[0] * (w * 8) for _ in range(h * 8)]
    for col in range(w):  # tiles run down each column, then across
        for row in range(h):
            at = TILES + 32 * (tile + col * h + row)
            for y in range(8):
                for b in range(4):
                    v = rom[at + y * 4 + b]
                    rows[row * 8 + y][col * 8 + b * 2] = v >> 4
                    rows[row * 8 + y][col * 8 + b * 2 + 1] = v & 15
    if attr & 0x0800:
        rows = [r[::-1] for r in rows]
    if attr & 0x1000:
        rows = rows[::-1]
    return rows


def compose(rom, n):
    """Frame n as (left, top, rows of (slot, colour)); left/top are relative to the player's position."""
    parts = [(x, y, piece_pixels(rom, tile, attr), SLOT[(attr >> 13) & 3]) for x, y, tile, attr in pieces(rom, n)]
    left, top = min(p[0] for p in parts), min(p[1] for p in parts)
    right, bottom = max(p[0] + len(p[2][0]) for p in parts), max(p[1] + len(p[2]) for p in parts)
    canvas = [[(0, 0)] * (right - left) for _ in range(bottom - top)]
    for x, y, pix, slot in parts:  # earlier pieces are drawn on top
        for j, row in enumerate(pix):
            for i, v in enumerate(row):
                if v and not canvas[y - top + j][x - left + i][1]:
                    canvas[y - top + j][x - left + i] = (slot, v)
    return left, top, canvas


def check(rom, capture):
    """Compares the ROM's frames with what the game actually drew in a sprite capture."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from sprite_capture import BASE, SIZE, read
    from sprite_frames import AX, AY, TEAM_PALETTE, isolated, picture, players
    same = different = 0
    previous = {}
    for smp in read(capture / "sprites.bin"):
        everyone = players(smp)
        current = {}
        for k, role, x, y, sx, sy in everyone:
            rec = BASE + SIZE * k
            current[k] = (smp.word(rec + 0x06), smp.byte(rec + 0x76) & 1)
            if k not in previous or not isolated(smp, k, everyone) or not 1 <= previous[k][0] < FRAME_COUNT:
                continue
            pic = picture(smp, k, sx, sy, (TEAM_PALETTE[k // 6],))
            if pic is None:
                continue
            drawn = [bytes(r[c] for c in range(len(pic[0])) if any(row[c] for row in pic)) for r in pic if any(r)]
            left, top, canvas = compose(rom, previous[k][0])
            mine = [[v if slot == 0 else 0 for slot, v in row] for row in canvas]
            if not previous[k][1]:  # the game mirrors the picture when the bit is clear
                mine = [r[::-1] for r in mine]
            cols = [c for c in range(len(mine[0])) if any(r[c] for r in mine)]
            mine = [bytes(r[c] for c in cols) for r in mine if any(r)]
            if mine == drawn:
                same += 1
            else:
                different += 1
        previous = current
    print(f"check against {capture.name}: {same} of {same + different} on-screen pictures match the ROM frame exactly")


def library_path(rom):
    """Where a ROM's sprite library lives: sprites/<crc32 of the ROM>.js, since hacks repaint the players."""
    return ROOT / "sprites" / f"{zlib.crc32(rom):08x}.js"


def build(rom):
    """Writes the ROM's sprite library and returns its path. Raises ValueError for a ROM laid out differently."""
    verify(rom)
    frames = {}
    for n in range(1, FRAME_COUNT):
        left, top, canvas = compose(rom, n)
        frames[f"{n:03x}"] = {"x": left, "y": top, "w": len(canvas[0]), "h": len(canvas),
                             "p": "".join(chr(48 + 16 * slot + v) for row in canvas for slot, v in row)}

    # Palette lines 0 and 1 are the rink's 32 colours, the same for every team (0000BBB0GGG0RRR0 words).
    def colour(word):
        r, g, b = (((word >> shift) & 0xE) * 255 // 14 for shift in (0, 4, 8))
        return f"#{r:02x}{g:02x}{b:02x}"

    rink = [colour(struct.unpack_from(">H", rom, RINK_PALETTE + 2 * i)[0]) for i in range(32)]
    library = {"version": 2, "frames": frames, "fixed": [rink[:16], rink[16:]]}
    out = library_path(rom)
    out.parent.mkdir(exist_ok=True)
    out.write_text("window.NHL94_SPRITES = " + json.dumps(library, separators=(",", ":")) + ";\n", encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    ap.add_argument("--check", type=Path, help="a capture folder with sprites.bin to compare against")
    args = ap.parse_args()
    rom = args.rom.read_bytes()
    try:
        out = build(rom)
    except ValueError as problem:
        sys.exit(f"{args.rom.name}: {problem}")
    print(f"{FRAME_COUNT - 1} frames written to {out} ({out.stat().st_size / 1024:.0f} KB)")
    if args.check:
        check(rom, args.check)


if __name__ == "__main__":
    main()
