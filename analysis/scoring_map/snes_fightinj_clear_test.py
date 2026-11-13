"""NOSE4Web 84a3f6b (McMarkis's 485ec28a on the 1 MB layout): fightinj ($7E:FE80-$FEB3) and fightinjany ($7E:FEB4) are
cleared as each game starts (StartGame_go's lda.l $7E347A made jsl F_gamestart). From power-on to the setup screen
(snes_ot_goal_check.start's presses), every byte of $FE80-$FEB5 is set to 1; then START into the game, and the bytes
read again once the clock runs. A ROM without the change (e.g. NHL94_fight_time.smc) keeps them: the control.

python snes_fightinj_clear_test.py ROM [ROM ...]"""
import sys
from pathlib import Path

import menu_shots as M
from snes_60fps_cvc import Mem, CLOCK, CLOCKSTOP

LO, HI = 0xFE80, 0xFEB6


def main():
    out = Path.home() / "NHL94_scoring_map" / "runs" / "_fightinj_boot"
    out.mkdir(parents=True, exist_ok=True)
    for rom in sys.argv[1:]:
        e = M.emulator(rom)
        m = Mem(e, rom)
        M.play(e, "w1500 START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", out)
        for a in range(LO, HI):
            e.ram[a] = 1
        before = sum(e.ram[a] for a in range(LO, HI))
        M.play(e, "START w240 START w200 w2400", out)
        for _ in range(12):
            c = m.w(CLOCK)
            e.run(240)
            if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
                break
            e.run(4, hold=["START"])
            e.run(60)
        after = [e.ram[a] for a in range(LO, HI)]
        print(Path(rom).name, f"set before the game: {before} bytes; in play: {sum(1 for v in after if v)} of {HI - LO} still set",
              "(cleared)" if not any(after) else "(kept)", flush=True)


if __name__ == "__main__":
    main()
