"""The SNES second period in full play (2026-11-07, the user approved). In the leagues' games both teams score about 5%
fewer goals a shot in period 2 (SNES_MECHANICS 16). Standing shots with only the period number changed came out the
same shot for shot (snes_period_hand_run.py), which leaves the play a standing shot doesn't reach (rushes, passes,
one-timers, rebounds, the computer's own decisions) and the people. Here the computer plays itself, both teams, from
the harness's real states, and the game's own counts (tmshots $177A, tmscore $178E) give goals per shot:

  p1        snes_top.state as it is (period 1; home attacks the top net)
  p3        the same with gsp $1630 = 2 (period 3; the same ends as period 1)
  p2        snes_bottom.state as it is (period 2; home attacks the bottom net)
  p2_as_p1  the same with gsp = 0 (only the period number changed)

p1 / p3 and p2 / p2_as_p1 share their segments' seeds, so they can be compared segment by segment: if play never reads
the period number, each pair comes out identical. p1 against p2 is the question: if the game itself has the dip, it
shows there; if not, the dip comes from the people.

Computer against computer: every pad off the teams (cont1team $1C84 0, padside $19F6 $FFFE, as StartGame sets an
empty pad), teampads $19D0 0, playerpad $19D4 and c1playernum $19EC cleared, the person flag (pflags $1283 bit $0008)
off; FaceoffPads gives no pad back (checked: no person-flagged object in 3 minutes of play). Each segment: a fresh
random seed, SEG frames of play (the clock runs from 598 to about 250, never to the period's end). Gentle mode, one
process, resumable.

python snes_period_cvc.py RUN [minutes]   -> paths.RUNS / RUN / segments.jsonl
python snes_period_cvc.py RUN report"""
import json
import math
import random
import sys
import time
from collections import defaultdict

import snes_harness as H
from lowload import breathe, gentle
from paths import RUNS, SNES_STATE_TOP, SNES_STATE_BOTTOM

CONT1TEAM, PADSIDE, PLAYERPAD, C1PLAYER, TEAMPADS, PFLAGS = 0x1C84, 0x19F6, 0x19D4, 0x19EC, 0x19D0, 0x1283
TMSHOTS, TMSCORE, GSP = 0x177A, 0x178E, 0x1630
SEG = 9000                                     # 2.5 minutes of real time, 6.25 game minutes
CONDS = {"p1": ("top", None), "p3": ("top", 2), "p2": ("bottom", None), "p2_as_p1": ("bottom", 0)}


def computer_only(e):
    for i in range(5):
        e.setw(CONT1TEAM + 2 * i, 0)
        e.setw(PADSIDE + 2 * i, 0xFFFE)
        e.setw(C1PLAYER + 2 * i, 0xFFFF)
    e.setw(TEAMPADS, 0)
    e.setw(TEAMPADS + 2, 0)
    for k in range(12):
        e.setw(PLAYERPAD + 2 * k, 0xFFFF)
        e.setw(PFLAGS + 2 * k, e.w(PFLAGS + 2 * k) & ~8)


def segment(e, base, gsp, seed):
    e.unserialize(base)
    if gsp is not None:
        e.setw(GSP, gsp)
    computer_only(e)
    e.setw(H.SEED, seed >> 16 or 1)
    e.setw(H.SEED + 2, seed & 0xFFFF or 1)
    s0 = [e.w(TMSHOTS), e.w(TMSHOTS + 2)]
    g0 = [e.w(TMSCORE), e.w(TMSCORE + 2)]
    person = 0
    for f in range(SEG):
        e.run(1)
        if f % 30 == 0 and any(e.w(PFLAGS + 2 * k) & 8 for k in range(12)):
            person += 1
        if f % 600 == 599:
            breathe()
    return dict(shots=[e.w(TMSHOTS) - s0[0], e.w(TMSHOTS + 2) - s0[1]],
                goals=[e.w(TMSCORE) - g0[0], e.w(TMSCORE + 2) - g0[1]], clock=e.w(H.CLOCK), person=person)


def main():
    run = sys.argv[1]
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    path = out / "segments.jsonl"
    if len(sys.argv) > 2 and sys.argv[2] == "report":
        return report(path)
    minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    gentle()
    done = defaultdict(set)
    if path.exists():
        for r in map(json.loads, open(path)):
            done[r["cond"]].add(r["i"])
    h = H.Harness(SNES_STATE_TOP)
    e = h.e
    bases = {"top": h.base, "bottom": open(SNES_STATE_BOTTOM, "rb").read()}
    t0 = time.time()
    with open(path, "a") as fh:
        i = 0
        while time.time() - t0 < minutes * 60:
            seed = random.Random(i).getrandbits(32)
            for c, (st, gsp) in CONDS.items():
                if i in done[c]:
                    continue
                r = segment(e, bases[st], gsp, seed)
                r.update(cond=c, i=i)
                fh.write(json.dumps(r) + "\n")
                fh.flush()
            i += 1
            if i % 10 == 0:
                print(i, "segments each", flush=True)
    print("time up", flush=True)


def report(path):
    rows = [json.loads(l) for l in open(path)]
    by = defaultdict(dict)
    for r in rows:
        by[r["cond"]][r["i"]] = r
    print("segments:", {c: len(v) for c, v in by.items()}, "with a person-flagged object:",
          sum(r["person"] > 0 for r in rows))
    print(f"{'':10}{'shots':>8}{'goals':>7}{'g/shot':>8}{'+-':>6}   home (g/shot)   away (g/shot)")
    for c in CONDS:
        v = list(by[c].values())
        s = [sum(r["shots"][t] for r in v) for t in (0, 1)]
        g = [sum(r["goals"][t] for r in v) for t in (0, 1)]
        S, G = sum(s), sum(g)
        p = G / S if S else 0
        se = math.sqrt(p * (1 - p) / S) if S else 0
        print(f"{c:10}{S:8}{G:7}{p:8.3f}{se:6.3f}   " +
              "   ".join(f"{g[t]:4}/{s[t]:5} ({g[t] / max(1, s[t]):.3f})" for t in (0, 1)))
    for a, b in (("p1", "p3"), ("p2", "p2_as_p1")):
        same = [i for i in by[a] if i in by[b]]
        diff = sum(by[a][i]["shots"] != by[b][i]["shots"] or by[a][i]["goals"] != by[b][i]["goals"] for i in same)
        print(f"{a} v {b}: {diff} of {len(same)} paired segments came out differently")


if __name__ == "__main__":
    main()
