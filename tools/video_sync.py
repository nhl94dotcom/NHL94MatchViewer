"""Where each helper recording's live play sits in a video of the session (2026-11-13; tools/replay_pack.py's timeline).

The video is RetroArch's own recording (every emulator frame), Genesis or SNES. The helper's recordings keep only live
play, timed by their own clock (`ms`), with no clock-of-day time, so they are found in the video by the camera: the
recordings keep the camera position every sample (SYSTEMS: Genesis $BD18 / $BD1C, SNES Vscroll / Hscroll), and the
video's rink scroll is measured frame to frame (phase correlation at half size, so half the units). Both are averaged
over SMOOTH frames (the retail SNES moves its picture on every other frame), and the directions are found by
calibrate() (Genesis + / -, SNES - / -). A stretch of play matches the video at one offset (video time - recording
time); each pause, instant replay, intermission or menu in the video adds to the offset from there on.

  1. measure     the video's scroll per frame (one ffmpeg pass at below-normal priority: about a minute for 37
                 minutes of video), saved beside the video as <video>.scroll.npz
  2. candidates  10-second stretches of each recording's camera movement matched in the video (normalised
                 cross-correlation of both scroll directions), the 12 best places each; a game is searched only where
                 it can be: after the previous game, leaving room for the games still to come
  3. path        one consistent placing (Viterbi): within a game the offset only grows, each change costing 2 + 0.1 a
                 second, since camera pans (after a faceoff ...) look alike all over a video and runs of false matches
                 win when changes are cheap; a stretch may be left out
  4. segments    runs at one offset; between two runs the step goes exactly at a clock jump if the recording has one
                 there (clock_jumps: live play the recording missed), else where the camera matches best and the
                 video's left-out frames look least like play (play_like) and show the least ice (a still camera matches
                 anywhere; a Genesis period break is black, a SNES pause keeps the frozen rink); each run's offset is
                 fitted as a line (the clocks differ by up to about 0.4%)

The Genesis frame counter ($B03E) doesn't step once a frame, so it can't place a recording. Checked on the user's
BOS-CHI series (2026-11-13, one 36:53 video, four games): every game in 3-4 runs of 24-53 checks, the steps 0.8 s at
the period breaks and one 5-6 s pause; a still a quarter-second before each of the 27 goals shows the clock one game
second above the goal's. And the user's TOR-NYI SNES video (39 minutes, four games): 1-6 runs a game of 5-69 checks,
all 25 goal stills within a game second; game 2's recording missed 3.5 s of play (its clock jumps P2 0:46 to 0:36).

python tools/video_sync.py VIDEO MATCH_NAME ... --out TIMELINE.json
  (the recordings in <home>/captures, the home NHL94_HOME or Documents/NHL94 Viewer). Prints each segment and the
  score of every check, then writes the timeline for replay_pack.py."""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_match import Capture  # noqa: E402

# Per system: the core's frame rate (the video's frames) and the camera words in the recordings (vertical,
# horizontal). Genesis: the camera $BD18 / $BD1C. SNES: the rink's scroll Vscroll $0D39 / Hscroll $0CED (ram94s.asm).
# Their directions against the video's scroll are found by calibrate() (Genesis: + / -).
SYSTEMS = {"genesis": {"fps": 59.92, "cam": (0xBD18, 0xBD1C)},
           "snes": {"fps": 60.0988, "cam": (0x0D39, 0x0CED)}}
FPS = SYSTEMS["genesis"]["fps"]
SMOOTH = 8           # frames: both scroll series are averaged over this many (smooth())
MEASURE_VERSION = 2  # measure()'s method: a cache made by another version (or of another file) is measured again
HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")


def video_size(video):
    import imageio_ffmpeg
    import re
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(video)], capture_output=True)
    m = re.search(rb"Video:.*?, (\d{3,4})x(\d{3,4})", p.stderr)
    return (int(m.group(1)), int(m.group(2))) if m else (320, 224)


def measure(video):
    """Per frame: the scroll from the previous frame (dy, dx at half size: 160x112 for the Genesis, 128x112 for the
    SNES) and the share of ice-coloured pixels (blue and green high, blue well above red: both systems' ice)."""
    cache = Path(str(video) + ".scroll.npz")
    st = Path(video).stat()
    stamp = np.array([st.st_size, int(st.st_mtime), MEASURE_VERSION])     # the video and the measure it was made with
    if cache.exists():
        d = np.load(cache)
        if "stamp" in d.files and np.array_equal(d["stamp"], stamp):
            return d["dy"].astype(float), d["dx"].astype(float), d["ice"]
    import imageio_ffmpeg
    vw, vh = video_size(video)
    W, H = vw // 2, vh // 2
    p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-threads", "1",
                          "-i", str(video), "-an", "-vsync", "passthrough", "-vf", f"scale={W}:{H}:flags=area",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE,
                         creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
    win = np.outer(np.hanning(H), np.hanning(W)).astype(np.float32)
    prev, dys, dxs, ice = None, [], [], []
    while True:
        b = p.stdout.read(W * H * 3 * 512)
        if not b:
            break
        k = len(b) // (W * H * 3)
        f = np.frombuffer(b[:k * W * H * 3], np.uint8).reshape(k, H, W, 3).astype(np.float32)
        r, g, bl = f[..., 0], f[..., 1], f[..., 2]
        ice.extend(((bl > 180) & (g > 180) & (bl - r > 25)).mean(axis=(1, 2)).tolist())
        gray = 0.3 * r + 0.59 * g + 0.11 * bl
        gray -= gray.mean(axis=(1, 2), keepdims=True)
        F = np.fft.rfft2(gray * win)
        before = np.concatenate([prev[None] if prev is not None else F[:1], F[:-1]])
        R = F * np.conj(before)
        R /= np.abs(R) + 1e-6
        c = np.fft.irfft2(R, s=(H, W)).reshape(k, -1)
        y, x = np.divmod(c.argmax(axis=1), W)
        dys.extend(np.where(y > H // 2, y - H, y).tolist())
        dxs.extend(np.where(x > W // 2, x - W, x).tolist())
        prev = F[-1]
    p.wait()
    np.savez(cache, dy=np.array(dys), dx=np.array(dxs), ice=np.array(ice), stamp=stamp)
    return np.array(dys, float), np.array(dxs, float), np.array(ice)


def system_of(name):
    c = Path(HOME / "captures" / name / "capture.json")
    return json.loads(c.read_text()).get("system", "genesis") if c.exists() else "genesis"


def camera(name):
    """A recording's camera velocity per video frame (its own clock put on the frame grid), vertical and horizontal,
    halved (the video is measured at half size); the directions are calibrate()'s."""
    c = Capture(HOME / "captures" / name)
    va, ha = SYSTEMS[system_of(name)]["cam"]
    s16 = lambda v: v - 65536 if v >= 32768 else v
    ms = np.array([c.ms(i) for i in range(c.count)], float)
    a = np.array([s16(c.word(i, va)) for i in range(c.count)], float)
    b = np.array([s16(c.word(i, ha)) for i in range(c.count)], float)
    grid = np.arange(int(ms[-1] / 1000 * FPS) + 1) / FPS * 1000
    A, B = np.interp(grid, ms, a) / 2, np.interp(grid, ms, b) / 2
    return np.diff(A, prepend=A[0]), np.diff(B, prepend=B[0]), ms[-1]


def smooth(a, k=SMOOTH):
    """A moving average over k frames: the retail SNES moves its picture on every other frame (0, 2, 0, 2 ...), so a
    frame's slip between the recording's samples and the video would otherwise wreck the match (2026-11-13: the
    BOS-CHI-style frame-by-frame match found nothing on a SNES video; smoothed, the vertical scroll matched)."""
    return np.convolve(a, np.ones(k) / k, mode="same")


def calibrate(cam, dy, dx, L=600, n=10):
    """The directions (sy, sx) that match the camera to the video's scroll: for each of the four, the best match of
    up to n stretches with movement anywhere in the video, summed; the largest wins. Prints the four sums."""
    vy, vx, _ = cam
    starts = [s for s in range(0, len(vy) - L, L) if vy[s:s + L].std() + vx[s:s + L].std() > 0.5][:n]
    score = {}
    for sy in (1, -1):
        for sx in (1, -1):
            score[(sy, sx)] = sum(float(np.nan_to_num(ncc(sy * vy[s:s + L], dy) + ncc(sx * vx[s:s + L], dx),
                                                      nan=-2).max()) for s in starts)
    best = max(score, key=score.get)
    print("directions (vertical, horizontal):", ", ".join(f"{k}: {v:.1f}" for k, v in score.items()), "->", best)
    return best


def ncc(chunk, sig):
    """Normalised cross-correlation of chunk against every position in sig."""
    L = len(chunk)
    c = chunk - chunk.mean()
    e = (c * c).sum()
    if e < 1e-6 or len(sig) < L:
        return np.full(max(1, len(sig) - L + 1), -1.0)
    n = 1 << int(np.ceil(np.log2(len(sig) + L)))
    corr = np.fft.irfft(np.fft.rfft(sig, n) * np.conj(np.fft.rfft(c, n)), n)[:len(sig) - L + 1]
    cs, cs2 = np.concatenate([[0], np.cumsum(sig)]), np.concatenate([[0], np.cumsum(sig * sig)])
    s1, s2 = cs[L:] - cs[:-L], cs2[L:] - cs2[:-L]
    return corr / np.sqrt(np.maximum(s2 - s1 * s1 / L, 1e-6) * e)


def candidates(vy, vx, dy, dx, lo=0, hi=None, L=600, hop=300, K=12):
    """For each 5-second stretch with camera movement: (recording frame, [(video frame of its start, score)] the K best
    places in the video between frames lo + the stretch's own place and hi - what is left of the recording after it,
    at least half a second apart)."""
    out = []
    hi = len(dy) if hi is None else hi
    for s in range(0, len(vy) - L, hop):
        if vy[s:s + L].std() + vx[s:s + L].std() < 0.3:
            continue
        a, b = lo + s, min(len(dy), hi - (len(vy) - s - L))
        if b - a < L:
            continue
        tot = ncc(vy[s:s + L], dy[a:b]) + ncc(vx[s:s + L], dx[a:b])
        tot = np.nan_to_num(tot, nan=-2.0)
        best = []
        for j in np.argsort(tot)[::-1]:
            if len(best) == K or tot[j] < 0.6:
                break
            if all(abs(a + j - v) > 30 for v, _ in best):
                best.append((int(a + j), float(tot[j])))
        if best:
            out.append((s, best))
    return out


def path(games, change=2.0, per_s=0.1, longest=400.0):
    """The best consistent placing of every stretch (Viterbi): within a game a stretch's offset (video - recording) is
    at or past the previous one's (the video only adds pauses), by at most `longest` seconds, each change costing
    `change` plus `per_s` a second (a long jump needs much more agreement than a pause's few seconds); the games follow one another in the video. A stretch may be left out (score 0). Returns per game the
    taken (recording frame, offset, score)."""
    items = [(gi, s, c) for gi, cands in enumerate(games) for s, c in cands]
    # states: per item, its candidates plus "left out" (None); the best total ending in each
    prev_states = [(None, None, 0.0, None)]   # (item index, candidate, total, back-pointer)
    layers = []
    for n, (gi, s, cands) in enumerate(items):
        layer = []
        for cand in list(cands) + [None]:
            best = None
            for k, st in enumerate(prev_states):
                tot = st[2]
                if cand is not None:
                    ok, add = True, cand[1]
                    last = st[4] if len(st) > 4 else None
                    if last is not None:
                        lgi, ls, lv = last
                        off, loff = cand[0] - s, lv - ls
                        if lgi == gi:
                            if off < loff - 12 or off > loff + longest * FPS:
                                ok = False
                            elif abs(off - loff) > 12:
                                add -= change + per_s * (off - loff) / FPS
                        elif cand[0] <= lv:
                            ok = False
                    if not ok:
                        continue
                    tot += add
                if best is None or tot > best[2]:
                    lastref = (gi, s, cand[0]) if cand is not None else (st[4] if len(st) > 4 else None)
                    best = (n, cand, tot, k, lastref)
            if best:
                layer.append(best)
        layers.append(layer)
        prev_states = layer
    # back-track
    k = max(range(len(prev_states)), key=lambda i: prev_states[i][2])
    taken = []
    for n in range(len(layers) - 1, -1, -1):
        st = layers[n][k]
        if st[1] is not None:
            gi, s, _ = items[n]
            taken.append((gi, s, st[1][0] - s, st[1][1]))
        k = st[3]
    taken.reverse()
    return [[(s, off, sc) for g, s, off, sc in taken if g == gi] for gi in range(len(games))]


def play_like(dy, dx, ice, window=15):
    """Per video frame: does it look like live play, the rink on screen and scrolling within a quarter-second either
    side? A pause (the Genesis menu screen, the SNES menu over a frozen rink), a period break, a black screen don't.
    (The ice share alone isn't enough: the SNES pause and "Period Over" keep the frozen rink on screen.)"""
    moving = np.convolve(((dy != 0) | (dx != 0)).astype(float), np.ones(2 * window + 1), mode="same") > 0
    return ((ice > 0.25) & moving).astype(float)


def split(vy, vx, dy, dx, play, r1, r2, o1, o2, weight=3.0):
    """The recording frame in [r1, r2] where the offset steps from o1 to o2: the camera matched best, and the video's
    frames left out (o2 - o1 of them, a pause, a replay or the break between periods) looking as little like live play
    as can be (play_like; a still camera matches anywhere: the step then goes where play stops on screen)."""
    ts = np.arange(r1, r2 + 1)
    e1 = np.abs(dy[np.clip(ts + o1, 0, len(dy) - 1)] - vy[ts]) + np.abs(dx[np.clip(ts + o1, 0, len(dx) - 1)] - vx[ts])
    e2 = np.abs(dy[np.clip(ts + o2, 0, len(dy) - 1)] - vy[ts]) + np.abs(dx[np.clip(ts + o2, 0, len(dx) - 1)] - vx[ts])
    c1 = np.concatenate([[0], np.cumsum(e1)])
    tot = c1 + np.concatenate([np.cumsum(e2[::-1])[::-1], [0]])
    ci = np.concatenate([[0], np.cumsum(play)])
    a = np.clip(np.arange(r1, r2 + 2) + o1, 0, len(play))
    b = np.clip(np.arange(r1, r2 + 2) + o2, 0, len(play))
    tot = tot + weight * (ci[b] - ci[a])
    k = int(np.argmin(tot))
    return r1 + k


def clock_jumps(name):
    """Recording frames (on the video's frame grid) where the recording missed live play: its game clock jumps 3+ game
    seconds from one sample to the next within a period while its own timer barely moved (2026-11-13: SNES TOR-NYI
    game 2, P2 0:46 to 0:36). A step found near one goes exactly there."""
    from season import load_match
    m = load_match(HOME / "matches" / f"{name}.js")
    t, clock, period = m["t"], m["clock"], m["period"]
    return [int(t[k] / 1000 * FPS) for k in range(1, len(t))
            if period[k] == period[k - 1] and clock[k - 1] - clock[k] >= 3 and t[k] - t[k - 1] < 500]


def timeline(video, names):
    global FPS
    systems = {system_of(n) for n in names}
    if len(systems) != 1:
        raise SystemExit(f"the games are from more than one system: {systems}")
    system = systems.pop()
    FPS = SYSTEMS[system]["fps"]
    dy, dx, ice = measure(video)
    play = play_like(dy, dx, ice) + ice     # a step goes where the video doesn't look like play, and off the rink
    big = (np.abs(dy) > 12) | (np.abs(dx) > 12)
    dy, dx = smooth(np.where(big, 0, dy)), smooth(np.where(big, 0, dx))
    cams = [(smooth(vy), smooth(vx), last) for vy, vx, last in (camera(name) for name in names)]
    sy, sx = calibrate(cams[0], dy, dx)
    cams = [(sy * vy, sx * vx, last) for vy, vx, last in cams]
    segs, lo = [], 0
    for gi, name in enumerate(names):
        vy, vx, last_ms = cams[gi]
        later = sum(len(c[0]) for c in cams[gi + 1:])    # the games still to come need at least their live length
        kept = path([candidates(vy, vx, dy, dx, lo, len(dy) - later)])[0]
        if not kept:
            raise SystemExit(f"{name}: not found in the video")
        runs = [[kept[0]]]
        for k in kept[1:]:
            (runs[-1] if abs(k[1] - runs[-1][-1][1]) <= 12 else runs.append([k]) or runs[-1]).append(k)
        bounds = [0]
        for a, b in zip(runs, runs[1:]):
            r1, r2 = a[-1][0] + 300, b[0][0] + 300
            o1, o2 = int(np.median([k[1] for k in a])), int(np.median([k[1] for k in b]))
            lo_r, hi_r = min(r1, r2), max(r1, r2)
            jumps = [j for j in clock_jumps(name) if lo_r - 300 <= j <= hi_r + 300]
            bounds.append(jumps[0] if jumps else split(vy, vx, dy, dx, play, lo_r, hi_r, o1, o2))
        bounds.append(len(vy))
        for run, b0, b1 in zip(runs, bounds, bounds[1:]):
            s = np.array([k[0] + 300 for k in run], float)
            o = np.array([k[1] for k in run], float)
            fit = np.polyfit(s, o, 1) if len(run) >= 3 and np.ptp(s) > 600 else [0.0, float(np.median(o))]
            off = lambda r: fit[0] * r + fit[1]
            v0, v1 = (b0 + off(b0)) / FPS, (b1 + off(b1)) / FPS
            segs.append([round(v0, 3), round(v1, 3), gi, round(b0 / FPS * 1000), round(fit[0], 6), len(run),
                         round(float(np.mean([k[2] for k in run])), 2)])
            print(f"{name}: recording {b0 / FPS:7.1f}-{b1 / FPS:7.1f} s -> video {v0:7.1f}-{v1:7.1f} s "
                  f"(offset {off(b0) / FPS:6.2f} s, {len(run)} checks, score {np.mean([k[2] for k in run]):.2f})")
        lo = int(segs[-1][1] * FPS)
    return {"video": Path(video).name, "system": system, "directions": [sy, sx], "fps": FPS,
            "duration": round(len(dy) / FPS, 2), "games": names,
            "segments": [s[:4] + [s[4]] for s in segs], "checks": [s[5:] for s in segs]}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
    if out:
        args = [a for a in args if a != str(out) and Path(a) != out]
    tl = timeline(Path(args[0]), args[1:])
    if out:
        out.write_text(json.dumps(tl, indent=1))
        print("written", out)


if __name__ == "__main__":
    main()
