"""NHL '95 (Genesis): NOSE4Web's 3-on-3 overtime (2026-11-16, 5648d86: NHL 94's code at NHL '95's addresses; the eight
places: priolist's readers releasepl $8966A, getlinee $8A392, SetPlList $83790; InProgress' InProgress_ap calls at
$894C6; the overtime mark at $9DCC; the faceoff's .apl row at $888E8; GetLowestPen's tmap test at $9F560;
setpersonel's second pass at $83754). The NHL '94 test (gen_3on3_ot_check.py) at NHL '95's addresses.

Each case: power-on, Game Setup (rows: 5-minute periods, penalties On Except Off-sides, line changes as the case),
into play (the computer on both sides), the game's seed ($FFCC6A) set from SEED, the play mode set (OptPlayMode
$FFCC4C 0, or 2 for playoff cases; `splayoff`: GameFlags bit 3 and $FFD1A7 bit 5, a season's playoff game); the third
period at 0-0 with 2 s left (`carry`: 40 s, the home skaters' Aggression (+$73) at 48 until one of them is boxed, then
played until the home tmap is below 6 in play) and played into overtime. In overtime the away skaters' Aggression is held at 48 (`carry`: home 48) (cases off, on, carry,
playoff, splayoff, pull) so penalties come; `pull` also sets the home team's tmgoalie (+$26) to -1 at the first
stoppage (a pulled goalie). Every 4 frames: each team's skaters on the ice (records with position 1-6, the team from
+$62 bit 6) and their positions, tmap (+$24 of $C288 / $C5EE), the goalie pulled (tmgoalie negative), the players in
the box (tmpdst +$68, 1-$7FFF); kept as segments of the same state. At each faceoff drop (the clock starting): both
teams' players by position and their spots from the puck, and whether each team's skaters number tmap - 1 (or tmap
with the goalie pulled). Screenshots: the first time each count is seen in play (the power-play clock), the first
faceoffs. Until the overtime ends (gsp leaves 3, or the game is over) or MAXF frames; then what follows (a shootout:
gmode2 $FFBF00 bit 0, its attempts and the skaters in them).

python gen95_3on3_check.py ROM CASE OUT [SEEDS] [MAXF]   (NHL95_CROWD=N: the away team's extra aggression only while
  fewer than N of it are boxed; default 2)
  CASE: off | on | carry | playoff | splayoff | reg | pull | tie | tieshort (tieshort: the overtime cut to 40 s once
  running; tie: no extra aggression, the overtime played out, for
  a ROM with a shootout after overtime)"""
import json
import sys
from pathlib import Path

import gen95_assist_check as G
import gen95_fight_check as F
import lowload
from emu import Emu

GSP, CLOCK, GMODE, GMODE2, SFLAGS7, PLAYMODE, SEED = 0xC020, 0xC022, 0xBEF0, 0xBF00, 0xBF02, 0xCC4C, 0xCC6A
OPTPEN, OPTLINE, GAMEFLAGS, SEASONF = 0xCC5A, 0xCC5C, 0xBF08, 0xD1A7
SCORE, TEAMS, TMAP, TMGOALIE, TMPDST = (0xC294, 0xC5FA), (0xC288, 0xC5EE), 0x24, 0x26, 0x68
ROUND, TEAMW, HG, AG = 0xD184, 0xD1A0, 0xD180, 0xD182
POS = {1: "LD", 2: "RD", 3: "LW", 4: "C", 5: "RW", 6: "EA"}
CROWD = int(__import__('os').environ.get('NHL95_CROWD', '2'))   # the extra aggression only while fewer of the team are boxed
AGR = 48                                       # the penalty roll is random(((50 - Agr) / 2) * 13)


def sw(v):
    return v - 0x10000 if v & 0x8000 else v


def stopped(e):
    return bool(e.w(GMODE) & 0x100)          # gmode's first byte, bit 0 (gmclock)


def cpu(e):
    e.setw(0xBF4C, 0); e.setw(0xBF4E, 0)
    for k in range(12):
        e.setb(G.rec(k) + 0x62, e.b(G.rec(k) + 0x62) & ~8)


def team_of(e, k):
    return 1 if e.b(G.rec(k) + 0x62) & 0x40 else 0


def on_ice(e, t):
    out = []
    for k in range(16):
        if k in (14, 15):
            continue
        p = e.w(G.rec(k) + 0x34)
        if 1 <= p <= 6 and team_of(e, k) == t:
            out.append(POS[p])
    return sorted(out)


def boxed(e, t):
    return [i for i in range(26) if 0 < e.w(TEAMS[t] + TMPDST + 2 * i) < 0x8000]


def agr(e, team):
    for k in range(12):
        if team_of(e, k) == team and 1 <= e.w(G.rec(k) + 0x34) <= 6:
            e.setb(G.rec(k) + 0x73, AGR)


def run_case(rom, case, seed, out, maxf):
    e = Emu(rom)
    F.to_setup(e)
    e.setb(F.ROW + 3, 0)                       # 5-minute periods
    e.setb(F.ROW + 6, 2)                       # penalties: On, Except Off-sides
    e.setb(F.ROW + 7, 0 if case == "on" else 1)   # line changes
    e.run(6, hold=["START"]); e.run(300); e.run(6, hold=["START"]); e.run(60); e.run(1800)
    for _ in range(6):
        e.run(6, hold=["START"]); e.run(300)
    opts = {"OptPen": e.w(OPTPEN), "OptLine": e.w(OPTLINE), "sflags7": e.b(SFLAGS7)}
    e.setl(SEED, (0x2545F491 * (seed + 1)) & 0xFFFFFFFF or 1)
    e.setw(PLAYMODE, 2 if case == "playoff" else 0)
    if case == "splayoff":
        e.setb(GAMEFLAGS, e.b(GAMEFLAGS) | 8); e.setb(SEASONF, e.b(SEASONF) | 0x20)
    e.setw(GSP, 2); e.setw(SCORE[0], 0); e.setw(SCORE[1], 0)
    carried = None
    if case == "carry":
        e.setw(CLOCK, 40)
        for f in range(30000):
            if f % 60 == 0:
                cpu(e)
            if not boxed(e, 0):
                agr(e, 0)
            e.run(1, hold=["START"] if f % 300 == 299 and stopped(e) else [])
            if e.w(TEAMS[0] + TMAP) < 6 and boxed(e, 0) and not stopped(e):
                carried = {"clock": e.w(CLOCK), "tmap": [e.w(b + TMAP) for b in TEAMS], "boxed": boxed(e, 0)}
                break
            if e.w(CLOCK) <= 3 and not stopped(e):
                e.setw(CLOCK, 40)
            e.setw(SCORE[0], 0); e.setw(SCORE[1], 0)
    e.setw(CLOCK, 2)
    last = None
    for f in range(40000):                     # into overtime: its clock running
        if f % 60 == 0:
            cpu(e)
        e.run(1, hold=["START"] if f % 300 == 299 and stopped(e) else [])
        c = e.w(CLOCK)
        if e.w(GSP) == 3 and not stopped(e) and last is not None and 0 < c < last and not e.b(GMODE2) & 1:
            break
        last = c if e.w(GSP) == 3 else None
    else:
        return {"case": case, "seed": seed, "error": "no overtime", "gsp": e.w(GSP), "opts": opts}
    ot_flag = bool(e.b(SFLAGS7) & 2)
    if case == "tieshort":
        e.setw(CLOCK, 40)                      # a short 3-on-3 overtime, then whatever follows a tie
    segs, faceoffs, seen, f, was_stopped, pulled = [], [], set(), 0, False, False
    pp = case in ("off", "on", "carry", "playoff", "splayoff", "pull")
    while f < maxf:
        if f % 60 == 0:
            cpu(e)
        if pp and len(boxed(e, 1)) < CROWD:
            agr(e, 1)
        if case == "pull" and not pulled and stopped(e) and f > 60:
            e.setw(TEAMS[0] + TMGOALIE, 0xFFFF); pulled = True
        st = stopped(e)
        e.run(4, hold=["START"] if f % 300 == 296 and st else [])
        f += 4
        if e.w(GSP) != 3 or e.b(GMODE2) & 1:
            break
        h, a = on_ice(e, 0), on_ice(e, 1)
        tm = [e.w(b + TMAP) for b in TEAMS]
        gl = [bool(e.w(b + TMGOALIE) & 0x8000) for b in TEAMS]
        bx = [len(boxed(e, 0)), len(boxed(e, 1))]
        tw = [[f"{e.w(TEAMS[t] + TMPDST + 2 * i):04X}" for i in boxed(e, t)] for t in (0, 1)]
        st = stopped(e)
        key = (tuple(h), tuple(a), tuple(tm), tuple(gl), tuple(bx))
        if not segs or segs[-1]["key"] != key:
            segs.append({"key": key, "from": f, "to": f, "clock": e.w(CLOCK), "stopped": st, "tmpdst": tw})
            tag = f"{len(h)}v{len(a)}_g{int(gl[0])}{int(gl[1])}"
            if tag not in seen and not st:
                seen.add(tag)
                e.screenshot(out / f"{case}_{seed}_{tag}.png")
        else:
            segs[-1]["to"] = f
        if was_stopped and not st:
            px, py = sw(e.w(G.PUCK)), sw(e.w(G.PUCK + 0x14))
            spots = {}
            for k in range(12):
                p = e.w(G.rec(k) + 0x34)
                if 1 <= p <= 6:
                    spots[f"{'HA'[team_of(e, k)]}{POS[p]}"] = (sw(e.w(G.rec(k))) - px, sw(e.w(G.rec(k) + 0x14)) - py)
            short = [len(x) != (t - (0 if g else 1)) for x, t, g in ((h, tm[0], gl[0]), (a, tm[1], gl[1]))]
            faceoffs.append({"f": f, "clock": e.w(CLOCK), "home": h, "away": a, "tmap": tm, "pulled": gl,
                             "boxed": bx, "short": short, "spots": spots})
            if len(faceoffs) <= 3:
                e.screenshot(out / f"{case}_{seed}_faceoff{len(faceoffs)}.png")
        was_stopped = st
    shoot = {"seen": False, "attempts": [], "skaters": set()}
    end = None
    ended = f < maxf
    for g in range(60 * 60 * 20 // 4 if ended else 0):          # what follows
        if g % 15 == 0:
            cpu(e)
        if e.b(GMODE2) & 1:
            shoot["seen"] = True
            k2 = (e.w(ROUND), e.w(TEAMW))
            if not shoot["attempts"] or shoot["attempts"][-1][:2] != list(k2):
                shoot["attempts"].append([k2[0], k2[1], e.w(HG), e.w(AG)])
            n = (len(on_ice(e, 0)), len(on_ice(e, 1)))
            if not stopped(e):
                shoot["skaters"].add(n)
        sig = (e.w(CLOCK), e.w(G.PUCK))
        e.run(4, hold=["START"] if g % 75 == 74 and (stopped(e) or e.b(GMODE2) & 1) and e.b(G.PUCK + 0x60) else [])
        if e.w(GSP) >= 4:
            end = {"score": [e.w(SCORE[0]), e.w(SCORE[1])], "shootout goals": [e.w(HG), e.w(AG)]}
            e.run(300); e.screenshot(out / f"{case}_{seed}_end.png")
            break
        if e.w(GSP) == 3 and not shoot["seen"] and not stopped(e) and e.w(CLOCK) > 250:
            end = {"another overtime": True, "score": [e.w(SCORE[0]), e.w(SCORE[1])]}
            break
    for s in segs:
        s["key"] = [list(x) for x in s["key"]]
    shoot["skaters"] = sorted(shoot["skaters"])
    return {"case": case, "seed": seed, "opts": opts, "ot_flag": ot_flag, "carried": carried, "frames": f,
            "score": [e.w(SCORE[0]), e.w(SCORE[1])], "segments": segs, "faceoffs": faceoffs, "after": end,
            "shootout": shoot}


def main():
    rom, case, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    seeds = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    maxf = int(sys.argv[5]) if len(sys.argv) > 5 else 15000
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    for s in range(seeds):
        r = run_case(rom, case, s, out, maxf)
        with open(out / f"{Path(rom).stem}_{case}.jsonl", "a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(json.dumps({k: r.get(k) for k in ("case", "seed", "opts", "ot_flag", "carried", "frames", "score",
                                                 "after", "error")}), flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
