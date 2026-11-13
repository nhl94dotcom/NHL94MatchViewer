"""SNES: B on defence that does nothing (2026-11-13, NOSE4Web's report from a league member: "pressing B on defence
sometimes does nothing, the skater seems stuck in an animation").

The reading (SNES_MECHANICS 7.3, findpc): B without the puck runs findpc, which picks the skater of the pad's team
with the lowest puck distance (+32 for each 45 degrees the puck is off the preferred direction while it is carried).
Locked skaters (pfalock) are skipped, except in a turn ($EBB0 SPAturnl, $EBE2 SPAturnr) or the cross-check to burst
range ($F196 SPAcrosscheck, $F208 SPAsweepchk, the shoulder and hip checks, $F342 SPAburst). If the choice is the pad's
own skater, findpc's .10 runs Sweepcheck (a poke) only when he isn't locked: locked, nothing happens.

Here, in the retail ROM's live play (snes_harness's state: home on pad 1, attacking the top net in period 1), pad 1
defends against the computer: it steers its skater at the puck, sometimes bursts (A) near the carrier (bursts and
checks), sometimes reverses (turns), and presses B at random moments when its team hasn't the puck (not at a faceoff).
Each B press: the RAM just before it (positions, puckc, puckdist $0B1D, puckdir $0B5D, SPA, pfalock $14E3, pflags,
playerpad $19D4, position, pfgoal) gives findpc's choice worked out the routine's way; then the frame with B runs and
B is held 4 frames (the retail game runs its logic on every other frame, so a 1-frame tap
can go unseen: the first try's 'nothing' presses were mostly that), then 4 more: a switch (c1playernum $19EC changed), a poke (his SPA $F208) or nothing.

python snes_b_nothing_trace.py OUT.jsonl [MINUTES of play, default 20] [SEED]   (gentle mode, one process)
python snes_b_nothing_trace.py OUT.jsonl report"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

import snes_harness as H
from lowload import breathe, gentle

C1, PLAYERPAD, PUCKC, PUCKDIST, PUCKDIR = 0x19EC, 0x19D4, 0x0AD9, 0x0B1D, 0x0B5D
SPA, PFALOCK, PFLAGS, POSITION, PFGOAL, PFTEAM = 0x11A3, 0x14E3, 0x1283, 0x0F43, 0x14C3, 0x1503
SFLAGS, CLOCK = 0x15D8, 0x1632
TURNS = (0xEBB0, 0xEBE3)
CHECKS = (0xF196, 0xF343)
SWEEP = 0xF208
B_FRAMES = 4
NAMES = {0xEBB0: "turn left", 0xEBE2: "turn right", 0xF196: "cross-check", 0xF208: "poke", 0xF27A: "shoulder check l",
         0xF2AC: "shoulder check r", 0xF2DE: "hip check l", 0xF310: "hip check r", 0xF342: "burst",
         0xEC14: "stop", 0xEAFE: "glide?", 0xEA4C: "skate"}
DIRS = H.DIRPAD


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def snapshot(e):
    g = lambda a, k: e.w(a + 2 * k)
    return {"puckc": s16(e.w(PUCKC)), "c1": e.w(C1) // 2,
            "obj": [{"x": s16(g(H.XPOS, k)), "y": s16(g(H.YPOS, k)), "spa": g(SPA, k), "lock": g(PFALOCK, k),
                     "flags": g(PFLAGS, k), "pad": s16(g(PLAYERPAD, k)), "pos": s16(g(POSITION, k)),
                     "goal": g(PFGOAL, k), "dist": g(PUCKDIST, k), "dir": g(PUCKDIR, k)} for k in range(12)]}


def findpc_choice(s, pad=0, team_first=0):
    """findpc for pad 1 (d4 = 0) as the routine does it, from the RAM before the frame: 'close' (the direct poke path),
    else the chosen object, or None (no candidate)."""
    o = s["obj"]
    me = s["c1"]
    puckc = s["puckc"]
    r0 = 8
    if puckc >= 0:
        m = o[me]
        if m["pos"] != 0 and m["pad"] >= 0 and m["lock"] == 0 and m["dist"] < 0x64:   # puckdist2 approximated below
            pass
        carrier = o[puckc // 2]
        if carrier["pad"] < 0 or True:            # the carrier is the computer's (no pad): a preferred direction
            r0 = 0 if m["goal"] else 4
    best, cost = None, 0xFFFF
    for k in range(team_first, team_first + 6):
        c = o[k]
        if c["pos"] <= 0 or c["pos"] & 0x8000:
            continue
        if c["flags"] & 0x1000:
            continue
        spa = c["spa"]
        eligible_locked = TURNS[0] <= spa < TURNS[1] or CHECKS[0] <= spa < CHECKS[1]
        if not eligible_locked and c["lock"]:
            continue
        if c["pad"] >= 0 and c["pad"] != pad:
            continue
        pen = 0
        if puckc >= 0 and r0 != 8:
            d = (r0 ^ c["dir"]) & 0xFFFF
            if d >= 4:
                d = (d ^ 0xFFFF) + 8 + 1 & 0xFFFF   # eor #$FFFF / adc #8 with the carry set by cmp
            if d:
                pen = (d - 1) * 32
        v = c["dist"] + pen
        if v > 0xFFFF:
            continue
        if v < cost:
            best, cost = k, v
    return best


def defend_input(e, s, rng, state):
    """Pad 1's held buttons for this frame: steer at the puck (or reverse now and then), A near the carrier."""
    me = s["obj"][s["c1"]]
    px, py = e.w(H.XPOS + 2 * 14), e.w(H.YPOS + 2 * 14)
    px, py = s16(px), s16(py)
    dx, dy = px - me["x"], py - me["y"]
    import math
    ang = (math.degrees(math.atan2(dx, dy)) + 360) % 360           # 0 = up the screen (y grows up the ice)
    d = int((ang + 22.5) // 45) % 8
    if state.get("reverse", 0) > 0:
        state["reverse"] -= 1
        d = (d + 4) % 8
    elif rng.random() < 0.01:
        state["reverse"] = rng.randint(6, 20)
    hold = list(DIRS[d])
    if s["puckc"] >= 0 and math.hypot(dx, dy) < 45 and rng.random() < 0.08:
        hold.append("A")
    return hold


def run(out, minutes, seed):
    rng = random.Random(seed)
    h = H.Harness()
    e = h.e
    e.unserialize(h.base)
    gentle()
    frames, f, next_b, state = int(minutes * 60 * 60), 0, 60, {}
    rows = []
    with open(out, "a") as fh:
        while f < frames:
            if f % 3600 == 0 and f:
                breathe()
            s = snapshot(e)
            ours = s["puckc"] >= 0 and s["puckc"] // 2 < 6
            faceoff = e.w(SFLAGS) & 0x0100
            hold = defend_input(e, s, rng, state)
            if f >= next_b and not ours and not faceoff and s["c1"] < 6:
                choice = findpc_choice(s)
                me = s["c1"]
                after = []
                for i in range(B_FRAMES + 4):            # B held B_FRAMES frames (the retail game reads the pad on
                    e.run(1, hold=hold + (["B"] if i < B_FRAMES else []))   # every other frame: a 1-frame tap can be
                    after.append(snapshot(e))            # missed altogether), then 4 more
                f += B_FRAMES + 4
                switched = any(a["c1"] != me for a in after)
                poked = any(a["obj"][me]["spa"] == SWEEP for a in after)
                m = s["obj"][me]
                row = {"f": f, "me": me, "loose": s["puckc"] < 0, "result": "switch" if switched else "poke" if poked else "nothing",
                       "spa": m["spa"], "anim": NAMES.get(m["spa"], f"{m['spa']:04X}"), "locked": bool(m["lock"]),
                       "choice": choice, "chose_me": choice == me, "dist": m["dist"],
                       "new": after[0]["c1"] if switched else None}
                fh.write(json.dumps(row) + "\n")
                rows.append(row)
                next_b = f + rng.randint(15, 70)
                continue
            e.run(1, hold=hold)
            f += 1
    return rows


def report(path):
    rows = [json.loads(l) for l in open(path)]
    c = Counter(r["result"] for r in rows)
    print(f"{len(rows)} B presses without the puck: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
    no = [r for r in rows if r["result"] == "nothing"]
    print(f"\nnothing ({len(no)}): his own skater locked {sum(r['locked'] for r in no)}; findpc's choice (worked out) his own "
          f"skater {sum(r['chose_me'] for r in no)}, none {sum(r['choice'] is None for r in no)}")
    print("  his animation:", ", ".join(f"{k} {v}" for k, v in Counter(r["anim"] for r in no).most_common()))
    print("  puck loose / carried:", sum(r["loose"] for r in no), "/", sum(not r["loose"] for r in no))
    lk = [r for r in rows if r["locked"]]
    print(f"\nall presses with his own skater locked ({len(lk)}):")
    for anim, n in Counter(r["anim"] for r in lk).most_common():
        sub = [r for r in lk if r["anim"] == anim]
        print(f"  {anim}: {n}: " + ", ".join(f"{k} {v}" for k, v in Counter(r['result'] for r in sub).most_common()))
    agree = sum((r["result"] == "switch") == (not r["chose_me"] and r["choice"] is not None) for r in rows)
    print(f"\nworked-out choice agrees with switch / no switch: {agree} of {len(rows)}")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] == "report":
        report(out)
    else:
        run(out, float(sys.argv[2]) if len(sys.argv) > 2 else 20, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
        report(out)
