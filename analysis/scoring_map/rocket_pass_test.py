"""NOSE4Web's rocket pass fix, played in the game (2026-11-07, the user approved running the patched ROM). The fix
(NOSE4Web's Genesis Hacks page) changes passtoa0: the meeting time in 64ths of a second, not eighths rounded toward
zero (the rocket pass), and the other root tried when the first is just below zero (a pass to a teammate skating away
close by made in an eighth). NOSE4Web replayed the arithmetic on the recorded passes (its rocket_pass_cases.json:
every targeted pass of the recorded Genesis games, 345 that the original sends over 1.3 times their speed, 12 on the
wrong root). Here the same moments are played in the ROM, original and patched, to see what the puck and the
players do:

- the moment: the sample before the pass, placed in live play as bot_scenario.py places a situation (all 12 records
  and the puck), the passer on pad 1 pressing B toward the recorded receiver for 3 frames;
- the pass: the frame the puck leaves him, the receiver the game aimed at (passReceiverPlayerNum $BEE0), the
  puck's speed then against the pass's intended speed (passspeed x 65536 / 960, as the cases give it), and the
  game's inputs as passtoa0 read them (fast_pass_study's), with the original's and the fix's answers for them;
- what came of it: who had the puck next (the receiver, another teammate, an opponent, nobody within 3 s) and when.

One ROM per process (the frontend takes one core): run it for each ROM, then compare.
python rocket_pass_test.py RUN ROM CASES.json [N normal cases] [minutes]   -> paths.RUNS / RUN / trials.jsonl
python rocket_pass_test.py report RUN_A RUN_B

Results: docs/STUDY_NOTES.md "NOSE4Web's rocket pass fix, played in the game"."""
import json
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from bot import rec, PUCKC, pad, dir_to
from bot_scenario import place, live_state, LIVE_STATES
from check_pass_timing import slot_of
from emu import Emu
from lowload import breathe, gentle
from paths import RUNS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from bot_situations import situation  # noqa: E402

K, AFTER, PRESS = 12, 180, 3
PASSSPEED, PASSPLAYER = 0xBEDE, 0xBEE0
HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
PUCK = 14


def cases(path, n_normal):
    """Every over-1.3 and wrong-root case, and n_normal of the rest (seeded), in a fixed order."""
    rows = json.loads(Path(path).read_text())["passes"]
    flagged = [r for r in rows if r["over_1_3"] or r["wrong_root"]]
    rest = [r for r in rows if not (r["over_1_3"] or r["wrong_root"])]
    random.Random(7).shuffle(rest)
    return flagged + rest[:n_normal]


_matches = {}


def match(name):
    if name not in _matches:
        from share_game import load_js_object
        _matches.clear()                     # one game at a time: the files are big
        _matches[name] = json.loads(load_js_object(HOME / "matches" / f"{name}.js"))
    return _matches[name]


def answers(dx, dy, rvx, rvy, ps):
    """passtoa0's puck velocity for these inputs: the original's (fast_pass_study.solve) and the fix's (its PASS_CODE
    and the four edits after it: the time in 64ths, x t / 16, / (15 t)), each (t, vx, vy)."""
    import fast_pass_study as F
    w16, w32 = F.w16, F.w32
    original = F.solve(dx, dy, rvx, rvy, ps)
    d5 = w16(ps >> 2)
    d2, d3 = w16(dx >> 2), w16(dy >> 2)
    vx, vy = w16((w16(rvx) * 0xF0) >> 16), w16((w16(rvy) * 0xF0) >> 16)
    j = w16(2 * w16(w16(d2 * vx) + w16(d3 * vy)))
    k = w32(vx * vx + vy * vy - d5 * d5)
    a2 = w32(d2 * d2 + d3 * d3)
    disc = w32(j * j - w32(w16(a2) * w16(k) * 4))
    d0, kw = F.sroot(disc), (w16(k) >> 2) or 1
    t = 192
    for _ in range(2):
        num = w16(w16(d0) - j)
        d0 = -d0
        q = int(num / kw)
        r = num - q * kw
        if abs(q) > 32767:
            break                                  # overflow: as the original, left to the limit
        if q < 0 or (q == 0 and r and (r < 0) != (kw < 0)):
            continue                               # below zero: the other root
        t = 192 if q >= 24 else max(8, q * 8 + max(0, int(r * 8 / kw)))
        break
    out = []
    for disp_base, v in ((dx, vx), (dy, vy)):
        step = w32(v * t) >> 4
        disp = w16(w16(disp_base) + step)
        num = disp * 65536 + (0xFFFF if step < 0 else 0)
        q = int(num / (t * 15))
        out.append(None if abs(q) > 32767 else q)
    return original, (t, out[0], out[1])


def snapshot(e):
    """What passtoa0 reads, for every player: position, sprite frame, drawn mirrored, velocity; and the puck."""
    import fast_pass_study as F
    w = lambda a: F.w16(e.w(a))
    return {k: (w(rec(k)), w(rec(k) + 0x14), e.w(rec(k) + 6), e.b(rec(k) + 0x76) & 1, w(rec(k) + 0x28), w(rec(k) + 0x2A))
            for k in list(range(12)) + [PUCK]}


def moment(case):
    """The case's moment in the match file. The cases count the recording's raw samples (fast_pass_study reads the
    capture), which keep the netplay rollback reads the match file leaves out: the match sample, near the same time,
    where the passer has the puck where the capture shows it, the pass leaving after it."""
    from export_match import Capture
    import fast_pass_study as F
    try:
        m = match(case["game"])
        cap = Capture(HOME / "captures" / case["game"])
    except (OSError, ValueError):
        return None, None
    i = case["sample_before_pass"]
    px, py = F.w16(cap.word(i, F.rec(PUCK, 0))), F.w16(cap.word(i, F.rec(PUCK, 0x14)))
    T, P, own = m["t"], m["puck"], m["owner"]
    best = None
    for q in range(len(T) - 1):
        if own[q] == case["passer"] and own[q + 1] != case["passer"]:
            d = math.hypot(P[3 * q] - px, P[3 * q + 1] - py)
            if d < 6 and (best is None or abs(T[q] - cap.ms(i)) < best[0]):
                best = (abs(T[q] - cap.ms(i)), q)
    return (m, best[1]) if best else (m, None)


def trial(e, base, case, seed):
    m, q = moment(case)
    if q is None:
        return dict(res="no situation")
    team = 0 if case["passer"] < 6 else 1
    s = situation(m, q, team, "rocketpass", case["game"], owner=case["passer"])
    if not s:
        return dict(res="no situation")
    receiver_role = m["role"][q * K + case["receiver"]]
    carrier = place(e, base, s, seed)
    if carrier is None:
        return dict(res="not placed")
    mate = slot_of(e, "us", receiver_role)
    if mate is None:
        return dict(res="no receiver")
    pos = lambda k: (e.sw(rec(k)), e.sw(rec(k) + 0x14))
    release = after = None
    inputs = None
    for f in range(PRESS + 60 + AFTER):
        own = e.w(PUCKC)
        if release is None:
            if own != carrier:
                return dict(res="lost before the pass")
            cx, cy = pos(carrier)
            mx, my = pos(mate)
            snap = snapshot(e)
            hold = ["B"] + pad(dir_to(mx - cx, my - cy)) if f < PRESS else []
        else:
            hold = []
        e.run(1, hold=hold)
        if e.b(0xFFF7) != 0:
            return dict(res="stoppage")
        own = e.w(PUCKC)
        if release is None and own != carrier:
            release = f
            vx, vy = e.sw(rec(PUCK) + 0x28), e.sw(rec(PUCK) + 0x2A)
            speed, ps = math.hypot(vx, vy), e.w(PASSSPEED)
            target = e.w(PASSPLAYER)
            out = dict(release=f, speed=round(speed), passspeed=ps, intended=round(ps * 65536 / 960),
                       ratio=round(speed / (ps * 65536 / 960), 3) if ps else None, target=target, mate=mate,
                       aimed_at_mate=target == mate, vx=vx, vy=vy)
            if target < 12:                         # the game's inputs, as fast_pass_study reads them
                import fast_pass_study as F, struct
                # as passtoa0 read them: the receiver moved already this frame if his record comes before the
                # passer's (the game updates the records in order), the puck where it was put at the release (19 of
                # 32 passes on the original ROM then match exactly)
                post = snapshot(e)
                x, y, fr, mirror, rvx, rvy = (post if target < carrier else snap)[target]
                if 0 < fr < 900:
                    hx, hy = struct.unpack_from(">bb", F.ROM, F.HOTLIST + 2 * fr)
                    hx = hx if mirror else -hx
                    dx, dy = x + hx - post[PUCK][0], y - hy - post[PUCK][1]
                    orig, fix = answers(dx, dy, rvx, rvy, ps)
                    out.update(inputs=[dx, dy, rvx, rvy, ps], original=list(orig), fixed=list(fix),
                               is_original=[orig[1], orig[2]] == [vx, vy], is_fixed=[fix[1], fix[2]] == [vx, vy])
            continue
        if release is not None and own < 12 and own != carrier:
            after = own
            out.update(next=after, frames=f - release)
            break
        if release is None and f >= PRESS + 30:
            return dict(res="no pass")
        if release is not None and f - release > AFTER:
            out.update(next=None, frames=None)
            break
        if f % 120 == 119:
            breathe()
    if release is None:
        return dict(res="no pass")
    who = "receiver" if after == out["target"] else "teammate" if after is not None and (after < 6) == (carrier < 6) \
        else "opponent" if after is not None else "nobody"
    out["res"] = who
    return out


def main():
    run, rom, cases_path = sys.argv[1], sys.argv[2], sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    minutes = float(sys.argv[5]) if len(sys.argv) > 5 else 60
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    path = out / "trials.jsonl"
    done = {r["i"] for r in map(json.loads, open(path))} if path.exists() else set()
    gentle()
    e = Emu(rom)
    bases = [live_state(e, j) for j in range(LIVE_STATES)]
    todo = cases(cases_path, n)
    t0 = time.time()
    with open(path, "a") as fh:
        for i, c in enumerate(todo):
            if i in done:
                continue
            if time.time() - t0 > minutes * 60:
                print("time up", flush=True)
                return
            r = trial(e, bases[i % LIVE_STATES], c, random.Random(i).getrandbits(32))
            breathe()
            r.update(i=i, game=c["game"], sample=c["sample_before_pass"], over_1_3=c["over_1_3"], wrong_root=c["wrong_root"],
                     nose_original=c["original"]["speed"], nose_fixed=c["fixed"]["speed"], nose_intended=c["intended_speed"])
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            if i % 50 == 49:
                print(f"{i + 1} of {len(todo)}", flush=True)
    print("done", flush=True)


def report(runs):
    data = {}
    for run in runs:
        data[run] = {r["i"]: r for r in map(json.loads, open(RUNS / run / "trials.jsonl"))}
    both = sorted(set.intersection(*[set(d) for d in data.values()]))
    passed = [i for i in both if all("ratio" in data[r][i] for r in runs)]
    print(len(both), "cases in every run;", len(passed), "with a pass in every run;",
          {r: Counter(x["res"] for x in data[r].values() if "ratio" not in x).most_common(4) for r in runs})
    groups = {"over 1.3": lambda r: r["over_1_3"] and not r["wrong_root"], "wrong root": lambda r: r["wrong_root"],
              "the rest": lambda r: not r["over_1_3"] and not r["wrong_root"]}
    for g, test in groups.items():
        sel = [i for i in passed if test(data[runs[0]][i])]
        print(f"\n{g}: {len(sel)} passes")
        for run in runs:
            rows = [data[run][i] for i in sel]
            ratios = sorted(x["ratio"] for x in rows)
            med = ratios[len(ratios) // 2] if ratios else None
            res = Counter(x["res"] for x in rows)
            n = max(1, len(rows))
            times = sorted(x["frames"] for x in rows if x.get("frames") is not None)
            print(f"  {run:12} speed / intended: median {med}, over 1.3 {sum(x > 1.3 for x in ratios)}, max {ratios[-1] if ratios else None};"
                  f" aimed at the receiver {sum(x['aimed_at_mate'] for x in rows)};"
                  f" next: " + ", ".join(f"{k} {100 * v / n:.0f}%" for k, v in res.most_common()) +
                  (f"; frames to the next touch median {times[len(times) // 2]}" if times else ""))
        if len(runs) == 2:
            a, b = runs
            changed = Counter((data[a][i]["res"], data[b][i]["res"]) for i in sel if data[a][i]["res"] != data[b][i]["res"])
            print("  changed outcomes (first run -> second):", dict(changed.most_common(6)))


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2:])
    else:
        main()
