"""Whole games of the scripted bot (bot.py) against the computer, in the harness (2026-10-31). Each game starts from
bot_start.state (bot_states.py) with its own random seed; START is tapped through the screens between periods. Per
game: the score, shots on goal, each goal (whose, the period and clock, and for the bot's the play it came from: a
deke or slapshot released within 120 frames before, else "other"), and the bot's plays (deke starts, swings, shots,
slapshots, pucks lost and where). Gentle mode, one process; resumable.
NHL94_BOT_VS="A,B" plays the bot against itself (version A against B on pad 2, the
sides swapped every other game, each seed twice). Counts penalties, PIM and power plays. NHL94_BOT_VERSION=1 for the first version; NHL94_BOT_LOG=1 keeps the bot's whole log (each game's "log"). python bot_run.py RUN GAMES [minutes]   -> paths.RUNS / RUN / bot_games.jsonl"""
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
VERSION = int(os.environ.get("NHL94_BOT_VERSION") or 67)     # bot.py's versions (the default 67 since 2026-11-12; 63, 61, 59, 57, 55, 54, 51 that day, 32 before)


STATS = (0xC6CE, 0xCA32)                       # team stat blocks: +$02 PP goals, +$04 power plays, +$06 penalties, +$08 PIM
DELAYED, PENALTY_LIST = 0x26, 0xC5DC              # stat-block byte $FF while the team has a delayed penalty
                                                 # coming; the penalty summary (PROJECT_NOTES "Penalties")
C2PLAYER, CONT2TEAM = 0xC322, 0xC32A             # pad 2's skater (c2playernum) and team (cont2team, 2 = Away)


def play(e, start, seed, frames_out=None, home=None, away=None):
    """home / away: bot versions (away None: the computer plays Away). With a bot away it plays on pad 2."""
    e.unserialize(start)
    e.setl(0xD066, seed)
    bot = Bot(0, home or VERSION)
    bot2 = None
    if away:
        bot2 = Bot(1, away)
        e.setw(CONT2TEAM, 2)
        k = next(k for k in range(6, 12) if e.b(0xB04A + k * 0x80 + 0x35) == 4)    # the centre
        e.setb(0xB04A + k * 0x80 + 0x62, e.b(0xB04A + k * 0x80 + 0x62) | 8)
        e.setw(C2PLAYER, k)
    goals, last_score, f, quiet, still, clock = [], (0, 0), 0, 0, 0, None
    # each penalty call (2026-11-01): who was called (the bot's own skater or a computer-run teammate) and what he
    # and his pad were doing. A call is taken as it appears in the summary (after the whistle); the foul's moment is
    # the fouled team's delayed flag going up when there was one, else the last 3 s before the call
    calls, flag_at, ring, was_up, ticked = [], [None, None], [], [False, False], 0
    R = lambda k: 0xB04A + k * 0x80

    def snap(hold, hold2):
        return dict(f=f, person=[bool(e.b(R(k) + 0x62) & 8) for k in range(12)], anim=[e.w(R(k) + 0x58) for k in range(12)],
                    roster=[e.b(R(k) + 0x66) for k in range(12)], pads=(tuple(hold), tuple(hold2)),
                    carrier=e.b(R(14) + 0x61) if e.b(R(14) + 0x60) == 0 else None)
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
        n_log = len(bot.log)
        hold = bot.step(e)
        for x in bot.log[n_log:]:                   # the emulator's own frame (bot_record.py's count when it records)
            x["ef"] = getattr(e, "frame_no", f)
        hold2 = bot2.step(e) if bot2 else []
        e.run(1, hold=hold, hold2=hold2)
        ring = (ring + [snap(hold, hold2)])[-900:]
        if still == 0:
            ticked = f                                     # the clock last moved (an immediate whistle stops it)
        for t, b in enumerate(STATS):
            up = e.b(b + DELAYED) == 0xFF
            if up and not was_up[t]:
                flag_at[t] = ring[-60:]                     # team t was fouled: the second before
            elif flag_at[t] is not None and f - flag_at[t][-1]["f"] > 1800:
                flag_at[t] = None
            was_up[t] = up
        n = e.w(PENALTY_LIST) // 4
        while len(calls) < min(n, 60):
            at = PENALTY_LIST + 2 + 4 * len(calls)
            code = e.b(at + 2)
            team, idx = code >> 7, e.b(at + 3)
            window, flagged = (flag_at[1 - team], True) if flag_at[1 - team] else (
                [w for w in ring if ticked - 60 <= w["f"] <= ticked + 30] or ring[-60:], False)
            flag_at[1 - team] = None
            ks = [k for k in range(team * 6, team * 6 + 6) if window[-1]["roster"][k] == idx]
            c = dict(team=team, code=code & 0x7F, idx=idx, f=f, flagged=flagged)
            if ks:
                k = ks[0]
                c.update(rec=k, person=any(w["person"][k] for w in window),
                         anims=sorted({w["anim"][k] for w in window}),
                         pad=sorted({x for w in window if w["person"][k] for x in w["pads"][team]}),
                         had_puck=any(w["carrier"] == k for w in window))
            calls.append(c)
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
                home=home or VERSION, away=away or "cpu",
                penalties=[e.w(b + 6) for b in STATS], pim=[e.w(b + 8) for b in STATS],
                power_plays=[e.w(b + 4) for b in STATS], pp_goals=[e.w(b + 2) for b in STATS],
                events=dict(ev), lost=dict(lost), shot_kinds=dict(Counter(x["kind"] for x in bot.log if x["ev"] == "shot"),
                                                                  **{"one-timer": sum(x["ev"] == "strike" for x in bot.log)}),
                calls=calls, deke_starts=[(x["ax"], x["ay"], x["v"], x["hand"]) for x in bot.log if x["ev"] == "deke start"],
                **({"log": bot.log} if os.environ.get("NHL94_BOT_LOG") else {}))


def main():
    run, games = sys.argv[1], int(sys.argv[2])
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    gentle()
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    path = out / "bot_games.jsonl"
    done = {(json.loads(l)["seed"], json.loads(l).get("home") if os.environ.get("NHL94_BOT_VS") else None)
            for l in open(path)} if path.exists() else set()
    e = Emu(RETAIL)
    start = (WORK / "bot_start.state").read_bytes()
    t0 = time.time()
    vs = os.environ.get("NHL94_BOT_VS")        # "A,B": the bot against itself, version A against B, the sides
    for g in range(games):                     # swapped every other game (the same seed twice)
        seed = 0x9E3779B1 * (g // 2 + 1 if vs else g + 1) & 0xFFFFFFFF
        home = away = None
        if vs:
            a, b = (int(x) for x in vs.split(","))
            home, away = (a, b) if g % 2 == 0 else (b, a)
        if (seed, home) in done:
            continue
        if time.time() - t0 > minutes * 60:
            print("time up")
            break
        r = play(e, start, seed, home=home, away=away)
        with open(path, "a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(f"game {g + 1}: {r['score'][0]}-{r['score'][1]}, shots {r['shots']}, "
              f"goals {[x['play'] for x in r['goals'] if x['team'] == 0]}, {r['events']}, lost {r['lost']}", flush=True)


if __name__ == "__main__":
    main()
