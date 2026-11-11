"""The fighting setting on a plus-minus ROM (2026-11-11, for NOSE4Web: the setting moved from $FFDF00, inside smozROM's
plus-minus log from $FFDEF4, to $FFF080). On CDL_Season_12_fighting.bin (and the original CDL for the comparison):
Fighting chosen on Game Setup's last line (RIGHT pressed until the word at $FFF080 reads the choice: 0 Off, 1 On, 2
Arcade), Penalties On Except Off-sides, 5-minute periods, the computer against itself (gen_injury_baseline's way),
every player's fighting rating (+$74) set to 14 so fights are likely when on, the random seed set at the opening faceoff;
two games in a row (back to Game Setup after the first, the setting left as it is). Every 2 frames: the setting word,
goals, a fight starting (pf2fight, +$63 bit 0, on any player). At each goal the plus-minus log ($FFDEF4 on, 512 bytes)
is kept. Prints the setting's values seen, goals, fights and a hash of the log after each goal; `compare` runs the
original CDL the same way (its Fighting line absent: no setting) for the Off case, so the two logs can be compared goal
by goal.

python gen_fight_setting_check.py ROM CHOICE OUT [--hot]   (CHOICE 0 / 1 / 2, or none for a ROM without the line)"""
import hashlib
import json
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

SETTING, OPTPEN, PERLEN, SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xF080, 0xD056, 0xD050, 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
BASE, SZ, LOG = 0xB04A, 0x80, 0xDEF4


def press(e, b, w=26):
    e.run(4, hold=[b])
    e.run(w)


def log_bytes(e):
    return bytes(e.b(LOG + i) for i in range(512))


def setup(e, out, choice):
    G.to_setup(e, out)
    if choice is not None:
        for _ in range(12):                      # down to the last line (Fighting)
            press(e, "DOWN")
        for _ in range(6):
            if e.w(SETTING) == choice:
                break
            press(e, "RIGHT")
    e.setw(OPTPEN, 2)
    e.setw(PERLEN, 0)


def play_game(e, hot, n, out):
    if not G.into_play(e):
        return dict(error="never reached play")
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    seen, goals, logs, fights = set(), 0, [], 0
    frame, still, last, ended, was = 0, 0, None, None, False
    score0 = None
    while frame < 60 * 60 * 40:
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
        e.run(2, hold=["START"] if still >= 8 and frame % 60 < 4 else [])
        frame += 2
        seen.add(e.w(SETTING))
        fighting = any(e.b(BASE + SZ * k + 0x63) & 1 for k in range(12))
        fights += fighting and not was
        was = fighting
        score = (e.w(0xC6DA), e.w(0xCA3E))
        if score0 is not None and sum(score) > sum(score0):
            e.run(60)                            # the log written
            frame += 60
            logs.append(hashlib.md5(log_bytes(e)).hexdigest()[:10])
            goals += 1
        score0 = score
        if ended is None and e.w(GSP) >= 3:
            ended = frame
        if ended is not None and (e.w(GSP) == 0 or frame - ended > 10 * 60 * 60):
            break
    e.screenshot(out / f"game{n}_end.png")
    return dict(game=n, frames=frame, final=score0, goals=goals, fights=fights, setting_seen=sorted(seen), logs=logs)


def main():
    rom, choice, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    choice = None if choice == "none" else int(choice)
    hot = "--hot" in sys.argv
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    e = Emu(rom)
    setup(e, out, choice)
    print("setting at Game Setup:", e.w(SETTING), flush=True)
    for n in range(2):
        if n:
            for _ in range(60):                  # back to Game Setup
                if e.b(SCREEN) == 15:
                    break
                press(e, "START", 200)
            e.setw(OPTPEN, 2)
            e.setw(PERLEN, 0)
            print("setting at the second Game Setup:", e.w(SETTING), flush=True)
        print(json.dumps(play_game(e, hot, n, out)), flush=True)


if __name__ == "__main__":
    main()
