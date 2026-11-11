"""chaos's fighting patch as NOSE4Web puts it in (2026-11-11, nhl94_fighting.bin, 3 MB): do fights happen, are
fighting majors given, does the game go on? The computer against itself (gen_injury_baseline's way: power-on to Game
Setup, START into play, both sides the computer every second), Penalties "On, Except Off-sides" (OptPen $D056 = 2)
and 5-minute periods (Optperlen $D050 = 0) set at Game Setup, the patch's own Fighting setting as the ROM starts it
(On). With `--hot`, every player's fighting rating (+$74 in each record, the working value, even, 0-14) is set to 14
each frame, so the few players who can start a fight aren't needed. Every penalty listed in the summary ($C5DC: a
byte count, then 4 bytes each: time, team | rule, roster index) is printed as it comes; at a fighting major (rule $26
or $28) the last 12 screenshots (one every 30 frames) are saved. The game is played to its end (or a frame limit) to
see it carries on.

python gen_fight_check.py ROM OUT [--hot] [seed]"""
import json
import sys
from collections import deque
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu
from goal_frames import grab

OPTPEN, OPTLINE, PERLEN, SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD056, 0xD058, 0xD050, 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
BASE, SZ, PENS = 0xB04A, 0x80, 0xC5DC
RULES = {0x16: "charging", 0x18: "slashing", 0x1A: "roughing", 0x1C: "cross-checking", 0x1E: "hooking", 0x20: "tripping",
         0x22: "interference", 0x24: "holding", 0x26: "FIGHTING", 0x28: "FIGHTING (2)", 0x2A: "instigating", 0x12: "roughing (injury)"}


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    hot = "--hot" in sys.argv
    seed = int([a for a in sys.argv[3:] if a.isdigit()][0]) if any(a.isdigit() for a in sys.argv[3:]) else 1
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1)
    e.setw(PERLEN, 0)
    e.screenshot(out / "setup_set.png")
    if not G.into_play(e):
        print("never reached play")
        return
    e.setl(SEED, (0x2545F491 * seed) & 0xFFFFFFFF or 1)
    shots = deque(maxlen=12)
    seen, frame, still, last, fights = 0, 0, 0, None, []
    while e.w(GSP) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
        if hot:
            for k in range(12):
                e.setb(BASE + SZ * k + 0x74, 14)
        fighting = any(e.b(BASE + SZ * k + 0x63) & 1 for k in range(12))     # pf2fight
        want = frame % 30 == 0 or (fighting and frame % 10 == 0)
        e.want_frame = want
        # START only for a screen that waits (not play: a fight or any stoppage stands the clock still too)
        e.run(2, hold=["START"] if still >= 8 and e.b(SCREEN) not in (0, 0x80) and frame % 60 < 4 else [])
        e.want_frame = False
        if want:
            img = grab(e)
            shots.append((frame, img))
            if fighting:
                k = len(fights)
                live = getattr(main, "live", {})
                live[k] = live.get(k, 0) + 1
                main.live = live
                if live[k] <= 60:
                    img.save(out / f"fight{k}_live_{live[k]:02d}.png")
        if fighting and not getattr(main, "was", False):
            print(f"frame {frame}: a fight starts (pf2fight) at period {e.w(GSP)}, clock {e.w(CLOCK)}", flush=True)
        main.was = fighting
        frame += 2
        n = e.w(PENS)
        if 0 < n <= 240:
            while seen + 4 <= n:
                t, code, who = e.w(PENS + 2 + seen), e.b(PENS + 4 + seen), e.b(PENS + 5 + seen)
                seen += 4
                rule = code & 0x7F
                name = RULES.get(rule, hex(rule))
                print(f"frame {frame}: period {t >> 14}, {t & 0x3FFF} s in, {'away' if code & 0x80 else 'home'} #{who}: {name}",
                      flush=True)
                if rule in (0x26, 0x28):
                    k = len(fights)
                    for j, (f, img) in enumerate(shots):
                        img.save(out / f"fight{k}_{j:02d}.png")
                    fights.append(dict(frame=frame, period=t >> 14, seconds=t & 0x3FFF, team=code >> 7, roster=who))
    print(json.dumps(dict(frames=frame, periods_done=e.w(GSP), score=[e.w(0xC6DA), e.w(0xCA3E)], fights=fights,
                          penalties=seen // 4)))
    e.screenshot(out / "end.png")


if __name__ == "__main__":
    main()
