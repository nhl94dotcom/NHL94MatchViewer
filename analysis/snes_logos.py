"""The SNES team logos, from the player's own ROM (2026-11-04): the TeamLogos sprite set and LogoPaletteTable, the logos and colours the game itself draws on its player cards and scouting
screens. (The centre-ice tiles are coloured by the rink's palette, so they're not used.) The disassembly's tools/snesgfx.py unpacks them; clone in %USERPROFILE%\\NHL94_disasm, read only.
logos(rom path) gives {abbr: (width, height, [(r, g, b, a) ...])}. Copyrighted game art: never commit the pictures.
python analysis/snes_logos.py <out.png>     a contact sheet, to check them"""
import importlib.util
import re
import struct
import sys
import zlib
from pathlib import Path

DISASM = Path.home() / "NHL94_disasm" / "NHL94SNES"
SPRITES = 0x81ABDE      # TeamLogos.spr.huf
PALETTES = 0x9C8497     # LogoPaletteTable: a 4-byte pointer per frame of the set


def tool():
    sys.path.insert(0, str(DISASM / "tools"))           # snesgfx imports its neighbour rompath
    spec = importlib.util.spec_from_file_location("snesgfx", DISASM / "tools" / "snesgfx.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def palette_names():
    """{LoROM address of a logo palette: team}, from the disassembly's list of the ROM's assets."""
    text = (DISASM / "tools" / "extractAssets94s.js").read_text(encoding="utf-8")
    return {int(m.group(2), 16): m.group(1) for m in re.finditer(r"\['LogoPalette([A-Z]+)\.pal',\s*0x([0-9A-Fa-f]+),", text)}


def logos(rom_path):
    gfx = tool()
    rom = rom_path.read_bytes()
    if len(rom) % 0x8000 == 512:
        rom = rom[512:]
    names = palette_names()
    frames = gfx.sprite_frames(gfx.unpack(rom, gfx.lorom_offset(SPRITES))[0])
    out = {}
    for n, (pieces, vram) in enumerate(frames):
        q = gfx.lorom_offset(PALETTES) + 4 * n
        at = (rom[q] | rom[q + 1] << 8 | rom[q + 2] << 16) | 0x800000
        team = names.get(at)
        if team is None:
            continue
        pal = [gfx.snes_rgb(struct.unpack_from("<H", rom, gfx.lorom_offset(at) + 2 * i)[0]) for i in range(16)]
        dots = {}
        for x, y, t, size in pieces:
            flip_x, flip_y, tile, sz = t & 0x4000, t & 0x8000, t & 0x1FF, 16 if size else 8
            for py in range(sz):
                for qx in range(sz):
                    sx, sy = (sz - 1 - qx) if flip_x else qx, (sz - 1 - py) if flip_y else py
                    c = gfx.tile_pixel(vram, tile + (sx >> 3) + 16 * (sy >> 3), sx & 7, sy & 7)
                    if c:
                        dots[x + qx, y + py] = tuple(pal[c][:3]) + (255,)
        left, top = min(k[0] for k in dots), min(k[1] for k in dots)
        w, h = max(k[0] for k in dots) - left + 1, max(k[1] for k in dots) - top + 1
        pix = [(0, 0, 0, 0)] * (w * h)
        for (x, y), c in dots.items():
            pix[(y - top) * w + x - left] = c
        out[team] = (w, h, pix)
    return out


def png_bytes(w, h, pix):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw += bytes(pix[y * w + x])
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import league_team_study as L
    all_logos = logos(L.rom("cd85e387.smc"))
    cols = 7
    cw, ch = 72, 72
    rows = (len(all_logos) + cols - 1) // cols
    W, H = cols * cw, rows * ch
    sheet = [(245, 245, 240, 255)] * (W * H)
    for i, (t, (w, h, pix)) in enumerate(sorted(all_logos.items())):
        ox, oy = (i % cols) * cw + 4, (i // cols) * ch + 4
        for y in range(min(h, ch - 4)):
            for x in range(min(w, cw - 4)):
                if pix[y * w + x][3]:
                    sheet[(oy + y) * W + ox + x] = pix[y * w + x]
        print(t, w, h, sum(1 for p in pix if p[3]))
    scale = 3
    big = [sheet[(y // scale) * W + (x // scale)] for y in range(H * scale) for x in range(W * scale)]
    Path(sys.argv[1]).write_bytes(png_bytes(W * scale, H * scale, big))


if __name__ == "__main__":
    main()
