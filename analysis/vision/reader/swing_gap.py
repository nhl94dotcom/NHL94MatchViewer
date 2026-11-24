"""Where the video's shot score falls short of the recording's (2026-11-23). For each recorded shot: the swing that
stands for it on the recording's side and on the video's (same team, release within 30 samples of the shot), their
scores, and each input's difference. Printed: how the shots split (both called, only the recording's, neither, no
video swing), and for those only the recording calls, each input's median on both sides and how often it differs much.
Needs swing_events.py test's READ_swing_recording.npz / READ_swing_video.npz.
python swing_gap.py READ.json ..."""
import sys
from collections import Counter

import numpy as np

from swing_events import FEATURES

TOL = dict(dist_net=12, off_centre=10, to_line=10, speed_after=1.0, aim_error=15, cross_x=20, cross_ok=0.5, speed_before=1.0,
           carried_before=3, next_owner=0.5, next_owner_t=6, deepest=15, nearest_net=15, puck_gap=6, heading_net=30,
           swing_len=4, released=0.5, best_aim=15, best_cross=20, best_speed=1.0, best_off=3)
split, rows = Counter(), []
for path in sys.argv[1:]:
    R = np.load(path.replace(".json", "_swing_recording.npz"))
    V = np.load(path.replace(".json", "_swing_video.npz"))

    def pick(D, f, team):
        c = [(abs(int(r) - f), j) for j, (r, (i, k)) in enumerate(zip(D["rel"], D["sw"])) if k // 6 == team and abs(int(r) - f) <= 30]
        if not c:
            return None
        near = [j for d, j in c if d <= min(c)[0] + 6]
        return max(near, key=lambda j: D["pr"][j])

    for f, team, xg in R["shots"]:
        a, b = pick(R, f, team), pick(V, f, team)
        if a is None:
            split["no recording swing"] += 1
        elif b is None:
            split["no video swing"] += 1
        else:
            ra, vb = R["pr"][a] >= 0.5, V["pr"][b] >= 0.5
            split["both called" if ra and vb else "recording only" if ra else "video only" if vb else "neither"] += 1
            if ra and not vb:
                rows.append((R["X"][a], V["X"][b], xg / 1000, float(V["pr"][b]), path, int(f)))
print(dict(split))
print("recording calls it, the video doesn't:", len(rows), "shots, xG", round(sum(r[2] for r in rows), 2))
A, B = np.array([r[0] for r in rows]), np.array([r[1] for r in rows])
for j, name in enumerate(FEATURES):
    far = np.abs(A[:, j] - B[:, j]) > TOL[name]
    print(f"  {name:15s} recording median {np.median(A[:, j]):8.1f}  video median {np.median(B[:, j]):8.1f}  differs much in {int(far.sum()):2d} of {len(rows)}")
both = Counter()
for a, b, *_ in rows:
    both[tuple(n for j, n in enumerate(FEATURES) if abs(a[j] - b[j]) > TOL[n])] += 1
print("the inputs that differ, shot by shot:")
for k, v in both.most_common(12):
    print("  ", v, k)
