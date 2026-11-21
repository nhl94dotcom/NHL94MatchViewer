"""NOSE4Web's fight momentum (Genesis NHL '94, 2026-11-19 builds on chaos's fighting patch): the winner's team word at
$FFF750 ($00 home, $40 visitors) and a timer at $FFF752 (90 at the knockout, -1 a game second while the clock runs);
while it runs the winner's skaters get +2 Agility and +2 Speed in playeracc (the goalie and the other team nothing).

games: computer games one after another in one session (the first from power-on, the next ones by START through the
game's end screens), 5-minute periods, penalties On Except Off-sides; with --hot every fighting rating (+$74) is 14
each frame, for more fights. Logged every frame:
- fights (pf2fight, +$63 bit 0, on any record): the two fighters; the knockout (the timer set to 90); the winner told
  by the loser's fall (a frame in 273-336, the fall frames, within 120 frames), against the team word;
- the timer: each change, with the clock: a drop must come with a clock tick, none while the clock stands;
- each period's last and next period's first value (the intermission), each game's first value of play (0 wanted;
  before each game's end a running timer is made sure of: set to 60 for the home team at 0:20 of period 3 if 0).
boost: from one moment of play (period 1, the clock running, no fight) saved, the same frames run with the timer 0,
then 90 for home, then 90 for the visitors: each record's speed (+$28, +$2A) against the timer-0 run, the frame it
first differs, and the mean speed over the first 40 frames.

python gen_fight_momentum_check.py games ROM OUT GAMES [--hot]   |   boost ROM OUT [SEED]"""
import json
import math
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

OPTPEN, OPTLINE, PERLEN, SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD056, 0xD058, 0xD050, 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
BASE, SZ = 0xB04A, 0x80
TEAM, TIMER = 0xF750, 0xF752
FALLS = set(range(273, 337)) | set(range(862, 870))   # the standard falls; chaos's knocked-down frames


def rec(k):
    return BASE + SZ * k


def computer(e):
    e.setw(CONT1, 0)
    e.setw(CONT2, 0)
    for k in range(12):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)


def boot(rom, out, seed):
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1)
    e.setw(PERLEN, 0)
    if not G.into_play(e):
        raise SystemExit("never reached play")
    e.setl(SEED, (0x2545F491 * seed) & 0xFFFFFFFF or 1)
    return e


def games(rom, out, n, hot):
    lowload.gentle()
    e = boot(rom, out, 1)
    ours = tuple(e.b(a) for a in G.TEAMS)
    log = open(out / "momentum.jsonl", "w")

    def note(**k):
        log.write(json.dumps(k) + "\n")
        log.flush()
        print(k, flush=True)

    game, frame, still, last_clk = 1, 0, 0, None
    note(what="game start", game=1, team=e.b(TEAM), timer=e.w(TIMER), clock=e.w(CLOCK), gsp=e.w(GSP))
    fighters, fight_at, nfights, ko = set(), None, 0, None
    prev_t, prev_gsp, poked, late = e.w(TIMER), e.w(GSP), False, False
    drops = dict(steps=0, same_second=0, skipped_seconds=0, jumps=0)
    drop_clk = None
    while game <= n and frame < 60 * 60 * 60 * n:
        mine = tuple(e.b(a) for a in G.TEAMS) == ours
        if frame % 60 == 0:
            computer(e)
            c = e.w(CLOCK)
            still = still + 1 if c == last_clk else 0
            last_clk = c
            if frame % 3600 == 0:
                lowload.breathe()
        if hot and fight_at is None:
            for k in range(12):
                e.setb(rec(k) + 0x74, 14)
        if mine and e.w(GSP) == 2 and e.b(SCREEN) == 0 and e.w(CLOCK) == 20 and e.w(TIMER) == 0 and not poked:
            e.setb(TEAM, 0)
            e.setw(TIMER, 60)
            poked = True
            note(what="poked a running timer before the game's end", game=game)
            prev_t, drop_clk = 60, None
        e.run(1, hold=["START"] if still >= 8 and e.b(SCREEN) not in (0, 0x80) and frame % 60 < 4 else [])
        frame += 1
        t, clk, gsp, scr = e.w(TIMER), e.w(CLOCK), e.w(GSP), e.b(SCREEN)
        now = {k for k in range(12) if e.b(rec(k) + 0x63) & 1}
        if now and fight_at is None:
            fighters, fight_at = set(now), frame
            nfights += 1
            note(what="fight", game=game, gsp=gsp, clock=clk, fighters=sorted(fighters), team=e.b(TEAM), timer=t)
        if fight_at is not None:
            fighters |= now
            if frame - fight_at == 12 and len(fighters) == 2:      # strengths low (the fight code sets them by now)
                lo, hi = sorted(fighters)
                e.setw(rec(lo) + 0x44, 3 if nfights % 2 else 5)
                e.setw(rec(hi) + 0x44, 5 if nfights % 2 else 3)
            if not now and frame - fight_at > 60:
                note(what="fight over", game=game, frames=frame - fight_at, knockout=ko is not None or t == 90)
                fight_at = None
        if t != prev_t:
            if t > prev_t:
                ko = dict(frame=frame, team=e.b(TEAM), fighters=sorted(fighters), falls=set())
                drop_clk = None
                note(what="timer set", game=game, gsp=gsp, clock=clk, timer=t, was=prev_t, team=e.b(TEAM), fighters=sorted(fighters))
            elif prev_t - t == 1:
                drops["steps"] += 1
                if drop_clk is not None and mine:
                    if clk == drop_clk:
                        drops["same_second"] += 1
                        note(what="two drops in one clock second", game=game, gsp=gsp, clock=clk, timer=t)
                    elif abs(drop_clk - clk) > 1 and gsp == prev_gsp:
                        drops["skipped_seconds"] += 1
                        note(what="clock seconds without a drop", game=game, gsp=gsp, clock=clk, last=drop_clk, timer=t)
                drop_clk = clk
            else:
                drops["jumps"] += 1
                note(what="timer jump", game=game, gsp=gsp, clock=clk, timer=t, was=prev_t, screen=scr, mine=mine)
        if ko is not None:
            for k in ko["fighters"]:
                if e.w(rec(k) + 6) in FALLS:
                    ko["falls"].add(k)
            if frame - ko["frame"] >= 120:
                winners = [k for k in ko["fighters"] if k not in ko["falls"]]
                want = None if len(winners) != 1 else (0 if winners[0] < 6 else 0x40)
                note(what="knockout", game=game, team=ko["team"], fighters=ko["fighters"], fell=sorted(ko["falls"]),
                     winner=winners, right=(want == ko["team"]) if want is not None else None)
                ko = None
        if mine and gsp != prev_gsp:
            note(what="period change", game=game, gsp_from=prev_gsp, gsp_to=gsp, timer_before=prev_t, timer_now=t, team=e.b(TEAM))
            if gsp >= 2:
                late = True
            if gsp == 0 and late:                                     # the next game
                game += 1
                late, poked = False, False
                if game > n:
                    break
                note(what="game start", game=game, team=e.b(TEAM), timer=t, clock=clk, gsp=gsp)
        if mine:
            prev_gsp = gsp
        prev_t = t
    note(what="drops", **drops, fights=nfights, frames=frame)


def boost(rom, out, seed):
    lowload.gentle()
    e = boot(rom, out, seed)
    for _ in range(60 * 40):
        computer(e)
        e.run(1)
        if e.w(GSP) == 0 and e.b(SCREEN) == 0 and e.w(CLOCK) < 270 and e.w(TIMER) == 0 and not any(
                e.b(rec(k) + 0x63) & 1 for k in range(12)):
            c = e.w(CLOCK)
            e.run(30)
            if e.w(CLOCK) != c:
                break
    base = e.serialize()
    res = {}
    for tag, team, timer in (("off", 0, 0), ("home", 0, 90), ("away", 0x40, 90)):
        e.unserialize(base)
        e.setb(TEAM, team)
        e.setw(TIMER, timer)
        rows = []
        for f in range(40):
            e.run(1)
            rows.append([(e.sw(rec(k) + 0x28), e.sw(rec(k) + 0x2A)) for k in range(12)])
        res[tag] = rows
        res[tag + "_pos"] = [e.b(rec(k) + 0x35) for k in range(12)]
    out_lines = []
    for tag in ("home", "away"):
        for k in range(12):
            first = next((f for f in range(40) if res[tag][f][k] != res["off"][f][k]), None)
            sp = lambda rows: sum(math.hypot(*r[k]) for r in rows[:40]) / 40
            line = dict(run=tag, record=k, team="home" if k < 6 else "away", position=res["off_pos"][k],
                        first_differs=first, mean_speed_off=round(sp(res["off"])), mean_speed=round(sp(res[tag])))
            out_lines.append(line)
            print(line, flush=True)
    json.dump(out_lines, open(out / f"boost_{seed}.json", "w"))


if __name__ == "__main__":
    mode, rom, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    if mode == "games":
        games(rom, out, int(sys.argv[4]), "--hot" in sys.argv)
    else:
        boost(rom, out, int(sys.argv[4]) if len(sys.argv) > 4 else 1)
