"""NOSE4Web's "one fight per game" on NHL '95 (Vancecookcobxin's fights, 2026-11-21: NHL_95_fight_once.bin 573CE0DC).
The test at $1E03A4 (before the willingness test) takes the failure exit when a4's or a5's bit is set; the mark at
$1E03EC; StartGame's clear ($9CB6). RAM $FFF754-$F75B: a bit per roster index, the home team's 4 bytes first; the team
from pflags $62 bit 6.

gen95_fight_check's route (power-on, Game Setup, Fighting On, 5-minute periods, a Regular Game, the computer on both
sides), the mark bytes set to $FF at Game Setup (the game's start must clear them), the check tension ($FFC028) held at
40 or more and every skater's +$74 at 12, so fights come often; GAMES games, each from power-on with its own wait at
Game Setup (the seed). Logged: each fight (the puck's +$63 bit 0, $FFB3C5) with its two fighters (the skaters showing
fight frames $3CA-$3E7; team from the record, 0-5 home; roster index +$66) and whether either had fought that game; the
mark bytes at each change; each fight's two records' pflags team bit (+$62 bit 6) against the record number; PenBuf
($FFBFCE) codes when play stops: fighting $26 / $28, instigator $2A.

python gen95_fight_once_check.py ROM OUT GAMES"""
import json
import sys
from collections import Counter
from pathlib import Path

from emu import Emu
import gen95_assist_check as G
import gen95_shootout_check as S
import lowload
from gen95_fight_check import CHKCNT, PENBUF, PUCKFLAGS, GSP, CLOCK, ROW, FIGHTROW, to_setup, frame_of

MARKS = 0xF754


def one(rom, n, note):
    e = Emu(rom)
    to_setup(e)
    e.run(37 * n)                                       # a different moment at Game Setup: another seed
    for i in range(8):
        e.run(6, hold=["DOWN"]); e.run(30)
    for _ in range(6):
        if e.b(FIGHTROW) == 1:
            break
        e.run(6, hold=["RIGHT"]); e.run(40)
    e.setb(ROW + 3, 0)
    for i in range(8):
        e.setb(MARKS + i, 0xFF)
    e.run(6, hold=["START"]); e.run(300)
    e.run(6, hold=["START"]); e.run(60)
    e.run(1800)
    for _ in range(6):
        e.run(6, hold=["START"]); e.run(300)
    marks = lambda: [e.b(MARKS + i) for i in range(8)]  # noqa: E731
    note(what="start of play", game=n, marks=marks(), setting=e.b(0xCC63))
    c, fought, cur, f, prev_marks, pen_seen = Counter(), set(), None, 0, marks(), None
    while f < 60 * 60 * 40 and e.w(GSP) < 3:
        if f % 60 == 0:
            S.computer(e)
            e.setw(CHKCNT, max(e.w(CHKCNT), 40))
            if cur is None:
                for k in range(12):
                    if k not in (5, 11):
                        e.setb(G.rec(k) + 0x74, 12)
            if f % 3600 == 0:
                lowload.breathe()
        on = bool(e.b(PUCKFLAGS) & 1)
        if on and cur is None:
            cur = dict(start=f, who=set())
        if cur is not None:
            cur["who"] |= {k for k in range(12) if 0x3CA <= frame_of(e, k) <= 0x3E7}
            if f - cur["start"] == 30:
                ids = sorted((0 if k < 6 else 1, e.b(G.rec(k) + 0x66)) for k in cur["who"])
                teambit = {k: bool(e.b(G.rec(k) + 0x62) & 0x40) for k in cur["who"]}
                rep = [i for i in ids if i in fought]
                c["fights"] += 1
                c["repeats"] += bool(rep)
                note(what="fight", game=n, gsp=e.w(GSP), clock=e.w(CLOCK), fighters=ids, repeat=rep,
                     already=sorted(fought), team_bit_agrees=all(teambit[k] == (k >= 6) for k in teambit))
                fought |= set(ids)
            if not on and f - cur["start"] > 60:
                cur = None
        if e.b(PENBUF) and pen_seen is None:
            codes = [e.b(PENBUF + i) for i in range(12)]
            pen_seen = codes
            for code in codes:
                if code in (0x26, 0x28):
                    c["fighting"] += 1
                elif code == 0x2A:
                    c["instigator"] += 1
        if not e.b(PENBUF):
            pen_seen = None
        m = marks()
        if m != prev_marks:
            note(what="marks", game=n, gsp=e.w(GSP), clock=e.w(CLOCK), marks=m, was=prev_marks)
            prev_marks = m
        e.run(1)
        f += 1
    note(what="game end", game=n, **c, frames=f)
    return c


def main():
    rom, out, games = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
    lowload.gentle()
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / "fight_once.jsonl", "a")

    def note(**k):
        log.write(json.dumps(k) + "\n")
        log.flush()
        print(k, flush=True)

    total = Counter()
    for n in range(games):
        total.update(one(rom, n, note))
    note(what="total", **total)


if __name__ == "__main__":
    main()
