"""NOSE4Web's SNES shootout for tied regular-season games, played (2026-11-11, 76802d1: NHL94_shootout.smc (after one
overtime), NHL94_shootout_after_period_3.smc, and the Classic copies). PeriodOver's lda #4 / sta gsp after overtime
(or its tie test after period 3) calls code that saves what PlayShootout's StartGame_go clears ($15D3-$1D52,
$30F4-$347B, lastperiod $1EAD) to $7E:F100 up, runs PlayShootout, reads the winner from the scores, puts everything
back, gives the winners one goal and runs PeriodOver again, which ends the game.

A computer game (snes_ot_goal_check.start), then each case from the same saved state:
- `tie`: regular season (OptPlayMode $34BC = 0), period 3 (gsp $1630 = 2) with 3 s left, 2-2 (the goals words $178E
  and the first period's): expected a shootout at once (after period 3) or overtime then a shootout (after one
  overtime: overtime's clock set to 3 s when it starts and the score kept tied until then);
- `untied`: the same at 3-2: the game ends, no shootout;
- `playoff`: the tie in the playoffs (OptPlayMode 2): overtime, no shootout.
Each case runs until the game is over (gsp 4) and 40 s (real) more, or 40 minutes (real); printed as they change:
gsp, shootoutmode ($1D81), the shootout round ($1D85), the score; screenshots every 2 s (real) while shootoutmode is
on and at each change, and of the screens after the game (START every 4 s). The team stats and lines ($15D3-$1D52, but
the score and gsp) and the scoring summary ($30F4-$347B) compared from period 3's last second to the game's end: the
words that changed.

python snes_shootout_check.py ROM OUT [case ...]   (default: tie untied playoff)"""
import json
import sys
from pathlib import Path

import lowload
from snes_60fps_cvc import CLOCK, GSP, computer_only
from snes_ot_goal_check import GOALS, GOALS_P, PLAYMODE, TEAMS, start

SHOOTMODE, ROUND, SFLAGS = 0x1D81, 0x1D85, 0x15D8
KEEP = [(0x15D3, 0x1D53), (0x30F4, 0x347C)]


def snapshot(m):
    return {a: m.w(a) & 0xFF for lo, hi in KEEP for a in range(lo, hi)}   # bytes


def set_score(m, h, a):
    for x in (GOALS, GOALS + 2) + tuple(GOALS_P + 2 * i for i in range(8)):
        m.setw(x, 0)
    m.setw(GOALS, h)
    m.setw(GOALS + 2, a)
    m.setw(GOALS_P, h)
    m.setw(GOALS_P + 2, a)


def run_case(e, m, base, case, out):
    e.unserialize(base)
    m.setw(PLAYMODE, 2 if case == "playoff" else 0)
    m.setw(GSP, 2)
    m.setw(CLOCK, 3)
    set_score(m, 3 if case == "untied" else 2, 2)
    e.run(2)
    before = snapshot(m)
    teams = tuple(m.w(a) for a in TEAMS)
    prev, shots, over_at, ot_set, last, still = None, 0, None, False, None, 0
    log = []
    menu_pressed = False
    for f in range(0, 60 * 60 * 40, 10):
        e.run(10)
        if f % 300 == 0:
            computer_only(m)
        if f % 3600 == 0:
            lowload.breathe()
        g, so = m.w(GSP), m.w(SHOOTMODE)
        if g == 3 and not ot_set and case != "untied":
            if 10 < m.w(CLOCK) < 299:                    # overtime's clock running (after its faceoff set it to
                m.setw(CLOCK, 3)                         # 5:00): 3 s left, still tied
                set_score(m, 2, 2)
                ot_set = True
        c = m.w(CLOCK)
        still = still + 10 if c == last else 0
        last = c
        if still >= 900 and not so:
            e.run(4, hold=["START"])
            still = 0
        # the shootout's menu ("Resume Shootout", sflags $0400) waits for pad 1 (sfpj): B held 8 frames (shorter
        # presses were lost); paused (bit 0): START
        # (once: later presses, B again while it runs, sent the game back to Game Setup; the menu between shooters
        # goes on by itself)
        if so and not menu_pressed and m.w(SFLAGS) & 0x400:
            e.run(30)
            e.run(8, hold=["B"])
            menu_pressed = True
            log.append(f"f{f}: B pressed once at the shootout's opening menu")
        st = (g, so & 0xFF, m.w(ROUND), m.w(GOALS), m.w(GOALS + 2))
        if st != prev:
            line = f"{case} f{f}: gsp {st[0]} shootoutmode {st[1]} round {st[2]} score {st[3]}-{st[4]} clock {c}"
            print(line, flush=True)
            log.append(line)
            e.screenshot(out / f"{case}_{shots:03d}_f{f}.png")
            shots += 1
            prev = st
        elif so and f % 120 == 0 and shots < 300:
            e.screenshot(out / f"{case}_{shots:03d}_f{f}.png")
            shots += 1
        if g >= 4 and over_at is None:
            over_at = f
            after = snapshot(m)
        if over_at is not None:
            if (f - over_at) % 240 == 0:
                e.screenshot(out / f"{case}_after_{(f - over_at) // 240:02d}.png")
                e.run(4, hold=["START"])
            if f - over_at > 60 * 40:
                break
    if over_at is None:
        after = snapshot(m)
    skip = {w + k for w in (GSP, CLOCK, GOALS, GOALS + 2) + tuple(GOALS_P + 2 * i for i in range(8)) for k in (0, 1)}
    changed = {f"${a:04X}": [before[a], after[a]] for a in before if before[a] != after[a] and a not in skip}
    res = {"case": case, "game over": over_at is not None, "final": [m.w(GOALS), m.w(GOALS + 2)],
           "teams same": tuple(m.w(a) for a in TEAMS) == teams, "changed words (but score, gsp, clock)": len(changed),
           "changed": dict(list(changed.items())[:60])}
    print(json.dumps(res), flush=True)
    return res


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    cases = sys.argv[3:] or ["tie", "untied", "playoff"]
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    e, m = start(rom, 0, out)
    e.run(600)
    base = e.serialize()
    for case in cases:
        run_case(e, m, base, case, out)


if __name__ == "__main__":
    main()
