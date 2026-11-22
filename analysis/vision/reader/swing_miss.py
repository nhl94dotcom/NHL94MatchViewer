"""Where the swing classifier fails on recordings (2026-11-22): python swing_miss.py MODEL.json MATCH_NAME ..."""
import collections, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import swing_events as S
model = json.loads(Path(sys.argv[1]).read_text())
home = Path.home() / "Documents" / "NHL94 Viewer" / "matches"
miss, false, tot = collections.Counter(), collections.Counter(), 0
ex = []
for name in sys.argv[2:]:
    m = S.load_js(home / f"{name}.js")
    sw = S.swings(m)
    X = np.array([S.features(m, i, k) for i, k in sw])
    pr = S.predict(model, X)
    rel = [S.release(m, i, k) for i, k in sw]
    used = set()
    for s in m["shotList"]:
        if s["kind"] not in ("shot", "one-timer") or s.get("team") not in (0, 1):
            continue
        tot += 1
        f, team = s["f"], s["team"]
        k = next((k for k in range(team * 6, team * 6 + 6) if m["role"][f * 12 + k] != "x" and int(m["roster"][f * 12 + k], 36) == s["idx"]), None)
        cand = [j for j, (i, kk) in enumerate(sw) if kk == k and -4 <= f - i <= 40]
        any_team = [j for j, (i, kk) in enumerate(sw) if kk // 6 == team and abs(m["t"][rel[j]] - m["t"][f]) <= 500]
        if any(pr[j] >= 0.5 for j in any_team):
            used.update(j for j in any_team if pr[j] >= 0.5)
            continue
        if not cand:
            why = "no swing by the shooter"
        else:
            j = max(cand, key=lambda j: pr[j])
            why = f"swing scored low, release estimate {'right' if abs(rel[j] - f) <= 3 else 'off by ' + ('4-10' if abs(rel[j] - f) <= 10 else '10+')}"
            if len(ex) < 14:
                ex.append((name[-7:], s["kind"], s.get("type"), s["result"], round(float(pr[j]), 2), rel[j] - f, dict(zip(S.FEATURES, [round(float(v), 1) for v in X[j]]))))
        miss[(why, s["kind"], s["result"])] += 1
    passes = {(p["f"], p["team"]) for p in m.get("passes", [])}
    others = [(s["f"], s["team"], s["kind"]) for s in m["shotList"] if s["kind"] not in ("shot", "one-timer")]
    for j, (i, k) in enumerate(sw):
        if pr[j] < 0.5 or j in used:
            continue
        r = rel[j]
        o = next((kind for f, t, kind in others if t == k // 6 and abs(f - r) <= 30), None)
        p_ = any(t == k // 6 and abs(f - r) <= 20 for f, t in passes)
        false["a shot the recording lists as '" + o + "'" if o else "a pass" if p_ else "nothing listed"] += 1
print("shots", tot, "missed", sum(miss.values()))
for k, v in miss.most_common(): print("  missed", v, k)
print("false", sum(false.values()), dict(false))
for e in ex: print("  ", e)
