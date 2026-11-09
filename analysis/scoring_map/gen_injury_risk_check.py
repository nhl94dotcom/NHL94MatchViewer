"""NOSE4Web's Genesis injury risk option, played (2026-11-09, f3d8449): a count a player of the knockdowns he took
($FFF000, 32 a team, the away team +32, by pnum), cleared at StartGame, halved at PeriodOver, and min(count x bonus,
cap) added to the impact in FallDown's injury roll (randomd0(160) <= impact).

- counts: NOSE4Web's changes laid over a copy of the scoring-map test ROM (as gen_hit_energy_check.py) and played in
  the harness: the away carrier hit by the pad skater's C (body check), B (poke) or A (hook / hold), OptLine On and
  Off: his count before and after (expected +1 a knockdown, nothing for a hold or no knockdown).
- injuries: the same with the strong build (+10 a knockdown, cap 60) against the unchanged test ROM: the carrier
  facing the pad skater (straight down the ice: facing 4, the case the game can injure) or on a diagonal (facing 3,
  which it never can), his count set to 0 or 6 before the hit; a C check from in front; injuries counted (SPAinjuryfall
  $145C or SPAinjury1 $1AF4 on him); the checker made heavy (working Weight +$67 and Checking +$75 30) and the carrier light (Weight 0),
  so that more hits knock him down; the puck kept on him until he goes down (the roll is for the carrier).
- each game / each period, the build itself from power-on (gen_ot_check.to_setup / into_play): junk written to
  $FFF000-$FFF03F at Game Setup, then START into a game: the bytes at the first frame of play; then counts set (7 and
  10 for a home and an away player), the clock set to 1 s and play run into the next period: the counts there.

python gen_injury_risk_check.py OUT RETAIL_ROM BUILD_ROM STRONG_ROM"""
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import gen_hit_energy_check as HE
import gen_ot_check as G
import harness as H
import lowload
from emu import Emu
from paths import ROM

COUNTS = 0xFFF000
INJURYFALL = 0x145C
INJURED = {0x145C, 0x1AF4}       # SPAinjuryfall, and SPAinjury1, which replaces it in the same frame for a period injury


def count_addr(e, k):
    return COUNTS + (32 if k >= 6 else 0) + e.b(H.rec(k) + 0x66)


def counts_part(rom):
    h = H.Harness(rom=rom)
    e = h.e
    res = Counter()
    for optline in (0, 1):
        for button in ("C", "B", "A"):
            for dy in (30, 50, 70):
                for at in (5, 15):
                    for sd in range(3):
                        before = {}

                        def setup(e, store=before):
                            if "c" not in store:
                                store["c"] = e.b(count_addr(e, 6))
                        r = HE.trial(h, button, dy, at, 0x3000 + 131 * sd + dy + at, optline, setup=setup)
                        e2 = e.b(count_addr(e, 6))
                        event = "down" if r["down"] else "flail" if r["flail"] else "nothing"
                        res[(optline, button, event, e2 - before["c"])] += 1
            lowload.breathe()
    return {f"{k}": v for k, v in res.items()}


def injury_part(rom):
    h = H.Harness(rom=rom)
    e = h.e
    res = Counter()
    for facing in (4, 3):
        for preset in (0, 6):
            for dy in (40, 60, 80):
                for at in (5, 15, 25, 35):
                    for sd in range(10):
                        def setup(e, facing=facing, preset=preset):
                            e.setb(H.rec(6) + 0x55, facing)
                            e.setb(count_addr(e, 6), preset)
                            e.setb(H.rec(2) + 0x67, 30)        # a heavy checker with top Checking
                            e.setb(H.rec(2) + 0x75, 30)
                            e.setb(H.rec(6) + 0x67, 0)         # against a light carrier
                            if e.w(H.rec(6) + 0x58) not in {0x0DD8, 0x0D26} | INJURED:
                                e.setw(H.PUCKC, 6)             # who keeps the puck until he goes down
                        seen = {"inj": False}
                        r = trial_watch(h, dy, at, 0x9000 + 37 * sd + dy + at, setup, seen)
                        res[(facing, preset, "down" if r["down"] else "-", seen["inj"])] += 1
            lowload.breathe()
    return {f"{k}": v for k, v in res.items()}


def trial_watch(h, dy, at, seed, setup, seen):
    """HE.trial with C, keeping the setup's facing for the whole trial and noting an injury fall."""
    e = h.e
    orig_run = e.run

    def run(n=1, **kw):
        orig_run(n, **kw)
        if e.w(H.rec(6) + 0x58) in INJURED:
            seen["inj"] = True
    e.run = run
    try:
        return HE.trial(h, "C", dy, at, seed, 0, setup=setup)
    finally:
        e.run = orig_run


def game_part(rom, out):
    e = Emu(rom)
    G.to_setup(e, out)
    for a in range(COUNTS, COUNTS + 64):
        e.setb(a, 0x5A)
    if not G.into_play(e):
        return {"error": "never reached play"}
    first = [e.b(a) for a in range(COUNTS, COUNTS + 64)]
    G.OURS.append(tuple(e.b(a) for a in G.TEAMS))
    e.setb(COUNTS + 3, 7)
    e.setb(COUNTS + 32 + 5, 10)
    e.setb(COUNTS + 9, 255)
    p0 = e.w(G.GSP)
    e.setw(G.CLOCK, 1)
    still, last = 0, None
    for f in range(30000):
        e.run(1, hold=["START"] if still >= 300 and f % 150 == 0 else [])
        c = e.w(G.CLOCK)
        still = still + 1 if c == last else 0
        last = c
        if e.w(G.GSP) == p0 + 1 and e.b(G.SCREEN) == 0 and G.ours(e) and still == 0 and f > 600:
            break
    return {"at the first frame of play (junk 0x5A written at setup)": sorted(set(first)),
            "period": [p0, e.w(G.GSP)],
            "after the intermission (set 7, 10, 255)": [e.b(COUNTS + 3), e.b(COUNTS + 32 + 5), e.b(COUNTS + 9)]}


def main():
    if sys.argv[1] == "--one":
        part, rom, out = sys.argv[2], sys.argv[3], Path(sys.argv[4])
        r = {"counts": counts_part, "injuries": injury_part}.get(part)
        res = r(rom) if r else game_part(rom, out)
        (out / f"{part}_{Path(rom).stem}.json").write_text(json.dumps(res, indent=1))
        print(part, Path(rom).name, json.dumps(res, indent=1), flush=True)
        return
    out, retail, build, strong = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    only = os.environ.get("ONLY")
    for nose, tag in ((build, "build"), (strong, "strong")):
        sub = out / tag
        sub.mkdir(exist_ok=True)
        test, n = HE.patched(sub, nose, retail)
        print(tag, "bytes laid over the test ROM:", n, flush=True)
        jobs.append(("counts", test, sub) if tag == "build" else ("injuries", test, sub))
    jobs.append(("injuries", ROM, out))
    jobs.append(("game", build, out))
    for part, rom, where in jobs:
        if only and part != only:
            continue
        subprocess.run([sys.executable, __file__, "--one", part, rom, str(where)], check=True)


if __name__ == "__main__":
    main()
