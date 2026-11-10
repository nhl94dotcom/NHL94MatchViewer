"""One-timers that can't start (Genesis, 2026-11-09; a community member: "B pass, C shoot, and the receiver just takes
the pass and stalls"). From the code (logic94 doinput, the passer's C): a one-timer starts only while onetimerplayer
($FFBF6C) is -1. assonetimer sets it to the receiver's SCnum when a one-timer starts; only EndOneTimer (the end of
assonetimer, or a check / fight knocking him out of it: collide94) and the faceoff setup put it back to -1. If his
one-timer assignment is replaced some other way, it stays set and every C on a pass does nothing (both teams) until
the next faceoff.

In each recorded Genesis game (captures/<name>/fast.bin.gz, the helper's blocks): every stretch with onetimerplayer
set, how long it lasted, and whether that record still had pf3onetimer (pflags3 +$64 bit 3) through it. A stretch
where the bit is gone but onetimerplayer stays set is a stuck one; for each, the C presses during it (pad bytes) and
what the stuck player was doing (his animation) when the bit went.

Also (the part that answers the question): every new C press on pads 1 and 2 ($BEEF / $BEF1 bit $20) while a pass
is in flight (passReceiverPlayerNum $BEE0 set, puckc $B7AA -1): whether a one-timer started within 6 samples (0.1 s
real), and if not, which of doinput's tests turned it down (in the code's order): the pad's skater (c1playernum $C320
/ c2playernum $C322) not the passer (lastplayer $BEDA) nor the receiver; a one-timer already on; the receiver a goalie
or a pad's skater (pflags +$62 bit 3, a teammate's pad); the puck not yet on the attacking half (pucky $B75E by the
skater's pfgoal, pflags bit 7). And each one-timer that started: how it ended (a shot: the team's shots on goal or
the puck at a one-timer's speed; caught: the receiver took the puck; neither).

python one_timer_misses.py [NAME ...]   (default: every Genesis game with a recording in Documents\\NHL94 Viewer)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from injury_risk_estimate import HOME, Capture  # noqa: E402

OTP, PASSREC, LASTP = 0xBF6C, 0xBEE0, 0xBEDA
PADS, CTRL, PUCKC, PUCKY, PUCKVX, PUCKVY = (0xBEEF, 0xBEF1), (0xC320, 0xC322), 0xB7AA, 0xB75E, 0xB772, 0xB774
REC, SZ = 0xB04A, 0x80
CLOCK, PERIOD, SCREEN = 0xC468, 0xC466, 0xFFF7


def signed(v):
    return v - 0x10000 if v >= 0x8000 else v


def study(name):
    t = (HOME / "matches" / f"{name}.js").read_text(encoding="utf-8")
    m = json.loads(t[t.index("{"):t.rindex("}") + 1])
    if m.get("system", "genesis") != "genesis":
        return None
    cap = Capture(HOME / "captures" / name, True)
    out = []
    i = 0
    while i < cap.n:
        p = signed(cap.w(i, OTP))
        if not 0 <= p < 16:
            i += 1
            continue
        start, bit_gone, anim_then = i, None, None
        while i < cap.n and signed(cap.w(i, OTP)) == p:
            if bit_gone is None and not cap.b(i, REC + SZ * p + 0x64) & 0x08:
                bit_gone, anim_then = i, cap.w(i, REC + SZ * p + 0x58)
            i += 1
        ms = cap.ms[min(i, cap.n - 1)] - cap.ms[start]
        stuck_ms = cap.ms[min(i, cap.n - 1)] - cap.ms[bit_gone] if bit_gone is not None else 0
        out.append({"start_ms": cap.ms[start] - cap.ms[0], "player": p, "ms": ms, "stuck_ms": stuck_ms,
                    "anim_when_bit_went": hex(anim_then) if anim_then is not None else None,
                    "period": cap.w(start, PERIOD), "clock": cap.w(start, CLOCK),
                    "ended_at_clock": cap.w(min(i, cap.n - 1), CLOCK)})
    presses = []
    for i in range(1, cap.n):
        for pad in (0, 1):
            if not cap.b(i, PADS[pad]) & 0x20 or cap.b(i - 1, PADS[pad]) & 0x20:
                continue
            ctrl, rec = signed(cap.w(i, CTRL[pad])), signed(cap.w(i, PASSREC))
            if not 0 <= ctrl < 12 or not 0 <= rec < 12 or signed(cap.w(i, PUCKC)) >= 0:
                continue
            last, otp = signed(cap.w(i, LASTP)), signed(cap.w(i, OTP))
            started = any(0 <= signed(cap.w(j, OTP)) < 16 for j in range(i, min(cap.n, i + 7)))
            fl = lambda k: cap.b(i, REC + SZ * k + 0x62)
            y = signed(cap.w(i, PUCKY))
            attack_half = (y if fl(ctrl) & 0x80 else -y) >= 0
            same_team = (ctrl < 6) == (rec < 6)
            if not same_team:
                continue                                   # a pass by the other team
            if started:
                why = "started"
            elif otp >= 0:
                why = "a one-timer already on"
            elif last == ctrl:
                why = ("receiver a goalie" if cap.b(i, REC + SZ * rec + 0x35) == 0 else
                       "puck not yet on the attacking half" if not attack_half else
                       "receiver on a pad (a teammate's)" if fl(rec) & 0x08 else "other (passer)")
            elif ctrl == rec:
                why = ("passed by a goalie" if 0 <= last < 12 and cap.b(i, REC + SZ * last + 0x35) == 0 else
                       "puck not yet on the attacking half" if not attack_half else "other (receiver)")
            else:
                why = "pad on a third skater"
            presses.append({"ms": cap.ms[i] - cap.ms[0], "why": why, "period": cap.w(i, PERIOD), "clock": cap.w(i, CLOCK)})
    return out, presses, ends(cap)


def ends(cap):
    res = []
    i = 0
    while i < cap.n:
        p = signed(cap.w(i, OTP))
        if not 0 <= p < 16:
            i += 1
            continue
        team = 0 if p < 6 else 1
        shots0 = cap.w(i, 0xC6CE if team == 0 else 0xCA32)
        while i < cap.n and signed(cap.w(i, OTP)) == p:
            i += 1
        j = min(i, cap.n - 1)
        fast = any(abs(signed(cap.w(k, PUCKVX))) + abs(signed(cap.w(k, PUCKVY))) > 15000 for k in range(j, min(cap.n, j + 6)))
        shots = cap.w(min(cap.n - 1, j + 90), 0xC6CE if team == 0 else 0xCA32) > shots0
        caught = any(signed(cap.w(k, PUCKC)) == p for k in range(j, min(cap.n, j + 4)))
        res.append("shot" if fast or shots else "caught by him" if caught else "neither")
    return res


def main():
    names = sys.argv[1:] or sorted(p.stem for p in (HOME / "matches").glob("*.js") if p.name != "season.js"
                                   and (HOME / "captures" / p.stem / "fast.bin.gz").exists())
    tot = stuck = 0
    allp, allends = [], []
    for n in names:
        try:
            r = study(n)
        except (KeyError, FileNotFoundError, ValueError) as err:
            print("skip", n, err)
            continue
        if r is None:
            continue
        r, presses, how = r
        allp.extend(presses)
        allends.extend(how)
        tot += len(r)
        bad = [s for s in r if s["stuck_ms"] > 1000]
        stuck += len(bad)
        print(f"{n}: {len(r)} one-timer stretches, {len(bad)} stuck over 1 s (real)")
        for s in bad:
            print("   ", s)
    print(f"all: {tot} stretches, {stuck} stuck")
    from collections import Counter
    print("new C presses by a pad during a teammate's pass:", dict(Counter(p["why"] for p in allp).most_common()))
    print("how the one-timers that started ended:", dict(Counter(allends).most_common()))


if __name__ == "__main__":
    main()
