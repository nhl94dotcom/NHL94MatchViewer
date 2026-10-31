"""GIFs of the bot's plays (bot.py) in a bot_run.py game, replayed exactly from its seed: python bot_gif.py GAME KIND
[N] [OUT_DIR] makes one GIF for each of the first N plays of KIND (deke, wrist, slap) in game number GAME (1-based,
as bot_run numbers them): from 60 frames before the play started to 90 after its shot, every second frame, the
game's own picture, with the play's result (goal or not) in the file name."""
import sys
from pathlib import Path

from PIL import Image

from bot import Bot
from bot_run import RETAIL, SCORE, VERSION
from emu import Emu
from lowload import gentle
from paths import WORK

START = {"deke": "deke start", "wrist": "wrist start", "slap": "slap start", "one-timer": "pass start"}


def main():
    game, kind = int(sys.argv[1]), sys.argv[2]
    want = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    out = Path(sys.argv[4]) if len(sys.argv) > 4 else WORK / "runs" / "bot_gifs"
    out.mkdir(parents=True, exist_ok=True)
    gentle()
    e = Emu(RETAIL)
    seed = 0x9E3779B1 * game & 0xFFFFFFFF
    start = (WORK / "bot_start.state").read_bytes()
    # pass 1: find the plays' frames (the same loop as bot_run.play, kept short)
    plays = []
    for passno in (1, 2):
        e.unserialize(start)
        e.setl(0xD066, seed)
        bot, frames, f, still, clock, quiet = Bot(0, VERSION), [], 0, 0, None, 0
        cur, made = None, 0
        while f < 70000 and (passno == 1 and len(plays) < want or passno == 2 and made < len(plays)):
            f += 1
            c, per = e.w(0xC468), e.w(0xC466)
            still = still + 1 if (per, c) == clock else 0
            clock = (per, c)
            if e.b(0xFFF7) != 0:
                quiet += 1
                e.run(1, hold=(["START"] if quiet % 90 < 4 else []))
                continue
            quiet = 0
            if still > 500:
                e.run(4, hold=["START"])
                still = 0
                continue
            n0 = len(bot.log)
            hold = bot.step(e)
            s0 = e.w(SCORE[0])
            if passno == 2 and cur is None and any(p[0] - 60 <= bot.frame <= p[1] + 90 for p in plays):
                cur = next(p for p in plays if p[0] - 60 <= bot.frame <= p[1] + 90)
                frames = []
            if cur is not None and bot.frame % 2 == 0:
                e.held, e.held2 = {e.PAD[b] for b in hold}, set()
                e.screenshot(out / "_f.png")
                frames.append(Image.open(out / "_f.png").copy())
            else:
                e.run(1, hold=hold)
            if passno == 1:
                for x in bot.log[n0:]:
                    if x["ev"] == START[kind]:
                        cur = [x["f"], None, False]
                    if x["ev"] == "shot" and cur and x.get("kind") == kind:
                        cur[1] = x["f"]
                    if x["ev"] == "lost" and cur and cur[1] is None:
                        cur = None
                if cur and cur[1] is not None and bot.frame > cur[1] + 90:
                    plays.append(tuple(cur[:2]) + (cur[2],))
                    cur = None
                if cur and cur[1] is not None and e.w(SCORE[0]) != s0:
                    cur[2] = True
            elif cur is not None and bot.frame > cur[1] + 90:
                made += 1
                tag = "goal" if cur[2] else "no_goal"
                path = out / f"bot_g{game}_{kind}{made}_{tag}.gif"
                frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0)
                print(path)
                cur = None
    (out / "_f.png").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
