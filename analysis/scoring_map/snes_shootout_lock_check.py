"""NOSE4Web's lock on Exit Shootout during its shootout, played (2026-11-11, 51876ae: PauseExitGame's jsl AskExitGame
goes to a stub that answers No while $7E:F0F0 is set). With pad 1 on the home team (a person's game, so demoread
leaves the game alone; the game started through the menus with the controller screen's default, pad 1 on the home
team, not taken off afterwards: setting cont1team later doesn't let START pause):
- `regular`: in play, START (the pause menu), Down until the last line (Exit Game), B: the exit prompt should come up
  (AskExitGame sets curitem $1DB9 to 0: set to $55 beforehand), Down (Yes), B: the game should leave for Game Setup
  (Opening2; a screenshot); the mark's value printed (it must be 0 in a regular game);
- `before`: a tied regular-season game at period 3's end: the shootout's opening menu (pmenulist $1EB7 = 3), Down to
  its last line (Exit Shootout), B: no prompt (curitem stays $55), the menu still up; Down and B again (as Yes would
  be); then Up to the first line (Start Shootout), B: the shootout starts (the round goes up);
- `between`: in the shootout, START: its pause menu (pmenulist 4), Down to Exit Shootout, B (twice, Down between): no
  prompt; Up to Resume Shootout, B: play goes on;
- then B every second until the game is over: the final score, gsp 4.
Screenshots at each step (OUT/<step>.png); a JSON line of results.

python snes_shootout_lock_check.py ROM OUT"""
import json
import sys
from pathlib import Path

import lowload
import menu_shots as M
from snes_60fps_cvc import CLOCK, CLOCKSTOP, CONT1TEAM, GSP, Mem
from snes_ot_goal_check import PLAYMODE
from snes_shootout_check import ROUND, SFLAGS, SHOOTMODE, set_score

MARK, CURITEM, PSITEM, PMENULIST = 0xF0F0, 0x1DB9, 0x0D15, 0x1EB7


def press(e, b, n=1):
    for _ in range(n):
        e.run(8, hold=[b])
        e.run(16)


def to_last(e, m):
    for _ in range(25):
        before = m.w(PSITEM)
        press(e, "DOWN")
        if m.w(PSITEM) == before:
            break


def person_start(rom, out):
    e = M.emulator(rom)
    m = Mem(e, rom)
    M.play(e, "w1500 START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", out)
    M.play(e, "START w240 START w200 w2400", out)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
            break
        e.run(8, hold=["START"])
        e.run(60)
    return e, m


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    e, m = person_start(rom, out)
    e.run(600)
    res_pad = m.w(CONT1TEAM)
    base = e.serialize()
    res = {"rom": Path(rom).name, "pad 1's team": res_pad, "mark in a regular game": m.w(MARK)}

    # regular game: Exit Game asks and exits
    press(e, "START")
    e.run(60)
    res["regular: menu list"] = m.w(PMENULIST)
    to_last(e, m)
    res["regular: last item"] = m.w(PSITEM)
    e.screenshot(out / "regular_1_exit_line.png")
    m.setw(CURITEM, 0x55)
    press(e, "B")
    e.run(30)
    res["regular: prompt came up"] = m.w(CURITEM) != 0x55
    e.screenshot(out / "regular_2_prompt.png")
    press(e, "DOWN")
    press(e, "B")
    e.run(300)
    e.screenshot(out / "regular_3_after_yes.png")
    res["regular: left the game (gsp, shootoutmode, pmenulist)"] = [m.w(GSP), m.w(SHOOTMODE), m.w(PMENULIST)]

    # the shootout's opening menu
    e.unserialize(base)
    m.setw(PLAYMODE, 0)
    m.setw(GSP, 2)
    m.setw(CLOCK, 3)
    set_score(m, 2, 2)
    still, last = 0, None
    for _ in range(1500):
        e.run(10)
        c = m.w(CLOCK)
        still = still + 10 if c == last else 0
        last = c
        if still >= 600 and not m.w(SHOOTMODE):      # a person's game waits for START at a period's start (overtime)
            press(e, "START")
            still = 0
        if m.w(GSP) == 3 and 10 < m.w(CLOCK) < 299:   # the after-overtime builds: overtime to 3 s, still tied
            m.setw(CLOCK, 3)
            set_score(m, 2, 2)
        if m.w(SHOOTMODE) and m.w(PMENULIST) == 3 and m.w(SFLAGS) & 0x400:
            break
    e.run(60)
    res["before: menu list"] = m.w(PMENULIST)
    res["before: mark"] = m.w(MARK)
    to_last(e, m)
    res["before: last item"] = m.w(PSITEM)
    e.screenshot(out / "before_1_exit_line.png")
    m.setw(CURITEM, 0x55)
    press(e, "B")
    e.run(30)
    res["before: prompt came up"] = m.w(CURITEM) != 0x55
    press(e, "DOWN")
    press(e, "B")
    e.run(60)
    e.screenshot(out / "before_2_after_exit_presses.png")
    res["before: still in the shootout menu (shootoutmode, pmenulist, sflags)"] = [m.w(SHOOTMODE) & 0xFF, m.w(PMENULIST), hex(m.w(SFLAGS))]
    for _ in range(10):
        press(e, "UP")
    res["before: item after Up"] = m.w(PSITEM)
    r0 = m.w(ROUND)
    press(e, "B")
    for _ in range(120):
        e.run(10)
        if m.w(ROUND) != r0:
            break
    res["before: Start Shootout started it (round before, after)"] = [r0, m.w(ROUND)]
    e.screenshot(out / "before_3_started.png")

    # its pause menu between shooters
    tries = 0
    for tries in range(1, 60):                    # START until its pause menu is up (not while a shot is on)
        e.run(60)
        press(e, "START")
        e.run(30)
        if m.w(SFLAGS) & 1 and m.w(PMENULIST) == 4:
            break
    res["between: START presses to pause"] = tries
    res["between: menu list"] = m.w(PMENULIST)
    to_last(e, m)
    res["between: last item"] = m.w(PSITEM)
    e.screenshot(out / "between_1_exit_line.png")
    m.setw(CURITEM, 0x55)
    press(e, "B")
    e.run(30)
    res["between: prompt came up"] = m.w(CURITEM) != 0x55
    press(e, "DOWN")
    press(e, "B")
    e.run(60)
    e.screenshot(out / "between_2_after_exit_presses.png")
    res["between: still in the shootout (shootoutmode, pmenulist, sflags)"] = [m.w(SHOOTMODE) & 0xFF, m.w(PMENULIST), hex(m.w(SFLAGS))]
    for _ in range(10):
        press(e, "UP")
    press(e, "B")
    e.run(120)
    res["between: after Resume (sflags)"] = hex(m.w(SFLAGS))

    # play on, B every second, to the end
    r1 = m.w(ROUND)
    for f in range(0, 60 * 60 * 6, 60):
        e.run(52)
        e.run(8, hold=["B"])
        if m.w(GSP) == 4:
            break
    e.run(120)
    e.screenshot(out / "end.png")
    res["end: rounds played after the menus"] = [r1, m.w(ROUND)]
    res["end: gsp, final score, mark"] = [m.w(GSP), m.w(0x178E), m.w(0x1790), m.w(MARK)]
    print(json.dumps(res))


if __name__ == "__main__":
    main()
