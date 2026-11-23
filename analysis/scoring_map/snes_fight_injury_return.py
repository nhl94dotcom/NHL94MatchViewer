"""Does a player hurt in a fight stay out? (SNES, McMarkis's fights; 2026-11-23, a league's report on its 1996 World
Cup of Hockey ROM, an SA-1 build: a fighter "injured for the game" came out of the box after his penalty, played on
and scored.)

McMarkis's fix (NHL94SNES-SA1 485ec28a): FightFall marks the loser tmpdst $FFFC (out for the game) and fightinj
($E74E + roster place, + 26 the visitors; fightinjany $E782); the penalty scene then puts the fight's box time in his
tmpdst over it; FightInjuredKeep (PenaltyManager, every pass) puts $FFFC back once his word is no longer box time.

Computer games (snes_momentum_blocks_check.boot: regular season, penalties on, the computer on both sides, periods
capped at 5 minutes), Fighting On (OptFights $E708 = 0), every skater's fighting rating ($1463) held at FIGHT (9) and, while a fight is on,
every player's $1483 at 60, so fights come and the loser is always hurt. --lines: line changes on (OptLine $34C6 = 1;
0 without it: this ROM's own default is 1).
Every frame, for each roster place whose fightinj byte is set (and, as a control, each whose tmpdst is ever $FFFC or
$FFFD without it): his tmpdst word at each change; whether he is on the ice (an object of his team with his pnum
$12A3), in seconds by the game clock, split into before his box time ended and after; his goals and assists ($18EE /
$1922) when he was marked and at the end. Flagged: on the ice after his box time, a word that is neither box time nor
$FFFC after it, points scored after he was hurt.

His shifts after the box are listed: where and when he comes on, and at each end whether the clock was stopped (a
whistle) and how many team mates left the ice with him (a line change).

python snes_fight_injury_return.py ROM OUT GAMES [FIRST] [--lines] [--fight=N] [--nose] [--all]   (--nose: NOSE4Web's 1 MB fights; --all: every fighter, hurt or not)"""
import json
import sys
from pathlib import Path

import lowload
import snes_60fps_cvc as cvc
from snes_momentum_blocks_check import boot, CLOCK, CLOCKSTOP, GSP, o

TMPDST, FIGHTINJ, FIGHTINJANY = 0x1852, 0xE74E, 0xE782
PNUM, PFTEAM, PFLAGS, FIGHTING, AGGRESS = 0x12A3, 0x1503, 0x1283, 0x1463, 0x1483
GOALS, ASSISTS, OPTLINE, FIGHTER, OPTFIGHTS = 0x18EE, 0x1922, 0x34C6, 0x0400, 0xE708
LINES = "--lines" in sys.argv
FIGHT = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--fight=")), 9)
ALL = "--all" in sys.argv          # follow every fighter, hurt or not (injured: his fightinj byte)
NOSE = "--nose" in sys.argv        # NOSE4Web's 1 MB fights: the marks at $7E:FE80 (fightinjany $FEB4), no OptFights
if NOSE:
    FIGHTINJ, FIGHTINJANY = 0xFE80, 0xFEB4


def run(rom, out, games, first):
    lowload.gentle()
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / ("return_lines.jsonl" if LINES else "return.jsonl"), "a")

    def note(**k):
        log.write(json.dumps(k) + "\n")
        log.flush()
        print(k, flush=True)

    for n in range(first, first + games):
        def before(e, m):
            m.setw(OPTLINE, 1 if LINES else 0)

        e, m = boot(rom, n, before)

        def byte(a):
            buf, off = m.at(a)
            return buf[off]

        note(what="start", game=n, lines=LINES, optline=m.w(OPTLINE), fightinjany=m.w(FIGHTINJANY))
        hurt = {}                                  # roster slot (0-51) -> record
        frames, still, last, fights, fighting = 0, 0, None, 0, False
        while m.w(GSP) < 3 and frames < 60 * 60 * 45:
            if frames % 60 == 0:
                cvc.computer_only(m)
                m.setw(OPTLINE, 1 if LINES else 0)
                if m.w(CLOCK) > 300:
                    m.setw(CLOCK, 300)
                still = still + 1 if m.w(CLOCK) == last else 0
                last = m.w(CLOCK)
                if frames % 3600 == 0:
                    lowload.breathe()
            if not NOSE:
                m.setw(OPTFIGHTS, 0)                 # Fighting On
            for k in range(12):
                if m.w(0x0F43 + o(k)) != 0:
                    m.setw(FIGHTING + o(k), FIGHT)
                if fighting:                         # only while a fight is on (held always, no fights come)
                    m.setw(AGGRESS + o(k), 60)
            e.run(1, hold=["START"] if still >= 15 and frames % 60 < 4 else [])
            frames += 1
            on = any(m.w(PFLAGS + o(k)) & FIGHTER for k in range(12))
            if on and not fighting:
                fights += 1
            fighting = on
            ice, infight = {}, set()
            for k in range(12):
                if m.w(PFLAGS + o(k)) & FIGHTER and (m.w(PNUM + o(k)) & 0xFF) < 26:
                    infight.add((1 if m.w(PFTEAM + o(k)) else 0) * 26 + (m.w(PNUM + o(k)) & 0xFF))
            for k in range(12):
                p = m.w(PNUM + o(k)) & 0xFF
                role = m.w(0x0F43 + o(k))             # on the ice: a position 0-5 and not parked at x -240 (an idle
                x = m.w(0x0D55 + o(k))                # object keeps its last pnum: 2026-11-23, 120 s "on the ice" in the box)
                if p < 26 and role < 6 and x != 0xFF10:
                    ice[(1 if m.w(PFTEAM + o(k)) else 0) * 26 + p] = k
            tick = frames % 24 == 0 and m.w(CLOCKSTOP) == 0      # a game second of running clock
            for j in range(52):
                w = m.w(TMPDST + 2 * j)
                if j not in hurt:
                    if byte(FIGHTINJ + j) or (ALL and j in infight):
                        hurt[j] = dict(game=n, slot=j, injured=bool(byte(FIGHTINJ + j)), team=j // 26, roster=j % 26, marked=[m.w(GSP), m.w(CLOCK)],
                                       words=[[m.w(GSP), m.w(CLOCK), f"{w:04X}"]], boxed=False, freed=None,
                                       ice_before=0, ice_in_box=0, ice_after=0, pts=[byte(GOALS + j), byte(ASSISTS + j)],
                                       not_out_after=0, stints=[], on=False)
                        note(what="hurt in a fight", **{k: v for k, v in hurt[j].items() if k in ("game", "team", "roster", "marked")},
                             word=f"{w:04X}")
                    continue
                h = hurt[j]
                if byte(FIGHTINJ + j):
                    h["injured"] = True
                if f"{w:04X}" != h["words"][-1][2]:
                    box_now = w < 0x8000 and (w & 0x07FF)
                    if not (box_now and h["words"][-1][2][0] in "0124567" and len(h["words"]) > 3 and abs(int(h["words"][-1][2], 16) - w) <= 2
                            and len(h["words"]) > 40):
                        if len(h["words"]) < 400:
                            h["words"].append([m.w(GSP), m.w(CLOCK), f"{w:04X}"])
                box_time = w < 0x8000 and (w & 0x07FF) != 0
                if box_time:
                    h["boxed"] = True
                elif h["boxed"] and h["freed"] is None:
                    h["freed"] = [m.w(GSP), m.w(CLOCK), f"{w:04X}"]
                    note(what="box time over", game=n, team=h["team"], roster=h["roster"], at=h["freed"][:2], word=f"{w:04X}",
                         on_ice=j in ice)
                # his shifts after the box: where he comes on (x, y; the clock stopped?), and what ends each: the clock
                # stopped at that frame (a whistle), how many of his team's skaters left the ice with him (a line change)
                if h["freed"]:
                    now = j in ice
                    mates = {q for q in ice if q // 26 == j // 26}
                    if now and not h["on"] and len(h["stints"]) < 12:
                        k = ice[j]
                        sx, sy = m.w(0x0D55 + o(k)), m.w(0x0DB7 + o(k))
                        h["stints"].append(dict(on=[m.w(GSP), m.w(CLOCK)], stopped_on=m.w(CLOCKSTOP) != 0,
                                                x=sx - 65536 if sx > 32767 else sx, y=sy - 65536 if sy > 32767 else sy,
                                                role=m.w(0x0F43 + o(k)), frames=0))
                    elif not now and h["on"] and h["stints"]:
                        st = h["stints"][-1]
                        st.update(off=[m.w(GSP), m.w(CLOCK)], stopped_off=m.w(CLOCKSTOP) != 0,
                                  mates_off_too=len(h.get("mates", set()) - mates) - 1)
                    if now and h["stints"]:
                        h["stints"][-1]["frames"] += 1
                    h["on"], h["mates"] = now, mates
                if tick:
                    if j in ice:
                        h["ice_after" if h["freed"] else "ice_in_box" if h["boxed"] else "ice_before"] += 1
                    if h["freed"] and w != 0xFFFC:
                        h["not_out_after"] += 1
        for j, h in hurt.items():
            h.pop("mates", None)
            h.pop("on", None)
            h["pts_end"] = [byte(GOALS + j), byte(ASSISTS + j)]
            h["end_word"] = f"{m.w(TMPDST + 2 * j):04X}"
            h["words"] = h["words"][:6] + (["..."] if len(h["words"]) > 12 else []) + h["words"][-6:] if len(h["words"]) > 12 else h["words"]
            note(what="hurt fighter", **h)
        note(what="game end", game=n, fights=fights, hurt=len(hurt), frames=frames, score=[m.w(0x178E), m.w(0x1790)])


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    run(a[0], Path(a[1]), int(a[2]), int(a[3]) if len(a) > 3 else 0)
