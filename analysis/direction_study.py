"""Up / down the screen and home / away beyond the shots themselves (docs/SHOOTING_STUDY.md, second part): passing,
turnovers, zone entries, checks, faceoffs, the home record and the working-rating bonus, and the measurable pieces of
the up / down mechanics (shot scatter, the goalie's stick saves). Run from the project folder after
analysis/shot_table.py: python analysis/direction_study.py"""
import glob
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
from export_match import own_end  # noqa: E402

K = 12
files = {}
for p in glob.glob("matches/*.js") + glob.glob(r"C:/Users/USER/Documents/NHL94 Viewer/matches/*.js"):
    if not p.endswith(".summary.json") and Path(p).name not in ("season.js", "shot_study.json"):
        files.setdefault(Path(p).name, p)

tally = defaultdict(Counter)   # (system, measure) -> counter
records = defaultdict(list)


def direction(m, f, team):
    e = own_end(m, f, team)
    return None if e is None else ("up" if e < 0 else "down")


for name, p in sorted(files.items()):
    try:
        m = json.loads(load_js_object(Path(p)))
    except Exception:
        continue
    if "shotList" not in m or not m.get("t") or m["t"][-1] - m["t"][0] < 120000:
        continue
    sy = m.get("system", "genesis")
    whole = m["period"][-1] >= 3
    # the result, for the home record (whole games only)
    if whole:
        h, a = m["score"][-2], m["score"][-1]
        tally[(sy, "home record")]["home win" if h > a else "away win" if a > h else "tie"] += 1
    # passes
    for e in m.get("passes", []):
        d = direction(m, e["f"], e["team"])
        if d is None:
            continue
        for key in (d, "home" if e["team"] == 0 else "away"):
            c = tally[(sy, "passes " + key)]
            c["passes"] += 1
            c[e.get("result")] += 1
    for e in m.get("bobbles", []):
        d = direction(m, e["f"], e["team"])
        if d:
            tally[(sy, "passes " + d)]["bobbled"] += 1
            tally[(sy, "passes " + ("home" if e["team"] == 0 else "away"))]["bobbled"] += 1
    # turnovers: who lost it, which way they were going
    for e in m.get("turnovers", []):
        if e.get("kind") not in ("giveaway", "takeaway"):
            continue
        d = direction(m, e["f"], e["from"])
        if d:
            tally[(sy, "turnovers lost going " + d)][e["kind"]] += 1
            tally[(sy, "turnovers lost by " + ("home" if e["from"] == 0 else "away"))][e["kind"]] += 1
    # zone entries
    for e in m.get("zoneEntries", []):
        d = direction(m, e["f"], e["team"])
        if d:
            for key in (d, "home" if e["team"] == 0 else "away"):
                tally[(sy, "entries " + key)][e["kind"]] += 1
                tally[(sy, "entries " + key)]["all"] += 1
    # checks landed
    for e in m.get("hits", []):
        d = direction(m, e["f"], e["team"])
        if d:
            tally[(sy, "checks")]["by a team going " + d] += 1
            tally[(sy, "checks")]["by " + ("home" if e["team"] == 0 else "away")] += 1
    # faceoffs: who won the draw (the game's faceoff count rising), and where
    for e in m.get("faceoffs", []):
        if e.get("won") in (0, 1):
            tally[(sy, "faceoffs")]["home won" if e["won"] == 0 else "away won"] += 1
    # the working-rating bonus at home and away (Genesis: work rows [frame, record, wgt, agl, spd, aidef, shp, sha])
    if sy == "genesis" and m.get("work"):
        for w in m["work"]:
            k = w[1]
            team = 0 if k < 6 else 1
            idx_c = m["roster"][w[0] * K + k]
            if idx_c == "x" or int(idx_c, 36) >= len(m["rosters"][team]):
                continue
            p_ = m["rosters"][team][int(idx_c, 36)]
            if p_.get("g"):
                continue
            nib = p_["a"][9]  # Shot Accuracy rating (0-6 on the screen)
            records[(sy, "home" if team == 0 else "away")].append(w[7] - 5 * nib)

rows = json.load(open(Path("matches") / "shot_study.json"))
for sy in ("genesis", "snes"):
    print(f"\n==================== {sy.upper()}")
    for k, c in sorted(tally.items()):
        if k[0] != sy:
            continue
        print(f"{k[1]:32}: " + ", ".join(f"{a} {b}" for a, b in c.most_common()))
    for side in ("home", "away"):
        v = records.get((sy, side))
        if v:
            print(f"working Shot Accuracy minus 5 x rating, {side}: mean {sum(v) / len(v):+.2f} over {len(v)} rating loads")
    # Scatter: a person's scattered shots, how far from the aim point they crossed (only shots with a known crossing)
    S = [r for r in rows if r["system"] == sy and r["human"] and r["kind"] == "shot" and r["perfect"] is False]
    for d in ("up", "down"):
        sel = [r for r in S if r["up"] == (d == "up")]
        wide = sum(r["result"] == "wide" for r in sel)
        print(f"scattered person shots going {d:4}: {len(sel)}, wide {wide} ({100 * wide / max(1, len(sel)):.0f}%), on goal {sum(1 for r in sel if r['counted'])}")
    # The goalie's stick saves by end (the end the shooting team attacked: up = the top net)
    for d in ("up", "down"):
        sel = [r for r in rows if r["system"] == sy and r["up"] == (d == "up") and r["result"] in ("save", "goal", "post") and r["save"]]
        st = [r for r in sel if r["save"] in ("stick",)]
        print(f"shots at the {'top' if d == 'up' else 'bottom'} net reaching the goalie: {len(sel)}, stick saves {len(st)} "
              f"({100 * len(st) / max(1, len(sel)):.0f}%), goals on them {sum(r['result'] == 'goal' for r in st)}, not counted {sum(1 for r in st if not r['counted'] and r['result'] != 'goal')}")
