"""The Genesis rink as the game draws it, stitched from a RetroArch video and its recordings (2026-11-13; the video
reader's first step: a background to find the camera and the sprites against).

The video's frames are placed on the rink by the camera the recordings keep ($BD18 vertical, $BD1C horizontal, per
sample; tools/video_sync.py's timeline gives each video frame its recording and moment). Only frames of live play (the
clock running: no faceoff line-up or its close-up box) whose camera moves at most 2 over the frames around them are
used (a frame of timing error then can't smear the picture). At each rink pixel
the median colour of up to DEPTH frames: the skaters, the puck and the referee move on, the rink stays. The bottom
score and clock boxes are masked; centre ice (the home team's logo) is kept per home team.

Rink pixel (u, v) = screen (x, y) + (camera_h, -camera_v) + (U0, V0): a fixed shift, so the picture is in the camera's
own units (one per screen pixel).

python analysis/vision/rink_mosaic.py VIDEO.timeline.json OUT.npz [STEP_FRAMES]"""
import bisect
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import replay_pack  # noqa: E402
from export_match import Capture  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
W, H = 320, 224
CAMV, CAMH = 0xBD18, 0xBD1C
V_RANGE, H_RANGE = (-260, 300), (-80, 80)      # the cameras seen, with room
U0, V0 = -H_RANGE[0], V_RANGE[1]               # rink pixel = screen + (cam_h + U0, V0 - cam_v)
PW, PH = W + H_RANGE[1] - H_RANGE[0], H + V_RANGE[1] - V_RANGE[0]
DEPTH = 31
HUD_TOP = 186                                  # the score and clock boxes: rows from here down (masked)


def s16(v):
    return v - 65536 if v & 0x8000 else v


class Truth:
    """The recordings' camera at any video second (the timeline's segments)."""

    def __init__(self, timeline):
        self.tl = timeline
        self.caps = {}

    def camera(self, v):
        seg = next((s for s in self.tl["segments"] if s[0] <= v < s[1]), None)
        if seg is None:
            return None
        name = self.tl["games"][seg[2]]
        if name not in self.caps:
            c = Capture(HOME / "captures" / name)
            ms = [c.ms(i) for i in range(c.count)]
            cv = np.array([s16(c.word(i, CAMV)) for i in range(c.count)])
            ch = np.array([s16(c.word(i, CAMH)) for i in range(c.count)])
            run = np.array([not (c.byte(i, 0xC2EA) & 1) for i in range(c.count)])     # gmode: the clock running
            self.caps[name] = (c, ms, cv, ch, run)
        c, ms, cv, ch, run = self.caps[name]
        t = replay_pack.at_ms(seg, v)
        i = max(0, bisect.bisect_right(ms, t) - 1)
        lo, hi = max(0, i - 4), min(len(ms), i + 5)
        lw, hw = max(0, i - 36), min(len(ms), i + 37)   # about half a second each way: wider than the timeline's error
        calm = cv[lw:hw].max() - cv[lw:hw].min() == 0 and ch[lw:hw].max() - ch[lw:hw].min() == 0 and bool(run[lw:hw].all())
        live = bool(run[lo:hi].all())          # live play only: faceoff line-ups and their close-up box stand still
        still = cv[lo:hi].max() - cv[lo:hi].min() <= 2 and ch[lo:hi].max() - ch[lo:hi].min() <= 2 and live
        moved = int(max(cv[lo:hi].max() - cv[lo:hi].min(), ch[lo:hi].max() - ch[lo:hi].min()))
        return int(cv[i]), int(ch[i]), bool(still), seg[2], i, moved, live, calm


def frames(video, step):
    import imageio_ffmpeg
    p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-threads", "1", "-i",
                          str(video), "-an", "-vsync", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE, creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
    n = 0
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        if n % step == 0:
            yield n, np.frombuffer(b, np.uint8).reshape(H, W, 3)
        n += 1
    p.wait()


def register(img, ref, u0, v0, reach=10, tol=40):
    """The shift within +-reach of (u0, v0) where the frame best matches the picture: the share of sampled pixels
    (above the score boxes) within tol of it (sprites differ, the rink agrees); coarse (every 2nd shift, every 6th
    pixel), then fine around the best. Returns (u, v, share)."""
    def share(u, v, sub):
        if u < 0 or v < 0 or u + W > PW or v + HUD_TOP > PH:
            return -1.0
        fs = img[:HUD_TOP:sub, ::sub].astype(np.int16)
        r = ref[v:v + HUD_TOP:sub, u:u + W:sub].astype(np.int16)
        return float((np.abs(fs - r).sum(axis=2) < tol).mean())
    coarse = max(((u0 + du, v0 + dv) for du in range(-reach, reach + 1, 2) for dv in range(-reach, reach + 1, 2)),
                 key=lambda uv: share(uv[0], uv[1], 6))
    best = max(((coarse[0] + du, coarse[1] + dv) for du in range(-2, 3) for dv in range(-2, 3)),
               key=lambda uv: share(uv[0], uv[1], 2))
    return best[0], best[1], share(best[0], best[1], 2)


def stack(tl, video, step, pick, refs=None, min_share=0.6):
    """Median pictures by home team from the frames pick() accepts, each placed by the camera and, with refs,
    nudged to where it matches its home team's reference picture best (frames matching under min_share left out)."""
    fps = tl.get("fps", 59.92)
    truth = Truth(tl)
    homes, rng, used, shifts = {}, np.random.default_rng(1), 0, []
    for n, img in frames(video, step):
        cam = truth.camera(n / fps)
        if cam is None or not pick(cam):
            continue
        cv, ch, _, game = cam[:4]
        home = tl["games"][game].rsplit("_", 1)[-1].split("-")[0]
        u0, v0 = ch + U0, V0 - cv
        if refs is not None:
            if home not in refs:
                continue
            u, v, share = register(img, refs[home], u0, v0)
            if share < min_share:
                continue
            shifts.append((u - u0, v - v0))
            u0, v0 = u, v
        if home not in homes:
            homes[home] = (np.zeros((DEPTH, PH, PW, 3), np.uint8), np.zeros((PH, PW), np.int32))
        stk, count = homes[home]
        sub = count[v0:v0 + HUD_TOP, u0:u0 + W]
        k = sub.copy()
        # reservoir sampling: each pixel keeps DEPTH frames drawn evenly from all that covered it
        slot = np.where(k < DEPTH, k, rng.integers(0, np.maximum(k, 1)))
        rows, cols = np.nonzero(slot < DEPTH)
        stk[slot[rows, cols], v0 + rows, u0 + cols] = img[rows, cols]
        sub += 1
        used += 1
    pictures, counts = {}, {}
    for home, (stk, count) in homes.items():
        pic = np.zeros((PH, PW, 3), np.uint8)
        filled = np.minimum(count, DEPTH)
        for d in range(1, DEPTH + 1):           # the median of however many frames each pixel kept
            sel = filled == d
            if sel.any():
                pic[sel] = np.median(stk[:d, sel], axis=0).astype(np.uint8)
        pictures[home] = pic
        counts[home] = np.minimum(count, 65535).astype(np.uint16)
    return pictures, counts, used, shifts


def build(timeline_path, out, step=6):
    """Pass 1: a reference from the frames of live play whose camera stood exactly still for about half a second
    each way (the timeline is good to a fraction of a second, not to a frame: a still camera over a wider window
    can't be misplaced by it); pass 2: every frame of live play, nudged onto the reference (the camera word and the screen's scroll
    can differ by a pixel or two, and the timeline by a frame), then the median."""
    tl = json.loads(Path(timeline_path).read_text())
    video = Path(timeline_path).with_name(tl["video"])
    refs, _, n1, _ = stack(tl, video, step, lambda cam: cam[7])
    print(f"pass 1: {n1} still frames, references for {sorted(refs)}")
    pics, counts, n2, shifts = stack(tl, video, step, lambda cam: cam[6], refs)
    from collections import Counter
    print(f"pass 2: {n2} frames placed; shifts from the camera word: {Counter(shifts).most_common(6)}")
    np.savez_compressed(out, **{f"game{h}": p for h, p in pics.items()}, **{f"count{h}": c for h, c in counts.items()},
                        **{f"ref{h}": p for h, p in refs.items()}, origin=np.array([U0, V0]))
    print(out)


if __name__ == "__main__":
    build(sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 6)
