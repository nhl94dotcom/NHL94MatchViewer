"""NOSE4Web's runaway-speed fix, played in the game (Genesis, 2026-11-07, the user approved running the patched ROM).
The "deceleration off" flag (pfdoff, pflags bit 0; GENESIS_MECHANICS 3.4) leaks: a person taking over a pass receiver
(asspassrec's exit when pfjoycon is set), a skater getting up from a fall into the boards (the end of the fall), and a
missed one-timer (assonetimer leaves it for puckstick, which a whiff never reaches). The fix clears it in the first
two. With it on, each burst stacks on the last: a runaway.

From the recorded check moments (check_pass_timing's situations: a person's carrier, a receiver, a checker), placed in
live play, on one ROM per run (the frontend takes one core; run it for each ROM and compare):

- takeover: the carrier (pad 1) passes to the receiver, then presses B again (the game's own switch: control goes to
  the skater nearest the puck's spot ahead); once he has the receiver, he skates away from the puck (so he never
  touches it) and bursts twice (C, 0.5 s apart). Peak speed over the next 2 s.
- boards: the checker (pad 2) bursts into the carrier; trials where the carrier falls with the flag set (a fall into
  the boards). Once he is up, he bursts twice. Peak speed.
- onetimer: the carrier passes, then presses C as the pass nears (the receiver one-times it); and takeover-onetimer:
  pass, B, then C. The puck's speed and direction 10 frames after the shot, and the flag on the shooter.
- whiff: pass, then C at once (the one-timer swings long before the puck): then the bursts away from the puck; and
  takeover_whiff: pass, B (he is the person's), then C at once, then the bursts.

A runaway: still over 10,000 0.6 s after the last burst (LATE; normal skating never exceeds about 9,500).
python runaway_fix_test.py RUN ROM [N situations]   -> paths.RUNS / RUN / trials.jsonl
python runaway_fix_test.py report RUN_A RUN_B

Results: docs/STUDY_NOTES.md "NOSE4Web's runaway-speed fix, played in the game"."""
import json
import math
import random
import sys
from collections import Counter, defaultdict

import check_pass_timing as T
from bot import rec, PUCKC, pad, dir_to
from bot_scenario import place, live_state, LIVE_STATES, CONT_TEAMS, C2PLAYER
from emu import Emu
from lowload import breathe, gentle
from paths import RUNS

C1PLAYER = 0xC320
ONLY = set(filter(None, __import__('os').environ.get('NHL94_RFT_CASES', '').split(',')))
RUNAWAY = 12000
LATE = 10000   # normal skating never exceeds about 9,500; a burst fades to it in about half a second


def sw(e, a):
    v = e.w(a)
    return v - 0x10000 if v >= 0x8000 else v


def speed(e, k):
    return math.hypot(sw(e, rec(k) + 0x28), sw(e, rec(k) + 0x2A))


def pos(e, k):
    return sw(e, rec(k)), sw(e, rec(k) + 0x14)


def flag(e, k):
    return e.b(rec(k) + 0x62) & 1


def setup(e, base, s, seed, checker_on_pad2=False):
    carrier = place(e, base, s, seed)
    if carrier is None:
        return None
    mate, checker = T.slot_of(e, "us", s["receiver"]), T.slot_of(e, "them", s["checker"])
    if mate is None or checker is None:
        return None
    if checker_on_pad2:
        e.setw(CONT_TEAMS[1], 2)
        for k in range(6, 12):
            e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
        e.setb(rec(checker) + 0x62, e.b(rec(checker) + 0x62) | 8)
        e.setw(C2PLAYER, checker)
    return carrier, mate, checker


def away(e, k):
    """A direction for k away from the puck."""
    kx, ky = pos(e, k)
    px, py = pos(e, 14)
    return dir_to(kx - px, ky - py)


def bursts(e, k, frames=130):
    """Three bursts (C) 30 frames apart, skating away from the puck; peak speed, and whether he touched it."""
    peak, late, touched = 0, 0, False
    for f in range(frames):
        d = away(e, k)
        hold = (["C"] if f in (2, 3, 32, 33, 62, 63) else []) + pad(d)
        e.run(1, hold=hold)
        peak = max(peak, speed(e, k))
        if f >= frames - 30:
            late = max(late, speed(e, k))                 # 37 frames and more after the last burst: a burst has faded
        touched = touched or e.w(PUCKC) == k
        if e.b(0xFFF7) != 0:
            break
    bursts.late = round(late)
    return round(peak), touched


def pass_to(e, carrier, mate, extra=None, frames=90):
    """The carrier passes (B toward the mate); extra(f, release) gives more presses after the release. Returns the
    release frame (None: no pass)."""
    release = None
    for f in range(frames):
        cx, cy = pos(e, carrier)
        mx, my = pos(e, mate)
        hold = ["B"] + pad(dir_to(mx - cx, my - cy)) if f < 3 else []
        if release is not None and extra:
            hold = extra(f, release)
            if hold == "done":
                return release
        e.run(1, hold=hold)
        if release is None and f < 20 and e.w(PUCKC) != carrier:
            release = f
            if not extra:
                return release
    return release


def takeover(e, base, s, seed):
    st = setup(e, base, s, seed)
    if not st:
        return dict(res="not placed")
    carrier, mate, _ = st
    rel = pass_to(e, carrier, mate)
    if rel is None:
        return dict(res="no pass")
    for f in range(12):                                   # B again: control to the receiver
        e.run(1, hold=["B"] if 2 <= f < 4 else [])
        if e.w(C1PLAYER) == mate:
            break
    if e.w(C1PLAYER) != mate:
        return dict(res="no switch")
    on = flag(e, mate)
    for _ in range(4):                                    # step clear of the puck's path first
        e.run(1, hold=pad(away(e, mate)))
    held = flag(e, mate)                                  # the fix clears it here (asspassrec's exit)
    peak, touched = bursts(e, mate)
    return dict(res="touched" if touched else "ok", flag_at_switch=on, flag_after_switch=held, flag_after=flag(e, mate),
                peak=peak, late=bursts.late)


def boards(e, base, s, seed):
    st = setup(e, base, s, seed, checker_on_pad2=True)
    if not st:
        return dict(res="not placed")
    carrier, _, checker = st
    fell = None
    for f in range(150):
        cx, cy = pos(e, carrier)
        kx, ky = pos(e, checker)
        e.run(1, hold=[], hold2=(["C"] if 10 <= f < 13 else []) + pad(dir_to(cx - kx, cy - ky)))
        if flag(e, carrier) and e.b(rec(carrier) + 0x62) & 0x20 and fell is None:   # flag on while locked in a fall
            fell = f
        if fell is not None and f > fell + 10 and not e.b(rec(carrier) + 0x62) & 0x20:
            break                                         # up again
        if e.b(0xFFF7) != 0:
            return dict(res="stoppage")
    if fell is None:
        return dict(res="no fall with the flag")
    e.setw(C1PLAYER, carrier)                             # still his to skate
    on = flag(e, carrier)
    peak, touched = bursts(e, carrier)
    return dict(res="touched" if touched else "ok", flag_up=on, peak=peak, late=bursts.late)


def onetimer(e, base, s, seed, switch=False, whiff=False):
    st = setup(e, base, s, seed)
    if not st:
        return dict(res="not placed")
    carrier, mate, _ = st
    state = {"c": None, "sw": False}

    def extra(f, rel):
        if whiff and switch:                              # take him over, then swing at once (long before the puck)
            if not state["sw"]:
                if e.w(C1PLAYER) == mate:
                    state["sw"], state["c"] = True, f
                return ["B"] if rel + 2 <= f < rel + 4 else ([] if f < rel + 15 else "done")
            return ["C"] if f < state["c"] + 2 else ([] if f < state["c"] + 30 else "done")
        if whiff:
            return ["C"] if rel + 1 <= f < rel + 3 else ([] if f < rel + 30 else "done")
        if switch and not state["sw"] and f >= rel + 2:
            if e.w(C1PLAYER) == mate:
                state["sw"] = True
            return ["B"] if f < rel + 4 else []
        mx, my = pos(e, mate)
        px, py = pos(e, 14)
        if state["c"] is None and math.hypot(mx - px, my - py) < 40:
            state["c"] = f
        if state["c"] is not None and f < state["c"] + 3:
            return ["C"]
        if state["c"] is not None and f > state["c"] + 12:
            return "done"
        return []
    rel = pass_to(e, carrier, mate, extra=extra, frames=120)
    if rel is None:
        return dict(res="no pass")
    out = dict(res="ok", vx=sw(e, rec(14) + 0x28), vy=sw(e, rec(14) + 0x2A), shooter_flag=flag(e, mate),
               anim="%04x" % e.w(rec(mate) + 0x58), switched=state["sw"])
    if whiff:
        e.setw(C1PLAYER, mate)
        peak, touched = bursts(e, mate)
        out.update(peak=peak, late=bursts.late, touched=touched, res="touched" if touched else "ok")
    return out


CASES = dict(takeover=takeover, boards=boards, onetimer=lambda *a: onetimer(*a),
             takeover_onetimer=lambda *a: onetimer(*a, switch=True), whiff=lambda *a: onetimer(*a, whiff=True),
             takeover_whiff=lambda *a: onetimer(*a, switch=True, whiff=True))


def main():
    run, rom = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 120
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    gentle()
    e = Emu(rom)
    bases = [live_state(e, j) for j in range(LIVE_STATES)]
    sits = T.situations()
    random.Random(11).shuffle(sits)
    with open(out / "trials.jsonl", "w") as fh:
        for i, s in enumerate(sits[:n]):
            for case, fn in CASES.items():
                if ONLY and case not in ONLY:
                    continue
                r = fn(e, bases[i % LIVE_STATES], s, random.Random(i).getrandbits(32))
                r.update(i=i, case=case)
                fh.write(json.dumps(r) + "\n")
                breathe()
    print("done", flush=True)


def report(runs):
    data = {r: [json.loads(l) for l in open(RUNS / r / "trials.jsonl")] for r in runs}
    for case in CASES:
        if not any(x["case"] == case for r in runs for x in data[r]):
            continue
        print(f"\n{case}:")
        for r in runs:
            rows = [x for x in data[r] if x["case"] == case]
            ok = [x for x in rows if x["res"] == "ok"]
            line = f"  {r:14} {len(rows)} trials, {len(ok)} measured; " + str(dict(Counter(x['res'] for x in rows)))
            if ok and "peak" in ok[0]:
                peaks = sorted(x["peak"] for x in ok)
                lates = sorted(x["late"] for x in ok)
                line += (f"; still fast 0.6 s after the last burst (over {LATE}) {sum(v > LATE for v in lates)}, that speed's median"
                         f" {lates[len(lates) // 2]}, max {lates[-1]} (peaks: median {peaks[len(peaks) // 2]}, max {peaks[-1]})")
            if ok and "flag_after_switch" in ok[0]:
                line += f"; flag on at the switch {sum(x['flag_at_switch'] for x in ok)}, still on 4 frames later {sum(x['flag_after_switch'] for x in ok)}"
            if ok and "flag_up" in ok[0]:
                line += f"; flag on once he is up {sum(x['flag_up'] for x in ok)}"
            if ok and "shooter_flag" in ok[0]:
                line += f"; shooter's flag on after {sum(x['shooter_flag'] for x in ok)}"
            print(line)
        if len(runs) == 2 and case in ("onetimer", "takeover_onetimer"):
            a = {x["i"]: x for x in data[runs[0]] if x["case"] == case and x["res"] == "ok"}
            b = {x["i"]: x for x in data[runs[1]] if x["case"] == case and x["res"] == "ok"}
            both = sorted(set(a) & set(b))
            same = sum((a[i]["vx"], a[i]["vy"]) == (b[i]["vx"], b[i]["vy"]) for i in both)
            print(f"  the puck 10 frames after the shot, the same in both: {same} of {len(both)}")
            for r, rows in ((runs[0], a), (runs[1], b)):
                sp = sorted(math.hypot(x["vx"], x["vy"]) for x in rows.values())
                print(f"  {r:14} shot speed median {sp[len(sp) // 2]:.0f}, share over 15,000 {sum(v > 15000 for v in sp) / max(1, len(sp)):.0%}")


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2:])
    else:
        main()
