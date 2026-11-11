"""Defencemen's weight bands (2026-11-11, the user: on the Genesis middleweight defencemen are poorer, suited neither
to C checks nor to CB checks; on the SNES heavier checks better). defence_value.py's fit (each Classic team-game's goals
from both lineups and both coaches), with the defencemen's Weight as bands instead of a straight line: per team-game,
how many of its two top defencemen are middleweights (stored Weight 7-9) and how many heavy (10+), light (6 and under)
the baseline; the defencemen's other ratings averaged, the forwards' ten as before. Names nobody.

python analysis/defence_weight_bands.py genesis|snes"""
import ast
import csv
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
import numpy as np
import defence_value as DV
from collections import Counter
system = sys.argv[1] if len(sys.argv) > 1 else "genesis"
ros = DV.rosters(system)
USED = {}
def lineup(players, keepers, team):
    F, D = [], []
    order = (lambda p: -p[9]) if players and len(players[0]) >= 10 else (lambda p: -USED.get((team, str(p[1]).lower()), 0))
    for p in sorted(players, key=order):
        r = ros.get((team, str(p[1]).lower()))
        if not r or r["g"]: continue
        if p[2] == "D" and len(D) < 2: D.append(r["a"])
        elif p[2] != "D" and len(F) < 3: F.append(r["a"])
    g = next((ros[(team, str(k[1]).lower())]["a"][1] for k in sorted(keepers, key=lambda k: -(k[-1] if len(k) >= 9 else USED.get((team, str(k[1]).lower()), 0))) if ros.get((team, str(k[1]).lower()), {}).get("g")), None)
    if len(F) < 3 or len(D) < 2 or g is None: return None
    f = list(np.mean([[a[i] for i in DV.IDX] for a in F], 0))
    other = [i for i in DV.IDX if i != 0]
    d = list(np.mean([[a[i] for i in other] for a in D], 0))
    mid = sum(7 <= a[0] <= 9 for a in D); heavy = sum(a[0] >= 10 for a in D)
    return f + d + [mid, heavy], g
csv.field_size_limit(10**9)
from collections import defaultdict
used = defaultdict(Counter)
FN = DV.DATA / ("All_Games_GENS.csv" if system == "genesis" else "All_Games_SNES.csv")
for r in csv.DictReader(open(FN, encoding="utf-8", errors="replace", newline="")):
    if r["League"].lower().startswith("classic"):
        for s_ in ("Home", "Away"):
            try:
                for p in ast.literal_eval(r[s_+"Players"] or "[]") + ast.literal_eval(r[s_+"Goalies"] or "[]"):
                    used[r["League"]][(r[s_+"TeamAbbrev"].strip(), str(p[1]).lower())] += 1
            except (ValueError, SyntaxError): pass
rows = []
for r in csv.DictReader(open(DV.DATA / ("All_Games_GENS.csv" if system == "genesis" else "All_Games_SNES.csv"), encoding="utf-8", errors="replace", newline="")):
    if r.get("sim") == "1" or r["RegOrPlay"] != "R" or not r["League"].lower().startswith("classic"): continue
    USED.clear(); USED.update(used[r["League"]])
    try:
        side = {s: lineup(ast.literal_eval(r[s+"Players"] or "[]"), ast.literal_eval(r[s+"Goalies"] or "[]"), r[s+"TeamAbbrev"].strip()) for s in ("Home","Away")}
    except (ValueError, SyntaxError): continue
    if None in side.values(): continue
    for s, o in (("Home","Away"),("Away","Home")):
        rows.append((float(r[s+"Score"]), side[s], side[o], s=="Home", r[s+"Player"].strip().lower(), r[o+"Player"].strip().lower()))
n = Counter(x[4] for x in rows); coaches = sorted(c for c,k in n.items() if k >= 40); ci = {c:i for i,c in enumerate(coaches)}; K = len(coaches)
nf = len(rows[0][1][0])
X = np.zeros((len(rows), 2*nf + 2 + 2*(K+1) + 1), np.float32)
for j, (gf, own, opp, home, c, oc) in enumerate(rows):
    X[j,:nf] = own[0]; X[j,nf] = own[1]; X[j,nf+1:2*nf+1] = opp[0]; X[j,2*nf+1] = opp[1]
    X[j,2*nf+2+ci.get(c,K)] = 1; X[j,2*nf+2+K+1+ci.get(oc,K)] = 1; X[j,-1] = home
y = np.array([x[0] for x in rows])
b, *_ = np.linalg.lstsq(X, y, rcond=None)
rng = np.random.default_rng(3); ng = len(rows)//2; bs = []
for _ in range(40):
    p = rng.integers(0, ng, ng); ix = np.concatenate([2*p, 2*p+1]); bb, *_ = np.linalg.lstsq(X[ix], y[ix], rcond=None); bs.append(bb[:2*nf+2])
se = np.std(bs, 0)
mids = Counter(x[1][0][-2] for x in rows); hv = Counter(x[1][0][-1] for x in rows)
print(f"{system}: {ng} games; team-games with 0/1/2 middleweight D: {[mids[k] for k in (0,1,2)]}, heavy: {[hv[k] for k in (0,1,2)]}")
for k, label in ((nf-2, "one middleweight D (7-9) instead of a light one"), (nf-1, "one heavy D (10+) instead of a light one")):
    f, a = b[k], -b[nf+1+k]
    print(f"  {label}: for {f:+.3f} +- {se[k]:.3f}, against (cut) {a:+.3f} +- {se[nf+1+k]:.3f}, total {f+a:+.3f} +- {np.hypot(se[k], se[nf+1+k]):.3f} goals a game")
names = [n for n in DV.NAMES if n != "Weight"]
for i, nm in enumerate(names):
    k = 10 + i
    f, a = b[k]/2, -b[nf+1+k]/2
    print(f"  D {nm}: for {f:+.3f}, against (cut) {a:+.3f} +- {se[nf+1+k]/2:.3f}, total {f+a:+.3f}")
