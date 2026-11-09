"""Do the power-play songs (LeadSong, slots 1 and 4) play after a real penalty? (2026-11-09, for NOSE4Web: the code
suggests the power-play display's sf2pwrplay, sflags2 bit 5, blocks LeadSong.) A scratch copy of the scoring-map test
ROM with checkagr's roll forced to 0 ($13E70 `bsr.w randomd0` -> `moveq #0,d0` / `nop`), so the first foul is called
through the game's own path; penalties on (OptPen $D056 = 2). The home skater (record 2, pad 1) skates into the away
carrier (record 6) and pokes, as in gen_forum_options_test's bcheck; then play runs on with no input (or with UP held
on alternate runs, so the home skater goes for the loose puck and the delayed penalty is whistled) for up to 3,000
frames: every change of sflags2's high byte ($C2EE: bit 5 sf2pwrplay, bit 6 sf2pwrtm), the two tmap counts, the
penalty counts and each song pick (SongNum $D6C8 written $7FFF after each, with SongIndex $D6CC).

python gen_leadsong_check.py OUT"""
import json
import sys
from pathlib import Path

import harness as H
import lowload
from gen_forum_options_test import build
from paths import ROM

SONGNUM, SONGIDX, SF2 = 0xD6C8, 0xD6CC, 0xC2EE
TMAP_H, TMAP_A = 0xC6CE + 0x24, 0xCA32 + 0x24


def run(h, seed, hold_up, log):
    e = h.e
    e.unserialize(h.base)
    e.setw(0xD056, 2)

    def park():
        for k in range(12):
            if k not in (2, 6, H.GOALIE):
                e.setw(H.rec(k), -100 + 18 * k)
                e.setw(H.rec(k) + 0x14, h.park_y)
                for off in (0x28, 0x2A, 0x2C):
                    e.setw(H.rec(k) + off, 0)
    for _ in range(30):
        park()
        for k, (x, y) in ((2, (0, 0)), (6, (0, 30))):
            e.setw(H.rec(k), x)
            e.setw(H.rec(k) + 0x14, y)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(H.rec(k) + off, 0)
        e.setb(H.rec(2) + 0x55, 0)
        e.setb(H.rec(6) + 0x55, 0)
        e.setw(H.PUCKC, 6)
        e.run(1)
    e.setl(0xD066, seed)
    e.setw(SONGNUM, 0x7FFF)
    last = None
    for f in range(3000):
        held = ["UP"] if (f < 70 or hold_up) else []
        if 5 <= f < 8:
            held = held + ["B"]
        if f < 70:
            park()
        e.run(1, hold=held)
        st = (e.b(SF2), e.w(TMAP_H), e.w(TMAP_A), e.w(0xC6CE + 6), e.w(0xCA32 + 6))
        song = e.w(SONGNUM)
        if st != last or song != 0x7FFF:
            log.append(dict(frame=f, sflags2_hi=f"{st[0]:08b}", tmap=[st[1], st[2]], pens=[st[3], st[4]],
                            clock=e.w(0xC468), song=None if song == 0x7FFF else hex(song),
                            slot=e.w(SONGIDX) if song != 0x7FFF else None))
            if song != 0x7FFF:
                e.setw(SONGNUM, 0x7FFF)
            last = st
        if f % 120 == 0:
            lowload.breathe()


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    rom = build(ROM, out, "checkagr_always", [(0x13E70, "6100d214", "70004e71")])
    h = H.Harness(rom=rom)
    res = {}
    for seed, up in ((0x1234, True), (0x5678, False), (0x9ABC, True)):
        log = []
        run(h, seed, up, log)
        res[f"{seed:04x}{'_up' if up else ''}"] = log
        print(f"seed {seed:04x} up={up}")
        for x in log:
            print("  ", x, flush=True)
    (out / "leadsong.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
