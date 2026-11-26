"""A calibrated xG for shots read from video (2026-11-26). The game's xG model is exact geometry: fed a video's
approximate spot, speed, aim and goalie it is right on average and off by 0.2 a shot (sd), 0.8 a team a game: as much
as the missed and false shots together. Here each call's xG is predicted from the video's own measurements
(swing_events.py test's READ_swingshots.json: the model's value from the video, the shot's distance and angle, speed,
kind, the goalie's place against the shot's line, whether he was read, the finder's confidence), fitted to the
recording's xG of the matched shots of the OTHER games (each game left out in turn), unmatched calls to 0.

Printed, per game and overall: each team's xG three ways (the recording's; the model's from the video; calibrated),
the errors, and whether the side ahead on xG is the recording's.

python xg_calib.py READ_swingshots.json [READ_swingshots.json ...]"""
import json
import math
import sys
from pathlib import Path

import numpy as np

import swing_events as SE

NAMES = ["model", "dist", "off_centre", "speed", "one_timer", "person", "goalie_person", "goalie_read", "goalie_off_line",
         "goalie_out", "confidence", "aimed_side"]


def feats(x):
    gl = x["v_gl"]
    sx, sy = x["v_spot"]
    dist = math.hypot(sx, gl - sy)
    g = x.get("v_goalie")
    read = bool(g) and x.get("v_gframe", 0) not in (0, None) and abs(g[1]) > 200 and (g[1] > 0) == (gl > 0)
    if read:
        t = (g[1] - sy) / (gl - sy) if gl != sy else 1.0
        off = abs(g[0] - (sx + (0 - sx) * t))                # the goalie off the line from the spot to the net's middle
        out = abs(gl) - abs(g[1])
    else:
        off, out = 12.0, 18.0
    return [x["video"], min(dist, 400.0), abs(sx), min(x["v_speed"], 30000) / 1000, float(x["kind"] == "one-timer"), float(x["v_human"]),
            float(x["v_gctl"]), float(read), min(off, 60.0), out, x["v_pr"], float(x["v_side"] != 0)]


def main():
    games = []
    for p in sys.argv[1:]:
        d = json.loads(Path(p).read_text())
        games.append((Path(p).parent.name + "/" + d["name"], d))
    rows = []
    for gi, (name, d) in enumerate(games):
        for x in d["per"]:
            if "v_spot" not in x:
                raise SystemExit(f"{name}: no video inputs in the file: run swing_events.py test again")
            rows.append((gi, x, feats(x), (x["rec"] or 0.0) if x["matched"] else 0.0))
    X = np.array([r[2] for r in rows])
    y = np.array([r[3] for r in rows])
    gidx = np.array([r[0] for r in rows])
    pred = np.zeros(len(rows))
    for gi in range(len(games)):
        tr = gidx != gi
        old = SE.FEATURES
        model = SE.fit(X[tr], y[tr], rounds=int(sys.argv and 60), rate=0.1)
        pred[gidx == gi] = SE.predict(model, X[gidx == gi])
    vid = X[:, 0]
    print(f"calls {len(rows)} (matched {sum(r[1]['matched'] for r in rows)}); a shot's error against the recording (matched; unmatched count as 0): "
          f"the model sd {np.std(vid - y):.3f}, mean abs {np.abs(vid - y).mean():.3f}; calibrated sd {np.std(pred - y):.3f}, mean abs {np.abs(pred - y).mean():.3f}")
    E = {"model": [], "calibrated": []}
    flips = {"model": 0, "calibrated": 0}
    clear = 0
    for gi, (name, d) in enumerate(games):
        rec = d["xg_rec"]
        sel = gidx == gi
        teams = np.array([r[1]["team"] for r in rows])[sel]
        tv = [float(vid[sel][teams == t].sum()) for t in (0, 1)]
        tc = [float(pred[sel][teams == t].sum()) for t in (0, 1)]
        for lab, tt in (("model", tv), ("calibrated", tc)):
            E[lab] += [tt[0] - rec[0], tt[1] - rec[1]]
        mr = rec[0] - rec[1]
        line = f"{name:22s} recorded {rec[0]:.2f} / {rec[1]:.2f} | model {tv[0]:.2f} / {tv[1]:.2f} | calibrated {tc[0]:.2f} / {tc[1]:.2f}"
        if abs(mr) >= 0.5:
            clear += 1
            for lab, tt in (("model", tv), ("calibrated", tc)):
                if (tt[0] - tt[1]) * mr < 0:
                    flips[lab] += 1
                    line += f" | {lab} FLIPS"
        else:
            line += " | level in the recording"
        print(line)
    for lab in E:
        e = np.array(E[lab])
        m = np.array(E[lab]).reshape(-1, 2)
        print(f"{lab}: a team's xG error mean {e.mean():+.2f}, sd {e.std():.2f}, mean abs {np.abs(e).mean():.2f}; the margin's error sd {np.std(m[:, 0] - m[:, 1]):.2f}; "
              f"the wrong side ahead in {flips[lab]} of the {clear} games the recording has 0.5 or more apart")
    use = np.zeros(len(NAMES))
    model = SE.fit(X, y, rounds=60, rate=0.1)
    for tree in model["trees"]:
        use[tree[0]] += 1
        for sub in tree[2:]:
            if sub[1] < 1e17:
                use[sub[0]] += 0.5
    print("splits by input (all games):", {NAMES[j]: float(use[j]) for j in np.argsort(-use) if use[j]})


if __name__ == "__main__":
    main()
