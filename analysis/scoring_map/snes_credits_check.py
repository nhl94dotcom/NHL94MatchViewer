"""SNES title screen credits, played (2026-11-09, for NOSE4Web a638265's credits editor). From power-on with no
input, the title screen's credits (StartCredits / RollCredits) are watched through their RAM: CreditStep ($0BD9: 0
title and name scroll in, 1 name scrolls in, 2 held, 3 done), CreditTitleIdx ($0BDD), CreditNameIdx ($0BE1). Each
time a title and name come to rest (step 2) a screenshot is saved as OUT/<run>_t<title>_n<name>.png; the frame each
roll ends (step 3) and the frame the next roll starts (StartCredits again, after the attract cycle) are printed, and
the first rest of the second roll is saved too. `menu_shots.emulator` reads the SA-1 builds' moved RAM.

python snes_credits_check.py ROM OUT [max_frames]"""
import sys
from pathlib import Path

import lowload
from menu_shots import emulator

STEP, TITLE, NAME, CTIME = 0x0BD9, 0x0BDD, 0x0BE1, 0x0BDB


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20000
    out.mkdir(parents=True, exist_ok=True)
    e = emulator(rom)
    last = None
    run, shots, started = 0, 0, False
    for f in range(limit):
        e.run(1)
        st, ti, ni = e.w(STEP), e.w(TITLE), e.w(NAME)
        now = (st, ti, ni)
        if now != last:
            if st == 0 and ti == 0 and ni == 0 and (last is None or last[0] == 3 or not started):
                if last is not None and (last[0] == 3 or started):
                    run += 1
                    print(f"frame {f}: roll {run + 1} starts", flush=True)
                started = True
            if st == 2 and started:
                e.run(1)
                e.screenshot(out / f"r{run + 1}_t{ti}_n{ni}.png")
                shots += 1
                print(f"frame {f}: rest, title {ti} name {ni}", flush=True)
                if run >= 1:
                    break
            if st == 3 and (last is None or last[0] != 3):
                print(f"frame {f}: roll {run + 1} ends (step 3)", flush=True)
                e.screenshot(out / f"r{run + 1}_end.png")
            last = now
        if f % 600 == 0:
            lowload.breathe()
        if f == 3000:
            e.screenshot(out / "frame3000.png")
    print(f"{shots} screenshots in {out}")


if __name__ == "__main__":
    main()
