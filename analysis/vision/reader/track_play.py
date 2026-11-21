"""An every-frame camera track of a video's live play (2026-11-20, the learning plan's step 1): camera_track.track
over the sync timeline's segments (each widened by MARGIN seconds), every other frame kept as lost.
python track_play.py VIDEO TIMELINE ROM OUT.npz [FIRST COUNT]"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scoring_map"))
import numpy as np
import lowload
import camera_track as C
MARGIN = 2.0
video, tl_path, rom, out = sys.argv[1:5]
first = int(sys.argv[5]) if len(sys.argv) > 5 else 0
count = int(sys.argv[6]) if len(sys.argv) > 6 else None
lowload.gentle()
tl = json.loads(Path(tl_path).read_text())
fps = tl["fps"]
ranges = [(int((s[0] - MARGIN) * fps), int((s[1] + MARGIN) * fps)) for s in tl["segments"]]
live = sum(b - a for a, b in ranges)
print(f"{len(ranges)} ranges, {live} frames of play (with margins)", flush=True)
t = time.time()
rows = C.track(Path(video), Path(rom), first, count, 1, only=ranges)
np.savez_compressed(out, rows=rows, step=np.array(1))
print(f"done: {len(rows)} frames, {int(rows[:, 4].sum())} placed, {time.time() - t:.0f} s", flush=True)
