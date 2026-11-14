"""Game events from a video's sound (2026-11-14; the video reader's events, for the stats that show why a game was won:
shots, checks, passes). The game plays its own sound for each (Genesis ram94: SFXshotfh / SFXshotbh +0-3, SFXpass
+0-3, SFXcheck +0-3, SFXpuckpost, SFXhorn, SFXwhistle ...), the same samples whatever the picture's quality.

The soundtrack (ffmpeg: mono, SR samples a second) as a log spectrogram (HOP 10 ms frames, BANDS log-spaced bands,
each band's level less its running median: what stands out of the crowd and the music). A kind's template: the
spectrogram around each event of that kind in the recordings of LEARN games (their video times through the timeline
of tools/video_sync.py: recording ms -> video second by each segment's rate), each patch aligned to the running mean
(+-ALIGN frames), averaged. Detection: each template's normalized correlation along the soundtrack, the peaks above a
threshold at least GAP apart. Checked on the other games: each detection against the recordings' events of that kind
(within TOL seconds): hits, misses, false alarms, by threshold.

python analysis/vision/audio_events.py VIDEO [--learn=0,1] [--kinds=shot,check,pass]
python analysis/vision/audio_events.py VIDEO --refs=SFX_REFS.npz   (sfx_refs.py's clean references: no learning from the video)"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
SR, HOP, WIN, BANDS = 16000, 160, 512, 48
PRE, POST, ALIGN, TOL, GAP = 5, 30, 12, 0.15, 0.12


def soundtrack(video):
    import imageio_ffmpeg
    cache = Path(str(video) + f".mono{SR}.npy")
    if cache.exists():
        return np.load(cache)
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-threads", "1", "-i",
                        str(video), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True,
                       creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
    a = np.frombuffer(p.stdout, np.float32).copy()
    np.save(cache, a)
    return a


def spectrogram(a):
    n = (len(a) - WIN) // HOP
    window = np.hanning(WIN).astype(np.float32)
    edges = np.unique(np.geomspace(3, WIN // 2, BANDS + 1).astype(int))
    out = np.zeros((n, len(edges) - 1), np.float32)
    for s in range(0, n, 20000):                       # in chunks: memory
        e = min(n, s + 20000)
        idx = np.arange(s, e)[:, None] * HOP + np.arange(WIN)[None, :]
        spec = np.abs(np.fft.rfft(a[idx] * window, axis=1)) ** 2
        cs = np.cumsum(spec, axis=1)
        out[s:e] = np.log(1e-6 + np.maximum(cs[:, edges[1:] - 1] - cs[:, edges[:-1] - 1], 0))
    # each band less its running median (2 s): what stands out
    k = 200
    med = np.zeros_like(out)
    for j in range(0, len(out), k):
        lo, hi = max(0, j - k), min(len(out), j + k)
        med[j:j + k] = np.median(out[lo:hi], axis=0)
    return out - med


def video_seconds(tl, gi, ms):
    for seg in tl["segments"]:
        if seg[2] != gi:
            continue
        import replay_pack
        v = seg[0] + (ms - seg[3]) * (1 + replay_pack.rate(seg)) / 1000
        if seg[0] <= v < seg[1]:
            return v
    return None


def events(video):
    """{kind: [(video second, game index)]} from the recordings: shots (shotList: attempts that were struck: on goal,
    wide, post, blocked), checks (hits), passes (passes tried), posts, goals."""
    import season
    tl = json.loads(Path(str(video) + ".timeline.json").read_text())
    out = {k: [] for k in ("shot", "check", "pass", "post", "goal")}
    for gi, name in enumerate(tl["games"]):
        m = season.load_match(HOME / "matches" / f"{name}.js")
        t = m["t"]

        def add(kind, f):
            v = video_seconds(tl, gi, t[f])
            if v is not None:
                out[kind].append((v, gi))
        for s in m.get("shotList", []):
            add("post" if s.get("result") == "post" else "shot", s["f"])
        for h in m.get("hits", []):
            add("check", h["f"])
        for p in m.get("passes", []):
            add("pass", p["f"])
        for g in m.get("goals", []):
            if "f" in g:
                add("goal", g["f"])
    return out, tl


def template(S, times):
    patches = []
    for v in times:
        c = int(round(v * SR / HOP))
        if c - PRE - ALIGN >= 0 and c + POST + ALIGN < len(S):
            patches.append(S[c - PRE - ALIGN:c + POST + ALIGN])
    if not patches:
        return None
    L = PRE + POST
    mean = np.mean([p[ALIGN:ALIGN + L] for p in patches], axis=0)
    for _ in range(3):                                   # align each patch to the mean, average again
        best = []
        for p in patches:
            sc = [np.sum(p[o:o + L] * mean) for o in range(2 * ALIGN + 1)]
            o = int(np.argmax(sc))
            best.append(p[o:o + L])
        mean = np.mean(best, axis=0)
    return mean - mean.mean()


def detect(S, tpl):
    """Normalized correlation of the template at every frame (the template's start)."""
    L = len(tpl)
    t = tpl / (np.linalg.norm(tpl) + 1e-9)
    n = len(S) - L
    out = np.zeros(n, np.float32)
    flat = t.ravel()
    for s in range(0, n, 50000):
        e = min(n, s + 50000)
        idx = np.arange(s, e)[:, None] + np.arange(L)[None, :]
        P = S[idx].reshape(e - s, -1)
        P = P - P.mean(axis=1, keepdims=True)
        out[s:e] = (P @ flat) / (np.linalg.norm(P, axis=1) + 1e-9)
    return out


def peaks(score, thr):
    gap = int(GAP * SR / HOP)
    idx = np.nonzero(score >= thr)[0]
    out, last = [], -10 ** 9
    for i in idx:
        if i - last > gap:
            out.append(i)
            last = i
        elif score[i] > score[out[-1]]:
            out[-1] = i
            last = i
    return out


def evaluate(found_s, truth_s):
    truth_s = sorted(truth_s)
    used = set()
    hits = 0
    for v in found_s:
        j = min(range(len(truth_s)), key=lambda q: abs(truth_s[q] - v)) if truth_s else None
        if j is not None and abs(truth_s[j] - v) <= TOL and j not in used:
            used.add(j)
            hits += 1
    return hits, len(truth_s) - len(used), len(found_s) - hits


KINDS = {"shot": range(20, 28), "pass": range(16, 20), "check": range(28, 32), "post": (37,), "goal": (4,)}


def resample(stereo, rate):
    """int16 stereo at `rate` -> float mono at SR (ffmpeg: no scipy here)."""
    import imageio_ffmpeg
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-f", "s16le", "-ar",
                        str(rate), "-ac", "2", "-i", "-", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       input=stereo.astype(np.int16).tobytes(), capture_output=True)
    return np.frombuffer(p.stdout, np.float32).copy()


def reference_templates(npz):
    """{kind: [template per effect number]} from sfx_refs.py's game: each effect's spectrogram at its exact start
    (the audio frame logged when lastsfx changed), averaged over its plays."""
    d = np.load(npz)
    rate = int(d["rate"])
    a = resample(d["audio"], rate)
    S = spectrogram(a)
    out = {}
    for kind, nums in KINDS.items():
        tpls = []
        for num in nums:
            starts = [int(round(at * SR / rate / HOP)) for f, n, at in d["events"] if n == num]
            patches = [S[c - PRE:c + POST] for c in starts if c - PRE >= 0 and c + POST < len(S)]
            if len(patches) >= 3:
                t = np.mean(patches, axis=0)
                tpls.append(t - t.mean())
        out[kind] = tpls
    return out


def main_refs(video, npz):
    """Each kind detected with the reference templates (the best of its effect numbers), on every game, against the
    recordings: found, missed, false, by threshold."""
    a = soundtrack(video)
    S = spectrogram(a)
    ev, tl = events(video)
    refs = reference_templates(npz)
    spans = [(min(s[0] for s in tl["segments"] if s[2] == g), max(s[1] for s in tl["segments"] if s[2] == g))
             for g in range(len(tl["games"]))]
    for kind, tpls in refs.items():
        if not tpls:
            print(f"{kind}: no reference")
            continue
        sc = np.max([np.nan_to_num(detect(S, t)) for t in tpls], axis=0)
        truth = [v for v, g in ev[kind]]
        near = []
        for v in truth:
            c = int(round(v * SR / HOP)) - PRE
            if 60 <= c < len(sc) - 60:
                w = sc[c - 60:c + 60]
                near.append(((int(np.argmax(w)) - 60) * HOP / SR, float(w.max())))
        offs = [o for o, _ in near]
        rnd = sc[np.random.default_rng(0).integers(0, len(sc), 5000)]
        print(f"{kind}: {len(tpls)} references, {len(truth)} events; best score near an event median "
              f"{np.median([b for _, b in near]):.2f} (random frames' 99th percentile {np.percentile(rnd, 99):.2f}); "
              f"its offset (s) p10/50/90 {np.round(np.percentile(offs, [10, 50, 90]), 2)}", flush=True)
        for thr in (0.4, 0.5, 0.6, 0.7, 0.8):
            found = [(i + PRE) * HOP / SR for i in peaks(sc, thr)]
            found = [v for v in found if any(a0 <= v <= b0 for a0, b0 in spans)]
            h, miss, fa = evaluate(found, truth)
            print(f"   threshold {thr}: found {h} of {len(truth)} ({100 * h / max(len(truth), 1):.0f}%), "
                  f"false {fa} ({100 * fa / max(len(found), 1):.0f}% of detections)", flush=True)


def main():
    if any(a.startswith("--refs=") for a in sys.argv):
        return main_refs(Path(sys.argv[1]), next(a.split("=", 1)[1] for a in sys.argv if a.startswith("--refs=")))
    video = Path(sys.argv[1])
    learn = [int(x) for x in next((a.split("=")[1] for a in sys.argv if a.startswith("--learn=")), "0,1").split(",")]
    kinds = next((a.split("=")[1] for a in sys.argv if a.startswith("--kinds=")), "shot,check,pass,post,goal").split(",")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
        import lowload
        lowload.gentle()
    except ImportError:
        pass
    a = soundtrack(video)
    S = spectrogram(a)
    ev, tl = events(video)
    games = sorted({g for v in ev.values() for _, g in v})
    test = [g for g in games if g not in learn]
    # the test games' video stretches (only their events are scored, and detections inside them)
    spans = {g: (min(s[0] for s in tl["segments"] if s[2] == g), max(s[1] for s in tl["segments"] if s[2] == g)) for g in games}
    for kind in kinds:
        tpl = template(S, [v for v, g in ev[kind] if g in learn])
        if tpl is None:
            print(f"{kind}: no events to learn from")
            continue
        np.save(Path(str(video) + f".tpl_{kind}.npy"), tpl)
        sc = detect(S, tpl)
        truth = [v for v, g in ev[kind] if g in test]
        print(f"{kind}: learned from {sum(1 for _, g in ev[kind] if g in learn)}, tested on {len(truth)}", flush=True)
        for thr in (0.3, 0.4, 0.5, 0.6, 0.7):
            found = [(i + PRE) * HOP / SR for i in peaks(sc, thr)]
            found = [v for v in found if any(spans[g][0] <= v <= spans[g][1] for g in test)]
            h, miss, fa = evaluate(found, truth)
            print(f"   threshold {thr}: found {h} of {len(truth)} ({100 * h / max(len(truth), 1):.0f}%), "
                  f"false {fa} ({100 * fa / max(len(found), 1):.0f}% of detections)", flush=True)


if __name__ == "__main__":
    main()
