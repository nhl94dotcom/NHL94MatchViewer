"""Passing out of a check, timed in the real SNES game (2026-11-07, the user approved; the Genesis test is
check_pass_timing.py). analysis/check_pass.py found that SNES passes out of a check reach a teammate about 80% of the
time whatever the timing, the checker picking off a few more at the last moment. Here the same moments are replayed
with only the moment of B changed.

The SNES harness can't give a skater to pad 2, so the checker is the computer's own defender: each situation (a moment
from a recorded SNES game, LEAD frames before an opponent burst at a person's carrier; check_pass.measure's events) is
placed in the retail ROM's live play (snes_harness's state: home on pad 1 attacking the top net), all 12 skaters at
their recorded places, speeds and facings, turned so the carrier's team is home going up, the puck on the carrier.
A scout run with no B finds the first frame an away skater starts a burst (SPA $F342) at the carrier (within REACH and
CONE of his facing). The same placement and seed are then replayed with B (toward the receiver: the teammate he passed
to, else the most open within 250) at that frame + each offset in OFFSETS (None: no pass); the game is deterministic,
so everything before the B press repeats exactly. The carrier holds the way he was skating until then.
Each trial: the frame of contact (the two under CONTACT apart or the checker in a check animation), of a knockdown (the
carrier's fall animation), of the pass leaving, and who had the puck next (a teammate, the checker, another opponent,
nobody within 3 s). Gentle mode, one process; resumable.

python snes_check_pass_timing.py RUN [N situations] [minutes]   -> paths.RUNS / RUN / trials.jsonl
python snes_check_pass_timing.py RUN report"""
import json
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import snes_harness as H
from lowload import breathe, gentle
from paths import RUNS, WORK, SNES_STATE_TOP

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

K, CONTACT, REACH, CONE, LEAD, AFTER, SCOUT = 12, 18, 70, 35, 15, 180, 150
OFFSETS = [-12, -6, 0, 3, 6, 9, 12, 15, 18, 24, None]
SEEDS = 2
VEL = 2097                        # SNES velocity words per game unit a frame (measured: positions move every other frame)
POSITION, FACING, SPA = 0x0F43, 0x1163, 0x11A3
PFLAGS, C1PLAYER, CARRIER2 = 0x1283, 0x19EC, 0x0AE7
PLAYERPAD = 0x19d4                # playerpad (ram94s.asm), per object
PFALOCK, PF2AIP, SKATE = 0x14E3, 0x1543, 0xEA4C   # pfalock, pf2aip (animation in progress), a plain skating SPA  # pflags (bit $0008 a person's), c1playernum (the object pad 1 controls, x 2)
LUNGE, PASS, DOWN = 0xF342, (0xEC66, 0xECD8), (0xF49C, 0xF54E)
CHECKS = (0xF27A, 0xF2AC, 0xF2DE, 0xF310)
HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
DIRS = {0: ["UP"], 1: ["UP", "RIGHT"], 2: ["RIGHT"], 3: ["DOWN", "RIGHT"], 4: ["DOWN"], 5: ["DOWN", "LEFT"],
        6: ["LEFT"], 7: ["UP", "LEFT"]}


def dir_to(dx, dy):
    return round(math.degrees(math.atan2(dx, dy)) / 45) % 8


def situations():
    cache = WORK / "snes_check_pass_situations.json"
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
        if m.get("system") != "snes" or "pos" not in m:
            continue
        t, role = m["t"], m["role"]
        P = lambda q, k: (m["pos"][(q * K + k) * 2], m["pos"][(q * K + k) * 2 + 1])
        for ev in CP.measure(m):
            f, A = ev["f"], ev["team"]
            q = f
            while q > 4 and t[f] - t[q] < LEAD * 1000 / 60:
                q -= 1
            c = m["owner"][q]
            if c is None or c < 0 or c // 6 != A or int(m["roster"][q * K + c], 36) != ev["carrier"]:
                continue
            goalie = next((k for k in range(A * 6, A * 6 + 6) if role[q * K + k] == "0"), None)
            if goalie is None or any(role[q * K + k] not in "012345" for k in range(K)):
                continue
            sg = -1 if P(q, goalie)[1] > 0 else 1        # the carrier's team turned to attack +y (the top net)
            a = q - 4
            dt = (t[q] - t[a]) / (1000 / 60)
            sk = {}
            for k in range(K):
                (x0, y0), (x1, y1) = P(a, k), P(q, k)
                side = "us" if k // 6 == A else "them"
                sk[f"{side}{role[q * K + k]}"] = [sg * x1, sg * y1, sg * (x1 - x0) / dt, sg * (y1 - y0) / dt,
                                                   (int(m["facing"][q * K + k]) + (0 if sg > 0 else 4)) % 8]
            to = None
            if ev.get("pass") and ev["pass"].get("to", -1) >= 0:
                to = next((k for k in range(A * 6, A * 6 + 6) if int(m["roster"][q * K + k], 36) == ev["pass"]["to"]), None)
            if to is None or role[q * K + to] == "0":
                best = None
                for k in range(A * 6, A * 6 + 6):
                    if k == c or role[q * K + k] == "0" or math.dist(P(q, k), P(q, c)) > 250:
                        continue
                    room = min(math.dist(P(q, k), P(q, o)) for o in range((1 - A) * 6, (1 - A) * 6 + 6))
                    if best is None or room > best[0]:
                        best = (room, k)
                if best is None:
                    continue
                to = best[1]
            px, py = m["puck"][q * 3], m["puck"][q * 3 + 1]
            rows.append(dict(src=[p.stem, q], sk=sk, carrier=role[q * K + c], receiver=role[q * K + to],
                             puck=[sg * px, sg * py], real=ev["out"]))
    cache.write_text(json.dumps(rows))
    return rows


class Rig(H.Harness):
    def park(self, keep_shooter=True):           # nobody parked: everyone plays
        return None

    def objects(self):
        e = self.e
        out = {}
        for k in range(12):
            out[("us" if k < 6 else "them") + str(e.w(POSITION + H.o(k)))] = k
        return out

    def place(self, s, seed):
        e = self.e
        e.unserialize(self.base)
        e.setw(H.CLOCK, 250)
        e.setw(H.SEED, seed >> 16 or 1)
        e.setw(H.SEED + 2, seed & 0xFFFF or 1)
        obj = self.objects()
        for key, (x, y, vx, vy, face) in s["sk"].items():
            k = obj.get(key)
            if k is None:
                return None
            self.put(k, round(x), round(y))
            e.setw(H.XVEL + H.o(k), round(vx * VEL))
            e.setw(H.YVEL + H.o(k), round(vy * VEL))
            e.setw(FACING + H.o(k), face)
        for k in range(12):                       # no animation left over from the saved moment (it blocks input)
            if e.w(POSITION + H.o(k)) == 0:
                continue
            e.setw(PFALOCK + H.o(k), 0)
            if e.w(PF2AIP + H.o(k)):
                e.setw(PF2AIP + H.o(k), 0)
                e.setw(SPA + H.o(k), SKATE)
        c = obj["us" + s["carrier"]]
        self.put(H.PUCK, round(s["puck"][0]), round(s["puck"][1]))
        e.setw(H.PUCKC, H.o(c))
        e.setw(CARRIER2, H.o(c))                # the carrier word beside puckc ($0AE7)
        for k in range(6):                       # pad 1 on the carrier: c1playernum and the person flag (pflags $0008)
            e.setw(PFLAGS + H.o(k), e.w(PFLAGS + H.o(k)) & ~0x0008)
        e.setw(PFLAGS + H.o(c), e.w(PFLAGS + H.o(c)) | 0x0008)
        e.setw(C1PLAYER, H.o(c))
        pad = next((e.w(PLAYERPAD + H.o(k)) for k in range(6) if not e.w(PLAYERPAD + H.o(k)) & 0x8000), 0)
        for k in range(6):                       # playerpad: the pad each object answers (negative: the computer)
            e.setw(PLAYERPAD + H.o(k), 0xFFFF)
        e.setw(PLAYERPAD + H.o(c), pad)
        return c, obj["us" + s["receiver"]], obj


def pos(h, k):
    return h.sw(H.XPOS + H.o(k)), h.sw(H.YPOS + H.o(k))


def scout(h, s, seed):
    """The frame an away skater first bursts at the carrier (no B pressed), and who; None if nobody does."""
    r = h.place(s, seed)
    if r is None:
        return None
    c, mate, obj = r
    e = h.e
    start = e.serialize()
    vx, vy = s["sk"]["us" + s["carrier"]][2:4]
    skate = dir_to(vx, vy) if math.hypot(vx, vy) > 0.3 else s["sk"]["us" + s["carrier"]][4]
    prev = {k: e.w(SPA + H.o(k)) for k in range(6, 12)}
    for f in range(SCOUT):
        e.run(1, hold=DIRS[skate])
        if e.w(H.PUCKC) != H.o(c):
            return None                          # lost it before any burst at him
        for k in range(6, 12):
            a = e.w(SPA + H.o(k))
            if a == LUNGE and prev[k] != LUNGE:
                (kx, ky), (cx, cy) = pos(h, k), pos(h, c)
                d = math.hypot(cx - kx, cy - ky)
                ang = math.radians(45 * (e.w(FACING + H.o(k)) & 7))
                cos = (math.sin(ang) * (cx - kx) + math.cos(ang) * (cy - ky)) / (d or 1)
                if d < REACH and math.degrees(math.acos(max(-1, min(1, cos)))) <= CONE:
                    if e.w(C1PLAYER) != H.o(c) or not e.w(PFLAGS + H.o(c)) & 0x0008:
                        return None              # pad 1 isn't on the carrier any more: no test
                    return dict(start=start, burst=f, checker=k, carrier=c, mate=mate, skate=skate)
            prev[k] = a
    return None


def trial(h, sc, offset):
    e = h.e
    e.unserialize(sc["start"])
    c, k, mate, skate = sc["carrier"], sc["checker"], sc["mate"], sc["skate"]
    bf = None if offset is None else sc["burst"] + offset
    contact = down = release = lost = b_at = pad_ok = None
    after = None
    for f in range(sc["burst"] + 60 + AFTER):
        hold = DIRS[skate]
        if release is None and lost is None and bf is not None and bf <= f < bf + 3 and e.w(H.PUCKC) == H.o(c):
            mx, my = pos(h, mate)
            cx, cy = pos(h, c)
            hold = ["B"] + DIRS[dir_to(mx - cx, my - cy)]
            if b_at is None:
                b_at, pad_ok = f, e.w(C1PLAYER) == H.o(c)
        e.run(1, hold=hold)
        own = e.w(H.PUCKC)
        if f >= min(sc["burst"], bf if bf is not None else 10 ** 6) - 1 and contact is None and \
                (math.dist(pos(h, c), pos(h, k)) < CONTACT or e.w(SPA + H.o(k)) in CHECKS):
            contact = f
        if down is None and e.w(SPA + H.o(c)) in DOWN:
            down = f
        if release is None and lost is None and own != H.o(c):
            if b_at is not None and e.w(SPA + H.o(c)) in PASS:
                release = f
            else:
                lost = f
        t0 = release if release is not None else lost
        if t0 is not None:
            if not own & 0x8000 and own != H.o(c):
                after = own // 2
                break
            if f - t0 > AFTER:
                break
        elif bf is not None and f > bf + 40:
            break
        elif bf is None and f > sc["burst"] + 60:
            break
        if f % 120 == 119:
            breathe()
    if release is not None:
        who = "teammate" if after is not None and after < 6 else "checker" if after == k else \
            "other opponent" if after is not None else "nobody"
        res = ("passed after contact: " if contact is not None and contact < release else "passed: ") + who
    elif lost is not None:
        res = "caught" if contact is not None and contact <= lost else "lost it"
    else:
        res = "kept it"
    return dict(res=res, pad_ok=pad_ok, offset=offset, burst=sc["burst"], contact=contact, down=down, release=release, b=b_at, lost=lost,
                lead=(contact - release) / 60 if contact is not None and release is not None else None,
                lead_down=(down - release) / 60 if down is not None and release is not None else None)


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
    sits = situations()
    random.Random(7).shuffle(sits)
    sits = sits[:n]
    done = {(r["i"], r["seed"], r.get("offset", "?")) for r in map(json.loads, open(path))} if path.exists() else set()
    h = Rig(state=SNES_STATE_TOP, top=True)
    t0 = time.time()
    with open(path, "a") as fh:
        for i, s in enumerate(sits):
            for sd in range(SEEDS):
                if all((i, sd, off) in done for off in OFFSETS) or (i, sd, "none") in done:
                    continue
                if time.time() - t0 > minutes * 60:
                    print("time up", flush=True)
                    return
                seed = random.Random(i * 10 + sd).getrandbits(32)
                sc = scout(h, s, seed)
                breathe()
                if sc is None:
                    fh.write(json.dumps(dict(i=i, seed=sd, offset="none", res="no burst at him")) + "\n")
                    fh.flush()
                    continue
                for off in OFFSETS:
                    if (i, sd, off) in done:
                        continue
                    r = trial(h, sc, off)
                    breathe()
                    r.update(i=i, seed=sd, offset=off, real=s.get("real"))
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
            print(f"situation {i + 1} of {len(sits)}", flush=True)
    print("done", flush=True)


def report(path):
    allrows = [json.loads(l) for l in open(path)]
    rows = [r for r in allrows if r["offset"] != "none"]
    print(len(rows), "trials,", len({(r["i"], r["seed"]) for r in rows}), "placements with a burst at the carrier;",
          sum(r["offset"] == "none" for r in allrows), "with none")
    by = defaultdict(Counter)
    for r in rows:
        by[r["offset"]][r["res"]] += 1
    print("By when B came (frames after the burst):")
    for off in OFFSETS:
        c = by.get(off)
        if c:
            n = sum(c.values())
            print(f"  {str(off):>5} ({n:4}): " + ", ".join(f"{k} {100 * v / n:.0f}%" for k, v in c.most_common()))
    print("Reached a teammate, by offset, same placement:")
    full = defaultdict(dict)
    for r in rows:
        full[(r["i"], r["seed"])][r["offset"]] = r
    full = {k: v for k, v in full.items() if len(v) == len(OFFSETS)}
    for off in OFFSETS:
        n = len(full)
        ok = sum(v[off]["res"].endswith("teammate") for v in full.values())
        dn = sum(v[off].get("down") is not None for v in full.values())
        print(f"  {str(off):>5}: {ok} of {n} ({100 * ok / max(1, n):.0f}%); knocked down in {dn}")
    for key, lab in (("lead", "before contact"), ("lead_down", "before a knockdown")):
        print(f"Passes by lead {lab} (real seconds):")
        for b0, b1, nm in ((-9, 0, "after it"), (0, 0.10, "under 0.10 s"), (0.10, 0.25, "0.10-0.25 s"), (0.25, 0.50, "0.25-0.50 s"), (0.50, 9, "0.50 s or more")):
            sel = [r for r in rows if r["release"] is not None and r.get(key) is not None and b0 <= r[key] < b1]
            c = Counter(r["res"].split(": ")[-1] for r in sel)
            n = len(sel) or 1
            print(f"  {nm:16} {len(sel):5}: " + ", ".join(f"{k} {100 * v / n:.0f}%" for k, v in c.most_common()))


if __name__ == "__main__":
    main()
