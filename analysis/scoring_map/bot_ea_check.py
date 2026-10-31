"""The EA Special as bot.py (version 7) plays it, from a standing start on its line (2026-10-31): the bot's skater
(record 2) starts LEAD frames back along the top net's EA line (bot.EA: a right-hander from his left; a left-hander
mirrored), moving along it at 1.7 a frame, Shot Power 20 / Shot Accuracy 15 (the EA runs' best was Power 3 of 6,
about 14), each hand, NHL94_DEKE_MOMENTS moments (default 16). Modes: "park" keeps every other skater away (the EA
runs' way), "free" leaves everyone on the ice. Counts goals (the first shot or the follow-up) within 150 frames of
the first shot. Modes "wingpark" / "wing": from the neutral zone instead (105 to his side, 20 up the ice, skating up the wing at 1.8; NHL94_EA_START="x,y,speed"),
version 8's approach (bot.EA_TUNE). python bot_ea_check.py park|free|wingpark|wing [LEAD] [shp]"""
import os
import random
import sys

from bot import Bot, EA, EA_SPEED
from harness import Harness, rec, SHOOTER, SCORE_HOME
from paths import WORK

MOMENTS = int(os.environ.get("NHL94_DEKE_MOMENTS") or 16)
START = tuple(map(float, (os.environ.get("NHL94_EA_START") or "-105,20,1.8").split(",")))   # "wing": x, y, speed up


def main():
    mode = sys.argv[1]
    lead = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    shp = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    h = Harness(rom=WORK / "nhl94_retail.bin", state=WORK / "bot_start.state", top=True)
    e = h.e
    (rx, ry), (ux, uy) = EA[1]["R"], EA[1]["u"]
    res = {}
    for hand in ("L", "R"):
        mx = 1 if hand == "R" else -1
        g = n = follow = 0
        rel = []
        for p in range(MOMENTS):
            x0, y0 = rx - lead * EA_SPEED * ux, ry - lead * EA_SPEED * uy
            if mode.startswith("wing"):             # "wing": from the neutral zone, up the wing at 1.8
                x0, y0 = START[:2]
            h.setup(round(mx * x0), round(y0), settle=80 + (p * 7) % 15, clock=290 - p)
            e.setb(rec(SHOOTER) + 0x6C, shp)
            e.setb(rec(SHOOTER) + 0x6D, 15)
            b0, a0 = e.b(rec(SHOOTER) + 0x76), e.b(rec(SHOOTER) + 4)
            e.setb(rec(SHOOTER) + 0x76, (b0 | 1) if hand == "L" else (b0 & ~1))
            e.setb(rec(SHOOTER) + 4, (a0 & ~8) if hand == "L" else (a0 | 8))
            e.setb(rec(SHOOTER) + 0x55, 1 if hand == "R" else 7)
            vx0, vy0 = (0, START[2]) if mode.startswith("wing") else (EA_SPEED * ux, EA_SPEED * uy)
            e.setw(rec(SHOOTER) + 0x28, round(mx * vx0 * 4096) & 0xFFFF)
            e.setw(rec(SHOOTER) + 0x2A, round(vy0 * 4096) & 0xFFFF)
            if mode.startswith("wing"):
                e.setb(rec(SHOOTER) + 0x55, 0)
            e.setl(0xD066, random.Random(p).getrandbits(32))
            bot = Bot(0, int(os.environ.get("NHL94_BOT_VERSION") or 7))
            s0, shot = e.w(SCORE_HOME), None
            for f in range(260):
                if mode in ("park", "wingpark"):
                    h.park(keep_shooter=True)
                e.run(1, hold=bot.step(e))
                if shot is None and any(x["ev"] == "shot" for x in bot.log):
                    shot = f
                if e.w(SCORE_HOME) != s0:
                    g += 1
                    follow += any(x.get("kind") == "ea follow" for x in bot.log)
                    break
                if shot is not None and f > shot + 150:
                    break
            n += 1
            st = next((x for x in bot.log if x["ev"] == "ea start"), None)
            rel.append(st and (st["off"], round(st["v"], 1)))
            if os.environ.get("NHL94_EA_VERBOSE"):
                print(hand, p, [(x["f"], x["ev"], x.get("kind", x.get("phase", ""))) for x in bot.log][:8])
        res[hand] = (g, n, follow)
        print(hand, "release (off the line, speed):", rel)
    print(mode, lead, shp, "goals / tries / of them follow-ups:", res)


if __name__ == "__main__":
    main()
