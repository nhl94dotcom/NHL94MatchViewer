"""A Genesis game's timeline from the score boxes in its video (2026-11-14; the video reader's events, first part).

The score boxes are read every STEP frames (hud_read.Reader: period, clock, the visitors' and the home team's
score); a reading counts once it has held for HOLD readings in a row (a box half covered, a fade, a replay's panel
read nothing or nonsense for a moment). From the held readings:
- games: a new game at a reading of the 1st period at 0-0 after anything else (a score that falls, jumps by more
  than one or a period that goes back is a misread and skipped: on a YouTube video a 7 once read as 6 split a game);
- goals: a score up by one (the team, the period and the clock of the last reading before it);
- whistles: the clock standing still for WHISTLE seconds (real) or more while the boxes are read (a stoppage, a
  faceoff to follow); the clock's reading then; at 0:00 marked period_end.
Checked on nhl94_playoffs-261113-133619.mkv (four games): the four games and their finals right; 27 of 27 goals the
same as the recordings' (team, period, clock within 1 s), none extra; every one of the 45 faceoffs during periods
matched by a whistle at its clock, plus 5 a game more (the clock standing at period ends and at pauses).

python analysis/vision/game_events.py VIDEO TEMPLATES.npz OUT.json [STEP] [--crop=X,Y,W,H]   (STEP: a tenth of a second
                                                        by default; the frame rate from the video)   (OUT also keeps the held readings:
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


def sample_frames(video, count=12):
    """count frames spread over the video, as camera_track.frames would give them (for Reader.fit)."""
    import stream_locate as L
    from PIL import Image
    w, h = C.video_size(video)
    d = L.duration(video)
    out = []
    for k in range(count):
        s = L.grab(video, d * (k + 0.5) / count, w, h)
        if C.CROP:
            x, y, cw, ch = C.CROP
            s = np.array(Image.fromarray(s[y:y + ch, x:x + cw]).resize((C.NATIVE_W, C.H), Image.BOX))
        elif (w, h) != (C.NATIVE_W, C.H):
            s = np.array(Image.fromarray(s).resize((C.NATIVE_W, C.H), Image.BILINEAR))
        out.append(s.astype(np.int16))
    return out


def read_video(video, templates, step=6):
    """Readings (frame, period, clock, visitors, home). The scores are read as the last held value, one more, or 0
    (Reader.read_score: a score only rises by one), which keeps an 8 from reading as a 6 or 0."""
    rd = hud_read.Reader(templates)
    if rd.native:
        print("template geometry (scale x, y, shift x, y, blur):", rd.fit(sample_frames(video)), flush=True)
    rows = []
    gap = 60 * C.video_fps(video)                        # a minute (real) with no reading: read freely again
    prev = {"vis": None, "home": None}                   # read freely until a reading holds (a video may start
    for n, f in C.frames(video):                         # mid-game), and again after a long gap (a break)
        if n % step:
            continue
        if rows and n - rows[-1][0] > gap:
            prev = {"vis": None, "home": None}
        r = rd.read(f)
        if r["period"] is None:
            continue
        clock = rd.read_clock(f, rows[-1][2] if rows else None)
        if clock is None:
            continue
        r["clock"] = clock
        sc = {k: rd.read_score(f, k, prev[k]) for k in ("vis", "home")}
        if None in sc.values():
            continue
        if sc["vis"] != prev["vis"] or sc["home"] != prev["home"]:
            pass
        rows.append((n, r["period"], r["clock"], sc["vis"], sc["home"]))
        if len(rows) >= HOLD and all(q[3:] == rows[-1][3:] for q in rows[-HOLD:]):
            prev = {"vis": sc["vis"], "home": sc["home"]}
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
        new = cur is None or (per == 0 and vis == 0 and home == 0 and (last[1] > 0 or last[3] + last[4] > 0
                                                                        or clock > last[2] + 60))
        if not new and (vis < last[3] or home < last[4] or per < last[1] or vis > last[3] + 1 or home > last[4] + 1):
            continue                                         # a misread (a score can't fall or jump): skipped
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
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    crop = next((a.split("=")[1] for a in sys.argv if a.startswith("--crop=")), None)
    if crop:
        C.CROP = tuple(int(v) for v in crop.split(","))
    video, templates, out = Path(args[0]), args[1], Path(args[2])
    fps = C.video_fps(video)
    step = int(args[3]) if len(args) > 3 else max(1, round(fps / 10))
    rows = held(read_video(video, templates, step))
    games = events(rows, fps)
    out.write_text(json.dumps({"video": str(video), "step": step, "fps": fps, "crop": C.CROP, "games": games,
                               "readings": rows}, indent=1))
    for g in games:
        print(f"game from frame {g['start_frame']} to {g['end_frame']}: final {g['final'][0]}-{g['final'][1]} (visitors-home), "
              f"{len(g['goals'])} goals, {len(g['whistles'])} whistles, periods {[p['period'] for p in g['periods']]}")


if __name__ == "__main__":
    main()
