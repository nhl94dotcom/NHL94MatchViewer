"""Energy and skating speed on the SNES (2026-11-10, NOSE4Web's "energy from hits only": knockdowns 1365, holds 683,
skating and bursts free). From the code (skating/playeracc): the speed index = legspd x 16 x (energy / 2 + $800) >> 16
(no energy: half of full), MaxSpeed's entry its square; Auto (OptLine 2) reads energy as $1000.

In live play (snes_assist_stick_test.Game, the retail game states; line changes On, OptLine $34C6 = 1):
- `speed ROM OUT`: the pad-1 skater skating straight from a standstill for 150 frames, everyone else parked, his
  energy (tmpde $17EA, by pnum) held at $1000 and after 1, 2 and 3 knockdowns of 1365 (2731, 1366, 1), his working
  leg speed (legspd $1303) the median skater's and 15: the highest speed reached (|Xvel, Yvel|).
- `shift ROM OUT`: the same skater, energy $1000, never hit, skating up and down and pressing A (the burst) every 40
  frames for 1,500 frames (the median SNES shift, 60 game s), and a player of his team on the bench (tmpdst $1852 =
  $FFFE) put at $800: both energies at the end.

python snes_energy_speed_check.py speed ROM OUT | shift ROM OUT"""
import json
import math
import sys
from pathlib import Path

import lowload
from snes_assist_stick_test import Game, POSITION, PUCK, XVEL, YVEL

OPTLINE, TMPDE, TMPDST, LEGSPD, PNUM, PFTEAM, CLOCK = 0x34C6, 0x17EA, 0x1852, 0x1303, 0x12A3, 0x1503, 0x1632


def slot(G, k, table=TMPDE):
    return table + (0x34 if G.w(PFTEAM + 2 * k) else 0) + 2 * (G.w(PNUM + 2 * k) & 0xFF)


def start(G):
    G.e.unserialize(G.g.bases[0])
    G.setw(OPTLINE, 1)
    a, team, up = G.me()
    return a, team, up


def keep_others(G, a, up):
    G.park(a, up)
    G.put(PUCK, 100, -200 * up)
    G.setw(CLOCK, 300)


def speed(rom, out):
    G = Game(rom)
    a, team, up = start(G)
    sk = sorted(G.w(LEGSPD + 2 * k) for k in range(12) if G.w(POSITION + 2 * k) not in (0, 0xFFFF))
    avg = sk[len(sk) // 2]
    res = {"working leg speeds on the ice": sk, "average used": avg}
    for legspd in (avg, 15):
        for n, en in ((0, 0x1000), (1, 4096 - 1365), (2, 4096 - 2730), (3, 1)):
            a, team, up = start(G)
            G.put(a, 0, -180 * up)
            top = 0
            for f in range(150):
                keep_others(G, a, up)
                G.setw(LEGSPD + 2 * a, legspd)
                G.setw(slot(G, a), en)
                G.run(hold=["UP" if up > 0 else "DOWN"])
                vx, vy = G.sw(XVEL + 2 * a), G.sw(YVEL + 2 * a)
                top = max(top, math.hypot(vx, vy))
            idx = (legspd * 16 * (en // 2 + 0x800)) >> 16
            res[f"leg speed {legspd}, {n} knockdowns (energy {en})"] = {"top reached": round(top), "code: index": idx}
        lowload.breathe()
    (out / f"speed_{Path(rom).stem}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def shift(rom, out):
    G = Game(rom)
    a, team, up = start(G)
    G.setw(slot(G, a), 0x1000)
    base = TMPDST + (0x34 if team else 0)
    bench = next(s for s in range(26) if G.w(base + 2 * s) == 0xFFFE)
    G.setw(TMPDE + (0x34 if team else 0) + 2 * bench, 0x800)
    way, bursts = "UP", 0
    for f in range(1500):
        keep_others(G, a, up)
        y = G.sw(0x0DB7 + 2 * a)
        way = "DOWN" if y > 200 else "UP" if y < -200 else way
        press = f % 40 == 0
        bursts += press
        G.run(hold=[way] + (["A"] if press else []))
        if f % 500 == 499:
            lowload.breathe()
    res = {"rom": Path(rom).name, "A presses": bursts, "skater energy at the end": hex(G.w(slot(G, a))),
           "bench slot": bench, "bench energy $800 ->": hex(G.w(TMPDE + (0x34 if team else 0) + 2 * bench))}
    (out / f"shift_{Path(rom).stem}.json").write_text(json.dumps(res, indent=1))
    print(res)


def main():
    what, rom, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    {"speed": speed, "shift": shift}[what](rom, out)


if __name__ == "__main__":
    main()
