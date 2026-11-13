"""NOSE4Web's hybrid icing (Genesis, 82a9a22: nhl94_hybrid_icing.bin, CDL_Season_12_hybrid_icing.bin), played
(2026-11-13). The build's PuckIChk, at the goal-line crossing outside the crease's width, races the two teams'
skaters to the line across the end-zone dots (y +-206, distance in y only, past it 0; goalies and pf2unav skipped):
the defenders as near or nearer, icing is called (AddPenalty PenIcing for icingPlayer); else ifok is cleared.

Computer games (the computer on both sides, the seed from the game's number), penalties on except offsides, line
changes LINES (default on), 5-minute periods; the away skaters at Aggression AGR (default 30) so some power plays come.
Watched every frame (iflags $FFBF80: bit 0 crossed, 1 the top line, 2 armed; icingPlayer the byte after):
- **armed:** ifok set: the icing player's team and both tmaps; armed short-handed is a fault (point 3);
- **the crossing:** ifcgl set: the puck x, y; each team's skaters' distance to the dot line by the build's rule (and
  who is skipped: in the box / changing, pf2unav), the goalie's position (pulled?), the tmaps, and the outcome: called
  (PenBuf gets PenIcing $C for icingPlayer) or waved off (ifok cleared); for a call the frames until the clock stops
  and the faceoff spot after it (the puck at the drop: should be the icing team's end);
- **the crease:** ifok cleared, ifcgl not set, a loose puck past the goal line within |x| <= 44 (point 4);
- **after a wave-off:** the frames until the next stoppage, so play goes on (point 2).
On retail (no hack) the same log shows the standard calls (on a defender's touch) for comparison.

python gen_hybrid_icing_check.py ROM GAMES OUT.jsonl [FIRST]"""
import json
import os
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

OPTPEN, OPTLINE, PERLEN, SEED = 0xD056, 0xD058, 0xD050, 0xD066
CONT1, CONT2, GSP, CLOCK, SCREEN, GMODE = 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7, 0xC2EA
TEAMS, TMAP = (0xC6CE, 0xCA32), 0x24
BASE, SZ, PUCK, PUCKC = 0xB04A, 0x80, 0xB04A + 14 * 0x80, 0xB7AA
IFLAGS, IPLAYER, PENBUF = 0xBF80, 0xBF81, 0xC3A4
AGR = int(os.environ.get("NHL94_AGR", "30"))
LINES = os.environ.get("NHL94_LINES", "on")


def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def race(e, top):
    """Each team's least distance to the dot line by the build's rule, and who was skipped."""
    line = 206 if top else -206
    out = []
    for t in (0, 1):
        best, skipped, goalie_on = 0x7FFF, [], False
        for k in range(6 * t, 6 * t + 6):
            pos = s16(e.w(BASE + SZ * k + 0x34))
            if pos == 0:
                goalie_on = True
            if pos <= 0:
                continue
            if e.b(BASE + SZ * k + 0x63) & 4:
                skipped.append(k)
                continue
            y = s16(e.w(BASE + SZ * k + 0x14))
            d = (line - y) if top else (y - line)
            best = min(best, max(d, 0))
        out.append({"best": best, "skipped": skipped, "goalie_on": goalie_on})
    return out


def skaters(e):
    """Each object's position word, pf2unav and y: [k, position, unav, y]."""
    return [[k, s16(e.w(BASE + SZ * k + 0x34)), bool(e.b(BASE + SZ * k + 0x63) & 4), s16(e.w(BASE + SZ * k + 0x14))]
            for k in range(12)]


def penbuf(e):
    return [(e.b(PENBUF + 2 * i), e.b(PENBUF + 2 * i + 1)) for i in range(33) if e.w(PENBUF + 2 * i)]


def game(rom, n, tmp):
    e = Emu(rom)
    G.to_setup(e, tmp)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 0 if LINES == "on" else 1)
    e.setw(PERLEN, 0)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    events, f, still, last, prev = [], 0, 0, None, e.b(IFLAGS)
    pending = None          # a crossing waiting for its outcome (the clock stopping, or the next stoppage)
    while e.w(GSP) < 3 and f < 60 * 60 * 40:
        if f % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if f % 3600 == 0:
                lowload.breathe()
        for k in range(6, 12):
            if 1 <= e.b(BASE + SZ * k + 0x35) <= 6:
                e.setb(BASE + SZ * k + 0x73, AGR)
        pre = {"puck": (s16(e.w(PUCK)), s16(e.w(PUCK + 0x14))), "race": race(e, bool(e.b(IFLAGS) & 2)),
               "pen": penbuf(e), "sk": skaters(e), "fl": e.b(IFLAGS)}
        e.run(1, hold=["START"] if still >= 8 and f % 60 < 4 else [])
        f += 1
        if e.b(SCREEN) != 0:
            prev = e.b(IFLAGS)
            continue
        fl, stopped = e.b(IFLAGS), bool(e.b(GMODE) & 1)
        tm = [e.w(TEAMS[0] + TMAP), e.w(TEAMS[1] + TMAP)]
        ip = e.b(IPLAYER)
        team = 0 if ip < 6 else 1
        px, py = s16(e.w(PUCK)), s16(e.w(PUCK + 0x14))
        if fl & 4 and not prev & 4:
            if tm[team] < tm[1 - team]:
                events.append({"f": f, "what": "armed short-handed", "team": team, "tmap": tm, "puck": [px, py]})
        if fl & 1 and not prev & 1 and prev & 4:
            new = [p for p in penbuf(e) if p not in pre["pen"]]
            called = any(p[0] == 0x0C for p in new)
            r = race(e, bool(fl & 2))
            ev = {"f": f, "what": "called" if called else ("waved off" if not fl & 4 else "crossed, open"),
                  "sk_before": pre["sk"], "sk_after": skaters(e), "pen_before": pre["pen"], "pen_after": penbuf(e),
                  "fl_before": pre["fl"], "fl_after": fl, "race_before": pre["race"],
                  "team": team, "player": ip, "tmap": tm, "puck": [px, py], "clock": e.w(CLOCK), "period": e.w(GSP),
                  "def": r[1 - team], "att": r[team], "lines": LINES, "stopped_at": None, "faceoff": None}
            events.append(ev)
            pending = ev
        if prev & 4 and not fl & 4 and not fl & 1 and not prev & 1 and e.w(PUCKC) >= 0x8000:
            if abs(pre["puck"][0]) <= 44 and abs(pre["puck"][1]) >= 258:     # PuckIChk's window, at the line
                events.append({"f": f, "what": "dropped in the crease width", "team": team, "puck": [px, py],
                               "puck_before": pre["puck"]})
        if pending is not None and pending["what"] == "crossed, open":      # retail: decided at the next touch
            if any(p[0] == 0x0C for p in penbuf(e) if p not in pre["pen"]):
                pending["what"], pending["decided_after"] = "called on a touch", f - pending["f"]
            elif not fl & 4:
                pending["what"], pending["decided_after"] = "waved off on a touch", f - pending["f"]
        if pending is not None:
            if pending["stopped_at"] is None and stopped:
                pending["stopped_at"] = f - pending["f"]
            if pending["stopped_at"] is not None and pending["faceoff"] is None and not stopped:
                pending["faceoff"] = [px, py]
                pending = None
            elif f - pending["f"] > 60 * 60 * 3:
                pending = None
        prev = fl
    return {"game": n, "frames": f, "events": events}


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
        ev = r.get("events", [])
        kinds = {}
        for x in ev:
            kinds[x["what"]] = kinds.get(x["what"], 0) + 1
        print(json.dumps({"game": n, "frames": r.get("frames"), "error": r.get("error"), "events": kinds}), flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
