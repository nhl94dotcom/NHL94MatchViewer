"""Shots from swings (2026-11-22). Every shot and most passes begin with the same swing: the skater's sprite goes onto
his shooting frames, and at the release he is on the fifth of the six for his facing (frame 100 + 6d: all 1,230
recorded shots). A read gets sprite frames right, and shows that frame at 91% of recorded shots (swing_diag.py),
the dangerous ones too, where the old shot finder (the puck leaving a carrier toward the net) found two in three.

A swing here: a skater's frame coming onto 100 + 6d after 3+ samples off it. What tells a shot from a pass is learnt,
from recorded games only (their match files hold the same things a read does: positions, frames, the puck, the
carrier): each swing labelled by the recording's own shot and pass lists, described by FEATURES (where he is from the
net he attacks, the puck's speed and line after the release, whether it was his before, who has it next), and a
boosted set of one-feature thresholds (numpy; no other package) fitted to shot or not (two-level trees since the same day: one-feature thresholds alone
missed combinations). A one-timer: a shot whose
swinger hadn't the puck before it.

python swing_events.py train OUT.json [--skip NAME_PART ...]     recorded Genesis games in <home>/matches, bot games
                                                                 and names containing a --skip part left out
python swing_events.py test MODEL.json READ.json                 a read (NHL94_INV_*, TEST_GAME as pseudo_run_any.py):
    the shots it finds against the recording's (same team within 0.5 s), and xG by team (xg_from_read's way)"""
import json
import math
import sys
from pathlib import Path

import numpy as np

SWING = {f for f in range(96, 144) if (f - 96) % 6}      # the swing frames: six for each of the eight facings, less
                                                         # the first (the plain stance: skating shows it all game)
FAST = 2.2                                               # units a sample: a puck released, not carried
AFTER, BEFORE = 45, 10
FEATURES = ["dist_net", "off_centre", "to_line", "speed_after", "aim_error", "cross_x", "cross_ok", "speed_before",
            "carried_before", "next_owner", "next_owner_t", "deepest", "nearest_net", "puck_gap", "heading_net", "swing_len", "released"]


def frame_of(m, i, k):
    return int("".join(m["frame"][(i * 12 + k) * 3:(i * 12 + k) * 3 + 3]), 16)


def xy(m, i, k):
    return m["pos"][(i * 12 + k) * 2], m["pos"][(i * 12 + k) * 2 + 1]


def attacks_top(m, i, team):
    """As xg.attacks_top: the other team's goalie is at the net this team attacks."""
    for side, sign in ((team, -1), (1 - team, 1)):
        for k in range(side * 6, side * 6 + 6):
            if m["role"][i * 12 + k] == "0":
                return (xy(m, i, k)[1] > 0) == (sign > 0)
    per = m["period"][i] if isinstance(m.get("period"), list) else 0
    return (team == 0) == (per in (0, 2))


def release2(m, i0, k, look=40):
    """(sample, found): the sample the puck leaves the swinger: the first from the swing's start with the puck moving
    at FAST or more over the next 3 samples and 5 or more units farther from him at their end (a skater gliding with
    the puck through a slapshot's wind-up keeps it at his stick: no release yet); none within `look`: 5 samples in,
    not found (a swing cut short, or a swing at a puck that never came)."""
    n = len(m["t"])
    P = m["puck"]
    for i in range(i0, min(n - 4, i0 + look)):
        sp = math.hypot(P[3 * (i + 3)] - P[3 * i], P[3 * (i + 3) + 1] - P[3 * i + 1]) / 3
        x, y = xy(m, i, k)
        x3, y3 = xy(m, i + 3, k)
        g0 = math.hypot(P[3 * i] - x, P[3 * i + 1] - y)
        if sp >= FAST and g0 <= 30 and math.hypot(P[3 * (i + 3)] - x3, P[3 * (i + 3) + 1] - y3) >= g0 + 5:
            return i, True
    return min(n - 1, i0 + 5), False


def release(m, i0, k, look=40):
    return release2(m, i0, k, look)[0]


def swings(m):
    """[(swing start, record)]: each skater's frame coming onto his shooting frames after 3+ samples off them."""
    n = len(m["t"])
    out = []
    for k in range(12):
        off = 3
        for i in range(n):
            if m["role"][i * 12 + k] in "0x":
                off = 3
                continue
            on = frame_of(m, i, k) in SWING
            if on and off >= 3:
                out.append((i, k))
            off = 0 if on else off + 1
    return sorted(out)


def features(m, i0, k):
    n = len(m["t"])
    P, owner = m["puck"], m["owner"]
    i, got = release2(m, i0, k)
    team = k // 6
    gl = 264 if attacks_top(m, i, team) else -264
    sg = 1 if gl > 0 else -1
    x, y = xy(m, i, k)
    px, py = P[3 * i], P[3 * i + 1]
    j = min(n - 1, i + 6)
    dt = max(1, j - i)
    vx, vy = (P[3 * j] - px) / dt, (P[3 * j + 1] - py) / dt
    sp = math.hypot(vx, vy)
    to_net = math.atan2(gl - py, -px)
    aim_error = abs((math.degrees(math.atan2(vy, vx) - to_net) + 180) % 360 - 180) if sp > 0.3 else 180.0
    cross_x = px + vx * (gl - py) / vy if vy * sg > 0.2 else 999.0
    b = max(0, i - 6)
    sb = math.hypot(px - P[3 * b], py - P[3 * b + 1]) / max(1, i - b)
    carried = sum(owner[q] == k for q in range(max(0, i0 - BEFORE), i0 + 1))
    nxt, nt, deep, near = 0, AFTER, -999.0, 999.0
    for q in range(i + 1, min(n, i + AFTER + 1)):
        deep = max(deep, sg * P[3 * q + 1])
        near = min(near, math.hypot(P[3 * q], P[3 * q + 1] - gl))
        o = owner[q]
        if nxt == 0 and o >= 0 and q > i + 3:
            if o == k:
                nxt = 1
            elif o // 6 == team:
                nxt = 2
            elif m["role"][q * 12 + o] == "0":
                nxt = 4
            else:
                nxt = 3
            nt = q - i
    f = frame_of(m, i0, k)
    d = (f - 96) // 6                                        # facing 0-7, 0 up the screen
    face = math.radians(90 - 45 * d)
    heading_net = abs((math.degrees(face - math.atan2(gl - y, -x)) + 180) % 360 - 180)
    return [math.hypot(x, gl - y), abs(x), sg * (gl - y), sp, aim_error, min(abs(cross_x), 200.0), float(abs(cross_x) <= 26),
            sb, carried, nxt, nt, deep, near, math.hypot(x - px, y - py), heading_net, i - i0, float(got)]


def labels(m, sw, before=4, after=40):
    """Each swing's label from the recording's lists: 2 one-timer, 1 shot, 0 a pass or nothing. A recorded shot labels
    one swing: the shooter's, starting up to `after` samples before it, whose release estimate is nearest its sample
    (a wind-up cut short just before the shot is its own swing, and no shot)."""
    ro = m["roster"]
    out = [0] * len(sw)
    rel = {}
    for s in m.get("shotList", []):
        if s["kind"] not in ("shot", "one-timer") or s.get("team") not in (0, 1):
            continue
        cand = [j for j, (i, k) in enumerate(sw) if k // 6 == s["team"] and m["role"][i * 12 + k] not in "0x"
                and int(ro[i * 12 + k], 36) == s["idx"] and -before <= s["f"] - i <= after]
        if cand:
            for j in cand:
                if j not in rel:
                    rel[j] = release(m, *sw[j])
            best = min(cand, key=lambda j: abs(rel[j] - s["f"]))
            out[best] = 2 if s["kind"] == "one-timer" else 1
    return out


# ---- a small boosted model: two-level trees (a threshold, then one on each side), logistic loss; numpy only
def _best_split(X, g, h, idx, cuts):
    best = None
    G, H = g[idx].sum(), h[idx].sum()
    for j, cs in enumerate(cuts):
        col = X[idx, j]
        for c in cs:
            left = col <= c
            gl_, hl = g[idx][left].sum(), h[idx][left].sum()
            gain = gl_ * gl_ / (hl + 1) + (G - gl_) ** 2 / (H - hl + 1)
            if best is None or gain > best[0]:
                best = (gain, j, float(c))
    return best


def fit(X, y, rounds=250, rate=0.1, w=None):
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    w = np.ones(len(y)) if w is None else np.asarray(w, float)
    F0 = math.log(max(y.mean(), 1e-6) / max(1 - y.mean(), 1e-6))
    F = np.full(len(y), F0)
    cuts = [np.unique(np.quantile(X[:, j], np.linspace(0.04, 0.96, 24))) for j in range(X.shape[1])]
    trees = []
    every = np.arange(len(y))
    for _ in range(rounds):
        p = 1 / (1 + np.exp(-F))
        g = w * (y - p)
        h = w * (p * (1 - p) + 1e-6)
        _, j, c = _best_split(X, g, h, every, cuts)
        tree = [j, c]
        for side in (X[:, j] <= c, X[:, j] > c):
            idx = every[side]
            if len(idx) < 40:
                v = rate * g[idx].sum() / (h[idx].sum() + 1)
                tree.append([0, 1e18, v, v])
                F[idx] += v
                continue
            _, j2, c2 = _best_split(X, g, h, idx, cuts)
            l2 = X[idx, j2] <= c2
            a = rate * g[idx][l2].sum() / (h[idx][l2].sum() + 1)
            b = rate * g[idx][~l2].sum() / (h[idx][~l2].sum() + 1)
            tree.append([j2, c2, a, b])
            F[idx] += np.where(l2, a, b)
        trees.append(tree)
    return dict(base=F0, trees=trees, features=FEATURES)


def predict(model, X):
    X = np.asarray(X, float)
    F = np.full(len(X), model["base"])
    for j, c, left, right in model["trees"]:
        side = X[:, j] <= c
        F += np.where(side, np.where(X[:, left[0]] <= left[1], left[2], left[3]),
                      np.where(X[:, right[0]] <= right[1], right[2], right[3]))
    return 1 / (1 + np.exp(-F))


def load_js(path):
    s = Path(path).read_text(encoding="utf-8")
    return json.loads(s[s.index("{"):s.rindex("}") + 1])


def train(out, skip):
    home = Path.home() / "Documents" / "NHL94 Viewer" / "matches"
    X, y, games = [], [], 0
    for p in sorted(home.glob("*.js")):
        if p.name == "season.js" or any(s in p.name for s in skip):
            continue
        try:
            m = load_js(p)
            summ = json.loads(p.with_name(p.stem + ".summary.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        if m.get("system") != "genesis" or summ.get("bot"):
            continue
        sw = swings(m)
        lab = labels(m, sw)
        for (i, k), l in zip(sw, lab):
            X.append(features(m, i, k))
            y.append(l)
        games += 1
        shots = sum(1 for s in m.get("shotList", []) if s["kind"] in ("shot", "one-timer"))
        print(p.stem, "swings", len(sw), "labelled shots", sum(l > 0 for l in lab), "of", shots, flush=True)
    X, y = np.array(X), np.array(y)
    np.savez_compressed(str(out).replace(".json", "_data.npz"), X=X, y=y)
    model = fit(X, y > 0)
    pr = predict(model, X)
    model["games"] = games
    Path(out).write_text(json.dumps(model))
    for thr in (0.3, 0.5, 0.7):
        hit = pr >= thr
        print(f"training fit at {thr}: shots found {int((hit & (y > 0)).sum())} of {int((y > 0).sum())}, false {int((hit & (y == 0)).sum())} (of {int((y == 0).sum())} other swings)")
    use = np.zeros(len(FEATURES))
    for j, c, left, right in model["trees"]:
        use[j] += 1
        use[left[0]] += 0.5
        use[right[0]] += 0.5
    print("splits by feature:", {FEATURES[j]: float(use[j]) for j in np.argsort(-use)})


def test(model_path, read_path):
    model = json.loads(Path(model_path).read_text())
    g = {"__name__": "swing_test", "__file__": str(Path(__file__).with_name("pseudo_run_any.py"))}
    src = Path(__file__).with_name("pseudo_run_any.py").read_text(encoding="utf-8").split("total = {}")[0]
    argv = sys.argv
    sys.argv = [argv[0], read_path]
    exec(src, g)
    sys.argv = argv
    PM, m, vf, maps, ROMP = g["PM"], g["m"], g["vf"], g["maps"], g["ROMP"]
    import xg as XG
    rows = json.loads(Path(read_path).read_text())
    fis = [r["fi"] for r in rows]
    qs = np.nonzero((vf >= min(fis)) & (vf <= max(fis)))[0]
    q0, q1 = int(qs[0]), int(qs[-1]) + 1
    tm = PM.slice_match(m, q0, q1)
    truth = PM.analyse(tm, str(ROMP))
    pm = PM.build(m, vf, rows, maps, q0, q1)
    pm["frame"] = "".join(pm["frame"]) if not isinstance(pm["frame"], str) else pm["frame"]
    name = Path(read_path).stem
    # the truth: the match file's own shots in this stretch (its xG, aim and all; the slice analysed again without the
    # pads lists about a fifth more "shots" that the real file doesn't have)
    T = [dict(s, f=s["f"] - q0) for s in m.get("shotList", []) if s["kind"] in ("shot", "one-timer") and s.get("team") in (0, 1) and q0 <= s["f"] < q1]
    # the upper bound: the same finder on the recording's own slice
    for label, mm in (("recording", tm), ("video", pm)):
        sw = swings(mm)
        if not sw:
            print(name, label, "no swings")
            continue
        X = np.array([features(mm, i, k) for i, k in sw])
        pr = predict(model, X)
        for thr in (0.5,):
            found = []
            for (i, k), p in zip(sw, pr):                    # one call a swing: a second within 30 samples is the same
                if p < thr:
                    continue
                r = release(mm, i, k)
                if found and any(k2 == k and abs(r2 - r) <= 30 for r2, k2, _ in found):
                    continue
                found.append((r, k, p))
            used, hit, hi_hit, pair = set(), 0, 0, {}
            for s in T:
                ta = truth["t"][s["f"]]
                best = None
                for j, (i, k, p) in enumerate(found):
                    if j in used or k // 6 != s["team"]:
                        continue
                    d = abs(mm["t"][i] - ta)
                    if d <= 500 and (best is None or d < best[0]):
                        best = (d, j)
                if best:
                    used.add(best[1])
                    pair[best[1]] = s
                    hit += 1
                    hi_hit += (s.get("xg") or 0) >= 0.3
            if label == "video":                              # why each recorded shot was missed
                import collections
                why = collections.Counter()
                matched_t = set()
                used2 = set()
                for s in T:
                    ta = truth["t"][s["f"]]
                    best = None
                    for j, (i, k, p) in enumerate(found):
                        if j in used2 or k // 6 != s["team"]:
                            continue
                        d = abs(mm["t"][i] - ta)
                        if d <= 500 and (best is None or d < best[0]):
                            best = (d, j)
                    if best:
                        used2.add(best[1])
                        continue
                    f = s["f"]
                    shk = next((k for k in range(s["team"] * 6, s["team"] * 6 + 6) if tm["role"][f * 12 + k] != "x"
                                and int(tm["roster"][f * 12 + k], 36) == s["idx"]), None)
                    tx, ty = xy(tm, f, shk) if shk is not None else (s["x"], s["y"])
                    near = [j for j, (i, k) in enumerate(sw) if k // 6 == s["team"] and -45 <= f - i <= 10
                            and math.hypot(xy(mm, min(len(mm["t"]) - 1, max(i, f)), k)[0] - tx, xy(mm, min(len(mm["t"]) - 1, max(i, f)), k)[1] - ty) <= 15]
                    if not near:
                        why["no swing read near the shooter"] += 1
                    else:
                        j = max(near, key=lambda j: pr[j])
                        r, got = release2(mm, *sw[j])
                        why[("release found" if got else "no release found") + (", timing right" if abs(r - f) <= 4 else ", timing off") + f", scored {'0.3-0.5' if pr[j] >= 0.3 else 'under 0.3'}"] += 1
                print(f"{name} video misses:", dict(why))
                Path(read_path.replace(".json", "_swingwhy.json")).write_text(json.dumps(dict(why)))
            hi = sum((s.get("xg") or 0) >= 0.3 for s in T)
            print(f"{name} {label}: swings {len(sw)}, called shots {len(found)}; recorded shots found {hit} of {len(T)} (xG 0.3+: {hi_hit} of {hi}), false {len(found) - len(used)}")
        if label == "video":
            lab = np.zeros(len(sw), int)                     # each recorded shot labels the nearest swing of its team
            rels = [release(mm, i, k) for i, k in sw]        # within 0.5 s (the cross-validated training's video part)
            for s in T:
                ta = truth["t"][s["f"]]
                c = [(abs(mm["t"][rels[j]] - ta), j) for j, (i, k) in enumerate(sw) if k // 6 == s["team"] and abs(mm["t"][rels[j]] - ta) <= 500]
                if c:
                    lab[min(c)[1]] = 1
            np.savez_compressed(read_path.replace(".json", "_swingdata.npz"), X=X, y=lab)
            res = dict(name=name, shots=len(T), found=hit, called=len(found), false=len(found) - len(used), hi=hi, hi_found=hi_hit)
            # xG by team, as xg_from_read: team-mean ratings, the aim's side from the flight, heights averaged
            first = {}
            for r in tm.get("work", []):
                first.setdefault(r[1], r[2:])
            role0 = tm["role"][:12]
            work, grow = [], {}
            for team in (0, 1):
                sk = [first[k] for k in range(team * 6, team * 6 + 6) if k in first and role0[k] not in "0x"]
                mean = [round(sum(c) / len(c)) for c in zip(*sk)] if sk else [64, 15, 15, 15, 15, 15]
                grow[team] = next((first[k] for k in range(team * 6, team * 6 + 6) if k in first and role0[k] == "0"), None)
                work += [[0, k, *mean] for k in range(team * 6, team * 6 + 6)]
            HEIGHTS = {1: [(1, .30), (2, .68), (3, .02)], -1: [(7, .30), (6, .68), (5, .02)], 0: [(0, .45), (8, .27), (4, .27)]}
            rom_bytes = Path(ROMP).read_bytes()
            P = pm["puck"]
            tot = [0.0, 0.0]
            n = len(pm["t"])
            per = []
            for jf, (i, k, p) in enumerate(found):
                team = k // 6
                f = min(n - 1, i)
                la = XG.launched(pm, f)
                carried = sum(pm["owner"][q] == k for q in range(max(0, i - BEFORE - 12), i + 1))
                sh = dict(f=f, team=team, idx=int(pm["roster"][f * 12 + k], 36), x=P[3 * f], y=P[3 * f + 1],
                          speed=round(math.hypot(la[0], la[1])) if la else 12000, kind="shot" if carried >= 3 else "one-timer",
                          result="save", human=bool(pm["ctrl"][f] >> k & 1))
                gk = next((q for q in range((1 - team) * 6, (1 - team) * 6 + 6) if pm["role"][f * 12 + q] == "0"), None)
                w2 = [r for r in work if r[1] != gk]
                if gk is not None and grow.get(1 - team):
                    w2.append([0, gk, *grow[1 - team]])
                side = 0
                gl = 264 if XG.attacks_top(pm, f, team) else -264
                if la and la[1] and (gl - P[3 * f + 1]) / la[1] > 0:
                    cx = P[3 * f] + la[0] * (gl - P[3 * f + 1]) / la[1]
                    side = 1 if cx > 8 else -1 if cx < -8 else 0
                v = 0.0
                for d, wgt in HEIGHTS[side]:
                    one = dict(sh, aim={"d": d})
                    XG._CACHE.clear()
                    XG.add_expected_goals(dict(pm, work=sorted(w2), shotList=[one]), stick_rom=rom_bytes, lock=True)
                    v += wgt * (one.get("xg") or 0.0)
                tot[team] += v
                per.append(dict(video=round(v, 3), rec=(pair[jf].get("xg") if jf in pair else None), matched=jf in pair,
                                kind=sh["kind"], rec_kind=pair[jf]["kind"] if jf in pair else None))
            rec = [sum(s.get("xg") or 0 for s in T if s["team"] == t and s["result"] != "blocked") for t in (0, 1)]
            print(f"{name} xG by team: recorded {rec[0]:.2f} / {rec[1]:.2f}, from video {tot[0]:.2f} / {tot[1]:.2f}")
            res.update(xg_rec=rec, xg_video=tot, per=per,
                       missed_xg=round(sum((s.get("xg") or 0) for s in T if not any(v is s for v in pair.values()) and s["result"] != "blocked"), 2))
            Path(read_path.replace(".json", "_swingshots.json")).write_text(json.dumps(res))


def cv(data_npz, out_prefix, reads, weight=3.0):
    """A model for each read, from the recordings' swings and the other reads' (weighted): READ_swingdata.npz files."""
    base = np.load(data_npz)
    D = {r: np.load(r.replace(".json", "_swingdata.npz")) for r in reads}
    for held in reads:
        X = np.concatenate([base["X"]] + [D[r]["X"] for r in reads if r != held])
        y = np.concatenate([base["y"] > 0] + [D[r]["y"] > 0 for r in reads if r != held])
        w = np.concatenate([np.ones(len(base["y"]))] + [np.full(len(D[r]["y"]), weight) for r in reads if r != held])
        model = fit(X, y, w=w)
        out = f"{out_prefix}_{Path(held).stem}.json"
        Path(out).write_text(json.dumps(model))
        print("model for", Path(held).stem, "from", len(y), "swings", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "cv":
        cv(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif sys.argv[1] == "train":
        skip = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--skip"]
        train(sys.argv[2], skip)
    else:
        test(sys.argv[2], sys.argv[3])
