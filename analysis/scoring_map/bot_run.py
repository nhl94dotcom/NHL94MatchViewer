"""Whole games of the scripted bot (bot.py) against the computer, in the harness (2026-10-31). Each game starts from
bot_start.state (bot_states.py) with its own random seed; START is tapped through the screens between periods. Per
game: the score, shots on goal, each goal (whose, the period and clock, and for the bot's the play it came from: a
deke or slapshot released within 120 frames before, else "other"), and the bot's plays (deke starts, swings, shots,
slapshots, pucks lost and where). Gentle mode, one process; resumable.
NHL94_BOT_VERSION=1 for the first version; NHL94_BOT_LOG=1 keeps the bot's whole log (each game's "log"). python bot_run.py RUN GAMES [minutes]   -> paths.RUNS / RUN / bot_games.jsonl"""
import json
import os
import sys
import time
from collections import Counter

from bot import Bot
from emu import Emu
from lowload import breathe, gentle
from paths import RUNS, WORK

RETAIL = WORK / "nhl94_retail.bin"
SCORE = (0xC6DA, 0xCA3E)
SHOTS = (0xC6CE, 0xCA32)
MAX_FRAMES = 70000
VERSION = int(os.environ.get("NHL94_BOT_VERSION") or 6)      # bot.py's versions (runs bot1-bot6 ran 1-6)


def play(e, start, seed, frames_out=None):
    e.unserialize(start)
    e.setl(0xD066, seed)
    bot = Bot(0, VERSION)
    goals, last_score, f, quiet, still, clock = [], (0, 0), 0, 0, 0, None
    while f < MAX_FRAMES:
        f += 1
        c, per = e.w(0xC468), e.w(0xC466)
        still = still + 1 if (per, c) == clock else 0       # frames the period and clock have stood still
        clock = (per, c)
        tied = e.w(SCORE[0]) == e.w(SCORE[1])
        if per >= 3 and not tied or c == 0 and still > 120 and (per >= 3 or per == 2 and not tied):
            break                                  # the game is over (regulation, or overtime)
        if e.b(0xFFF7) != 0:                        # a pause or a screen
            quiet += 1
            e.run(1, hold=(["START"] if quiet % 90 < 4 else []))
            continue
        quiet = 0
        if still > 500:                             # the intermission menu: play is flagged live but the clock
            e.run(4, hold=["START"])                # waits for START (a faceoff waits only about 300)
            still = 0
            continue
        hold = bot.step(e)
        e.run(1, hold=hold)
        score = (e.w(SCORE[0]), e.w(SCORE[1]))
        if score != last_score:
            team = 0 if score[0] != last_score[0] else 1
            play_ = "other"
            if team == 0:
                shot = next((ev for ev in reversed(bot.log) if ev["ev"] in ("shot", "strike")), None)
                if shot and bot.frame - shot["f"] <= 120:
                    play_ = "one-timer" if shot["ev"] == "strike" else shot["kind"]
            goals.append(dict(team=team, period=e.w(0xC466), clock=e.w(0xC468), play=play_, f=bot.frame))
            last_score = score
        if f % 600 == 0:
            breathe()
        if frames_out is not None:
            frames_out.append(f)
    ev = Counter(x["ev"] for x in bot.log)
    lost = Counter(x.get("phase") for x in bot.log if x["ev"] == "lost")
    return dict(seed=seed, frames=f, score=list(last_score), shots=[e.w(SHOTS[0]), e.w(SHOTS[1])], goals=goals,
                events=dict(ev), lost=dict(lost), shot_kinds=dict(Counter(x["kind"] for x in bot.log if x["ev"] == "shot"),
                                                                  **{"one-timer": sum(x["ev"] == "strike" for x in bot.log)}),
                deke_starts=[(x["ax"], x["ay"], x["v"], x["hand"]) for x in bot.log if x["ev"] == "deke start"],
                **({"log": bot.log} if os.environ.get("NHL94_BOT_LOG") else {}))


def main():
    run, games = sys.argv[1], int(sys.argv[2])
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    gentle()
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    path = out / "bot_games.jsonl"
    done = {json.loads(l)["seed"] for l in open(path)} if path.exists() else set()
    e = Emu(RETAIL)
    start = (WORK / "bot_start.state").read_bytes()
    t0 = time.time()
    for g in range(games):
        seed = 0x9E3779B1 * (g + 1) & 0xFFFFFFFF
        if seed in done:
            continue
        if time.time() - t0 > minutes * 60:
            print("time up")
            break
        r = play(e, start, seed)
        with open(path, "a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(f"game {g + 1}: {r['score'][0]}-{r['score'][1]}, shots {r['shots']}, "
              f"goals {[x['play'] for x in r['goals'] if x['team'] == 0]}, {r['events']}, lost {r['lost']}", flush=True)


if __name__ == "__main__":
    main()
