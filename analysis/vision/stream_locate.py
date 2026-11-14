"""Where the game's picture is in a stream's layout (2026-11-14; the video reader for Twitch / YouTube videos).

A streamer's video shows the game scaled up somewhere in a bigger frame, with a webcam, overlays and a still
background around it. From SAMPLES frames spread over the video (read at a quarter size): each pixel's spread over
time; the changing pixels grouped; the largest group's box is the game's picture (a webcam is a smaller group of its
own). The box is then checked and fitted: the picture cut out at that box (and at boxes a few pixels larger or
smaller on each side), squeezed to 256 x 224, matched against the drawn rink (camera_track.Rink.full); the box with
the best mean match over the samples wins.

python analysis/vision/stream_locate.py VIDEO   -> prints X,Y,W,H (for camera_track.py --crop)"""
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_track as C  # noqa: E402
import sprites as S  # noqa: E402

SAMPLES, Q = 48, 4


def duration(video):
    import imageio_ffmpeg
    import re
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(video)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def grab(video, t, w, h):
    import imageio_ffmpeg
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "fatal", "-ss", f"{t:.2f}", "-i",
                        str(video), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    return np.frombuffer(p.stdout[:w * h * 3], np.uint8).reshape(h, w, 3)


def locate(video, rom=None):
    rom = rom or Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin"
    w, h = C.video_size(video)
    d = duration(video)
    shots = [grab(video, d * (k + 0.5) / SAMPLES, w, h) for k in range(SAMPLES)]
    small = np.stack([s[::Q, ::Q].astype(np.float32).mean(axis=2) for s in shots])
    moving = small.std(axis=0) > 12
    groups = sorted(S.label(moving), key=lambda g: -len(g[0]))
    ys, xs = groups[0]
    box = (int(xs.min()) * Q, int(ys.min()) * Q, int(xs.max() - xs.min() + 1) * Q, int(ys.max() - ys.min() + 1) * Q)
    print(f"changing area: {box} ({len(groups)} groups; the next largest {len(groups[1][0]) if len(groups) > 1 else 0} "
          f"against {len(ys)} cells)", flush=True)
    rink = C.Rink(rom)
    from PIL import Image

    def score(b):
        x, y, bw, bh = b
        if x < 0 or y < 0 or x + bw > w or y + bh > h:
            return -1
        vals = []
        for s in shots[::4]:
            crop = np.array(Image.fromarray(s[y:y + bh, x:x + bw]).resize((C.NATIVE_W, C.H), Image.BOX)).astype(np.int16)
            vals.append(rink.full(crop)[2])
        return float(np.median(vals))
    best = (score(box), box)
    step = max(1, Q // 2)
    for _ in range(3):                                  # each side in or out a little, while the match improves
        better = False
        for i in range(4):
            for dv in (-2 * step, -step, step, 2 * step):
                b = list(best[1])
                if i < 2:
                    b[i] += dv
                    b[i + 2] -= dv
                else:
                    b[i] += dv
                sc = score(tuple(b))
                if sc > best[0] + 0.02:                  # a clear gain only: the change-box is usually exact
                    best, better = (sc, tuple(b)), True
        if not better:
            break
    print(f"the game's picture: {best[1]} (median rink match {best[0]:.2f})")
    return best[1]


if __name__ == "__main__":
    x, y, bw, bh = locate(Path(sys.argv[1]))
    print(f"{x},{y},{bw},{bh}")
