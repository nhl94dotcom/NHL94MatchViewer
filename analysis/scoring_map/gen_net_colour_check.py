"""NOSE4Web's net colours (Genesis, 2026-11-09, 629e033: both nets' six sprite pieces, attribute high bytes
$A16C0-$A16E8 every 8, given another palette line). The first ROM (retail) plays from power-on into play (gen_ot_check.into_play) and saves
that state; every ROM then starts from it with the same presses, so the same frames: 2400 frames of play with a screenshot every
120, then START, DOWN to Instant Replay and C, and a screenshot every 60 frames of the replay. Each ROM's
screenshots are compared with the first ROM's (retail): the bounding boxes of the pixels that differ, and a sheet
of the frames that differ (retail above, the edit below) for looking.

python gen_net_colour_check.py OUT RETAIL ROM [ROM ...]"""
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

SCREEN = 0xFFF7


def shots(rom, out, state):
    """state: the play state to start from (written by the first ROM, loaded by the rest: the edits only change
    sprite attributes, and the test ROMs boot a few frames sooner without the checksum check, which moves the
    random seed)."""
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    if state.exists():
        e.unserialize(state.read_bytes())
    else:
        G.to_setup(e, out)
        if not G.into_play(e):
            print(rom, "never reached play")
            return
        state.write_bytes(bytes(e.serialize()))
    for k in range(20):
        e.run(120)
        e.screenshot(out / f"play_{k:02d}.png")
    e.run(4, hold=["START"])
    e.run(90)
    e.run(4, hold=["DOWN"])
    e.run(30)
    e.screenshot(out / "menu.png")
    e.run(4, hold=["C"])
    for k in range(20):
        e.run(60)
        e.screenshot(out / f"replay_{k:02d}.png")
    lowload.breathe()


def main():
    out = Path(sys.argv[1])
    roms = sys.argv[2:]
    import subprocess
    for i, rom in enumerate(roms):           # one emulator per process
        subprocess.run([sys.executable, __file__, "--one", rom, str(out / f"rom{i}"), str(out / "play.state")], check=True)
    from PIL import Image, ImageChops
    base = out / "rom0"
    for i in range(1, len(roms)):
        other = out / f"rom{i}"
        pairs = []
        for p in sorted(base.glob("*.png")):
            q = other / p.name
            if not q.exists():
                continue
            a, b = Image.open(p).convert("RGB"), Image.open(q).convert("RGB")
            box = ImageChops.difference(a, b).getbbox()
            print(Path(roms[i]).name, p.stem, box, flush=True)
            if box:
                pairs.append((a, b))
        if pairs:
            w, h = pairs[0][0].size
            sheet = Image.new("RGB", (w * min(6, len(pairs)), 2 * h))
            for k, (a, b) in enumerate(pairs[:6]):
                sheet.paste(a, (k * w, 0))
                sheet.paste(b, (k * w, h))
            sheet.save(out / f"diff_{Path(roms[i]).stem}.png")


if __name__ == "__main__":
    if sys.argv[1] == "--one":
        shots(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]))
    else:
        main()
