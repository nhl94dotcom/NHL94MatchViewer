"""The SNES title screen, for NOSE4Web's title picture editor (2026-11-27: which pieces are which layers, the pictures'
data and the code that loads them, the video memory a new picture may use, the colours, fades and cycling).

TitleScreen (bank $9D, called from Opening after IntroSequence) splits the screen with IRQs: the frame hook sets the
top band (lines 0-$45, then WH3 changes at $46) to BG mode 9 (mode 1, BG3 priority), later mode 1: BG1 map $5400
(Title94Map, the "94" puck), BG2 map $5800 (TitleNHLMap, the NHL letters), both on TitleLogoTiles at $4000, BG3 map
$5C00 tiles $5000; .irq2 at line $50 switches to mode 7 (BG1 map and tiles at 0: LicenceTiles, the team logos
LoadTitleLogo draws, TitlePuckTiles from tile 128), TM from TitleM7TM; .irq3 at line $B0 BG1 + OBJ. Sprites: the
N / H / L letters (TitleSprites), the licence lines and the copyright and credits text (PrintStringSprites).

From the ROM: where each picture is (its packing header: $10 LZ, $30 Huffman; the unpacked size) and every
`lda.w #bank / sta.b p0+2 / lda.w #address / sta.b p0` in the code that names it (the immediates to repoint).
From power-on, every frame while TitleScreen runs (TitleBGMode $0BD1 1 or 9, until .8 clears it), from the core:
- the title's state words (TitleBGMode, TitleM7TM, TitleWH3, TitleLogoFlags, brightness, FrameCount) at each change;
- video memory (Snes9x memory 3): the words ever non-zero, by region, and when each region changed;
- the top band's BG1 / BG2 / BG3 maps (rows 0-9 shown): the tiles and palettes they name, and the (palette,
  colour) pairs their pixels use; the mode 7 map's tiles (low bytes of $0000-$3FFF) and their 8-bit colours;
- sprites (OAMData in the state's PPU block, +2003): visible entries, their tiles and palettes;
- colour memory (CGDATA in the state's PPU block, +64, big-endian words): each row's changes, frame by frame, and
  brightness (INIDISP's fade) apart;
- screenshots every 30 frames for the first 600, then every 300, and at each change of the state words (the first 80).
The 2 MB builds add TitleStampLoad (the '27 stamp over the puck: tiles after TitleLogoTiles, BG palette 4, BG1 map
words rewritten) and BuildVersionShow (the version line: sprite tiles $1FA-$1FF, sprite palette 1).

python snes_title_screen_check.py ROM OUT"""
import ctypes as C
import json
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

import menu_shots as M

OFFSETS = {"TitleLogoTiles": 0xA0000, "Title94Map": 0xD5DC6, "TitleNHLMap": 0xD588C, "LicenceTiles": 0xAF8C6,
           "TitlePuckTiles": 0xB25E5, "TitlePalette": 0xD4CA9, "TitleSpritePalette": 0xD60D5, "TitleSprites": 0x8B188,
           "LicenceNHLPAMap": 0x3FF91, "TitlePuckMap": 0xD5EE5}
STATE = {"TitleBGMode": 0x0BD1, "TitleM7TM": 0x0BD3, "TitleWH3": 0x0BCD, "TitleLogoFlags": 0x0BFF,
         "brightness": 0x0AD3, "FrameCount": 0x0764}


def sa1(data):
    return len(data) > 0x7FD6 and data[0x7FD5] == 0x23


def snes_addrs(off, data):
    """The CPU addresses a file offset can be read at: LoROM (banks $00-$7D and $80-$FF), and on SA-1 HiROM ($C0+)."""
    out = [((off >> 15) | 0x80, 0x8000 | off & 0x7FFF), (off >> 15, 0x8000 | off & 0x7FFF)]
    if sa1(data):
        out.append((0xC0 + (off >> 16), off & 0xFFFF))
    return out


def immediates(data, off):
    """`lda.w #bank (A9 bb 00) / sta.b p0+2 (85 xx) / lda.w #addr (A9 lo hi) / sta.b p0 (85 yy)`, in either order of
    the two halves, naming this offset."""
    hits = []
    for bank, addr in snes_addrs(off, data):
        pat = re.compile(re.escape(bytes([0xA9, bank, 0x00, 0x85])) + b"." + re.escape(bytes([0xA9, addr & 0xFF, addr >> 8, 0x85])), re.S)
        for m in pat.finditer(data):
            hits.append(dict(at=f"${m.start():05X}", bank_imm=f"${m.start() + 1:05X}", addr_imm=f"${m.start() + 6:05X}",
                             as_cpu=f"${bank:02X}:{addr:04X}"))
    return hits


def picture_info(data):
    out = {}
    for name, off in OFFSETS.items():
        h = data[off:off + 5]
        kind = {0x10: "LZ", 0x30: "Huffman"}.get(h[0], "?") if h[1:2] == b"\xFB" else "RLE / plain"
        size = (h[2] << 16 | h[3] << 8 | h[4]) if h[1:2] == b"\xFB" else None
        out[name] = dict(offset=f"${off:05X}", header=h.hex(), packing=kind, unpacked_bytes=size, code=immediates(data, off))
    return out


class Probe:
    def __init__(self, rom, out):
        self.e = M.emulator(rom)
        self.out = out
        self.vram = (C.c_ubyte * self.e.lib.retro_get_memory_size(3)).from_address(self.e.lib.retro_get_memory_data(3))

    def raw(self):
        n = self.e.lib.retro_serialize_size()
        buf = (C.c_ubyte * n)()
        self.e.lib.retro_serialize(buf, n)
        return bytes(buf)

    def cgram(self):
        r = self.raw()
        i = r.index(b"PPU:")
        p = r[i + 11:i + 11 + int(r[i + 4:i + 10])]
        return [struct.unpack_from(">H", p, 64 + 2 * k)[0] for k in range(256)]

    def words(self):
        return np.frombuffer(bytes(self.vram), dtype="<u2").copy()

    def oam(self):
        """The sprite table itself (OAMData in the state's PPU block, at +2003: found against the NMI's buffer)."""
        r = self.raw()
        i = r.index(b"PPU:")
        b = r[i + 11 + 2003:i + 11 + 2003 + 544]
        out = []
        for k in range(128):
            x, y, t, at = b[4 * k:4 * k + 4]
            hi = b[512 + k // 4] >> (2 * (k % 4)) & 3
            x |= (hi & 1) << 8
            if y >= 224 and y < 240:
                continue
            out.append((k, x, y, t | (at & 1) << 8, at >> 1 & 7, hi >> 1))
        return out


def tile4(vr, base, t):
    """Colour numbers of a 4-bit tile at word address base + 16 t."""
    cols = set()
    a = base + 16 * t
    for r in range(8):
        w0, w1 = int(vr[a + r]), int(vr[a + 8 + r])
        for b in range(8):
            cols.add((w0 >> b & 1) | (w0 >> (8 + b) & 1) << 1 | (w1 >> b & 1) << 2 | (w1 >> (8 + b) & 1) << 3)
    return cols


def tile2(vr, base, t):
    cols = set()
    a = base + 8 * t
    for r in range(8):
        w = int(vr[a + r])
        for b in range(8):
            cols.add((w >> b & 1) | (w >> (8 + b) & 1) << 1)
    return cols


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    data = Path(rom).read_bytes()
    R = dict(rom=Path(rom).name, sa1=sa1(data), pictures=picture_info(data))
    p = Probe(rom, out)
    e = p.e
    started = None
    events, last = [], None
    ever = np.zeros(0x8000, bool)
    region_changes = defaultdict(list)
    prev = None
    cg_first, cg_prev = None, None
    cg_rows = defaultdict(list)          # row -> frames its colours changed
    top = {"BG1": defaultdict(set), "BG2": defaultdict(set), "BG3": defaultdict(set)}   # tile -> palettes
    pairs = {"BG1": set(), "BG2": set(), "BG3": set(), "mode7": set(), "OBJ": set()}
    m7tiles = set()
    sprites = defaultdict(set)           # palette -> tiles
    regions = [(0x0000, 0x2000, "mode 7 map / tiles 0-127"), (0x2000, 0x4000, "mode 7 tiles 128-255"),
               (0x4000, 0x5000, "BG1/2 tiles (TitleLogoTiles)"), (0x5000, 0x5400, "BG3 tiles"),
               (0x5400, 0x5800, "BG1 map"), (0x5800, 0x5C00, "BG2 map"), (0x5C00, 0x6000, "BG3 map"),
               (0x6000, 0x8000, "sprite tiles")]
    shots = 0
    for f in range(20000):
        e.run(1)
        mode = e.w(STATE["TitleBGMode"])
        if started is None:
            if mode in (1, 9) and e.w(STATE["brightness"]):
                started = f
            else:
                continue
        elif mode not in (1, 9):
            R["title_frames"] = [started, f]
            break
        k = f - started
        st = {n: e.w(a) for n, a in STATE.items() if n != "FrameCount"}
        if st != last:
            events.append(dict(frame=k, **st))
            if shots < 80:
                e.screenshot(out / f"ev_{k:05d}.png")
                shots += 1
            last = st
        if (k < 600 and k % 30 == 0) or k % 300 == 0:
            e.screenshot(out / f"t_{k:05d}.png")
        vr = p.words()
        ever |= vr != 0
        if prev is not None:
            for lo, hi, name in regions:
                if (vr[lo:hi] != prev[lo:hi]).any():
                    if not region_changes[name] or region_changes[name][-1][1] != k - 1:
                        region_changes[name].append([k, k])
                    else:
                        region_changes[name][-1][1] = k
        prev = vr
        cg = p.cgram()
        if cg_first is None:
            cg_first = cg
        if cg_prev is not None and cg != cg_prev:
            for r in range(16):
                if cg[16 * r:16 * r + 16] != cg_prev[16 * r:16 * r + 16]:
                    cg_rows[r].append(k)
        cg_prev = cg
        if k % 10 == 0:
            for name, mp, base in (("BG1", 0x5400, 0x4000), ("BG2", 0x5800, 0x4000), ("BG3", 0x5C00, 0x5000)):
                for i in range(32 * 10):                     # the top band's rows
                    c = int(vr[mp + i])
                    t, pal = c & 0x3FF, c >> 10 & 7
                    cols = (tile2(vr, base, t) if name == "BG3" else tile4(vr, base, t)) - {0}
                    if cols:
                        top[name][t].add(pal)
                        pairs[name] |= {(pal, c_) for c_ in cols}
            lo = vr[0:0x4000] & 0xFF                          # the mode 7 map: 128 x 128 bytes
            names = set(int(x) for x in np.unique(lo))
            m7tiles |= names
            hi = (vr[0:0x4000] >> 8).reshape(256, 64)
            for t in names:
                pairs["mode7"] |= {(int(v) >> 4, int(v) & 15) for v in np.unique(hi[t]) if v}
            for (_, x, y, t, pal, big) in p.oam():
                sprites[pal].add(t)
    R["events"] = events
    R["vram_ever_nonzero"] = {name: int(ever[lo:hi].sum()) for lo, hi, name in regions}
    R["vram_last_nonzero_word"] = {name: (f"${lo + int(np.nonzero(ever[lo:hi])[0][-1]):04X}" if ever[lo:hi].any() else None) for lo, hi, name in regions}
    R["vram_changed_frames"] = {k: v[:20] for k, v in region_changes.items()}
    R["map_rows_used"] = {n: sorted({i // 32 for i in range(32 * 28) if int(prev[mp + i]) & 0x3FF}) for n, mp in (("BG1", 0x5400), ("BG2", 0x5800), ("BG3", 0x5C00))}
    R["top_band_tiles"] = {n: [min(d), max(d), len(d), sorted({p_ for v in d.values() for p_ in v})] if d else None for n, d in top.items()}
    R["colour_pairs"] = {n: sorted(v) for n, v in pairs.items()}
    R["mode7_tiles"] = [min(m7tiles), max(m7tiles), len(m7tiles)] if m7tiles else None
    R["sprite_palettes"] = {pal: [min(t), max(t), len(t)] for pal, t in sorted(sprites.items())}
    R["cgram_rows_changed"] = {r: [v[0], v[-1], len(v)] for r, v in sorted(cg_rows.items())}
    R["cgram_first"] = [" ".join(f"{c:04X}" for c in cg_first[16 * r:16 * r + 16]) for r in range(16)] if cg_first else None
    R["cgram_last"] = [" ".join(f"{c:04X}" for c in cg_prev[16 * r:16 * r + 16]) for r in range(16)] if cg_prev else None
    (out / "title.json").write_text(json.dumps(R, indent=1, default=list))
    print(json.dumps({k: v for k, v in R.items() if k not in ("events", "cgram_first", "cgram_last", "colour_pairs")}, indent=1, default=list))


if __name__ == "__main__":
    main()
