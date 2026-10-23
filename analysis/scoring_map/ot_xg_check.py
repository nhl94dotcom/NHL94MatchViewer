"""The Genesis xG model (tools/xg.py) against one-timers played in the real game, strike by strike:
python ot_xg_check.py [every] [moments] -> paths.RUNS / ot_xg_check.jsonl
A sample of the one-timer study's set-ups (every `every`-th job of the full plan, default 14: about 60 over both
nets), `moments` moments a timing (default 8, spread over the study's 32). At each strike: the goalie's position,
speed, ratings and sprite frame and the puck's spot and speed are read from the game, the strike is played out with
SEEDS random seeds (the game's rate for that strike), and the model is asked the same question from the same state as
add_expected_goals asks it of a recorded one-timer (auto-aim from his coming position, reach 12), also with its stick
and rebound options and without the position blur (the state here is exact). One process in gentle mode (it runs beside the study's chunks)."""
import json
import random
import sys
import zlib
from pathlib import Path

from lowload import breathe
from ot_harness import OneTimer, PASSER
from ot_run import plan_jobs, TIMINGS
from paths import RUNS

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg  # noqa: E402

SEEDS, SAMPLES = 8, 400
ROM = next((Path(__file__).resolve().parents[2] / "roms").glob("9438f5dd*.bin"), None)


def main():
    every = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    moments = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    ot = OneTimer("genesis")
    s, e = ot.s, ot.e
    rom = xg.GenesisRom(ROM.read_bytes()) if ROM else None
    jobs = plan_jobs("full")[::every]
    out = RUNS / "ot_xg_check.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"{len(jobs)} set-ups x {len(TIMINGS)} timings x {moments} moments", flush=True)
    with open(out, "w") as f:
        for net, R, P in jobs:
            rnd = random.Random(zlib.crc32(f"xgcheck,{net},{R},{P}".encode()))
            for timing in TIMINGS:
                for p in range(0, 32, 32 // moments):
                    ot.setup(net, P, R, p, rnd)
                    by = 2 + p % 4 if timing == "early" else 2 + (p * 5) % 9
                    press, info = ot.pass_to_press(timing, by=by)
                    if press is None:
                        continue
                    pre, frames = ot.swing(press, None)
                    if pre is None:
                        continue
                    # the strike frame: the state the model starts from
                    ot.strike(pre, None, rnd.getrandbits(32))
                    after = e.serialize()
                    g = s.rec(s.GOALIE)
                    px, py, pz = s.xy(s.PUCK) + (max(0, e.sw(s.rec(s.PUCK) + 0x18)),)
                    gx, gy = s.xy(s.GOALIE)
                    gvx, gvy = s.v(s.GOALIE)
                    ratings = [e.b(g + o) for o in (0x67, 0x68, 0x69, 0x6B, 0x6C)]
                    frame, facing, mirror = e.w(g + 6), e.b(g + 0x55), not e.b(g + 0x76) & 1
                    speed = 0
                    for _ in range(10):                      # as the converter: the fastest over the next frames
                        vx, vy = s.v(s.PUCK)
                        speed = max(speed, (vx * vx + vy * vy) ** 0.5)
                        ot.run()
                    e.unserialize(after)
                    # the game: the strike from fresh seeds
                    res = {"GOAL": 0, "SAVED": 0, "POST": 0, "MISSED": 0}
                    for _ in range(SEEDS):
                        ot.strike(pre, None, rnd.getrandbits(32))
                        res[ot.play_out()] += 1
                        breathe()
                    # the model, as add_expected_goals for a recorded one-timer
                    gl = 264 if net == "top" else -264
                    d = xg.auto_aim(px, py, gx + 8 * gvx / 4096, gy + 8 * gvy / 4096, gl)
                    tx, tz = xg.AIM[d]
                    sha = e.b(s.rec(3) + 0x6D)
                    model = {}
                    for name, stick, rebound, spread in (("plain", False, False, 4.0), ("exact", False, False, 0.0),
                                                         ("stick", True, True, 0.0)):
                        if stick and not rom:
                            continue
                        xg.GOALIE_SPREAD = spread                # the recordings' blur; none for an exact state
                        rng = random.Random(f"{net}{R}{P}{timing}{p}{name}")
                        goals = 0
                        for _ in range(SAMPLES):
                            G = xg.Goalie(gx, gy, gvx, gvy, *ratings[:4], rom=rom if stick else None,
                                          frame=frame if stick else None, facing=facing, mirror=mirror,
                                          puck_control=ratings[4])
                            goals += xg.play_out((px, py, pz), (tx, gl, tz), max(1.0, speed / 68), sha,
                                                 (sha + 1) / (sha + 16), G, 12, 0, rng, stick=stick,
                                                 rebound=rebound) == "goal"
                        model[name] = goals / SAMPLES
                        breathe()
                    f.write(json.dumps({"net": net, "R": R, "P": P, "timing": timing, "p": p, "puck": [px, py, pz],
                                        "speed": round(speed), "goalie": [gx, gy, gvx, gvy], "aim": d, "game": res,
                                        "model": model}) + "\n")
                    f.flush()
            print(net, R, P, flush=True)


if __name__ == "__main__":
    main()
