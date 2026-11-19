"""GIFs of a flat puck going in past a goalie in a stick save, NHL '94 and NHL '95 (2026-11-19; slip_save.py's case:
docs/img/slip_save_94_95.svg). slip_save.collect keeps the game at the first frame of each stick save; the first puck
from the given lanes and speeds that goes in (NHL '95: untouched; NHL '94: after the goalie touches it) is played again
with every frame kept, from 6 frames before he could reach it to 20 after the goal, at a third of the game's speed.

python slip_gif.py GAME ROM STATE OUT.gif    (GAME 94 or 95)"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import gen95_assist_check as G
import slip_save as S
from emu import Emu
from goal_frames import grab
from slip_compare import CFG, GOALIE, s16

TRY = {"95": [(0, 18000), (-1, 18000), (1, 18000), (0, 12000)], "94": [(-1, 15000), (0, 15000), (-2, 18000)]}


def shoot(e, st, lane, sp, team, frames=None):
    e.unserialize(st)
    gx, gy = s16(e.w(G.rec(GOALIE))), s16(e.w(G.rec(GOALIE) + 0x14))
    P = G.PUCK
    e.setw(P, (gx + lane) & 0xFFFF); e.setw(P + 0x14, (gy - 60) & 0xFFFF); e.setw(P + 0x18, 0)
    e.setw(P + 0x28, 0); e.setw(P + 0x2A, sp & 0xFFFF); e.setw(P + 0x2C, 0)
    e.setb(P + 0x60, 0xFF); e.setb(P + 0x5E, 0); e.setb(G.rec(GOALIE) + 0x5E, 0)
    s0 = e.w(team + 0x0C)
    touched, goal_at = False, None
    pv = (0, sp)
    for f in range(90):
        for k in range(12):
            if k != GOALIE:
                e.setw(G.rec(k), (-100 + 18 * k) & 0xFFFF); e.setw(G.rec(k) + 0x14, (-230) & 0xFFFF)
        e.want_frame = frames is not None
        e.run(1)
        e.want_frame = False
        if frames is not None:
            frames.append(grab(e))
        px, py = s16(e.w(P)), s16(e.w(P + 0x14))
        gx, gy = s16(e.w(G.rec(GOALIE))), s16(e.w(G.rec(GOALIE) + 0x14))
        v = (s16(e.w(P + 0x28)), s16(e.w(P + 0x2A)))
        if e.b(P + 0x60) == 0:
            return False, True, None
        if math.hypot(px - gx, py - gy) <= 22 and math.hypot(v[0] - pv[0], v[1] - pv[1]) > 0.2 * max(1, math.hypot(*pv)):
            touched = True
        pv = v
        if goal_at is None and e.w(team + 0x0C) != s0:
            goal_at = f
            if frames is None:
                return True, touched, f
        if goal_at is not None and f >= goal_at + 20:
            break
    return goal_at is not None, touched, goal_at


def main():
    game, rom, state, out = sys.argv[1:5]
    c = CFG[game]
    G.BASE, G.TEAM = c["base"], c["team"]
    G.PUCK = G.rec(14)
    e = Emu(rom)
    states = S.collect(game, e, Path(state).read_bytes())
    want_touch = game == "94"
    for lane, sp in TRY[game]:
        for key, st in sorted(states.items()):
            goal, touched, at = shoot(e, st, lane, sp, c["team"])
            if goal and touched == want_touch:
                frames = []
                shoot(e, st, lane, sp, c["team"], frames)
                start = max(2, at - int(60 / (sp / 4096)) - 6)   # the first frames still draw the old shot
                shots = []
                title = (f"NHL '{game}: a flat puck at a goalie in a stick save, {lane:+d} from his centre"
                         if lane else f"NHL '{game}: a flat puck at the middle of a goalie in a stick save")
                note = "in after he touches it: his body bounces it back" if touched else "in untouched: it slides through"
                for i, im in enumerate(frames[start:]):
                    im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
                    canvas = Image.new("RGB", (im.width, im.height + 40), (255, 255, 255))
                    canvas.paste(im, (0, 40))
                    d = ImageDraw.Draw(canvas)
                    d.text((8, 4), title, fill=(31, 41, 51))
                    d.text((8, 20), f"{note}   (a third of the game's speed)", fill=(82, 96, 109))
                    shots.append(canvas)
                shots += [shots[-1]] * 30
                shots[0].save(out, save_all=True, append_images=shots[1:], duration=50, loop=0, optimize=True)
                print(f"{out}: state {key}, lane {lane}, speed {sp}, goal at frame {at}, {len(shots)} frames", flush=True)
                return
    print("no goal found in", TRY[game])


if __name__ == "__main__":
    main()
