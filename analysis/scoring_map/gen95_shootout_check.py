"""NHL '95 (Genesis): NOSE4Web's shootouts for tied regular-season games (2026-11-16, e4790c2: *_shootout_after_ot.bin,
*_shootout_after_p3.bin; the saved state at $FFF000 (mark byte) and $FFF002 on: both team structs, $6CC bytes, and
ScoreSumbytes). From a live state (gen95_assist_check's mkstate; the ROM powered on first, since the core's states
leave out save RAM, where the shootout's shooter lists come from), one case at a time: the mode and season flags set,
the period set with 60 s left at 0-0, a goal put in at each net through the game's own Goal (so the scoring summary,
the shots and the goal stats are real; one more home goal for the untied cases), then 3 s left; played on with the
computer on both sides (cont1team / cont2team and the person flags cleared every second), START when nothing moves for
5 s, until the game is over (gsp 4) and 20 s of end screens, or 30 minutes of frames.

Logged: the shootout's start (gmode2 bit 0, the mark) and gsp then, each attempt (round, team, goal counts), its end;
the final score; both team structs, ScoreSumbytes and the scoring summary at the end against the frame before the
shootout started (expected: the same but the winner's goals +1); the $FFF000-$FFF6CF block changing at any time no
shootout runs; screenshots of the end screens. RESULTS forces attempts as gen95_shootout_mode_check.py does (G goal, M
miss, '.' as played).

python gen95_shootout_check.py ROM STATE OUT_DIR CASE [RESULTS]
CASES: ot_tie, p3_tie, ot_tie_season, p3_tie_season, playoff_ot_tie, season_playoff_ot_tie, playoff_p3_tie,
season_playoff_p3_tie, p3_untied, ot_untied. In a second overtime (playoffs) a home goal is put in."""
import sys
from pathlib import Path

import numpy as np

from emu import Emu
import gen95_assist_check as G
import lowload

GSP, CLOCK, MODE, GAMEFLAGS, SEASONF, HM, AW, GMODE = 0xC020, 0xC022, 0xCC4C, 0xBF08, 0xD1A7, 0xC294, 0xC5FA, 0xBEF0
GMODE2, ROUND, TEAMW, HG, AG, SUMB, SUM, MARK = 0xBF00, 0xD184, 0xD1A0, 0xD180, 0xD182, 0xC02C, 0xC02E, 0xF000
TM, TMLEN, TMSIZE, CONT1, CONT2 = 0xC288, 0x6CC, 0x366, 0xBF4C, 0xBF4E
CASES = {  # mode, season, season playoffs, gsp, untied
    "ot_tie": (0, False, False, 3, False), "p3_tie": (0, False, False, 2, False),
    "ot_tie_season": (0, True, False, 3, False), "p3_tie_season": (0, True, False, 2, False),
    "playoff_ot_tie": (2, False, False, 3, False), "season_playoff_ot_tie": (0, True, True, 3, False),
    "p3_untied": (0, False, False, 2, True), "ot_untied": (0, False, False, 3, True),
    "playoff_p3_tie": (2, False, False, 2, False), "season_playoff_p3_tie": (0, True, True, 2, False)}


def block(e, a, n):
    return np.frombuffer(e.ram, np.uint8)[(a + np.arange(n)) ^ 1].copy()


def computer(e):
    e.setw(CONT1, 0); e.setw(CONT2, 0)
    for k in range(12):
        e.setb(G.rec(k) + 0x62, e.b(G.rec(k) + 0x62) & ~8)


def put_goal(e, home):
    """A goal for one team through the game's own Goal: the puck into the net that team attacks (found by trying; tried
    again every half second for 20 s, since a carried puck can't be set loose)."""
    for _ in range(40):
        if _put_goal(e, home):
            return True
        for f in range(30):
            if f == 0:
                computer(e)
            e.run(1)
    return False


def _put_goal(e, home):
    st = e.serialize()
    for s in (1, -1):
        e.unserialize(st)
        h0, a0 = e.w(HM), e.w(AW)
        p = G.PUCK
        for k in (5, 11):
            e.setw(G.rec(k), 120); e.setw(G.rec(k) + 0x14, (s * -200) & 0xFFFF)
        e.setw(p, 0); e.setw(p + 0x14, (s * 245) & 0xFFFF); e.setw(p + 0x18, 0); e.setb(p + 0x60, 0xFF)
        e.setw(p + 0x28, 0); e.setw(p + 0x2A, (s * 3000) & 0xFFFF); e.setw(p + 0x2C, 0)
        for f in range(90):
            e.run(1)
            if (e.w(HM), e.w(AW)) != (h0, a0):
                break
        if (e.w(HM) > h0) if home else (e.w(AW) > a0):
            for f in range(60 * 40):           # until play runs again (the faceoff after the goal)
                if f % 60 == 0:
                    computer(e)
                c = e.w(CLOCK)
                e.run(1, hold=["START"] if f % 300 == 299 else [])
                if f > 300 and e.w(CLOCK) < c:
                    return True
            return True
    e.unserialize(st)
    return False


def main():
    rom, state, out, case = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4]
    results = sys.argv[5] if len(sys.argv) > 5 else ""
    lowload.gentle()
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    e.run(1500)
    e.unserialize(Path(state).read_bytes())
    mode, season, splay, gsp, untied = CASES[case]
    e.setw(MODE, mode)
    e.setb(GAMEFLAGS, e.b(GAMEFLAGS) & ~8 | (8 if season else 0))
    e.setb(SEASONF, e.b(SEASONF) & ~0x20 | (0x20 if splay else 0))
    e.setw(GSP, 2); e.setw(CLOCK, 90); e.setw(HM, 0); e.setw(AW, 0)        # the goals in the third period
    ok = [put_goal(e, True), put_goal(e, False)] + ([put_goal(e, True)] if untied and gsp == 2 else [])
    e.setw(CLOCK, 3)
    print(f"{Path(rom).name} {case}: third period, goals put in {ok}, score {e.w(HM)}-{e.w(AW)}, ScoreSumbytes {e.w(SUMB)},"
          f" mode {mode}, season {season}, season playoffs {splay}; {'overtime cut to 3 s' if gsp == 3 else 'no overtime cut'}"
          f"{', a home goal in overtime' if untied and gsp == 3 else ''}")
    ot_starts, c_prev, armed = 0, None, False
    ref = block(e, MARK, 0x6D0)
    outside, so_on, so_start, key, att, state_, last, still, f, over_at = 0, False, None, None, -1, "wait", None, 0, 0, None
    prev = (block(e, TM, TMLEN), e.w(SUMB), block(e, SUM, 0x100), e.w(GSP), (e.w(HM), e.w(AW)))
    while f < 60 * 60 * 30:
        if f % 60 == 0:
            computer(e)
        on = bool(e.b(GMODE2) & 1)
        if on and not so_on:
            so_start = dict(tm=prev[0], sumb=prev[1], sum=prev[2], gsp=prev[3], score=prev[4])
            print(f"  shootout starts after gsp {prev[3]} ended at {prev[4][0]}-{prev[4][1]} (gsp now {e.w(GSP)}), mark {e.b(MARK)};"
                  f" saved copy = the structs before it: {bool((block(e, MARK + 2, TMLEN) == so_start['tm']).all())},"
                  f" saved ScoreSumbytes {e.w(MARK + 2 + TMLEN)} (was {so_start['sumb']})")
        if so_on and not on:
            tm = block(e, TM, TMLEN)
            d = np.nonzero(tm != so_start["tm"])[0]
            win = "home" if e.w(HG) > e.w(AG) else "away"
            print(f"  shootout over: shootout goals {e.w(HG)}-{e.w(AG)} ({win} wins), score {e.w(HM)}-{e.w(AW)} (before it"
                  f" {so_start['score'][0]}-{so_start['score'][1]}), gsp {e.w(GSP)}, mark {e.b(MARK)}; ScoreSumbytes {e.w(SUMB)}"
                  f" (before {so_start['sumb']}), summary the same: {bool((block(e, SUM, so_start['sumb']) == so_start['sum'][:so_start['sumb']]).all())};"
                  f" team-struct bytes changed: {['home' if x < TMSIZE else 'away'] and [('H' if x < TMSIZE else 'A') + f'+${x % TMSIZE:03X}' for x in d]}")
            ref = block(e, MARK, 0x6D0)
        so_on = on
        if not on:
            now = block(e, MARK, 0x6D0)
            if (now != ref).any():
                outside += 1
                if outside == 1:
                    print(f"  $F000 block changed with no shootout running, gsp {e.w(GSP)}: offsets {list(np.nonzero(now != ref)[0][:8])}")
                ref = now
        if on:
            k2 = (e.w(ROUND), e.w(TEAMW))
            if k2 != key:
                key, att, state_ = k2, att + 1, "wait"
                print(f"    attempt {att + 1}: round {k2[0]}, {'home' if k2[1] == 0 else 'away'}, goals before {e.w(HG)}-{e.w(AG)}")
            p = G.PUCK
            carried = e.b(p + 0x60) == 0
            y = e.sw(p + 0x14); x = e.sw(p)
            r = results[att] if 0 <= att < len(results) else "."
            if state_ == "wait" and carried:
                state_ = "had"
            if r == "M" and abs(y) > 200 and abs(x) < 60:
                e.setw(p, 150 if x >= 0 else (-150) & 0xFFFF); e.setw(p + 0x28, 0); e.setb(p + 0x60, 0xFF)
            if state_ == "had" and not carried and abs(y) > 120 and r == "G":
                s = 1 if y > 0 else -1
                for k in (5, 11):
                    e.setw(G.rec(k), 120); e.setw(G.rec(k) + 0x14, (s * -200) & 0xFFFF)
                e.setw(p, 0); e.setw(p + 0x14, (s * 245) & 0xFFFF); e.setw(p + 0x18, 0)
                e.setw(p + 0x28, 0); e.setw(p + 0x2A, (s * 3000) & 0xFFFF); e.setw(p + 0x2C, 0)
                state_ = "done"
        c_now = e.w(CLOCK)
        if not on and e.w(GSP) == 3 and c_prev is not None and c_now > c_prev + 50:
            armed = True                      # the clock was reset (it is reset again at the period's real start)
        if armed and not on and e.w(GSP) == 3 and c_prev is not None and c_now < c_prev:
            armed = False                     # the overtime's clock is running
            ot_starts += 1
            print(f"  overtime {ot_starts} starts, clock {c_now}, score {e.w(HM)}-{e.w(AW)}")
            if ot_starts == 1 and gsp == 3:
                if untied:
                    print(f"  overtime: a home goal put in: {put_goal(e, True)}")
                else:
                    e.setw(CLOCK, 3)
            elif ot_starts >= 2:
                print(f"  overtime {ot_starts}: a home goal put in: {put_goal(e, True)}")
        c_prev = c_now
        if not on:
            prev = (block(e, TM, TMLEN), e.w(SUMB), block(e, SUM, 0x100), e.w(GSP), (e.w(HM), e.w(AW)))
        sig = (e.w(CLOCK), e.w(G.PUCK), e.w(G.PUCK + 0x14))
        still = still + 1 if sig == last else 0
        last = sig
        e.run(1, hold=["START"] if still >= 300 and still % 300 == 0 else [])
        f += 1
        if e.w(GSP) >= 4 and over_at is None:
            over_at = f
            print(f"  game over (gsp 4), score {e.w(HM)}-{e.w(AW)}, shootout ran: {so_start is not None}")
        if over_at is not None and f - over_at in (300, 900):
            e.screenshot(out / f"{case}_end{f - over_at}.png")
        if over_at is not None and f - over_at > 900:
            break
        if f % 3600 == 0:
            lowload.breathe()
    if over_at is None:
        print(f"  not over after {f} frames: gsp {e.w(GSP)}, score {e.w(HM)}-{e.w(AW)}, gmode2 {e.b(GMODE2):02X}")
    print(f"  $FFF000-$FFF6CF changed with no shootout running: {'never' if outside == 0 else f'{outside} times'}")


if __name__ == "__main__":
    main()
