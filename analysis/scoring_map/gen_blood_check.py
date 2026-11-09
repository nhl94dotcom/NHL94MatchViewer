"""NOSE4Web's head blood for game injuries (Genesis), in the game (2026-11-08).

The build: SPAinjuryfall's lists land on frame 369 (or 371) for 30, then hold 370 (or 372): the lying frames 275 / 291
with one blood piece in front (palette line 1, colours 12 and 13); the frame table copied to the ROM's end (the long at
$5DE7E, from Sprites $5DE7A); HotList 369-372 copied from 275 / 291; addframe2's tile number read unsigned.

A scratch copy of the ROM with injuries forced (gen_injury_check.patched: every fall of a puck carrier is an injury,
`game` or `period`), pad 1 on the home team and idle. Every frame: each player's sprite frame (any frame 369-372 shown
by a player who isn't in SPAinjuryfall is reported), palette line 1's colours 12 and 13 (palfadenew $BD28, and the
video chip's colour memory every 30 frames of play); for each injury the injured player's frames until he is taken off, which
way he fell (369-370 or 371-372), screenshots (whole and a crop round him from the sprite table), and one while the
horizontal scoreboard (sfhor) is up. Runs until two injuries in each lying direction or 40 minutes of frames.

python gen_blood_check.py ROM OUT [game|period]"""
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

import menu_shots as M
from gen_injury_check import patched
from gen_score_logo_check import Watch, VRAM_AT, PAL, VSPR, GSP, CLOCK, SFLAGS

FALL, INJ1, REC = 0x145C, 0x1AF4, 0xB04A


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    mode = sys.argv[3] if len(sys.argv) > 3 else "game"
    out.mkdir(parents=True, exist_ok=True)
    g = Watch(patched(rom, out, mode == "game"), out)
    e = g.e
    M.play(e, "w900 START w120 START w120 DOWN*7 RIGHT w60 S:setup", out)
    for _ in range(40):
        if e.b(0xFFF7) == 0:
            break
        e.run(4, hold=["START"])
        e.run(200)
    g.wait_play()
    w = lambda a: e.w(0xFF0000 | a)
    pal_seen, cram_seen, stray = Counter(), Counter(), []
    injuries, active = [], {}
    dirs = {"369-370": 0, "371-372": 0}
    for f in range(60 * 60 * 40):
        e.run(1)
        pal_seen[(w(PAL + 32 + 24), w(PAL + 32 + 26), g.in_play())] += 1
        if f % 30 == 0 and g.in_play():
            st = e.serialize()
            cram = st[VRAM_AT + 0x10000:VRAM_AT + 0x10080]
            cram_seen[(cram[32 + 24] | cram[32 + 25] << 8, cram[32 + 26] | cram[32 + 27] << 8)] += 1
        hor = bool(e.b(0xFF0000 | SFLAGS) & 0x80)
        for k in range(12):
            a = REC + k * 0x80
            anim, fr = w(a + 0x58), w(a + 0x06) & 0x7FF
            if 369 <= fr <= 372 and anim != FALL:
                stray.append((f, k, fr, hex(anim)))
            if anim in (FALL, INJ1) and k not in active:
                active[k] = dict(start=f, anim=hex(anim), frames=[], hor_shot=None, period=w(GSP) + 1, clock=w(CLOCK))
            if k in active:
                inj = active[k]
                if not inj["frames"] or inj["frames"][-1][0] != fr:
                    inj["frames"].append([fr, f - inj["start"], f - inj["start"]])
                else:
                    inj["frames"][-1][2] = f - inj["start"]
                t = f - inj["start"]
                tag = f"{mode}_{len(injuries)}_{k}"
                if t in (10, 40, 80, 200, 400):
                    e.screenshot(out / f"{tag}_{t:03d}.png")
                if hor and inj["hor_shot"] is None:
                    inj["hor_shot"] = t
                    e.screenshot(out / f"{tag}_hor.png")
                if fr == 0 or (anim not in (FALL, INJ1) and t > 30):
                    shown = {x[0] for x in inj["frames"]}
                    inj["dir"] = "369-370" if shown & {369, 370, 275} else "371-372" if shown & {371, 372, 291} else "?"
                    if shown & {641, 642, 643}:
                        inj["dir"] = "641-646"
                    elif shown & {647, 648, 649}:
                        inj["dir"] = "647-652"
                    dirs[inj["dir"]] = dirs.get(inj["dir"], 0) + 1
                    inj["record"] = k
                    injuries.append(inj)
                    del active[k]
        if len(injuries) >= 8 or (mode == "game" and min(dirs["369-370"], dirs["371-372"]) >= 2) or \
                (mode == "period" and min(dirs.get("641-646", 0), dirs.get("647-652", 0)) >= 2):
            break
        if f % 600 == 0 and e.b(0xFFF7) != 0:
            e.run(4, hold=["START"])
    print(f"{Path(rom).name} {mode}: {len(injuries)} injuries in {f} frames; by lying direction {dirs}")
    for inj in injuries:
        seq = " ".join(f"{fr}@{a}-{b}" for fr, a, b in inj["frames"])
        print(f"  record {inj['record']} P{inj['period']} {inj['clock']}s {inj['anim']} {inj['dir']}: {seq}  "
              f"(horizontal scoreboard at +{inj['hor_shot']})")
    print("frames 369-372 shown outside SPAinjuryfall:", stray[:10], len(stray))
    print("palette line 1 colours 12 / 13 (palfadenew; in play; frames):", sorted(pal_seen.items()))
    print("palette line 1 colours 12 / 13 (colour memory in play, every 30 frames; 9-bit form):", sorted(cram_seen.items()))


if __name__ == "__main__":
    main()
