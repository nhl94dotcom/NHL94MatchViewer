"""NHL '95 (Genesis): a real season game through NOSE4Web's overtime and shootout builds (2026-11-16). Power-on, Game
Setup's play mode 6 (New Season; W18 lists it under another name), START through Season Setup to Games Today, A on the
first game (played by people), START to Season Options, START (Play Games) and on until play runs; then the computer on
both sides, the third period at 0-0 with 90 s left, a goal put in for each team through the game's own Goal, 3 s left;
the overtime cut to 3 s once its clock runs (the cut skipped with --full-ot); a shootout's attempts forced by RESULTS
(G goal, M miss, as gen95_shootout_mode_check.py); a second overtime ended by a home goal. After the game START until
the season screens are back, then six more START presses (days simulated). Printed: the game's teams and end, the
save RAM bytes that changed in the standings ($1AF6 on, 3 bytes a team: wins, ties, losses, as RecordTeamResult) by
team, and whether $FFF000-$FFF6CF ever changed while no shootout ran, from power-on to the end (the season screens,
the simulated days).

python gen95_season_check.py ROM OUT_DIR [RESULTS] [--full-ot]"""
import sys
from pathlib import Path
import ctypes as C

import numpy as np

from emu import Emu
import gen95_assist_check as G
import gen95_shootout_check as S
import lowload

HOMET, VIST = 0xBF54, 0xBF56
STAND = slice(0x1AF6 * 2, (0x1AF6 + 26 * 3) * 2)    # the standings in the core's save RAM (each byte doubled)


def saveram(e):
    L = e.lib
    ptr, size = L.retro_get_memory_data(0), L.retro_get_memory_size(0)
    return np.frombuffer((C.c_ubyte * size).from_address(ptr), np.uint8).copy()


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    args = [a for a in sys.argv[3:] if not a.startswith("--")]
    results = args[0] if args else ""
    full_ot = "--full-ot" in sys.argv
    lowload.gentle()
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    e.run(1500)
    ref = S.block(e, S.MARK, 0x6D0)
    outside = [0]
    was_on = [False]

    def watch():
        nonlocal ref
        on = bool(e.b(S.GMODE2) & 1)
        if was_on[0] and not on:
            ref = S.block(e, S.MARK, 0x6D0)          # the shootout's own writes end here
        was_on[0] = on
        if not on:
            now = S.block(e, S.MARK, 0x6D0)
            if (now != ref).any():
                outside[0] += 1
                if outside[0] <= 3:
                    print(f"  $F000 block changed with no shootout running (gsp {e.w(S.GSP)}): offsets"
                          f" {list(np.nonzero(now != ref)[0][:8])}")
                ref = now

    def step(n, hold=()):
        for i in range(n):
            e.run(1, hold=list(hold))
            watch()

    for _ in range(3):
        step(6, ["START"]); step(200)
    e.setb(0xD282, 6); step(60)
    step(6, ["START"]); step(400)              # Season Setup
    step(6, ["START"]); step(400)              # Games Today
    step(6, ["A"]); step(120)                   # the first game: people
    e.screenshot(out / "games_today.png")
    step(6, ["START"]); step(400)              # Season Options
    step(6, ["START"]); step(300)              # Play Games
    f, last = 0, None
    while f < 60 * 60 * 3:                      # until play runs
        c = e.w(S.CLOCK)
        step(1, ["START"] if f % 300 == 299 else [])
        f += 1
        if e.w(S.GSP) == 0 and last is not None and 0 < e.w(S.CLOCK) < last:
            break
        last = c
    print(f"{Path(rom).name}: in play after {f} frames, home team {e.w(HOMET)}, away {e.w(VIST)}, GameFlags {e.b(S.GAMEFLAGS):02X},"
          f" season flags {e.b(S.SEASONF):02X}, OptPlayMode {e.w(S.MODE)}")
    sr0 = saveram(e)
    S.computer(e)
    e.setw(S.GSP, 2); e.setw(S.CLOCK, 90); e.setw(S.HM, 0); e.setw(S.AW, 0)
    ok = [S.put_goal(e, True), S.put_goal(e, False)]
    if e.w(S.HM) != e.w(S.AW):                  # a goal that wouldn't go in: the tie set in RAM
        e.setw(S.AW, e.w(S.HM)); ok.append("tie set in RAM")
    e.setw(S.CLOCK, 3)
    print(f"  third period: goals put in {ok}, {e.w(S.HM)}-{e.w(S.AW)}")
    ot, armed, cprev, so_on, key, att, st, still, sig0, over = 0, False, None, False, None, -1, "wait", 0, None, None
    f = 0
    while f < 60 * 60 * 30:
        if f % 60 == 0:
            S.computer(e)
        on = bool(e.b(S.GMODE2) & 1)
        c = e.w(S.CLOCK)
        if not on and e.w(S.GSP) == 3 and cprev is not None and c > cprev + 50:
            armed = True
        if armed and not on and e.w(S.GSP) == 3 and c < cprev:
            armed = False; ot += 1
            print(f"  overtime {ot} runs, clock {c}, {e.w(S.HM)}-{e.w(S.AW)}")
            if ot == 1 and not full_ot:
                e.setw(S.CLOCK, 3)
            elif ot >= 2:
                print(f"  overtime {ot}: a home goal put in: {S.put_goal(e, True)}")
        cprev = e.w(S.CLOCK)
        if on and not so_on:
            print(f"  shootout starts, {e.w(S.HM)}-{e.w(S.AW)}")
        if so_on and not on:
            print(f"  shootout over: shootout goals {e.w(S.HG)}-{e.w(S.AG)}, score {e.w(S.HM)}-{e.w(S.AW)}")
        so_on = on
        if on:
            k2 = (e.w(S.ROUND), e.w(S.TEAMW))
            if k2 != key:
                key, att, st = k2, att + 1, "wait"
            p = G.PUCK
            carried = e.b(p + 0x60) == 0
            y, x = e.sw(p + 0x14), e.sw(p)
            r = results[att] if 0 <= att < len(results) else "."
            if st == "wait" and carried:
                st = "had"
            if r == "M" and abs(y) > 200 and abs(x) < 60:
                e.setw(p, 150 if x >= 0 else (-150) & 0xFFFF); e.setw(p + 0x28, 0); e.setb(p + 0x60, 0xFF)
            if st == "had" and not carried and abs(y) > 120 and r == "G":
                s = 1 if y > 0 else -1
                for k in (5, 11):
                    e.setw(G.rec(k), 120); e.setw(G.rec(k) + 0x14, (s * -200) & 0xFFFF)
                e.setw(p, 0); e.setw(p + 0x14, (s * 245) & 0xFFFF); e.setw(p + 0x18, 0)
                e.setw(p + 0x28, 0); e.setw(p + 0x2A, (s * 3000) & 0xFFFF); e.setw(p + 0x2C, 0)
                st = "done"
        sig = (e.w(S.CLOCK), e.w(G.PUCK), e.w(G.PUCK + 0x14))
        still = still + 1 if sig == sig0 else 0
        sig0 = sig
        step(1, ["START"] if still >= 300 and still % 300 == 0 else [])
        f += 1
        if e.w(S.GSP) >= 4 and over is None:
            over = f
            print(f"  game over: {e.w(S.HM)}-{e.w(S.AW)}")
        if over is not None:
            now = saveram(e)[STAND]
            if (now != sr0[STAND]).any():
                step(120)
                break
            if f - over > 60 * 60 * 3:
                print("  no standings write within 3 minutes of frames after the game"); break
        if f % 3600 == 0:
            lowload.breathe()
    e.screenshot(out / "after_game.png")
    sr1 = saveram(e)
    for _ in range(6):
        step(6, ["START"]); step(400)
    e.screenshot(out / "later.png")
    d = np.nonzero(sr0 != sr1)[0]
    print(f"  save RAM: {len(sr0)} bytes, {len(d)} changed from the game's start to its end screens; first changed indexes {[hex(x) for x in d[:16]]}")
    for scale, off in ((2, 1),):
        base = 0x1AF6 * scale + off
        hits = [x for x in d if base <= x < base + 26 * 3 * scale]
        if hits:
            print(f"  standings changes (save RAM index = offset x {scale} + {off}):")
            for x in hits:
                rel = (x - base) // scale
                print(f"    team {rel // 3} {'wins ties losses'.split()[rel % 3]}: {sr0[x]} -> {sr1[x]}")
    print(f"  $FFF000-$FFF6CF changed with no shootout running, power-on to the end: {'never' if outside[0] == 0 else f'{outside[0]} times'}")


if __name__ == "__main__":
    main()
