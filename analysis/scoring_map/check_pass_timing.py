"""Passing out of a check, timed in the real game (2026-11-07, the user approved: does the moment you press B against a
burst decide whether the pass gets through, as the recordings suggest?). analysis/check_pass.py found in the recorded
Genesis games that a pass released under 0.10 s (real) before contact reached a teammate 60% of the time and the
checker picked off 11%, against about 80% and 4% for 0.10-0.50 s. Recorded games can't separate the timing from the
situation (who presses B late may be in worse trouble), so here the same situations are played with only the timing
changed.

Situations: moments from the recorded games (check_pass.measure's events: an opponent bursting at a person's
carrier), placed in the retail ROM's live play as bot_scenario.py places them (all 12 records and the puck, the attack
turned up the ice, the computer's state reset), LEAD frames before the recorded burst. The receiver is the teammate the
person passed to then, or else the most open skater teammate within 250 units. The checker is given pad 2: he steers
at the carrier (aiming a little ahead of him) and presses C at frame LEAD, as in the recording. The carrier on pad 1
keeps skating the way he was going and presses B toward the receiver at LEAD + offset, for each offset in OFFSETS
(frames; None: no pass). Each trial notes the frame of contact (the two under CONTACT apart, or the game counting a
check by the away team), of the pass leaving his stick, and who had the puck next: a teammate, the checker, another
opponent (skater or goalie), or nobody within 3 s (180 frames). Caught: he lost the puck before any pass left.
Gentle mode, one process (another long run may be going); resumable.

python check_pass_timing.py RUN [N situations] [minutes]   -> paths.RUNS / RUN / trials.jsonl
python check_pass_timing.py RUN report"""
import json
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from bot import rec, PUCKC, pad, dir_to
from bot_scenario import place, live_state, LIVE_STATES, CONT_TEAMS, C2PLAYER, RETAIL
from emu import Emu
from lowload import breathe, gentle
from paths import RUNS, WORK

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from bot_situations import situation  # noqa: E402

K, CONTACT, LEAD, AFTER = 12, 18, 15, 180
OFFSETS = [-6, 0, 3, 6, 9, 12, 15, 18, 24, None]
SEEDS = 2
AWAY_CHECKS = 0xCA32 + 0x10        # the Away team's checks (team stat +$10)
HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")


def situations():
    """Check moments from every recorded Genesis game (cached in the work folder: positions only, no names)."""
    cache = WORK / "check_pass_situations.json"
    if cache.exists():
        return json.loads(cache.read_text())
    import check_pass as CP
    from share_game import load_js_object
    rows = []
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season":
            continue
        try:
            m = json.loads(load_js_object(p))
        except (ValueError, OSError):
            continue
        if m.get("system", "genesis") != "genesis" or "pos" not in m:
            continue
        t = m["t"]
        for ev in CP.measure(m):
            f, A = ev["f"], ev["team"]
            q = f
            while q > 0 and t[f] - t[q] < LEAD * 1000 / 60:
                q -= 1
            carrier = next((k for k in range(A * 6, A * 6 + 6) if int(m["roster"][q * K + k], 36) == ev["carrier"]), None)
            checker = next((k for k in range((1 - A) * 6, (1 - A) * 6 + 6) if int(m["roster"][q * K + k], 36) == ev["checker"]), None)
            if carrier is None or checker is None or m["owner"][q] != carrier:
                continue
            s = situation(m, q, A, "checkpass", p.stem, owner=carrier)
            if not s:
                continue
            s["checker"] = m["role"][q * K + checker]
            # the receiver: the teammate he passed to, else the most open skater within 250
            to = None
            if ev.get("pass") and ev["pass"].get("to", -1) >= 0:
                to = next((k for k in range(A * 6, A * 6 + 6) if int(m["roster"][q * K + k], 36) == ev["pass"]["to"]), None)
            if to is None or m["role"][q * K + to] in "0x":
                P = lambda k: m["pos"][(q * K + k) * 2:(q * K + k) * 2 + 2]
                best = None
                for k in range(A * 6, A * 6 + 6):
                    if k == carrier or m["role"][q * K + k] not in "12345":
                        continue
                    d = math.dist(P(k), P(carrier))
                    if d > 250:
                        continue
                    room = min(math.dist(P(k), P(o)) for o in range((1 - A) * 6, (1 - A) * 6 + 6) if m["role"][q * K + o] in "012345")
                    if best is None or room > best[0]:
                        best = (room, k)
                if best is None:
                    continue
                to = best[1]
            s["receiver"] = m["role"][q * K + to]
            s["real"] = ev["out"]
            rows.append(s)
    cache.write_text(json.dumps(rows))
    return rows


def slot_of(e, side, role):
    for k in (range(6) if side == "us" else range(6, 12)):
        if str(e.b(rec(k) + 0x35)) == role:
            return k
    return None


def trial(e, base, s, seed, offset):
    carrier = place(e, base, s, seed)
    if carrier is None:
        return None
    checker, mate = slot_of(e, "them", s["checker"]), slot_of(e, "us", s["receiver"])
    if checker is None or mate is None:
        return None
    e.setw(CONT_TEAMS[1], 2)                      # the checker on pad 2
    for k in range(6, 12):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setb(rec(checker) + 0x62, e.b(rec(checker) + 0x62) | 8)
    e.setw(C2PLAYER, checker)
    pos = lambda k: (e.sw(rec(k)), e.sw(rec(k) + 0x14))
    vel = lambda k: (e.sw(rec(k) + 0x28) / 4096, e.sw(rec(k) + 0x2A) / 4096)
    vx, vy = vel(carrier)
    skate = dir_to(vx, vy) if math.hypot(vx, vy) > 0.3 else e.b(rec(carrier) + 0x55) & 7
    checks0 = e.w(AWAY_CHECKS)
    contact = release = b_at = lost = hit = None
    burst = LEAD
    after = None
    for f in range(LEAD + 60 + AFTER):
        cx, cy = pos(carrier)
        kx, ky = pos(checker)
        cvx, cvy = vel(carrier)
        aim = dir_to(cx + 8 * cvx - kx, cy + 8 * cvy - ky)
        hold2 = (["C"] if burst <= f < burst + 3 else []) + pad(aim)
        own = e.w(PUCKC)
        hold = []
        if release is None and lost is None:
            mx, my = pos(mate)
            hold = pad(skate)
            if offset is not None and offset + LEAD <= f < offset + LEAD + 3 and own == carrier:
                hold = ["B"] + pad(dir_to(mx - cx, my - cy))
                if b_at is None:
                    b_at = f
        e.run(1, hold=hold, hold2=hold2)
        if e.b(0xFFF7) != 0:
            return dict(res="stoppage")
        own = e.w(PUCKC)
        if hit is None and e.w(AWAY_CHECKS) != checks0:
            hit = f
        if contact is None and f >= burst and (math.dist(pos(carrier), pos(checker)) < CONTACT or hit is not None):
            contact = f
        if release is None and lost is None and own != carrier:
            anim = e.w(rec(carrier) + 0x58)
            if b_at is not None:
                release = f
            elif f < burst:
                return dict(res="lost before the burst")      # a placement that didn't hold (not counted)
            else:
                lost = f
        if (release is not None or lost is not None) and after is None and own < 12 and own != carrier:
            after = own
            break
        if (release is not None or lost is not None) and f - (release if release is not None else lost) > AFTER:
            break
        if release is None and lost is None and offset is not None and f > offset + LEAD + 40:
            break                                 # the B press made no pass (he had lost it, or was locked)
        if offset is None and f > burst + 60 and lost is None:
            break                                 # no pass and still has it a second after the burst
        if f % 120 == 119:
            breathe()
    if release is not None:
        who = "teammate" if after is not None and after < 6 else "checker" if after == checker else \
            "other opponent" if after is not None else "nobody"
        res = "passed: " + who
        if contact is not None and contact < release:
            res = "passed after contact: " + who
    elif lost is not None:
        res = "caught" if contact is not None and contact <= lost else "lost it"
    else:
        res = "kept it"
    return dict(res=res, offset=offset, burst=burst, contact=contact, hit=hit, release=release, b=b_at, lost=lost,
                lead=(contact - release) / 60 if contact is not None and release is not None else None,
                lead_hit=(hit - release) / 60 if hit is not None and release is not None else None)


def main():
    run = sys.argv[1]
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    path = out / "trials.jsonl"
    if len(sys.argv) > 2 and sys.argv[2] == "report":
        return report(path)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    gentle()
    sits = situations()
    random.Random(7).shuffle(sits)
    sits = sits[:n]
    done = {(r["i"], r["seed"], r.get("offset", "?")) for r in map(json.loads, open(path))} if path.exists() else set()
    e = Emu(RETAIL)
    bases = [live_state(e, j) for j in range(LIVE_STATES)]
    t0 = time.time()
    with open(path, "a") as fh:
        for i, s in enumerate(sits):
            for sd in range(SEEDS):
                seed = random.Random(i * 10 + sd).getrandbits(32)
                for off in OFFSETS:
                    if (i, sd, off) in done:
                        continue
                    if time.time() - t0 > minutes * 60:
                        print("time up", flush=True)
                        return
                    r = trial(e, bases[(i + sd) % LIVE_STATES], s, seed, off)
                    breathe()
                    if r is None:
                        continue
                    r.update(i=i, seed=sd, offset=off, real=s.get("real"))
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
            print(f"situation {i + 1} of {len(sits)}", flush=True)
    print("done", flush=True)


def report(path):
    rows = [json.loads(l) for l in open(path)]
    rows = [r for r in rows if r["res"] not in ("lost before the burst", "stoppage")]
    print(len(rows), "trials,", len({r["i"] for r in rows}), "situations")
    print("By when B came (frames after the burst):")
    by = defaultdict(Counter)
    for r in rows:
        by[r.get("offset")][r["res"]] += 1
    keys = sorted({k for c in by.values() for k in c})
    for off in OFFSETS:
        c = by.get(off)
        if not c:
            continue
        n = sum(c.values())
        print(f"  {str(off):>5} ({n:4}): " + ", ".join(f"{k} {100 * c[k] / n:.0f}%" for k in keys if c[k]))
    print("Passes that left before contact, by lead (real seconds):")
    bins = [(None, "checker never got there"), ((0, 0.10), "under 0.10 s"), ((0.10, 0.25), "0.10-0.25 s"),
            ((0.25, 0.50), "0.25-0.50 s"), ((0.50, 9), "0.50 s or more")]
    for b, lab in bins:
        sel = [r for r in rows if r["res"].startswith("passed:") and
               ((r["lead"] is None) if b is None else (r["lead"] is not None and b[0] <= r["lead"] < b[1]))]
        c = Counter(r["res"][8:] for r in sel)
        n = len(sel) or 1
        print(f"  {lab:24} {len(sel):5}: " + ", ".join(f"{k} {100 * v / n:.0f}%" for k, v in c.most_common()))
    print("Passes that left before the check landed (the game counted it), by lead (real seconds):")
    for b, lab in [((0, 0.10), "under 0.10 s"), ((0.10, 0.25), "0.10-0.25 s"), ((0.25, 0.50), "0.25-0.50 s"), ((0.50, 9), "0.50 s or more")]:
        sel = [r for r in rows if r["release"] is not None and r.get("lead_hit") is not None and b[0] <= r["lead_hit"] < b[1]]
        c = Counter(r["res"].split(": ")[-1] for r in sel)
        n = len(sel) or 1
        print(f"  {lab:24} {len(sel):5}: " + ", ".join(f"{k} {100 * v / n:.0f}%" for k, v in c.most_common()))
    print("Reached a teammate, by offset, over the situations where every offset was played (same situation, same seed):")
    full = defaultdict(dict)
    for r in rows:
        full[(r["i"], r["seed"])][r["offset"]] = r
    full = {k: v for k, v in full.items() if len(v) == len(OFFSETS)}
    for off in OFFSETS:
        n = len(full)
        ok = sum(v[off]["res"].endswith("teammate") for v in full.values())
        hitme = sum(v[off].get("hit") is not None for v in full.values())
        print(f"  {str(off):>5}: {ok} of {n} ({100 * ok / max(1, n):.0f}%); the check landed in {hitme}")
    late = [r for r in rows if r["res"].startswith("passed after contact")]
    c = Counter(r["res"] for r in late)
    print("Passes released after contact:", len(late), dict(c))


if __name__ == "__main__":
    main()
