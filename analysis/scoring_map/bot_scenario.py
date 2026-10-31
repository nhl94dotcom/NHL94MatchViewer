"""The scripted bot played from real game situations (2026-10-31, docs/BOT_PLAN.md phase 1): each situation from
bot_situations.py (all 12 records and the puck from a moment in the user's recorded games, the attack turned up the
ice) is written into a live-play state of the retail ROM (bot_live.state: bot_start.state played on past the opening
faceoff, made on first use), the carrier given pad 1 (c1playernum $C320 and his pflags joystick bit), and the bot
plays on for up to FRAMES frames against the computer. Every version plays the same situations with the same random
seed, so versions compare pair by pair.
Per situation: the result (goal; held, the goalie keeping it 20 frames; lost, an opponent skater keeping it 20 frames;
stoppage; time, none of these), shots on goal, the frames it took, the bot's plays (its log's shot kinds).
python bot_scenario.py RUN VERSION[,VERSION...] [N] [minutes]   -> paths.RUNS / RUN / scen_<version>.jsonl"""
import json
import math
import os
import random
import sys
import time
from collections import Counter

from bot import Bot, rec, PUCKC
from emu import Emu
from lowload import breathe, gentle
from paths import RUNS, WORK

RETAIL = WORK / "nhl94_retail.bin"
FRAMES = int(os.environ.get("NHL94_SCEN_FRAMES") or 360)
C1PLAYER = 0xC320                  # c1playernum (ram94.asm): the record pad 1 controls
SCORE, SHOTS = (0xC6DA, 0xCA3E), (0xC6CE, 0xCA32)


def live_state(e):
    p = WORK / "bot_live.state"
    if p.exists():
        return p.read_bytes()
    e.unserialize((WORK / "bot_start.state").read_bytes())
    bot = Bot(0)
    for f in range(900):                         # past the faceoff (about 300 frames) into play
        e.run(1, hold=bot.step(e))
    assert e.b(0xFFF7) == 0 and e.w(0xC466) == 0
    p.write_bytes(e.serialize())
    return p.read_bytes()


def place(e, base, s, seed):
    e.unserialize(base)
    e.setw(0xC468, 250)                          # plenty of period left
    e.setl(0xD066, seed)
    slot = {}
    for k in range(12):
        slot[("us" if k < 6 else "them", str(e.b(rec(k) + 0x35)))] = k
    for side in ("us", "them"):
        for role, (x, y, vx, vy, face) in s[side].items():
            k = slot.get((side, role))
            if k is None:
                return None
            r = rec(k)
            e.setw(r, round(x) & 0xFFFF)
            e.setw(r + 2, 0)
            e.setw(r + 0x14, round(y) & 0xFFFF)
            e.setw(r + 0x16, 0)
            e.setw(r + 0x18, 0)
            e.setl(r + 0x1C, (round(x) & 0xFFFF) << 16)
            e.setl(r + 0x20, (round(y) & 0xFFFF) << 16)
            e.setw(r + 0x28, round(vx * 4096) & 0xFFFF)
            e.setw(r + 0x2A, round(vy * 4096) & 0xFFFF)
            e.setw(r + 0x2C, 0)
            e.setb(r + 0x55, face)
    carrier = slot[("us", s["carrier"])]
    for k in range(6):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setb(rec(carrier) + 0x62, e.b(rec(carrier) + 0x62) | 8)
    e.setw(C1PLAYER, carrier)
    e.setw(PUCKC, carrier)
    pr = rec(14)
    e.setw(pr, round(s["puck"][0]) & 0xFFFF)
    e.setw(pr + 0x14, round(s["puck"][1]) & 0xFFFF)
    e.setw(pr + 0x18, 0)
    return carrier


def play(e, base, s, seed, version):
    if place(e, base, s, seed) is None:
        return None
    bot = Bot(0, version)
    s0, sh0 = [e.w(a) for a in SCORE], [e.w(a) for a in SHOTS]
    res, theirs = "time", 0
    for f in range(FRAMES):
        e.run(1, hold=bot.step(e))
        sc = [e.w(a) for a in SCORE]
        if sc[0] != s0[0]:
            res = "goal"
            break
        if sc[1] != s0[1]:
            res = "against"
            break
        if e.b(0xFFF7) != 0:
            res = "stoppage"
            break
        own = e.w(PUCKC)
        if 6 <= own < 12:
            theirs += 1
            if theirs >= 20:
                res = "held" if e.b(rec(own) + 0x35) == 0 else "lost"
                break
        else:
            theirs = 0
        if f % 600 == 599:
            breathe()
    return dict(res=res, frames=f + 1, shots=e.w(SHOTS[0]) - sh0[0],
                plays=dict(Counter(x["kind"] for x in bot.log if x["ev"] == "shot")))


def main():
    run, versions = sys.argv[1], [int(v) for v in sys.argv[2].split(",")]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
    minutes = float(sys.argv[4]) if len(sys.argv) > 4 else 60
    gentle()
    sits = json.loads((WORK / "bot_situations.json").read_text())[:n]
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(RETAIL)
    base = live_state(e)
    t0 = time.time()
    for v in versions:
        path = out / f"scen_{v}.jsonl"
        done = {json.loads(l)["i"] for l in open(path)} if path.exists() else set()
        with open(path, "a") as fh:
            for i, s in enumerate(sits):
                if i in done:
                    continue
                if time.time() - t0 > minutes * 60:
                    print("time up")
                    return
                seed = random.Random(i).getrandbits(32)
                r = play(e, base, s, seed, v)
                if r is None:
                    continue
                r["i"] = i
                fh.write(json.dumps(r) + "\n")
                fh.flush()
        rows = [json.loads(l) for l in open(path)]
        c = Counter(r["res"] for r in rows)
        print(f"version {v}: {len(rows)} situations, goals {c['goal']} ({100 * c['goal'] / len(rows):.1f}%), "
              f"shots {sum(r['shots'] for r in rows)}, {dict(c)}", flush=True)


if __name__ == "__main__":
    main()
