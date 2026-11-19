"""NHL '95's checkpuckcoll fixes in computer games (2026-11-19; NOSE4Web: the stick test loads ChkStickSqP's address at
$7B6A2, so the stick circle always passes (a box) and the nopuck half reach never applies; the body test's y compare
at $7B6F6 is a move, so puckbody is never reached; NHL_95_stick_reach c74fbee4, NHL_95_body_block 5c9183b0,
NHL_95_stick_body 7330ac2a, made by hand here with the same CRCs).

Each ROM plays the same GAMES computer games from the live state (gen95_stats_check's set-up: nobody on a pad,
penalties on, each period's clock set to SECS; the seed $CC6A from the game's number). Every frame:
- pickups: the puck going from loose to a skater: his team's own (a pass taken or a regather; the last carrier his
  team), the other team's (a loose puck won), or a goalie's;
- steals: the carrier changing to the other team with the puck loose under 10 frames;
- goalie touches: the goalie taking it, or a loose puck's speed changing by over 3,000 within 30 of him;
- body blocks: a loose puck moving faster than 12,000 whose speed changes by over 3,000 within 20 of a skater who
  doesn't take it in the next 6 frames;
- stuck: a loose puck still (speed under 200) for 300 frames with the clock running, or one carrier for 1,200
  frames (20 s real) in a row;
- shots on goal (the team struct's +0) and goals at the end.

python gen95_checkpuck_check.py ROM GAMES OUT.jsonl [SECS]   |   report OUT.jsonl [OUT2 ...]"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

import gen95_organ_resume_check as O
import lowload

HOME, TMSIZE = 0xC288, 0x366
GSP, CLOCK, GMODE, GMODE2, OPTPEN, PUCKC, SEED = 0xC020, 0xC022, 0xBEF0, 0xBF00, 0xCC5A, 0xB3C2, 0xCC6A
BASE, SZ, PUCK = 0xAC62, 0x80, 14
SHOTS = 0xEA
STATE = Path.home() / "NHL94_scoring_map" / "runs" / "nhl95" / "assists" / "live_retail.state"


def rec(k):
    return BASE + k * SZ


def game(rom, n, secs):
    r = O.R(rom, str(STATE))
    e = r.e
    e.unserialize(r.base)
    e.setw(0xBF4C, 0)
    e.setw(0xBF4E, 0)
    for k in range(12):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setw(OPTPEN, 1)
    e.setw(CLOCK, min(e.w(CLOCK), secs))
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    c = Counter()
    last_gsp, still = e.w(GSP), 0
    prev_c, last_carrier, loose_for = None, None, 0
    prev_v = (0, 0)
    pending = []                     # (frame, skater) body-block candidates
    still_puck = same_carrier = 0
    p = rec(PUCK)
    for f in range(60 * 60 * 40):
        clk = e.w(CLOCK)
        e.run(1, hold=["START"] if still > 900 and f % 240 == 0 else [])
        running = e.w(CLOCK) != clk
        still = still + 1 if not running else 0
        if e.w(CLOCK) > secs:                     # each period's clock capped (it refills at the faceoff)
            e.setw(CLOCK, secs)
        if e.w(GMODE2) & 0x0800 or e.w(GSP) >= 3:
            break
        pc = e.w(PUCKC)
        carrier = pc if pc < 12 else None
        px, py = e.sw(p), e.sw(p + 0x14)
        vx, vy = e.sw(p + 0x28), e.sw(p + 0x2A)
        speed = math.hypot(vx, vy)
        if still > 60:                            # the clock stopped (it ticks every game second, about 24 frames)
            prev_c, pending, prev_v = carrier, [], (vx, vy)
            continue
        if carrier is not None:
            if prev_c is None and last_carrier is not None:
                if e.b(rec(carrier) + 0x35) == 0:
                    c["pickups: goalie"] += 1
                elif (carrier < 6) == (last_carrier < 6):
                    c["pickups: own team"] += 1
                else:
                    c["pickups: other team"] += 1
                    if loose_for < 10:
                        c["steals (loose under 10 frames)"] += 1
            if prev_c is not None and prev_c != carrier and (carrier < 6) != (prev_c < 6):
                c["steals (direct)"] += 1
            same_carrier = same_carrier + 1 if carrier == prev_c else 0
            if same_carrier == 1200:
                c["stuck: one carrier 20 s"] += 1
            last_carrier, loose_for, still_puck = carrier, 0, 0
        else:
            loose_for += 1
            dv = math.hypot(vx - prev_v[0], vy - prev_v[1])
            if dv > 3000:
                near = []
                for k in range(12):
                    if e.b(rec(k) + 0x35) == 0xFF:
                        continue
                    d = math.hypot(e.sw(rec(k)) - px, e.sw(rec(k) + 0x14) - py)
                    near.append((d, k))
                near.sort()
                if near:
                    d, k = near[0]
                    if e.b(rec(k) + 0x35) == 0 and d < 30:
                        c["goalie touches (deflected)"] += 1
                    elif d < 20 and math.hypot(*prev_v) > 12000:
                        pending.append((f, k))
            still_puck = still_puck + 1 if speed < 200 and running else 0
            if still_puck == 300:
                c["stuck: loose and still 5 s"] += 1
        for fr, k in list(pending):
            if f - fr >= 6:
                pending.remove((fr, k))
                if carrier != k:
                    c["body blocks"] += 1
        if carrier is not None and prev_c is None and e.b(rec(carrier) + 0x35) == 0:
            c["goalie touches (held)"] += 1
        prev_c, prev_v = carrier, (vx, vy)
        if f % 6000 == 5999:
            lowload.breathe()
    score = [e.w(HOME + tm * TMSIZE + 0xC) for tm in (0, 1)]
    shots = [e.w(HOME + tm * TMSIZE) for tm in (0, 1)]          # the team's shots on goal (+0, as NHL '94's)
    return dict(game=n, rom=Path(rom).name, frames=f, counts=dict(c), goals=sum(score), shots=sum(shots))


def report(paths):
    for path in paths:
        R = [json.loads(line) for line in open(path)]
        tot = Counter()
        for r in R:
            tot.update(r["counts"])
            tot["goals"] += r["goals"]
            tot["shots on goal"] += r["shots"]
        print(f"== {path}: {len(R)} games")
        for k in sorted(tot):
            print(f"  {k:36s} {tot[k]:6d}   {tot[k] / max(len(R), 1):7.1f} a game")


def main():
    if sys.argv[1] == "report":
        report(sys.argv[2:])
        return
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    secs = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    lowload.gentle()
    for n in range(games):
        r = game(rom, n, secs)
        with open(out, "a") as fo:
            fo.write(json.dumps(r) + "\n")
        print(n, r["counts"], r["goals"], r["shots"], flush=True)
    report([out])


if __name__ == "__main__":
    main()
