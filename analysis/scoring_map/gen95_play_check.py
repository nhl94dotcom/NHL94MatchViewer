"""NHL '95 (Genesis): NOSE4Web's energy, skating and puck settings (2026-11-17; NHL_95_play.bin / W18_play.bin against
the originals; settings_all too), played. NHL '95 keeps a roster player's energy at team struct +$34 + 2 x roster
place (tmpde, full $1000) and his place word at +$68 (-1 on the ice, -2 on the bench); OptLine ($FFCC5C) 0 is line
changes On.

  energy ROM STATE OUT [FRAMES]   a computer game from the live state, line changes on, penalties on: every change of
        every roster player's energy, by where he was (ice / bench) and its size: the drain on the ice ($8C1C2: 33 a
        step on retail, 50 on the build), the bench's gain a second ($7DB62: 9 / 12), a burst ($AA96: 204 / 150), a
        knockdown (hook $7B14A: 1365) and a hold (hook $7B02C: 683).
  burst ROM STATE               pad 1's skater standing, UP held, C (burst) pressed, at energies 4096 / 2048 / 1024:
        his speed before and after the burst's push ($AAAC: energy / 128 after the cost on retail; a fixed 40) and
        the energy it took.
  stop ROM STATE                pad 1's skater at full speed up the ice, then DOWN held (a hockey stop, stopna:
        $8BB28-$8BB5E, 150 a frame on retail, 120): the frames and distance until his Y speed is 0.
  friction ROM STATE            the loose puck (record 14) put at 12 spots with speed (V + 37 k, 0), its share of
        speed lost a frame over 30 frames (clean runs only: untouched, on the ice, off the boards), at shares of the
        period gone (gameclock $C022 against PerTimeTotal $C026): the friction shift ($8BBC8: 7 retail, 5) and choppy
        ice (hook $8BBCA: L/16 more, L the quarters gone, 0-4, the puck only).

python gen95_play_check.py MODE ROM STATE [OUT] [FRAMES]"""
import json
import sys
from collections import Counter
from pathlib import Path

import gen95_organ_resume_check as O
import lowload

HOME, TMSIZE, BASE, SZ = 0xC288, 0x366, 0xAC62, 0x80
GSP, CLOCK, PERTOT, GMODE, OPTPEN, OPTLINE, PUCKC = 0xC020, 0xC022, 0xC026, 0xBEF0, 0xCC5A, 0xCC5C, 0xB3C2


def rec(k):
    return BASE + k * SZ


def sw(v):
    return v - 0x10000 if v >= 0x8000 else v


def energy_words(e):
    return [[e.w(HOME + t * TMSIZE + 0x34 + 2 * i) for i in range(26)] for t in (0, 1)]


def place_words(e):
    return [[e.w(HOME + t * TMSIZE + 0x68 + 2 * i) for i in range(26)] for t in (0, 1)]


def energy(rom, state, frames):
    import gen95_shootout_check as SC
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    e.setw(OPTPEN, 1)
    e.setw(OPTLINE, 0)
    prev, deltas = energy_words(e), Counter()
    for f in range(frames):
        if f % 60 == 0:
            SC.computer(e)
        e.run(1)
        now, pl = energy_words(e), place_words(e)
        for t in (0, 1):
            for i in range(26):
                d = now[t][i] - prev[t][i]
                if d:
                    where = "ice" if pl[t][i] == 0xFFFF else ("bench" if pl[t][i] == 0xFFFE else "other")
                    deltas[(where, d)] += 1
        prev = now
        if f % 6000 == 5999:
            lowload.breathe()
    return deltas


def pad_skater(e, base, seed, spots):
    import gen95_group1_fixes_check as G1
    p = G1.Play(e, base, spots, seed)
    G1.control(e, 1, 2, 1)
    G1.control(e, 2, None, 2)
    return p


def burst(rom, state):
    r = O.R(rom, state)
    e = r.e
    out = []
    place_of = lambda: e.b(rec(2) + 0x66)          # noqa: E731
    for en in (4096, 2048, 1024):
        for trial in range(4):
            p = pad_skater(e, r.base, trial * 31337, {2: (0, -150)})
            ea = HOME + 0x34 + 2 * place_of()
            sp = []
            for f in range(60):
                e.setw(ea, en) if f < 30 else None
                if f == 30:
                    e0 = e.w(ea)
                p.frame(held=["UP"] + (["C"] if 30 <= f < 33 else []), hold=[])
                sp.append(sw(e.w(rec(2) + 0x2A)))
            jumps = [sp[i] - sp[i - 1] for i in range(30, 45)]
            out.append(dict(energy=en, before=sp[29], peak_jump=max(jumps), after=max(sp[30:45]),
                            cost=e0 - e.w(ea), spa_after=hex(e.w(rec(2) + 0x58))))
            print(json.dumps(out[-1]), flush=True)
    return out


def stop(rom, state):
    r = O.R(rom, state)
    e = r.e
    out = []
    for trial in range(16):
        p = pad_skater(e, r.base, trial * 7121, {2: (0, -200)})
        for f in range(90):
            p.frame(held=["UP"], hold=[])
        v0, y0, n = sw(e.w(rec(2) + 0x2A)), sw(e.w(rec(2) + 0x14)), None
        for f in range(120):
            p.frame(held=["DOWN"], hold=[])
            if sw(e.w(rec(2) + 0x2A)) <= 0:
                n = f + 1
                break
        out.append(dict(speed=v0, frames=n, distance=sw(e.w(rec(2) + 0x14)) - y0, spa=hex(e.w(rec(2) + 0x58))))
        print(json.dumps(out[-1]), flush=True)
    return out


CASES = [(0, 0.02), (0, 0.30), (0, 0.55), (0, 0.80), (0, 0.95), (1, 0.02), (3, 0.02)]


def friction(rom, state):
    import gen95_group1_fixes_check as G1
    r = O.R(rom, state)
    e = r.e
    res = {}
    for gsp, share in CASES:
        rates, flags = [], Counter()
        for k in range(12):
            p = G1.Play(e, r.base, {}, k * 999)
            e.setw(GSP, gsp)
            tot = e.w(PERTOT) or 300
            e.setw(CLOCK, max(1, round(tot * (1 - share))))
            x0, y0 = (-60 + 10 * k), (-100 + 17 * k)
            v0 = 3000 + 37 * k
            G1.put(e, 14, x0, y0, v0 / 4096, 0)
            e.setb(rec(14) + 0x60, 0xFF)
            e.setw(PUCKC, 0xFFFF)
            flags[e.b(rec(14) + 0x62) & 1] += 1
            vs, clean = [], True
            for f in range(31):
                p.frame(hold=[])
                vx, vy, z = sw(e.w(rec(14) + 0x28)), sw(e.w(rec(14) + 0x2A)), sw(e.w(rec(14) + 0x18))
                if vy or z or e.w(PUCKC) < 0x8000 or (vs and vx > vs[-1]):
                    clean = False
                    break
                vs.append(vx)
            if clean and len(vs) == 31 and vs[0] > 0:
                rates.append(1 - (vs[-1] / vs[0]) ** (1 / 30))
        res[f"gsp {gsp}, {share:.0%} gone"] = (len(rates), sum(rates) / len(rates) if rates else None)
        print(Path(rom).name, f"gsp {gsp}, {share:.0%} gone: clean runs {len(rates)}, speed lost a frame "
              f"{res[f'gsp {gsp}, {share:.0%} gone'][1]}", "puck pfdoff", dict(flags), flush=True)
        lowload.breathe()
    return res


GM1, GM2, C1P, C2P, PENBUF, GOALIE_AW = 0xCC5E, 0xCC60, 0xBF44, 0xBF46, 0xBFCE, 11


def goalie_rec(e, team):
    return next(k for k in range(6 * team, 6 * team + 6) if e.b(rec(k) + 0x35) == 0)


def gswitch(rom, state):
    """Manual goalies (goaliemode1 / 2 = 0): pad 1's skater (or pad 2's) without the puck holds B; the frames until
    his goalie is the one under the pad (pflags bit 3): the B-hold timer, $11 a press on retail ($A1E4 / $A1EA and the
    reloads at $83F07 ...), $0A on the build."""
    import gen95_group1_fixes_check as G1
    r = O.R(rom, state)
    e = r.e
    out = []
    for padn, me, them in ((1, 2, 7), (2, 7, 2)):
        for trial in range(4):
            p = G1.Play(e, r.base, {me: (0, 0), them: (0, -120 if padn == 2 else 120)}, trial * 4111)
            e.setw(GM1, 0); e.setw(GM2, 0)
            G1.control(e, 1, None, 1); G1.control(e, 2, None, 2)
            if not p.give(them):
                continue
            G1.control(e, padn, me, 1 if me < 6 else 2)
            g = goalie_rec(e, 0 if me < 6 else 1)
            n = None
            for f in range(80):
                held = ["B"] if f >= 5 else []
                p.frame(held=held if padn == 1 else [], held2=held if padn == 2 else [], hold=[me, them])
                if e.b(rec(g) + 0x62) & 8:
                    n = f - 5 + 1
                    break
            out.append(dict(pad=padn, frames_held=n))
            print(json.dumps(out[-1]), flush=True)
    return out


def ghold(rom, state, n=16):
    """The away goalie on pad 2 (manual, nothing pressed); pad 1's skater shoots from the slot: when the goalie has the
    puck (puckc), the frames until the clock stops (temp5: $8C on retail, $12C on the build ($7BB46)) and the stop's
    code in PenBuf."""
    import gen95_group1_fixes_check as G1
    r = O.R(rom, state)
    e = r.e
    out = []
    for trial in range(n):
        p = G1.Play(e, r.base, {2: ((-30, 0, 30)[trial % 3], 150), GOALIE_AW: (0, 250)}, trial * 2713)
        e.setw(GM2, 0)
        G1.control(e, 1, 2, 1)
        g = goalie_rec(e, 1)
        G1.control(e, 2, g, 2)
        if trial % 2:                                    # half: the puck laid at his stick (no shot)
            ok = p.give(g)
        else:
            ok = p.give(2)
        if not ok:
            continue
        got, stop = (0 if trial % 2 else None), None
        for f in range(600):
            p.frame(held=["C"] if f < 3 and not trial % 2 else [], hold=[])
            if got is None and e.w(PUCKC) == g:
                got = f
            if got is not None and e.w(GMODE) & 0x100:
                stop = f - got
                break
            if got is not None and e.w(PUCKC) != g:
                break
        out.append(dict(trial=trial, held_by_goalie=got is not None, frames_to_whistle=stop,
                        code=hex(e.w(PENBUF) >> 8) if stop is not None else None))
        print(json.dumps(out[-1]), flush=True)
    return out


def grange(rom, state):
    """The away goalie on pad 2 (manual) holding a direction for 240 frames (the puck held by a home skater far up the
    ice): the farthest he gets (x, y) and any whistle (PenBuf code 8: the goalie out of range, at |y| < $AA retail /
    $96 build ($8301E / $83026)); his box: x +-$24 (+-$1E build), y +-$E7 (+-$C8)."""
    import gen95_group1_fixes_check as G1
    r = O.R(rom, state)
    e = r.e
    out = []
    for dirs in (["DOWN"], ["LEFT"], ["RIGHT"], ["DOWN", "LEFT"], ["DOWN", "RIGHT"]):
        p = G1.Play(e, r.base, {2: (0, -200)}, 1)
        e.setw(GM2, 0)
        G1.control(e, 1, None, 1)
        g = goalie_rec(e, 1)
        G1.control(e, 2, g, 2)
        if not p.give(2):
            continue
        xs, ys, wh = [], [], None
        for f in range(240):
            p.frame(held2=dirs, hold=[2])
            xs.append(sw(e.w(rec(g)))); ys.append(sw(e.w(rec(g) + 0x14)))
            if wh is None and e.w(GMODE) & 0x100:
                wh = (f, hex(e.w(PENBUF) >> 8), xs[-1], ys[-1])
                break
        out.append(dict(dirs=dirs, x=(min(xs), max(xs)), y=(min(ys), max(ys)), whistle=wh))
        print(json.dumps(out[-1]), flush=True)
    return out


GCASES = [  # x, y, x speed, y speed (px a frame) for the top net's goalie, pad 2 holding the same way
    (33, 250, 2.0, 0), (-33, 250, -2.0, 0), (40, 250, 2.0, 0), (0, 215, 0, -2.0), (0, 235, 0, -2.0),
    (0, 160, 0, 0), (0, 140, 0, 0), (0, 180, 0, 0)]


def grange2(rom, state):
    """The away (top) goalie on pad 2 (manual), put at a spot moving outward with the pad held that way: whether his
    speed is stopped (BA_PS_flags bit 1, the box x +-$24 / y $E7 on retail, +-$1E / $C8 on the build) and whether a
    whistle comes within 60 frames (PenBuf code 8: out of range inside |y| $AA retail / $96 build)."""
    import gen95_group1_fixes_check as G1
    r = O.R(rom, state)
    e = r.e
    out = []
    for x, y, vx, vy in GCASES:
        p = G1.Play(e, r.base, {2: (0, -200)}, 1)
        e.setw(GM2, 0)
        G1.control(e, 1, None, 1)
        g = goalie_rec(e, 1)
        G1.control(e, 2, g, 2)
        if not p.give(2):
            continue
        dirs = (["RIGHT"] if vx > 0 else ["LEFT"] if vx < 0 else []) + (["DOWN"] if vy < 0 else [])
        G1.put(e, g, x, y, vx, vy)
        v1, flag, wh = None, False, None
        for f in range(60):
            p.frame(held2=dirs, hold=[2])
            if f == 0:
                v1 = (sw(e.w(rec(g) + 0x28)), sw(e.w(rec(g) + 0x2A)))
            flag = flag or bool(e.b(0xBEF8) & 2)
            if wh is None and e.w(GMODE) & 0x100:
                wh = (f, hex(e.w(PENBUF) >> 8))
        out.append(dict(at=(x, y), speed=(round(vx * 4096), round(vy * 4096)), speed_after_1=v1, box_flag=flag,
                        whistle=wh, now=(sw(e.w(rec(g))), sw(e.w(rec(g) + 0x14)))))
        print(json.dumps(out[-1]), flush=True)
    return out


COUNTS = 0xF700           # the build's knockdown counts: a byte a roster place, the away team +$20
FALLS = (0xFAA, 0x109C, 0x2454)


def injrate(rom, state, frames, seed):
    """A computer game from the live state (line changes on, penalties on, the seed set): knockdowns (a skater
    entering a fall animation, SPA $FAA / $109C / $2454) and injuries (a roster place word turning $FFFD / $FFFC)."""
    import gen95_shootout_check as SC
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    e.setw(OPTPEN, 1)
    e.setw(OPTLINE, 0)
    e.setl(0xCC6A, seed)
    prev_spa = [e.w(rec(k) + 0x58) for k in range(12)]
    prev_pl = place_words(e)
    falls, inj = 0, []
    for f in range(frames):
        if f % 60 == 0:
            SC.computer(e)
        e.run(1)
        spa = [e.w(rec(k) + 0x58) for k in range(12)]
        falls += sum(1 for k in range(12) if spa[k] in FALLS and prev_spa[k] not in FALLS)
        prev_spa = spa
        pl = place_words(e)
        for t in (0, 1):
            for i in range(26):
                if pl[t][i] in (0xFFFD, 0xFFFC) and prev_pl[t][i] != pl[t][i]:
                    inj.append(dict(f=f, team=t, place=i, word=f"{pl[t][i]:04x}", count=e.b(COUNTS + 32 * t + i)))
        prev_pl = pl
        if f % 6000 == 5999:
            lowload.breathe()
    return dict(rom=Path(rom).name, seed=seed, frames=frames, knockdowns=falls, injuries=inj,
                counts_home=[e.b(COUNTS + i) for i in range(26)], counts_away=[e.b(COUNTS + 32 + i) for i in range(26)])


def scratch_roll(rom, out):
    """A scratch copy where every knockdown of the carrier reaches the injury roll (the fall-back animation and facing
    tests at $7B45A / $7B466 made NOPs; the roll itself, retail's or the build's hook at $7B47C, kept)."""
    b = bytearray(Path(rom).read_bytes())
    for a in (0x7B45A, 0x7B466):
        assert b[a:a + 2] == bytes.fromhex("6600"), hex(a)
        b[a:a + 4] = bytes.fromhex("4e714e71")
    q = Path(out) / f"scratch_roll_{Path(rom).stem}.bin"
    q.write_bytes(bytes(b))
    return q


def injroll(rom, state, out, count, n=60):
    """Pad 2 hits pad 1's carrier (gen95_stats_check.stumble's approach) on the scratch copy, the carrier's knockdown
    count held at COUNT: knockdowns, injuries, and the count after the hit (the build adds one a knockdown)."""
    import math
    import random
    import gen95_group1_fixes_check as G1
    r = O.R(str(scratch_roll(rom, out)), state)
    e = r.e
    A, D = 2, 7
    rows = []
    for trial in range(n):
        rnd = random.Random(trial)
        x0, y0 = rnd.uniform(-60, 60), rnd.uniform(-60, 60)
        ang = rnd.uniform(0, 2 * math.pi)
        dist, trig = rnd.uniform(70, 110), rnd.choice((22, 30, 38))
        p = G1.Play(e, r.base, {A: (round(x0), round(y0)), D: (round(x0 + dist * math.sin(ang)), round(y0 + dist * math.cos(ang)))},
                    rnd.getrandbits(32))
        G1.control(e, 1, A, 1)
        if not p.give(A):
            continue
        G1.control(e, 2, D, 2)
        place = e.b(rec(A) + 0x66)
        wa = HOME + 0x68 + 2 * place
        c, fell, injured, hit, imp = None, False, None, False, None
        for f in range(240):
            if not fell:
                e.setb(COUNTS + place, count)
            ax, ay = G1.pos(e, A)
            kx, ky = G1.pos(e, D)
            if c is None and math.hypot(ax - kx, ay - ky) < trig:
                c = f
            p.frame(held2=(["C"] if c is not None and f < c + 3 else []) + G1.pad(G1.dir_to(ax - kx, ay - ky)), hold=[])
            if not fell and e.w(rec(A) + 0x58) in FALLS:
                fell, imp = True, sw(e.w(rec(A) + 0x32))
            if e.w(wa) in (0xFFFD, 0xFFFC):
                injured = f"{e.w(wa):04x}"
                break
            if fell and f > (c or 0) + 60:
                break
        rows.append(dict(trial=trial, fell=fell, injured=injured, count_after=e.b(COUNTS + place), impact=imp))
        if trial % 10 == 9:
            lowload.breathe()
    return rows


def injcounts(rom):
    """The build from power-on: junk at the counts at Game Setup, START into a Regular Game: the counts at the first
    frame of play (cleared at the game's start, hook $9C34); then 7 and 10 set for a home and an away place, the clock
    at 1 s and play run into the next period: the counts there (halved at the period's end, hook $8CB64)."""
    from emu import Emu
    import gen95_fight_check as F
    e = Emu(rom)
    F.to_setup(e)
    for _ in range(12):
        if e.b(0xD283):
            break
        e.run(6, hold=["START"]); e.run(200)
    for i in range(64):
        e.setb(COUNTS + i, 0x5A)
    e.run(6, hold=["START"]); e.run(300)
    e.run(6, hold=["START"]); e.run(60)
    first, last = None, None
    for f in range(60 * 120):
        e.run(1, hold=["START"] if f % 240 == 0 else [])
        c = e.w(CLOCK)
        if e.w(GSP) == 0 and last is not None and 0 < c < last:
            first = [e.b(COUNTS + i) for i in range(64)]
            break
        last = c
    e.setb(COUNTS + 3, 7); e.setb(COUNTS + 32 + 5, 10)
    e.setw(CLOCK, 1)
    gsp0, after, last = e.w(GSP), None, None
    for f in range(60 * 120):
        e.run(1, hold=["START"] if f % 240 == 0 else [])
        c = e.w(CLOCK)
        if e.w(GSP) == gsp0 + 1 and last is not None and 0 < c < last:
            after = (e.b(COUNTS + 3), e.b(COUNTS + 32 + 5))
            break
        last = c
    return dict(first_frame_nonzero=[i for i, v in enumerate(first or []) if v], first_frame_sample=(first or [])[:8],
                next_period=after)


def main():
    mode, rom, state = sys.argv[1], sys.argv[2], sys.argv[3]
    lowload.gentle()
    if mode == "energy":
        out = Path(sys.argv[4])
        out.mkdir(parents=True, exist_ok=True)
        d = energy(rom, state, int(sys.argv[5]) if len(sys.argv) > 5 else 30000)
        (out / f"energy_{Path(rom).stem}.json").write_text(json.dumps({f"{k[0]} {k[1]}": v for k, v in d.items()}))
        for where in ("ice", "bench", "other"):
            print(Path(rom).name, where, sorted(((k[1], v) for k, v in d.items() if k[0] == where), key=lambda kv: -kv[1])[:12])
    elif mode == "burst":
        burst(rom, state)
    elif mode == "stop":
        stop(rom, state)
    elif mode == "injrate":
        out = Path(sys.argv[4])
        out.mkdir(parents=True, exist_ok=True)
        frames, seeds = int(sys.argv[5]), int(sys.argv[6]) if len(sys.argv) > 6 else 1
        res = [injrate(rom, state, frames, s_ * 0x9E3779B1 & 0xFFFFFFFF) for s_ in range(seeds)]
        (out / f"injrate_{Path(rom).stem}.json").write_text(json.dumps(res))
        for x in res:
            print(x["rom"], "seed", x["seed"], "knockdowns", x["knockdowns"], "injuries", x["injuries"],
                  "count sum", sum(x["counts_home"]) + sum(x["counts_away"]), flush=True)
    elif mode == "injroll":
        out, count = Path(sys.argv[4]), int(sys.argv[5])
        out.mkdir(parents=True, exist_ok=True)
        rows = injroll(rom, state, out, count, int(sys.argv[6]) if len(sys.argv) > 6 else 60)
        (out / f"injroll_{Path(rom).stem}_{count}.json").write_text(json.dumps(rows))
        bonus = lambda c: (min(5 * c, 25) * 5 + 1) >> 1          # noqa: E731 the build's: count after the hook's +1
        build = "play" in Path(rom).stem or "settings_all" in Path(rom).stem
        exp = sum(min(1, max(0, (x["impact"] + (bonus(count + 1) if build else 0) + 1) / 400)) for x in rows if x["fell"] and x["impact"] is not None)
        print("expected injuries from the impacts at the falls", round(exp, 1))
        print(Path(rom).name, "count", count, "knockdowns", sum(x["fell"] for x in rows), "injuries",
              sum(1 for x in rows if x["injured"]), Counter(x["injured"] for x in rows if x["injured"]),
              "counts after", Counter(x["count_after"] for x in rows if x["fell"]))
    elif mode == "injcounts":
        print(injcounts(rom))
    elif mode == "gswitch":
        gswitch(rom, state)
    elif mode == "ghold":
        ghold(rom, state)
    elif mode == "grange2":
        grange2(rom, state)
    elif mode == "grange":
        grange(rom, state)
    elif mode == "friction":
        friction(rom, state)


if __name__ == "__main__":
    main()
