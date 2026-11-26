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

python gen_options_round.py clock|skating|goalie|ratings ROM [...]"""
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


if __name__ == "__main__":
    lowload.gentle()
    mode, rom = sys.argv[1], sys.argv[2]
    if mode == "clock":
        clock(rom, int(sys.argv[3]) if len(sys.argv) > 3 else 40000)
    else:
        {"skating": skating, "goalie": goalie, "ratings": ratings}[mode](rom)
