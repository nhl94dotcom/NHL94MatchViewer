"""NOSE4Web's Genesis NHL '94 options not yet played, round of 2026-11-25 (each ROM built from the original with only
the options named; the same test run on the original beside it). One emulator a process: a test takes one ROM.

Each test plays the ROM from power-on into a game (gen_ot_check.to_setup / into_play) and works from that live state.

  clock ROM [FRAMES]   the computer on both sides, every skater's Aggression held at 15 (penalties come): the frames
        between the game clock's seconds while it runs (24 on the original, 60 in real time), and for each player
        put in the box (tmpdst, team block +$66 by roster place: its low 11 bits the seconds left) the frames between
        his seconds.
  skating ROM          pad 1's skater, the others parked, his energy full. Burst: UP held, C pressed at frame 30:
        his speed's jump (the push; energy / 128 = 32 on the original). Stop: UP for 90 frames, then DOWN: the
        frames and distance until his speed up the ice is 0 (stopna's rate, 150 a frame on the original).
  goalie ROM           pad 1 on the home goalie (manual). hold: the puck slid onto him, nothing pressed: frames until
        the whistle (gmode's clock bit). side: LEFT / RIGHT held 240 frames: how far he gets from the net's middle.
        out: the pad held away from his net, without the puck and with it: how far he gets, and where a whistle comes.
  ratings ROM          every on-ice record's roster place and working bytes +$67..$75 (weight first), and the same
        players' rating nibbles in the ROM's roster (tools/systems/genesis.read_teams).

  stars ROM OUT [WAIT] [agg]   a computer game: the plus-minus log's entry at every goal, the three stars' scores
        against the formula, the log at a second game's start (see stars()).
  energy ROM [PERIODS] line changes On: energy lost a game second on the ice, gained on the bench (see energy()).

python gen_options_round.py clock|skating|goalie|ratings|stars|energy ROM [...]"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import gen_ot_check as G
import lowload
from emu import Emu

B, SZ = 0xB04A, 0x80
POS, PFLAGS, SPA = 0x35, 0x62, 0x58
PUCKC, GMODE, GSP, CLOCK, CONT1, CONT2, C1P, SCREEN = 0xB7AA, 0xC2EA, 0xC466, 0xC468, 0xC328, 0xC32A, 0xC320, 0xFFF7
TEAMS = (0xC6CE, 0xCA32)
OPTLINE, SFLAGS7 = 0xD058, 0xC2FC


def rec(k):
    return B + SZ * k


def boot(rom):
    e = Emu(rom)
    G.to_setup(e, Path(rom).parent)
    if not G.into_play(e):
        raise SystemExit("never reached play")
    e.run(150)
    return e, e.serialize()


def computer(e):
    e.setw(CONT1, 0)
    e.setw(CONT2, 0)
    for k in range(12):
        e.setb(rec(k) + PFLAGS, e.b(rec(k) + PFLAGS) & ~8)


def pad1(e, k):
    e.setw(CONT1, 1)
    e.setw(CONT2, 0)
    e.setw(C1P, k)
    for j in range(12):
        e.setb(rec(j) + PFLAGS, (e.b(rec(j) + PFLAGS) & ~8) | (8 if j == k else 0))


def park(e, keep, y=150):
    for j in range(12):
        if j not in keep and e.b(rec(j) + POS) != 0xFF:
            e.setw(rec(j), (-100 + 18 * (j % 6)) & 0xFFFF)
            e.setw(rec(j) + 0x14, y & 0xFFFF)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(rec(j) + off, 0)


def puck_away(e, x=100, y=150):
    P = rec(14)
    e.setw(PUCKC, 0xFFFF)
    e.setb(P + 0x60, 0xFF)
    e.setw(P, x & 0xFFFF); e.setw(P + 0x14, y & 0xFFFF); e.setw(P + 0x18, 0)
    for off in (0x28, 0x2A, 0x2C):
        e.setw(P + off, 0)


def clock(rom, frames=40000):
    e, base = boot(rom)
    ticks, last, since, run = [], e.w(CLOCK), 0, 0
    box = {}                                   # (team, place) -> [value, frames since its last change, [intervals]]
    for f in range(frames):
        if f % 60 == 0:
            computer(e)
            for k in range(12):
                if e.b(rec(k) + POS) not in (0, 0xFF):
                    e.setb(rec(k) + 0x73, 15)
            if f % 3600 == 0:
                lowload.breathe()
        e.run(1, hold=["START"] if e.b(SCREEN) != 0 and f % 60 < 4 else [])
        if e.b(SCREEN) != 0:
            last, since = e.w(CLOCK), 0
            continue
        c = e.w(CLOCK)
        since += 1
        if c == last - 1:
            ticks.append(since)
        if c != last:
            last, since = c, 0
        for t, team in enumerate(TEAMS):
            for p in range(26):
                w = e.w(team + 0x66 + 2 * p)
                v = w & 0x07FF if w < 0x8000 and not w & 0x2000 else None
                b = box.get((t, p))
                if v is None or v == 0:
                    if b:
                        b[0] = None
                    continue
                if b is None or b[0] is None:
                    box[(t, p)] = [v, 0, b[2] if b else []]
                    continue
                b[1] += 1
                if v == b[0] - 1:
                    b[2].append(b[1])
                if v != b[0]:
                    b[0], b[1] = v, 0
    pen = [x for b in box.values() for x in b[2]]
    out = dict(rom=Path(rom).name, clock_seconds_seen=len(ticks),
               frames_per_clock_second=dict(median=statistics.median(ticks) if ticks else None, least=min(ticks, default=None)),
               players_boxed=sum(1 for b in box.values() if b[2]), box_seconds_seen=len(pen),
               frames_per_box_second=dict(median=statistics.median(pen) if pen else None, least=min(pen, default=None)))
    print(json.dumps(out), flush=True)


def skater_setup(e, base, k=2):
    e.unserialize(base)
    e.setw(OPTLINE, 1)
    pad1(e, k)


def skating(rom):
    e, base = boot(rom)
    k = 2
    en = TEAMS[0] + 0x32 + 2 * e.b(rec(k) + 0x66)
    res = dict(rom=Path(rom).name, burst=[], stop=[])
    for trial in range(4):
        skater_setup(e, base)
        e.setw(rec(k), 0); e.setw(rec(k) + 0x14, (-150) & 0xFFFF)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(k) + off, 0)
        sp = []
        for f in range(60):
            park(e, (k,)); puck_away(e); e.setw(CLOCK, 250)
            if f < 30:
                e.setw(en, 0x1000)
            if f == 30:
                e0 = e.w(en)
            pad1(e, k)
            e.run(1, hold=["UP"] + (["C"] if 30 <= f < 33 else []))
            sp.append(e.sw(rec(k) + 0x2A))
        jumps = [sp[i] - sp[i - 1] for i in range(30, 45)]
        res["burst"].append(dict(speed_before=sp[29], biggest_jump=max(jumps), energy_cost=e0 - e.w(en), working_speed=e.b(rec(k) + 0x69)))
    for trial in range(6):
        skater_setup(e, base)
        e.setw(rec(k), (-20 + 8 * trial) & 0xFFFF); e.setw(rec(k) + 0x14, (-200) & 0xFFFF)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(k) + off, 0)
        for f in range(90):
            park(e, (k,), y=-250); puck_away(e, 100, -250); e.setw(CLOCK, 250); e.setw(en, 0x1000); pad1(e, k)
            e.run(1, hold=["UP"])
        v0, y0, n = e.sw(rec(k) + 0x2A), e.sw(rec(k) + 0x14), None
        for f in range(240):
            park(e, (k,), y=-250); puck_away(e, 100, -250); e.setw(CLOCK, 250); e.setw(en, 0x1000); pad1(e, k)
            e.run(1, hold=["DOWN"])
            if e.sw(rec(k) + 0x2A) <= 0:
                n = f + 1
                break
        res["stop"].append(dict(speed=v0, frames_to_stop=n, distance=e.sw(rec(k) + 0x14) - y0))
    print(json.dumps(res), flush=True)


def goalie(rom):
    e, base = boot(rom)
    res = dict(rom=Path(rom).name)
    e.unserialize(base)
    k = next(j for j in range(6) if e.b(rec(j) + POS) == 0)
    gx0, gy0 = e.sw(rec(k)), e.sw(rec(k) + 0x14)
    own = 1 if gy0 > 0 else -1                     # the end he defends
    away = "DOWN" if own > 0 else "UP"
    res["goalie at"] = [gx0, gy0]

    def frame(hold=(), with_puck=False):
        park(e, (k,), y=-own * 150)
        if not with_puck:
            puck_away(e, 100, -own * 150)
        e.setw(CLOCK, 250)
        pad1(e, k)
        e.run(1, hold=list(hold))

    def give():
        P = rec(14)
        for f in range(80):
            if f % 20 == 0 and e.w(PUCKC) != k:
                x, y = e.sw(rec(k)), e.sw(rec(k) + 0x14)
                e.setw(PUCKC, 0xFFFF); e.setb(P + 0x60, 0xFF)
                e.setw(P, x & 0xFFFF); e.setw(P + 0x14, (y - own * 14) & 0xFFFF); e.setw(P + 0x18, 0)
                e.setw(P + 0x28, 0); e.setw(P + 0x2A, (own * 1500) & 0xFFFF); e.setw(P + 0x2C, 0)
                e.setw(P + 0x5E, 0); e.setw(rec(k) + 0x5E, 0)
            frame(with_puck=True)
            if e.w(PUCKC) == k:
                return True
        return False

    # hold: frames with the puck until the whistle
    holds = []
    for trial in range(3):
        e.unserialize(base)
        for _ in range(10 + 7 * trial):
            frame()
        if not give():
            holds.append("never had the puck")
            continue
        n = None
        for f in range(1500):
            frame(with_puck=True)
            if e.w(GMODE) & 0x100:
                n = f + 1
                break
            if e.w(PUCKC) != k:
                n = f"lost it after {f + 1}"
                break
        holds.append(n)
    res["frames held until the whistle"] = holds
    # side range
    side = {}
    for d in ("LEFT", "RIGHT"):
        e.unserialize(base)
        xs, wh = [], None
        for f in range(240):
            frame([d])
            xs.append(e.sw(rec(k)))
            if wh is None and e.w(GMODE) & 0x100:
                wh = f
        side[d] = dict(farthest_x=min(xs) if d == "LEFT" else max(xs), whistle_at_frame=wh)
    res["side"] = side
    # out from the net, without and with the puck
    for label, puck in (("out without the puck", False), ("out with the puck", True)):
        e.unserialize(base)
        for _ in range(10):
            frame()
        if puck and not give():
            res[label] = "never had the puck"
            continue
        ys, wh = [], None
        for f in range(600):
            frame([away], with_puck=puck)
            ys.append(e.sw(rec(k) + 0x14))
            if e.w(GMODE) & 0x100:
                wh = dict(frame=f, y=ys[-1])
                break
            if puck and e.w(PUCKC) != k:
                wh = dict(frame=f, y=ys[-1], lost_the_puck=True)
                break
        res[label] = dict(nearest_centre_ice=min(abs(y) for y in ys), whistle=wh)
    print(json.dumps(res), flush=True)


def ratings(rom):
    from systems import genesis
    e, base = boot(rom)
    teams = genesis.read_teams(Path(rom))
    ids = [e.b(0xC6F7), e.b(0xCA5B)]
    rows = []
    for k in range(12):
        if e.b(rec(k) + POS) == 0xFF:
            continue
        place = e.b(rec(k) + 0x66)
        t = teams[ids[k // 6]]
        pl = t["players"][place] if place < len(t["players"]) else {}
        rows.append(dict(rec=k, pos=e.b(rec(k) + POS), place=place, name=pl.get("name"), working=[e.b(rec(k) + o) for o in range(0x67, 0x76)],
                         rom={kk: pl.get(kk) for kk in pl if kk not in ("name",)}))
    print(json.dumps(dict(rom=Path(rom).name, teams=[teams[i]["abbr"] for i in ids], rows=rows)), flush=True)


STARSCORES, PMLEN, PMLOG = 0xCF36, 0xDEF4, 0xDEF6
VALUES = {"linesOff": dict(goal=11000, assist=7000, shot=500, check=500, ga=-11000, sa=4000, shutout=16000),
          "linesOn": dict(goal=14300, assist=9100, shot=650, check=650, ga=-11000, sa=4500, shutout=20800)}


def star_formula(st, v):
    """NOSE4Web's CalcTeamStarScores (its bytes at $1867E read): every slot starts at the goal difference; a skater
    adds goals, assists, shots and checks; a goalie with shots against and the ice time adds half an assist's value
    an assist, the shutout, goals against, and the shots faced (one fewer for the losers)."""
    out = []
    for t in (0, 1):
        s = st[t]
        margin = st[t]["score"] - st[1 - t]["score"]
        for i in range(26):
            val = margin
            if i >= s["goalies"]:
                val += s["g"][i] * v["goal"] + s["a"][i] * v["assist"] + s["s"][i] * v["shot"] + s["c"][i] * v["check"]
            elif s["s"][i] and s["ice"][i] >= st[0]["need"]:
                val += s["a"][i] * v["assist"] // 2 + (v["shutout"] if s["g"][i] == 0 else 0) + s["g"][i] * v["ga"]
                val += (s["s"][i] - (1 if margin < 0 else 0)) * v["sa"]
            out.append(val)
    return out


def stars(rom, out, wait=0, agg=False, lines="linesOff"):
    """A computer game from power-on (WAIT more frames on Game Setup first: another game). Every goal: the skaters
    on the ice (records 0-11 not parked at x $FF10, their roster places) against the plus-minus log's new entry (14
    bytes from $FFDEF6 + the length word at $FFDEF4: a flag byte, a byte left alone, the 12 places). At the Stars of
    the Game box (gmode bit 7): the 52 scores at $FFCF36 against the formula on the team blocks (the three taken
    are cleared). Then START back to the menus and into a second game: the log's length and old entries. AGG: every
    skater's Aggression held at 15, for penalties (the formula's "checks" are the bytes at +$102: penalty minutes
    on a ROM without the bodycheck count, ROM $12302 = D532 0000)."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    G.to_setup(e, out)
    e.run(wait)
    if agg:
        e.setw(0xD056, 1)                                    # OptPen: On (Off as the menu comes up)
    if not G.into_play(e):
        raise SystemExit("never reached play")
    print("log length at the first frame of play", e.w(PMLEN), "OptLine", e.w(OPTLINE), flush=True)

    def on_ice():
        return [0xFF if e.w(rec(k)) == 0xFF10 else e.b(rec(k) + 0x66) for k in range(12)]

    def team_stats():
        st = []
        for t in TEAMS:
            st.append(dict(score=e.w(t + 0xC), g=[e.b(t + 0xB4 + i) for i in range(26)], a=[e.b(t + 0xCE + i) for i in range(26)],
                           s=[e.b(t + 0xE8 + i) for i in range(26)], c=[e.b(t + 0x102 + i) for i in range(26)],
                           ice=[e.w(t + 0x136 + 2 * i) for i in range(26)]))
        return st

    goals, res, f, still, last, score = [], None, 0, 0, None, (0, 0)
    prev_ice, prev_len = on_ice(), e.w(PMLEN)
    mine, was_mine, drops = (e.b(0xC6F7), e.b(0xCA5B)), True, []
    while f < 60 * 60 * 40:
        computer(e)
        if agg:
            for k in range(12):
                if e.b(rec(k) + POS) not in (0, 0xFF):
                    e.setb(rec(k) + 0x73, 15)
        e.run(1, hold=["START"] if still > 900 and f % 240 == 0 else [])
        f += 1
        c = e.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        now = (e.w(TEAMS[0] + 0xC), e.w(TEAMS[1] + 0xC))
        n = e.w(PMLEN)
        is_mine = (e.b(0xC6F7), e.b(0xCA5B)) == mine
        if not (is_mine and was_mine):                       # an intermission highlight of another game: only the log watched
            if n != prev_len or is_mine != was_mine:
                drops.append(dict(f=f, gsp=e.w(GSP), clock=c, len=(prev_len, n), ours=is_mine, score=now))
                print(f"  {'our game again' if is_mine else 'another game (intermission highlight)'}: the log's length {prev_len} -> {n}, "
                      f"score shown {now}", flush=True)
            prev_len, was_mine, prev_ice = n, is_mine, on_ice()
            if is_mine:
                score = now
            continue
        if now != score or n != prev_len:
            entry = [e.b(PMLOG + prev_len + i) for i in range(max(n - prev_len, 0))]
            goals.append(dict(f=f, gsp=e.w(GSP), clock=c, score=now, was=score, ice_before=prev_ice, ice=on_ice(), len=(prev_len, n),
                              entry=entry, sflags4=e.b(0xC2F4), gmode2=e.b(0xC2FA), skaters=[sum(1 for x in on_ice()[a:a + 6] if x != 0xFF) for a in (0, 6)]))
            g = goals[-1]
            away = now[1] > score[1]
            ok = len(entry) == 14 and entry[2:] == prev_ice and bool(entry[0] & 0x80) == away
            print(f"goal {g['was']} -> {now} period {g['gsp'] + 1} clock {c}: on the ice {prev_ice}; entry {entry}; "
                  f"{'agrees' if ok else 'DIFFERS'}; on the ice a side {g['skaters']}", flush=True)
            score, prev_len = now, n
        prev_ice = on_ice()
        if res is None and e.w(GMODE) & 0x8000:
            e.run(2)                                         # ShowThreeStars sets the bit, then waits a frame before the scores
            f += 2
            st = team_stats()
            got = [e.l(STARSCORES + 4 * i) for i in range(52)]
            got = [x - (1 << 32) if x & 0x80000000 else x for x in got]
            from systems import genesis
            teams = genesis.read_teams(Path(rom))
            ids = [e.b(0xC6F7), e.b(0xCA5B)]
            best = None
            for goalies in ((2, 2), (3, 3), (2, 3), (3, 2), (1, 1)):
                for need in (0, 1, 100000):
                    for t in (0, 1):
                        st[t]["goalies"] = goalies[t]
                    st[0]["need"] = need
                    want = star_formula(st, VALUES[lines])
                    bad = [i for i in range(52) if got[i] != want[i] and got[i] != 0]
                    if best is None or len(bad) < len(best[0]):
                        best = (bad, want, goalies, need)
            bad, want, goalies, need = best
            taken = [i for i in range(52) if got[i] == 0 and want[i] != 0]
            order = sorted(range(52), key=lambda i: (-want[i], i))[:3]

            def who(i):
                t = teams[ids[i // 26]]
                p = t["players"][i % 26] if i % 26 < len(t["players"]) else {}
                s = st[i // 26]
                return f"{t['abbr']} {p.get('name')} (G {s['g'][i % 26]} A {s['a'][i % 26]} S {s['s'][i % 26]} +$102 {s['c'][i % 26]}, score {want[i]})"
            res = dict(f=f, gsp=e.w(GSP), score=now, bad=bad, taken=taken, top3=order, goalies=goalies, need=need,
                       names=[who(i) for i in order], taken_names=[who(i) for i in taken])
            print(f"stars: final {now}, period word {e.w(GSP)}; scores other than the three taken that differ from the formula: {len(bad)} "
                  f"(goalie slots {goalies}, ice-time rule {need}); cleared slots {taken}; the formula's top three {order}", flush=True)
            for i in order:
                print("   ", who(i), flush=True)
            for i in bad:
                print("    differs:", i, got[i], want[i], who(i), flush=True)
            print("    bodycheck count in this ROM:", Path(rom).read_bytes()[0x12302:0x12306].hex() == "4e714e71",
                  "; players with a count at +$102:", [who(i) for i in range(52) if st[i // 26]["c"][i % 26]], flush=True)
            e.run(30)
            e.screenshot(out / "stars.png")
        if res is not None and f > res["f"] + 600:
            break
    # a second game from the same power-on: the log cleared
    old = e.w(PMLEN)
    for _ in range(40):
        e.run(4, hold=["START"])
        e.run(90)
        if e.b(SCREEN) != 0:
            break
    ok2 = G.into_play(e)
    after = [e.b(PMLOG + i) for i in range(old)]
    print(f"second game reached {ok2}: the log's length {old} -> {e.w(PMLEN)}, old entries' bytes not zero {sum(1 for x in after if x)}; "
          f"scores {e.w(TEAMS[0] + 0xC)}-{e.w(TEAMS[1] + 0xC)}", flush=True)
    (out / "stars.json").write_text(json.dumps(dict(rom=Path(rom).name, goals=goals, stars=res, highlights=drops)))


def energy(rom, periods=1):
    """Line changes On (OptLine $D058 = 0 on Game Setup), the computer on both sides, PERIODS periods. Every 60
    frames each roster place's energy (team block +$32, words) and where he is (+$66: $FFFF the ice, $FFFE the
    bench). Over pairs of samples a clock second or more apart with him in the same place: energy lost a game second
    on the ice, gained on the bench (below the top), and the shifts' lengths."""
    e = Emu(rom)
    G.to_setup(e, Path(rom).parent)
    e.setw(OPTLINE, 0)
    if not G.into_play(e):
        raise SystemExit("never reached play")
    log, f, still, last = [], 0, 0, None
    while e.w(GSP) < periods and f < 60 * 60 * 25:
        computer(e)
        e.run(60, hold=["START"] if still >= 5 else [])
        f += 60
        c = e.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        if e.b(SCREEN) == 0:
            log.append((e.w(GSP), c, [[(e.w(t + 0x32 + 2 * s), e.w(t + 0x66 + 2 * s)) for s in range(26)] for t in TEAMS]))
        if f % 3600 == 0:
            lowload.breathe()
    ice, bench, top, steps = [], [], 0, {}
    shifts = []
    for t in (0, 1):
        for s in range(26):
            run = None
            for a, b in zip(log, log[1:]):
                (en0, w0), (en1, w1) = a[2][t][s], b[2][t][s]
                top = max(top, en0)
                secs = a[1] - b[1]
                if w0 == 0xFFFF:
                    run = (run or 0) + max(secs, 0)
                elif run:
                    shifts.append(run)
                    run = None
                if a[0] != b[0] or secs < 1 or w0 != w1:
                    continue
                if w0 == 0xFFFF and en1 > 0 and en0 != 0x1000 + 9:
                    if en0 != en1 or s >= 3:                 # a goalie's never moves: left out
                        ice.append((en0 - en1) / secs)
                        steps[en0 - en1] = steps.get(en0 - en1, 0) + 1
                elif w0 == 0xFFFE and en1 < 0x1000 and en0 < 0x1000:
                    bench.append((en1 - en0) / secs)
    q = lambda v: [round(x, 1) for x in statistics.quantiles(v, n=4)] if len(v) > 3 else v
    print(json.dumps(dict(rom=Path(rom).name, optline=e.w(OPTLINE), samples=len(log), top_energy=top,
                          ice_pairs=len(ice), ice_lost_a_second_quartiles=q(ice), ice_lost_mean=round(statistics.mean(ice), 2) if ice else None,
                          bench_pairs=len(bench), bench_gained_quartiles=q(bench), bench_gained_mean=round(statistics.mean(bench), 2) if bench else None,
                          commonest_ice_steps=sorted(steps.items(), key=lambda kv: -kv[1])[:8], shifts=len(shifts), shift_seconds_quartiles=q(shifts),
                          lowest_energy=min(min(x[0] for x in tm) for _, _, tms in log for tm in tms))), flush=True)


if __name__ == "__main__":
    lowload.gentle()
    mode, rom = sys.argv[1], sys.argv[2]
    if mode == "clock":
        clock(rom, int(sys.argv[3]) if len(sys.argv) > 3 else 40000)
    elif mode == "stars":
        stars(rom, sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 0, len(sys.argv) > 5)
    elif mode == "energy":
        energy(rom, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    else:
        {"skating": skating, "goalie": goalie, "ratings": ratings}[mode](rom)
