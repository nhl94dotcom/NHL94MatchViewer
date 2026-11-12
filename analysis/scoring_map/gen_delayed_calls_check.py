"""Calls during a delayed penalty (2026-11-12, for NOSE4Web 86e06ef: nhl94_delayed_calls.bin, checkagr's team test
skipped by a bra.w at $13EC4; known bug 12). The computer against itself (gen_injury_baseline's way: Game Setup with
penalties On Except Off-sides (OptPen $D056 = 2), line changes off, 5-minute periods; the seed from the game's number),
every skater's working Aggression (+$73) held at AGR (default 30: checkagr's range (40 - Agr) / 2 x 13 = 65, so
penalties come often). Every 2 frames:
- a new PenBuf entry ($C3A4, 33 words: penalty byte, player byte (bit 7: called)): its team, and whether the OTHER team
  had a penalty pending then (DelayedPen $C300 bit 1 home / 2 away): a "cross" call, which the original never makes;
- each whistle that sent players off: the PenBuf entries by team, and both teams' tmap (+$24 of the team structs $C6CE /
  $CA32) when play resumed (5 and 5 = 4-on-4);
- the delayed-penalty goalie pull: frames with gmpendel (gmode $C2EA bit 3) set and a team's tmgoalie (+$26) negative,
  and which team (the one with the puck, $B7AA);
- each goal: PenBuf's entries and DelayedPen at that moment, the box and tmap at the next faceoff;
- at the end: the penalty log (PenSumLength $C5DC / 4 entries) against the teams' tmPenalties (+$6).

python gen_delayed_calls_check.py ROM GAMES OUT.jsonl   (one emulator a game, resumes)
python gen_delayed_calls_check.py --pending BUILD RETAIL GAMES K OUT.json   (a moment with one minor pending and both
  teams at six, found in each of BUILD's games; K trials from it on both ROMs, the team with the puck at Aggression
  NHL94_AGR: was it called, did play stop at once, the players on the ice after)"""
import json
import os
import subprocess
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

OPTPEN, OPTLINE, PERLEN, SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD056, 0xD058, 0xD050, 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
GMODE, DELAYED, PENBUF, PENSUMLEN, PUCKC = 0xC2EA, 0xC300, 0xC3A4, 0xC5DC, 0xB7AA
TEAMS = (0xC6CE, 0xCA32)
TMAP, TMGOALIE, TMPEN, SCORE = 0x24, 0x26, 0x6, (0xC6DA, 0xCA3E)
BASE, SZ = 0xB04A, 0x80
AGR = int(os.environ.get("NHL94_AGR", "30"))


def game(rom, n, tmp):
    e = Emu(rom)
    G.to_setup(e, tmp)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1)
    e.setw(PERLEN, 0)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    seen = [0] * 33
    entries, crosses, whistles, goals, pulls = [], 0, [], [], {"frames": 0, "teams": {}}
    frame, still, last, was_pen, pend_goal, score = 0, 0, None, False, None, (0, 0)
    cur = []                                        # entries since the last whistle was dealt with
    while e.w(GSP) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
        for k in range(12):
            if e.b(BASE + SZ * k + 0x35) not in (0, 0xFF):
                e.setb(BASE + SZ * k + 0x73, AGR)
        e.run(2, hold=["START"] if still >= 8 and frame % 60 < 4 else [])
        frame += 2
        if e.b(SCREEN) != 0:
            continue
        d = e.b(DELAYED)
        gm = e.b(GMODE)                         # btst on (gmode).w reads its first byte
        for i in range(33):
            w = e.w(PENBUF + 2 * i)
            pen, pl = w >> 8, w & 0x7F
            if w and (seen[i] & 0x7F7F) != (w & 0x7F7F):
                team = 1 if pl >= 6 else 0
                other_pending = bool(d & (4 if team == 0 else 2))
                own_pending = bool(d & (2 if team == 0 else 4))
                pc = e.w(PUCKC)
                ent = {"f": frame, "pen": pen, "player": pl, "team": team, "other_pending": other_pending,
                       "own_pending": own_pending, "clock": e.w(CLOCK), "period": e.w(GSP),
                       "puck_team": None if pc >= 12 else (1 if pc >= 6 else 0), "stopped": bool(gm & 1)}
                entries.append(ent)
                cur.append(ent)
                crosses += other_pending
            seen[i] = w
        if gm & 8:                                  # gmpendel: a delayed call is up
            for t, b in enumerate(TEAMS):
                if e.w(b + TMGOALIE) & 0x8000:
                    pulls["frames"] += 2
                    pc = e.w(PUCKC)
                    key = f"team{t}_puck{None if pc >= 12 else (1 if pc >= 6 else 0)}"
                    pulls["teams"][key] = pulls["teams"].get(key, 0) + 2
        pen_now = bool(gm & 4)
        if was_pen and not pen_now:                 # the whistle's penalties dealt with: play resumes at a faceoff
            mins = [x for x in cur if x["pen"] not in (0x0C, 0x0E, 0x10, 0x06, 0x0A)]
            whistles.append({"f": frame, "entries": [(x["team"], x["pen"], x["other_pending"]) for x in cur],
                             "tmap": [e.w(b + TMAP) for b in TEAMS], "teams_called": sorted({x["team"] for x in mins})})
            cur = []
        was_pen = pen_now
        sc = (e.w(SCORE[0]), e.w(SCORE[1]))
        if sc != score:
            goals.append({"f": frame, "scorer": 0 if sc[0] > score[0] else 1, "delayed": d,
                          "penbuf": [e.w(PENBUF + 2 * i) for i in range(33) if e.w(PENBUF + 2 * i)],
                          "tmap": [e.w(b + TMAP) for b in TEAMS]})
            score = sc
    log_n = e.w(PENSUMLEN) // 4
    return {"game": n, "frames": frame, "periods": e.w(GSP), "score": list(score), "entries": entries,
            "cross_calls": crosses, "whistles": whistles, "goals": goals, "pulls": pulls,
            "log_entries": log_n, "tm_penalties": [e.w(b + TMPEN) for b in TEAMS]}


NOPEN = {0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x10, 0x14}      # whistles and the like: no minutes


def find_pending(rom, n, tmp):
    """Play game n (the ratings as they are) until one team has a minor pending (gmpendel up, one PenBuf entry with
    minutes) with both teams at six: that moment's state, the penalized team, or None."""
    e = Emu(rom)
    G.to_setup(e, tmp)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1)
    e.setw(PERLEN, 0)
    if not G.into_play(e):
        return None, None
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    frame, still, last = 0, 0, None
    while e.w(GSP) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
        e.run(2, hold=["START"] if still >= 8 and frame % 60 < 4 else [])
        frame += 2
        if e.b(SCREEN) != 0 or not e.b(GMODE) & 8 or e.b(GMODE) & 1:
            continue
        ents = [e.w(PENBUF + 2 * i) for i in range(33) if e.w(PENBUF + 2 * i)]
        mins = [w for w in ents if (w >> 8) not in NOPEN]
        if len(ents) == 1 and len(mins) == 1 and [e.w(b + TMAP) for b in TEAMS] == [6, 6] and e.w(PUCKC) < 12:
            return e.serialize(), 1 if (mins[0] & 0x7F) >= 6 else 0
    return None, None


def trials(rom, state, pen_team, k, agr):
    """From the saved moment: the team with the puck (not the penalized one) at Aggression agr, a fresh seed each
    trial; to the end of the whistle's penalties (or 2,400 frames). What was called, how soon play stopped after it,
    and tmap when play resumed."""
    e = Emu(rom)
    out = []
    other = 1 - pen_team
    for t in range(k):
        e.unserialize(state)
        e.setl(SEED, (0x9E3779B1 * (t + 1)) & 0xFFFFFFFF or 1)
        seen = {e.w(PENBUF + 2 * i) & 0x7F7F for i in range(33) if e.w(PENBUF + 2 * i)}
        f, call, stop_at, was_pen, res = 0, None, None, False, None
        while f < 2400:
            for j in range(6 * other, 6 * other + 6):
                if e.b(BASE + SZ * j + 0x35) not in (0, 0xFF):
                    e.setb(BASE + SZ * j + 0x73, agr)
            e.run(2)
            f += 2
            gm = e.b(GMODE)
            for i in range(33):
                w = e.w(PENBUF + 2 * i) & 0x7F7F
                if w and w not in seen:
                    seen.add(w)
                    tm = 1 if (w & 0x7F) >= 6 else 0
                    if call is None and tm == other and (w >> 8) not in NOPEN:
                        pc = e.w(PUCKC)
                        call = {"f": f, "pen": w >> 8, "puck_team": None if pc >= 12 else (1 if pc >= 6 else 0)}
            if gm & 1 and stop_at is None:
                stop_at = f
            if gm & 4:
                was_pen = True
            elif was_pen:
                res = [e.w(b + TMAP) for b in TEAMS]
                break
        out.append({"trial": t, "call": call, "stop_at": stop_at, "tmap_after": res,
                    "goalie_out": [bool(e.w(b + TMGOALIE) & 0x8000) for b in TEAMS]})
    return out


def pending_main(games, k, agr, out):
    """--pending BUILD RETAIL GAMES K OUT.json: the saved moments come from BUILD's games; trials on both ROMs."""
    build, retail = sys.argv[2], sys.argv[3]
    res = []
    for n in range(games):
        state, pen_team = find_pending(build, n, out.parent / "_boot")
        if state is None:
            continue
        res.append({"game": n, "pen_team": pen_team, "build": trials(build, state, pen_team, k, agr),
                    "retail": trials(retail, state, pen_team, k, agr)})
        out.write_text(json.dumps(res))
        lowload.breathe()


def main():
    if sys.argv[1] == "--pending":
        lowload.gentle()
        return pending_main(int(sys.argv[4]), int(sys.argv[5]), AGR, Path(sys.argv[6]))
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    lowload.gentle()
    done = {json.loads(line)["game"] for line in out.read_text().splitlines()} if out.exists() else set()
    for n in range(games):
        if n in done:
            continue
        r = subprocess.run([sys.executable, __file__, "--one", rom, str(n), str(out.parent / "_boot")],
                           capture_output=True, text=True)
        line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else json.dumps({"game": n, "error": r.stderr[-300:]})
        with out.open("a") as fh:
            fh.write(line + "\n")
        print(line[:300], flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "--one":
        p = Path(sys.argv[4])
        p.mkdir(parents=True, exist_ok=True)
        print(json.dumps(game(sys.argv[2], int(sys.argv[3]), p)))
    else:
        main()
