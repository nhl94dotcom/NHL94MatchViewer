"""A SNES fight watched from start to end (2026-11-11, for NOSE4Web b3f1510: McMarkis's fighting, NHL94_fighting.smc and
its kin). A computer game (snes_ot_goal_check.start: the menus, the computer on both sides) runs until a player's
pflags $0400 (fighting) comes on; then a screenshot every 20 frames while any player is fighting and for 6 s (real)
after (fight_NN.png), the calls in the penalty buffer ($15DE: $2A / $2C fighting majors, $2E instigator) as they
appear, and the pflags of the two fighters. With PAD (an argument), pad 1 is given the home team when the fight starts
and presses Y, B and A in turn (the fight buttons), so a person's punches show too. Then, in play again: START (the
pause menu: pause.png), DOWN and B (Instant Replay: replay_NN.png every 30 frames for 6 s), and out (B, START).

python snes_fight_shots.py ROM OUT [max_minutes] [pad] [startonly]   (startonly: START through the ROM's own setup
defaults, for league ROMs whose setup screen differs from retail's, SDL16)"""
import sys
from pathlib import Path

import lowload
from snes_60fps_cvc import CLOCK, GSP, computer_only
from snes_ot_goal_check import start

PFLAGS, FIGHTER, PENBUF = 0x1283, 0x0400, 0x15DE
CONT1TEAM, PADSIDE, PLAYERPAD, C1PLAYER, TEAMPADS = 0x1C84, 0x19F6, 0x19D4, 0x19EC, 0x19D0


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    limit = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 30
    pad = "pad" in sys.argv[3:]
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    if "startonly" in sys.argv[3:]:          # a league ROM whose setup screen differs (SDL16): START through its defaults
        import menu_shots as M
        from snes_60fps_cvc import CLOCKSTOP, Mem
        e = M.emulator(rom)
        m = Mem(e, rom)
        M.play(e, "w1500 START w240", out)
        for _ in range(25):
            c = m.w(CLOCK)
            e.run(240)
            if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
                break
            e.run(4, hold=["START"])
            e.run(60)
        computer_only(m)
    else:
        e, m = start(rom, 0, out)
    fighters = lambda: [k for k in range(12) if m.w(PFLAGS + 2 * k) & FIGHTER]
    seen_calls = set()

    def calls():
        new = []
        for slot in range(0, 64, 2):
            code, obj = m.w(PENBUF + slot) & 0xFF, m.w(PENBUF + slot) >> 8
            if code and (slot, code, obj) not in seen_calls:
                seen_calls.add((slot, code, obj))
                new.append((hex(code), obj & 0x7F))
        return new
    frame, still, last = 0, 0, None
    while frame < 60 * 60 * limit and not fighters():
        e.run(10)
        frame += 10
        if frame % 300 == 0:
            computer_only(m)
            if frame % 3600 == 0:
                lowload.breathe()
        c = m.w(CLOCK)
        still = still + 10 if c == last else 0
        last = c
        if still >= 900:
            e.run(4, hold=["START"])
            still = 0
    if not fighters():
        print(f"no fight within {limit} minutes")
        return
    print(f"fight at frame {frame}: fighters {fighters()}, period {m.w(GSP)}, clock {m.w(CLOCK)}", flush=True)
    if pad:                                  # pad 1 on the home team (snes_period_cvc's way, in reverse)
        m.setw(CONT1TEAM, 1)
        m.setw(TEAMPADS, 1)
    shot, after = 0, None
    for f in range(0, 60 * 60, 2):
        hold = [("Y", "B", "A")[(f // 30) % 3]] if pad and f % 30 < 4 else []
        e.run(2, hold=hold)
        new = calls()
        if new:
            print(f"  +{f} frames: calls {new}", flush=True)
        if f % 20 == 0 and shot < 80:
            e.screenshot(out / f"fight_{shot:02d}.png")
            shot += 1
        if fighters():
            after = None
        elif after is None:
            after = f
            print(f"  +{f} frames: the fight is over (no fighter flag)", flush=True)
        elif f - after > 360:
            break
    e.run(240)
    e.run(4, hold=["START"])
    e.run(90)
    e.screenshot(out / "pause.png")
    e.run(4, hold=["DOWN"])
    e.run(20)
    e.run(4, hold=["B"])
    for k in range(12):
        e.run(30)
        e.screenshot(out / f"replay_{k:02d}.png")
    for b in ("B", "START", "B", "START"):
        e.run(4, hold=[b])
        e.run(60)
    e.run(300)
    e.screenshot(out / "after.png")
    print("done; pictures in", out)


if __name__ == "__main__":
    main()
