"""NOSE4Web's three-round shootout (0095e61) in the SNES's own Shootout mode, from the main menu (2026-11-14).

From power-on: Play Mode set to Shootout (OPTPLAYMODE $34BC = 4) on the menu, START until shootoutmode ($1D81) is on,
the computer on both sides; the shootout's opening menu waits for pad 1: B held 8 frames once (as
snes_shootout_check). Every attempt logged: the round ($1D85), the shooting team (BA_Team $15D4: 0 home, 2
visitors; the visitors shoot first), the score (tmscore $178E home / $1790 visitors: the shootout's goals). Ends when
shootoutmode clears (or 40 minutes of frames); screenshots at each attempt and every 2 s (real) after the last.

--results=GM...: each attempt's result in turn (G goal, M miss, anything else as played): once the shooter has had
the puck and it is loose and on its way (|Y| 140-250), the puck is put into the net it is going at (Y +-262, speed
on into it) or wide of it (X 110, speed outward).

--pad: pad 1 left on its team from the menus (the 2 MB / SA-1 builds' computer-only shootout stops at the first
attempt in this harness); pad 1's shooter, given no input, lets his attempt run out (a miss).

python snes_shootout_mode_check.py ROM OUT [--results=...] [--pad]"""
import sys
from pathlib import Path

import lowload
import menu_shots as M
from snes_60fps_cvc import Mem, computer_only

OPTPLAYMODE, SOMODE, ROUND, BATEAM, SFLAGS = 0x34BC, 0x1D81, 0x1D85, 0x15D4, 0x15D8
HOME, VIS = 0x178E, 0x1790
PUCKX, PUCKY, PUCKZ, PUCKVZ, PUCKVX, PUCKVY, PUCKC = 0x0D71, 0x0DD3, 0x0DF9, 0x0E01, 0x0EDF, 0x0EFF, 0x0AD9


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    results = next((a.split("=")[1] for a in sys.argv if a.startswith("--results=")), "")
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    e = M.emulator(rom)
    m = Mem(e, rom)
    M.play(e, "w1800 START w240" if m.sa1 else "w1500 START w240 START w240", out)
    for _ in range(8):
        if m.w(OPTPLAYMODE) == 4:
            break
        M.play(e, "RIGHT w30", out)
    print("Play Mode", m.w(OPTPLAYMODE), flush=True)
    for _ in range(30):
        if m.w(SOMODE) & 0xFF:
            break
        e.run(4, hold=["START"])
        e.run(150)
    pad = "--pad" in sys.argv
    if not pad:
        computer_only(m)
    print("shootoutmode", m.w(SOMODE), flush=True)
    pressed, attempt, n_att, carried, decided, shots, over = False, None, -1, False, False, 0, None
    for f in range(60 * 60 * 40):
        e.run(1)
        if f % 300 == 0:
            if not pad:
                computer_only(m)
            if f % 3600 == 0:
                lowload.breathe()
        so = m.w(SOMODE) & 0xFF
        if so and not pressed and m.w(SFLAGS) & 0x400:
            e.run(30)
            e.run(8, hold=["B"])
            pressed = True
            print(f"f{f}: B pressed at the shootout's opening menu", flush=True)
        at = (m.w(ROUND), 1 if m.w(BATEAM) else 0)
        if so and (attempt is None or at[1] != attempt[1]):   # a new attempt when the shooting team changes (BA_Team
            attempt, n_att, carried, decided = at, n_att + 1, False, False   # moves on before the round count does)
            print(f"f{f}: attempt: round {at[0]}, {'visitors' if at[1] else 'home'} shooting, score "
                  f"{m.w(VIS)}-{m.w(HOME)} (visitors-home)", flush=True)
            e.screenshot(out / f"att_{shots:03d}_f{f}.png")
            shots += 1
        pc = s16(m.w(PUCKC))
        if so and pc >= 0:
            carried = True
        want = results[n_att] if 0 <= n_att < len(results) else None
        if so and want in ("G", "M") and carried and not decided and pc < 0:
            py = s16(m.w(PUCKY))
            if 140 < abs(py) < 250:
                end = 1 if py > 0 else -1
                x, vx, vy = (0, 0, end * 3000) if want == "G" else (110, 3000, 0)
                for a, v in ((PUCKX, x), (PUCKY, end * 262 if want == "G" else end * 240), (PUCKZ, 0), (PUCKVZ, 0),
                             (PUCKVX, vx), (PUCKVY, vy)):
                    m.setw(a, v & 0xFFFF)
                decided = True
                print(f"f{f}:   result forced: {'goal' if want == 'G' else 'miss'}", flush=True)
        if pressed and not so and over is None:
            over = f
            print(f"f{f}: shootout over: score {m.w(VIS)}-{m.w(HOME)} (visitors-home), round {m.w(ROUND)}", flush=True)
        if over is not None:
            if (f - over) % 120 == 0:
                e.screenshot(out / f"end_{(f - over) // 120:02d}.png")
            if f - over > 600:
                break
    if over is None:
        print("no end seen", flush=True)


if __name__ == "__main__":
    main()
