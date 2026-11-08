"""NOSE4Web's SNES Y-button fix, played in the game (2026-11-08, the user approved running the patched ROMs). Holdplayer
(Y without the puck: hook or hold the nearest opponent in front) lets a player locked in an animation through unless
it is the burst, so a player who is down can still hook and hold. The fix (the bne .t1 before its rtl made two nops)
stops Y for any lock (pfalock), as doinput's other buttons are stopped: an ordinary knockdown (pfalock 1) and the locks
that hold an animation number instead (a fall into the boards or the bench, being held).

From the recorded SNES check moments (snes_check_pass_timing: a person's carrier on pad 1, the computer's skater
bursting at him), played with no pass: on frames where the pad-1 skater is locked (not in the burst), without the
puck, with an opponent within 40, the game is played twice from that frame, holding the same direction, once with Y
for 2 frames and once without, 16 frames on. Any difference in the animations (SPA) or locks of the 12 skaters is Y
acting; whether the locked skater's own changed, and whether a teammate had the puck (Y then works for the carrier:
a pass), are noted. Unlocked frames with an opponent near are tried the same way (Y should act there: the test's control).

python snes_y_button_test.py RUN ROM [N situations]   -> paths.RUNS / RUN / trials.jsonl (retail layout)
python snes_y_button_test.py report RUN [RUN]"""
import json
import math
import random
import sys
from collections import Counter, defaultdict

import snes_harness as H
from snes_check_pass_timing import Rig, scout, situations, pos, dir_to, DIRS, SPA, PFALOCK, LUNGE
from snes_emu import SnesEmu
from lowload import breathe, gentle
from paths import RUNS, SNES_STATE_TOP

NEAR, BRANCHES, GAP, AFTER = 40, 8, 4, 16


def signature(h):
    e = h.e
    return tuple(e.w(SPA + H.o(k)) for k in range(12)) + tuple(e.w(PFALOCK + H.o(k)) for k in range(12))


def branch(h, c, d):
    e = h.e
    st = e.serialize()
    branch.unlocked = None                         # the first frame after which he was no longer locked
    for f in range(AFTER):
        e.run(1, hold=(["Y"] if f < 2 else []) + DIRS[d])
        if branch.unlocked is None and not e.w(PFALOCK + H.o(c)):
            branch.unlocked = f
    with_y = signature(h)
    branch.own = (with_y[c], with_y[12 + c])
    e.unserialize(st)
    for f in range(AFTER):
        e.run(1, hold=DIRS[d])
    without = signature(h)
    branch.own_changed = branch.own != (without[c], without[12 + c])
    e.unserialize(st)
    return with_y != without


def play(h, sc):
    e = h.e
    e.unserialize(sc["start"])
    c, skate = sc["carrier"], sc["skate"]
    out, last = [], -99
    for f in range(sc["burst"] + 150):
        e.run(1, hold=DIRS[skate])
        if f < sc["burst"] or f - last < GAP or len(out) >= BRANCHES:
            continue
        if e.w(H.PUCKC) == H.o(c):
            continue
        lock, spa = e.w(PFALOCK + H.o(c)), e.w(SPA + H.o(c))
        cx, cy = pos(h, c)
        near = min(range(6, 12), key=lambda k: math.dist(pos(h, k), (cx, cy)))
        if math.dist(pos(h, near), (cx, cy)) > NEAR:
            continue
        kx, ky = pos(h, near)
        if lock and spa == LUNGE:
            continue
        acted = branch(h, c, dir_to(kx - cx, ky - cy))
        kind = "unlocked" if not lock else "knockdown (lock 1)" if lock == 1 else "lock holds an animation"
        own = e.w(H.PUCKC)
        out.append(dict(f=f, kind=kind, lock=lock, spa="%04x" % spa, acted=acted, unlocked=branch.unlocked, own_changed=branch.own_changed,
                        mate_has_puck=own < 0x8000 and own // 2 < 6))
        last = f
    return out


def main():
    run, rom = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 150
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    gentle()
    h = Rig(state=SNES_STATE_TOP, top=True, emu=SnesEmu(rom))
    sits = situations()
    random.Random(7).shuffle(sits)
    with open(out / "trials.jsonl", "w") as fh:
        for i, s in enumerate(sits[:n]):
            sc = scout(h, s, random.Random(i * 10).getrandbits(32))
            if sc is None:
                continue
            for r in play(h, sc):
                r["i"] = i
                fh.write(json.dumps(r) + "\n")
            fh.flush()
            breathe()
    print("done", flush=True)


def report(runs):
    for run in runs:
        rows = [json.loads(l) for l in open(RUNS / run / "trials.jsonl")]
        by = defaultdict(Counter)
        for r in rows:
            by[r["kind"]][r["acted"]] += 1
        print(f"{run}: " + "; ".join(f"{k}: Y acted {c[True]} of {c[True] + c[False]}" for k, c in sorted(by.items())))
        late = [r for r in rows if r["kind"] != "unlocked" and r["acted"]]
        print(f"   of the locked frames where Y acted: the lock over within the Y press (2 frames) "
              f"{sum(r['unlocked'] is not None and r['unlocked'] <= 1 for r in late)} of {len(late)}")
        print(f"   of those, a teammate with the puck (Y then works for him: a pass) "
              f"{sum(bool(r.get('mate_has_puck')) for r in late)}; the downed skater's own SPA changed "
              f"{sum(r.get('own_changed', False) for r in late)}")
        spas = Counter((r["spa"], r["lock"] if r["lock"] < 0x100 else "anim") for r in rows if r["kind"] != "unlocked" and r["acted"])
        if spas:
            print("   where Y acted while locked (SPA, lock):", dict(spas.most_common(8)))


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2:])
    else:
        main()
