"""Penalties a game by rule in SNES computer games (snes_60fps_cvc.py's output), against the first file as the baseline
(2026-11-19, for NOSE4Web's SNES referee strictness option: checkagr's range (20 - Agr) x 16 becomes x 32 / 21 / 16 / 11
/ 7, so the checking calls should scale 50 / 76 / 100 / 145 / 229%; goalie interference's threshold 1 / 2 / 2 / 3 / 4
for the original's 2). Rule names and minutes from ROM's rule table (snes.read_rules); only calls with minutes (fights
and penalty-shot codes as listed), each call once.

python snes_ref_report.py ROM OUT.jsonl [OUT.jsonl ...]"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from systems import snes  # noqa: E402


def main():
    rules = snes.read_rules(Path(sys.argv[1]).read_bytes())
    rows = []
    for p in sys.argv[2:]:
        G = [json.loads(line) for line in Path(p).read_text().splitlines() if line.strip()]
        c = Counter(rules[code]["name"] for g in G for _, code in g["calls"] if code in rules and rules[code]["min"])
        rows.append((Path(p).stem, len(G), c, sum(sum(g["goals"]) for g in G), sum(g.get("optpen_found") == 2 for g in G)))
    base = rows[0]
    names = sorted({k for _, _, c, _, _ in rows for k in c}, key=lambda k: -base[2][k])
    print(f"{'':24s}" + "".join(f"{nm[:16]:>18s}" for nm, *_ in rows))
    print(f"{'games':24s}" + "".join(f"{n:18d}" for _, n, *_ in rows))
    for k in names + ["all"]:
        line = f"{k:24s}"
        for nm, n, c, _, _ in rows:
            v = sum(c.values()) if k == "all" else c[k]
            b = sum(base[2].values()) if k == "all" else base[2][k]
            if nm == base[0] or not b:
                line += f"  {v / n:6.2f}          "
            else:
                ratio = (v / n) / (b / base[1])
                line += f"  {v / n:6.2f} {ratio:4.0%}±{ratio * math.sqrt(1 / max(v, 1) + 1 / b):3.0%}"
        print(line)
    print(f"{'goals a game':24s}" + "".join(f"{g / n:18.2f}" for _, n, _, g, _ in rows))


if __name__ == "__main__":
    main()
