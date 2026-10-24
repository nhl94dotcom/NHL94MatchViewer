"""The SNES xG model (tools/xg_snes.py) against one-timers played in the real game, strike by strike (as
ot_xg_check.py does for the Genesis): python ot_xg_check_snes.py [every] [moments] -> paths.RUNS / ot_xg_check_snes.jsonl
A sample of the one-timer study's set-ups (every `every`-th job of the full plan, default 14), `moments` moments a
timing (default 4), each of the nine aims (the d-pad held from the press: the aim index the model uses). At each
strike the state is read from the game - the puck's spot, the goalie's spot, facing, sprite frame and ratings, his
speed over the swing's frames - the strike is played out with SEEDS fresh seeds (the game's rate), and the model is
asked the same question as add_expected_goals asks it of a recorded one-timer (that aim, the puck's speed off the
stick). One process in gentle mode."""
import json
import math
import random
import sys
import zlib
from pathlib import Path

from lowload import breathe
from ot_harness import OneTimer
from ot_run import plan_jobs, TIMINGS
from paths import RUNS, SNES_ROM

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg_snes as XS  # noqa: E402

SEEDS, SAMPLES = 4, 200
FACING, FRAME = 0x1163, 0x0D97
WORK = (0x12C3, 0x12E3, 0x1303, 0x1343)        # weight, agility, speed, aidef (systems/snes.py OBJ_WORK)


def main():
    every = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    moments = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    ot = OneTimer("snes")
    s, e = ot.s, ot.e
    data = XS.RomData(SNES_ROM.read_bytes())      # the retail ROM the harness runs
    jobs = plan_jobs("full")[::every]
    out = RUNS / "ot_xg_check_snes.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    g = 2 * s.GOALIE
    print(f"{len(jobs)} set-ups x {len(TIMINGS)} timings x {moments} moments x 9 aims", flush=True)
    with open(out, "w") as f:
        for net, R, P in jobs:
            rnd = random.Random(zlib.crc32(f"xgcheck-snes,{net},{R},{P}".encode()))
            for timing in TIMINGS:
                for p in range(0, 32, 32 // moments):
                    ot.setup(net, P, R, p, rnd)
                    by = 2 + p % 4 if timing == "early" else 2 + (p * 5) % 9
                    press, info = ot.pass_to_press(timing, by=by)
                    if press is None:
                        continue
                    e.unserialize(press)
                    g0 = s.xy(s.GOALIE)
                    for aim in range(9):
                        pre, frames = ot.swing(press, aim)
                        if pre is None:
                            continue
                        ot.strike(pre, aim, rnd.getrandbits(32))
                        after = e.serialize()
                        px, py = s.xy(s.PUCK)
                        gx, gy = s.xy(s.GOALIE)
                        n = max(1, frames)
                        gvx, gvy = (gx - g0[0]) / n * 4096, (gy - g0[1]) / n * 4096
                        facing, frame = e.w(FACING + g) & 7, e.w(FRAME + g)
                        ratings = [e.w(a + g) for a in WORK]
                        sha = e.w(s.H.SHOTACC + 2 * 3)
                        speed = 0
                        for _ in range(10):                  # as the converter: the fastest over the next frames
                            vx, vy = s.v(s.PUCK)
                            speed = max(speed, math.hypot(vx, vy))
                            ot.run()
                        e.unserialize(after)
                        res = {"GOAL": 0, "SAVED": 0, "POST": 0, "MISSED": 0}
                        for _ in range(SEEDS):
                            ot.strike(pre, aim, rnd.getrandbits(32))
                            res[ot.play_out()] += 1
                            breathe()
                        ty = 264 if net == "top" else -264
                        tx, tz = XS.AIM[aim]
                        rng = random.Random(f"{net}{R}{P}{timing}{p}{aim}")
                        goals = 0
                        for _ in range(SAMPLES):
                            G = XS.Goalie(data, gx, gy, gvx, gvy, facing, frame, *ratings)
                            goals += XS.play_out(px, py, tx, ty, tz, max(1.0, speed / 136), sha, (sha + 1) / (sha + 16),
                                                 G, rng) == "goal"
                        breathe()
                        f.write(json.dumps({"net": net, "R": R, "P": P, "timing": timing, "p": p, "aim": aim,
                                            "puck": [px, py], "speed": round(speed), "goalie": [gx, gy, round(gvx), round(gvy)],
                                            "game": res, "model": goals / SAMPLES}) + "\n")
                        f.flush()
            print(net, R, P, flush=True)


if __name__ == "__main__":
    main()
