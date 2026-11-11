"""Game Setup's lines and choices, an original ROM against an edited one (2026-11-11, for NOSE4Web's fighting builds:
the patched main menu rebuilt from the ROM's own). Power-on to Game Setup the same way on both; for each line, from
the top, RIGHT pressed until the menu box comes back to how it started (a line's choices cycle), the cursor's row
(caption and choice) saved as a hash after each press, up to 40 presses. Each line's sequence of boxes is compared between
the ROMs; the edited ROM's extra lines are listed. Screenshots of every distinct box go to OUT/<tag>/.
`--fourway`: the EA 4-Way Play adaptor plugged in (emu.Emu(fourway=True)), which adds its own Players choices.

python gen_menu_compare.py ORIGINAL EDITED OUT [--fourway]"""
import hashlib
import sys
from pathlib import Path

from emu import Emu
from goal_frames import grab


def walk(rom, out, fourway):
    e = Emu(rom, fourway=fourway)
    e.run(1800)
    e.run(4, hold=["START"])
    e.run(120)

    row = [0]

    def box():
        """The cursor's own row (caption and choice): the box shows six rows of 16 pixels from y 116, and the cursor
        stays on the last of them once the list scrolls."""
        e.want_frame = True
        e.run(1)
        e.want_frame = False
        img = grab(e)
        y = 116 + 16 * min(row[0], 5)
        crop = img.crop((0, y, img.width, y + 15))
        return hashlib.md5(crop.tobytes()).hexdigest()[:12], img

    def press(b, wait=26):
        e.run(4, hold=[b])
        e.run(wait)
    lines = []
    out.mkdir(parents=True, exist_ok=True)
    for i in range(14):
        h0, img = box()
        img.save(out / f"line{i:02d}_00.png")
        seq = [h0]
        for k in range(40):
            press("RIGHT")
            h, img = box()
            if h == h0:
                break
            seq.append(h)
            img.save(out / f"line{i:02d}_{k + 1:02d}.png")
        lines.append(seq)
        before = box()[1].crop((0, 112, 320, 214)).tobytes()
        press("DOWN")
        if box()[1].crop((0, 112, 320, 214)).tobytes() == before:      # the cursor didn't move: the last line
            break
        row[0] += 1
    return lines


def main():
    a, b, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    fourway = "--fourway" in sys.argv
    la = walk(a, out / "original", fourway)
    lb = walk(b, out / "edited", fourway)
    print(f"lines: original {len(la)}, edited {len(lb)}")
    for i in range(max(len(la), len(lb))):
        sa = la[i] if i < len(la) else None
        sb = lb[i] if i < len(lb) else None
        if sa is None:
            print(f"  line {i}: only in the edited ROM, {len(sb)} choices")
        elif sb is None:
            print(f"  line {i}: only in the original, {len(sa)} choices")
        else:
            print(f"  line {i}: choices {len(sa)} / {len(sb)}, boxes {'the same' if sa == sb else 'DIFFER'}")


if __name__ == "__main__":
    main()
