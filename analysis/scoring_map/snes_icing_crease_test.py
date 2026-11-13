"""The SNES icing build's crease window, forced (2026-11-13, for NOSE4Web b98739a; retail SNES has no window: any
crossing of the far goal line counts, and the build drops icing within |x| <= 44 as the Genesis does). From one saved
moment of a computer game (snes_ot_goal_check.start), each trial: icing armed in RAM (iflags $0CF1: ifok, ifdir for
the top line; icingPlayer, its high byte, a home skater), the puck loose (puckc $0AD9 = $FFFF) at X, y 240 (or -240),
on the ice, sent across the line fast (Yvel $2E00 or -$2E00, Xvel 0: faster than updateplayers' early wave-off
looks at). Every frame for 40 frames: iflags; the outcome is "crossed" (ifcgl set: the race or, on retail, the touch
decides), "dropped" (ifok cleared with no crossing, the puck past y 258) or "other".

python snes_icing_crease_test.py ROM [ROM ...]"""
import json
import sys

import lowload
from snes_ot_goal_check import start

IFLAGS, PUCKC, PUCKZ = 0x0CF1, 0x0AD9, 0x0DF9
PX, PY, PVX, PVY = 0x0D55 + 28, 0x0DB7 + 28, 0x0EC3 + 28, 0x0EE3 + 28
XS = (-60, -48, -40, -20, 0, 20, 40, 44, 46, 60)


def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def trial(e, m, base, x, top):
    e.unserialize(base)
    m.setw(IFLAGS, (2 << 8) | 0x04 | (0x02 if top else 0))
    m.setw(PUCKC, 0xFFFF)
    m.setw(PX, x & 0xFFFF)
    m.setw(PY, (240 if top else -240) & 0xFFFF)
    m.setw(PUCKZ, 0)
    m.setw(PVX, 0)
    m.setw(PVY, (0x2E00 if top else -0x2E00) & 0xFFFF)
    out = "other"
    for f in range(40):
        e.run(1)
        fl, py = m.w(IFLAGS), s16(m.w(PY))
        if fl & 1:
            return {"x": x, "top": top, "outcome": "crossed", "frame": f, "y": py, "iflags": f"{fl:04X}"}
        if not fl & 4:
            return {"x": x, "top": top, "outcome": "dropped" if abs(py) >= 258 else "cleared early", "frame": f,
                    "y": py, "iflags": f"{fl:04X}"}
    return {"x": x, "top": top, "outcome": out}


def main():
    lowload.gentle()
    for rom in sys.argv[1:]:
        e, m = start(rom, 0, __import__("pathlib").Path.home() / "NHL94_scoring_map" / "runs" / "_crease_boot")
        e.run(900)
        while m.w(0x15D6):                      # until the clock runs (in play)
            e.run(30)
        base = e.serialize()
        res = [trial(e, m, base, x, top) for top in (True, False) for x in XS]
        print(rom.split("/")[-1], json.dumps([(r["x"], "top" if r["top"] else "bottom", r["outcome"]) for r in res]),
              flush=True)


if __name__ == "__main__":
    main()
