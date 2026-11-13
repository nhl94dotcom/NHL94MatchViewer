"""3-on-3 overtime (2026-11-12, for NOSE4Web a91a6f8: nhl94_3on3_ot.bin, every overtime; CDL_Season_12_3on3_ot.bin,
regular season only). In overtime (sflags7 bit 1, not a shootout) the fill order is G, C, LW, RD, LD, RW, extra
attacker; each team has tmap 4 plus one for each penalty the other team has beyond its own (at most 2); the faceoff
uses the full-strength row.

Each case: power-on, Game Setup, then in RAM penalties On Except Off-sides (OptPen $D056 = 2), line changes (OptLine
$D058: 0 on, 1 off), 5-minute periods, the play mode (OptPlayMode $D048: 0 regular season, 2 playoffs); into play,
the computer on both sides; the third period's clock set to 2 s at 0-0 (or, with `carry`, to 40 s with the home
team's Aggression at 38 until a home minor is being served, then to 2 s) and played into overtime. In overtime the
away team's skaters are held at Aggression AGR (`pp` cases; default 38) so penalties come. Every 4 frames: each
team's skaters on the ice (objects with position 1-6) and their positions, tmap (+$24 of $C6CE / $CA32), the goalie
(tmgoalie +$26 negative = pulled), the penalty box; kept as segments of the same (home, away) count. At each faceoff
drop (the clock starting again): both teams' players by position, their spots relative to the puck, and a screenshot of the first few; a screenshot the first time each count is seen (the
power-play clock on the scoreboard). Until the overtime ends (gsp leaves 3) or 15,000 frames; then what follows (the
shootout flag gmode2 $C2FA bit 0, and the skaters in it).

python gen_3on3_ot_check.py ROM CASE OUT [SEEDS]   (NHL94_AGR_UNTIL_CROWDED=1: the aggression only until three of
  a team are in the box, to see them come out)
  CASE: off | on | carry | playoff | reg   (off / on: line changes off / on, penalties in overtime; carry: a home
  minor carried over from the third period; playoff: OptPlayMode 2; reg: regular season, no extra aggression)"""
import json
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

OPTPEN, OPTLINE, PERLEN, PLAYMODE, SEED = 0xD056, 0xD058, 0xD050, 0xD048, 0xD066
CONT1, CONT2, GSP, CLOCK, SCREEN, GMODE, GMODE2, PENBUF = 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7, 0xC2EA, 0xC2FA, 0xC3A4
SCORE, TEAMS, TMAP, TMGOALIE = (0xC6DA, 0xCA3E), (0xC6CE, 0xCA32), 0x24, 0x26
BASE, SZ, PUCK = 0xB04A, 0x80, 14
POS = {1: "LD", 2: "RD", 3: "LW", 4: "C", 5: "RW", 6: "EA"}
AGR = 38


def sw(v):
    return v - 0x10000 if v & 0x8000 else v


def cpu(e):
    e.setw(CONT1, 0)
    e.setw(CONT2, 0)
    for k in range(12):
        e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)


def on_ice(e, t):
    return sorted(POS.get(e.b(BASE + SZ * k + 0x35), "?") for k in range(6 * t, 6 * t + 6)
                  if 1 <= e.b(BASE + SZ * k + 0x35) <= 6)


UNTIL_CROWDED = bool(__import__("os").environ.get("NHL94_AGR_UNTIL_CROWDED"))


def boxed_of(e, t):
    """The team's players in the box (tmpdst, team struct +$66, a word a roster player: 1-$7FFF)."""
    return [i + 1 for i in range(26) if 0 < e.w(TEAMS[t] + 0x66 + 2 * i) < 0x8000]


def run_case(rom, case, seed, out):
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 0 if case == "on" else 1)
    e.setw(PERLEN, 0)
    if not G.into_play(e):
        return {"case": case, "seed": seed, "error": "never reached play"}
    e.setw(PLAYMODE, 2 if case == "playoff" else 0)
    e.setl(SEED, (0x2545F491 * (seed + 1)) & 0xFFFFFFFF or 1)
    G.OURS.clear()
    G.OURS.append(tuple(e.b(a) for a in G.TEAMS))
    e.setw(GSP, 2)
    e.setw(SCORE[0], 0)
    e.setw(SCORE[1], 0)
    carried = None
    if case == "carry":
        e.setw(CLOCK, 40)
        for f in range(20000):
            if f % 60 == 0:
                cpu(e)
            for k in range(6):
                if 1 <= e.b(BASE + SZ * k + 0x35) <= 5:
                    e.setb(BASE + SZ * k + 0x73, AGR)
            e.run(1, hold=["START"] if f % 300 == 0 and e.b(SCREEN) != 0 else [])
            if e.w(TEAMS[0] + TMAP) == 5 and not e.b(GMODE) & 1 and e.b(SCREEN) == 0:
                carried = {"clock": e.w(CLOCK), "tmap": [e.w(b + TMAP) for b in TEAMS]}
                break
            if e.w(CLOCK) <= 3 and not e.b(GMODE) & 1:
                e.setw(CLOCK, 40)                   # keep the period going until the penalty comes
            e.setw(SCORE[0], 0)
            e.setw(SCORE[1], 0)
    e.setw(CLOCK, 2)
    # into overtime
    for f in range(40000):
        if f % 60 == 0:
            cpu(e)
        e.run(1, hold=["START"] if f % 150 == 0 and e.b(SCREEN) != 0 else [])
        if e.w(GSP) == 3 and e.b(SCREEN) == 0 and G.ours(e) and e.w(CLOCK) != 0:
            break                                   # overtime's own opening faceoff (not an intermission highlight)
    else:
        return {"case": case, "seed": seed, "error": "no overtime", "gsp": e.w(GSP)}
    segs, faceoffs, shots_seen, f, was_stopped = [], [], set(), 0, True
    pp = case in ("off", "on", "carry", "playoff")
    shoot = {"seen": False, "skaters": set()}
    while f < 15000:
        if f % 60 == 0:
            cpu(e)
        if pp and UNTIL_CROWDED and any(len(boxed_of(e, t)) >= 3 for t in (0, 1)):
            pp = False                                      # three in one box: let them come out (the return)
        if pp:
            for k in range(6, 12):
                if 1 <= e.b(BASE + SZ * k + 0x35) <= 6:
                    e.setb(BASE + SZ * k + 0x73, AGR)
        e.run(4, hold=["START"] if f % 300 == 0 and e.b(SCREEN) != 0 else [])
        f += 4
        if e.b(SCREEN) == 0 and G.ours(e) and (e.w(GSP) != 3 or e.w(CLOCK) == 0):
            break                                   # the overtime is over (highlights of other games skipped)
        if e.b(GMODE2) & 1:
            shoot["seen"] = True
            shoot["skaters"].add((len(on_ice(e, 0)), len(on_ice(e, 1))))
            continue
        if e.b(SCREEN) != 0 or not G.ours(e):
            continue
        h, a = on_ice(e, 0), on_ice(e, 1)
        tm = [e.w(b + TMAP) for b in TEAMS]
        gl = [bool(e.w(b + TMGOALIE) & 0x8000) for b in TEAMS]
        stopped = bool(e.b(GMODE) & 1)
        key = (tuple(h), tuple(a), tuple(tm), tuple(gl))
        if not segs or segs[-1]["key"] != key:
            segs.append({"key": key, "from": f, "to": f, "clock": e.w(CLOCK), "stopped": stopped})
            tag = f"{len(h)}v{len(a)}_g{int(gl[0])}{int(gl[1])}"
            if tag not in shots_seen and not stopped:
                shots_seen.add(tag)
                e.screenshot(out / f"{case}_{seed}_{tag}.png")
        else:
            segs[-1]["to"] = f
        if was_stopped and not stopped:                     # a faceoff drop
            px, py = sw(e.w(BASE + SZ * PUCK)), sw(e.w(BASE + SZ * PUCK + 0x14))
            spots = {}
            for k in range(12):
                p = e.b(BASE + SZ * k + 0x35)
                if 1 <= p <= 6:
                    spots[f"{'HA'[k // 6]}{POS[p]}"] = (sw(e.w(BASE + SZ * k)) - px, sw(e.w(BASE + SZ * k + 0x14)) - py)
            faceoffs.append({"f": f, "clock": e.w(CLOCK), "puck": (px, py), "home": h, "away": a, "tmap": tm,
                             "boxed": [len(boxed_of(e, 0)), len(boxed_of(e, 1))],
                             "spots": spots})
            if len(faceoffs) <= 4:
                e.screenshot(out / f"{case}_{seed}_faceoff{len(faceoffs)}.png")
        was_stopped = stopped
    after = []
    for _ in range(3000):                                   # what follows: a shootout?
        e.run(4, hold=["START"] if _ % 75 == 0 else [])
        if e.b(GMODE2) & 1:
            shoot["seen"] = True
            if e.b(SCREEN) == 0:
                shoot["skaters"].add((len(on_ice(e, 0)), len(on_ice(e, 1))))
    for s in segs:
        s["key"] = [list(s["key"][0]), list(s["key"][1]), list(s["key"][2]), list(s["key"][3])]
    return {"case": case, "seed": seed, "carried": carried, "frames": f, "gsp_end": e.w(GSP),
            "score": [e.w(SCORE[0]), e.w(SCORE[1])], "segments": segs, "faceoffs": faceoffs,
            "shootout": {"seen": shoot["seen"], "skaters": sorted(shoot["skaters"])}}


def main():
    rom, case, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    seeds = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    for s in range(seeds):
        r = run_case(rom, case, s, out)
        with open(out / f"{Path(rom).stem}_{case}.jsonl", "a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(json.dumps({k: r.get(k) for k in ("case", "seed", "carried", "frames", "gsp_end", "score", "error")}),
              flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
