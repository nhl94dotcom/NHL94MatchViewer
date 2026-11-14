"""Players followed over time in a Genesis video (2026-11-14; the video reader's third step, second part).

Each frame's detections (sprites.players) are put on the rink with the frame's camera (camera_track.py):
X = x + Hpos - 128, Y = 107 + Vpos - y - DY (DY: the detections sit DY pixels above the body point; Z, the height, is
taken as 0). Per team, each detection joins the nearest live track within GATE rink units (a greedy match, nearest
pairs first), or starts a new track; a track not matched for KEEP frames ends. Tracks shorter than MIN_LEN frames (a
split-off piece, a star, the crowd) are dropped.

python analysis/vision/player_tracks.py check VIDEO CAMERA_TRACK.npz HOME AWAY [FIRST] [COUNT] [STEP] [STATIC.npz]
  the kept tracks' points on still-camera frames against the recorded players of their team: found, missed, extra,
  and the position error."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_track as C  # noqa: E402
import sprites as S  # noqa: E402

DY = -4          # sprites.players' centres against the body point (measured: -3.9 pixels)
GATE = 14        # rink units a player can move between two looked-at frames (STEP 2: 1/30 s real)
KEEP = 8         # frames a track survives unseen
MIN_LEN = 12     # frames a kept track needs


def to_rink(x, y, hpos, vpos):
    return x + hpos - 128, 107 + vpos - (y - DY)


def track(dets_by_frame):
    """dets_by_frame: [(n, [(team, X, Y)])] in order. Returns tracks: {id: {"team", "pts": [(n, X, Y)]}}."""
    tracks, live, nid = {}, {0: [], 1: []}, 0
    for n, dets in dets_by_frame:
        for team in (0, 1):
            ds = [d for d in dets if d[0] == team]
            cand = sorted((np.hypot(tracks[t]["pts"][-1][1] - d[1], tracks[t]["pts"][-1][2] - d[2]), t, k)
                          for t in live[team] for k, d in enumerate(ds))
            used_t, used_d = set(), set()
            for dist, t, k in cand:
                if dist > GATE or t in used_t or k in used_d:
                    continue
                used_t.add(t)
                used_d.add(k)
                tracks[t]["pts"].append((n, ds[k][1], ds[k][2]))
            for k, d in enumerate(ds):
                if k not in used_d:
                    tracks[nid] = {"team": team, "pts": [(n, d[1], d[2])]}
                    live[team].append(nid)
                    nid += 1
            live[team] = [t for t in live[team] if n - tracks[t]["pts"][-1][0] <= KEEP]
    return {t: v for t, v in tracks.items() if len(v["pts"]) >= MIN_LEN}


def check(video, track_npz, home, away, first, count, step, static_npz=None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import rink_mosaic as RM
    rom = Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin"
    tl = json.loads(Path(str(video) + ".timeline.json").read_text())
    truth, fps = RM.Truth(tl), tl.get("fps", 59.92)
    cams = {int(r[0]): r for r in np.load(track_npz)["rows"]}
    rink = C.Rink(rom)
    cols = S.team_colours(rom, home, away)
    static = np.load(static_npz)["mask"] if static_npz else None
    seq, raw = [], {}
    for n, f in C.frames(video, first, count):
        if n % step or n not in cams or not cams[n][4]:
            continue
        _, hpos, vpos = cams[n][:3]
        hpos, vpos = int(hpos), int(vpos)
        dets = [(t, *to_rink(x, y, hpos, vpos)) for t, x, y, _ in S.players(rink, f, hpos, vpos, cols, static)]
        seq.append((n, dets))
        raw[n] = (hpos, vpos, dets)
    tracks = track(seq)
    at = {}
    for tid, tr in tracks.items():
        for n, X, Y in tr["pts"]:
            at.setdefault(n, []).append((tr["team"], X, Y, tid))

    def s16(v):
        return v - 65536 if v & 0x8000 else v
    res = {"raw": [0, 0, 0], "tracked": [0, 0, 0]}
    errs = []
    for n, (hpos, vpos, dets) in raw.items():
        cam = truth.camera(n / fps)
        if not cam or not cam[7]:
            continue
        c, i = truth.caps[tl["games"][cam[3]]][0], cam[4]
        recs = []
        for r in range(12):
            a = 0xB04A + 0x80 * r
            X, Y = s16(c.word(i, a)), s16(c.word(i, a + 0x14))
            x, y = X - hpos + 128, 107 - Y + vpos
            if 4 <= x < 252 and 8 <= y < 178:
                recs.append((0 if r < 6 else 1, X, Y))
        for name, pts in (("raw", [d[:3] for d in dets]), ("tracked", [p[:3] for p in at.get(n, [])])):
            used = set()
            for team, X, Y in recs:
                best = min(((abs(p[1] - X) + abs(p[2] - Y), k) for k, p in enumerate(pts) if p[0] == team and k not in used),
                           default=None)
                if best and best[0] <= 16:
                    used.add(best[1])
                    res[name][0] += 1
                    if name == "tracked":
                        errs.append(np.hypot(pts[best[1]][1] - X, pts[best[1]][2] - Y))
                else:
                    res[name][1] += 1
            res[name][2] += len(pts) - len(used)
    for name, (a, b, e) in res.items():
        print(f"{name}: found {a}, missed {b}, extra {e} (found {a / max(a + b, 1):.1%}, extra {e / max(a + e, 1):.1%} of "
              f"detections)")
    print(f"tracks kept {len(tracks)}; position error (rink units) median {np.median(errs):.1f}, 90% {np.percentile(errs, 90):.1f}")


if __name__ == "__main__":
    if sys.argv[1] == "check":
        a = sys.argv[2:]
        check(Path(a[0]), a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 0, int(a[5]) if len(a) > 5 else 3000,
              int(a[6]) if len(a) > 6 else 2, a[7] if len(a) > 7 else None)
