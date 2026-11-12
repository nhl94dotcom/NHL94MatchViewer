"""NOSE4Web's SNES bodycheck statistics, played (2026-11-12, 5c9609b: NHL94_bodychecks.smc, SDL16_bodychecks.smc,
nhl94snes_SA1_bodychecks.sfc). The counting is the Vault's: FallDown's `lda tmchecks,y` becomes a jsr that adds 1 to
the checker's byte (a3) at $168E and the hit player's (a2) at $16C2, 26 a team, the roster place from pnum $12A3 read
as a word (SA-1: low RAM in BW-RAM, through snes_60fps_cvc.Mem). A computer game (snes_ot_goal_check.start: penalties
on, the computer on both sides), 5-minute periods, START whenever the clock has stood 15 s (real), watched every 2
frames:
- at each rise of a team's checks (tmchecks $17B6 / $17B8): which given and taken bytes rose; the given one must be a
  player of the checking team, the taken one of the other, and the two on the ice (objects 0-11 by pnum and pfteam
  $1503) within REACH of each other; their pnum words (high byte 0?);
- every sample: the given sums equal the team checks, the taken sums the other team's; any write in $168E-$16F5 that
  is not a rise of one byte at a check;
- at the game's end: Player Stats (the pause menu's stats screens are reached from the end-of-game menu) screenshotted
  for each team and sort, and the counts printed by roster place;
- then START on into the next game: the counts at its first sample of play (all 0?).

SPLASH (SDL16: a league splash screen before the title): START pressed past it first, then the game started as
snes_ot_goal_check.start does.

python snes_bodycheck_check.py ROM OUT [SPLASH]"""
import json
import math
import sys
from pathlib import Path

import lowload
from snes_60fps_cvc import CLOCK, GSP, Mem, computer_only
from snes_ot_goal_check import start
import menu_shots as M
from snes_60fps_cvc import CLOCKSTOP, OPTPEN, SEED


def start_after_splash(rom, out):
    """snes_ot_goal_check.start with START pressed past a league splash screen first (SDL16)."""
    e = M.emulator(rom)
    m = Mem(e, rom)
    M.play(e, "w1500 START w240 START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", out)
    M.play(e, "START w240 START w200 w2400", out)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    m.setw(OPTPEN, 2)
    computer_only(m)
    m.setw(SEED, 0x9E37)
    m.setw(SEED + 2, (0x7F4A * 3) & 0xFFFF)
    return e, m

GIVEN, TAKEN, PNUM, PFTEAM, XPOS, YPOS, CHECKS, PENLEN, SPA = 0x168E, 0x16C2, 0x12A3, 0x1503, 0x0D55, 0x0DB7, 0x17B6, 0x163C, 0x11A3
REACH = 48


def counts(m):
    g = [m.w(GIVEN + j) & 0xFF for j in range(52)]
    t = [m.w(TAKEN + j) & 0xFF for j in range(52)]
    return g, t


def objects(m):
    """Each roster place's objects (a list: an idle slot can keep an old pnum, SPA 0, 2026-11-12 on the SA-1)."""
    out = {}
    for k in range(12):
        p = m.w(PNUM + 2 * k)
        side = 1 if m.w(PFTEAM + 2 * k) else 0
        if p < 26:
            out.setdefault(26 * side + p, []).append((k, p, _s(m.w(XPOS + 2 * k)), _s(m.w(YPOS + 2 * k))))
    return out


def _s(v):
    return v - 0x10000 if v & 0x8000 else v


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    e, m = start_after_splash(rom, out) if len(sys.argv) > 3 else start(rom, 0, out)
    g0, t0 = counts(m)
    res = {"rom": Path(rom).name, "counts at the first sample of play (given, taken sums)": [sum(g0), sum(t0)]}
    prev_g, prev_t = g0, t0
    prev_c = [m.w(CHECKS), m.w(CHECKS + 2)]
    events, bad, sums_bad, highs, stray = [], [], 0, 0, []
    last, still, over_at, f = None, 0, None, 0
    while f < 60 * 60 * 60:
        e.run(2)
        f += 2
        if f % 600 == 0:
            computer_only(m)
        if f % 7200 == 0:
            lowload.breathe()
        g, t = counts(m)
        c = [m.w(CHECKS), m.w(CHECKS + 2)]
        if g != prev_g or t != prev_t or c != prev_c:
            dg = [j for j in range(52) if g[j] != prev_g[j]]
            dt = [j for j in range(52) if t[j] != prev_t[j]]
            rises = [s for s in (0, 1) if c[s] > prev_c[s]]
            if rises and m.w(GSP) < 4:
                s = rises[0]
                ok = (len(dg) == 1 and len(dt) == 1 and g[dg[0]] == prev_g[dg[0]] + 1 and t[dt[0]] == prev_t[dt[0]] + 1
                      and dg[0] // 26 == s and dt[0] // 26 == 1 - s)
                ob = objects(m)
                dist = None
                if ok and dg[0] in ob and dt[0] in ob:
                    dist = round(min(math.hypot(x[2] - y[2], x[3] - y[3]) for x in ob[dg[0]] for y in ob[dt[0]]))
                ev = {"f": f, "team": s, "given": dg, "taken": dt, "dist": dist}
                events.append(ev)
                if not ok or dist is None or dist > REACH:
                    ev["objects (k, pnum, team, x, y, SPA)"] = [
                        (k, m.w(PNUM + 2 * k), m.w(PFTEAM + 2 * k), _s(m.w(XPOS + 2 * k)), _s(m.w(YPOS + 2 * k)),
                         hex(m.w(SPA + 2 * k))) for k in range(12)]
                    e.screenshot(out / f"odd_check_f{f}.png")
                    bad.append(ev)
            elif dg or dt:
                stray.append({"f": f, "gsp": m.w(GSP), "given": [(j, prev_g[j], g[j]) for j in dg],
                              "taken": [(j, prev_t[j], t[j]) for j in dt], "checks": [prev_c, c]})
            prev_g, prev_t, prev_c = g, t, c
        if m.w(GSP) < 4 and (sum(g[:26]) != c[0] or sum(g[26:]) != c[1] or sum(t[26:]) != c[0] or sum(t[:26]) != c[1]):
            sums_bad += 1
        for k in range(12):
            w = m.w(PNUM + 2 * k)
            if w >> 8 and w != 0xFFFF:
                highs += 1
        cl = m.w(CLOCK)
        still = still + 2 if cl == last else 0
        last = cl
        if m.w(GSP) >= 4:
            if over_at is None:
                over_at = f
                res["at the game's end: team checks, given sums, taken sums"] = [c, [sum(g[:26]), sum(g[26:])],
                                                                                  [sum(t[:26]), sum(t[26:])]]
                res["given by roster place (home, away)"] = [g[:26], g[26:]]
                res["taken by roster place (home, away)"] = [t[:26], t[26:]]
                res["largest penalty log"] = m.w(PENLEN)
                e.screenshot(out / "end.png")
                break
        elif still >= 900:
            e.run(4, hold=["START"])
            still = 0
    res.update({"checks seen": len(events), "checks not one given and one taken byte of the right teams, in reach": bad[:10],
                "samples whose sums disagree": sums_bad, "pnum high byte not 0 (but $FFFF)": highs,
                "count changes without a check": stray[:10],
                "distance checker - hit player (median, max)": [sorted(x["dist"] for x in events if x["dist"] is not None)[len(events) // 2] if events else None,
                                                                 max((x["dist"] or 0) for x in events) if events else None]})
    (out / "base_end.state").write_bytes(e.serialize())
    print(json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
