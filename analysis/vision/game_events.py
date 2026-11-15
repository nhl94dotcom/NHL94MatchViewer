"""A Genesis game's timeline from the score boxes in its video (2026-11-14; the video reader's events, first part).

The score boxes are read every STEP frames (hud_read.Reader: period, clock, the visitors' and the home team's
score); a reading counts once it has held for HOLD readings in a row (a box half covered, a fade, a replay's panel
read nothing or nonsense for a moment). From the held readings:
- games: a new game at a reading of the 1st period at 0-0 after anything else (a score that falls, jumps by more
  than one or a period that goes back is a misread and skipped: on a YouTube video a 7 once read as 6 split a game);
- goals: a score up by one (the team, the period and the clock of the last reading before it);
- teams: the score box's abbreviations (Reader.read_teams: visitors above, home below) every 5 s, the commonest pair
  in each game;
- whistles: the clock standing still for WHISTLE seconds (real) or more while the boxes are read (a stoppage, a
  faceoff to follow); the clock's reading then; at 0:00 marked period_end.
Against other screens (a soft copy, 2026-11-15): read_video's rink_at (frames with no rink skipped), fits (a new
held score only when it can follow the game so far, or steady for NEW_GAME s), a goal only where the new score
also wins read freely, and steady (a reading far from its neighbours' median clock dropped).
Checked on nhl94_playoffs-261113-133619.mkv (four games): the four games and their finals right; 27 of 27 goals the
same as the recordings' (team, period, clock within 1 s), none extra; every one of the 45 faceoffs during periods
matched by a whistle at its clock, plus 5 a game more (the clock standing at period ends and at pauses).

python analysis/vision/game_events.py VIDEO TEMPLATES.npz OUT.json [STEP] [--crop=X,Y,W,H] [--camera=TRACK.npz]   (STEP: a tenth of a second
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
NEW_GAME = 5.0                    # seconds (real) a new game's 0-0 must hold (fits)
TEAM_READS = []
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


def read_video(video, templates, step=6, rink_at=None):
    """Readings (frame, period, clock, visitors, home). The scores are read as the last held value, one more, or 0
    (Reader.read_score: a score only rises by one), which keeps an 8 from reading as a 6 or 0. rink_at(frame): False
    where the camera track found no rink (the frame is skipped: on a soft copy of BOS-CHI a break screen read as clock
    3:33 with one more goal, often enough to hold, and the scores crept up and split the series into eight games)."""
    rd = hud_read.Reader(templates)
    if rd.native:
        print("template geometry (scale x, y, shift x, y, blur):", rd.fit(sample_frames(video)), flush=True)
    rows = []
    global TEAM_READS
    TEAM_READS = []                                      # (frame, visitors, home): the score box's abbreviations
    team_every = round(5 * C.video_fps(video))           # every 5 s (real)
    gap = 60 * C.video_fps(video)                        # a minute (real) with no reading: read freely again
    good = None                                          # the last held reading that fit the game so far
    new_span = NEW_GAME * C.video_fps(video)
    prev = {"vis": None, "home": None}                   # read freely until a reading holds (a video may start
    for n, f in C.frames(video):                         # mid-game), and again after a long gap (a break)
        if n % step or (rink_at is not None and not rink_at(n)):
            continue
        if rows and n - rows[-1][0] > gap:
            prev, good = {"vis": None, "home": None}, None
        r = rd.read(f)
        if r["period"] is None:
            continue
        if n % team_every < step:
            vt, ht = rd.read_teams(f)
            if vt and ht:
                TEAM_READS.append((n, vt, ht))
        clock = rd.read_clock(f, rows[-1][2] if rows else None)
        if clock is None:
            continue
        r["clock"] = clock
        sc = {k: rd.read_score(f, k, prev[k]) for k in ("vis", "home")}
        if None in sc.values():
            continue
        if any(prev[k] is not None and sc[k] == prev[k] + 1 and rd.read_score(f, k, None) != sc[k] for k in sc):
            continue                     # a goal only where the new score also wins read freely (a faint box's 2,
                                         # fading at a faceoff on a soft copy, matched 3 better than 2 or 0)
        if sc["vis"] != prev["vis"] or sc["home"] != prev["home"]:
            pass
        rows.append((n, r["period"], r["clock"], sc["vis"], sc["home"]))
        if len(rows) >= HOLD and all(q[3:] == rows[-1][3:] for q in rows[-HOLD:]) and fits(rows, good, new_span):
            prev = {"vis": sc["vis"], "home": sc["home"]}
            good = rows[-1]
    return rows


def fits(rows, good, new_span):
    """The last HOLD readings (held) can follow the last good one: a later period, or the same period with the clock
    not run back up and the score at most one goal on (a replay or a break screen read as another time: on a soft
    copy of BOS-CHI, clock 3:33, 6:32 and 13:33 in a 3rd-period stoppage, whose score then held and crept up). Or
    steady: the same period and score held over new_span frames with the clock never going up (a break screen's
    readings jump about), which also lets the reading recover after a stray one was taken as good, and is the only
    way in for a new game's 1st period at 0-0 (0 is always a candidate score, so a break screen's few readings at
    0-0 had reset a game's score)."""
    if good is None:
        return True
    span = []
    for q in reversed(rows):
        if q[0] < rows[-1][0] - new_span:
            break
        span.append(q)
    span.reverse()
    if (span[0][0] <= rows[-1][0] - 0.8 * new_span and all(q[1] == span[-1][1] and q[3:] == span[-1][3:] for q in span)
            and all(b[2] <= a[2] for a, b in zip(span, span[1:]))):
        return True
    run = rows[-HOLD:]
    _, per, clock, vis, home = run[-1]
    if per == 0 and vis == 0 and home == 0:
        return False
    if vis < good[3] or home < good[4] or vis + home > good[3] + good[4] + 1:
        return False
    return per > good[1] or (per == good[1] and all(q[2] <= good[2] + 3 for q in run))


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


def steady(rows, fps, window=15.0, tol=15):
    """The rows whose clock is within tol (game seconds) of the median clock of the rows in the same period within
    window seconds (real) either side: a break screen or a replay read as another time is dropped, whichever side of
    the true clock it falls (on a soft copy of BOS-CHI a stray 1:30 in a 3rd period, kept as the last reading, had
    every true reading after it skipped as the clock running back up)."""
    out, w = [], window * fps
    frames = [r[0] for r in rows]
    import bisect
    for k, r in enumerate(rows):
        lo, hi = bisect.bisect_left(frames, r[0] - w), bisect.bisect_right(frames, r[0] + w)
        near = sorted(q[2] for q in rows[lo:hi] if q[1] == r[1])
        if abs(r[2] - near[len(near) // 2]) <= tol:
            out.append(r)
    return out


def events(rows, fps):
    games, cur, last = [], None, None
    for n, per, clock, vis, home in steady(rows, fps):
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
                if b == a + 1:                           # the clock stops at a goal: the first reading with the
                    at = clock if per == last[1] and clock <= last[2] else last[2]   # new score has its time
                    cur["goals"].append({"team": team, "period": last[1], "clock": at, "frame": n,
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
    rink_at = None
    cam = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--camera=")), None)
    if cam:                                              # the camera track: frames with no rink skipped
        cams = {int(r[0]): r for r in np.load(cam)["rows"]}
        fr = sorted(cams)
        cstep = int(np.median(np.diff(fr[:5000]))) if len(fr) > 1 else 1

        def rink_at(n):
            k = n - n % cstep
            return any(m in cams and cams[m][4] for m in (k - cstep, k, k + cstep))
    rows = held(read_video(video, templates, step, rink_at))
    games = events(rows, fps)
    from collections import Counter
    for g in games:                                      # each game's teams: the commonest pair read in it
        pairs = Counter((v, h) for n, v, h in TEAM_READS if g["start_frame"] <= n <= g["end_frame"])
        if pairs:
            (g["visitors"], g["home"]), _ = pairs.most_common(1)[0]
    out.write_text(json.dumps({"video": str(video), "step": step, "fps": fps, "crop": C.CROP, "games": games,
                               "readings": rows}, indent=1))
    for g in games:
        print(f"game from frame {g['start_frame']} to {g['end_frame']}: {g.get('visitors', '?')} at {g.get('home', '?')}, "
              f"final {g['final'][0]}-{g['final'][1]} (visitors-home), "
              f"{len(g['goals'])} goals, {len(g['whistles'])} whistles, periods {[p['period'] for p in g['periods']]}")


if __name__ == "__main__":
    main()
