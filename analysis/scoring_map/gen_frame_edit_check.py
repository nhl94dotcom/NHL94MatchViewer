"""Sprite frame edits seen in play (Genesis, 2026-11-22: NOSE4Web's "Clockwise's sprite edit" with 37 more taped
frames, nhl94_clockwise_more_tape.bin 91FC2E1C and CDL_Season_12_clockwise_more_tape.bin 8D82CFD4).

BASE plays from power-on into play (gen_ot_check) and its state is kept; EDIT starts from the same state (the edits
change graphics only; BASE's screens are all taken first, the core being one per process). Then for every frame number 0..LAST: both load the state, every skater's sprite frame (the
word at +$06 of records 0-11, goalies left alone) is set to that number, one frame is run and the screen taken. The screens are compared:
a frame "shows" an edit when pixels differ between BASE and EDIT. For each frame that shows one: the differing pixels'
count, how many groups they make (pixels within 3 of each other: a stick's tape, a face's eyes), the groups' sizes,
and the colours EDIT draws there. The frames listed on the command line get a sheet for looking (BASE left, EDIT
right, each differing group enlarged x6, differing pixels boxed), and are checked off against the frames that show.

python gen_frame_edit_check.py BASE EDIT OUT LAST FRAME [FRAME ...]   (NHL94_STATE_ROM: the ROM that plays into the state)"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import gen_ot_check as G
import lowload
from emu import Emu

REC, SIZE, FRAME = 0xB04A, 0x80, 0x06


def screen(e):
    e.want_frame = True
    e.lib.retro_run()
    e.want_frame = False
    data, w, h, pitch = e.frame
    if getattr(e, "pixfmt", 0) == 2:
        img = Image.frombuffer("RGB", (w, h), data, "raw", "BGR;16", pitch, 1)
    else:
        img = Image.frombuffer("RGBX", (w, h), data, "raw", "BGRX", pitch, 1).convert("RGB")
    return np.array(img)


def forced(e, state, f):
    e.unserialize(state)
    for _ in range(3):                           # the screen shown is built a frame behind: set again each frame
        for k in range(12):
            if e.b(REC + SIZE * k + 0x35) != 0:  # skaters only: a goalie given another frame goes into a save move of
                e.setw(REC + SIZE * k + FRAME, f)  # his own (an edited goalie frame then shows whatever was asked for)
        img = screen(e)
    return img


def groups(mask, reach=3):
    ys, xs = np.nonzero(mask)
    left = set(zip(ys.tolist(), xs.tolist()))
    out = []
    while left:
        seed = left.pop()
        g, stack = [seed], [seed]
        while stack:
            y, x = stack.pop()
            near = [(a, b) for a in range(y - reach, y + reach + 1) for b in range(x - reach, x + reach + 1) if (a, b) in left]
            for p in near:
                left.discard(p)
            g += near
            stack += near
        out.append(g)
    return sorted(out, key=lambda g: (g[0][0], g[0][1]))


def main():
    base, edit, out, last = sys.argv[1], sys.argv[2], Path(sys.argv[3]), int(sys.argv[4])
    listed = [int(x) for x in sys.argv[5:]]
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    e0 = Emu(os.environ.get("NHL94_STATE_ROM", base))   # the ROM that plays into the state (a patched BASE can fail
    G.to_setup(e0, out)                                 # the game's checksum test at power-on: the original then)
    if not G.into_play(e0):
        raise SystemExit("never reached play")
    e0.run(150)
    state = e0.serialize()
    if "NHL94_STATE_ROM" in os.environ:
        e0 = Emu(base)
    e0.unserialize(state)
    plain0 = screen(e0)
    A = [forced(e0, state, f) for f in range(last + 1)]   # all of BASE's first: the core is one per process, a
    e1 = Emu(edit)                                         # second Emu takes it over
    e1.unserialize(state)
    plain1 = screen(e1)
    print("unforced screens differ in", int((plain0 != plain1).any(2).sum()), "pixels", flush=True)
    res, tiles = {}, []
    # what differs whatever frame the players are given is not theirs (another sprite on the screen: the official's
    # stick-like piece here): its pixels are left out of every frame's count
    always = np.ones(plain0.shape[:2], bool)
    for f in (1, 2, 3, 50, 200, 700):
        always &= (A[f] != forced(e1, state, f)).any(2)
    const = int(always.sum())
    print("pixels that differ whatever the frame:", const, flush=True)
    for f in range(last + 1):
        a, b = A[f], forced(e1, state, f)
        held = sum(e1.w(REC + SIZE * k + FRAME) == f for k in range(12))
        mask = (a != b).any(2) & ~always
        n = int(mask.sum())
        if f % 100 == 0:
            lowload.breathe()
        if not n:
            continue
        gs = groups(mask)
        cols = sorted({tuple(int(v) for v in b[y, x]) for g in gs for y, x in g})
        res[f] = dict(pixels=n, groups=len(gs), sizes=sorted(len(g) for g in gs), colours=cols, still_set=held)
        if f in listed:
            from collections import Counter
            mode = Counter(len(g) for g in gs if len(g) != const).most_common(1)
            pick = [g for g in gs if mode and len(g) == mode[0][0]] or gs
            cen = lambda g: (sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g))  # noqa: E731
            far = lambda g: min([abs(cen(g)[0] - cen(h)[0]) + abs(cen(g)[1] - cen(h)[1]) for h in gs if h is not g] or [999])  # noqa: E731
            g = max(pick, key=far)                         # a player standing clear of the others
            res[f]["shown_group"] = len(g)
            ys, xs = [p[0] for p in g], [p[1] for p in g]
            cy, cx = (min(ys) + max(ys)) // 2, (min(xs) + max(xs)) // 2
            y0, y1 = max(0, cy - 26), min(a.shape[0], cy + 27)
            x0, x1 = max(0, cx - 26), min(a.shape[1], cx + 27)
            Z = 5
            marked = b.copy()
            marked[mask] = (255, 0, 255)
            im = Image.new("RGB", (3 * ((x1 - x0) * Z + 4), (y1 - y0) * Z + 12), (255, 255, 255))
            d = ImageDraw.Draw(im)
            d.text((1, 0), f"{f}: {len(g)} px   original | edit | changed pixels", fill=(0, 0, 0))
            for k, src in enumerate((a, b, marked)):
                part = Image.fromarray(src[y0:y1, x0:x1]).resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.NEAREST)
                im.paste(part, (k * ((x1 - x0) * Z + 4), 12))
            tiles.append(im)
    shows = sorted(res)
    print("frames that show an edit:", len(shows), flush=True)
    print("listed and showing:", sorted(set(listed) & set(shows)))
    print("listed, NOT showing:", sorted(set(listed) - set(shows)))
    for f in listed:
        if f in res:
            print(f, res[f])
    (out / "frames.json").write_text(json.dumps(dict(listed=listed, shows=res)))
    W, n, x, y, rh = 1900, 0, 0, 0, 0
    S = Image.new("RGB", (W, 2600), (255, 255, 255))
    for im in tiles:
        if x + im.width > W:
            x, y, rh = 0, y + rh + 6, 0
        if y + im.height > S.height:
            S.crop((0, 0, W, y)).save(out / f"sheet_{n}.png")
            n, x, y, rh = n + 1, 0, 0, 0
            S = Image.new("RGB", (W, 2600), (255, 255, 255))
        S.paste(im, (x, y))
        x += im.width + 8
        rh = max(rh, im.height)
    S.crop((0, 0, W, y + rh)).save(out / f"sheet_{n}.png")
    print("sheets:", n + 1)


if __name__ == "__main__":
    main()
