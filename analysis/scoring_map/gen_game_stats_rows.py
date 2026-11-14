"""Room for a 16th row on the Genesis Game Stats page (2026-11-14, for NOSE4Web's giveaways / takeaways row).

StatsReport (period94) draws every TeamStatTextTbl row at once into plane A, 2 map rows each from row 0 (15 rows:
plane rows 0-29 of the 64 x 32 plane), and scrolls them with up / down as far as matchupvis ($FFD59E: $70, 15 rows;
$30, 11). A 16th row would take plane rows 30-31 and need matchupvis $80. This plays a computer game into play, opens
Game Stats from the pause menu (item 4, $CF20), scrolls to the bottom (screenshot), then sets matchupvis one row further ($80) and
scrolls on (screenshot): what the screen shows below row 15 when the plane is scrolled one row further (the plane wraps:
plane rows 0-1, "Score", come next).

python gen_game_stats_rows.py ROM OUT"""
import sys
from pathlib import Path

import gen_ot_check as G
from emu import Emu

MATCHUPVIS, ITEM, VSCROLL = 0xD59E, 0xCF20, None


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(0xD056, 1)                     # OptPen: penalties on (15 rows)
    if not G.into_play(e):
        print("never reached play")
        return
    e.run(600)
    G.press(e, "START")
    e.run(60)
    for _ in range(30):
        if e.w(ITEM) == 4:
            break
        G.press(e, "DOWN")
    G.press(e, "C")
    e.run(240)
    e.screenshot(out / "stats_top.png")
    print("matchupvis", hex(e.w(MATCHUPVIS)))
    e.run(200, hold=["DOWN"])
    e.run(30)
    e.screenshot(out / "stats_bottom_15rows.png")
    e.setw(MATCHUPVIS, e.w(MATCHUPVIS) + 0x10)     # one row more
    e.run(200, hold=["DOWN"])
    e.run(30)
    e.screenshot(out / "stats_bottom_16rows.png")
    print("written", sorted(p.name for p in out.glob("stats_*.png")))


if __name__ == "__main__":
    main()
