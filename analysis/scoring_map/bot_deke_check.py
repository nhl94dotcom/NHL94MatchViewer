"""The standing deke set-up (deke_run.py plan "best", deke2) played by bot.py's own inputs in the retail ROM
(2026-10-31): why the bot's dekes scored 16% in whole games against 82-96% standing. The bot's skater (record 2)
starts 45 to the attacker's left, 140 up the ice, moving (VX across, VY up the ice) units a frame, Shot Power 20,
Shot Accuracy 15, each hand, 16 moments; "park" keeps every other skater away as the deke runs did.
python bot_deke_check.py park|free VX VY [version]
Found: parked, entering at 0.5 / 2.1 (the runs' set-up) 27 of 32; 1.2 / 1.7 (diagonal, as the bot arrived in games)
11 of 32; 0.0 / 2.1 (straight up) 6 of 32; at 0.5 / 2.1 with the others free 14 of 32 (left-handers 14 of 16,
right-handers 0 of 16)."""
import random
import sys

from bot import Bot
from harness import Harness, rec, SHOOTER, PUCKC, SCORE_HOME
from paths import WORK


def main():
    park = sys.argv[1] == "park"
    vx, vy = float(sys.argv[2]), float(sys.argv[3])
    version = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    h = Harness(rom=WORK / "nhl94_retail.bin", state=WORK / "bot_start.state", top=True)
    e = h.e
    res = {}
    for hand in ("L", "R"):
        g = n = 0
        for p in range(16):
            h.setup(-45, 140, settle=80 + (p * 7) % 15, clock=290 - p)
            e.setb(rec(SHOOTER) + 0x6C, 20)
            e.setb(rec(SHOOTER) + 0x6D, 15)
            b0, a0 = e.b(rec(SHOOTER) + 0x76), e.b(rec(SHOOTER) + 4)
            e.setb(rec(SHOOTER) + 0x76, (b0 | 1) if hand == "L" else (b0 & ~1))
            e.setb(rec(SHOOTER) + 4, (a0 & ~8) if hand == "L" else (a0 | 8))
            e.setb(rec(SHOOTER) + 0x55, 1)
            e.setw(rec(SHOOTER) + 0x28, round(vx * 4096) & 0xFFFF)
            e.setw(rec(SHOOTER) + 0x2A, round(vy * 4096) & 0xFFFF)
            e.setl(0xD066, random.Random(p).getrandbits(32))
            bot = Bot(0, version)
            bot.phase, bot.t = "drive", 0
            s0, shot = e.w(SCORE_HOME), None
            for f in range(260):
                if park:
                    h.park(keep_shooter=shot is None)
                hold = bot.step(e) if e.w(PUCKC) == SHOOTER or bot.phase == "swing" else []
                e.run(1, hold=hold)
                if shot is None and any(x["ev"] == "shot" for x in bot.log):
                    shot = f
                if e.w(SCORE_HOME) != s0:
                    g += 1
                    break
                if shot is not None and f > shot + 120:
                    break
            n += 1
        res[hand] = (g, n)
    print("parked" if park else "others free", vx, vy, res)


if __name__ == "__main__":
    main()
