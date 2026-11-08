"""NOSE4Web's penalty-shot table fix, played in the game (Genesis, 2026-11-08, the user approved running the patched
ROMs). PenShotPenalties (tables94.asm) is read one word early in the original: a foul on a breakaway gives the penalty
shot of the foul before it in the code list (charging -> slashing PS, slashing -> roughing PS, ...). The fix moves the
seven entries one word later.

A breakaway is made in live play: a carrier (the computer's, skating at the net) crossing the blue line with every skater of the
other team behind him, one of them close behind, chasing (the computer's, or on pad 2 pressing C, B or holding B toward
him). When a foul is called (a new PenBuf entry), the frame is played again from the frame before with BA_PS_flags bit 3 ("a penalty shot pending") set: PenShotChk
then returns the foul's own code untouched (clearing the breakaway flag instead changes the frame's assignments). So each trial
gives the pair (the foul, the penalty shot called for it).

python ps_table_test.py RUN ROM [N]   -> paths.RUNS / RUN / trials.jsonl
python ps_table_test.py report RUN [RUN]"""
import json
import random
import sys
from collections import Counter

from bot import rec, PUCKC, pad, dir_to
from bot_scenario import live_state, reset_ai, LIVE_STATES, CONT_TEAMS, C2PLAYER, C1PLAYER
from emu import Emu
from lowload import breathe, gentle
from paths import RUNS

PENBUF, BA_PS_FLAGS, BA_SKTR, PSPENALTY, OPTPEN = 0xC3A4, 0xC2F2, 0xD406, 0xD410, 0xD056
NAMES = {0x12: "roughing (injury)", 0x14: "no text (injury)", 0x16: "charging", 0x18: "slashing", 0x1A: "roughing",
         0x1C: "cross check", 0x1E: "hooking", 0x20: "tripping", 0x22: "interference", 0x24: "holding",
         0x2E: "hooking PS", 0x30: "tripping PS", 0x34: "interference PS", 0x36: "roughing PS", 0x38: "charging PS",
         0x3A: "cross check PS", 0x3C: "slashing PS"}
RIGHT = {0x16: 0x38, 0x18: 0x3C, 0x1A: 0x36, 0x1C: 0x3A, 0x1E: 0x2E, 0x20: 0x30}   # the foul's own penalty shot
MODES = ("cpu", "C", "B", "Bhold")


def sw(v):
    return v - 0x10000 if v >= 0x8000 else v


def penbuf(e):
    out = []
    for i in range(8):
        v = e.w(PENBUF + 2 * i)
        if v == 0:
            break
        out.append(v)
    return out


def put(e, k, x, y, vx=0.0, vy=0.0, face=0):
    r = rec(k)
    e.setw(r, round(x) & 0xFFFF)
    e.setw(r + 2, 0)
    e.setw(r + 0x14, round(y) & 0xFFFF)
    e.setw(r + 0x16, 0)
    e.setw(r + 0x18, 0)
    e.setl(r + 0x1C, (round(x) & 0xFFFF) << 16)
    e.setl(r + 0x20, (round(y) & 0xFFFF) << 16)
    e.setw(r + 0x28, round(vx * 4096) & 0xFFFF)
    e.setw(r + 0x2A, round(vy * 4096) & 0xFFFF)
    e.setw(r + 0x2C, 0)
    e.setb(r + 0x55, face % 8)


def setup(e, base, rnd):
    """The breakaway. Returns (carrier, chaser, direction up the ice (+1 / -1), mode)."""
    e.unserialize(base)
    e.setw(0xC468, 250)
    e.setl(0xD066, rnd.getrandbits(32))
    e.setw(OPTPEN, 1)
    e.setw(PENBUF, 0)
    e.setw(BA_PS_FLAGS, 0)
    roles = {k: e.b(rec(k) + 0x35) for k in range(12)}
    carrier = next(k for k in range(6) if roles[k] == 4)
    up = 1 if e.b(rec(carrier) + 0x62) & 0x80 else -1        # pfgoal: he attacks the top net
    face = 0 if up > 0 else 4
    x0, y0 = rnd.uniform(-60, 60), up * rnd.uniform(55, 82)   # outside the zone: the flag is set crossing the line
    v = rnd.uniform(1.0, 2.0)
    put(e, carrier, x0, y0, 0, up * v, face)
    them = [k for k in range(6, 12) if roles[k] not in (0, 0xFF)]
    chaser = rnd.choice(them)
    gap = rnd.uniform(8, 28)
    put(e, chaser, x0 + rnd.uniform(-10, 10), y0 - up * gap, 0, up * (v + rnd.uniform(0.3, 1.2)), face)
    for j, k in enumerate(m for m in them if m != chaser):
        put(e, k, rnd.uniform(-90, 90), y0 - up * rnd.uniform(70, 160), 0, up * 1.0, face)
    for k in range(6):
        if roles[k] not in (0, 0xFF, 4):
            put(e, k, rnd.uniform(-90, 90), y0 - up * rnd.uniform(40, 140), 0, up * 1.0, face)
    for k in range(12):
        if roles[k] <= 5:
            reset_ai(e, k, str(roles[k]), k < 6, k == carrier)
    for k in range(12):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setw(CONT_TEAMS[0], 0)                       # the carrier is the computer's (a person's lost the placed puck)
    mode = rnd.choice(MODES)
    if mode != "cpu":
        e.setw(CONT_TEAMS[1], 2)
        e.setb(rec(chaser) + 0x62, e.b(rec(chaser) + 0x62) | 8)
        e.setw(C2PLAYER, chaser)
    else:
        e.setw(CONT_TEAMS[1], 0)
    pr = rec(14)
    e.setw(pr, round(x0) & 0xFFFF)
    e.setw(pr + 0x14, round(y0 + up * 4) & 0xFFFF)
    e.setw(pr + 0x18, 0)
    e.setw(PUCKC, carrier)
    return carrier, chaser, up, mode


def holds(e, f, carrier, chaser, up, mode):
    h1 = []
    if mode == "cpu":
        return h1, []
    cx, cy = sw(e.w(rec(carrier))), sw(e.w(rec(carrier) + 0x14))
    kx, ky = sw(e.w(rec(chaser))), sw(e.w(rec(chaser) + 0x14))
    d = pad(dir_to(cx - kx, cy - ky))
    if mode == "C":
        return h1, d + (["C"] if f % 12 in (0, 1) else [])
    if mode == "B":
        return h1, d + (["B"] if f % 10 in (0, 1) else [])
    return h1, d + ["B"]


def trial(e, base, rnd):
    carrier, chaser, up, mode = setup(e, base, rnd)
    broke = False
    before = penbuf(e)
    hist = []                                         # (state, holds, BA_PS_flags) at the start of each frame
    for f in range(150):
        h1, h2 = holds(e, f, carrier, chaser, up, mode)
        hist = (hist + [(e.serialize(), (h1, h2), e.w(BA_PS_FLAGS))])[-4:]
        e.run(1, hold=h1, hold2=h2)
        broke = broke or bool(e.b(rec(carrier) + 0x64) & 2)
        now = penbuf(e)
        if now != before:
            new = [v for v in now if v not in before]
            if not new:
                before = now
                continue
            code, who = new[0] >> 8, new[0] & 0xFF
            if code < 0x12:                           # a goal or another whistle
                return dict(res="whistle %02x" % code, mode=mode, brk=broke)
            out = dict(res="foul", mode=mode, frame=f, code=code, who=who, carrier=carrier, chaser=chaser,
                       brk=bool(e.b(rec(carrier) + 0x64) & 2) or broke, ps_flags=e.w(BA_PS_FLAGS),
                       shooter=e.w(BA_SKTR), pspenalty=e.w(PSPENALTY), plain=code, plain_who=who)
            if code >= 0x2E:
                # The game's frame and the emulator's are not in step: PenShotChk can run in one and AddPenalty in
                # the next. Played again from the frame where "pending" (BA_PS_flags bit 3, the word's $0800) came
                # on, with it on from the start: PenShotChk then leaves d0, the foul, as it is
                start = next((j for j in range(len(hist)) if not hist[j][2] & 0x0800 and
                              (hist[j + 1][2] if j + 1 < len(hist) else e.w(BA_PS_FLAGS)) & 0x0800), None)
                if start is None:
                    out.update(plain=None, plain_who=None, note="pending earlier")
                    return out
                real = e.serialize()
                e.unserialize(hist[start][0])
                e.setw(BA_PS_FLAGS, e.w(BA_PS_FLAGS) | 0x0800)
                again = []
                for st, (a1, a2), _ in hist[start:] + [(None, (h1, h2), None)] * 2:
                    e.run(1, hold=a1, hold2=a2)
                    again = [v for v in penbuf(e) if v not in before]
                    if again:
                        break
                out["plain"] = again[0] >> 8 if again else None
                out["plain_who"] = again[0] & 0xFF if again else None
                e.unserialize(real)                   # back to the game as it was played
            return out
        if e.b(0xFFF7) != 0 or e.w(0xC2EA) & 0x0100:
            return dict(res="stoppage", mode=mode, brk=broke)
    return dict(res="none", mode=mode, brk=broke)


def main():
    run, rom = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    gentle()
    e = Emu(rom)
    bases = [live_state(e, j) for j in range(LIVE_STATES)]
    with open(out / "trials.jsonl", "w") as fh:
        for i in range(n):
            r = trial(e, bases[i % LIVE_STATES], random.Random(1000 + i))
            r["i"] = i
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            breathe()
    print("done", flush=True)


def report(runs):
    for run in runs:
        rows = [json.loads(l) for l in open(RUNS / run / "trials.jsonl")]
        print(f"\n{run}: {len(rows)} trials, {dict(Counter(r['res'] for r in rows))}; breakaway flag seen "
              f"{sum(r['brk'] for r in rows)}")
        fouls = [r for r in rows if r["res"] == "foul"]
        pairs = Counter((r["plain"], r["code"], r["who"] == r["plain_who"], r["shooter"] == r["carrier"] if r["code"] >= 0x2E else None)
                        for r in fouls)
        for (plain, code, same, shooter), c in sorted(pairs.items(), key=lambda t: (t[0][0] or 0, t[0][1])):
            ok = "" if code < 0x2E else (" right" if RIGHT.get(plain) == code else " WRONG")
            print(f"  {NAMES.get(plain, plain)!s:18} -> {NAMES.get(code, hex(code)):18} {c:4}{ok}"
                  f"{'' if same else ' (other player)'}{'' if shooter in (None, True) else ' (shooter not the carrier)'}")


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2:])
    else:
        main()
