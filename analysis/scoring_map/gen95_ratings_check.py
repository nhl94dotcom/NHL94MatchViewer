"""NHL '95 (Genesis): NOSE4Web's Ratings options ported from NHL '94 (2026-11-18, mv_review_2026-11-18/ratings95):
clutch time, the hot / cold range and the base weight, played against the originals.

NHL '95 (the NHL95Genesis disassembly): setplayer (players95.asm) gives each rating attribute 3-$F (TempWord2 $BB12)
to AttributeCalc: the roster nibble x 5 plus the player's first hot / cold value (team struct +$1A4 + 16 x pnum,
signed) / 3, held to 0-$1E; then the bonuses, and BoostAttribute (d3 += ($1E - d3) / 4) on Spd, ShP, Chk, Stk and Pas.
Record offsets (equals.inc): legstr $68 (Agl), legspd $69, aioff $6A, aidef $6B, shotspd $6C, shotacc $6D, passacc $6E,
spodds $70, stickhand $71, endurance $72, aggress $73, fighting $74, checking $75, pnum $66; pfteam = bit 6 of $62.
Create_HotCold_Table fills 416 values a team with randomd0s of the word at $83E92 (9 on retail: -9 to 8). The VBlank
tick ($7A392, video95.asm) takes a second off gameclock ($C022) and plays SFXbeep2 as it reaches 60.

  diff ORIG BUILD               the bytes that differ, in runs.
  clutch ORIG BUILD STATE       from the live state (the original's), for each case (period gsp $C020, clock, home /
        away score words $C294 / $C5FA): (1) the tick: the clock set to 121 and played to 119; the 12 records' rating
        bytes, build minus original, at the frame the clock reads 120; (2) rebuilds: the clock set below 2:00 (or above,
        for "before 2:00"), line changes on (OptLine $CC5C 0), every on-ice energy drained, the computer playing 2,400
        frames: every setplayer seen (a record's pnum or ratings changed), build against original, the same player's
        first new rating set after the case was set.
  goals ORIG BUILD STATE        rebuilds at the faceoff after a goal (put_goal), the score after it deciding: P3 at 1:50
        2-2 home scores (3-2), 3-2 away scores (3-3), 3-2 home scores (4-2), 4-2 home scores (5-2); P2; P3 at 4:40. The
        12 records' ratings when play runs again, build minus original.
  clock ORIG BUILD STATE        P3, tied, the clock from 125 to 55: the clock each frame, and each new sound-driver
        sequence (slot ids, gen95_organ_resume_check's PTR / SID) with its frame, on both ROMs: the 1:00 beep's frame.
  play ORIG BUILD STATE         P1 (the clutch idle): computer play on both, every record's X / Y and weight byte each
        frame, the team stat blocks at the end: the same play means the collisions (their own 140) are as before.
  steps ROM ... STATE           the logic steps over 2,400 frames from the state (OldVcount changes) and frames a step.
  hotcold ROM                   from power-on to a Regular Game (as gen95_assist_check's mkstate) at three different
        title waits: each team's hot / cold table (+$1A4, 416 signed bytes), its values' spread, and for the 12 on the
        ice whether Agility (legstr) and Endurance (no bonuses) are 5 x n + the first value / 3 (divs, toward zero).
  weight ROM OUT                Team Roster (attribute page) and Create Player screenshots, and the words at $8566C,
        $99450 and the collisions' own 140 at $7ACE4.

python gen95_ratings_check.py diff ORIG BUILD | clutch | goals | clock ORIG BUILD STATE | hotcold ROM |
       weight ROM OUT"""
import json
import struct
import sys
from collections import Counter
from pathlib import Path

import lowload

GSP, CLOCK, CLOCKF, HMSCORE, AWSCORE, OPTLINE, OPTPEN = 0xC020, 0xC022, 0xC024, 0xC294, 0xC5FA, 0xCC5C, 0xCC5A
HOME, TMSIZE, BASE, SZ = 0xC288, 0x366, 0xAC62, 0x80
OLDVCOUNT = 0xAC58               # ram95.asm
NAMES = {0x68: "Agl", 0x69: "Spd", 0x6A: "OfA", 0x6B: "DfA", 0x6C: "ShP", 0x6D: "ShA", 0x6E: "Pas", 0x70: "PSO",
         0x71: "Stk", 0x72: "End", 0x73: "Agr", 0x74: "Fgt", 0x75: "Chk"}
CASES = {   # name: (gsp, clock for the rebuilds, home score, away score)
    "P3 tied": (2, 110, 2, 2), "P3 within one": (2, 110, 3, 2), "P3 two-goal lead": (2, 110, 4, 2),
    "OT tied": (3, 110, 2, 2), "P2 tied": (1, 110, 2, 2), "P3 before 2:00, tied": (2, 280, 2, 2)}


def rec(k):
    return BASE + k * SZ


def ratings(e, k):
    return {o: e.b(rec(k) + o) for o in NAMES}


def diff(a, b):
    A, B = Path(a).read_bytes(), Path(b).read_bytes()
    runs, i = [], 0
    n = min(len(A), len(B))
    while i < n:
        if A[i] != B[i]:
            j = i
            while j < n and (A[j] != B[j] or (j + 8 < n and A[j:j + 8] != B[j:j + 8])):
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1
    return dict(sizes=(len(A), len(B)), runs=[(hex(s), ln, A[s:s + min(ln, 12)].hex(), B[s:s + min(ln, 12)].hex()) for s, ln in runs[:40]],
                count=len(runs))


def setcase(e, gsp, clock, hs, aw):
    e.setw(GSP, gsp)
    e.setw(CLOCK, clock)
    e.setw(CLOCKF, 0)
    e.setw(HMSCORE, hs)
    e.setw(AWSCORE, aw)


def tick(rom, state, case):
    import gen95_organ_resume_check as O
    import gen95_shootout_check as SC
    gsp, _, hs, aw = CASES[case]
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    setcase(e, gsp, 121, hs, aw)
    SC.computer(e)
    for f in range(400):
        e.run(1)
        if f % 60 == 0:
            SC.computer(e)
        if e.w(CLOCK) == 120:
            return dict(frame=f, recs=[(k, e.b(rec(k) + 0x66), ratings(e, k)) for k in range(12)])
    return None


def rebuilds(rom, state, case, frames=2400):
    import gen95_organ_resume_check as O
    import gen95_shootout_check as SC
    gsp, clock, hs, aw = CASES[case]
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    setcase(e, gsp, clock, hs, aw)
    e.setw(OPTLINE, 0)
    for t in (0, 1):                                  # every roster player's energy low: line changes come at once
        for i in range(26):
            e.setw(HOME + t * TMSIZE + 0x34 + 2 * i, 300)
    SC.computer(e)
    prev = {k: (e.b(rec(k) + 0x66), ratings(e, k)) for k in range(12)}
    seen = []
    for f in range(frames):
        e.run(1)
        if f % 60 == 0:
            SC.computer(e)
        for k in range(12):
            now = (e.b(rec(k) + 0x66), ratings(e, k))
            if now != prev[k]:
                seen.append(dict(f=f, k=k, team=(e.b(rec(k) + 0x62) >> 6) & 1, pnum=now[0], clock=e.w(CLOCK), r=now[1]))
                prev[k] = now
        if f % 1200 == 1199:
            lowload.breathe()
    return seen


def clutch(orig, build, state):
    out = {}
    for case in CASES:
        res = {}
        if case != "P3 before 2:00, tied":
            a, b = tick(orig, state, case), tick(build, state, case)
            if a and b:
                d = Counter()
                for (k, pa, ra), (_, pb, rb) in zip(a["recs"], b["recs"]):
                    if pa == pb:
                        for o in NAMES:
                            d[(NAMES[o], rb[o] - ra[o])] += 1
                res["tick (12 records x rating: build - original)"] = sorted((n, v, c) for (n, v), c in d.items() if v)
                res["tick frames"] = (a["frame"], b["frame"])
                capped = sum(1 for k, _, rb in b["recs"] for o in (0x68, 0x69, 0x6C, 0x6D, 0x6E, 0x70, 0x71, 0x72, 0x75) if rb[o] == 30)
                res["build ratings at 30 after the tick"] = capped
        A, B = rebuilds(orig, state, case), rebuilds(build, state, case)
        # each build rating set against the original's set of the same player (team, pnum) nearest to it (once play
        # has drifted, the same player can come on at another moment, e.g. on a power play, with other bonuses)
        by = lambda S: {key: [s["r"] for s in S if (s["team"], s["pnum"]) == key] for key in {(s["team"], s["pnum"]) for s in S}}   # noqa: E731
        ga, gb = by(A), by(B)
        d, n = Counter(), 0
        for key in set(ga) & set(gb):
            for rb in gb[key]:
                ra = min(ga[key], key=lambda r: sum(abs(r[o] - rb[o]) for o in NAMES))
                n += 1
                for o in NAMES:
                    d[(NAMES[o], rb[o] - ra[o])] += 1
        res["rebuilds"] = dict(sets_compared=n, sets_orig=len(A), sets_build=len(B),
                               changes=sorted((nm, v, c) for (nm, v), c in d.items() if v),
                               clock_at_end=(A[-1]["clock"] if A else None, B[-1]["clock"] if B else None))
        out[case] = res
        print(case, json.dumps(res), flush=True)
    return out


GOAL_CASES = {   # name: (gsp, clock, home, away, the scorer is home): the score after the goal decides
    "P3 2-2, home scores (3-2)": (2, 110, 2, 2, True), "P3 3-2, away scores (3-3)": (2, 110, 3, 2, False),
    "P3 3-2, home scores (4-2)": (2, 110, 3, 2, True), "P3 4-2, home scores (5-2)": (2, 110, 4, 2, True),
    "P2 2-2, home scores": (1, 110, 2, 2, True), "P3 4:40 2-2, home scores": (2, 280, 2, 2, True)}


def goal_rebuild(rom, state, case):
    """A goal (gen95_shootout_check.put_goal, which plays on until the faceoff after it): the 12 records' ratings when
    play runs again."""
    import gen95_organ_resume_check as O
    import gen95_shootout_check as SC
    gsp, clock, hs, aw, home = GOAL_CASES[case]
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    setcase(e, gsp, clock, hs, aw)
    SC.computer(e)
    if not SC.put_goal(e, home):
        return None
    return dict(score=(e.w(HMSCORE), e.w(AWSCORE)), clock=e.w(CLOCK), recs=[(k, e.b(rec(k) + 0x66), ratings(e, k)) for k in range(12)])


def goals(orig, build, state):
    out = {}
    for case in GOAL_CASES:
        a, b = goal_rebuild(orig, state, case), goal_rebuild(build, state, case)
        if not a or not b:
            out[case] = "no goal"
            continue
        d = Counter()
        for (k, pa, ra), (_, pb, rb) in zip(a["recs"], b["recs"]):
            if pa == pb:
                for o in NAMES:
                    d[(NAMES[o], rb[o] - ra[o])] += 1
        out[case] = dict(score=(a["score"], b["score"]), clock=(a["clock"], b["clock"]),
                         changes=sorted((n, v, c) for (n, v), c in d.items() if v))
        print(case, json.dumps(out[case]), flush=True)
        lowload.breathe()
    return out


def clock_run(rom, state):
    import gen95_organ_resume_check as O
    import gen95_shootout_check as SC
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    setcase(e, 2, 125, 2, 2)
    SC.computer(e)
    clocks, seqs, prev_ids = [], [], set()
    for f in range(9000):
        e.run(1, hold=["START"] if f % 300 == 299 and e.w(CLOCK) == (clocks[-300] if len(clocks) >= 300 else -1) else [])
        if f % 60 == 0:
            SC.computer(e)
        clocks.append(e.w(CLOCK))
        ids = {(j, e.w(O.SID + 2 * j)) for j in range(8) if O.l(e, O.PTR + 4 * j) != 0xFFFFFFFF}
        for x in ids - prev_ids:
            seqs.append((f, e.w(CLOCK), x[1]))
        prev_ids = ids
        if e.w(CLOCK) < 55:
            break
    return clocks, seqs


def clock(orig, build, state):
    ca, sa = clock_run(orig, state)
    cb, sb = clock_run(build, state)
    at = lambda c, v: next((i for i, x in enumerate(c) if x == v), None)          # noqa: E731
    near60 = lambda s, c: [x for x in s if abs(x[0] - (at(c, 60) or -999)) <= 3]   # noqa: E731
    def steps(c):                     # frames each clock value lasted while the clock ran on (stoppages left out)
        out, i = Counter(), 1
        while i < len(c):
            j = i
            while j < len(c) and c[j] == c[i]:
                j += 1
            if j < len(c) and c[j] == c[i] - 1 and i > 0 and c[i - 1] == c[i] + 1:
                out[j - i] += 1
            i = j
        return sorted(out.items())
    return dict(frames_to=dict((v, (at(ca, v), at(cb, v))) for v in (124, 120, 119, 100, 61, 60, 59)),
                frames_a_second=(steps(ca), steps(cb)),
                same_clock_each_frame=ca[:len(cb)] == cb[:len(ca)],
                sequences_started_at_1_00=(near60(sa, ca), near60(sb, cb)))


def to_game(rom, title_wait):
    from emu import Emu
    e = Emu(rom)
    e.run(1500 + title_wait)
    press = lambda b, w: (e.run(6, hold=[b]), e.run(w))                         # noqa: E731
    for _ in range(3):
        press("START", 200)
    press("START", 300); press("START", 60); e.run(1800); press("START", 400); press("START", 10)
    for i in range(1200):
        e.run(1)
        if e.w(0xB3C2) < 12 and i > 200:
            break
    return e


def hotcold(rom):
    out = []
    for wait in (0, 137, 611):
        e = to_game(rom, wait)
        tables = []
        for t in (0, 1):
            raw = bytes(e.b(HOME + t * TMSIZE + 0x1A4 + i) for i in range(416))
            tables.append([x - 256 if x > 127 else x for x in raw])
        vals = tables[0] + tables[1]
        ok, bad = 0, []
        for k in range(12):
            team = (e.b(rec(k) + 0x62) >> 6) & 1
            pn = e.b(rec(k) + 0x66)
            if pn >= 26:
                continue
            hc = tables[team][pn * 16]
            off = int(hc / 3)
            for o in (0x68, 0x72):
                v = e.b(rec(k) + o)
                if 0 < v < 30:
                    if (v - off) % 5 == 0:
                        ok += 1
                    else:
                        bad.append((k, NAMES[o], v, hc))
        out.append(dict(title_wait=wait, min=min(vals), max=max(vals), spread=sorted(Counter(vals).items()),
                        first_values=[tables[t][p * 16] for t in (0, 1) for p in range(26)][:12],
                        agl_end_as_5n_plus_hc3=ok, off_rule=bad))
        print(json.dumps(out[-1]), flush=True)
        lowload.breathe()
    return out


def weight(rom, out):
    b = Path(rom).read_bytes()
    words = {hex(a): b[a:a + 2].hex() for a in (0x8566A, 0x8566C, 0x9944E, 0x99450, 0x7ACE2, 0x7ACE4)}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    return dict(words=words, note="screens: see menu_shots runs")


def main():
    lowload.gentle()
    mode = sys.argv[1]
    if mode == "diff":
        print(json.dumps(diff(sys.argv[2], sys.argv[3]), indent=1))
    elif mode == "clutch":
        clutch(sys.argv[2], sys.argv[3], sys.argv[4])
    elif mode == "goals":
        goals(sys.argv[2], sys.argv[3], sys.argv[4])
    elif mode == "play":
        print(json.dumps(same_play(sys.argv[2], sys.argv[3], sys.argv[4])))
    elif mode == "steps":
        print(json.dumps([steps(r, sys.argv[-1]) for r in sys.argv[2:-1]]))
    elif mode == "clock":
        print(json.dumps(clock(sys.argv[2], sys.argv[3], sys.argv[4])))
    elif mode == "hotcold":
        hotcold(sys.argv[2])
    elif mode == "weight":
        print(json.dumps(weight(sys.argv[2], sys.argv[3])))



def same_play(orig, build, state, frames=2400):
    """P1 from the live state (the clutch idle, the hot / cold table already made): computer play on both ROMs, every
    record's X / Y and weight byte ($67) compared each frame, and the team stat blocks at the end."""
    import gen95_organ_resume_check as O
    import gen95_shootout_check as SC
    runs = []
    for rom in (orig, build):
        r = O.R(rom, state)
        e = r.e
        e.unserialize(r.base)
        SC.computer(e)
        tr = []
        for f in range(frames):
            e.run(1)
            if f % 60 == 0:
                SC.computer(e)
            tr.append(tuple((e.w(rec(k)), e.w(rec(k) + 0x14), e.b(rec(k) + 0x67)) for k in range(15)))
        runs.append((tr, [e.w(HOME + t * TMSIZE + o) for t in (0, 1) for o in range(0, 0x60, 2)]))
    (ta, sa), (tb, sb) = runs
    first = next((i for i in range(frames) if ta[i] != tb[i]), None)
    return dict(frames=frames, first_different_frame=first, team_stats_same=sa == sb,
                weights=sorted({w for fr in ta for (_, _, w) in fr[:12]}))



def steps(rom, state, frames=2400):
    """The game's logic steps over `frames` frames from the state: DoGameFrame copies Vcount into OldVcount once a
    step, moving the game on by the vblanks since the last (d7): steps counted, and the mean d7."""
    import gen95_organ_resume_check as O
    import gen95_shootout_check as SC
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    SC.computer(e)
    n, prev = 0, e.w(OLDVCOUNT)
    for f in range(frames):
        e.run(1)
        if f % 60 == 0:
            SC.computer(e)
        v = e.w(OLDVCOUNT)
        if v != prev:
            n += 1
            prev = v
    return dict(steps=n, mean_frames_a_step=round(frames / max(1, n), 4))


if __name__ == "__main__":
    main()
