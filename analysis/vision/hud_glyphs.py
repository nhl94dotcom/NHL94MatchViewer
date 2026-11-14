"""The score boxes' characters as the game draws them (2026-11-14): templates for hud_read.py from the emulator,
every digit and period, not only those a learning video happened to show (a YouTube series' 8s read as 6 or 0).

A computer game in play on the ROM (analysis/scoring_map's headless Genesis Plus GX: 256 x 224 frames); for each
case the period ($C466), clock ($C468) and scores ($CA3E visitors, $C6DA home) are set, the game paused and resumed
(which redraws both boxes: printscores1), and each of hud_read.CELLS cut out with its label. Cases: periods 0-3,
clocks covering every minute digit (and 10 / 20 minutes), every seconds digit, scores 0-19 each side.

python analysis/vision/hud_glyphs.py ROM OUT.npz"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
import hud_read  # noqa: E402


def cases():
    out = []
    for k in range(20):
        per = k % 4
        clock = [5 * 60 + 37, 9 * 60 + 58, 10 * 60 + 41, 1 * 60 + 9, 4 * 60 + 23, 7 * 60 + 15, 2 * 60 + 46, 8 * 60 + 2,
                 3 * 60 + 30, 6 * 60 + 54, 20 * 60, 0 * 60 + 19, 12 * 60 + 33, 14 * 60 + 47, 16 * 60 + 5,
                 18 * 60 + 28, 11 * 60 + 11, 13 * 60 + 39, 15 * 60 + 52, 19 * 60 + 6][k]
        out.append((per, clock, k, (k * 7 + 3) % 20))
    return out


def main():
    import gen_1on1_edit_lines as G
    from PIL import Image
    rom, out = sys.argv[1], Path(sys.argv[2])
    work = out.parent / "_hudgen"
    r = G.Run(rom, work)
    r.to_play()
    e = r.e
    sums, counts = defaultdict(lambda: np.zeros((8, 8))), defaultdict(int)
    for per, clock, vis, home in cases():
        e.setw(0xC466, per)
        e.setw(0xC468, clock)
        e.setw(0xCA3E, vis)
        e.setw(0xC6DA, home)
        r.press("START", 60)
        r.press("START", 90)
        clock = e.w(0xC468)                    # the clock ran a little meanwhile
        e.setw(0xC468, clock)
        r.step(2)
        e.screenshot(work / "_g.png")
        f = np.array(Image.open(work / "_g.png").convert("RGB")).astype(np.int16)
        m, s = divmod(e.w(0xC468), 60)
        lab = {hud_read.CELLS["per"][0]: "p" + hud_read.PERIODS[per], hud_read.CELLS["per"][1]: "q" + hud_read.PERIODS[per],
               hud_read.CELLS["min"][0]: str(m // 10) if m >= 10 else " ", hud_read.CELLS["min"][1]: str(m % 10),
               hud_read.CELLS["sec"][0]: str(s // 10), hud_read.CELLS["sec"][1]: str(s % 10)}
        for key, v in (("vis", vis), ("home", home)):
            lab[hud_read.CELLS[key][0]] = str(v // 10) if v >= 10 else " "
            lab[hud_read.CELLS[key][1]] = str(v % 10)
        for rc, ch in lab.items():
            g = hud_read.group(rc)
            kind = "per" if g == "per" else "clk" if g in ("min", "sec") else "score"
            sums[(kind, ch)] += hud_read.cell(f, rc)
            counts[(kind, ch)] += 1
    keys = sorted(sums)
    np.savez_compressed(out, keys=np.array(["|".join(k) for k in keys]),
                        tmpl=np.stack([sums[k] / counts[k] for k in keys]), counts=np.array([counts[k] for k in keys]),
                        native=np.array(True))
    print(f"{len(keys)} templates: " + ", ".join(f"{k[0]}:{k[1]!r}" for k in keys))


if __name__ == "__main__":
    main()
