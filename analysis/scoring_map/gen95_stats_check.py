"""NHL '95 (Genesis): NOSE4Web's statistics settings, played (2026-11-17; NHL_95_stats.bin / W18_stats.bin against the
originals): bodychecks shown (a count at the team struct's +$104 a roster place, while the clock runs: hook $7B164;
penalty minutes no longer added to the player at $8941E), the three stars (CalcTeamStarScores $95C8A rewritten: NHL 94's
fuller formula with the game's own checks at +$11E), time on ice (+$138 words) on the Player Stats page.

  game ROM STATE OUT [PERIOD_SECONDS]   a computer game from the live state (nobody on a pad, penalties on), each
        period's clock set to PERIOD_SECONDS: every change of a player's +$104 and +$11E (team, place, clock running),
        each penalty (PenBuf) and the team penalty minutes (+$8); when the stars are worked out (gmstars, gmode's low
        byte bit 7) the 52 longs at ThreeStars ($FFCAF8) against the formula from the team structs, and the three
        chosen. Results in OUT/game_<rom>.json.

python gen95_stats_check.py game ROM STATE OUT [PERIOD_SECONDS]"""
import json
import sys
from collections import Counter
from pathlib import Path

import gen95_organ_resume_check as O
import lowload

HOME, TMSIZE = 0xC288, 0x366
GSP, CLOCK, GMODE, GMODE2, OPTPEN, PENBUF = 0xC020, 0xC022, 0xBEF0, 0xBF00, 0xCC5A, 0xBFCE
STARS = 0xCAF8
BASE, SZ = 0xAC62, 0x80
SHOWN, CHECKS, GOALS, ASSISTS, SHOTS, TOI = 0x104, 0x11E, 0xB6, 0xD0, 0xEA, 0x138


def rec(k):
    return BASE + k * SZ


def arr(e, team, off, n=26):
    t = HOME + team * TMSIZE
    return [e.b(t + off + i) for i in range(n)]


def words(e, team, off, n=26):
    t = HOME + team * TMSIZE
    return [e.w(t + off + 2 * i) for i in range(n)]


def s32(v):
    return v - (1 << 32) if v >= 1 << 31 else v


def expected_scores(e, team, d5, goalies):
    """The build's formula (NOSE4Web's linesOff values) for one team's 26 slots."""
    t = HOME + team * TMSIZE
    o = HOME + (1 - team) * TMSIZE
    d3 = e.w(t + 0xC) - e.w(o + 0xC)
    g, a, s, c, toi = arr(e, team, GOALS), arr(e, team, ASSISTS), arr(e, team, SHOTS), arr(e, team, CHECKS), words(e, team, TOI)
    out = []
    for i in range(26):
        v = d3
        if i >= goalies:
            v += a[i] * 7000 + s[i] * 500 + g[i] * 11000 + c[i] * 500
        elif toi[i] >= d5 and s[i]:
            v += (a[i] * 7000) >> 1
            if g[i] == 0:
                v += 16000
            v += g[i] * -11000
            v += ((s[i] - 1) if d3 < 0 else s[i]) * 4000
        out.append(v)
    return out


GIVE, TAKE = 0xEA10, 0xEA50                      # giveaways / takeaways: a byte a roster place, 32 a team, home first
TOTALS = (0xEB00, 0xEE66)                        # the teams' giveaways (and takeaways at +2): team struct + $2878
PUCKC = 0xB3C2


def gt(e):
    return [e.b(GIVE + i) for i in range(64)], [e.b(TAKE + i) for i in range(64)]


def game(rom, state, secs):
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    e.setw(0xBF4C, 0)
    e.setw(0xBF4E, 0)
    for k in range(12):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setw(OPTPEN, 1)
    e.setw(CLOCK, min(e.w(CLOCK), secs))
    prev = {(tm, off): arr(e, tm, off) for tm in (0, 1) for off in (SHOWN, CHECKS)}
    pim = [e.w(HOME + tm * TMSIZE + 8) for tm in (0, 1)]
    log, pens, stars = [], [], None
    last_gsp, last_pb = e.w(GSP), 0
    still = 0
    g0, t0 = gt(e)
    carrier_team, lost_by, gained_by = None, None, None
    gtlog = []
    for f in range(60 * 60 * 40):
        clk = e.w(CLOCK)
        e.run(1, hold=["START"] if still > 900 and f % 240 == 0 else [])
        still = still + 1 if e.w(CLOCK) == clk else 0
        if e.w(GSP) != last_gsp:
            last_gsp = e.w(GSP)
            if e.w(CLOCK) > secs:
                e.setw(CLOCK, secs)
        running = not e.w(GMODE) & 0x100
        for tm in (0, 1):
            for off in (SHOWN, CHECKS):
                now = arr(e, tm, off)
                for i, (a, b) in enumerate(zip(prev[(tm, off)], now)):
                    if a != b:
                        log.append(dict(f=f, team=tm, place=i, what="shown" if off == SHOWN else "checks", by=b - a,
                                        running=running, gsp=e.w(GSP), clock=e.w(CLOCK)))
                prev[(tm, off)] = now
            p = e.w(HOME + tm * TMSIZE + 8)
            if p != pim[tm]:
                pens.append(dict(f=f, team=tm, team_pim_by=p - pim[tm], gsp=e.w(GSP), clock=e.w(CLOCK)))
                pim[tm] = p
        pc = e.w(PUCKC)
        if pc < 12:
            tm = 0 if pc < 6 else 1
            if carrier_team is not None and tm != carrier_team:
                lost_by, gained_by = carrier_team, tm
            carrier_team = tm
        g1, t1 = gt(e)
        for kind, a, b in (("give", g0, g1), ("take", t0, t1)):
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    gtlog.append(dict(f=f, kind=kind, team=i // 32, place=i % 32, by=y - x, lost_by=lost_by, gained_by=gained_by,
                                      running=not e.w(GMODE) & 0x100, shootout=bool(e.w(GMODE2) & 0x0100), gsp=e.w(GSP)))
        g0, t0 = g1, t1
        pb = e.w(PENBUF)
        if pb and pb != last_pb and (pb >> 8) >= 0x12:
            pens.append(dict(f=f, penbuf=f"{pb:04x}"))
        last_pb = pb
        if stars is None and e.w(GMODE) & 0x8000:                # gmstars (bit 7 of $FFBEF0): the stars box
            want = expected_scores(e, 0, 0, 2) + expected_scores(e, 1, 0, 2)
            best = None
            for k in range(240):                                 # the scores are worked out a little later: the frame
                got = [s32(e.l(STARS + 4 * i)) for i in range(52)]   # that agrees best
                m = sum(g == w for g, w in zip(got, want))
                if best is None or m > best[0]:
                    best = (m, k, got)
                e.run(1)
            stars = dict(f=f, after=best[1], got=best[2], gsp=e.w(GSP), want=want,
                         stats=dict(goals=[arr(e, tm, GOALS) for tm in (0, 1)], assists=[arr(e, tm, ASSISTS) for tm in (0, 1)],
                                    shots=[arr(e, tm, SHOTS) for tm in (0, 1)], checks=[arr(e, tm, CHECKS) for tm in (0, 1)],
                                    toi=[words(e, tm, TOI) for tm in (0, 1)], score=[e.w(HOME + tm * TMSIZE + 0xC) for tm in (0, 1)]))
        if e.w(GMODE2) & 0x0800 or (stars and f > stars["f"] + 600):
            break
        if f % 6000 == 5999:
            lowload.breathe()
    res = dict(rom=Path(rom).name, frames=f, log=log, pens=pens, stars=stars, gtlog=gtlog,
               totals=[[e.w(TOTALS[tm]), e.w(TOTALS[tm] + 2)] for tm in (0, 1)], gt_final=gt(e),
               final=dict(score=[e.w(HOME + tm * TMSIZE + 0xC) for tm in (0, 1)],
                          shown=[arr(e, tm, SHOWN) for tm in (0, 1)], checks=[arr(e, tm, CHECKS) for tm in (0, 1)],
                          goals=[arr(e, tm, GOALS) for tm in (0, 1)], assists=[arr(e, tm, ASSISTS) for tm in (0, 1)],
                          shots=[arr(e, tm, SHOTS) for tm in (0, 1)], toi=[words(e, tm, TOI) for tm in (0, 1)],
                          team_pim=pim))
    return res, r


def scen(rom, state, n=12):
    """Set plays from the live state (gen95_group1_fixes_check's Play: the named skaters at spots, the rest parked),
    home skater 2 on pad 1 with the puck, away skater 7: the giveaway / takeaway counts after each, and the carrier and
    cause words ($FFEA00 / $FFEA02) at the moment that matters."""
    import random
    import gen95_group1_fixes_check as G1
    r = O.R(rom, state)
    e = r.e
    A, D = 2, 7
    out = []

    def counts():
        g, t = gt(e)
        return dict(give_home=g[:32], give_away=g[32:], take_home=t[:32], take_away=t[32:])

    def diff(c0, c1):
        d = {}
        for k in c0:
            for i, (x, y) in enumerate(zip(c0[k], c1[k])):
                if x != y:
                    d[f"{k}[{i}]"] = y - x
        return d

    pa = lambda k: e.b(G1.rec(k) + 0x66)          # noqa: E731 roster place
    for trial in range(n):
        seed = random.Random(trial).getrandbits(32)
        dx = (-20, 0, 20)[trial % 3]
        # drop pass: A with the pad held back; the away skater close behind takes it
        p = G1.Play(e, r.base, {A: (dx, 40), D: (dx, 14)}, seed)
        G1.control(e, 1, A, 1)
        if p.give(A):
            c0 = counts()
            flags = 0
            for f in range(120):
                p.frame(held=(["A", "DOWN"] if f < 4 else []), hold=([] if f > 3 else [D]))
                flags |= e.w(0xBF08)
            out.append(dict(play="drop pass", trial=trial, drop_flag=bool(flags & 0x0200), d=diff(c0, counts()),
                            places=dict(A=pa(A), D=pa(D)), carrier=e.w(PUCKC)))
        # fake shot in the attacking zone, then the away skater pokes it (pad 2 B)
        p = G1.Play(e, r.base, {A: (dx, 150), D: (dx, 172)}, seed)
        G1.control(e, 1, A, 1)
        if p.give(A):
            c0 = counts()
            flags, w = 0, None
            for f in range(40):
                p.frame(held=(["A"] if f < 6 else []))
                flags |= e.w(0xBF08)
                if f == 20:
                    w = (e.w(0xEA00), e.w(0xEA02), e.w(PUCKC))
            G1.control(e, 2, D, 2)
            for f in range(150):
                ax, ay = G1.pos(e, A)
                kx, ky = G1.pos(e, D)
                p.frame(held2=G1.pad(G1.dir_to(ax - kx, ay - ky)) + (["B"] if f % 12 < 2 else []), hold=[])
            out.append(dict(play="fake shot, then a poke", trial=trial, fake_flag=bool(flags & 0x0100), words_after_fake=w,
                            d=diff(c0, counts()), places=dict(A=pa(A), D=pa(D)), carrier=e.w(PUCKC)))
        # a light hit: pad 2 skates (no burst) into the carrier; the stumble hook marks the hitter
        p = G1.Play(e, r.base, {A: (dx, 0), D: (dx + 40, 0)}, seed)
        G1.control(e, 1, A, 1)
        if p.give(A):
            G1.control(e, 2, D, 2)
            c0 = counts()
            cause, fell = [], False
            for f in range(200):
                ax, ay = G1.pos(e, A)
                kx, ky = G1.pos(e, D)
                p.frame(held2=G1.pad(G1.dir_to(ax - kx, ay - ky)) + (["C"] if trial % 2 and 6 <= f < 9 else []), hold=[])
                cause.append(e.w(0xEA02))
                fell = fell or bool(e.b(G1.rec(A) + 0x64) & 0x20) or e.w(G1.rec(A) + 0x58) in G1.SPA_FALLS
            out.append(dict(play="hit (" + ("burst" if trial % 2 else "skate") + ")", trial=trial, fell=fell,
                            cause_seen=sorted(set(cause)), d=diff(c0, counts()), places=dict(A=pa(A), D=pa(D)),
                            carrier=e.w(PUCKC)))
        # a shot blocked: the away skater in the shot's line keeps the puck
        p = G1.Play(e, r.base, {A: (dx, 120), D: (dx, 150)}, seed)
        G1.control(e, 1, A, 1)
        if p.give(A):
            c0 = counts()
            for f in range(150):
                p.frame(held=(["C", "UP"] if f < 3 else []), hold=[D] if f < 30 else [])
            out.append(dict(play="shot into a skater", trial=trial, d=diff(c0, counts()), places=dict(A=pa(A), D=pa(D)),
                            carrier=e.w(PUCKC)))
        lowload.breathe()
    return out


def stumble(rom, state, n=60):
    """Hits from the group 1 boards test's approach (pad 2 skates in from 70-110 and bursts within 22-38; the carrier
    on pad 1 in open ice): each hit's outcome (check animation, the carrier down or not, the puck dropped), the cause
    word ($FFEA02) right after, and the counts when the away team then has the puck."""
    import math
    import random
    import gen95_group1_fixes_check as G1
    r = O.R(rom, state)
    e = r.e
    A, D = 2, 7
    out = []
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
        g0, t0 = gt(e)
        c, hit, fell, dropped, cause = None, None, False, False, set()
        for f in range(240):
            ax, ay = G1.pos(e, A)
            kx, ky = G1.pos(e, D)
            if c is None and math.hypot(ax - kx, ay - ky) < trig:
                c = f
            chase = G1.pad(G1.dir_to(e.sw(0xAC62 + 14 * 0x80) - kx, e.sw(0xAC62 + 14 * 0x80 + 0x14) - ky)) if hit is not None else G1.pad(G1.dir_to(ax - kx, ay - ky))
            p.frame(held2=(["C"] if c is not None and f < c + 3 else []) + chase, hold=[])
            if hit is None and e.w(G1.rec(D) + 0x58) in G1.SPA_CHECKS:
                hit = f
            if hit is not None:
                fell = fell or bool(e.b(G1.rec(A) + 0x64) & 0x20) or e.w(G1.rec(A) + 0x58) in G1.SPA_FALLS
                dropped = dropped or e.w(PUCKC) != A
                cause.add(e.w(0xEA02))
        g1, t1 = gt(e)
        d = {f"{k}[{i}]": y - x for k, a, b in (("give", g0, g1), ("take", t0, t1)) for i, (x, y) in enumerate(zip(a, b)) if x != y}
        out.append(dict(trial=trial, hit=hit is not None, fell=fell, dropped=dropped, cause=sorted(cause), d=d,
                        carrier=e.w(PUCKC), placeA=e.b(G1.rec(A) + 0x66), placeD=e.b(G1.rec(D) + 0x66)))
        if trial % 10 == 9:
            lowload.breathe()
    return out


def fights(rom, maxfights=3):
    """Fighting On (Game Setup's ninth row), the computer on both sides, the check tension held at 40 or more
    (gen95_fight_check's --push): every giveaway / takeaway change, and whether a fight was on (the puck's +$63 bit 0)."""
    from emu import Emu
    import gen95_fight_check as F
    import gen95_shootout_check as SC
    e = Emu(rom)
    F.to_setup(e)
    for i in range(8):
        e.run(6, hold=["DOWN"]); e.run(30)
    for _ in range(6):
        if e.b(F.FIGHTROW) == 1:
            break
        e.run(6, hold=["RIGHT"]); e.run(40)
    e.run(6, hold=["START"]); e.run(300)
    e.run(6, hold=["START"]); e.run(60)
    e.run(1800)
    for _ in range(6):
        e.run(6, hold=["START"]); e.run(300)
    g0, t0 = gt(e)
    nf, on_prev, rows, fight_frames = 0, False, [], 0
    for f in range(60 * 60 * 30):
        if f % 60 == 0:
            SC.computer(e)
            e.setw(F.CHKCNT, max(e.w(F.CHKCNT), 40))
        e.run(1)
        on = bool(e.b(F.PUCKFLAGS) & 1)
        fight_frames += on
        if on and not on_prev:
            nf += 1
        g1, t1 = gt(e)
        for kind, a, b in (("give", g0, g1), ("take", t0, t1)):
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    rows.append(dict(f=f, kind=kind, slot=i, by=y - x, fight_on=on, fights_so_far=nf,
                                     running=not e.w(GMODE) & 0x100))
        g0, t0 = g1, t1
        if not on and on_prev and nf >= maxfights:
            e.run(600)
            break
        on_prev = on
        if f % 6000 == 5999:
            lowload.breathe()
    return dict(fights=nf, fight_frames=fight_frames, changes=rows)


import os
OT_SECS = int(os.environ.get("OT_SECS", "120"))     # overtime cut to this (3: straight to the shootout)


def ot_shootout(rom, state):
    """gen95_shootout_check's tie: the third period, 1-1 through the game's own Goal, 3 s left; overtime (3-on-3 on
    the settings_all builds outside the playoffs) cut to 120 s, then the shootout: every giveaway / takeaway change
    with the period, whether a shootout runs (gmode2 bit 0) and the skaters on the ice (tmap, team struct +$24)."""
    from emu import Emu
    import gen95_shootout_check as SC
    e = Emu(rom)
    e.run(1500)
    e.unserialize(Path(state).read_bytes())
    e.setw(GSP, 2); e.setw(CLOCK, 90); e.setw(SC.HM, 0); e.setw(SC.AW, 0)
    SC.put_goal(e, True); SC.put_goal(e, False)
    e.setw(CLOCK, 3)
    g0, t0 = gt(e)
    rows, still, ot_set, so_seen, carrier_team, lost, gained = [], 0, False, False, None, None, None
    for f in range(60 * 60 * 30):
        if f % 60 == 0:
            SC.computer(e)
        clk = e.w(CLOCK)
        e.run(1, hold=["START"] if still > 300 and f % 240 == 0 else [])
        still = still + 1 if e.w(CLOCK) == clk else 0
        if e.w(GSP) == 3 and e.w(CLOCK) > OT_SECS and not so_seen:     # the overtime clock cut (the game sets it
            e.setw(CLOCK, OT_SECS)                                       # again at the faceoff: held until it runs)
            ot_set = True
        so = bool(e.w(GMODE2) & 0x0100)
        so_seen = so_seen or so
        pc = e.w(PUCKC)
        if pc < 12:
            tm = 0 if pc < 6 else 1
            if carrier_team is not None and tm != carrier_team:
                lost, gained = carrier_team, tm
            carrier_team = tm
        g1, t1 = gt(e)
        for kind, a, b in (("give", g0, g1), ("take", t0, t1)):
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    rows.append(dict(f=f, kind=kind, team=i // 32, by=y - x, gsp=e.w(GSP), shootout=so,
                                     tmap=(e.w(HOME + 0x24), e.w(HOME + TMSIZE + 0x24)), lost=lost, gained=gained,
                                     right=(kind == "give" and i // 32 == lost) or (kind == "take" and i // 32 == gained)))
        g0, t0 = g1, t1
        if e.w(GSP) >= 4 and f > 600:
            e.run(600)
            break
        if f % 6000 == 5999:
            lowload.breathe()
    return dict(rows=rows, shootout_seen=so_seen, final=(e.w(SC.HM), e.w(SC.AW)), gsp=e.w(GSP))


def main():
    mode, rom, state, out = sys.argv[1:5]
    secs = int(sys.argv[5]) if len(sys.argv) > 5 else 120
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    if mode == "ot":
        res = ot_shootout(rom, state)
        (out / f"ot_{Path(rom).stem}.json").write_text(json.dumps(res))
        rows = res["rows"]
        print("shootout seen", res["shootout_seen"], "final", res["final"], "gsp", res["gsp"])
        print("changes by period and shootout:", dict(Counter((x["gsp"], x["shootout"], x["tmap"]) for x in rows)))
        print("right team as the puck went:", sum(x["right"] for x in rows), "of", len(rows))
        return
    if mode == "fights":
        res = fights(rom)
        (out / f"fights_{Path(rom).stem}.json").write_text(json.dumps(res))
        ch = res["changes"]
        print("fights", res["fights"], "fight frames", res["fight_frames"], "| changes", len(ch), "| during a fight",
              sum(x["fight_on"] for x in ch), "| with the clock stopped", sum(not x["running"] for x in ch))
        for x in ch:
            if x["fight_on"]:
                print("  during a fight:", x)
        return
    if mode == "stumble":
        rows = stumble(rom, state)
        (out / f"stumble_{Path(rom).stem}.json").write_text(json.dumps(rows))
        print(dict(Counter(("hit" if x["hit"] else "no hit", "down" if x["fell"] else ("dropped" if x["dropped"] else "kept")) for x in rows)))
        for x in rows:
            if x["hit"] and x["dropped"]:
                print(json.dumps(x))
        return
    if mode == "scen":
        rows = scen(rom, state)
        (out / f"scen_{Path(rom).stem}.json").write_text(json.dumps(rows))
        for x in rows:
            print(json.dumps(x))
        return
    if mode == "game":
        res, r = game(rom, state, secs)
        (out / f"game_{Path(rom).stem}.json").write_text(json.dumps(res))
        lg = res["log"]
        print(res["rom"], "frames", res["frames"], "score", res["final"]["score"], "team penalty minutes", res["final"]["team_pim"])
        print("  changes:", dict(Counter((x["what"], x["by"], x["running"]) for x in lg)))
        print("  penalties:", [p for p in res["pens"]][:12])
        print("  final shown (+$104):", res["final"]["shown"])
        print("  final checks (+$11E):", res["final"]["checks"])
        gl = res["gtlog"]
        ok = lambda x: (x["kind"] == "give" and x["team"] == x["lost_by"]) or (x["kind"] == "take" and x["team"] == x["gained_by"])  # noqa: E731
        print("  giveaways / takeaways:", dict(Counter((x["kind"], x["by"]) for x in gl)), "| team as the puck went:",
              sum(ok(x) for x in gl), "of", len(gl), "| while the clock stood:", sum(not x["running"] for x in gl),
              "| in a shootout:", sum(x["shootout"] for x in gl))
        gf, tf = res["gt_final"]
        print("  team totals (give, take):", res["totals"], "| sums of the players':", [[sum(gf[32 * tm:32 * tm + 32]), sum(tf[32 * tm:32 * tm + 32])] for tm in (0, 1)])
        st = res["stars"]
        print("  stars worked out:", bool(st))
        if st:
            got, want = st["got"], st["want"]
            for i in range(52):
                tm, pl = divmod(i, 26)
                flag = "" if got[i] == want[i] else "  <- differs"
                if got[i] != want[i] or i % 26 < 2 or any(st["stats"][k][tm][pl] for k in ("goals", "assists", "shots", "checks")):
                    print(f"   team {tm} place {pl}: got {got[i]}, formula {want[i]}{flag}  (g {st['stats']['goals'][tm][pl]} a {st['stats']['assists'][tm][pl]} "
                          f"s {st['stats']['shots'][tm][pl]} c {st['stats']['checks'][tm][pl]} toi {st['stats']['toi'][tm][pl]})")


if __name__ == "__main__":
    main()
