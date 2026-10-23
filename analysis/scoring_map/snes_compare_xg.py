"""The viewer's SNES xG model (tools/xg_snes.py play_out) for the SNES map's shots, against a set goalie at his spot
for that puck, with the map's goalie (Montreal: weight 48, Agility 8, Speed 8, aidef 7 working) and shooter:
python snes_compare_xg.py RUN -> paths.RUNS / RUN / snes_compare.json. The puck starts where it leaves the stick
(about 18 in front of the shooter), at the speed measured in the game (wrist 86, slapshot 173)."""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg_snes as X  # noqa: E402
from paths import RUNS, SNES_ROM  # noqa: E402

run = RUNS / sys.argv[1]
res = json.load(open(run / "snes_map.json"))
meta = res.pop("meta")
data = X.RomData(open(SNES_ROM, "rb").read())
PP = {"wrist": 86, "slap": 173}
out = []
for k, v in res.items():
    net, x, y = k.split(",")
    x, y = int(x), int(y)
    top = net == "top"
    sg = 1 if top else -1
    px, py = x, sg * (y + 18)
    gx, gy = X.set_spot(px, py, top)
    facing = X.vtoa(px - gx, py - gy)
    facing = 4 if facing == 8 and top else 0 if facing == 8 else facing
    frame = data.anim(0xE0FE, facing)[0][0]
    for kind in PP:
        for aim in range(9):
            c = v[f"{kind},{aim}"]
            if c["valid"] * 2 < meta["phases"]:
                continue
            tx, tz = X.AIM[aim]                    # shotsets: screen x at both ends
            rng = random.Random(f"{k}{kind}{aim}")
            n = 300
            goals = 0
            for _ in range(n):
                g = X.Goalie(data, gx, gy, 0, 0, facing, frame, 48, 8, 8, 7)
                g.randomise(rng)
                goals += X.play_out(px, py, tx, 264 * sg, tz, PP[kind], meta["sha"], (meta["sha"] + 1) / (meta["sha"] + 16),
                                    g, rng) == "goal"
            out.append(dict(net=net, kind=kind, x=x, y=y, aim=aim, game=c["g"] / c["n"], n=c["n"], model=goals / n))
json.dump(out, open(run / "snes_compare.json", "w"))
print(len(out))
