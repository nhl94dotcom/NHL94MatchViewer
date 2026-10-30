"""Who takes the penalties, by working Aggression (2026-10-30). For every penalty in the recorded games (both systems,
both game folders, each game once): the fouling player's working Aggression at the moment it was called (SNES
`aggress` $1443, a word per object, 0-15; Genesis record +$73, 0-15 after the wrap, GENESIS_MECHANICS 8.2), read from
the recording itself, and whether a person controlled him. Set beside it, the share of skater time at each value (every
sample, skaters on the ice, goalies left out), so "most penalties were by maxed players" can be weighed against how
many skaters are maxed anyway. Also each penalty's code (the rule-table number) and the SNES person / computer split.
python analysis/penalty_aggression.py   -> prints the tables"""
import bisect
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
from export_match import Capture  # noqa: E402
from share_game import load_js_object  # noqa: E402

DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
SNES_AGR, SNES_POS = 0x1443, 0x0F43
GEN_REC, GEN_AGR, GEN_POS = 0xB04A, 0x73, 0x35
HOMES = (Path("."), Path.home() / "Documents" / "NHL94 Viewer")


def games():
    seen = set()
    for home in HOMES:
        for mf in sorted((home / "matches").glob("*.js")):
            if mf.name.startswith("season") or mf.name.endswith(".summary.js") or mf.name in ("games.js",) or mf.stem in seen:
                continue
            cap = home / "captures" / mf.stem
            if (cap / "capture.json").exists():
                seen.add(mf.stem)
                yield mf, cap


def agr(cap, i, k, system):
    if system == "snes":
        return cap.word(i, SNES_AGR + 2 * k) & 0xFF
    return cap.byte(i, GEN_REC + 0x80 * k + GEN_AGR)


def main():
    pens = {"snes": [], "genesis": []}
    exposure = {s: Counter() for s in pens}
    for mf, folder in games():
        m = json.loads(load_js_object(mf))
        system = m.get("system", "genesis")
        try:
            cap = Capture(folder)
        except Exception as e:  # noqa: BLE001
            print("skip", folder.name, e)
            continue
        ms = [cap.ms(i) for i in range(cap.count)]
        K, t = 12, m["t"]
        for f in range(0, len(t), 30):                     # skater time: every 30th sample (half a second)
            i = bisect.bisect_left(ms, t[f])
            if i >= cap.count:
                break
            for k in range(K):
                r = m["role"][f * K + k]
                if r in ("x", "0"):
                    continue
                exposure[system][(agr(cap, i, k, system), bool(m["ctrl"][f] >> k & 1))] += 1
        for p in m.get("penalties", []):
            f = p.get("called", p["f"])
            k = next((k for k in range(p["team"] * 6, p["team"] * 6 + 6)
                      if m["role"][f * K + k] != "x" and DIGITS.index(m["roster"][f * K + k]) == p["idx"]), None)
            if k is None:
                continue
            i = min(cap.count - 1, bisect.bisect_left(ms, t[f]))
            pens[system].append((agr(cap, i, k, system), bool(p.get("human")), p["code"], mf.stem))
    for system, rows in pens.items():
        ex = exposure[system]
        tot = sum(ex.values()) or 1
        print(f"\n{system.upper()}: {len(rows)} penalties in {len({r[3] for r in rows})} games "
              f"(by a person {sum(r[1] for r in rows)}, the computer {sum(not r[1] for r in rows)})")
        print("  working Aggression: penalties (person / computer) | share of skater time (person / computer)")
        for a in range(16):
            n = [r for r in rows if r[0] == a]
            e_p, e_c = ex[(a, True)], ex[(a, False)]
            if n or e_p or e_c:
                print(f"  {a:2}: {len(n):3} ({sum(r[1] for r in n)} / {sum(not r[1] for r in n)})"
                      f" | {100 * (e_p + e_c) / tot:5.1f}% ({100 * e_p / tot:4.1f} / {100 * e_c / tot:4.1f})")
        mx = 15
        p_mx = sum(r[0] == mx for r in rows)
        e_mx = sum(v for (a, _), v in ex.items() if a == mx) / tot
        print(f"  at {mx}: {p_mx} of {len(rows)} penalties ({100 * p_mx / max(1, len(rows)):.0f}%), against "
              f"{100 * e_mx:.0f}% of skater time")
        print("  codes:", dict(Counter(r[2] for r in rows)))


if __name__ == "__main__":
    main()
