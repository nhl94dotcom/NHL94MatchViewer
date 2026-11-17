"""NHL '95 (Genesis): NOSE4Web's rules settings, played (2026-11-17; NHL_95_rules.bin / W18_rules.bin against the
originals; settings_all too): fighting penalty time 2:00 (hook $89448: the box time for $26 / $28 only), the real-time
clock ($7A384, $89568, $7A3CC), penalty time 30 s a minute (the word at $8942C: minutes x $1E where retail has x $3C),
and the rest below.

  box ROM STATE OUT [FRAMES]   a computer game from the live state (penalties on, Fighting On, the check tension held
        at 40 or more so fights come): each player put in the box (his box word, team struct +$68 by roster place, set
        with $2000: the low 11 bits are its seconds) with the penalty's code (PenBuf, or a fight's), every later change
        of his word's flags, and the frames each clock second takes while the clock runs. FGT=N in the environment
        holds every skater's fighting byte at N (W18's are 0: no fights otherwise).
  otlen ROM STATE              the overtime clock as it starts, by Optperlen 0-3 (the 4th: 30 Seconds) and kind of
        game (regular, season, season playoffs, playoffs): hook $7D4AE
  injury ROM STATE OUT [N]     a scratch copy (the original untouched) where every knockdown of the carrier is an
        injury (the animation, facing and random tests of the roll at $7B45A / $7B466 / $7B480 made NOPs); pad 2 hits
        pad 1's carrier: the word the injury leaves ($FFFD the period, $FFFC the game; injury95's NOPs $9F078 /
        $9F088), then the period run out: his word and whether he plays in the next period
  delayed ROM STATE HOLD [FRAMES]   checkagr's delayed-penalty block ($89A10): sflags9 bit 1 (a home penalty
        pending) / bit 2 (an away one) held set (HOLD 2, 4 or 6); the calls on each team. AGR=50 holds every skater's
        aggression (+$73) at 50 so checkagr calls every time
  bcheck ROM STATE OPTPEN      Bcheck's roll with penalties off ($7AF3C): pad 2's skater sweeps (B) at a skater
        without the puck as he skates in: whether the target falls
  so ROM STATE                 the shootout's injured-shooter skip (hook $9DD82): marks put in the saved box words
        (SO_MARKS) of list entries, the shootout kept level; each turn's shooter
  icing ROM STATE OUT [FRAMES] hybrid icing in a computer game (SEEDS=N games): each crossing, the race, the outcome
  icingset ROM STATE           hybrid icing, set plays: the shot sent on wide into the corner past the goal line, a
        teammate and a defender held at a grid of distances from the dot line (y +-$D7): call or wave-off

python gen95_rules_check.py MODE ..."""
import json
import os
import sys
from collections import Counter
from pathlib import Path

import gen95_organ_resume_check as O
import lowload

HOME, TMSIZE = 0xC288, 0x366
GSP, CLOCK, GMODE, PENBUF, OPTPEN, SETTING, CHKCNT = 0xC020, 0xC022, 0xBEF0, 0xBFCE, 0xCC5A, 0xCC63, 0xC028
BASE, SZ = 0xAC62, 0x80
PDST = 0x68
AGR = int(os.environ["AGR"]) if os.environ.get("AGR") else None   # every skater's aggression (+$73) held at this
FGT = int(os.environ["FGT"]) if os.environ.get("FGT") else None   # every skater's fighting byte (+$74) held at this


def sw(v):
    return v - 0x10000 if v >= 0x8000 else v


def rec(k):
    return BASE + k * SZ


def box_words(e):
    return [[e.w(HOME + tm * TMSIZE + PDST + 2 * i) for i in range(26)] for tm in (0, 1)]


def box(rom, state, frames):
    import gen95_shootout_check as SC
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    e.setw(OPTPEN, 1)
    e.setb(SETTING, 1)
    prev = box_words(e)
    codes = {}                        # (team, place) -> the last penalty code seen for him in PenBuf
    entries, ticks, last_clock, run_frames = [], Counter(), e.w(CLOCK), 0
    hist = {}                         # (team/place) -> each change of his word's flag bits (or to 0)
    for f in range(frames):
        if f % 60 == 0:
            SC.computer(e)
            e.setw(CHKCNT, max(e.w(CHKCNT), 40))
            if FGT is not None:                     # W18's rosters fight 0: no fight can start without it
                for k in range(12):
                    if k not in (5, 11):
                        e.setb(rec(k) + 0x74, FGT)
        e.run(1)
        for i in range(8):
            v = e.w(PENBUF + 2 * i)
            if not v:
                break
            code, k = v >> 8, v & 0x7F
            if code >= 0x12 and k < 12:
                tm = 0 if k < 6 else 1
                codes[(tm, e.b(rec(k) + 0x66))] = code
        now = box_words(e)
        for tm in (0, 1):
            for i in range(26):
                w0, w1 = prev[tm][i], now[tm][i]
                if w1 != w0 and w1 < 0x8000 and w1 & 0x2000 and not (w0 < 0x8000 and w0 & 0x2000):
                    entries.append(dict(f=f, team=tm, place=i, word=f"{w1:04x}", seconds=w1 & 0x7FF,
                                        code=codes.get((tm, i)), gsp=e.w(GSP), clock=e.w(CLOCK)))
        for tm in (0, 1):
            for i in range(26):
                w0, w1 = prev[tm][i], now[tm][i]
                if w1 != w0 and ((w1 & 0xF800) != (w0 & 0xF800) or w1 == 0):
                    hist.setdefault(f"{tm}/{i}", []).append(f"{w1:04x}")
        prev = now
        running = not e.w(GMODE) & 0x100
        c = e.w(CLOCK)
        if running:
            run_frames += 1
        if c != last_clock:
            if running and c == last_clock - 1:
                ticks[run_frames] += 1
            run_frames = 0
            last_clock = c
        if f % 6000 == 5999:
            lowload.breathe()
    return dict(rom=Path(rom).name, entries=entries, frames_per_clock_second=dict(ticks), history=hist,
                final={f"{tm}/{i}": f"{w:04x}" for tm in (0, 1) for i, w in enumerate(now[tm]) if w})


MODE, GAMEFLAGS, SEASONF, PERLEN, HM, AW = 0xCC4C, 0xBF08, 0xD1A7, 0xCC54, 0xC294, 0xC5FA


def otlen(rom, state):
    """The overtime's clock as it starts, by period length (Optperlen 0-3) and kind of game: a tied third period with 3
    s left, played on (START through screens) until the overtime's clock runs."""
    from emu import Emu
    import gen95_shootout_check as SC
    out = []
    e = Emu(rom)
    e.run(1500)
    base = Path(state).read_bytes()
    kinds = {"regular game": (0, False, False), "season game": (0, True, False), "season playoffs": (0, True, True),
             "playoffs": (2, False, False)}
    for perlen in range(4):
        for kind, (mode, season, splay) in kinds.items():
            e.unserialize(base)
            e.setw(MODE, mode)
            e.setb(GAMEFLAGS, e.b(GAMEFLAGS) & ~8 | (8 if season else 0))
            e.setb(SEASONF, e.b(SEASONF) & ~0x20 | (0x20 if splay else 0))
            e.setw(PERLEN, perlen)
            e.setw(GSP, 2); e.setw(CLOCK, 3); e.setw(HM, 1); e.setw(AW, 1)
            got, last, still = None, None, 0
            for f in range(60 * 120):
                if f % 60 == 0:
                    SC.computer(e)
                c = e.w(CLOCK)
                e.run(1, hold=["START"] if still > 300 and f % 240 == 0 else [])
                still = still + 1 if e.w(CLOCK) == c else 0
                if e.w(GSP) == 3 and got is None and e.w(CLOCK) > 3:
                    got = e.w(CLOCK)
                if e.w(GSP) >= 4:
                    break
                if got is not None and f > 600:
                    break
            out.append(dict(perlen=perlen, kind=kind, ot_clock=got, gsp=e.w(GSP)))
            print(f"Optperlen {perlen}, {kind}: overtime clock {got}", flush=True)
        lowload.breathe()
    return out


def scratch_injury(rom, out):
    """A scratch copy where every fall-back knockdown of the puck carrier is an injury (the fall-back animation test at $7B45A, the facing test at $7B466 and
    the random roll's bgt at $7B480 made NOPs; the original ROM is not touched)."""
    b = bytearray(Path(rom).read_bytes())
    for a in (0x7B45A, 0x7B466, 0x7B480):
        assert b[a:a + 2] in (bytes.fromhex("6600"), bytes.fromhex("6e00")), hex(a)
        b[a:a + 4] = bytes.fromhex("4e714e71")
    p = Path(out) / f"scratch_injury_{Path(rom).stem}.bin"
    p.write_bytes(bytes(b))
    return p


def injury(rom, state, out, n=40):
    """Hits by pad 2 on pad 1's carrier (gen95_stats_check.stumble's approach) on the scratch copy, the carrier's
    fighting byte (+$74) set to 0, 4, 8 or 12 by trial (retail: /4 = 0 the period, 3 the game, else the game half the
    time), sflags13 bit 1 (a season injury already given) set on every fifth: the word the injury leaves
    ($FFFD the period, $FFFC the game), then the period's clock cut to 3 s and played on into the next period: his word
    then, and whether he is on the ice again."""
    import math
    import random
    import gen95_group1_fixes_check as G1
    import gen95_shootout_check as SC
    r = O.R(str(scratch_injury(rom, out)), state)
    e = r.e
    A, D = 2, 7
    res = []
    for trial in range(n):
        rnd = random.Random(trial)
        x0, y0 = rnd.uniform(-60, 60), rnd.uniform(-60, 60)
        ang = rnd.uniform(0, 2 * math.pi)
        dist, trig = rnd.uniform(70, 110), rnd.choice((22, 30, 38))
        p = G1.Play(e, r.base, {A: (round(x0), round(y0)), D: (round(x0 + dist * math.sin(ang)), round(y0 + dist * math.cos(ang)))},
                    rnd.getrandbits(32))
        fgt = (0, 4, 8, 12)[trial % 4]
        e.setb(rec(A) + 0x74, fgt)
        if trial % 5 == 4:
            e.setb(0xBF10, e.b(0xBF10) | 2)
        G1.control(e, 1, A, 1)
        if not p.give(A):
            continue
        G1.control(e, 2, D, 2)
        place = e.b(rec(A) + 0x66)
        wa = HOME + PDST + 2 * place
        c, word = None, None
        for f in range(240):
            ax, ay = G1.pos(e, A)
            kx, ky = G1.pos(e, D)
            if c is None and math.hypot(ax - kx, ay - ky) < trig:
                c = f
            p.frame(held2=(["C"] if c is not None and f < c + 3 else []) + G1.pad(G1.dir_to(ax - kx, ay - ky)), hold=[])
            if e.w(wa) in (0xFFFD, 0xFFFC):
                word = e.w(wa)
                break
        row = dict(trial=trial, fgt=fgt, season_flag=trial % 5 == 4, place=place, word=None if word is None else f"{word:04x}")
        if word is not None:
            gsp0 = e.w(GSP)
            e.setw(CLOCK, 3)
            still, after, on_ice = 0, None, None
            for f in range(60 * 150):
                if f % 60 == 0:
                    SC.computer(e)
                clk = e.w(CLOCK)
                e.run(1, hold=["START"] if still > 300 and f % 240 == 0 else [])
                still = still + 1 if e.w(CLOCK) == clk else 0
                if e.w(GSP) == gsp0 + 1 and not e.w(GMODE) & 0x100 and e.w(CLOCK) < clk:
                    after = e.w(wa)
                    on_ice = any(e.b(rec(k) + 0x66) == place and e.b(rec(k) + 0x35) != 0xFF for k in range(6))
                    break
                if e.w(GSP) >= 4:
                    break
            row.update(next_period_word=None if after is None else f"{after:04x}", on_ice_next_period=on_ice)
        res.append(row)
        print(json.dumps(row), flush=True)
        lowload.breathe()
    return res


def delayed(rom, state, hold, frames):
    """A computer game (penalties on) with sflags9 ($FFBF06) bit 1 (a home penalty pending) and / or bit 2 (an away
    one) held set every frame (HOLD 0, 2, 4 or 6): the calls on each team (team struct +6) with their codes. checkagr
    ($8996E) returns $7F (no call) for a home checker while bit 2 is set and an away checker while bit 1 is set."""
    import gen95_shootout_check as SC
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    e.setw(OPTPEN, 1)
    n0 = [e.w(HOME + 6), e.w(HOME + TMSIZE + 6)]
    seen, calls = set(), Counter()
    for f in range(frames):
        if f % 60 == 0:
            SC.computer(e)
            if AGR is not None:                     # every skater's aggression (+$73): 50 makes checkagr call each time
                for k in range(12):
                    if k not in (5, 11):
                        e.setb(rec(k) + 0x73, AGR)
        if hold:
            e.setb(0xBF06, e.b(0xBF06) | hold)
        e.run(1)
        for i in range(32):
            v = e.w(PENBUF + 2 * i)
            if not v:
                break
            if (i, v) not in seen:
                seen.add((i, v))
                calls[("home" if (v & 0x7F) < 6 else "away", v >> 8)] += 1
        if e.w(PENBUF) == 0:
            seen.clear()
        if f % 6000 == 5999:
            lowload.breathe()
    n1 = [e.w(HOME + 6), e.w(HOME + TMSIZE + 6)]
    return dict(rom=Path(rom).name, hold=hold, home_calls=n1[0] - n0[0], away_calls=n1[1] - n0[1],
                codes={f"{k[0]} {k[1]:02x}": v for k, v in calls.items()})


def bcheck(rom, state, optpen, n=40):
    """Bcheck ($7AF2A): pad 2's skater (away 7) sweeps with B at a home skater who hasn't the puck (home 1, 14-22
    straight up the ice from him, held there; the carrier, home 2, 60 further on), Penalties OPTPEN: whether the
    target fell. Retail with penalties off rolls randomd0($20 + the checker's Chk - the target's legstr) >= $18 first;
    the build's bra at $7AF3C skips the roll."""
    import gen95_group1_fixes_check as G1
    r = O.R(rom, state)
    e = r.e
    D, T, A = 7, 1, 2
    rows = []
    for trial in range(n):
        dx, gap = (-30, 0, 30)[trial % 3], (17, 18, 19, 18, 17)[trial % 5]       # gap: B pressed this far from him (18: the sweep lands)
        p = G1.Play(e, r.base, {D: (dx, -60), T: (dx, 0), A: (dx, 60)}, trial * 7919)
        e.setw(OPTPEN, optpen)
        G1.control(e, 1, None, 1)
        if not p.give(A):
            continue
        G1.control(e, 2, D, 2)
        fell, spas, pressed = False, set(), None
        for f in range(110):
            ty = sw(e.w(rec(T) + 0x14))
            dy = ty - sw(e.w(rec(D) + 0x14))
            if pressed is None and dy <= gap:
                pressed = f
            b = pressed is not None and f < pressed + 3
            p.frame(held2=["UP"] + (["B"] if b else []), hold=[T, A] if f < 70 else [A])
            spas.add(e.w(rec(D) + 0x58))
            fell = fell or bool(e.b(rec(T) + 0x64) & 0x20) or e.w(rec(T) + 0x58) in G1.SPA_FALLS
        rows.append(dict(trial=trial, gap=gap, fell=fell, checker_spas=sorted(spas)))
        if trial % 10 == 9:
            lowload.breathe()
    return rows


SO_MARKS = {0: {0: 0xFFFC, 1: 0xFFFD, 4: 0x1000}, 1: {2: 0x203C, 3: 0x103C}}   # team -> list entry -> saved word


def so(rom, state):
    """The shootout's injured-shooter skip (hook $9DD82): a regular game tied 1-1 with 3 s left, overtime cut to 3 s;
    once the shootout's saved team structs are in ($FFF000 mark set; the saved box words at $F06A + 2 x roster place,
    +$366 the visitors) and the lists built (homeshooters $D186 / awayshooters $D194), SO_MARKS go into the saved words
    of those list entries. The shootout kept level (goals $D180 / $D182 at 0) to round 8. Each turn: the shooter
    (BA_Skater_Offset $D00E) against the list entry the index ($D192) names and against the entry the build should take
    (stepped past $FFFC and positive words with $1000)."""
    from emu import Emu
    import gen95_shootout_check as SC
    e = Emu(rom)
    e.run(1500)
    e.unserialize(Path(state).read_bytes())
    e.setw(GSP, 2); e.setw(CLOCK, 90); e.setw(SC.HM, 0); e.setw(SC.AW, 0)
    SC.put_goal(e, True); SC.put_goal(e, False)
    e.setw(CLOCK, 3)
    lists, marked, key, rows, still = None, False, None, [], 0
    for f in range(60 * 60 * 25):
        if f % 60 == 0:
            SC.computer(e)
        clk = e.w(CLOCK)
        e.run(1, hold=["START"] if still > 300 and f % 240 == 0 else [])
        still = still + 1 if e.w(CLOCK) == clk else 0
        so_on = bool(e.w(0xBF00) & 0x0100)
        if e.w(GSP) == 3 and e.w(CLOCK) > 3 and not so_on and not marked:
            e.setw(CLOCK, 3)
        if so_on and not marked and e.b(0xF000) and e.w(0xD186) != e.w(0xD188):
            lists = [[e.w(a + 2 * i) for i in range(5)] for a in (0xD186, 0xD194)]
            for tm, m in SO_MARKS.items():
                for i, w in m.items():
                    e.setw(0xF06A + tm * TMSIZE + 2 * lists[tm][i], w)
            marked = True
            print("lists (roster places)", lists, "gsp", e.w(GSP), flush=True)
        if marked and so_on:
            e.setw(0xD180, 0); e.setw(0xD182, 0)
            k = (e.w(0xD184), e.w(0xD1A0))
            if k != key:
                if key is not None:                  # the turn just over: its shooter as he stood at the end
                    rows.append(dict(round=key[0], team_word=key[1], index_word=idx, shooter=shooter,
                                     entry_home=[i for i, v in enumerate(lists[0]) if v == shooter],
                                     entry_away=[i for i, v in enumerate(lists[1]) if v == shooter]))
                    print(json.dumps(rows[-1]), flush=True)
                key = k
            shooter, idx = e.w(0xD00E), e.w(0xD192)
            if e.w(0xD184) > 8:
                break
        if f % 6000 == 5999:
            lowload.breathe()
    return dict(lists=lists, rows=rows)


def icing(rom, state, frames, seed=0):
    """Hybrid icing (hook $89B32 at the goal-line crossing outside the crease's width): a computer game from the live
    state (penalties on); at each crossing (icing flags $FFBB86 bit 0 set; bit 1 the top end, bit 2 armed, $BB87 the
    icing skater's record): each team's nearest skater's distance to the line y +-$D7 by the build's rule (in y only,
    past it 0; position word +$34 <= 0 and pflags2 bit 2 skipped), and the outcome within 30 frames: called (icing,
    code $0C, in PenBuf) or waved off (bit 2 cleared); after a call the puck's y at the next drop (the clock running)."""
    import gen95_shootout_check as SC
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    e.setw(OPTPEN, 1)
    e.setl(0xCC6A, seed)
    rows, prev, pending = [], e.b(0xBB86), None
    for f in range(frames):
        if f % 60 == 0:
            SC.computer(e)
        e.run(1)
        fl = e.b(0xBB86)
        if fl & 1 and not prev & 1:
            line = 0xD7 if fl & 2 else -0xD7
            icer = e.b(0xBB87)
            team = 0 if icer < 6 else 1
            dist = []
            for t in (team, 1 - team):
                best = None
                for k in range(6 * t, 6 * t + 6):
                    if sw(e.w(rec(k) + 0x34)) <= 0 or e.b(rec(k) + 0x63) & 4:
                        continue
                    y = sw(e.w(rec(k) + 0x14))
                    d = max(0, (line - y) if line > 0 else (y - line))
                    best = d if best is None else min(best, d)
                dist.append(best)
            pending = dict(f=f, icer=icer, team=team, top=bool(fl & 2), armed_before=bool(prev & 4),
                           puck=(sw(e.w(0xB362)), sw(e.w(0xB376))), icing_team_nearest=dist[0], other_team_nearest=dist[1],
                           expected="call" if dist[1] is not None and (dist[0] is None or dist[1] <= dist[0]) else "wave off")
        if pending is not None and "outcome" not in pending:
            called = any(e.w(PENBUF + 2 * i) >> 8 == 0x0C for i in range(8))
            if called or not fl & 4 or f - pending["f"] > 30:
                pending["outcome"] = "call" if called else ("wave off" if not fl & 4 else "armed still")
                pending["after_frames"] = f - pending["f"]
                rows.append(pending)
                if not called:
                    print(json.dumps(pending), flush=True)
                    pending = None
        if pending is not None and pending.get("outcome") == "call" and "drop_y" not in pending:
            if not e.w(GMODE) & 0x100 and f - pending["f"] > 60:
                pending["drop_y"] = sw(e.w(0xB376))
                print(json.dumps(pending), flush=True)
                pending = None
        prev = fl
        if f % 6000 == 5999:
            lowload.breathe()
    return rows


def icing_set(rom, state):
    """Hybrid icing, set plays: a skater of the team attacking up the screen takes the puck in his own half (the touch
    arms icing: iflags bit 2), then the puck is sent loose up the ice to the right corner (past the goal line, y
    $10B, at x about 100: wide of the crease). A teammate and a defender stand held at x -60 at the distances below the
    dot line (y $D7) of the grid (0 = on it, negative = past it); everyone else parked. The outcome within 40 frames
    of the crossing: called (PenIcing $0C in PenBuf), waved off (bit 2 cleared), or still armed (retail: called at a
    defender's touch)."""
    import gen95_group1_fixes_check as G1
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    up_home = bool(e.b(rec(2) + 0x62) & 0x80)
    icer, mate, dfd = (2, 3, 7) if up_home else (7, 8, 2)
    rows = []
    grid = [(a, d) for a in (-20, 0, 15, 30, 60) for d in (-20, 0, 15, 30, 60)] + [(30, None), (None, 30)]
    for n, (da, dd) in enumerate(grid):
        spots = {icer: (40, -60)}
        if da is not None:
            spots[mate] = (-60, 0xD7 - da)
        if dd is not None:
            spots[dfd] = (-70, 0xD7 - dd)
        p = G1.Play(e, r.base, spots, n * 104729)
        e.setw(OPTPEN, 1)
        G1.control(e, 1, None, 1)
        G1.control(e, 2, None, 2)
        if not p.give(icer):
            continue
        G1.control(e, 1, icer, 1 if icer < 6 else 2)
        armed = bool(e.b(0xBB86) & 4)
        crossed, out, fl, sent = None, None, 0, False
        for f in range(220):
            p.frame(held=["C", "UP"] if f < 3 and icer < 6 else [], held2=["C", "UP"] if f < 3 and icer >= 6 else [],
                    hold=[k for k in spots if k != icer])
            if not sent and e.w(0xB3C2) >= 0x8000:       # the shot is away: sent on to the right corner instead
                x, y = sw(e.w(rec(14))), sw(e.w(rec(14) + 0x14))
                G1.put(e, 14, x, y, (100 - x) / ((0x10B + 10 - y) / 5.0), 5.0)
                sent = True
            fl = e.b(0xBB86)
            if crossed is None and fl & 1:
                crossed = f
            called = any(e.w(PENBUF + 2 * i) >> 8 == 0x0C for i in range(8))
            if called:
                out = "call"
                break
            if crossed is not None and not fl & 4:
                out = "wave off"
                break
            if crossed is not None and f > crossed + 40:
                out = "armed still"
                break
            if crossed is None and not fl & 4 and f > 5:
                out = "unarmed before the line"
                break
        exp = None
        if da is not None or dd is not None:
            A_ = max(0, da) if da is not None else None
            D_ = max(0, dd) if dd is not None else None
            exp = "call" if D_ is not None and (A_ is None or D_ <= A_) else "wave off"
        rows.append(dict(attacker=da, defender=dd, armed=armed, crossed=crossed, outcome=out, expected=exp,
                         puck=(sw(e.w(0xB362)), sw(e.w(0xB376)))))
        print(json.dumps(rows[-1]), flush=True)
        if n % 10 == 9:
            lowload.breathe()
    return rows


def main():
    mode = sys.argv[1]
    lowload.gentle()
    if mode == "icingset":
        rows = icing_set(sys.argv[2], sys.argv[3])
        print(Path(sys.argv[2]).name, dict(Counter((x["expected"], x["outcome"]) for x in rows)))
        return
    if mode == "icing":
        rom, state, out = sys.argv[2], sys.argv[3], Path(sys.argv[4])
        frames = int(sys.argv[5]) if len(sys.argv) > 5 else 60000
        out.mkdir(parents=True, exist_ok=True)
        rows = []
        for seed in range(int(os.environ.get("SEEDS", "1"))):
            rows += icing(rom, state, frames, seed * 0x9E3779B1 & 0xFFFFFFFF)
        (out / f"icing_{Path(rom).stem}.json").write_text(json.dumps(rows))
        print(Path(rom).name, "crossings", len(rows), dict(Counter((x["expected"], x["outcome"]) for x in rows)))
        return
    if mode == "so":
        so(sys.argv[2], sys.argv[3])
        return
    if mode == "bcheck":
        rom, state, optpen = sys.argv[2], sys.argv[3], int(sys.argv[4])
        rows = bcheck(rom, state, optpen)
        print(Path(rom).name, "penalties", optpen, "target fell", sum(x["fell"] for x in rows), "of", len(rows),
              "| by gap", dict(Counter((x["gap"], x["fell"]) for x in rows)), "| checker SPAs", Counter(s for x in rows for s in x["checker_spas"]).most_common(6))
        return
    if mode == "delayed":
        rom, state, hold = sys.argv[2], sys.argv[3], int(sys.argv[4])
        print(json.dumps(delayed(rom, state, hold, int(sys.argv[5]) if len(sys.argv) > 5 else 30000)), flush=True)
        return
    if mode == "injury":
        rom, state, out = sys.argv[2], sys.argv[3], Path(sys.argv[4])
        out.mkdir(parents=True, exist_ok=True)
        res = injury(rom, state, out, int(sys.argv[5]) if len(sys.argv) > 5 else 40)
        (out / f"injury_{Path(rom).stem}.json").write_text(json.dumps(res))
        print(dict(Counter((x["fgt"], x["season_flag"], x["word"], x.get("next_period_word"), x.get("on_ice_next_period")) for x in res)))
        return
    if mode == "otlen":
        rom, state = sys.argv[2], sys.argv[3]
        otlen(rom, state)
        return
    if mode == "box":
        rom, state, out = sys.argv[2], sys.argv[3], Path(sys.argv[4])
        frames = int(sys.argv[5]) if len(sys.argv) > 5 else 30000
        out.mkdir(parents=True, exist_ok=True)
        res = box(rom, state, frames)
        (out / f"box_{Path(rom).stem}.json").write_text(json.dumps(res))
        print(res["rom"], "frames a clock second (while running):", sorted(res["frames_per_clock_second"].items(), key=lambda kv: -kv[1])[:4])
        print("  box entries (code, seconds):", dict(Counter((x["code"], x["seconds"]) for x in res["entries"])))
        for x in res["entries"]:
            k = f"{x['team']}/{x['place']}"
            print(f"  {k} code {x['code']} entered {x['word']}: {' '.join(res['history'].get(k, []))} | at the end {res['final'].get(k)}")


if __name__ == "__main__":
    main()
