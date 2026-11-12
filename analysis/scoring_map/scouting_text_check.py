"""Ron Barr's matchup-screen text as the game types it (2026-11-12, for NOSE4Web 6806a72's text editor), both systems.
A ROM is taken to the matchup screen (gen_announcer_check's / snes_announcer_check's presses) and the text box is read
from video memory every 6 frames until the text is done: Genesis plane A rows 4-10, columns 9-38 (UpdateScoutingDisplay:
print at 9,4 plus scoutcolumn / VertLineScrolling, a new row past column 29); SNES BG1 (map at word 0) rows 14-21,
columns 2-20 (ScoutTypeWord: a new row past column 20). Each cell is decoded through the ROM's own font map (Genesis
SmallFontMap, the word for a character plus smallfontchars $B012; SNES SmallFontMap+6, plus smallfontchars and
printfontset), so a character whose font word is 0 reads as a space, as it shows. The rows are followed through the box's
scrolling (a row that leaves the top is kept), giving the whole text as typed, row by row. Then:
- each script line the game shows (NOSE4Web's order: Genesis 27, 26, 34 or 35, 30-33 with line 29 between; SNES 29,
  28, 30-33) is looked for in the typed text, its stand-ins as wildcards (whole, in order);
- each row's length against the box (30 / 19 columns), and any word cut at a row's end;
- the glyph each character of PUNCT shows: its font word, its tile, drawn from video memory (glyphs_<tag>.png, 8x);
- box pictures (box_<tag>_NN.png, 3x) each time the box is full and at the end.

python scouting_text_check.py ROM OUT [TAG]"""
import json
import re
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import menu_shots as M
from scouting_script import script

PUNCT = "!?&\"()-/:.,'"


def lorom(bank, addr):
    return ((bank & 0x7F) << 15) | (addr & 0x7FFF)


class Genesis:
    rows, cols, width = range(4, 11), range(9, 39), 30
    box_px = (72, 32, 312, 88)
    stands = re.compile(r"[{}\[\]<>|\\$@#%=*^;_+]")
    shown = [27, 26, 34, 30, 31, 32, 33]          # 35 instead of 34 when one team is much hotter
    between = 29

    def __init__(self, rom, data):
        from gen_setup_screen import state, vword, tile_pixels
        from gen_announcer_check import planes, PRESSES
        self.state, self.vword, self.tile_pixels, self.planes = state, vword, tile_pixels, planes
        self.presses = PRESSES
        m = re.search(rb"\x24\x7c(....)\x08\x38\x00\x03..\x67.{1,3}\x24\x7c(....)", data, re.S)
        at = struct.unpack(">I", m.group(1))[0]                      # SmallFontMap
        mp = at + struct.unpack(">I", data[at + 4:at + 8])[0]
        self.font = {c: struct.unpack(">H", data[mp + 4 + 2 * c:mp + 6 + 2 * c])[0] for c in range(0x20, 0x7F)}

    def start(self, e, out):
        M.play(e, self.presses, out)
        e.run(4, hold=["START"])

    def read(self, e):
        st, vr, cram, reg = self.state(e)
        (pl, width, sat) = self.planes(reg)
        base = pl[0][1]
        fb = e.w(0xFFB012)
        grid = [[self.vword(vr, base + 2 * (y * width + x)) & 0x7FF for x in self.cols] for y in self.rows]
        return grid, fb, vr

    def glyph(self, vr, tile):
        return self.tile_pixels(vr, tile)


class Snes:
    rows, cols, width = range(14, 22), range(2, 21), 19
    box_px = (8, 104, 184, 192)
    stands = re.compile(r"%[0-9a-zA-Z]")
    shown = [29, 28, 30, 31, 32, 33]
    between = None

    def __init__(self, rom, data):
        m = re.search(rb"\xda\x0a\xaa\xbf(...)\x65", data, re.S)
        a = int.from_bytes(m.group(1), "little")
        mp = lorom(a >> 16, a & 0xFFFF)
        self.font = {c: struct.unpack("<H", data[mp + 2 * c:mp + 2 * c + 2])[0] for c in range(0x20, 0x7F)}

    def start(self, e, out):
        M.play(e, "w1500 START w240 START w240 w60 START w240", out)
        e.run(4, hold=["START"])

    def read(self, e):
        from snes_ronbarr_check import vram
        vr = vram(e)
        fb = (e.w(0x35B6) + e.w(0x35A8)) & 0x3FF
        grid = [[struct.unpack_from("<H", vr, 2 * (32 * y + x))[0] & 0x3FF for x in self.cols] for y in self.rows]
        return grid, fb, vr

    def glyph(self, vr, tile):
        a = 2 * 0x2000 + 32 * tile
        px = []
        for r in range(8):
            p0, p1, p2, p3 = vr[a + 2 * r], vr[a + 2 * r + 1], vr[a + 16 + 2 * r], vr[a + 16 + 2 * r + 1]
            px += [((p0 >> b) & 1) | (((p1 >> b) & 1) << 1) | (((p2 >> b) & 1) << 2) | (((p3 >> b) & 1) << 3) for b in range(7, -1, -1)]
        return px


def decode(sysm, grid, fb):
    inv = {}
    for c, w in sorted(sysm.font.items(), key=lambda kv: (kv[0] not in (0x20, 0x4F), kv[0])):
        inv.setdefault(w, chr(c))
    rows = []
    for row in grid:
        s = ""
        for t in row:
            if t == 0 and fb != 0:
                s += " "              # never typed
            else:
                s += inv.get(t - fb, " ")      # not a font tile: the box's empty cells
        rows.append(s.rstrip())
    return rows


def follow(prev, cur):
    """How many rows scrolled off between two samples (prev's rows now at cur's i - s), or None."""
    for s in range(len(prev) + 1):
        if all(cur[i].startswith(prev[i + s]) or prev[i + s] == "" for i in range(len(prev) - s)):
            return s
    return None


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    tag = sys.argv[3] if len(sys.argv) > 3 else Path(rom).stem
    out.mkdir(parents=True, exist_ok=True)
    data = Path(rom).read_bytes()
    _, at, end, lines = script(data)
    sysm = Genesis(rom, data) if rom.lower().endswith(".bin") else Snes(rom, data)
    e = M.emulator(rom)
    sysm.start(e, out)
    kept, prev, still, shots, f, odd = [], None, 0, 0, 0, []
    vr = fb = None
    while f < 9000:
        e.run(6)
        f += 6
        grid, fb, vr = sysm.read(e)
        cur = decode(sysm, grid, fb)
        if prev is None:
            prev = cur
            continue
        if cur == prev:
            still += 6
            if still > 700 and any(kept + cur):
                break
            continue
        still = 0
        s = follow(prev, cur)
        if s is None:
            odd.append((f, prev, cur))     # the screen changed otherwise (the text done, the screen left)
            break
        if s:
            img = Image.open(_shot(e, out / f"tmp_{tag}.png")).crop(sysm.box_px)
            img.resize((img.width * 3, img.height * 3), Image.NEAREST).save(out / f"box_{tag}_{shots:02d}.png")
            shots += 1
            kept += prev[:s]
        prev = cur
    kept += prev
    img = Image.open(_shot(e, out / f"tmp_{tag}.png")).crop(sysm.box_px)
    img.resize((img.width * 3, img.height * 3), Image.NEAREST).save(out / f"box_{tag}_{shots:02d}.png")
    while kept and not kept[-1]:
        kept.pop()
    print(f"{tag}: the text typed in {f} frames, {len(kept)} rows (box {sysm.width} wide):")
    for r in kept:
        print(f"  |{r:<{sysm.width}}| {len(r)}")
    too_long = [r for r in kept if len(r) > sysm.width]
    # the shown lines, looked for in order, stand-ins as wildcards, a font-word-0 character as a space
    flat = re.sub(r"\s+", " ", " ".join(kept)).strip()
    pos, found = 0, {}
    def pattern(t):
        pat, i = "", 0
        while i < len(t):
            m = sysm.stands.match(t, i)
            if m:
                pat += r".+?"
                i = m.end()
                continue
            ch = t[i]
            pat += r"\s*" if ch == " " or sysm.font.get(ord(ch), 1) == 0 else re.escape(ch)
            i += 1
        return re.compile(re.sub(r"(\\s\*)+", r"\\s*", pat), re.S)

    for n in sysm.shown:
        if n >= len(lines) or not lines[n].strip():
            found[n] = "empty"
            continue
        m = pattern(lines[n].strip()).search(flat, pos)
        if not m and isinstance(sysm, Genesis) and n == 34 and len(lines) > 35 and lines[35].strip():
            m = pattern(lines[35].strip()).search(flat, pos)        # the much-hotter line instead
            n = "34 or 35"
        found[n] = bool(m)
        if m:
            pos = m.end()
    res = {"rom": Path(rom).name, "frames": f, "rows": len(kept), "too long": too_long, "shown lines found": found,
           "odd change": [o[0] for o in odd]}
    # glyphs
    sheet = Image.new("RGB", (len(PUNCT) * 80, 110), "white")
    d = ImageDraw.Draw(sheet)
    glyphs = {}
    for k, ch in enumerate(PUNCT):
        w = sysm.font.get(ord(ch))
        tile = w + fb
        px = sysm.glyph(vr, tile)
        glyphs[ch] = {"word": hex(w), "tile": hex(tile), "pixels lit": sum(1 for p in px if p)}
        for i, p in enumerate(px):
            if p:
                x, y = k * 80 + 8 + 8 * (i % 8), 8 + 8 * (i // 8)
                d.rectangle([x, y, x + 7, y + 7], fill=(0, 0, 0))
        d.text((k * 80 + 30, 80), repr(ch), fill=(200, 0, 0))
    sheet.save(out / f"glyphs_{tag}.png")
    res["glyphs"] = glyphs
    print(json.dumps(res))


def _shot(e, p):
    e.screenshot(p)
    return p


if __name__ == "__main__":
    main()
