"""Passing out of a check on the SNES: do the ratings change it? (2026-11-07, the user approved; the Genesis test is
check_pass_ratings.py.) The moments of snes_check_pass_timing.py, played again with one rating changed at a time.

Working ratings (word arrays, ram94s.asm; 0-15, weight the rating x 8), written after the placement, before the scout
(so the burst the scout finds is the one with that rating):

  base             nothing changed
  pas lo / pas hi  the carrier's Pass Accuracy ($13A3: on the SNES it only steadies the pass's speed) 4 / 15
  stk lo / stk hi  the receiver's Stick Handling ($1403) 4 / 15
  spd lo / spd hi  the defenders' Speed ($1303), every opposing skater (the checker is the computer's, found by the
                   scout) 8 / 15
  wt lo / wt hi    the defenders' Weight ($12C3) 32 / 112
  chk lo / chk hi  the defenders' Checking ($1483) 4 / 15

B at -6, +3, +12 and +24 frames from the burst; one seed. Gentle mode, resumable.

python snes_check_pass_ratings.py RUN [N situations] [minutes]   -> paths.RUNS / RUN / trials.jsonl
python snes_check_pass_ratings.py RUN report"""
import json
import random
import sys
import time
from collections import Counter, defaultdict

import snes_check_pass_timing as T
import snes_harness as H
from lowload import breathe, gentle
from paths import RUNS, SNES_STATE_TOP

FIELDS = dict(pas=(0x13A3, "carrier", (4, 15)), stk=(0x1403, "mate", (4, 15)), spd=(0x1303, "them", (8, 15)),
              wt=(0x12C3, "them", (32, 112)), chk=(0x1483, "them", (4, 15)))
VARIANTS = ["base"] + [f"{f} {lv}" for f in FIELDS for lv in ("lo", "hi")]
OFFSETS = [-6, 3, 12, 24]
_cur = {"v": "base"}


class RatedRig(T.Rig):
    def place(self, s, seed):
        r = super().place(s, seed)
        if r is None or _cur["v"] == "base":
            return r
        c, mate, obj = r
        field, lv = _cur["v"].split()
        addr, who, levels = FIELDS[field]
        val = levels[lv == "hi"]
        ks = [c] if who == "carrier" else [mate] if who == "mate" else \
            [k for k in range(6, 12) if self.e.w(T.POSITION + H.o(k)) != 0]
        for k in ks:
            self.e.setw(addr + H.o(k), val)
        _cur["set"] = (addr, ks, val)
        return r


def main():
    run = sys.argv[1]
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    path = out / "trials.jsonl"
    if len(sys.argv) > 2 and sys.argv[2] == "report":
        return report(path)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    gentle()
    sits = T.situations()
    random.Random(7).shuffle(sits)
    sits = sits[:n]
    done = {(r["i"], r["v"], r["offset"]) for r in map(json.loads, open(path))} if path.exists() else set()
    h = RatedRig(state=SNES_STATE_TOP, top=True)
    t0 = time.time()
    with open(path, "a") as fh:
        for i, s in enumerate(sits):
            seed = random.Random(i * 10).getrandbits(32)
            for v in VARIANTS:
                if (i, v, "none") in done or all((i, v, o) in done for o in OFFSETS):
                    continue
                if time.time() - t0 > minutes * 60:
                    print("time up", flush=True)
                    return
                _cur["v"], _cur["set"] = v, None
                sc = T.scout(h, s, seed)
                breathe()
                if sc is None:
                    fh.write(json.dumps(dict(i=i, v=v, offset="none", res="no burst at him")) + "\n")
                    fh.flush()
                    continue
                for off in OFFSETS:
                    if (i, v, off) in done:
                        continue
                    r = T.trial(h, sc, off)
                    breathe()
                    st = _cur.get("set")
                    if st:
                        r["held"] = all(h.e.w(st[0] + H.o(k)) == st[2] for k in st[1])
                    r.update(i=i, v=v, offset=off)
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
            if i % 20 == 19:
                print(f"situation {i + 1} of {len(sits)}", flush=True)
    print("done", flush=True)


def report(path):
    allrows = [json.loads(l) for l in open(path)]
    rows = [r for r in allrows if r["offset"] != "none"]
    print(len(rows), "trials,", len({r["i"] for r in rows}), "situations;",
          sum(r.get("held") is False for r in rows), "with the rating changed during the trial")
    full = defaultdict(dict)
    for r in rows:
        full[r["i"]][(r["v"], r["offset"])] = r
    full = {i: d for i, d in full.items() if len(d) == len(VARIANTS) * len(OFFSETS)}
    print(len(full), "situations with a burst in every variant; reached a teammate / picked off by the checker / caught:")
    print(f"  {'':8}" + "".join(f"{'B ' + format(o, '+d'):>12}" for o in OFFSETS) + f"{'all':>12}{'checker':>9}{'caught':>8}")
    for v in VARIANTS:
        cells = []
        for offs in [[o] for o in OFFSETS] + [OFFSETS]:
            sel = [full[i][(v, o)] for i in full for o in offs]
            cells.append(f"{100 * sum(r['res'].endswith('teammate') for r in sel) / max(1, len(sel)):11.0f}%")
        sel = [full[i][(v, o)] for i in full for o in OFFSETS]
        ck = 100 * sum(r["res"].endswith("checker") for r in sel) / max(1, len(sel))
        ca = 100 * sum(r["res"] == "caught" for r in sel) / max(1, len(sel))
        print(f"  {v:8}" + "".join(cells) + f"{ck:8.0f}%{ca:7.0f}%")
    print("Each variant against base, over the situations with a burst in both (all offsets): teammate, checker, caught;"
          " better / worse for a teammate, same situation and offset")
    by = defaultdict(dict)
    for r in rows:
        by[r["i"]][(r["v"], r["offset"])] = r
    for v in VARIANTS[1:]:
        both = [i for i, d in by.items() if all((v, o) in d and ("base", o) in d for o in OFFSETS)]
        pr = lambda w: [by[i][(w, o)] for i in both for o in OFFSETS]
        line = []
        for w in ("base", v):
            sel = pr(w)
            n = max(1, len(sel))
            line.append(f"{100 * sum(r['res'].endswith('teammate') for r in sel) / n:3.0f}% {100 * sum(r['res'].endswith('checker') for r in sel) / n:3.0f}% {100 * sum(r['res'] == 'caught' for r in sel) / n:3.0f}%")
        b = sum(by[i][(v, o)]["res"].endswith("teammate") and not by[i][("base", o)]["res"].endswith("teammate") for i in both for o in OFFSETS)
        w_ = sum(by[i][("base", o)]["res"].endswith("teammate") and not by[i][(v, o)]["res"].endswith("teammate") for i in both for o in OFFSETS)
        print(f"  {v:8} {len(both):4} situations: base {line[0]} | variant {line[1]} | {b} / {w_}")
    print("Bursts found, by variant (of the situations tried):",
          {v: sum(1 for r in allrows if r["v"] == v and r["offset"] != "none") // len(OFFSETS) for v in VARIANTS})


if __name__ == "__main__":
    main()
