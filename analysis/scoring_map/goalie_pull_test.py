"""NOSE4Web's goalie-pull fix (CPgoalie, logic94), played in the game (Genesis, 2026-11-08, the user approved running the
patched ROMs). In the third period with a minute or less left, the computer pulls its goalie when it has the puck in
its attacking half (ChkGoalies, every so often while the clock runs) and is behind by... the original's tests are
`bmi` (leading: no) and `cmp #2 / bne` (not exactly 2: no), so it pulls only when exactly two goals down. The fix
(bmi -> ble, bne -> bgt) pulls when one or two down.

From live play: the period set to the third, the clock to 50 seconds, the score to the deficit tried (the computer's
team, Away, behind by 0-3), an Away skater given the puck in his attacking half, then 300 frames of play: whether
Away's tmgoalie ($CA58) goes negative (no goalie: CPgoalie's st sets its first byte, $FF00).

python goalie_pull_test.py RUN ROM [seeds]   -> paths.RUNS / RUN / trials.jsonl
python goalie_pull_test.py report RUN [RUN]"""
import json
import random
import sys
from collections import defaultdict

from bot import rec, PUCKC
from bot_scenario import live_state, LIVE_STATES, CONT_TEAMS
from emu import Emu
from lowload import breathe, gentle
from paths import RUNS

PERIOD, CLOCK, SCORE_HOME, SCORE_AWAY, GOALIE_AWAY = 0xC466, 0xC468, 0xC6DA, 0xCA3E, 0xCA58


def trial(e, base, deficit, seed):
    e.unserialize(base)
    e.setl(0xD066, seed)
    e.setw(PERIOD, 2)
    e.setw(CLOCK, 50)
    e.setw(SCORE_HOME, 3 + deficit)
    e.setw(SCORE_AWAY, 3)
    e.setw(CONT_TEAMS[1], 0)                              # Away is the computer's
    k = next(k for k in range(6, 12) if e.b(rec(k) + 0x35) == 4)
    down = not e.b(rec(k) + 0x62) & 0x80                  # pfgoal clear: he attacks the bottom net
    y = -60 if down else 60
    for a, v in ((0, 0), (0x14, y)):
        e.setw(rec(k) + a, v & 0xFFFF)
        e.setw(rec(14) + a, v & 0xFFFF)
    e.setw(rec(k) + 0x28, 0)
    e.setw(rec(k) + 0x2A, 0)
    e.setw(PUCKC, k)
    for f in range(300):
        e.run(1)
        if e.w(GOALIE_AWAY) & 0x8000:                     # st tmgoalie: its first byte $FF (the word $FF00)
            return dict(pulled=True, frame=f)
    return dict(pulled=False)


def main():
    run, rom = sys.argv[1], sys.argv[2]
    seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    gentle()
    e = Emu(rom)
    bases = [live_state(e, j) for j in range(LIVE_STATES)]
    with open(out / "trials.jsonl", "w") as fh:
        for s in range(seeds):
            for b, base in enumerate(bases):
                for deficit in range(4):
                    r = trial(e, base, deficit, random.Random(s * 31 + b).getrandbits(32))
                    r.update(deficit=deficit, base=b, seed=s)
                    fh.write(json.dumps(r) + "\n")
                    breathe()
    print("done", flush=True)


def report(runs):
    for run in runs:
        rows = [json.loads(l) for l in open(RUNS / run / "trials.jsonl")]
        by = defaultdict(list)
        for r in rows:
            by[r["deficit"]].append(r["pulled"])
        print(f"{run}: " + ", ".join(f"{d} down: pulled {sum(v)} of {len(v)}" for d, v in sorted(by.items())))


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2:])
    else:
        main()
