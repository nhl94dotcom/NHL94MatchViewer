"""SNES: how ordinary shot wind-ups end (2026-11-13, for NOSE4Web's shotFix 80f108e: puckglue puts the game-wide shot
flag sfssdir back when the player who gains the puck is in a shot swing, SPA $ED4A-$F020, below SPAnum $18). Computer
games (snes_ot_goal_check.start; the computer's shots go through ShotMode and the same flag), every frame for every
object in SPAshotf / SPAshotb (the ROM's own words through tools/systems/snes_layout.py) while it is the carrier at
the start: puckc ($0AD9, object x 2) and nopuck ($1203, doshot sets 16 for the shooter) each frame. Each wind-up ends:
  fired          doshot ran (the puck went loose with his nopuck at 16)
  held_regather  no shot, he has the puck at the end, and it left him and came back during the wind-up
  held_kept      no shot, he has the puck at the end and never lost it (a hold or hook clears the flag: holdcheck)
  lost           someone else has it, or it is loose, with no shot
Run the same seeds on the ROM without the change: the totals (wind-ups, fired, lost) show whether shots and play are
otherwise unchanged.

--force-regather: 3 frames into every wind-up the puck is made loose where it is (puckc $FFFF; nothing else changed),
so he gathers it straight back through the ordinary pickup: retail loses the shot, the fix should keep it.

python snes_shot_windup_trace.py ROM GAMES OUT.jsonl [FIRST] [--force-regather]"""
import json
import sys
from pathlib import Path

import lowload
from snes_60fps_cvc import CLOCK, GSP, computer_only
from snes_ot_goal_check import start
from snes_onetimer_hold_trace import layout_of

SPA, NOPUCK, PUCKC = 0x11A3, 0x1203, 0x0AD9
FORCE = "--force-regather" in sys.argv


def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def shot_words(rom):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    from systems import snes_layout
    data = Path(rom).read_bytes()
    data = data[512:] if len(data) % 0x8000 == 512 else data
    lay = snes_layout.layout(data)
    return tuple(lay.rom_spa(w) for w in (0xED4A, 0xEE5C))


def game(rom, n, tmp, words):
    e, m = start(rom, n, tmp)
    counts = {"fired": 0, "held_regather": 0, "held_kept": 0, "lost": 0}
    cases = []
    open_ = {}
    f, still, last = 0, 0, None
    while m.w(GSP) < 3 and f < 60 * 60 * 40:
        if f % 300 == 0:
            computer_only(m)
            if f % 3600 == 0:
                lowload.breathe()
        if f % 60 == 0:
            c = m.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
        e.run(1, hold=["START"] if still >= 8 and f % 60 < 4 else [])
        f += 1
        pc = s16(m.w(PUCKC))
        for k in range(12):
            in_w = m.w(SPA + 2 * k) in words
            if in_w and k not in open_ and pc == 2 * k:
                open_[k] = {"start": f, "left": False, "fired": False, "clock": m.w(CLOCK), "period": m.w(GSP)}
            if k in open_:
                s = open_[k]
                if FORCE and f - s["start"] == 3 and pc == 2 * k and not s.get("forced"):
                    m.setw(PUCKC, 0xFFFF)          # knocked loose at his stick: he gathers it back (puckstick, puckglue)
                    s["forced"] = True
                    continue
                if pc != 2 * k:
                    if pc < 0 and m.w(NOPUCK + 2 * k) == 16:
                        s["fired"] = True
                    elif not s["fired"]:
                        s["left"] = True
                if not in_w:
                    if s["fired"]:
                        kind = "fired"
                    elif pc == 2 * k:
                        kind = "held_regather" if s["left"] else "held_kept"
                    else:
                        kind = "lost"
                    counts[kind] += 1
                    if kind.startswith("held"):
                        cases.append({"kind": kind, "start": s["start"], "frames": f - s["start"], "period": s["period"],
                                      "clock": s["clock"]})
                    del open_[k]
    return {"game": n, "frames": f, "counts": counts, "held": cases}


def main():
    args = [a for a in sys.argv if not a.startswith("--")]
    rom, games, out = args[1], int(args[2]), Path(args[3])
    args = [a for a in sys.argv if not a.startswith("--")]
    first = int(args[4]) if len(args) > 4 else 1
    words = shot_words(rom)
    lowload.gentle()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "_boot"
    tmp.mkdir(parents=True, exist_ok=True)
    for n in range(first, first + games):
        r = game(rom, n, tmp, words)
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(json.dumps({"game": n, "frames": r["frames"], "counts": r["counts"]}), flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
