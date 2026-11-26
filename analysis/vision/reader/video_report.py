"""A game's report from its video alone (2026-11-26): no recording needed. The read (run_reader.py's rows, the star
pass merged in) fills a blank match made from the ROM (pseudo_match.blank: one sample a video frame), the converter's
analysis runs on it, and the measures that held up against recordings are printed for the two teams: goals (the
score box), possession, attacking-zone time, passes and their completion, pucks lost, hits, zone entries. Shots are
the swing finder's calls: a count to within a few (about four in five found, one call in eight not a shot); expected
goals are left out (off by 1 a team a game, the wrong side ahead in one game in four: VIEWER_NOTES).

HOME / AWAY: the teams' abbreviations as the score box shows them (or team numbers).
NHL94_INV_ROM the game's ROM, NHL94_INV_MAPS the frame maps learnt from recorded games (pseudo_maps*.json),
NHL94_SWING_MODEL the shot model (default: the work folder's swing/model_all9l.json).

python video_report.py READ.json HOME AWAY [OUT.json]"""
import json
import os
import sys
from pathlib import Path

import numpy as np

V = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(V / "analysis/vision"))
sys.path.insert(0, str(V / "tools"))
import pseudo_match as PM  # noqa: E402
import swing_events as SE  # noqa: E402

BLUE = 88


def calls(model, pm):
    """The swing finder's shots on a match with no recording: (release sample, record, confidence)."""
    sw = SE.swings(pm)
    if not sw:
        return []
    pr = SE.predict(model, np.array([SE.features(pm, i, k) for i, k in sw]))
    found = []
    for (i, k), p in zip(sw, pr):
        if p < 0.5:
            continue
        r = SE.release(pm, i, k)
        if any(k2 == k and abs(r2 - r) <= 30 for r2, k2, _ in found):
            continue
        found.append((r, k, float(p)))
    return found


def report(read_path, home, away, rom, maps_path, model_path, fps=60.0):
    rows = json.loads(Path(read_path).read_text())
    fis = [r["fi"] for r in rows]
    first, n = min(fis), max(fis) - min(fis) + 1
    mp = json.loads(Path(maps_path).read_text())
    maps = dict(anim={int(k): v for k, v in mp["anim"].items()}, facing={int(k): v for k, v in mp["facing"].items()}, goalie=set(mp["goalie"]))
    blank = PM.blank(rom, home, away, n, fps, Path(read_path).stem)
    pm = PM.build(blank, np.arange(first, first + n, dtype=float), rows, maps, 0, n)
    pm["frame"] = "".join(pm["frame"]) if not isinstance(pm["frame"], str) else pm["frame"]
    shots = calls(json.loads(Path(model_path).read_text()), pm)
    pm = PM.analyse(pm, str(rom))
    live = [i for i in range(n) if pm["puck"][3 * i + 2] > -100]
    own = [pm["owner"][i] for i in live]
    car = [sum(1 for o in own if o >= 0 and o // 6 == t) for t in (0, 1)]
    zone = [0, 0]
    for i in live:
        y = pm["puck"][3 * i + 1]
        if abs(y) > BLUE:
            zone[0 if (y > 0) == SE.attacks_top(pm, i, 0) else 1] += 1
    P = pm.get("passes") or []
    sc = pm["score"]
    goals = []                                              # the highest score the box held for two seconds running
    for t in (0, 1):                                        # (a misread digit flickers; a goal stays)
        best, run, cur = 0, 0, None
        for i in range(n):
            v = sc[2 * i + t]
            run = run + 1 if v == cur else 1
            cur = v
            if run >= 2 * int(fps) and v > best:
                best = v
        goals.append(best)
    read = sum(1 for r in rows if r.get("cam") is not None)
    out = {
        "goals (score box)": goals,
        "shots (about)": [sum(k // 6 == t for _, k, _ in shots) for t in (0, 1)],
        "possession %": [round(100 * car[t] / max(1, sum(car))) for t in (0, 1)],
        "attacking zone time %": [round(100 * zone[t] / max(1, len(live))) for t in (0, 1)],
        "passes": [sum(p["team"] == t for p in P) for t in (0, 1)],
        "pass completion %": [round(100 * sum(p["team"] == t and p.get("result") != "failed" for p in P) / max(1, sum(p["team"] == t for p in P))) for t in (0, 1)],
        "puck lost (turnovers against)": [sum(x.get("from") == t for x in pm.get("turnovers") or []) for t in (0, 1)],
        "hits": [sum(h["team"] == t for h in pm.get("hits") or []) for t in (0, 1)],
        "zone entries": [sum(e.get("team") == t for e in pm.get("zoneEntries") or []) for t in (0, 1)],
    }
    return dict(home=pm["team1"], away=pm["team2"], frames=n, frames_read=read, puck_in_play_frames=len(live), measures=out)


def main():
    read_path, home, away = sys.argv[1:4]
    home, away = (int(x) if x.isdigit() else x for x in (home, away))
    rom = os.environ["NHL94_INV_ROM"]
    maps = os.environ["NHL94_INV_MAPS"]
    model = os.environ.get("NHL94_SWING_MODEL", str(Path.home() / "NHL94_scoring_map/runs/vision/swing/model_all9l.json"))
    res = report(read_path, home, away, rom, maps, model)
    print(f"{Path(read_path).name}: {res['home']} (home) / {res['away']}; {res['frames']} video frames, {res['frames_read']} read, the puck in play in {res['puck_in_play_frames']}")
    for k, v in res["measures"].items():
        print(f"  {k:32s} {v[0]:>6} / {v[1]}")
    if len(sys.argv) > 4:
        Path(sys.argv[4]).write_text(json.dumps(res))


if __name__ == "__main__":
    main()
