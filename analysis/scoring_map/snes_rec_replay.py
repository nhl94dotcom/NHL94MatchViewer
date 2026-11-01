"""The recorded SNES shots at a computer goalie replayed in the retail game (2026-10-31; SNES_SHOOTING 4.7): why the xG
model's goalie as the game moves him (xg_snes.GLIDE_IN_SAVE) is right on the game's own shots but 24% high on the
recorded ones. Each recorded shot (the match files in NHL94_HOME, default Documents\\NHL94 Viewer; read only) at a
computer goalie (the shot list's gctl), not blocked, with a launch the recording shows (xg.launched: the puck's
velocity over the 50 ms after the release), is placed in the SNES harness (snes_top.state, turned to the top net): the
goalie where the recording has him, at his speed, facing and working ratings, after the harness has let him set
against the puck there; the puck loose at its spot with that launch; every skater parked. The game plays it out
(MOMENTS settle lengths x SEEDS random seeds) and so does the model from the same state, given the same launch (no aim,
no scatter), with its goalie as before (glide off) and as the game moves him (glide on). Per shot: the recorded
result, whether a person took the goalie within 20 frames, the game's rate, the model's two values.
python snes_rec_replay.py RUN [minutes]   -> paths.RUNS / RUN / snes_rec_replay.jsonl   (gentle, resumable)"""
import json
import math
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg  # noqa: E402
import xg_snes as xs  # noqa: E402
from share_game import load_js_object  # noqa: E402

from lowload import breathe, gentle  # noqa: E402
from paths import RUNS, SNES_ROM, SNES_STATE_TOP  # noqa: E402
from snes_harness import (Harness, GOALIE, PUCK, PUCKC, PUCKZ, PUCKVZ, XVEL, YVEL, LEGSTR, LEGSPD, AIDEF,  # noqa: E402
                          SEED, o)

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
MOMENTS, SEEDS, SAMPLES = 4, 4, 200
FACING, WEIGHT = 0x1163, 0x12C3
K, FRAME_MS = 12, 1000 / 60


def shots():
    out = []
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season":
            continue
        try:
            m = json.loads(load_js_object(p))
        except (ValueError, OSError):
            continue
        if m.get("system") != "snes" or not m.get("work"):
            continue
        T, P = m["t"], m["pos"]
        rows = {}
        for r in m["work"]:
            rows.setdefault(r[1], []).append(r)
        for sh in m["shotList"]:
            if sh.get("gctl") != "cpu" or sh["result"] == "blocked" or sh["kind"] not in ("shot", "one-timer"):
                continue
            f, team = sh["f"], sh["team"]
            gk = next((k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if m["role"][f * K + k] == "0"), None)
            own = next((k for k in range(team * 6, team * 6 + 6) if m["role"][f * K + k] == "0"), None)
            if gk is None or own is None:
                continue
            launch = xg.launched(m, f)
            if launch is None:
                continue
            j0 = f
            while j0 > 0 and T[f] - T[j0 - 1] <= 100:
                j0 -= 1
            fr0 = max(1, (T[f] - T[j0]) / FRAME_MS)
            gx, gy = P[(f * K + gk) * 2], P[(f * K + gk) * 2 + 1]
            gvx = (gx - P[(j0 * K + gk) * 2]) / fr0 * 4096
            gvy = (gy - P[(j0 * K + gk) * 2 + 1]) / fr0 * 4096
            work = max((r for r in rows.get(gk, []) if r[0] <= f), key=lambda r: r[0], default=None)
            gw = work[2:] if work else [48, 10, 10, 11, 10, 0]
            took = False
            g = f
            while g < len(T) and T[g] - T[f] <= 20 * FRAME_MS:
                if (m["ctrl"][g] >> gk) & 1:
                    took = True
                    break
                g += 1
            r = 1 if P[(f * K + own) * 2 + 1] < 0 else -1     # turned so that the shot is at the top net
            px, py, pz = m["puck"][3 * f:3 * f + 3]
            out.append(dict(name=p.stem, f=f, result=sh["result"], took=took, sha=None,
                            puck=[r * px, r * py, max(0, pz)], launch=[r * launch[0], r * launch[1], launch[2]],
                            goalie=[r * gx, r * gy, r * gvx, r * gvy], facing=(int(m["facing"][f * K + gk]) + (0 if r > 0 else 4)) % 8,
                            frame=int(m["frame"][(f * K + gk) * 3:(f * K + gk) * 3 + 3], 16), gw=list(gw[:4])))
    return out


def model(s, data, glide):
    xs.GLIDE_IN_SAVE = glide
    xs.GOALIE_SPREAD = 0.0
    gx, gy, gvx, gvy = s["goalie"]
    rng = random.Random(1)
    goals = 0
    for _ in range(SAMPLES):
        G = xs.Goalie(data, gx, gy, gvx, gvy, s["facing"], s["frame"], *s["gw"])
        goals += xs.play_out(s["puck"][0], s["puck"][1], 0, 264, 0, 1.0, 10, 0.5, G, rng,
                             launch=tuple(s["launch"])) == "goal"
    return goals / SAMPLES


def game(h, s, j, seed):
    e = h.e
    gx, gy, gvx, gvy = s["goalie"]
    h.setup(round(s["puck"][0]), round(s["puck"][1]), settle=60 + 7 * j, seed=seed)
    h.put(GOALIE, round(gx), round(gy))                 # the goalie as recorded (after setting against the puck)
    e.setw(XVEL + o(GOALIE), round(gvx) & 0xFFFF)
    e.setw(YVEL + o(GOALIE), round(gvy) & 0xFFFF)
    e.setw(FACING + o(GOALIE), s["facing"])
    for a, v in zip((WEIGHT, LEGSTR, LEGSPD, AIDEF), s["gw"]):
        e.setw(a + o(GOALIE), v)
    h.put(PUCK, round(s["puck"][0]), round(s["puck"][1]))
    e.setw(XVEL + o(PUCK), round(s["launch"][0]) & 0xFFFF)
    e.setw(YVEL + o(PUCK), round(s["launch"][1]) & 0xFFFF)
    e.setw(PUCKZ, round(s["puck"][2]) & 0xFFFF)
    e.setw(PUCKVZ, round(s["launch"][2]) & 0xFFFF)
    e.setw(PUCKC, 0xFFFF)                               # loose: the shot is on its way
    e.setw(SEED, seed >> 16 or 1)
    e.setw(SEED + 2, seed & 0xFFFF or 1)
    goal, _ = h.decide(maxf=120)
    return goal


def main():
    run = sys.argv[1]
    minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    gentle()
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    path = out / "snes_rec_replay.jsonl"
    done = {(json.loads(l)["name"], json.loads(l)["f"]) for l in open(path)} if path.exists() else set()
    data = xs.RomData(SNES_ROM.read_bytes())
    h = Harness(state=SNES_STATE_TOP, top=True)
    t0 = time.time()
    todo = [s for s in shots() if (s["name"], s["f"]) not in done]
    print(len(todo), "shots to replay", flush=True)
    with open(path, "a") as fh:
        for s in todo:
            if time.time() - t0 > minutes * 60:
                print("time up")
                break
            rnd = random.Random(f"{s['name']}:{s['f']}")
            g = [game(h, s, j, rnd.getrandbits(32)) for j in range(MOMENTS) for _ in range(SEEDS)]
            s["game"] = sum(g) / len(g)
            s["model_old"] = model(s, data, False)
            s["model_glide"] = model(s, data, True)
            fh.write(json.dumps(s) + "\n")
            fh.flush()
            breathe()


if __name__ == "__main__":
    main()
