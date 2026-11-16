"""NHL '95 (Genesis): NOSE4Web's overtime until a goal (2026-11-16, a961bb7: PeriodOver's move.w #4,(gsp).w at $8CB9E and
clockcont_0's beq.s .eog at $8CCDA made NOPs). From a live state (gen95_assist_check's): the period, clock, score and
mode set, then played on (START through screens that wait) until play runs again in a new overtime or the game ends.
Cases: a tied overtime with 3 s left in an exhibition regular game (OptPlayMode 0), the same flagged as a season game
(GameFlags bit 3, the season's playoff bit, SeasonDay+1 bit 5, clear), the same in season playoffs (bit 5 set), a
playoff game (OptPlayMode 2); a tied third period with 3 s left (regulation's end); an untied third period. Where a
new overtime starts, a goal is put in (the puck into the top net) and the result read.

python gen95_ot_check.py ROM STATE"""
import sys
from pathlib import Path

from emu import Emu
import gen95_assist_check as G

GSP, CLOCK, MODE, GAMEFLAGS, SEASONF, HM, AW, GMODE = 0xC020, 0xC022, 0xCC4C, 0xBF08, 0xD1A7, 0xC294, 0xC5FA, 0xBEF0


def play_on(e, frames=60 * 60 * 6):
    """Until a new overtime runs (gsp 3, the clock reset and running) or the game is over (gsp 4)."""
    last, still = None, 0
    for f in range(frames):
        e.run(1, hold=["START"] if still >= 150 and f % 150 == 0 else [])
        c = e.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        if e.w(GSP) >= 4:
            return f"game over (gsp {e.w(GSP)}), score {e.w(HM)}-{e.w(AW)}"
        if e.w(GSP) == 3 and c > 60 and not e.b(GMODE) & 1:
            c0 = c
            e.run(120)
            if e.w(CLOCK) < c0:
                return f"another overtime (gsp 3, clock {c0} and running), score {e.w(HM)}-{e.w(AW)}"
    return "nothing decided"


def goal(e):
    """The puck into the top net (home attacks up in odd periods; overtime: either way, so both nets tried)."""
    st = e.serialize()
    for y, vy in ((250, 3000), (-250, -3000)):
        e.unserialize(st)
        h0, a0 = e.w(HM), e.w(AW)
        for f in range(120):
            if f == 0:
                P = G.PUCK
                e.setw(P, 0); e.setw(P + 0x14, y & 0xFFFF); e.setw(P + 0x18, 0)
                e.setw(P + 0x28, 0); e.setw(P + 0x2A, vy & 0xFFFF); e.setb(P + 0x60, 0xFF)
                for k in (5, 11):                      # both goalies aside
                    e.setw(G.rec(k), 120); e.setw(G.rec(k) + 0x14, 0)
            e.run(1)
            if (e.w(HM), e.w(AW)) != (h0, a0):
                return True
    return False


def main():
    rom, state = sys.argv[1], sys.argv[2]
    e = Emu(rom)
    base = Path(state).read_bytes()
    cases = [("exhibition regular game, overtime tied 1-1", 0, False, False, 3, (1, 1)),
             ("season game (regular season), overtime tied 1-1", 0, True, False, 3, (1, 1)),
             ("season playoff game, overtime tied 1-1", 0, True, True, 3, (1, 1)),
             ("exhibition playoff game (play mode 2), overtime tied 1-1", 2, False, False, 3, (1, 1)),
             ("exhibition regular game, third period tied 2-2", 0, False, False, 2, (2, 2)),
             ("exhibition regular game, third period 2-1 (untied)", 0, False, False, 2, (2, 1))]
    for name, mode, season, splayoff, gsp, (h, a) in cases:
        e.unserialize(base)
        e.setw(MODE, mode)
        gf = e.b(GAMEFLAGS) & ~8 | (8 if season else 0)
        e.setb(GAMEFLAGS, gf)
        e.setb(SEASONF, e.b(SEASONF) & ~0x20 | (0x20 if splayoff else 0))
        e.setw(GSP, gsp); e.setw(CLOCK, 3); e.setw(HM, h); e.setw(AW, a)
        what = play_on(e)
        line = f"{name}: {what}"
        if what.startswith("another overtime"):
            again = play_on_after_goal = None
            if goal(e):
                again = play_on(e, 60 * 60 * 2)
                line += f"; a goal put in: {again}"
            else:
                line += "; no goal could be put in"
        print(line, flush=True)


if __name__ == "__main__":
    main()
