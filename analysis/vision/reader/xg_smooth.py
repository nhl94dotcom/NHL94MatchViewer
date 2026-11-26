"""A smooth xG for shots read from video (2026-11-26, after xg_calib.py: the game's exact-geometry xG can't be fed a
video's approximate inputs). Fitted on the RECORDED games' shots (their match files: thousands, with the exact xG
known), from inputs a video gives too and that a few pixels don't upset: the shot's distance and angle, its kind,
its speed, whose shot (a person's), and where the goalie stands against the shot's line.

  fit OUT.json [--skip PART ...]      the recorded Genesis games in <home>/matches (bot games and names with a --skip
                                      part left out): the model, and how it does on its own games
  test MODEL.json READ_swingshots.json ...   per game: each team's xG by the recording (exact), by this model on the
                                      recording's own shots (what smoothing alone costs), and by this model on the
                                      video's calls; the errors, and the side ahead

python xg_smooth.py fit OUT.json [--skip PART ...] | test MODEL.json READ_swingshots.json ..."""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

import swing_events as SE

NAMES = ["dist", "off_centre", "angle", "speed", "one_timer", "person", "goalie_person", "goalie_read", "goalie_off_line", "goalie_out"]
HOME = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents/NHL94 Viewer"))


def feats(sx, sy, gl, speed, one_timer, person, gperson, goalie):
    dist = math.hypot(sx, gl - sy)
    ang = abs(math.degrees(math.atan2(abs(sx), max(1e-6, abs(gl - sy)))))
    read = goalie is not None and abs(goalie[1]) > 200 and (goalie[1] > 0) == (gl > 0)
    if read:
        t = (goalie[1] - sy) / (gl - sy) if gl != sy else 1.0
        off = abs(goalie[0] - (sx - sx * t))
        out = abs(gl) - abs(goalie[1])
    else:
        off, out = 6.0, 19.0                                 # about the recorded shots' medians
    return [min(dist, 400.0), min(abs(sx), 150.0), ang, min(speed or 12000, 30000) / 1000, float(one_timer), float(person),
            float(gperson), float(read), min(off, 60.0), max(-10.0, min(out, 60.0))]


def recorded(m):
    """(features, exact xG, team) of each unblocked shot / one-timer with an xG in a match file."""
    out = []
    for s in m.get("shotList", []):
        if s.get("kind") not in ("shot", "one-timer") or s.get("team") not in (0, 1) or s.get("xg") is None or s.get("result") == "blocked":
            continue
        f, team = s["f"], s["team"]
        gl = 264 if SE._attacks_top_raw(m, f, team) else -264
        gk = next((q for q in range((1 - team) * 6, (1 - team) * 6 + 6) if m["role"][f * 12 + q] == "0"), None)
        g = SE.xy(m, f, gk) if gk is not None else None
        out.append((feats(s["x"], s["y"], gl, s.get("speed"), s["kind"] == "one-timer", bool(s.get("human")), s.get("gctl") == "human", g),
                    float(s["xg"]), team))
    return out


def load(path):
    s = Path(path).read_text()
    return json.loads(s[s.index("{"):s.rindex("}") + 1])


def fit(out, skip):
    X, y, games = [], [], 0
    for p in sorted((HOME / "matches").glob("20*.js")):
        if any(k in p.name for k in skip):
            continue
        m = load(p)
        if m.get("system") != "genesis" or m.get("bot"):
            continue
        r = recorded(m)
        if r:
            games += 1
            X += [a for a, _, _ in r]
            y += [b for _, b, _ in r]
    X, y = np.array(X), np.array(y)
    model = SE.fit(X, y, rounds=200, rate=0.08)
    pr = SE.predict(model, X)
    print(f"{games} games, {len(y)} shots; mean exact xG {y.mean():.3f}, model {pr.mean():.3f}; a shot's difference sd {np.std(pr - y):.3f}; "
          f"correlation {np.corrcoef(pr, y)[0, 1]:.2f}")
    use = np.zeros(len(NAMES))
    for tree in model["trees"]:
        use[tree[0]] += 1
    print("first splits by input:", {NAMES[j]: int(use[j]) for j in np.argsort(-use) if use[j]})
    model["features"] = NAMES
    Path(out).write_text(json.dumps(model))


def test(model_path, paths):
    model = json.loads(Path(model_path).read_text())
    E = {"exact model on the video (as now)": [], "smooth on the recording's shots": [], "smooth on the video": []}
    flips = {k: 0 for k in E}
    clear = 0
    for p in paths:
        d = json.loads(Path(p).read_text())
        name = Path(p).parent.name + "/" + d["name"]
        rec = d["xg_rec"]
        # the recording's own shots, smooth: the timeline's match file, the stretch the read covers (the per's frames)
        per = d["per"]
        vid_exact = [sum(x["video"] for x in per if x["team"] == t) for t in (0, 1)]
        Xv = np.array([feats(x["v_spot"][0], x["v_spot"][1], x["v_gl"], x["v_speed"], x["kind"] == "one-timer", x["v_human"], x["v_gctl"],
                             x["v_goalie"] if x.get("v_gframe") else None) for x in per])
        pv = SE.predict(model, Xv) if len(per) else np.zeros(0)
        vid_smooth = [float(pv[[x["team"] == t for x in per]].sum()) for t in (0, 1)]
        rs = d.get("rec_smooth")
        row = f"{name:22s} exact {rec[0]:.2f} / {rec[1]:.2f} | video, exact model {vid_exact[0]:.2f} / {vid_exact[1]:.2f} | video, smooth {vid_smooth[0]:.2f} / {vid_smooth[1]:.2f}"
        vals = {"exact model on the video (as now)": vid_exact, "smooth on the video": vid_smooth}
        if rs:
            vals["smooth on the recording's shots"] = rs
            row += f" | recording, smooth {rs[0]:.2f} / {rs[1]:.2f}"
        mr = rec[0] - rec[1]
        if abs(mr) >= 0.5:
            clear += 1
        for k, tt in vals.items():
            E[k] += [tt[0] - rec[0], tt[1] - rec[1]]
            if abs(mr) >= 0.5 and (tt[0] - tt[1]) * mr < 0:
                flips[k] += 1
                row += f" | FLIPS ({k.split(' on ')[0]}, {k.split(' on ')[1][:9]})"
        print(row)
    for k, e in E.items():
        if not e:
            continue
        e = np.array(e)
        mm = e.reshape(-1, 2)
        print(f"{k}: a team's error mean {e.mean():+.2f}, sd {e.std():.2f}, mean abs {np.abs(e).mean():.2f}; the margin's error sd {np.std(mm[:, 0] - mm[:, 1]):.2f}; "
              f"wrong side ahead in {flips[k]} of {clear}")


if __name__ == "__main__":
    if sys.argv[1] == "fit":
        fit(sys.argv[2], [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--skip"])
    else:
        test(sys.argv[2], sys.argv[3:])
