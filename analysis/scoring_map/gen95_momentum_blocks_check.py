"""NOSE4Web's NHL '95 ports of fight momentum and blocked shots (2026-11-20, b174169: NHL_95_momentum_blocks.bin,
W18_momentum_blocks.bin; Vancecookcobxin's fighting, both options on).

Momentum: the winner's team byte at $FFF750 ($00 home, $40 visitors) and a timer word at $FFF752 (90 at the knockout,
-1 a game second while the clock runs; 0 at a new game); the winner's skaters +2 Agility and +2 Speed (playeracc).
Blocks: puckbody ($7BCA8) counts a skater's body stopping the other team's shot in flight: a byte per roster place at
$FFEA90 (visitors +$20), the team totals at $FFEB04 / $FFEE6A.

games: computer games one after another in one session (gen95_fight_check's boot: Fighting On, 5-minute periods;
--push holds the check tension ChkCnt at 40+ so fights come often; --fgt=N sets every skater's fighting byte +$74 to
N each second (W18 rates nobody)). Every frame:
- fights (the puck's +$63 bit 0): the fighters (fight frames $3CA-$3E7), the knockout (the timer rising), the loser
  (a fall frame $3D1, $3D2, $3DE, $3DF, $3E6, $3E7), the team byte against the winner;
- the timer: each drop with the clock (a drop in a clock second that had one already, or clock seconds skipped);
  each period change and each new game's first value;
- blocks as gen_blocks_check.py: shots (sf2shot $FFBEF4 bit 4 rising, shotplayer $FFBAD6), puckbody's signature
  (the puck's speed after the frame 256 x its offset from the skater, Zvel 0, within the body's reach), every change
  of the 64 counts and two totals, each matched to a body hit; at each game's end the counts against the totals, and
  the counts at each new game's start.
boost: from one moment of play saved, the timer 0, then 90 for home, then 90 for the visitors: each record's speed
against the timer-0 run, the frame it first differs, the mean speed over 40 frames.

python gen95_momentum_blocks_check.py games ROM OUT GAMES [--push] [--fgt=N]   |   boost ROM OUT"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

import gen95_assist_check as G
import gen95_fight_check as F
import gen95_shootout_check as S
import lowload
from emu import Emu

TEAM, TIMER = 0xF750, 0xF752
GSP, CLOCK, GMODE, CHKCNT = 0xC020, 0xC022, 0xBEF0, 0xC028
PUCKC, SFLAGS2, SHOTPLAYER = 0xB3C2, 0xBEF4, 0xBAD6
COUNTS, TOTALS = 0xEA90, (0xEB04, 0xEE6A)
PUCK = 14
FIGHT = range(0x3CA, 0x3E8)
FALL = {0x3D1, 0x3D2, 0x3DE, 0x3DF, 0x3E6, 0x3E7}
BODY = 9


def rec(k):
    return G.rec(k)


def s8(v):
    return v - 256 if v > 127 else v


def boot(rom):
    e = Emu(rom)
    F.to_setup(e)
    for _ in range(8):
        e.run(6, hold=["DOWN"]); e.run(30)
    for _ in range(6):
        if e.b(F.FIGHTROW) == 1:
            break
        e.run(6, hold=["RIGHT"]); e.run(40)
    e.setb(F.ROW + 3, 0)                         # 5-minute periods
    e.run(6, hold=["START"]); e.run(300)
    e.run(6, hold=["START"]); e.run(60)
    e.run(1800)
    for _ in range(6):
        e.run(6, hold=["START"]); e.run(300)
    return e


def games(rom, out, n, push, fgt):
    lowload.gentle()
    e = boot(rom)
    log = open(out / "games.jsonl", "w")

    def note(**k):
        log.write(json.dumps(k) + "\n")
        log.flush()
        print(k, flush=True)

    c = Counter()
    game, frame, still, last = 1, 0, 0, None
    note(what="game start", game=1, team=e.b(TEAM), timer=e.w(TIMER), counts=sum(e.b(COUNTS + i) for i in range(64)),
         totals=[e.w(t) for t in TOTALS], gsp=e.w(GSP), clock=e.w(CLOCK))
    fight, ko, prev_t, prev_gsp, drop_clk, ended = None, None, e.w(TIMER), e.w(GSP), None, False
    prev_counts = bytes(e.b(COUNTS + i) for i in range(64))
    prev_tot = [e.w(t) for t in TOTALS]
    prev_shot, shooter, last_carrier, hits = False, None, None, []
    p = rec(PUCK)
    while game <= n and frame < 60 * 60 * 60 * n:
        if frame % 60 == 0:
            S.computer(e)
            if push:
                e.setw(CHKCNT, max(e.w(CHKCNT), 40))
            if fgt is not None:
                for k in range(12):
                    if k not in (5, 11):
                        e.setb(rec(k) + 0x74, fgt)
            sig = (e.w(CLOCK), e.w(p), e.w(p + 0x14))
            still = still + 1 if sig == last else 0
            last = sig
            if frame % 3600 == 0:
                lowload.breathe()
        before = [(e.sw(rec(k)), e.sw(rec(k) + 0x14)) for k in range(12)]
        pb = (e.sw(p), e.sw(p + 0x14))
        if e.w(PUCKC) < 12:
            last_carrier = e.w(PUCKC)
        e.run(1, hold=["START"] if still >= 6 and frame % 60 < 4 else [])
        frame += 1
        t, clk, gsp = e.w(TIMER), e.w(CLOCK), e.w(GSP)
        # ---- fights and momentum
        on = bool(e.b(p + 0x63) & 1)
        if on and fight is None:
            fight = dict(start=frame, who=set())
            c["fights"] += 1
        if fight is not None:
            for k in range(12):
                if (e.w(rec(k) + 6) & 0x7FF) in FIGHT:
                    fight["who"].add(k)
            if not on and frame - fight["start"] > 60:
                note(what="fight over", game=game, gsp=gsp, clock=clk, fighters=sorted(fight["who"]),
                     frames=frame - fight["start"], knockout=ko is not None)
                fight = None
        if t != prev_t:
            if t > prev_t:
                ko = dict(frame=frame, team=e.b(TEAM), fell=set(), was=prev_t)
                drop_clk = None
                note(what="timer set", game=game, gsp=gsp, clock=clk, timer=t, was=prev_t, team=e.b(TEAM))
            elif prev_t - t == 1:
                c["timer drops"] += 1
                if drop_clk is not None and gsp == prev_gsp:
                    if clk == drop_clk:
                        c["timer: two drops in one clock second"] += 1
                    elif abs(drop_clk - clk) > 1:
                        c["timer: clock seconds without a drop"] += 1
                drop_clk = clk
            else:
                c["timer jumps"] += 1
                note(what="timer jump", game=game, gsp=gsp, clock=clk, timer=t, was=prev_t)
        if ko is not None:
            for k in (fight["who"] if fight else range(12)):
                if (e.w(rec(k) + 6) & 0x7FF) in FALL:
                    ko["fell"].add(k)
            if frame - ko["frame"] >= 150:
                who = sorted(fight["who"]) if fight else []
                win = [k for k in who if k not in ko["fell"]]
                want = (0 if win[0] < 6 else 0x40) if len(win) == 1 else None
                right = (want == ko["team"]) if want is not None else None
                c[f"knockouts: team byte right {right}"] += 1
                note(what="knockout", game=game, team=ko["team"], fighters=who, fell=sorted(ko["fell"]), winner=win,
                     right=right, after_running_timer=ko["was"])
                ko = None
        if gsp != prev_gsp:
            note(what="period change", game=game, gsp_from=prev_gsp, gsp_to=gsp, timer=t, team=e.b(TEAM))
            if gsp >= 4 or (prev_gsp >= 2 and gsp == 0):
                if not ended:
                    teams = [sum(prev_counts[:32]), sum(prev_counts[32:])]
                    note(what="game end", game=game, players=teams, totals=prev_tot, timer=t)
                    ended = True
        if ended and gsp == 0 and clk >= 290 and not (e.w(GMODE) & 0x100):
            game += 1
            ended = False
            note(what="game start", game=game, team=e.b(TEAM), timer=t, counts=sum(e.b(COUNTS + i) for i in range(64)),
                 totals=[e.w(x) for x in TOTALS], clock=clk)
            if game > n:
                break
        prev_t, prev_gsp = t, gsp
        # ---- blocks
        shot = bool(e.b(SFLAGS2) & 0x10)
        if shot and not prev_shot:
            sp = e.w(SHOTPLAYER)
            shooter = sp if sp < 12 else None
            c["shots"] += 1
        vx, vy, vz = e.sw(p + 0x28), e.sw(p + 0x2A), e.sw(p + 0x2C)
        hit = None
        if e.w(PUCKC) >= 12:
            for k in range(12):
                if e.b(rec(k) + 0x35) == 0xFF:
                    continue
                ok = False
                for (ax, ay), (bx, by) in ((pb, before[k]), ((e.sw(p), e.sw(p + 0x14)), (e.sw(rec(k)), e.sw(rec(k) + 0x14)))):
                    dx, dy = ax - bx, ay - by
                    if math.hypot(dx, dy) > BODY or (dx == 0 and dy == 0):
                        continue
                    if abs(s8((vx >> 8) & 0xFF) - s8(dx & 0xFF)) <= 3 and abs(s8((vy >> 8) & 0xFF) - s8(dy & 0xFF)) <= 3:
                        ok = True
                if ok and vz == 0:
                    hit = k
                    break
        if hit is not None:
            goalie = e.b(rec(hit) + 0x35) == 0
            team = 1 if hit >= 6 else 0
            kind = ("no shot in flight" if not prev_shot else "shot, shooter unknown" if shooter is None
                    else "teammate's shot" if (shooter >= 6) == (team == 1) else "the other team's shot")
            hits.append([frame, hit, team, kind + (" (goalie)" if goalie else ""), False])
        counts = bytes(e.b(COUNTS + i) for i in range(64))
        tot = [e.w(x) for x in TOTALS]
        if counts != prev_counts:
            for i in range(64):
                d = counts[i] - prev_counts[i]
                if d and not (d < 0 and counts[i] == 0):
                    tm, slot = divmod(i, 32)
                    who = None
                    for h in hits:
                        if frame - h[0] <= 1 and h[2] == tm and e.b(rec(h[1]) + 0x66) == slot:
                            h[4] = True
                            who = h
                    c["counts: " + (("matched to a body hit: " + who[3]) if who else "NO body hit matched")] += 1
                    if not who or "no shot" in who[3]:
                        sp_now = e.w(SHOTPLAYER)
                        note(what="count without a body hit" if not who else "count, no shot in flight the frame before",
                             game=game, team=tm, slot=slot, d=d, clock=clk, gsp=gsp, shot_before=prev_shot,
                             shot_now=shot, shotplayer_now=sp_now if sp_now < 12 else None, shooter=shooter,
                             z=e.sw(p + 0x18), gmode=e.w(GMODE), puckc=e.w(PUCKC))
        prev_counts, prev_tot, prev_shot = counts, tot, shot
    for h in hits:
        c[f"body hits: {h[3]}: {'counted' if h[4] else 'not counted'}"] += 1
    note(what="summary", frames=frame, **dict(c))


def boost(rom, out):
    lowload.gentle()
    e = boot(rom)
    for _ in range(60 * 60):
        S.computer(e)
        e.run(1)
        if e.w(GSP) == 0 and e.w(CLOCK) < 270 and not (e.w(GMODE) & 0x100) and not (e.b(rec(PUCK) + 0x63) & 1):
            c0 = e.w(CLOCK)
            e.run(30)
            if e.w(CLOCK) != c0:
                break
    base = e.serialize()
    res, pos = {}, [e.b(rec(k) + 0x35) for k in range(12)]
    for tag, team, timer in (("off", 0, 0), ("home", 0, 90), ("away", 0x40, 90)):
        e.unserialize(base)
        e.setb(TEAM, team)
        e.setw(TIMER, timer)
        rows = []
        for _ in range(40):
            e.run(1)
            rows.append([(e.sw(rec(k) + 0x28), e.sw(rec(k) + 0x2A)) for k in range(12)])
        res[tag] = rows
    lines = []
    for tag in ("home", "away"):
        for k in range(12):
            first = next((f for f in range(40) if res[tag][f][k] != res["off"][f][k]), None)
            sp = lambda rows: sum(math.hypot(*r[k]) for r in rows) / 40
            lines.append(dict(run=tag, record=k, team="home" if k < 6 else "away", position=pos[k], first_differs=first,
                              mean_speed_off=round(sp(res["off"])), mean_speed=round(sp(res[tag]))))
            print(lines[-1], flush=True)
    json.dump(lines, open(out / "boost.json", "w"))


def press(e, b, after=26):
    e.run(4, hold=[b])
    e.run(after)


def screens(rom, out, game_item, player_item, pen=None, left=1):
    """A game in play (period 1, under 4:30), the counts set (home places 0-5: 1-6, visitors' 6-1, totals 21 each),
    paused: the pause menu (a screenshot at each item), Player Stats (PLAYER, C) every page RIGHT, A, LEFT back, and
    Game Stats (GAME, C) top and bottom. pen: OptPen ($FFCC5A) set first."""
    lowload.gentle()
    e = boot(rom)
    if pen is not None:
        e.setw(0xCC5A, pen)
    for _ in range(60 * 60):
        S.computer(e)
        e.run(1)
        if e.w(GSP) == 0 and e.w(CLOCK) < 270 and not (e.w(GMODE) & 0x100):
            break
    for p in range(32):
        e.setb(0xFF0000 | (COUNTS + p), p + 1 if p < 6 else 0)
        e.setb(0xFF0000 | (COUNTS + 32 + p), 6 - p if p < 6 else 0)
    e.setw(TOTALS[0], 21)
    e.setw(TOTALS[1], 21)
    press(e, "START", 90)
    for _ in range(left):
        press(e, "LEFT", 60)
    base = e.serialize()
    for k in range(12):
        e.screenshot(out / f"menu_{k:02d}_item{e.w(0xCADE)}.png")
        press(e, "DOWN")
    e.unserialize(base)

    def to_item(n):
        for _ in range(30):
            if e.w(0xCADE) == n:
                return True
            press(e, "DOWN")
        return False

    if player_item is not None and to_item(player_item):
        press(e, "C")
        e.run(240)
        e.screenshot(out / "player_00.png")
        for k in range(1, 12):
            press(e, "RIGHT")
            e.run(90)
            e.screenshot(out / f"player_{k:02d}.png")
        press(e, "A")
        e.run(120)
        for k in range(12, 24):
            e.screenshot(out / f"player_{k:02d}_other.png")
            press(e, "LEFT")
            e.run(90)
    e.unserialize(base)
    if game_item is not None and to_item(game_item):
        press(e, "C")
        e.run(240)
        e.screenshot(out / "game_top.png")
        e.run(300, hold=["DOWN"])
        e.run(30)
        e.screenshot(out / "game_bottom.png")
    print("screens done", flush=True)


if __name__ == "__main__":
    mode, rom, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    fgt = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--fgt=")), None)
    if mode == "games":
        games(rom, out, int(sys.argv[4]), "--push" in sys.argv, fgt)
    elif mode == "screens":
        items = [None if v == "-" else int(v) for v in sys.argv[4].split(":")] if len(sys.argv) > 4 else [None, None]
        pen = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--pen=")), None)
        left = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--left=")), 1)
        screens(rom, out, items[0], items[1], pen, left)
    else:
        boost(rom, out)
