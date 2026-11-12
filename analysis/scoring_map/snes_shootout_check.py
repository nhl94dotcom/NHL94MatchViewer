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

On the 2 MB builds (SA-1 and the LoROM 32-team, 2026-11-12, NOSE4Web add97a6) also: the extra stats StartGame_go's
ClearTeamStats / ClearPlayerChecks clears there (players' checks for $E788 and against $E7BC, a byte each, posts $E7F0,
time on ice $E800, a word each), set to known values at period 3's last second (EXTRA_SEED) and read at the game's end;
the fight state FightGameStart clears (fighton $E700, ChkCnt $E702, OptFights $E708, fightinjany $E782) before and
after; and on the SA-1 builds BW-RAM $40:4800-$5FFF (the free room NOSE4Web saves into from $4810) sampled every 10
frames: each byte that changes, by when (before the shootout, in it, after it).

--pad (2026-11-12): pad 1 left on its team from the menus (snes_shootout_lock_check.person_start), never taken off: the
2 MB builds' computer-only shootouts crashed in round 1 in this harness (the LoROM 32-team build's own Shootout mode
too), with a pad on a team they play through.

python snes_shootout_check.py ROM OUT [--pad] [case ...]   (default: tie untied playoff)"""
import json
import sys
from pathlib import Path

import lowload
from snes_60fps_cvc import CLOCK, GSP, computer_only
from snes_ot_goal_check import GOALS, GOALS_P, PLAYMODE, TEAMS, start

SHOOTMODE, ROUND, SFLAGS = 0x1D81, 0x1D85, 0x15D8
KEEP = [(0x15D3, 0x1D53), (0x30F4, 0x347C)]
PCHF, PCHA, TMPOSTS, PTOI = 0xE788, 0xE7BC, 0xE7F0, 0xE800
FIGHT = {"fighton": 0xE700, "ChkCnt": 0xE702, "OptFights": 0xE708, "fightinjany": 0xE782}


def two_mb(rom):
    return len(Path(rom).read_bytes()) >= 0x200000


def seed_extra(m):
    """Known values in the extra stats: checks for 1 + k % 5, against 2 + k % 3 (bytes), posts 3 / 4, ice time 100 + k."""
    for k in range(0, 52, 2):
        m.setw(PCHF + k, (1 + k % 5) | (1 + (k + 1) % 5) << 8)
        m.setw(PCHA + k, (2 + k % 3) | (2 + (k + 1) % 3) << 8)
    m.setw(TMPOSTS, 3)
    m.setw(TMPOSTS + 2, 4)
    for k in range(52):
        m.setw(PTOI + 2 * k, 100 + k)


def extra(m):
    return {"checks for": sum((m.w(PCHF + k) & 0xFF) for k in range(52)),
            "checks against": sum((m.w(PCHA + k) & 0xFF) for k in range(52)),
            "posts": [m.w(TMPOSTS), m.w(TMPOSTS + 2)], "ice time (s)": sum(m.w(PTOI + 2 * k) for k in range(52)),
            "fight": {n: m.w(a) for n, a in FIGHT.items()}}


def snapshot(m):
    return {a: m.w(a) & 0xFF for lo, hi in KEEP for a in range(lo, hi)}   # bytes


def set_score(m, h, a):
    for x in (GOALS, GOALS + 2) + tuple(GOALS_P + 2 * i for i in range(8)):
        m.setw(x, 0)
    m.setw(GOALS, h)
    m.setw(GOALS + 2, a)
    m.setw(GOALS_P, h)
    m.setw(GOALS_P + 2, a)


PAD = False


def run_case(e, m, base, case, out, rom=None):
    e.unserialize(base)
    m.setw(PLAYMODE, 2 if case == "playoff" else 0)
    m.setw(GSP, 2)
    m.setw(CLOCK, 3)
    set_score(m, 3 if case == "untied" else 2, 2)
    big = rom is not None and two_mb(rom)
    if big:
        seed_extra(m)
    e.run(2)
    before = snapshot(m)
    extra_before = extra(m) if big else None
    bwfree = m.bw if m.sa1 else None
    bw0 = bytes(bwfree[0x4800:0x6000]) if bwfree is not None else None
    bw_seen, phase, so_seen = {}, "before", False
    teams = tuple(m.w(a) for a in TEAMS)
    prev, shots, over_at, ot_set, last, still = None, 0, None, False, None, 0
    log = []
    menu_pressed = False
    for f in range(0, 60 * 60 * 40, 10):
        e.run(10)
        if f % 300 == 0 and not PAD:
            computer_only(m)
        if f % 3600 == 0:
            lowload.breathe()
        g, so = m.w(GSP), m.w(SHOOTMODE)
        if so & 0xFF:
            so_seen, phase = True, "in the shootout"
        elif so_seen:
            phase = "after"
        if bw0 is not None:
            now = bytes(bwfree[0x4800:0x6000])
            if now != bw0:
                for i in range(len(now)):
                    if now[i] != bw0[i] and i not in bw_seen:
                        bw_seen[i] = (f, phase)
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
            extra_after = extra(m) if big else None
        if over_at is not None:
            if (f - over_at) % 240 == 0:
                e.screenshot(out / f"{case}_after_{(f - over_at) // 240:02d}.png")
                e.run(4, hold=["START"])
            if f - over_at > 60 * 40:
                break
    if over_at is None:
        after = snapshot(m)
        extra_after = extra(m) if big else None
    skip = {w + k for w in (GSP, CLOCK, GOALS, GOALS + 2) + tuple(GOALS_P + 2 * i for i in range(8)) for k in (0, 1)}
    changed = {f"${a:04X}": [before[a], after[a]] for a in before if before[a] != after[a] and a not in skip}
    res = {"case": case, "game over": over_at is not None, "final": [m.w(GOALS), m.w(GOALS + 2)],
           "teams same": tuple(m.w(a) for a in TEAMS) == teams, "changed words (but score, gsp, clock)": len(changed),
           "changed": dict(list(changed.items())[:60])}
    if big:
        res["extra stats and fight state (period 3's last second, the game's end)"] = [extra_before, extra_after]
    if bw0 is not None:
        runs = []
        for i in sorted(bw_seen):
            if runs and i == runs[-1][1] + 1 and bw_seen[i][1] == runs[-1][2]:
                runs[-1][1] = i
            else:
                runs.append([i, i, bw_seen[i][1], bw_seen[i][0]])
        res["BW-RAM $40:4800-$5FFF bytes changed (from, to, when, first frame)"] = [
            [f"$40:{0x4800 + a:04X}", f"$40:{0x4800 + b:04X}", w, f] for a, b, w, f in runs]
    print(json.dumps(res), flush=True)
    return res


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    global PAD
    args = sys.argv[3:]
    PAD = "--pad" in args
    cases = [c for c in args if c != "--pad"] or ["tie", "untied", "playoff"]
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    if PAD:
        from snes_shootout_lock_check import person_start
        e, m = person_start(rom, out)
    else:
        e, m = start(rom, 0, out)
    e.run(600)
    base = e.serialize()
    for case in cases:
        run_case(e, m, base, case, out, rom)


if __name__ == "__main__":
    main()
