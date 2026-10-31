"""The standing deke set-up (deke_run.py plan "best", deke2) played by bot.py's own inputs in the retail ROM
(2026-10-31): why the bot's dekes scored 16% in whole games against 82-96% standing. The bot's skater (record 2)
starts 45 to the attacker's left, 140 up the ice, moving (VX across, VY up the ice) units a frame, Shot Power 20,
Shot Accuracy 15, each hand, 16 moments (NHL94_DEKE_MOMENTS). Modes: "park" keeps every other skater away and takes the shooter off
the ice once he has shot, as the deke runs did (harness.decide); "free" leaves everyone (the shooter coasts on);
"shooter" takes only the shooter off after his shot; "brake" leaves everyone, the shooter holding Down after it.
python bot_deke_check.py park|free|shooter|brake VX VY [version]
Found: parked, entering at 0.5 / 2.1 (the runs' set-up) 27 of 32; 1.2 / 1.7 (diagonal, as the bot arrived in games)
11 of 32; 0.0 / 2.1 (straight up) 6 of 32. With 48 tries a hand (version 4): park 38 / 48 (left / right),
free 40 / 4: with everyone on the ice a right-hander's turn is slower, and the runs' timing misses (bot.DEKE6, re-timed
with everyone on: STUDY_NOTES "A scripted bot")."""
import os
import random
import sys

from bot import Bot
from harness import Harness, rec, SHOOTER, PUCKC, SCORE_HOME
from paths import WORK

MOMENTS = int(os.environ.get("NHL94_DEKE_MOMENTS") or 16)


def main():
    mode = sys.argv[1]
    vx, vy = float(sys.argv[2]), float(sys.argv[3])
    version = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    h = Harness(rom=WORK / "nhl94_retail.bin", state=WORK / "bot_start.state", top=True)
    e = h.e
    res = {}
    for hand in ("L", "R"):
        g = n = 0
        for p in range(MOMENTS):
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
                if mode == "park":
                    h.park(keep_shooter=shot is None)
                elif mode == "shooter" and shot is not None:
                    e.setw(rec(SHOOTER), -100)              # off the ice, at the far end
                    e.setw(rec(SHOOTER) + 0x14, -230)
                    for off in (0x28, 0x2A, 0x2C):
                        e.setw(rec(SHOOTER) + off, 0)
                hold = bot.step(e) if e.w(PUCKC) == SHOOTER or bot.phase == "swing" else []
                if mode == "brake" and shot is not None:
                    hold = ["DOWN"]
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
    print(mode, vx, vy, version, res)


if __name__ == "__main__":
    main()
