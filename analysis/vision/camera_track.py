"""The Genesis camera from the video alone (2026-11-14; the video reader's second step).

Each frame is matched against the rink as the ROM draws it (rink_render.py). The game plays in the 256-pixel-wide
mode (H32): the rink map is 384 wide and the camera's Hpos runs -64..64, so 256 + 128 = 384. A RetroArch recording
may stretch it to 320 (nhl94_playoffs-261113-133619.mkv does), so frames are squeezed back to 256 first.
Measured on that video's still-camera frames against the recordings: frame pixel (x, y) is rink-map pixel
(x + Hpos + 63, y - Vpos + 256) in all 40 checked (the 63, not updatescroll's 64, from the squeeze's resampling).

The match: the share of sampled pixels above the score boxes (rows 0-185) within 60 (summed over R, G, B) of the
render; the sprites, the centre-ice logo (a sprite) and the crowd's animation miss, the rink agrees. A frame is placed
by a small search around the last frame's place (tracking), or, when that's lost (a share under LOST) or at the start,
by a search over the whole rink (coarse, then the best few refined; while lost, only every RETRY frames). Frames that place nowhere (menus, the
close-up faceoff box, intermissions, replays' panels) are kept as lost.

python analysis/vision/camera_track.py VIDEO OUT.npz [--rom ROM] [--first N] [--count N] [--check TIMELINE]
  --check: each placed frame's camera against the recordings' (tools/video_sync.py's timeline), printed."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rink_render  # noqa: E402

NATIVE_W, H, HUD_TOP = 256, 224, 186
OFF_X, OFF_Y = 63, 256            # rink-map pixel = frame pixel + (Hpos + OFF_X, OFF_Y - Vpos)
PAD = 64                          # the render padded with black so a search can run past its edges
LOST = 0.55                       # under this share a frame isn't placed
RETRY = 10                        # while lost, a whole-rink search every RETRY frames (menus, breaks: most of a video)
TOL = 60


def video_size(video):
    import imageio_ffmpeg
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(video)], capture_output=True, text=True)
    for line in p.stderr.splitlines():
        if "Video:" in line:
            import re
            m = re.search(r", (\d{3,4})x(\d{3,4})", line)
            if m:
                return int(m.group(1)), int(m.group(2))
    raise ValueError("no video stream")


def frames(video, first=0, count=None):
    """(frame number, native-width RGB frame as int16) for every frame from `first`; ffmpeg does the squeeze."""
    import imageio_ffmpeg
    w, h = video_size(video)
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "fatal", "-threads", "1", "-i", str(video),
           "-an", "-fps_mode", "passthrough"]
    if (w, h) != (NATIVE_W, H):
        cmd += ["-vf", f"scale={NATIVE_W}:{H}:flags=bilinear"]
    cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
    size, n = NATIVE_W * H * 3, 0
    try:
        while True:
            b = p.stdout.read(size)
            if len(b) < size:
                break
            if n >= first:
                yield n, np.frombuffer(b, np.uint8).reshape(H, NATIVE_W, 3).astype(np.int16)
            n += 1
            if count is not None and n >= first + count:
                break
    finally:
        p.kill()


class Rink:
    def __init__(self, rom):
        r = rink_render.render(Path(rom).read_bytes()).astype(np.int16)
        self.img = np.zeros((r.shape[0] + 2 * PAD, r.shape[1] + 2 * PAD, 3), np.int16)
        self.img[PAD:PAD + r.shape[0], PAD:PAD + r.shape[1]] = r
        self.h, self.w = self.img.shape[:2]

    def ice(self):
        """The playing surface in the padded render: flooded from centre ice through the colours found on the ice
        between the blue lines (ice, lines, circles, scratches), stopping at the boards' kick plate and glass."""
        if getattr(self, "_ice", None) is not None:
            return self._ice
        img = self.img
        h, w = img.shape[:2]
        cy, cx = h // 2, w // 2
        key = (img[:, :, 0].astype(np.int32) << 16) | (img[:, :, 1].astype(np.int32) << 8) | img[:, :, 2]
        inside = np.isin(key, np.unique(key[cy - 120:cy + 120, cx - 100:cx + 100]))
        m = np.zeros((h, w), bool)
        m[cy, cx] = True
        while True:
            p = np.pad(m, 1)
            g = (m | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]) & inside
            if (g == m).all():
                break
            m = g
        self._ice = m
        return m

    def share(self, f, u, v, sub):
        """u, v: the frame's top-left in the padded render."""
        if u < 0 or v < 0 or u + NATIVE_W > self.w or v + HUD_TOP > self.h:
            return -1.0
        a = f[:HUD_TOP:sub, ::sub]
        b = self.img[v:v + HUD_TOP:sub, u:u + NATIVE_W:sub]
        return float((np.abs(a - b).sum(axis=2) < TOL).mean())

    def local(self, f, u0, v0, reach=10):
        c = max(((u0 + du, v0 + dv) for du in range(-reach, reach + 1, 2) for dv in range(-reach, reach + 1, 2)),
                key=lambda p: self.share(f, p[0], p[1], 4))
        best = max(((c[0] + du, c[1] + dv) for du in range(-2, 3) for dv in range(-2, 3)),
                   key=lambda p: self.share(f, p[0], p[1], 2))
        return best[0], best[1], self.share(f, best[0], best[1], 1)

    def full(self, f):
        us = range(PAD - 8, PAD + 384 - NATIVE_W + 9, 4)          # the camera's whole range, with room
        vs = range(PAD - 8, self.h - PAD - HUD_TOP + 8, 4)
        cands = sorted(((self.share(f, u, v, 8), u, v) for u in us for v in vs), reverse=True)[:6]
        return max((self.local(f, u, v, reach=4) for _, u, v in cands), key=lambda r: r[2])


def track(video, rom, first=0, count=None):
    rink = Rink(rom)
    out, last, tried = [], None, -RETRY
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
        import lowload
    except ImportError:
        lowload = None
    for n, f in frames(video, first, count):
        if lowload:
            lowload.breathe()
        r = rink.local(f, *last) if last else None
        if (r is None or r[2] < LOST) and n - tried >= RETRY:   # lost: the whole rink, every RETRY frames
            r, tried = rink.full(f), n
        if r is None or r[2] < LOST:
            out.append((n, 0, 0, r[2] if r else 0, 0))
            last = None
            continue
        u, v, s = r
        last = (u, v)
        hpos, vpos = u - PAD - OFF_X, OFF_Y - (v - PAD)
        out.append((n, hpos, vpos, s, 1))
        if n % 2000 == 0:
            print(f"frame {n}: camera ({vpos}, {hpos}) share {s:.2f}", flush=True)
    return np.array(out, np.float32)


def check(rows, timeline_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import rink_mosaic as RM
    tl = json.loads(Path(timeline_path).read_text())
    truth, fps = RM.Truth(tl), tl.get("fps", 59.92)
    errs, moving, lost_live, placed_dead = [], [], 0, 0
    for n, hpos, vpos, s, ok in rows:
        cam = truth.camera(n / fps)
        live = bool(cam and cam[6])
        if not ok:
            lost_live += live
            continue
        if not cam:
            placed_dead += 1
            continue
        if cam[7]:                                       # a still camera: the recording's word is exact for it
            errs.append((hpos - cam[1], vpos - cam[0]))
        elif live:                                       # moving: the timeline is good to a fraction of a second only
            moving.append(max(abs(hpos - cam[1]), abs(vpos - cam[0])))
    e = np.array(errs)
    print(f"{len(rows)} frames: placed {int(rows[:, 4].sum())}; lost in live play {lost_live}; placed outside the "
          f"recordings {placed_dead}")
    if len(e):
        for name, col in (("Hpos", e[:, 0]), ("Vpos", e[:, 1])):
            print(f"  {name} error on still-camera frames ({len(col)}): exact {np.mean(col == 0):.1%}, within 1 "
                  f"{np.mean(np.abs(col) <= 1):.1%}, within 4 {np.mean(np.abs(col) <= 4):.1%}, worst {np.abs(col).max():.0f}")
    if moving:
        m = np.array(moving)
        print(f"  moving camera, live play ({len(m)} frames; the timeline's own error included): within 4 "
              f"{np.mean(m <= 4):.1%}, within 16 {np.mean(m <= 16):.1%}, median {np.median(m):.0f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--rom", default=str(Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin"))
    ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--count", type=int)
    ap.add_argument("--check")
    a = ap.parse_args()
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
        import lowload
        lowload.gentle()
    except ImportError:
        pass
    rows = track(a.video, a.rom, a.first, a.count)
    np.savez_compressed(a.out, rows=rows)
    if a.check:
        check(rows, a.check)


if __name__ == "__main__":
    main()
