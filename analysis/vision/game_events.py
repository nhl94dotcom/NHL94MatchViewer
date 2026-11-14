"""A Genesis game's timeline from the score boxes in its video (2026-11-14; the video reader's events, first part).

The score boxes are read every STEP frames (hud_read.Reader: period, clock, the visitors' and the home team's
score); a reading counts once it has held for HOLD readings in a row (a box half covered, a fade, a replay's panel
read nothing or nonsense for a moment). From the held readings:
- games: a new game when the period goes back to the 1st with the clock at least as high as before, or the scores
  fall;
- goals: a score up by one (the team, the period and the clock of the last reading before it);
- whistles: the clock standing still for WHISTLE seconds (real) or more while the boxes are read (a stoppage, a
  faceoff to follow); the clock's reading then; at 0:00 marked period_end.
Checked on nhl94_playoffs-261113-133619.mkv (four games): the four games and their finals right; 27 of 27 goals the
same as the recordings' (team, period, clock within 1 s), none extra; every one of the 45 faceoffs during periods
matched by a whistle at its clock, plus 5 a game more (the clock standing at period ends and at pauses).

python analysis/vision/game_events.py VIDEO TEMPLATES.npz OUT.json [STEP]   (OUT also keeps the held readings:
                                                        [frame, period, clock, visitors, home])
python analysis/vision/game_events.py check OUT.json     (the goals against the recordings' match files, through
                                                        tools/video_sync.py's timeline beside the video)"""
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_track as C  # noqa: E402
import hud_read  # noqa: E402

HOLD, WHISTLE = 3, 2.0
HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")


def read_video(video, templates, step=6):
    rd = hud_read.Reader(templates)
    rows = []
    for n, f in C.frames(video):
        if n % step:
            continue
        r = rd.read(f)
        if None in (r["period"], r["clock"], r["vis"], r["home"]):
            continue
        rows.append((n, r["period"], r["clock"], r["vis"], r["home"]))
    return rows


def held(rows):
    out, run = [], []
    for r in rows:
        if run and r[1:] != run[-1][1:]:
            run = []
        run.append(r)
        if len(run) == HOLD:
            out.append(run[0])
        elif len(run) > HOLD:
            out.append(r)
    return out


def events(rows, fps):
    games, cur, last = [], None, None
    for n, per, clock, vis, home in rows:
        new = cur is None or (per < last[1]) or (per == last[1] and clock > last[2] + 5) or vis < last[3] or home < last[4]
        if new:
            cur = {"start_frame": n, "goals": [], "whistles": [], "periods": []}
            games.append(cur)
            stand = None
        else:
            for team, a, b in (("visitors", last[3], vis), ("home", last[4], home)):
                if b == a + 1:
                    cur["goals"].append({"team": team, "period": last[1], "clock": last[2], "frame": n,
                                         "score": [vis, home]})
        if not cur["periods"] or cur["periods"][-1]["period"] != per:
            cur["periods"].append({"period": per, "frame": n, "clock": clock})
        if last is not None and not new and clock == last[2]:
            stand = stand or last[0]
            if (n - stand) / fps >= WHISTLE and (not cur["whistles"] or cur["whistles"][-1]["frame"] != stand):
                cur["whistles"].append({"frame": stand, "period": per, "clock": clock, "period_end": clock == 0})
        else:
            stand = None
        cur["end_frame"] = n
        cur["final"] = [vis, home]
        last = (n, per, clock, vis, home)
    return games


def check(out_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import season
    import replay_pack
    data = json.loads(Path(out_path).read_text())
    tl = json.loads(Path(data["video"] + ".timeline.json").read_text())
    fps = tl.get("fps", 59.92)
    for name in tl["games"]:
        m = season.load_match(HOME / "matches" / f"{name}.js")
        rec = [(g["team"], g["period"], g["clock"]) for g in m["goals"]]
        segs = [s for s in tl["segments"] if tl["games"][s[2]] == name]
        lo, hi = segs[0][0] * fps, segs[-1][1] * fps
        found = [g for gm in data["games"] for g in gm["goals"] if lo - 600 <= g["frame"] <= hi + 600]
        vid = [(0 if g["team"] == "home" else 1, g["period"], g["clock"]) for g in found]
        both = sum(1 for r in rec if any(r[0] == v[0] and r[1] == v[1] and abs(r[2] - v[2]) <= 1 for v in vid))
        print(f"{name}: recorded goals {len(rec)}, read from the video {len(vid)}, the same (team, period, clock within 1 s) {both}")
        for r in rec:
            if not any(r[0] == v[0] and r[1] == v[1] and abs(r[2] - v[2]) <= 1 for v in vid):
                print("   recorded only:", r)
        for v in vid:
            if not any(r[0] == v[0] and r[1] == v[1] and abs(r[2] - v[2]) <= 1 for r in rec):
                print("   video only:", v)
    _ = replay_pack


def main():
    if sys.argv[1] == "check":
        check(sys.argv[2])
        return
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
        import lowload
        lowload.gentle()
    except ImportError:
        pass
    video, templates, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    step = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    rows = held(read_video(video, templates, step))
    games = events(rows, 59.92)
    out.write_text(json.dumps({"video": str(video), "step": step, "games": games, "readings": rows}, indent=1))
    for g in games:
        print(f"game from frame {g['start_frame']} to {g['end_frame']}: final {g['final'][0]}-{g['final'][1]} (visitors-home), "
              f"{len(g['goals'])} goals, {len(g['whistles'])} whistles, periods {[p['period'] for p in g['periods']]}")


if __name__ == "__main__":
    main()
