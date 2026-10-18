"""After a turnover, how long the computer skaters of the team that lost the puck, who were skating up the ice, take to
turn back toward their own end, by position, both systems (SNES_MECHANICS 12.1). python analysis/turnover_reaction.py"""
import sys
from goalie_study import games, role, pos  # noqa: E402
import statistics as st; sys.path.insert(0, "tools")
from export_match import own_end
from collections import defaultdict
def vy(m, f, k, back=6):
    t = m["t"]; j = max(0, f - back)
    dt = (t[f] - t[j]) / 1000
    return (pos(m, f, k)[1] - pos(m, j, k)[1]) / dt if dt > 0 else 0
for sysname in ("genesis", "snes"):
    D = defaultdict(list)
    for n, m in games(sysname):
        t = m["t"]; T = len(t)
        for tv in m.get("turnovers", []):
            f = tv["f"]; lost = tv["from"]
            if f + 120 >= T or f < 10: continue
            e = own_end(m, f, lost)
            if e is None: continue
            for k in range(lost * 6, lost * 6 + 6):
                r = role(m, f, k)
                if r in "0x" or (m["ctrl"][f] >> k) & 1: continue
                v0 = vy(m, f, k) * -e    # + = skating toward the attacked end
                if v0 < 60: continue
                q = next((q for q in range(f, min(T, f + 150)) if vy(m, q, k, 3) * -e < 0 and t[q] - t[f] < 3000), None)
                if q is None: continue
                pos_name = {"1": "D", "2": "D", "3": "W", "5": "W", "4": "C"}[r]
                D[pos_name].append(t[q] - t[f])
    print(sysname, {k: (len(v), st.median(v)) for k, v in D.items()})
