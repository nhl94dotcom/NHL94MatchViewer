"""NOSE4Web's blocked shots on screen (Genesis NHL '94 and '95 builds): the Player Stats pages and the Game Stats row.

From a paused computer game (gen_toi_page_check.py play's OUT/paused.state, or made here), the block counts are set to
known values first (home roster places 0-5: 1, 2, 3, 4, 5, 6; visitors' 0-5: 6, 5, 4, 3, 2, 1, the rest 0; the team
totals 21 each), then:
- Player Stats (the pause menu item PLAYER, C): every page RIGHT (a screenshot each), then A (the other team) and back
  LEFT through the pages (a screenshot each);
- Game Stats (item GAME, C): the top, and the bottom after holding DOWN;
with penalties as the saved game had them; --pen=N sets OptPen ($FFD056) first (0 off, 1 on).

python gen_blocks_screens.py ROM OUT COUNTS HOME_TOTAL AWAY_TOTAL [--pen=N] [--items=GAME:PLAYER] [--state=PATH]
  COUNTS the first count byte ($E890 on NHL '94, $EA90 on NHL '95), the totals' addresses in hex (low 16 bits)"""
import sys
from pathlib import Path

import gen_ot_check as G
import gen_toi_page_check as T
import lowload
from emu import Emu

ITEM, OPTPEN = 0xCF20, 0xD056


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    counts, tot_h, tot_a = (int(a, 16) for a in sys.argv[3:6])
    opts = dict(a.lstrip("-").split("=") for a in sys.argv[6:] if "=" in a)
    game_item, player_item = (int(v) for v in opts.get("items", "4:5").split(":"))
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    state = Path(opts["state"]) if "state" in opts else out / "paused.state"
    if not state.exists():
        T.play(rom, out, 240)
        state = out / "paused.state"
    e = Emu(rom)
    e.unserialize(state.read_bytes())
    if "pen" in opts:
        e.setw(OPTPEN, int(opts["pen"]))
    for p in range(32):
        e.setb(0xFF0000 | (counts + p), p + 1 if p < 6 else 0)
        e.setb(0xFF0000 | (counts + 32 + p), 6 - p if p < 6 else 0)
    e.setw(0xFF0000 | tot_h, 21)
    e.setw(0xFF0000 | tot_a, 21)
    base = e.serialize()

    def to_item(n):
        for _ in range(30):
            if e.w(ITEM) == n:
                return True
            G.press(e, "DOWN")
        return False

    # Player Stats
    if to_item(player_item):
        G.press(e, "C")
        e.run(240)
        e.screenshot(out / "player_00.png")
        for k in range(1, 12):
            G.press(e, "RIGHT")
            e.run(90)
            e.screenshot(out / f"player_{k:02d}.png")
        G.press(e, "A")
        e.run(120)
        for k in range(12, 24):
            e.screenshot(out / f"player_{k:02d}_other.png")
            G.press(e, "LEFT")
            e.run(90)
    else:
        print("no Player Stats item", flush=True)
    # Game Stats
    e.unserialize(base)
    if to_item(game_item):
        G.press(e, "C")
        e.run(240)
        e.screenshot(out / "game_top.png")
        e.run(300, hold=["DOWN"])
        e.run(30)
        e.screenshot(out / "game_bottom.png")
    else:
        print("no Game Stats item", flush=True)
    print("done", out, flush=True)


if __name__ == "__main__":
    main()
