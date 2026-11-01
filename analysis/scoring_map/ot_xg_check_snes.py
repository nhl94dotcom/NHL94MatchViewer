"""The SNES xG model (tools/xg_snes.py) against one-timers played in the real game, strike by strike (as
ot_xg_check.py does for the Genesis): python ot_xg_check_snes.py [every] [moments] -> paths.RUNS / ot_xg_check_snes.jsonl
A sample of the one-timer study's set-ups (every `every`-th job of the full plan, default 14), `moments` moments a
timing (default 4), each of the nine aims (the d-pad held from the press: the aim index the model uses). At each
strike the state is read from the game - the puck's spot, the goalie's spot, facing, sprite frame and ratings, his
speed over the swing's frames - the strike is played out with SEEDS fresh seeds (the game's rate), and the model is
asked the same question as add_expected_goals asks it of a recorded one-timer (that aim, the puck's speed off the
stick). One process in gentle mode.

2026-10-31 (SNES_SHOOTING 4.7, the recorded-shots gap): the one-timer is the game's own shot at a goalie still moving
across after the pass, the case the standing and deke calibrations didn't cover. Each strike is now asked of the model
four ways: its goalie as before or gliding in a save move (xg_snes.GLIDE_IN_SAVE), each fresh (as the converter starts
him) or with his inner state read from the game's RAM at the strike (snes_goalie_state.internals). With a RUN name the
output goes to paths.RUNS / RUN / ot_xg_check_snes.jsonl and a rerun resumes (set-ups already done are skipped);
`minutes` stops it after that long.
python ot_xg_check_snes.py [every] [moments] [RUN] [minutes]"""
import json
import math
import random
import sys
import zlib
from pathlib import Path

from lowload import breathe, gentle
from ot_harness import OneTimer
from ot_run import plan_jobs, TIMINGS
from paths import RUNS, SNES_ROM

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg_snes as XS  # noqa: E402
from snes_goalie_state import internals as read_internals  # noqa: E402
import time  # noqa: E402

SEEDS, SAMPLES = 4, 200
# the model variants asked: (glide in a save, the goalie's inner state, the game's save-side rules); env
# NHL94_OT_VARIANTS="choice" for the save-choice test (2026-11-01: old / glide, each with and without the side rules)
_V = __import__("os").environ.get("NHL94_OT_VARIANTS")
VARIANTS = ([(False, False, False), (True, False, False), (False, False, True), (True, False, True)] if _V == "choice" else
            [(False, False, False), (True, False, False), (False, False, "launch"), (True, False, "launch")]
            if _V == "launch" else
            [(False, False, False), (False, True, False), (True, False, False), (True, True, False)])
# "launch" (2026-11-01, snes_goalie_path.py: on the game's own puck path the gliding goalie stops 76% of one-timers from
# 120-200 out, the game 68%): the model also given the puck's launch as the game struck it (no aim, no scatter)
FACING, FRAME = 0x1163, 0x0D97
WORK = (0x12C3, 0x12E3, 0x1303, 0x1343)        # weight, agility, speed, aidef (systems/snes.py OBJ_WORK)


def main():
    gentle()
    every = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    moments = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    ot = OneTimer("snes")
    s, e = ot.s, ot.e
    data = XS.RomData(SNES_ROM.read_bytes())      # the retail ROM the harness runs
    jobs = plan_jobs("full")[::every]
    run = sys.argv[3] if len(sys.argv) > 3 else None
    minutes = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
    out = RUNS / run / "ot_xg_check_snes.jsonl" if run else RUNS / "ot_xg_check_snes.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if run and out.exists():
        done = {(r["net"], r["R"], r["P"]) for r in map(json.loads, open(out))}
    t0 = time.time()
    g = 2 * s.GOALIE
    print(f"{len(jobs)} set-ups x {len(TIMINGS)} timings x {moments} moments x 9 aims", flush=True)
    with open(out, "a" if run else "w") as f:
        for net, R, P in jobs:
            if (net, R, P) in done:
                continue
            if time.time() - t0 > minutes * 60:
                print("time up", flush=True)
                break
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
                        launch = (s.v(s.PUCK)[0], s.v(s.PUCK)[1], e.w(s.H.PUCKVZ) - (0x10000 if e.w(s.H.PUCKVZ) & 0x8000 else 0))
                        px, py = s.xy(s.PUCK)
                        gx, gy = s.xy(s.GOALIE)
                        n = max(1, frames)
                        gvx, gvy = (gx - g0[0]) / n * 4096, (gy - g0[1]) / n * 4096
                        facing, frame = e.w(FACING + g) & 7, e.w(FRAME + g)
                        state = read_internals(bytes(e.ram[:0x4000]), s.GOALIE, data, net == "top")
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
                        models = {}
                        for glide, use, choice in VARIANTS:
                            if True:
                                XS.GLIDE_IN_SAVE, XS.SAVE_CHOICE = glide, choice is True
                                rng = random.Random(f"{net}{R}{P}{timing}{p}{aim}")
                                goals = 0
                                for _ in range(SAMPLES):
                                    G = XS.Goalie(data, gx, gy, gvx, gvy, facing, frame, *ratings)
                                    if use:
                                        G.set_internals(**state)
                                    goals += XS.play_out(px, py, tx, ty, tz, max(1.0, speed / 136), sha,
                                                         (sha + 1) / (sha + 16), G, rng,
                                                         launch=launch if choice == "launch" else None) == "goal"
                                models[("glide" if glide else "old") + ("_state" if use else "") + ("_launch" if choice == "launch" else "_choice" if choice else "")] = goals / SAMPLES
                        XS.GLIDE_IN_SAVE = XS.SAVE_CHOICE = False
                        breathe()
                        f.write(json.dumps({"net": net, "R": R, "P": P, "timing": timing, "p": p, "aim": aim,
                                            "puck": [px, py], "speed": round(speed), "goalie": [gx, gy, round(gvx), round(gvy)],
                                            "game": res, "model": models["old"], "models": models,
                                            "state": state}) + "\n")
                        f.flush()
            print(net, R, P, flush=True)


if __name__ == "__main__":
    main()
