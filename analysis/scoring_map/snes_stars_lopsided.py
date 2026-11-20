"""Three stars after a lopsided game on McMarkis's 2 MB SNES builds (2026-11-20; NOSE4Web's question: a 10-0 win over
the computer gave all three stars to the losers). A computer game (shootout_savestate_check's Snes set-up) with each
period's clock cut to a few seconds; just before the end of the third, the stats are written to a lopsided game (the
score, each player's goals, assists and shots; STATS below), then the game works out the stars itself. Logs every
change of the stars' variables (star1-3 $1E2B, scores $1E31, starplayerend $1E21, stargoalieend $1E23, otgoalscorer
$1E1F), the formula on the stats, and screenshots of the stars screen.
python snes_stars_lopsided.py ROM OUT [home|away] [natural]   (the side that wins 10-0; natural: no stats written,
the losers' net left empty all game (tmgoalie $17AA/$17AC $FFFF every frame) and each period cut to 100 s)"""
import json
import sys
from pathlib import Path

import lowload
import shootout_savestate_check as SC

GOALS, ASSISTS, SHOTS, SCORE = 0x18EE, 0x1922, 0x1956, 0x178E
STARV = {"otgoalscorer": 0x1E1F, "starplayerend": 0x1E21, "stargoalieend": 0x1E23, "star1": 0x1E2B, "star2": 0x1E2D,
         "star3": 0x1E2F, "s1lo": 0x1E31, "s1hi": 0x1E33, "s2lo": 0x1E35, "s2hi": 0x1E37, "s3lo": 0x1E39, "s3hi": 0x1E3B}
# the winners (indexes within the team, 0-1 the goalies): goals, assists, shots; the losers' shots
WIN = {0: (0, 0, 0), 2: (4, 1, 9), 3: (3, 2, 7), 4: (2, 3, 6), 5: (1, 4, 5), 6: (0, 3, 3), 7: (0, 2, 2)}
LOSE = {2: (0, 0, 3), 3: (0, 0, 2), 4: (0, 0, 2), 5: (0, 0, 1)}


def setb(m, a, v):
    w = m.w(a)
    m.setw(a, (w & 0xFF00) | v)


def write_stats(m, winner):
    base_w, base_l = (0, 26) if winner == 0 else (26, 0)
    for i in range(52):
        for a in (GOALS, ASSISTS, SHOTS):
            setb(m, a + i, 0)
    lose_shots = sum(s for _, _, s in LOSE.values())
    win_shots = sum(s for _, _, s in WIN.values())
    for k, (g, a, s) in WIN.items():
        setb(m, GOALS + base_w + k, g); setb(m, ASSISTS + base_w + k, a); setb(m, SHOTS + base_w + k, s)
    for k, (g, a, s) in LOSE.items():
        setb(m, GOALS + base_l + k, g); setb(m, ASSISTS + base_l + k, a); setb(m, SHOTS + base_l + k, s)
    # goalies: goals against and shots against
    setb(m, GOALS + base_w, 0); setb(m, SHOTS + base_w, lose_shots)
    setb(m, GOALS + base_l, 10); setb(m, SHOTS + base_l, win_shots)
    m.setw(SCORE + 2 * winner, 10)
    m.setw(SCORE + 2 * (1 - winner), 0)


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    winner = 1 if len(sys.argv) > 3 and sys.argv[3] == "away" else 0
    natural = "natural" in sys.argv[4:]
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    S = SC.Snes(rom, 0)
    e, m = S.e, S.m
    S.new_game(0)
    print("sa1", m.sa1, "OptPerlen", m.w(0x34C2), flush=True)
    log, prev, f, last, still, cut, wrote, end = [], None, 0, None, 0, set(), None, None
    while f < 60 * 60 * 30:
        if f % 300 == 0:
            S.computer()
        if f % 3600 == 0:
            lowload.breathe()
        g, c = S.gsp(), S.clock()
        if g not in cut and 30 < c < 2000:
            m.setw(S.CLOCK, 100 if natural else 20 if g == 2 else 6)
            cut.add(g)
            print("cut period", g, flush=True)
        if natural and end is None and g < 3:
            m.setw(0x17AA + 2 * (1 - winner), 0xFFFF)
            if wrote is None:
                wrote = 0
        if not natural and g == 2 and 0 < c <= 8 and wrote is None:
            write_stats(m, winner)
            wrote = f
            print("stats written at", f, "clock", c, json.dumps(S.stats()[3]), flush=True)
        still = still + 1 if c == last else 0
        last = c
        press = still >= 900 and still % 900 == 0 and (end is None or f - end > 1500)
        e.run(4 if press else 1, hold=["START"] if press else [])
        f += 1
        v = {k: m.w(a) for k, a in STARV.items()}
        if v != prev:
            log.append((f, v))
            if prev is not None:
                print(f, json.dumps(v), flush=True)
            prev = v
            if wrote is not None and end is None and f > wrote + 60 and (v["s1lo"], v["s1hi"]) != (log[0][1]["s1lo"], log[0][1]["s1hi"]):
                end = f
                st = S.stats()
                first = dict(stats=dict(goals=st[0], assists=st[1], shots=st[2], score=st[3]), formula=S.star_formula(st, 0), game=v)
                print("STARS", json.dumps(first), flush=True)
        if end is not None and f - end in (5, 30, 90, 180, 300):
            e.screenshot(out / f"stars_{winner}{'n' if natural else ''}_{f - end:03d}.png")
        if end is not None and f - end > 400:
            break
    res = dict(winner=["home", "away"][winner], first=first if end else None, log=log)
    (out / f"stars_{winner}{'n' if natural else ''}.json").write_text(json.dumps(res))


if __name__ == "__main__":
    main()
