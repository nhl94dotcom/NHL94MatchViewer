"""SNES: one-timer swings that end with the receiver holding the puck (2026-11-13, the user's "one-timer that never
fires": the swing plays with the puck on his stick and no shot comes; 2 of 503 swings in the recorded games, one a
computer player's). Computer games (snes_ot_goal_check.start: penalties on, the seed from the game's number; the
computer one-times on its own in the attacking zone), every frame for each object in a one-timer swing (SPA $11A3 =
SPAonetimerf $EF6E / SPAonetimerb $F020) a trace row: SPAnum $11C3, SPAcnt $11E3, asscur $0B7D (asspassrec is $15),
nopuck $1203, passwait $0BAD, pfalock $14E3, puckc $0AD9, onetimerreq $0BAB, onetimer $1E89, passReceiverPlayerNum $0D07,
the puck (x, y, z) and the object (x, y). At the swing's end: "struck" (the team's tmOneTimers $17D6 rose), "held" (he
had the puck at some frame and no strike: also a carrier whose own shot, with this animation, he gathered again),
"missed" (neither). Every held swing is kept whole (with the 30 frames before it); the others counted. (The first run,
24 games, compared puckc with the object number; its rows were re-read offline with the object number x 2.)

python snes_onetimer_hold_trace.py ROM GAMES OUT.jsonl [FIRST]"""
import json
import sys
from pathlib import Path

import lowload
from snes_60fps_cvc import CLOCK, GSP, computer_only
from snes_ot_goal_check import start

SPA, SPANUM, SPACNT, ASSCUR, NOPUCK, PASSWAIT, PFALOCK = 0x11A3, 0x11C3, 0x11E3, 0x0B7D, 0x1203, 0x0BAD, 0x14E3
PUCKC, OTREQ, ONETIMER, PASSREC, TMONETIMERS = 0x0AD9, 0x0BAB, 0x1E89, 0x0D07, 0x17D6
XPOS, YPOS, PFTEAM, PUCKZ = 0x0D55, 0x0DB7, 0x1503, 0x0DF9
SWINGS = (0xEF6E, 0xF020)


def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def row(m, k, f):
    return [f, m.w(SPANUM + 2 * k), s16(m.w(SPACNT + 2 * k)), m.w(ASSCUR + 2 * k), m.w(NOPUCK + 2 * k),
            s16(m.w(PASSWAIT + 2 * k)), m.w(PFALOCK + 2 * k), s16(m.w(PUCKC)), m.w(OTREQ), m.w(ONETIMER),
            s16(m.w(PASSREC)), [s16(m.w(XPOS + 28)), s16(m.w(YPOS + 28)), m.w(PUCKZ)],
            [s16(m.w(XPOS + 2 * k)), s16(m.w(YPOS + 2 * k))]]


COLS = ["f", "SPAnum", "SPAcnt", "asscur", "nopuck", "passwait", "pfalock", "puckc", "onetimerreq", "onetimer",
        "passReceiver", "puck", "player"]


def game(rom, n, tmp):
    e, m = start(rom, n, tmp)
    hist = {k: [] for k in range(12)}
    swing = {}
    counts = {"struck": 0, "held": 0, "missed": 0}
    held = []
    f, still, last = 0, 0, None
    while m.w(GSP) < 3 and f < 60 * 60 * 40:
        if f % 300 == 0:
            computer_only(m)
            if f % 3600 == 0:
                lowload.breathe()
        if f % 60 == 0:
            c = m.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
        e.run(1, hold=["START"] if still >= 8 and f % 60 < 4 else [])
        f += 1
        for k in range(12):
            r = row(m, k, f)
            h = hist[k]
            h.append(r)
            if len(h) > 30:
                h.pop(0)
            in_swing = m.w(SPA + 2 * k) in SWINGS
            if in_swing and k not in swing:
                team = 0 if m.w(PFTEAM + 2 * k) == 0 else 1
                swing[k] = {"k": k, "team": team, "start": f, "ot0": m.w(TMONETIMERS + 2 * team), "rows": list(h[:-1]),
                            "had": False, "clock": m.w(CLOCK), "period": m.w(GSP)}
            if k in swing:
                s = swing[k]
                if in_swing:
                    s["rows"].append(r)
                    s["had"] |= s16(m.w(PUCKC)) == 2 * k          # puckc is the object number x 2
                else:
                    struck = m.w(TMONETIMERS + 2 * s["team"]) != s["ot0"]
                    kind = "struck" if struck else "held" if s["had"] else "missed"
                    counts[kind] += 1
                    if kind == "held":
                        s["rows"] += [row(m, k, f + i) for i in range(1)]
                        held.append({x: s[x] for x in ("k", "team", "start", "clock", "period")} | {"cols": COLS, "rows": s["rows"]})
                    del swing[k]
    return {"game": n, "frames": f, "counts": counts, "held": held}


def main():
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    lowload.gentle()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "_boot"
    tmp.mkdir(parents=True, exist_ok=True)
    for n in range(first, first + games):
        r = game(rom, n, tmp)
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(json.dumps({"game": n, "frames": r["frames"], "counts": r["counts"]}), flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
