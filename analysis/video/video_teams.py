"""The two teams of each game found in the video archive (2026-10-24). The HUD font (video_hud.py) was learned from
games between two teams only, so other teams' letters read as nonsense; but each letter is drawn the same every time,
so the score box's six letter cells, thresholded, fall into a handful of exact pictures. `cells` takes a few frames
with the HUD from the middle of every game in the work folder's *.games.json; `label` names the games' teams with
letters.json (picture -> letter, labelled by eye from the pictures `cells` found) by the majority of those frames and
writes them into the games files as away_team / home_team (the box shows the away team on top). Gentle mode.
python analysis/video/video_teams.py cells <work folder> <recordings folder>
python analysis/video/video_teams.py label <work folder>"""
import json
import sys
from collections import Counter
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
import video_hud as VH  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

NAMES = [f"{r}{n}" for r in ("top", "bot") for n in (1, 2, 3)]


def key(c):
    return "".join(str(v) for v in np.asarray(c, np.uint8).ravel())


def cells(work, recordings):
    work, out = Path(work), []
    for f in sorted(work.glob("*.games.json")):
        gs = json.load(open(f))
        if not gs:
            continue
        c = av.open(str(Path(recordings) / (f.name[:-len(".games.json")] + ".mkv")))
        v = c.streams.video[0]
        for gi, g in enumerate(gs):
            got = 0
            for frac in (0.3, 0.5, 0.7, 0.4, 0.6, 0.8):
                if got >= 3:
                    break
                t = g["start_t"] + frac * (g["end_t"] - g["start_t"])
                c.seek(int(t / v.time_base), stream=v)
                fr = None
                for fr in c.decode(v):
                    if fr.time >= t:
                        break
                a = fr.to_ndarray(format="rgb24")
                if not VH.hud_shown(a):
                    continue
                got += 1
                out.append({"file": f.name, "game": gi, "cells": [key(VH.cell(a, n) > 0.5) for n in NAMES]})
                breathe()
        c.close()
    json.dump(out, open(work / "team_cells.json", "w"))
    print(len(out), "frames;", len({k for r in out for k in r["cells"]}), "different letter pictures")


def label(work):
    work = Path(work)
    letters = json.load(open(work / "letters.json"))
    votes = {}
    for r in json.load(open(work / "team_cells.json")):
        s = "".join(letters.get(k if isinstance(k, str) else key(k), "?") for k in r["cells"])
        votes.setdefault((r["file"], r["game"]), Counter())[(s[:3].strip("_"), s[3:].strip("_"))] += 1
    teams = Counter()
    for f in sorted(work.glob("*.games.json")):
        gs = json.load(open(f))
        for gi, g in enumerate(gs):
            v = votes.get((f.name, gi))
            if v:
                g["away_team"], g["home_team"] = v.most_common(1)[0][0]
            teams[g["away_team"]] += 1
            teams[g["home_team"]] += 1
        f.write_text(json.dumps(gs, indent=1))
    print(dict(teams.most_common()))


if __name__ == "__main__":
    gentle()
    if sys.argv[1] == "cells":
        cells(*sys.argv[2:4])
    else:
        label(sys.argv[2])
