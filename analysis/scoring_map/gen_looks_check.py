"""NOSE4Web's "looks" options played (2026-11-09, nhl94_looks.bin against nhl94.bin): the intro screens' wait, puck
friction, the home team's puck colours and the fan's colour.

- intro: from power-on with no input, a screenshot every 2 frames; each run of unchanged frames of 30 or more is
  printed with its start and length (the EA Sports and High Score screens are the first long ones).
- friction: in play, with the puck loose, it is put at 12 spots in turn, each far from every skater, with speed (6000,
  0) on the ice; the speed is read each frame for 30 frames (a run touched by anyone, or off the boards, is dropped),
  and the kept fraction a second worked out from the frame-to-frame ratio.
- looks: a screenshot at the opening faceoff and every 60 frames after, for the puck and the crowd (OUT/looks_NN.png).

python gen_looks_check.py ROM OUT"""
import hashlib
import statistics
import sys
from pathlib import Path

import lowload
import gen_1on1_edit_lines as G

REC, PUCK = 0xB04A, 0xB04A + 14 * 0x80


def intro(r, out):
    last, start, runs = None, 0, []
    for f in range(0, 1400, 2):
        r.step(2)
        p = out / "_intro.png"
        r.e.screenshot(p)
        h = hashlib.md5(p.read_bytes()).hexdigest()
        if h != last:
            if last is not None and f - start >= 30:
                runs.append((start, f - start))
            last, start = h, f
            if len(runs) < 6:
                r.e.screenshot(out / f"intro_{f:04d}.png")
    print("intro: unchanged stretches (start frame, frames):", runs, flush=True)


def friction(r):
    e = r.e
    ratios = []
    spots = [(x, y) for x in (-60, 0, 60) for y in (-150, -50, 50, 150)]
    for k in range(60):
        x, y = spots[k % len(spots)]
        e.setw(PUCK + 0x00, x)
        e.setw(PUCK + 0x14, y)
        e.setw(PUCK + 0x18, 0)
        e.setw(PUCK + 0x28, 6000)
        e.setw(PUCK + 0x2A, 0)
        e.setw(PUCK + 0x2C, 0)
        e.setb(PUCK + 0x60, 0xFF)
        e.setw(PUCK + 0x5E, 0)
        sp = []
        for _ in range(30):
            r.step(1)
            sp.append((e.w(PUCK + 0x28), e.w(PUCK + 0x2A), e.w(PUCK + 0x18), e.b(PUCK + 0x60)))
        vx = [s[0] for s in sp]
        clean = all(s[1] == 0 and s[2] == 0 and s[3] == 0xFF for s in sp) and all(
            0 < b <= a for a, b in zip(vx, vx[1:]))
        if clean and vx[0] > 0:
            ratios.append((vx[-1] / vx[0]) ** (1 / (len(vx) - 1)))
        if len(ratios) >= 12:
            break
        lowload.breathe()
    if ratios:
        m = statistics.median(ratios)
        print(f"friction: {len(ratios)} clean runs, a frame {m:.5f} (1/{1 / (1 - m):.0f}), a second {m ** 60:.3f}",
              flush=True)
    else:
        print("friction: no clean run", flush=True)


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    r = G.Run(rom, out)
    intro(r, out)
    print("in play:", r.to_play(), flush=True)
    st = r.e.serialize()
    for i in range(6):
        r.e.screenshot(out / f"looks_{i:02d}.png")
        r.step(60)
    r.e.unserialize(st)
    friction(r)


if __name__ == "__main__":
    main()
