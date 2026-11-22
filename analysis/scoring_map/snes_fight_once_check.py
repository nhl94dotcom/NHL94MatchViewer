"""NOSE4Web's "one fight per game" on the SNES (2026-11-21: NHL94_fight_once.smc 04429DE9, NOSE4Web's 1 MB fights;
nhl94snes_2026_fight_once.sfc 94208CDB, 2 MB; nhl94_2026_fight_once.sfc 6F67F456, SA-1). checkfight's puck-at-faceoff
test becomes a jsl that returns Z and C set (the exit, both modes) when either player has fought; the mark after the
fight-on test sets both; FightGameStart clears them. RAM: LoROM $7E:FEC0-$FEC7, SA-1 BW-RAM $40:5840-$5847, a bit per
roster index, the home team's 4 bytes first.

Computer games (snes_momentum_blocks_check's boot: 5-minute periods, penalties On, No Offside, the computer on both
sides, the seed from the game's number). The mark bytes are set to $FF at the pre-game menus (the game's start must
clear them). Every skater's fighting rating ($1463) held at 14 each second. Fighting mode: on (OptFights $E708 0) or,
on McMarkis's builds, whistle (2). Logged: each fight (the skaters with pflags $0400): the two fighters (team: pfteam
$1503; roster index: pnum $12A3) and whether either had fought earlier that game; the mark bytes at every change; the
penalties called (the buffer at $15DE, as snes_60fps_cvc): fighting majors $2A / $2C, instigator $2E.
Run on the build and on the same layout's fighting build without the option (the control).

python snes_fight_once_check.py ROM OUT GAMES [on|whistle] [--mc]   (--mc: McMarkis's fights, OptFights set)"""
import json
import sys
from collections import Counter
from pathlib import Path

import lowload
import snes_60fps_cvc as cvc
from snes_momentum_blocks_check import boot, CLOCK, CLOCKSTOP, GSP, OPTFIGHTS, FIGHTER, FIGHTING, o

PFLAGS, PFTEAM, PNUM, POSITION = 0x1283, 0x1503, 0x12A3, 0x0F43
PENBUF = 0x15DE
CODES = {0x2A: "fighting", 0x2C: "fighting", 0x2E: "instigator"}


def marks_buf(e, m):
    return (m.bw, 0x5840) if m.sa1 else (e.ram, 0xFEC0)


def run(rom, out, games, mode, mc):
    lowload.gentle()
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / "fight_once.jsonl", "a")

    def note(**k):
        log.write(json.dumps(k) + "\n")
        log.flush()
        print(k, flush=True)

    total = Counter()
    for n in range(games):
        def before(e, m):
            buf, at = marks_buf(e, m)
            for i in range(8):
                buf[at + i] = 0xFF
            if mc:
                m.setw(OPTFIGHTS, 2 if mode == "whistle" else 0)

        e, m = boot(rom, n, before)
        buf, at = marks_buf(e, m)
        marks = lambda: [buf[at + i] for i in range(8)]  # noqa: E731
        note(what="start of play", game=n, marks=marks(), mode=mode)
        prev_marks, fought, fight, frames, still, last, seen = marks(), set(), None, 0, 0, None, set()
        c = Counter()
        while m.w(GSP) < 3 and frames < 60 * 60 * 50:
            if frames % 60 == 0:
                cvc.computer_only(m)
                if mc:
                    m.setw(OPTFIGHTS, 2 if mode == "whistle" else 0)
                for k in range(12):
                    if m.w(POSITION + o(k)) != 0:
                        m.setw(FIGHTING + o(k), 14)
                if m.w(CLOCK) > 300:
                    m.setw(CLOCK, 300)
                sig = m.w(CLOCK)
                still = still + 1 if sig == last else 0
                last = sig
                if frames % 3600 == 0:
                    lowload.breathe()
            e.run(1, hold=["START"] if still >= 15 and frames % 60 < 4 else [])
            frames += 1
            on = [k for k in range(12) if m.w(PFLAGS + o(k)) & FIGHTER]
            if on and fight is None:
                fight = dict(start=frames, who=set(on))
            if fight is not None:
                fight["who"] |= set(on)
                if frames - fight["start"] == 6:
                    ids = sorted((1 if m.w(PFTEAM + o(k)) else 0, m.w(PNUM + o(k)) & 0xFF) for k in fight["who"])
                    rep = [i for i in ids if i in fought]
                    c["fights"] += 1
                    c["repeats"] += bool(rep)
                    note(what="fight", game=n, gsp=m.w(GSP), clock=m.w(CLOCK), stopped=m.w(CLOCKSTOP), fighters=ids,
                         repeat=rep, already=sorted(fought))
                    fought |= set(ids)
                if not on and frames - fight["start"] > 60:
                    fight = None
            if frames % 10 == 0:
                now = set()
                for slot in range(0, 64, 2):
                    b, off = m.at(PENBUF + slot)
                    code, obj = b[off], b[off + 1] & 0x7F
                    if code and obj < 12:
                        now.add((slot, code, obj))
                        if (slot, code, obj) not in seen:
                            c[CODES.get(code, "other")] += 1
                seen = now
            mk = marks()
            if mk != prev_marks:
                note(what="marks", game=n, gsp=m.w(GSP), clock=m.w(CLOCK), marks=mk, was=prev_marks)
                prev_marks = mk
        note(what="game end", game=n, **c, frames=frames)
        total.update(c)
    note(what="total", **total)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    run(a[0], Path(a[1]), int(a[2]), a[3] if len(a) > 3 else "on", "--mc" in sys.argv)
