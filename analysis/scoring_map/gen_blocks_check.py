"""NOSE4Web's blocked shots (Genesis, 2026-11-19; the option counts at puckbody's first instruction, $153CA: a byte a
roster place at $FFE890 (32 home, then 32 visitors), the teams' totals at team struct + $2236, $FFE904 / $FFEC68).

Computer games (gen_ref_cvc's set-up: 5-minute periods, penalties On Except Off-sides, line changes off, seeds by game
number). Every frame, from the game's own RAM:
- shots: sflags2's sf2shot ($C2EE bit 4) rising (doshot), the shooter from shotplayer ($BED8) and, as a check, the
  last carrier (puckc) or a one-timer's swinger;
- body hits: puckbody's signature, the puck's speed after the frame equal to 256 x (puck - skater) in x and y (its
  `move.b d0,Xvel` / `move.b d1,Yvel`: the high bytes, to within 2) with the skater within 20, and Zvel 0;
- the counts: every change of the 64 bytes and the two totals, with the screen ($FFF7, 0 = play) and the clock.
Each count is matched to a body hit on the same or the previous frame; each body hit is classed by who shot (the
other team, a teammate, no shot in flight) and whether it was counted. At the end of each game the counts are
compared with the team totals.

python gen_blocks_check.py ROM GAMES OUT.jsonl [FIRST]   |   report OUT.jsonl ..."""
import json
import math
import sys
from collections import Counter
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

OPTPEN, OPTLINE, PERLEN, SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD056, 0xD058, 0xD050, 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
BASE, SZ, PUCK, PUCKC = 0xB04A, 0x80, 14, 0xB7AA
SFLAGS2, SHOTPLAYER = 0xC2EE, 0xBED8
COUNTS, TOTALS = 0xE890, (0xE904, 0xEC68)
BODY = 9            # checkpuckcoll's .chkbody: within 8 in x and y and distance squared <= $40 (the stick reaches further)


def rec(k):
    return BASE + SZ * k


def s8(v):
    return v - 256 if v > 127 else v


def game(rom, n):
    e = Emu(rom)
    G.to_setup(e, Path(rom).parent)
    e.setw(PERLEN, 0)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    c = Counter()
    events = []
    counts0 = bytes(e.b(COUNTS + i) for i in range(64))
    start_counts = sum(counts0)
    prev_counts = counts0
    prev_tot = [e.w(t) for t in TOTALS]
    prev_shot = False
    shooter = None
    last_carrier = None
    hits = []                      # (frame, skater, team, kind, z)
    frame, still, last = 0, 0, None
    p = rec(PUCK)
    while e.w(GSP) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
            cl = e.w(CLOCK)
            still = still + 1 if cl == last else 0
            last = cl
            if frame % 3600 == 0:
                lowload.breathe()
        before = [(e.sw(rec(k)), e.sw(rec(k) + 0x14)) for k in range(12)]
        pb = (e.sw(p), e.sw(p + 0x14))
        pc_before = e.w(PUCKC)
        if pc_before < 12:
            last_carrier = pc_before
        e.run(1, hold=["START"] if still >= 8 and frame % 60 < 2 else [])
        frame += 1
        screen = e.b(SCREEN)
        shot = bool(e.b(SFLAGS2) & 0x10)
        if shot and not prev_shot:
            sp = e.w(SHOTPLAYER)
            shooter = sp if sp < 12 else None
            c["shots (sf2shot rising)"] += 1
            if shooter is not None and last_carrier is not None and shooter != last_carrier:
                c["shots: shotplayer not the last carrier (one-timers)"] += 1
        vx, vy, vz = e.sw(p + 0x28), e.sw(p + 0x2A), e.sw(p + 0x2C)
        hit = None
        if e.w(PUCKC) >= 12:
            for k in range(12):
                if e.b(rec(k) + 0x35) == 0xFF:
                    continue
                ok = False
                for (ax, ay), (bx, by) in ((pb, before[k]), ((e.sw(p), e.sw(p + 0x14)), (e.sw(rec(k)), e.sw(rec(k) + 0x14)))):
                    dx, dy = ax - bx, ay - by
                    if math.hypot(dx, dy) > BODY or (dx == 0 and dy == 0):
                        continue
                    if abs(s8((vx >> 8) & 0xFF) - s8(dx & 0xFF)) <= 3 and abs(s8((vy >> 8) & 0xFF) - s8(dy & 0xFF)) <= 3:
                        ok = True
                if ok and vz == 0:
                    hit = k
                    break
        if hit is not None and screen == 0:
            goalie = e.b(rec(hit) + 0x35) == 0
            team = 1 if hit >= 6 else 0
            if not prev_shot:
                kind = "no shot in flight"
            elif shooter is None:
                kind = "shot, shooter unknown"
            elif (shooter >= 6) == (team == 1):
                kind = "teammate's shot"
            else:
                kind = "the other team's shot"
            if goalie:
                kind += " (goalie)"
            hits.append([frame, hit, team, kind, e.sw(p + 0x18), False])
        counts = bytes(e.b(COUNTS + i) for i in range(64))
        tot = [e.w(t) for t in TOTALS]
        if counts != prev_counts:
            for i in range(64):
                d = counts[i] - prev_counts[i]
                if d:
                    team, slot = divmod(i, 32)
                    match = [h for h in hits if frame - h[0] <= 1]
                    who = None
                    for h in match:
                        if h[2] == team and e.b(rec(h[1]) + 0x66) == slot:
                            h[5] = True
                            who = h
                    near = sorted((math.hypot(e.sw(rec(k)) - e.sw(p), e.sw(rec(k) + 0x14) - e.sw(p + 0x14)), k)
                                  for k in range(12) if e.b(rec(k) + 0x35) != 0xFF)
                    ev = dict(f=frame, team=team, slot=slot, d=d, screen=screen, clock=e.w(CLOCK), period=e.w(GSP),
                              matched=who[3] if who else None, z=e.sw(p + 0x18), v=[vx, vy, vz], shot=prev_shot,
                              shooter=shooter, nearest=[(round(dd, 1), k, e.b(rec(k) + 0x35), e.b(rec(k) + 0x66)) for dd, k in near[:3]],
                              puckc=e.w(PUCKC))
                    events.append(ev)
                    c["counts: " + (("matched to a body hit: " + who[3]) if who else "NO body hit matched")] += 1
                    if screen != 0:
                        c["counts outside play"] += 1
        if tot != prev_tot:
            c["total changes"] += sum(t - pt for t, pt in zip(tot, prev_tot))
        prev_counts, prev_tot, prev_shot = counts, tot, shot
    for h in hits:
        c[f"body hits: {h[3]}: {'counted' if h[5] else 'not counted'}"] += 1
        if "other team" in h[3] and "goalie" not in h[3] and not h[5]:
            events.append(dict(f=h[0], uncounted=h[3], skater=h[1], z=h[4]))
    teams = [sum(prev_counts[:32]), sum(prev_counts[32:])]
    return {"game": n, "rom": Path(rom).name, "frames": frame, "counts": dict(c), "events": events,
            "start_counts": start_counts, "players": teams, "totals": prev_tot,
            "goals": [e.w(0xC6CE + 0xC), e.w(0xCA32 + 0xC)]}


def report(paths):
    for path in paths:
        R = [json.loads(line) for line in open(path) if line.strip()]
        R = [r for r in R if not r.get("error")]
        tot = Counter()
        bad = 0
        for r in R:
            tot.update(r["counts"])
            bad += r["players"] != r["totals"] or r["start_counts"] != 0
        print(f"== {path}: {len(R)} games; players' counts against the team totals or not zero at the start: {bad} off")
        for k in sorted(tot):
            print(f"  {k:72s} {tot[k]:6d}   {tot[k] / max(len(R), 1):6.2f} a game")


def main():
    if sys.argv[1] == "report":
        report(sys.argv[2:])
        return
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    lowload.gentle()
    for n in range(first, first + games):
        r = game(rom, n)
        with open(out, "a") as fo:
            fo.write(json.dumps(r) + "\n")
        print(n, r.get("counts"), flush=True)


if __name__ == "__main__":
    main()
