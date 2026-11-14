"""Zone time from a Genesis video (2026-11-14; the video reader's first analysis).

The camera follows the puck: in the recordings the puck's Y is the camera's Vpos less about 8 (BOS-CHI: 0.97 Vpos -
6 to -11, spread 45), so each live frame's zone is read from the camera alone (camera_track.py; blue lines at +-64):
the home team's attacking zone, neutral, its defending zone, by the period's direction (home attacks up in periods 1
and 3, and overtime). Live play: frames inside a game whose score-box clock (game_events.py's held readings) changes
within the next 48 frames (a game second is 24); the period from the readings.
Per game: the share of live play in each zone, and each team's attack-zone time in game seconds (2.5 a real
second).

python analysis/vision/zone_time.py CAMERA_TRACK.npz EVENTS.json [--check]
  --check: against the recordings' puck (the match file's names from tools/video_sync.py's timeline): the shares from
  the puck's own Y over the same games."""
import json
import os
import sys
from pathlib import Path

import numpy as np

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
OFFSET, BLUE, FPS = -8, 64, 59.92


def zone(y, period):
    up = period % 2 == 0
    yy = y if up else -y
    return 1 if yy > BLUE else -1 if yy < -BLUE else 0


def live_frames(readings, fps=FPS):
    """{frame: period} for frames in stretches where the clock runs (within 0.8 s real: a game second is 0.4)."""
    out = {}
    near, gap = round(0.8 * fps), round(0.4 * fps)
    for k in range(len(readings) - 1):
        n, per, clock = readings[k][:3]
        later = [r for r in readings[k + 1:k + 12] if r[0] - n <= near]
        if later and any(r[2] != clock for r in later) and readings[k + 1][0] - n <= gap:
            for f in range(n, readings[k + 1][0]):
                out[f] = per
    return out


def main():
    d = np.load(sys.argv[1])
    cams = d["rows"]
    cstep = int(d["step"]) if "step" in d else 1         # camera_track --step: each placed frame stands for cstep
    ev = json.loads(Path(sys.argv[2]).read_text())
    fps = ev.get("fps", FPS)
    live = live_frames(ev["readings"], fps)
    games = []
    for g in ev["games"]:
        z = []
        for n, hpos, vpos, share, ok in cams:
            n = int(n)
            if ok and g["start_frame"] <= n <= g["end_frame"] and n in live:
                z.append(zone(vpos + OFFSET, live[n]))
        z = np.array(z)
        sh = [float(np.mean(z == k)) for k in (1, 0, -1)]
        secs = len(z) * cstep / fps * 2.5
        games.append({"final": g["final"], "shares": sh, "home_attack_s": round(sh[0] * secs), "away_attack_s": round(sh[2] * secs),
                      "live_game_s": round(secs)})
        print(f"game {g['final'][0]}-{g['final'][1]}: live {secs:.0f} game s; home attacking {100 * sh[0]:.0f}%, neutral "
              f"{100 * sh[1]:.0f}%, home defending {100 * sh[2]:.0f}% (home attack-zone {sh[0] * secs:.0f} s, visitors "
              f"{sh[2] * secs:.0f} s)")
    if "--check" in sys.argv:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
        from export_match import Capture
        tl = json.loads(Path(ev["video"] + ".timeline.json").read_text())

        def s16(v):
            return v - 65536 if v & 0x8000 else v
        for name, g in zip(tl["games"], games):
            c = Capture(HOME / "captures" / name)
            t = [zone(s16(c.word(i, 0xB04A + 0x80 * 14 + 0x14)), c.word(i, 0xC466)) for i in range(0, c.count, 3)
                 if c.byte(i, 0xFFF7) == 0 and not c.byte(i, 0xC2EA) & 1]
            t = np.array(t)
            print(f"  {name}: the puck's own (recording) {[round(100 * float(np.mean(t == k))) for k in (1, 0, -1)]}%, "
                  f"the video's {[round(100 * x) for x in g['shares']]}%")


if __name__ == "__main__":
    main()
