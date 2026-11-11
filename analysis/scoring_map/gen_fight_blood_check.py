"""Fights and head blood together (2026-11-11, for NOSE4Web: nhl94_fighting_blood.bin, CDL_Season_12_fighting_blood.bin).
gen_blood_check's run (injuries forced in a scratch copy: every fall of a puck carrier an injury; the blood frames
369-372 watched, screenshots of each injury), with every player's fighting rating (+$74) set to 14 before each frame
so fights come too, a fight's start (pf2fight, +$63 bit 0) counted and screenshots taken every 20 frames while one is
on (fight_NN_MM.png). Printed at the end: injuries (from gen_blood_check's own lines) and fights.

python gen_fight_blood_check.py ROM OUT [game|period]"""
import sys
from pathlib import Path

import emu

BASE, SZ = 0xB04A, 0x80
state = dict(fights=0, was=False, frame=0, shots=0)
_run = emu.Emu.run


def run(self, n=1, hold=(), *a, **k):
    for i in range(12):
        self.setb(BASE + SZ * i + 0x74, 14)
    r = _run(self, n, hold, *a, **k)
    state["frame"] += n
    try:
        fighting = any(self.b(BASE + SZ * i + 0x63) & 1 for i in range(12))
    except Exception:
        fighting = False
    if fighting and not state["was"]:
        state["fights"] += 1
        state["shots"] = 0
        print(f"fight {state['fights']} starts, frame {state['frame']}", flush=True)
    if fighting and state["frame"] % 20 < n and state["shots"] < 12 and OUT is not None:
        self.screenshot(OUT / f"fight_{state['fights']:02d}_{state['shots']:02d}.png")
        state["shots"] += 1
    state["was"] = fighting
    return r


OUT = None

if __name__ == "__main__":
    OUT = Path(sys.argv[2])
    OUT.mkdir(parents=True, exist_ok=True)
    emu.Emu.run = run
    import gen_blood_check
    gen_blood_check.main()
    print(f"fights: {state['fights']}")
