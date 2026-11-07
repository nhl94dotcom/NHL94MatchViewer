"""Passing out of a check: do the ratings change it? (2026-11-07, the user approved.) check_pass_timing.py found that
the moment B is pressed against the checker's burst decides much of whether the pass gets through. Here the same
recorded check moments are played again with one rating changed at a time, to see whether a good passer can wait
longer, or a fast or heavy checker picks off more.

The ratings are the working values (0-30) in the skater's record (ram94.asm: weight $67, legspd $69, passacc $6E,
stickhand $71; weight is the rating x 8, 32-112 in the rosters), written after the situation is placed and checked
again at the end of the trial (low / high: Passing and Stickhandling 8 / 28, Speed 12 / 24, Weight 32 / 112):

  base             nothing changed (the base state's players)
  pas lo / pas hi  the carrier's Passing (pass speed only: 160 + 2 x Passing)
  stk lo / stk hi  the receiver's Stickhandling (catching hard passes)
  spd lo / spd hi  the checker's Speed
  wt lo / wt hi    the checker's Weight (acceleration; the checker is on pad 2, a person, so the weight bug applies)

The low and high values are near the ends of those seen in the rosters. Offsets: B a little before the burst, just
after it, and late (frames after the burst; check_pass_timing's best was 0 to +3). One seed per situation and variant.
Gentle mode, resumable.

python check_pass_ratings.py RUN [N situations] [minutes]   -> paths.RUNS / RUN / trials.jsonl
python check_pass_ratings.py RUN report"""
import json
import random
import sys
import time
from collections import Counter, defaultdict

import check_pass_timing as T
from bot import rec
from bot_scenario import live_state, LIVE_STATES, RETAIL
from emu import Emu
from lowload import breathe, gentle
from paths import RUNS

LEVELS = dict(pas=(8, 28), stk=(8, 28), spd=(12, 24), wt=(32, 112))   # weight is stored x 8 (setplayer)
FIELDS = dict(pas=0x6E, stk=0x71, spd=0x69, wt=0x67)
WHO = dict(pas="carrier", stk="mate", spd="checker", wt="checker")
VARIANTS = ["base"] + [f"{f} {lv}" for f in FIELDS for lv in ("lo", "hi")]
OFFSETS = [-6, 3, 12, 18]

_place = T.place
_current = {}


def place_with_rating(e, base, s, seed):
    """T.place, then the variant's rating written on the right skater."""
    carrier = _place(e, base, s, seed)
    v = _current.get("v", "base")
    _current["slots"] = None
    if carrier is None or v == "base":
        return carrier
    field, lv = v.split()
    who = {"carrier": carrier, "checker": T.slot_of(e, "them", s["checker"]), "mate": T.slot_of(e, "us", s["receiver"])}
    k = who[WHO[field]]
    if k is None:
        return carrier
    _current["was"] = e.b(rec(k) + FIELDS[field])
    val = LEVELS[field][lv == "hi"]
    e.setb(rec(k) + FIELDS[field], val)
    _current["slots"] = (k, FIELDS[field], val)
    return carrier


T.place = place_with_rating


def main():
    run = sys.argv[1]
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    path = out / "trials.jsonl"
    if len(sys.argv) > 2 and sys.argv[2] == "report":
        return report(path)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    gentle()
    sits = T.situations()
    random.Random(7).shuffle(sits)
    sits = sits[:n]
    done = {(r["i"], r["v"], r["offset"]) for r in map(json.loads, open(path))} if path.exists() else set()
    e = Emu(RETAIL)
    bases = [live_state(e, j) for j in range(LIVE_STATES)]
    t0 = time.time()
    with open(path, "a") as fh:
        for i, s in enumerate(sits):
            seed = random.Random(i * 10).getrandbits(32)
            for v in VARIANTS:
                for off in OFFSETS:
                    if (i, v, off) in done:
                        continue
                    if time.time() - t0 > minutes * 60:
                        print("time up", flush=True)
                        return
                    _current["v"] = v
                    r = T.trial(e, bases[i % LIVE_STATES], s, seed, off)
                    breathe()
                    if r is None:
                        continue
                    sl = _current.get("slots")
                    if sl:
                        r["held"] = e.b(rec(sl[0]) + sl[1]) == sl[2]     # the rating still set at the end
                    r.update(i=i, v=v, offset=off, real=s.get("real"))
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
            print(f"situation {i + 1} of {len(sits)}", flush=True)
    print("done", flush=True)


def report(path):
    rows = [json.loads(l) for l in open(path)]
    rows = [r for r in rows if r["res"] not in ("lost before the burst", "stoppage")]
    print(len(rows), "trials,", len({r["i"] for r in rows}), "situations;",
          sum(1 for r in rows if r.get("held") is False), "with the rating changed during the trial")
    # paired: situations where every variant and offset was played
    full = defaultdict(dict)
    for r in rows:
        full[r["i"]][(r["v"], r["offset"])] = r
    full = {i: d for i, d in full.items() if len(d) == len(VARIANTS) * len(OFFSETS)}
    print(len(full), "situations with every variant and offset played; reached a teammate / picked off by the checker:")
    print(f"  {'':10}" + "".join(f"{'B ' + format(o, '+d') + ' fr':>16}" for o in OFFSETS) + f"{'all':>16}")
    for v in VARIANTS:
        cells = []
        for offs in [[o] for o in OFFSETS] + [OFFSETS]:
            sel = [full[i][(v, o)] for i in full for o in offs]
            n = len(sel) or 1
            ok = sum(r["res"].endswith("teammate") for r in sel)
            ck = sum(r["res"].endswith("checker") for r in sel)
            cells.append(f"{100 * ok / n:5.0f}% / {100 * ck / n:3.0f}%")
        print(f"  {v:10}" + "".join(f"{c:>16}" for c in cells))
    print("Outcomes by variant (all offsets):")
    for v in VARIANTS:
        c = Counter(r["res"] for r in rows if r["v"] == v)
        n = sum(c.values()) or 1
        print(f"  {v:8} {n:5}: " + ", ".join(f"{k} {100 * x / n:.0f}%" for k, x in c.most_common(6)))
    print("Paired differences against base (reached a teammate, same situation and offset): better / worse / same")
    for v in VARIANTS[1:]:
        b = w = s = 0
        for i in full:
            for o in OFFSETS:
                x, y = full[i][(v, o)]["res"].endswith("teammate"), full[i][("base", o)]["res"].endswith("teammate")
                b += x and not y
                w += y and not x
                s += x == y
        print(f"  {v:8} {b:4} / {w:4} / {s:4}")


if __name__ == "__main__":
    main()
