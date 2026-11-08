"""NOSE4Web's Genesis penalty-shot fixes, played in the game (2026-11-08, the user approved running the patched ROMs):
- bug 15, the retake: "a penalty shot pending" (BA_PS_flags bit 3) is cleared only by a goal or EndPenaltyShotPlay,
  so after another whistle during the attempt InProgress still finds it and starts another penalty shot. The fix
  clears it in puckshootout's .initflags as each attempt starts.
- bug 17, the ghost puck: a puck flipped out of the rink after the award whistle keeps "no collision" (pfnc, its
  pflags bit 2, $B7AC) into the attempt. The fix clears it in SetupPenaltyShot.

Each trial: a penalty shot awarded on a breakaway as in ps_table_test.py (the computer's carrier, a defender fouling
him). Then
- whistle: once the attempt is live (the shooter has the puck) and a random 10-60 frames in, another whistle is
  called (a PenBuf entry, out of play $06, as AddPenalty2 writes one) and the game played on. When the stoppage ends
  (gmpen off), InProgress has chosen: the puck back at centre with the attempt still under way (BA_PS_flags bit 2) is
  a retake; bit 2 going off (puckfaceoff) a faceoff.
- ghost: at the award whistle the puck is given pfnc (as a puck out of the rink has it); its pfnc as the attempt
  goes live (the shooter has the puck), and how the attempt ends (a goal, the puck out of the rink, or neither).

python ps_fixes_test.py RUN ROM [N]   -> paths.RUNS / RUN / trials.jsonl
python ps_fixes_test.py report RUN [RUN]"""
import json
import random
import sys
from collections import Counter

import ps_table_test as P
from bot import rec
from bot_scenario import live_state, LIVE_STATES
from emu import Emu
from lowload import breathe, gentle
from paths import RUNS

UNDERWAY, PENDING = 0x0400, 0x0800
PUCK_PFLAGS = rec(14) + 0x62                          # $B7AC
GMODE = 0xC2EA


def run_until(e, test, frames):
    for f in range(frames):
        e.run(1)
        if test():
            return f
    return None


def award(e, base, rnd):
    """A penalty shot foul (its PenBuf entry just written), or None."""
    for _ in range(40):
        r = P.trial(e, base, rnd)
        if r["res"] == "foul" and r["code"] >= 0x2E:
            return r
    return None


def whistle(e, base, rnd):
    r = award(e, base, rnd)
    if r is None:
        return dict(res="no award")
    if run_until(e, lambda: e.w(P.BA_PS_FLAGS) & UNDERWAY, 3000) is None:
        return dict(res="no attempt")
    shooter = e.w(P.BA_SKTR)
    if run_until(e, lambda: e.w(P.PUCKC) == shooter, 1500) is None:     # the attempt live: the shooter has the puck
        return dict(res="no carry")
    wait = rnd.randint(10, 60)
    for _ in range(wait):
        e.run(1)
        if not e.w(P.BA_PS_FLAGS) & UNDERWAY or e.w(GMODE) & 0x0400 or P.penbuf(e):
            return dict(res="ended first", code=r["code"])
    e.setw(P.PENBUF, 0x06 << 8 | shooter)               # out of play, called on the shooter (any player will do)
    e.setw(P.PENBUF + 2, 0)
    if run_until(e, lambda: e.w(GMODE) & 0x0400, 30) is None:   # gmpen: Stop4Pen has called it (the clock is
        return dict(res="whistle not called")                     # stopped all through an attempt)
    if run_until(e, lambda: not e.w(GMODE) & 0x0400, 3000) is None:  # InProgress has chosen what comes next
        return dict(res="stoppage never ends")
    for f in range(90):
        e.run(1)
        if not e.w(P.BA_PS_FLAGS) & UNDERWAY:
            return dict(res="faceoff", code=r["code"], frames=f)
        if (P.sw(e.w(rec(14))), P.sw(e.w(rec(14) + 0x14))) == (0, 0):
            return dict(res="retake", code=r["code"], frames=f)
    return dict(res="neither", code=r["code"], flags=e.w(P.BA_PS_FLAGS), gmode=e.w(GMODE))


def ghost(e, base, rnd):
    r = award(e, base, rnd)
    if r is None:
        return dict(res="no award")
    e.setb(PUCK_PFLAGS, e.b(PUCK_PFLAGS) | 4)
    if run_until(e, lambda: e.w(P.BA_PS_FLAGS) & UNDERWAY, 3000) is None:
        return dict(res="no attempt")
    shooter = e.w(P.BA_SKTR)
    if run_until(e, lambda: e.w(P.PUCKC) == shooter, 1500) is None:
        return dict(res="no carry")
    nc_start = bool(e.b(PUCK_PFLAGS) & 4)                 # as the attempt goes live
    out, nc_frames = False, 0
    for f in range(1500):
        e.run(1)
        nc_frames += bool(e.b(PUCK_PFLAGS) & 4)
        x, y = P.sw(e.w(rec(14))), P.sw(e.w(rec(14) + 0x14))
        out = out or abs(x) > 140 or abs(y) > 300
        if not e.w(P.BA_PS_FLAGS) & UNDERWAY:
            break
    return dict(res="ok", code=r["code"], nc_start=nc_start, nc_frames=nc_frames, out_of_rink=out, frames=f)


CASES = dict(whistle=whistle, ghost=ghost)


def main():
    run, rom = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    gentle()
    e = Emu(rom)
    bases = [live_state(e, j) for j in range(LIVE_STATES)]
    with open(out / "trials.jsonl", "w") as fh:
        for i in range(n):
            for case, fn in CASES.items():
                r = fn(e, bases[i % LIVE_STATES], random.Random(5000 + 97 * i))
                r.update(i=i, case=case)
                fh.write(json.dumps(r) + "\n")
                fh.flush()
                breathe()
    print("done", flush=True)


def report(runs):
    for run in runs:
        rows = [json.loads(l) for l in open(RUNS / run / "trials.jsonl")]
        print(f"\n{run}:")
        w = [r for r in rows if r["case"] == "whistle"]
        print(f"  whistle during the attempt: {dict(Counter(r['res'] for r in w))}")
        g = [r for r in rows if r["case"] == "ghost" and r["res"] == "ok"]
        print(f"  ghost: {len(g)} attempts; no-collision on as the attempt starts {sum(r['nc_start'] for r in g)}, "
              f"on through the attempt (frames, median) {sorted(r['nc_frames'] for r in g)[len(g) // 2] if g else '-'}, "
              f"the puck out of the rink {sum(r['out_of_rink'] for r in g)}; "
              f"{dict(Counter(r['res'] for r in rows if r['case'] == 'ghost'))}")


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2:])
    else:
        main()
