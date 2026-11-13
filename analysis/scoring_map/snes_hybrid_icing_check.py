"""NOSE4Web's SNES icing options (b98739a: NHL94_icing.smc, nhl94snes_SA1_icing.sfc, both options on), played
(2026-11-13); gen_hybrid_icing_check.py is the Genesis one. The build wraps pucknorm's PuckIChk call ($9E:DD40 ->
$9B:FF20): on the call where the loose puck crosses (ifok and ifcgl newly set), the two teams' skaters race to the dot
line (y +-206, y only, past it 0; goalies, off-ice and pf2unav skipped): the defenders as near or nearer, AddPenalty
PenIcing for icingPlayer; else ifok cleared. And PuckIChk's .3 ($9E:F783 -> $9B:FFE4): a crossing within |x| <= 44
drops the icing (ifok cleared), as on the Genesis.

Computer games from snes_ot_goal_check.start (penalties on, No Offside; line changes LINES, default on; the game's
seed from its number), 5-minute periods as the build has them; the away skaters' Aggression ($1443) at AGR (default
18). Every frame, iflags ($0CF1: bit 0 crossed, 1 the top line, 2 armed; icingPlayer its high byte):
- armed short-handed (tmap $17A6, away +2): a fault;
- each crossing: puck x, y, both teams' distances by the build's rule, the outcome (PenBuf $15DE gets PenIcing $C:
  called; ifok cleared: waved off; neither: open, decided at a touch as retail), the frames to the stoppage and the
  faceoff spot (the puck at the drop);
- a drop within the crease width (ifok cleared, no crossing, the loose puck at the goal line);
- the early wave-off by updateplayers (a defender within 30 of a slow low puck), counted apart.

python snes_hybrid_icing_check.py ROM GAMES OUT.jsonl [FIRST]"""
import json
import os
import sys
from pathlib import Path

import lowload
from snes_60fps_cvc import CLOCK, CLOCKSTOP, GSP, computer_only
from snes_ot_goal_check import start

IFLAGS, PUCKX, PUCKY, PUCKC, TMAP, PENBUF = 0x0CF1, 0x0D71, 0x0DD3, 0x0AD9, 0x17A6, 0x15DE
POSITION, PFLAGS, YPOS, PFTEAM, AGGRESS, OPTLINE = 0x0F43, 0x1283, 0x0DB7, 0x1503, 0x1443, 0x34C6
AGR = int(os.environ.get("NHL94_AGR", "18"))
LINES = os.environ.get("NHL94_LINES", "on")


def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def race(m, top, icer_team):
    line = 206 if top else -206
    best = [0x7FFF, 0x7FFF]
    skipped, goalie = [[], []], [False, False]
    for k in range(12):
        pos, t = s16(m.w(POSITION + 2 * k)), 0 if m.w(PFTEAM + 2 * k) == 0 else 1
        if pos == 0:
            goalie[t] = True
        if pos <= 0:
            continue
        if m.w(PFLAGS + 2 * k) & 0x1000:
            skipped[t].append(k)
            continue
        y = s16(m.w(YPOS + 2 * k))
        best[t] = min(best[t], max((line - y) if top else (y - line), 0))
    return {"def": best[1 - icer_team], "att": best[icer_team], "skipped": skipped, "goalie_on": goalie}


def penbuf(m):
    out = []
    for i in range(32):
        w = m.w(PENBUF + 2 * i)
        if not w:
            break
        out.append((w & 0xFF, w >> 8))
    return out


def game(rom, n, tmp):
    e, m = start(rom, n, tmp)
    m.setw(OPTLINE, 1 if LINES == "on" else 0)
    events, f, prev, pending, still, last = [], 0, m.w(IFLAGS), None, 0, None
    while m.w(GSP) < 3 and f < 60 * 60 * 40:
        if f % 300 == 0:
            computer_only(m)
            if f % 3600 == 0:
                lowload.breathe()
        if f % 60 == 0:
            c = m.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
        for k in range(12):
            if m.w(PFTEAM + 2 * k) != 0:
                m.setw(AGGRESS + 2 * k, AGR)
        pre_pen, pre_puck = penbuf(m), (s16(m.w(PUCKX)), s16(m.w(PUCKY)))
        e.run(1, hold=["START"] if still >= 8 and f % 60 < 4 else [])
        f += 1
        fl = m.w(IFLAGS)
        stopped = m.w(CLOCKSTOP) != 0
        icer = (fl >> 8) & 0xFF
        team = 0 if m.w(PFTEAM + 2 * icer) == 0 else 1 if icer < 12 else -1
        tm = [m.w(TMAP), m.w(TMAP + 2)]
        px, py = s16(m.w(PUCKX)), s16(m.w(PUCKY))
        loose = m.w(PUCKC) >= 0x8000
        if fl & 4 and not prev & 4 and team >= 0 and tm[team] < tm[1 - team]:
            events.append({"f": f, "what": "armed short-handed", "team": team, "tmap": tm, "puck": [px, py]})
        if fl & 1 and not prev & 1 and prev & 4:
            new = [p for p in penbuf(m) if p not in pre_pen]
            called = any(p[0] == 0x0C for p in new)
            ev = {"f": f, "what": "called" if called else ("waved off" if not fl & 4 else "crossed, open"),
                  "team": team, "player": icer, "tmap": tm, "puck": [px, py], "clock": m.w(CLOCK), "period": m.w(GSP),
                  **race(m, bool(fl & 2), max(team, 0)), "stopped_at": None, "faceoff": None}
            events.append(ev)
            pending = ev
        elif prev & 4 and not fl & 4 and not fl & 1 and not prev & 1 and loose:
            what = ("dropped in the crease width" if abs(pre_puck[0]) <= 44 and abs(pre_puck[1]) >= 258
                    else "early wave-off" if abs(pre_puck[1]) < 258 else "cleared at the line, outside the window")
            events.append({"f": f, "what": what, "team": team, "puck": [px, py], "puck_before": list(pre_puck)})
        if pending is not None and pending["what"] == "crossed, open":
            if any(p[0] == 0x0C for p in penbuf(m) if p not in pre_pen):
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
        kinds = {}
        for x in r["events"]:
            kinds[x["what"]] = kinds.get(x["what"], 0) + 1
        print(json.dumps({"game": n, "frames": r["frames"], "events": kinds}), flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
