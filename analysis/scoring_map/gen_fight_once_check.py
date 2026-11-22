"""NOSE4Web's "one fight per game" (Genesis NHL '94 on chaos's fights, 2026-11-21: nhl94_fight_once.bin D8E3BDA0,
nhl94_fight_once_momentum.bin 82631D1D). Once a player has fought he can't fight again that game: checkfight's test
at $20025E takes .exit when either player's bit is set; the mark at $20030C sets both fighters' bits; StartGame clears
them ($77D8). RAM $FFF754-$F75B: a bit per roster index, the home team's 4 bytes first.

Computer games one after another in one session (gen_fight_momentum_check's boot, 5-minute periods, penalties On
Except Off-sides, line changes off), every skater's fighting rating (+$74) held at 14 between fights (with it nearly
every hard hit is a fight on the plain build), the fighters' strengths set low once a fight is on (it ends sooner).
The mark bytes are set to $FF at Game Setup before the first game (StartGame must clear them). Logged:
- each fight: the two fighters (team, roster index), and whether either had fought earlier that game (a repeat);
- the mark bytes at every change, and at each game's start;
- each period's penalty summary ($C5DC: a count byte, then 4 bytes: time, team | rule, roster index): fighting majors
  ($26 / $28) and instigator minors ($2A).
Run on the build and on a fighting build without the option (the control: repeats expected there).

--shootout (nhl94_fight_once_shootout.bin D4C9C257, 2026-11-22: the season shootout after a tied period 3): Regular
Season (OptPlayMode $D048 = 0), and with 8 s left in period 3 the score levelled (the higher goals word lowered) if it
isn't tied: the shootout follows; logged as it goes: the build's shootout flag ($FFF082), the round ($D578), each side's
shootout goals ($D574 / $D576), the marks; the fighting ratings left alone while the flag is set. Then the next game.

python gen_fight_once_check.py ROM OUT GAMES [--shootout]"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu
from gen_fight_momentum_check import CLOCK, GSP, SCREEN, computer, rec, OPTPEN, OPTLINE, PERLEN, SEED

MARKS = 0xF754
PENSUM = 0xC5DC


def marks(e):
    return [e.b(MARKS + i) for i in range(8)]


def penalties(e):
    """The summary as gen_fight_check reads it: a word, its length in bytes; then 4 bytes each from +2: the time word,
    team | rule, roster index."""
    n = e.w(PENSUM)
    out = []
    if 0 < n <= 240:
        for i in range(n // 4):
            code = e.b(PENSUM + 4 + 4 * i)
            out.append((code & 0x7F, code >> 7, e.b(PENSUM + 5 + 4 * i)))   # rule, team (high bit), roster index
    return n, out


HMGOALS, AWGOALS, PLAYMODE, SOFLAG, SOROUND, SOHOME, SOAWAY = 0xC6DA, 0xCA3E, 0xD048, 0xF082, 0xD578, 0xD574, 0xD576


def run(rom, out, n, shootout=False):
    lowload.gentle()
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1)
    e.setw(PERLEN, 0)
    if shootout:
        e.setw(PLAYMODE, 0)                          # Regular Season
    for i in range(8):
        e.setb(MARKS + i, 0xFF)                     # StartGame must clear these
    if not G.into_play(e):
        raise SystemExit("never reached play")
    e.setl(SEED, 0x2545F491)
    ours = tuple(e.b(a) for a in G.TEAMS)
    log = open(out / "fight_once.jsonl", "w")

    def note(**k):
        log.write(json.dumps(k) + "\n")
        log.flush()
        print(k, flush=True)

    game, frame, still, last_clk = 1, 0, 0, None
    note(what="game start", game=game, marks=marks(e))
    fought, fight_at, fighters, nfights, prev_gsp, late = set(), None, set(), 0, e.w(GSP), False
    prev_marks = marks(e)
    tally = Counter()
    pen_seen = 0
    levelled, so_state, so_frames = False, None, 0
    while game <= n and frame < 60 * 60 * 60 * n:
        mine = tuple(e.b(a) for a in G.TEAMS) == ours
        if frame % 60 == 0:
            computer(e)
            c = e.w(CLOCK)
            still = still + 1 if c == last_clk else 0
            last_clk = c
            if frame % 3600 == 0:
                lowload.breathe()
        if fight_at is None and not (shootout and e.b(SOFLAG)):
            for k in range(12):
                e.setb(rec(k) + 0x74, 14)
        if shootout and mine and not levelled and e.w(GSP) == 2 and e.b(SCREEN) == 0 and 0 < e.w(CLOCK) <= 8:
            h, a = e.w(HMGOALS), e.w(AWGOALS)
            if h != a:
                e.setw(HMGOALS, min(h, a))
                e.setw(AWGOALS, min(h, a))
            levelled = True
            note(what="levelled for the shootout", game=game, was=[h, a], now=[e.w(HMGOALS), e.w(AWGOALS)],
                 fights_this_game=sorted(fought), marks=marks(e))
        if shootout:
            st = (e.b(SOFLAG), e.w(SOROUND), e.w(SOHOME), e.w(SOAWAY))
            if st != so_state:
                note(what="shootout", game=game, flag=st[0], round=st[1], home=st[2], away=st[3], gsp=e.w(GSP),
                     screen=e.b(SCREEN), score=[e.w(HMGOALS), e.w(AWGOALS)], marks=marks(e))
                so_state = st
            if st[0]:                                # a look at it every 15 s (real), and a stop if it never ends
                so_frames += 1
                if so_frames % 900 == 1 and so_frames < 900 * 40 and os.environ.get("NHL94_SO_SHOTS", "1") == "1":
                    e.screenshot(out / f"so_g{game}_{so_frames // 900:02d}.png")
                    note(what="shootout look", game=game, frames=so_frames, clock=e.w(CLOCK), gsp=e.w(GSP),
                         screen=e.b(SCREEN), box=[e.b(rec(k) + 0x35) for k in range(12)])
                if os.environ.get("NHL94_SO_EARLY") == str(game) and so_frames % 120 == 1 and so_frames < 120 * 50:
                    e.screenshot(out / f"so_g{game}_early_{so_frames // 120:02d}.png")   # its first 100 s (real) closely
                    note(what="early look", n=so_frames // 120, clock=e.w(CLOCK), gsp=e.w(GSP), screen=e.b(SCREEN),
                         score=[e.w(HMGOALS), e.w(AWGOALS)], teams=[e.b(a) for a in G.TEAMS], state=st)
                if so_frames > 30000:
                    note(what="shootout not finished after 30000 frames", game=game, round=st[1], marks=marks(e))
                    (out / f"so_g{game}_stuck.state").write_bytes(e.serialize())
                    for i in range(8):               # what it is doing: a screenshot every 5 s (real)
                        e.screenshot(out / f"so_g{game}_stuck_{i}.png")
                        note(what="stuck look", i=i, clock=e.w(CLOCK), gsp=e.w(GSP), screen=e.b(SCREEN),
                             score=[e.w(HMGOALS), e.w(AWGOALS)], teams=[e.b(a) for a in G.TEAMS], state=st)
                        e.run(300)
                    break
            else:
                so_frames = 0
        # the build's menu before the shootout ("Start Shootout", shown with screen 0) waits for START; left alone the
        # intermission's highlights of other games go round for ever (2026-11-22: a 0-0 game sat there 2 hours)
        waiting = shootout and e.b(SOFLAG) and so_frames > 600 and so_state is not None and so_state[1:] == (1, 0, 0)
        e.run(1, hold=["START"] if (waiting and frame % 120 < 4)
              or (still >= 8 and e.b(SCREEN) not in (0, 0x80) and frame % 60 < 4) else [])
        frame += 1
        gsp = e.w(GSP)
        now = {k for k in range(12) if e.b(rec(k) + 0x63) & 1}
        if now and fight_at is None:
            fight_at, fighters = frame, set(now)
        if fight_at is not None:
            fighters |= now
            if frame - fight_at == 12 and len(fighters) == 2:
                lo, hi = sorted(fighters)
                e.setw(rec(lo) + 0x44, 3)
                e.setw(rec(hi) + 0x44, 5)
            if frame - fight_at == 13:
                ids = sorted((0 if k < 6 else 1, e.b(rec(k) + 0x66)) for k in fighters)
                rep = [i for i in ids if i in fought]
                nfights += 1
                tally["fights"] += 1
                tally["repeats"] += bool(rep)
                note(what="fight", game=game, gsp=gsp, clock=e.w(CLOCK), fighters=ids, repeat=rep,
                     already=sorted(fought))
                fought |= set(ids)
            if not now and frame - fight_at > 60:
                fight_at = None
        if frame % 30 == 0:
            cnt, pens = penalties(e)
            if len(pens) < pen_seen:
                pen_seen = 0
            for rule, team, who in pens[pen_seen:]:
                kind = "fighting" if rule in (0x26, 0x28) else "instigator" if rule == 0x2A else "other"
                tally[kind] += 1
                note(what="penalty", game=game, gsp=gsp, clock=e.w(CLOCK), rule=hex(rule), team=team, roster=who,
                     kind=kind)
            pen_seen = len(pens)
        m = marks(e)
        if m != prev_marks:
            note(what="marks", game=game, gsp=gsp, clock=e.w(CLOCK), marks=m, was=prev_marks)
            prev_marks = m
        if mine and gsp != prev_gsp:
            if gsp >= 2:
                late = True
            if gsp == 0 and late:
                game += 1
                late, levelled = False, False
                fought = set()
                if game > n:
                    break
                note(what="game start", game=game, marks=marks(e))
        if mine:
            prev_gsp = gsp
    note(what="end", **tally, frames=frame)


if __name__ == "__main__":
    run(sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]), "--shootout" in sys.argv)
