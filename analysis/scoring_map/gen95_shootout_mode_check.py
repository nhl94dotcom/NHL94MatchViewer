"""NHL '95 (Genesis): Shootout mode from Game Setup, attempt by attempt (2026-11-16, for NOSE4Web's NHL shootout 4d3bdf2:
three rounds, ends once a team can't catch up, then sudden death). Power-on to Game Setup, setupvalues' play mode set
to $C (Shootout), START through the controller screen; at the shootout's pause menu START (PLAY GAME); the computer on
both sides (cont1team / cont2team and the person flags cleared every second). Every attempt is logged when it comes
up (round, shooting team, the goal counts, the shooter list index); the end is gmode2 bit 3 (CountShootoutGoals' end)
or the title.

RESULTS (optional) forces each attempt in turn: G a goal, M a miss, '.' as played. G: once the attempt's shooter has
had the puck and it is loose past y 120, it is put into that net (both goalies moved aside). M: whenever the puck comes
within 60 of the middle past y 200, it is moved 150 out, loose and still.

python gen95_shootout_mode_check.py ROM OUT_DIR [RESULTS] [MAX_ATTEMPTS]"""
import sys
from pathlib import Path

from emu import Emu
import gen95_assist_check as G
import lowload

GMODE2, ROUND, TEAMW, HG, AG, NUM, SETUP = 0xBF00, 0xD184, 0xD1A0, 0xD180, 0xD182, 0xD192, 0xD282
CONT1, CONT2 = 0xBF4C, 0xBF4E


def run(rom, out, results="", maxatt=24):
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    e.run(1500)
    for _ in range(3):
        e.run(6, hold=["START"]); e.run(200)
    e.setb(SETUP, 0xC); e.run(30)
    e.run(6, hold=["START"]); e.run(300)       # the controller screen
    e.run(6, hold=["START"]); e.run(400)       # into the shootout's menu
    log, att, key, state, f, menu_wait = [], -1, None, "wait", 0, 0
    ended = None
    while f < 60 * 60 * 30:
        if f % 60 == 0:
            e.setw(CONT1, 0); e.setw(CONT2, 0)
            for k in range(12):
                e.setb(G.rec(k) + 0x62, e.b(G.rec(k) + 0x62) & ~8)
        k2 = (e.w(ROUND), e.w(TEAMW), e.w(HG), e.w(AG))
        if k2[:2] != (key or (None, None))[:2]:
            att += 1
            key = k2
            log.append(f"attempt {att + 1}: round {k2[0]}, {'home' if k2[1] == 0 else 'away'} shoots,"
                       f" goals before {k2[2]}-{k2[3]}, shooter index {e.w(NUM)}")
            state = "wait"
            if att >= maxatt:
                ended = "stopped: attempt limit"; break
        if e.b(GMODE2) & 8 and not ended:
            ended = f"over (gmode2 bit 3) after round {e.w(ROUND)}, {'home' if e.w(TEAMW) == 0 else 'away'} last, goals {e.w(HG)}-{e.w(AG)}"
            e.run(240); e.screenshot(out / "end.png")
            break
        if not e.b(GMODE2) & 1:
            ended = "back to the title (gmode2 bit 0 clear)"; break
        # the pause menu between attempts: press START when the clock (shootout) isn't running for a while
        p = G.PUCK
        carried = e.b(p + 0x60) == 0
        y = e.w(p + 0x14); y = y - 0x10000 if y >= 0x8000 else y
        r = results[att] if 0 <= att < len(results) else "."
        if state == "wait" and carried:
            state = "had"
        x = e.w(p); x = x - 0x10000 if x >= 0x8000 else x
        if r == "M" and abs(y) > 200 and abs(x) < 60:      # a miss: kept out of the goal mouth all attempt
            e.setw(p, 150 if x >= 0 else (-150) & 0xFFFF); e.setw(p + 0x28, 0); e.setb(p + 0x60, 0xFF)
        if state == "had" and not carried and abs(y) > 120 and r == "G":
            s = 1 if y > 0 else -1
            for k in (5, 11):
                e.setw(G.rec(k), 120); e.setw(G.rec(k) + 0x14, (s * -200) & 0xFFFF)
            e.setw(p, 0 if r == "G" else 100); e.setw(p + 0x14, (s * 245) & 0xFFFF); e.setw(p + 0x18, 0)
            e.setw(p + 0x28, 0); e.setw(p + 0x2A, (s * 3000) & 0xFFFF); e.setw(p + 0x2C, 0)
            state = "done"
        menu_wait += 1
        e.run(1, hold=["START"] if menu_wait % 300 == 0 and state == "wait" and not carried else [])
        if carried:
            menu_wait = 0
        f += 1
        if f % 3600 == 0:
            lowload.breathe()
    if ended is None:
        ended = "nothing ended within the frames"
    log.append(ended)
    return log


def main():
    lowload.gentle()
    rom, out = sys.argv[1], Path(sys.argv[2])
    res = sys.argv[3] if len(sys.argv) > 3 else ""
    mx = int(sys.argv[4]) if len(sys.argv) > 4 else 24
    for line in run(rom, out, res, mx):
        print(line, flush=True)


if __name__ == "__main__":
    main()
