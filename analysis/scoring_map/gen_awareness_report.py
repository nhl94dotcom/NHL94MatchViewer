"""Summary of gen_awareness_cvc.py's games (RATING_VALUES chunk C): per rating tested, the HIGH team's goals and shots
minus the LOW team's a game (regulation only: a game tied after three periods stops there), with standard errors, the
same per rating step (the levels' frames converted by GENESIS_MECHANICS 12.1: rating 6 about 8 frames, rating 1 about 14,
so 5 steps by default), and the wins.

python gen_awareness_report.py OUT.jsonl [STEPS]"""
import json
import statistics as st
import sys
from pathlib import Path


def main():
    rows = [json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines() if x.strip()]
    rows = [r for r in rows if "error" not in r and r["periods"] >= 3]
    steps = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    for rating in ("OfA", "DfA"):
        rs = [r for r in rows if r["rating"] == rating]
        if len(rs) < 2:
            continue
        print(f"{rating}: {len(rs)} games, levels {rs[0]['levels']} (high, low, the other rating)")
        for what in ("goals", "shots"):
            d = [r[f"{what}_high"] - r[f"{what}_low"] for r in rs]
            m, se = st.mean(d), st.stdev(d) / len(d) ** 0.5
            hi = st.mean(r[f"{what}_high"] for r in rs)
            lo = st.mean(r[f"{what}_low"] for r in rs)
            print(f"  {what}: high {hi:.2f}, low {lo:.2f} a game; difference {m:+.2f} +- {se:.2f};"
                  f" a step {m / steps:+.3f} +- {se / steps:.3f}")
        w = sum(r["goals_high"] > r["goals_low"] for r in rs)
        l = sum(r["goals_high"] < r["goals_low"] for r in rs)
        print(f"  high team won {w}, lost {l}, tied {len(rs) - w - l} after regulation")


if __name__ == "__main__":
    main()
