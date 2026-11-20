"""NHL '95 (Genesis): NOSE4Web's "B button while your skater is down" fix (2026-11-19, 55ec4f0: chgplayer's beq.w at
$AC0A, which let the pad's own skater be picked while locked, NOPped, so the lock test covers him too, as in NHL '94).
The original and the fix from the same live state (gen95_group1_fixes_check's: a Regular Game, pad 1 on home record
A = 2), each trial seeded the same on both ROMs; B pressed (2 frames) while pad 1's skater is locked (pfalock, bit 5
of +$62), then c1playernum ($FFBF44) 20 frames later: switched (another home skater, not the goalie), kept, or
something odd (an away record, out of range, or a record off the ice); then 120 more frames, c1playernum checked every
frame (odd if it ever leaves home records 0-5).
Cases (pad 1's skater A nearest the puck in each, as in the commissioner's report):
  burst   A bursts (C) at the computer's carrier; B 2-8 frames into SPAburst2
  check   A bursts (C) within 30 of the carrier, a check animation (SPA_CHECKS); B 0-4 frames into it
  down    A carries the puck, pad 2's skater bursts into him; B 4-30 frames after he is locked in a fall (after
          the check animation; falls show SPAfall $FAA and others such as $2454 / $B5C)
  none    as burst, every other home skater locked by hand before each frame while B is pressed (nobody can be
          chosen; the game can clear a hand-set lock within the frame, so an odd switch here is the harness)
  three   as burst, two of A's teammates off the ice (the position word at +$34 $FFFF), the third free
  threel  as three, the third locked too
python gen95_bswitch_check.py ps OUT ROM STATE [ROM STATE ...] [N]   (a real penalty shot, awarded as in
    gen95_group1_fixes_check pstable: the computer's shooter, pad 1 on whoever the game gives it, the home goalie;
    pad 1 presses C (a save move) once the puck is within 70 of him, and B as soon as he is locked without
    the puck, when nobody may be picked: only the shooter and
    the goalie are allowed (BA_PS_flags bit 2) and the first pass skips goalies; c1playernum followed 90 frames)
python gen95_bswitch_check.py OUT ROM STATE [ROM STATE ...] [N]
python gen95_bswitch_check.py ps OUT ROM STATE [ROM STATE ...] [N]   (a real penalty shot, awarded as in
    gen95_group1_fixes_check pstable: the computer's shooter, pad 1 on whoever the game gives it, the home goalie;
    pad 1 presses C (a save move) once the puck is within 70 of him, and B as soon as he is locked without
    the puck, when nobody may be picked: only the shooter and
    the goalie are allowed (BA_PS_flags bit 2) and the first pass skips goalies; c1playernum followed 90 frames)
python gen95_bswitch_check.py OUT ROM STATE [ROM STATE ...] [N]
python gen95_bswitch_check.py shootout OUT ROM [ROM ...]   (Shootout mode; see shootout(): use the editor-opened ROMs,
    whose boot skips the ROM check, so the menu presses land as gen95_shootout_mode_check expects)
"""
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

from emu import Emu
import gen95_group1_fixes_check as G
import lowload

C1P, LOCK = G.C1P, 0x20
A, MATE, MATE2, D = 2, 3, 1, 7
CASES = ("burst", "check", "down", "none", "three", "threel")
HOME_SKATERS = (0, 1, 2, 3, 4)            # record 5 is the home goalie in these states


def locked(e, k):
    return bool(e.b(G.rec(k) + G.PFL) & LOCK)


def valid(e):
    """Pad 1 on a home record that is on the ice (chgplayer's own test: the position word at +$34 not negative; the
    goalie allowed, as the pad takes him when he gets the puck)."""
    c = e.w(C1P)
    return c < 6 and not e.w(G.rec(c) + 0x34) & 0x8000


def press_b(e, p, f0, hold_extra=None, held=()):
    """B for 2 frames from now, then 20 frames; c1playernum before, after, and whether it stayed valid."""
    before = e.w(C1P)
    was_locked = locked(e, before)
    bad = 0
    for f in range(22):
        if hold_extra:
            hold_extra(f)
        p.frame(held=(["B"] if f < 2 else []) + list(held))
        bad += not valid(e)
    after = e.w(C1P)
    for _ in range(120):
        p.frame()
        bad += not valid(e)
    return dict(before=before, locked=was_locked, after=after, switched=after != before, odd_frames=bad,
                after_pos=e.b(G.rec(after) + G.POS) if after < 16 else None)


def burst_case(e, base, seed, case):
    rnd = random.Random(seed)
    cx, cy = rnd.uniform(-60, 60), rnd.uniform(-60, 60)
    gap = rnd.uniform(60, 90)
    ang = rnd.uniform(0, 2 * math.pi)
    spots = {D: (round(cx), round(cy)), A: (round(cx + gap * math.sin(ang)), round(cy + gap * math.cos(ang))),
             MATE: (round(cx + 120 * math.sin(ang + 2)), round(cy + 120 * math.cos(ang + 2)))}
    if case.startswith("three") or case == "none":
        spots[MATE2] = (round(cx - 100 * math.sin(ang)), round(cy - 100 * math.cos(ang)))
    p = G.Play(e, base, spots, seed)
    G.control(e, 2, None, 0)
    G.control(e, 1, A, 1)
    if not p.give(D):
        return dict(res="no pickup")
    if case.startswith("three"):
        for k in HOME_SKATERS:
            if k not in (A, MATE2):
                e.setw(G.rec(k) + 0x34, 0xFFFF)          # off the ice: chgplayer's tst.w / ble skips him
    when = rnd.randint(2, 8) if case != "check" else rnd.randint(0, 4)
    start = near = None
    for f in range(160):
        ax, ay = G.pos(e, A)
        dx, dy = G.pos(e, D)
        anim = e.w(G.rec(A) + 0x58)
        trig = (anim == G.SPA_BURST2) if case != "check" else (anim in G.SPA_CHECKS)
        if trig and start is None:
            start = f
        if start is not None and f - start >= when and locked(e, A):
            lockers = [k for k in HOME_SKATERS if k != A] if case in ("none", "threel") else []

            def lock(_f):
                for k in lockers:
                    e.setb(G.rec(k) + G.PFL, e.b(G.rec(k) + G.PFL) | LOCK)
            r = press_b(e, p, f, lock if lockers else None)
            r.update(res="ok", case=case, anim=anim)
            return r
        if near is None and (case != "check" or math.hypot(dx - ax, dy - ay) < 30):
            near = f
        p.frame(held=G.pad(G.dir_to(dx - ax, dy - ay)) + (["C"] if near is not None and f < near + 3 else []), hold=[D])
    return dict(res="never locked" if start is not None else "no burst / check", case=case)


def down_case(e, base, seed):
    rnd = random.Random(seed)
    x0, y0 = rnd.uniform(-60, 60), rnd.uniform(-60, 60)
    gap, trig = rnd.uniform(70, 100), rnd.choice((22, 30, 38))
    p = G.Play(e, base, {A: (round(x0), round(y0)), D: (round(x0 + gap), round(y0 + rnd.uniform(-10, 10))),
                         MATE: (round(x0 - 90), round(y0 + 90))}, seed)
    G.control(e, 1, A, 1)
    if not p.give(A):
        return dict(res="no pickup", case="down")
    G.control(e, 2, D, 2)
    c = fell = hit = None
    when = rnd.randint(4, 30)
    for f in range(400):
        ax, ay = G.pos(e, A)
        kx, ky = G.pos(e, D)
        if c is None and math.hypot(ax - kx, ay - ky) < trig:
            c = f
        if hit is None and e.w(G.rec(D) + 0x58) in G.SPA_CHECKS:
            hit = f
        if hit is not None and fell is None and locked(e, A) and e.w(G.rec(A) + 0x58) not in (0xB8E, G.SPA_BURST2):
            fell = f                                            # down: locked in his fall after the check
        if fell is not None and f - fell >= when:
            if not locked(e, A):
                return dict(res="up before B", case="down")
            r = press_b(e, p, f)
            r.update(res="ok", case="down", anim=e.w(G.rec(A) + 0x58))
            return r
        p.frame(held2=(["C"] if c is not None and f < c + 3 else []) + (G.pad(G.dir_to(ax - kx, ay - ky)) if fell is None else []),
                hold=[MATE] + ([A] if c is None else []))
        if c is None and f > 150:
            return dict(res="never close", case="down")
    return dict(res="no fall", case="down")


def live(out, pairs, n):
    for rom, state in pairs:
        e = Emu(rom)
        e.run(1500)
        base = Path(state).read_bytes()
        rows = []
        for i in range(n):
            for case in CASES:
                r = down_case(e, base, 9000 + i) if case == "down" else burst_case(e, base, 9000 + i, case)
                r["i"] = i
                rows.append(r)
            if i % 5 == 4:
                lowload.breathe()
        name = Path(rom).stem
        (out / f"live_{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        print(f"== {name}")
        for case in CASES:
            rs = [r for r in rows if r["case"] == case]
            ok = [r for r in rs if r["res"] == "ok"]
            print(f"  {case:7s} trials {len(rs)}, B pressed while locked {len(ok)}: switched {sum(r['switched'] for r in ok)},"
                  f" kept {sum(not r['switched'] for r in ok)}, odd frames {sum(r['odd_frames'] for r in ok)};"
                  f" not run {dict(Counter(r['res'] for r in rs if r['res'] != 'ok'))}")
        del e


def home_award(e, base, rnd):
    """gen95_group1_fixes_check's breakaway turned round: pad 1's home carrier (the home centre) across the blue line,
    the away chaser close behind, pressing C or B (pad 2) or the computer's, until a penalty shot is awarded to home."""
    for _ in range(80):
        e.unserialize(base)
        e.setw(G.CLOCK, 250)
        e.setl(G.SEED, rnd.getrandbits(32))
        e.setw(G.OPTPEN, 1)
        e.setw(G.PENBUF, 0)
        e.setw(G.BA_PS, 0)
        roles = {k: e.b(G.rec(k) + G.POS) for k in range(12)}
        carrier = next(k for k in range(6) if roles[k] == 4)
        up = 1 if e.b(G.rec(carrier) + G.PFL) & 0x80 else -1
        face = 0 if up > 0 else 4
        x0, y0 = rnd.uniform(-60, 60), up * rnd.uniform(55, 82)
        v = rnd.uniform(1.0, 2.0)
        G.put(e, carrier, x0, y0, 0, up * v, face)
        them = [k for k in range(6, 12) if roles[k] not in (0, 0xFF)]
        chaser = rnd.choice(them)
        G.put(e, chaser, x0 + rnd.uniform(-10, 10), y0 - up * rnd.uniform(8, 28), 0, up * (v + rnd.uniform(0.3, 1.2)), face)
        for k in them:
            if k != chaser:
                G.put(e, k, rnd.uniform(-90, 90), y0 - up * rnd.uniform(70, 160), 0, up * 1.0, face)
        for k in range(6):
            if roles[k] not in (0, 0xFF, 4):
                G.put(e, k, rnd.uniform(-90, 90), y0 - up * rnd.uniform(40, 140), 0, up * 1.0, face)
        for k in range(12):
            if roles[k] <= 5:
                G.fresh(e, k)
        mode = rnd.choice(("cpu", "C", "B"))
        G.control(e, 1, carrier, 1)
        G.control(e, 2, chaser if mode != "cpu" else None, 2 if mode != "cpu" else 0)
        G.put(e, 14, x0, y0 + up * 4)
        e.setw(G.PUCKC, carrier)
        before = G.penbuf(e)
        for f in range(150):
            cx, cy = G.pos(e, carrier)
            kx, ky = G.pos(e, chaser)
            h2 = [] if mode == "cpu" else G.pad(G.dir_to(cx - kx, cy - ky)) + ([mode] if f % 12 in (0, 1) else [])
            e.run(1, hold=["UP" if up > 0 else "DOWN"], hold2=h2)
            new = [v for v in G.penbuf(e) if v not in before]
            if new:
                if new[0] >> 8 >= 0x2E:
                    return carrier
                break
            if G.stopped(e):
                break
    return None


def ps_real(e, base, seed):
    """A penalty shot for pad 1's team: pad 1 on the shooter (as the game gives it) shoots (C toward the net), and B in
    his follow-through, locked and without the puck, when only he (and the goalie, never taken in the first pass) may be
    picked: nothing should change."""
    rnd = random.Random(seed)
    if home_award(e, base, rnd) is None:
        return dict(res="no award")
    if G.run_until(e, lambda: e.w(G.BA_PS) & G.UNDERWAY, 3000) is None:
        return dict(res="no attempt")
    shooter = e.w(G.BA_SKTR)
    for f in range(1500):                              # pad 1 skates to the puck at centre
        if e.w(G.PUCKC) == shooter:
            break
        sx, sy = G.pos(e, shooter)
        px, py = G.pos(e, 14)
        e.run(1, hold=G.pad(G.dir_to(px - sx, py - sy)) if e.w(C1P) == shooter else [])
    else:
        return dict(res="no carry", shooter=shooter, c1p=e.w(C1P))
    if e.w(C1P) != shooter:
        return dict(res="pad 1 not on the shooter", shooter=shooter, c1p=e.w(C1P))
    sx, sy = G.pos(e, shooter)
    gy = 264 if e.b(G.rec(shooter) + G.PFL) & 0x80 else -264
    toward = G.pad(G.dir_to(-sx, gy - sy))
    for f in range(160):
        e.run(1, hold=toward + (["C"] if 40 <= f < 44 else []))
        if e.w(G.PUCKC) != shooter and locked(e, shooter):
            break
    else:
        return dict(res="no shot", shooter=shooter)
    before, flags = e.w(C1P), e.b(G.BA_PS)
    odd = 0
    for f in range(92):
        e.run(1, hold=["B"] if f < 2 else [])
        c = e.w(C1P)
        odd += c >= 12 or bool(e.w(G.rec(c) + 0x34) & 0x8000)
    return dict(res="ok", shooter=shooter, before=before, after=e.w(C1P), ps_flag=bool(flags & 4), odd=odd,
                still_attempt=bool(e.w(G.BA_PS) & G.UNDERWAY))


def ps(out, pairs, n):
    for rom, state in pairs:
        e = Emu(rom)
        e.run(1500)
        base = Path(state).read_bytes()
        rows = []
        for i in range(n):
            rows.append(dict(i=i, **ps_real(e, base, 6000 + 31 * i)))
            lowload.breathe()
        name = Path(rom).stem
        (out / f"ps_{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        ok = [r for r in rows if r["res"] == "ok"]
        print(f"== {name} penalty shots: {len(ok)} presses in the shooter's follow-through (flag set {sum(r['ps_flag'] for r in ok)});"
              f" kept the shooter {sum(r['after'] == r['shooter'] for r in ok)}, other {sum(r['after'] != r['shooter'] for r in ok)};"
              f" odd frames {sum(r['odd'] for r in ok)}; not run {dict(Counter(r['res'] for r in rows if r['res'] != 'ok'))}")
        del e


def shootout(out, roms):
    """Shootout mode from Game Setup (gen95_shootout_mode_check's way in: play mode $C); in each home attempt the game
    gives pad 1 the shooter (BA_Sktr_SCnum): he skates to the puck, carries it toward the net, shoots (C), and B is
    pressed in his follow-through (locked, without the puck): nothing should change. Away attempts: pad 1 holds the
    home goalie, nothing pressed. Until the shootout ends (gmode2 bit 3) or 60 attempts' worth of frames."""
    import gen95_shootout_mode_check as S
    for rom in roms:
        e = Emu(rom)
        e.run(1500)
        for _ in range(3):
            e.run(6, hold=["START"]); e.run(200)
        e.setb(S.SETUP, 0xC); e.run(30)
        e.run(6, hold=["START"]); e.run(300)
        e.run(6, hold=["START"]); e.run(400)
        rows, f, key, done, shot_at, phase = [], 0, None, False, None, "skate"
        while f < 60 * 60 * 20 and e.b(S.GMODE2) & 1 and not e.b(S.GMODE2) & 8:
            k2 = (e.w(S.ROUND), e.w(S.TEAMW))
            if k2 != key:
                key, done, phase = k2, False, "skate"
            sh = e.w(G.BA_SKTR)
            hold = []
            live_ = e.w(G.BA_PS) & G.UNDERWAY
            if live_ and k2[1] == 0 and not done and sh < 6 and e.w(C1P) == sh:
                sx, sy = G.pos(e, sh)
                if phase == "skate":
                    px, py = G.pos(e, 14)
                    hold = G.pad(G.dir_to(px - sx, py - sy))
                    if e.w(G.PUCKC) == sh:
                        phase, shot_at = "carry", f + 50
                elif phase == "carry":
                    gy = 264 if e.b(G.rec(sh) + G.PFL) & 0x80 else -264
                    hold = G.pad(G.dir_to(-sx, gy - sy)) + (["C"] if shot_at <= f < shot_at + 4 else [])
                    if e.w(G.PUCKC) != sh and locked(e, sh):
                        before, flags = e.w(C1P), e.b(G.BA_PS)
                        odd = 0
                        for g in range(92):
                            e.run(1, hold=["B"] if g < 2 else [])
                            c = e.w(C1P)
                            odd += c >= 12 or bool(e.w(G.rec(c) + 0x34) & 0x8000)
                        f += 92
                        rows.append(dict(round=k2[0], shooter=sh, before=before, after=e.w(C1P), ps_flag=bool(flags & 4),
                                         odd=odd))
                        done = True
                        continue
                    if f > shot_at + 200:
                        done = True
            e.run(1, hold=hold or (["START"] if f % 300 == 10 and not live_ else []))
            f += 1
        name = Path(rom).stem
        (out / f"shootout_{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        ended = "the end (gmode2 bit 3)" if e.b(S.GMODE2) & 8 else "the frame limit" if f >= 60 * 60 * 20 else "the title"
        print(f"== {name} shootout: {len(rows)} home attempts with B in the shooter's follow-through (flag set "
              f"{sum(r['ps_flag'] for r in rows)}); kept the shooter {sum(r['after'] == r['shooter'] for r in rows)}, other "
              f"{sum(r['after'] != r['shooter'] for r in rows)}; odd frames {sum(r['odd'] for r in rows)}; ran to {ended}")
        del e


def main():
    if sys.argv[1] == "shootout":
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        lowload.gentle()
        shootout(out, sys.argv[3:])
        return
    if sys.argv[1] == "ps":
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        args = sys.argv[3:]
        n = int(args.pop()) if len(args) % 2 else 20
        lowload.gentle()
        ps(out, list(zip(args[::2], args[1::2])), n)
        return
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    args = sys.argv[2:]
    n = int(args.pop()) if len(args) % 2 else 20
    lowload.gentle()
    live(out, list(zip(args[::2], args[1::2])), n)


if __name__ == "__main__":
    main()
