"""NOSE4Web's ten Genesis settings on the SNES (2026-11-20), played. Each part runs the same trials on every ROM given
(the editor-opened original first, then builds with one setting each), from the retail live states
(snes_assist_stick_test.Game; the SA-1 build boots its own). From the NHL94SNES disassembly:

- `goalie`: the home goalie put on pad 1 (playerpad 0, the person flag), the others parked.
  - hold: the puck given to him at a depth from his goal line's end of the rink (|y| 240 ... 90, x 0), no buttons:
    the frames until the whistle (gmclock $15D6 set). assgoalie .13: holding with |y| >= the line (cmp #$BB / #$FF45)
    counts temp5 (puckglue's 140) down by the timestep; nearer the middle the whistle is at once (temp5 = 0).
    The same with his animation set to SPAgdive as he takes it (puckglue's 5 for a dive catch), and for the away
    goalie (the computer's) at depth 240.
  - box: without the puck, the pad held left, right or up the ice for 300 frames: the farthest x and the least depth
    he reached, and where he was at the end (the SNES skates him back when he's out of the box).
- `skate`: the pad-1 skater, the others parked.
  - stop: RIGHT held 90 frames from a standstill, then the pad let go (dostop / stopna's friction, ($70 + legstr) x
    timestep) or LEFT held: x speed after 4, 8, 16 and 32 frames, and the frames until it is 0 or below.
  - burst: standing, facing right, energy (tmpde) $1000, $800 or $400, line changes off / on (OptLine $34C6): A
    pressed; the x speed 6 frames later (burst.asm: speed energy x $233 >> 16 into Xvel along facedir; NOSE4Web's
    option a fixed push for everyone).
  - glide: moving right at $3000 with pfdoff (bit 0 of pflags, as a pass receiver), no pad: the speed kept a second.
- `puck`: the puck put loose at centre ice (z 0) sliding right at $3000 (and $1800), everyone parked: its speed at each
  of 3 seconds (updateplayers' table .22 for a gliding object, the puck's own row .20).
- `cvc ROM GAMES OUT [FIRST]`: computer games as snes_60fps_cvc (5-minute periods, penalties On, No Offside), to the
  end of the game and ShowThreeStars: every clock tick's frame (play, the replay, a pause), each penalty box stay in
  frames and clock seconds, the clock at each period's start, icing (iflags $0CF1 armed, PenIcing $0C calls), the
  three stars (star1-3 $1E2B, scores $1E31) with each player's goals, assists, shots (goalies: against) and whether
  the box came up, and a work RAM hash each 600 frames (`same` compares two ROMs' runs: where they first differ).
  PLAYOFFS=1: Play Mode set to New Playoffs on the menu (RIGHT x 2) (intermission highlights: DoHiLights, ticks counted as
  'highlight' while sflags3 bit 3 is set). CLUTCH=1: in the third period the scores are set level when the clock reaches 2:30 (clutch time's case).

python snes_gen_settings_check.py goalie|skate|puck OUT ROM [ROM ...]
python snes_gen_settings_check.py cvc ROM GAMES OUT [FIRST]   |   dive ROM GAMES OUT (dive catches, computer games)   |   same A.jsonl B.jsonl   |   report OUT.jsonl ..."""
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

import lowload
from snes_assist_stick_test import Game, PUCKC, CARRIER2, PLAYERPAD, POSITION, PFGOAL, XPOS, YPOS, XVEL, YVEL, ZPOS, PUCK

GMCLOCK, CLOCK, GSP, SFLAGS, PFLAGS, SPA, FACEDIR, TEMP5 = 0x15D6, 0x1632, 0x1630, 0x15D8, 0x1283, 0x11A3, 0x1163, 0x1083
TMPDE, PNUM, OPTLINE, PFALOCK, PF2AIP = 0x17EA, 0x12A3, 0x34C6, 0x14E3, 0x1543
SPAGDIVE = 0xE4B6
STARS, STARSCORE, TMGOALS, TMASSISTS, TMPSHOTS, TMSCORE = 0x1E2B, 0x1E31, 0x18EE, 0x1922, 0x1956, 0x178E
IFLAGS, PENBUF, INBOX = 0x0CF1, 0x15DE, 0x1624
GOALS_P, SHOTS_P = 0x177E, 0x176A


def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def goalie_k(G, team):
    return next(k for k in range(6 * team, 6 * team + 6) if G.w(POSITION + 2 * k) == 0)


def to_pad1(G, k):
    for j in range(12):
        G.setw(PLAYERPAD + 2 * j, 0xFFFF)
        G.setw(PFLAGS + 2 * j, G.w(PFLAGS + 2 * j) & ~8)
    G.setw(PLAYERPAD + 2 * k, 0)
    G.setw(PFLAGS + 2 * k, G.w(PFLAGS + 2 * k) | 8)
    G.setw(0x19EC, 2 * k)                                  # c1playernum
    G.setw(0x19D0, 1 if k < 6 else 0)                      # teampads
    G.setw(0x19D2, 0 if k < 6 else 1)
    G.setw(0x19F6, 0 if k < 6 else 1)                      # padside
    G.setw(0x1C84, 1 if k < 6 else 2)                      # cont1team


def park_all(G, keep, y):
    for j in range(12):
        if j in keep or G.w(POSITION + 2 * j) == 0xFFFF:
            continue
        G.put(j, -100 + 18 * (j % 6) + (10 if j >= 6 else 0), y)


def give_puck(G, k):
    G.setw(PUCKC, 2 * k)
    G.setw(CARRIER2, 2 * k)
    G.setw(ZPOS + 2 * PUCK, 0)


def goalie_part(G):
    out = []
    base = G.g.bases[0]
    for team, person in ((0, True), (1, False)):
        for depth in ((240, 215, 200, 190, 186, 180, 150, 120, 90) if person else (240, 200)):
            for dive in ((False, True) if person and depth == 240 else (False,)):
                G.e.unserialize(base)
                k = goalie_k(G, team)
                if person:
                    to_pad1(G, k)
                else:
                    to_pad1(G, next(j for j in range(6 * (1 - team), 6 * (1 - team) + 6) if G.w(POSITION + 2 * j) == 4))
                park_all(G, {k}, 0)
                G.run(2)
                own = 1 if s16(G.w(YPOS + 2 * k)) > 0 else -1
                y0 = own * depth
                G.put(k, 0, y0)
                G.put(PUCK, 0, y0 + own * -6)
                if dive:                                  # in a dive as he takes it (assgoalie keeps an animation
                    G.setw(SPA + 2 * k, SPAGDIVE)         # in progress)
                    G.setw(PF2AIP + 2 * k, 1)
                picked = None
                for f in range(40):                       # his own pickup (puckglue starts the hold timer)
                    G.run(1)
                    if G.w(PUCKC) == 2 * k:
                        picked = f
                        break
                    G.put(PUCK, s16(G.w(XPOS + 2 * k)), s16(G.w(YPOS + 2 * k)) - own * 6)
                whistle, held = None, 0
                for f in range(1500 if picked is not None else 0):
                    G.run(1)
                    if G.w(PUCKC) == 2 * k:
                        held += 1
                    if G.w(GMCLOCK):
                        whistle = f
                        break
                out.append(dict(part="hold", person=person, depth=depth, dive=dive, picked=picked, whistle=whistle, held=held,
                                y=s16(G.w(YPOS + 2 * k))))
    for name, pad in (("left", ["LEFT"]), ("right", ["RIGHT"]), ("out", None)):
        G.e.unserialize(base)
        k = goalie_k(G, 0)
        to_pad1(G, k)
        own = 1 if s16(G.w(YPOS + 2 * k)) > 0 else -1
        park_all(G, {k}, -own * 200)
        G.put(PUCK, 0, -own * 200)
        G.setw(PUCKC, 0xFFFF)
        hold = pad or (["DOWN"] if own > 0 else ["UP"])
        xs, ds = [], []
        for f in range(300):
            if G.w(PLAYERPAD + 2 * k) != 0:              # the game gives the pad back to a skater: keep it on him
                to_pad1(G, k)
            G.run(1, hold=hold)
            xs.append(s16(G.w(XPOS + 2 * k)))
            ds.append(abs(s16(G.w(YPOS + 2 * k))))
        out.append(dict(part="box", dir=name, min_x=min(xs), max_x=max(xs), least_depth=min(ds), most_depth=max(ds),
                        end_x=xs[-1], end_depth=ds[-1], at=[(xs[i], ds[i]) for i in (30, 60, 120, 200, 299)]))
    return out


def skater(G):
    k, team, up = G.me()
    park_all(G, {k}, -230 * up)
    G.put(k, -60, 0)
    G.put(PUCK, 0, 230 * up)
    G.setw(PUCKC, 0xFFFF)
    return k


def skate_part(G):
    out = []
    base = G.g.bases[0]
    for after in ("release", "reverse"):
        G.e.unserialize(base)
        k = skater(G)
        G.run(90, hold=["RIGHT"])
        v0 = s16(G.w(XVEL + 2 * k))
        vs, stop = {}, None
        for f in range(1, 121):
            G.run(1, hold=["LEFT"] if after == "reverse" else [])
            v = s16(G.w(XVEL + 2 * k))
            if f in (4, 8, 16, 32):
                vs[f] = v
            if stop is None and v <= 0:
                stop = f
        out.append(dict(part="stop", after=after, v0=v0, v=vs, frames_to_0=stop))
    for optline in (0, 1, 2):
        for energy in (0x1000, 0x800, 0x400):
            G.e.unserialize(base)
            k = skater(G)
            G.setw(OPTLINE, optline)
            G.run(30)
            G.setw(FACEDIR + 2 * k, 2)                      # facing right
            G.setw(XVEL + 2 * k, 0)
            G.setw(YVEL + 2 * k, 0)
            team = 0 if k < 6 else 1
            slot = G.w(PNUM + 2 * k) + (0x1A if team else 0)
            G.setw(TMPDE + 2 * slot, energy)
            G.run(1)
            before = s16(G.w(XVEL + 2 * k))
            G.run(3, hold=["A"])
            vs = []
            for _ in range(6):
                G.run(1)
                vs.append(s16(G.w(XVEL + 2 * k)))
            out.append(dict(part="burst", optline=optline, energy=energy, before=before, after=max(vs),
                            energy_after=G.w(TMPDE + 2 * slot), spa=G.w(SPA + 2 * k)))
    G.e.unserialize(base)
    k = skater(G)
    G.run(2)
    G.setw(XVEL + 2 * k, 0x3000)
    G.setw(YVEL + 2 * k, 0)
    G.setw(PFLAGS + 2 * k, G.w(PFLAGS + 2 * k) | 1)
    G.run(1)
    v1 = s16(G.w(XVEL + 2 * k))
    G.run(60)
    out.append(dict(part="glide", v1=v1, v61=s16(G.w(XVEL + 2 * k)), pfdoff=G.w(PFLAGS + 2 * k) & 1))
    return out


def puck_part(G):
    out = []
    base = G.g.bases[0]
    for v in (0x3000, 0x1800):
        G.e.unserialize(base)
        k = skater(G)
        park_all(G, set(), 230)
        G.put(k, -100, 230)
        G.run(2)
        G.setw(PUCKC, 0xFFFF)
        G.put(PUCK, -120, 0, v, 0)
        G.setw(ZPOS + 2 * PUCK, 0)
        G.run(1)
        speeds = [s16(G.w(XVEL + 2 * PUCK))]
        for sec in range(3):
            G.run(60)
            speeds.append(s16(G.w(XVEL + 2 * PUCK)))
        out.append(dict(part="puck", v=v, speeds=speeds, x=s16(G.w(XPOS + 2 * PUCK)), z=G.w(ZPOS + 2 * PUCK),
                        kept=[round(speeds[i + 1] / speeds[i], 3) if speeds[i] else None for i in range(3)]))
    return out


# --- computer games
def cvc_game(rom, n):
    import snes_60fps_cvc as C
    import menu_shots as M
    e = M.emulator(rom)
    m = C.Mem(e, rom)
    tmp = Path(f"x_tmp_gs{os.getpid()}")
    if m.sa1:
        M.play(e, f"w{1800 + 53 * n} START w240", tmp)
    else:
        po = "RIGHT*2 w30 " if os.environ.get("PLAYOFFS") == "1" else "LEFT w30 " if os.environ.get("SHOOTOUT") == "1" else ""       # Play Mode: Playoffs
        M.play(e, f"w{1500 + 53 * n} START w240 START w240 {po}DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
    M.play(e, "START w240 START w200 w2400", tmp)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(GMCLOCK) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    m.setw(C.OPTPEN, 2)
    shootout = os.environ.get("SHOOTOUT") == "1"
    if not shootout:
        C.computer_only(m)
    m.setw(C.SEED, (0x9E37 * (n + 1)) & 0xFFFF or 1)
    m.setw(C.SEED + 2, (0x7F4A * (n + 3)) & 0xFFFF or 1)
    for a in range(STARS, STARS + 6, 2):
        m.setw(a, 0x7777)
    clutch = os.environ.get("CLUTCH") == "1"
    ticks = Counter()               # (state, frames since the last tick) -> count
    period_start, boxes, box_open = [], [], {}
    armed, icing_calls, seen, hashes = 0, 0, set(), []
    last_clock, last_tick, frame, still, prev_period = m.w(CLOCK), 0, 0, 0, None
    last_armed = 0
    stars_at = None
    pp_ticks, ps, ps_cur = [0, 0], [], None    # clock ticks with a team a man up (tmap $17A6); penalty shots
    while frame < 400000:
        e.run(1)
        frame += 1
        c, per, sf = m.w(CLOCK), m.w(GSP), m.w(SFLAGS)
        state = "highlight" if m.w(0x15DC) & 8 else "replay" if sf & 0x0800 else "pause" if sf & 1 else             "stopped" if m.w(GMCLOCK) else "play"
        if per != prev_period and per < 4:
            period_start.append((per, c))
            prev_period = per
        if c == last_clock - 1:
            ticks[(state, min(frame - last_tick, 999))] += 1
            if state == "play":
                ta, tb = m.w(0x17A6), m.w(0x17A8)
                if ta != tb:
                    pp_ticks[0 if ta > tb else 1] += 1
            last_tick = frame
            if clutch and per == 2 and c == 150:
                s = m.w(TMSCORE)
                m.setw(TMSCORE + 2, s)
        elif c != last_clock:
            last_tick = frame
        last_clock = c
        if frame % 2 == 0:
            ia = m.w(IFLAGS) & 4
            if ia and not last_armed:
                armed += 1
            last_armed = ia
            now = set()
            for slot in range(0, 64, 2):
                buf, o = m.at(PENBUF + slot)
                code, obj = buf[o], buf[o + 1] & 0x7F
                if code:
                    now.add((slot, code, obj))
                    if (slot, code, obj) not in seen and code == 0x0C:
                        icing_calls += 1
            seen = now
            box = m.w(INBOX)
            for t, nib in ((0, (box >> 4) & 0xF), (1, box & 0xF)):
                o = box_open.get(t)
                if o and nib < o[0]:
                    boxes.append(dict(team=t, frames=frame - o[1], clock_s=o[2] - c if per == o[3] else None, n=o[0]))
                    box_open[t] = (nib, frame, c, per) if nib else None
                elif nib > (o[0] if o else 0):
                    box_open[t] = (nib, frame, c, per)
        psa = m.w(0x163A)                       # PenShotActive: pstimer's start and how long the shot ran
        if psa and ps_cur is None:
            ps_cur = dict(start=frame, timer0=m.w(0x1E9F), shooter=m.w(0x1E8D), person=None)
            sh = m.w(0x1E8D)
            if sh < 24:
                ps_cur["person"] = bool(m.w(PFLAGS + sh) & 8)
        elif not psa and ps_cur is not None:
            ps_cur["frames"] = frame - ps_cur.pop("start")
            ps.append(ps_cur)
            ps_cur = None
        if frame % 600 == 0:
            if per < 3 and not shootout:
                h = hashlib.md5(bytes(m.e.ram[0:0x2000]) + bytes(m.e.ram[0x2000:0x4000])).hexdigest()[:8] if not m.sa1 else None
                hashes.append(h)
                C.computer_only(m)
            lowload.breathe()
        if m.w(STARS) != 0x7777 and stars_at is None:
            stars_at = frame
        if stars_at is not None and frame > stars_at + 300:
            break
        if c == last_clock and state != "play":
            still += 1
        else:
            still = 0
        if still >= 900:
            e.run(4, hold=["START"])
            frame += 4
            still = 0
    stars = [m.w(STARS + 2 * i) for i in range(3)]
    scores = []
    for i in range(3):
        lo, hi = m.w(STARSCORE + 4 * i), m.w(STARSCORE + 4 * i + 2)
        scores.append((s16(hi) << 15) | (lo & 0x7FFF))
    players = []
    for x in range(52):
        buf, o = m.at(TMGOALS + x)
        g = buf[o]
        buf, o = m.at(TMASSISTS + x)
        a = buf[o]
        buf, o = m.at(TMPSHOTS + x)
        s = buf[o]
        players.append((g, a, s))
    checks = []
    for x in range(52):                         # NOSE4Web's bodycheck counts (given), read by the new star weights
        buf, o = m.at(0x168E + x)
        checks.append(buf[o])
    per = lambda base, t: sum(m.w(base + 4 * q + 2 * t) for q in range(4))
    toi = []
    for x in range(52):                         # NOSE4Web's / McMarkis's time on ice: a word a player at $7E:E800
        buf, o = m.at(0xE800 + 2 * x)
        toi.append(buf[o] | buf[o + 1] << 8)
    return dict(pp_time=[m.w(0x1756), m.w(0x1758)], pp_ticks=pp_ticks, toi=toi, penalty_shots=ps, checks168e=checks, game=n, rom=Path(rom).name, frames=frame, ticks=[[k[0], k[1], v] for k, v in ticks.items()],
                period_start=period_start, boxes=boxes, icing_armed=armed, icing_calls=icing_calls,
                stars=stars, star_scores=scores, stars_frame=stars_at, players=players,
                goals=[per(GOALS_P, t) for t in (0, 1)], shots=[per(SHOTS_P, t) for t in (0, 1)],
                hashes=hashes, clutch=clutch, playmode=m.w(0x34BC))


def dive_game(rom, n):
    """Computer games (cvc_game's start): every goalie pickup, temp5 on his first frame with it (puckglue's 140, or
    the dive amount for a catch in a dive), the frames until his animation ends (pf2aip clear) and until the whistle
    (gmclock) or the puck leaves him."""
    import snes_60fps_cvc as C
    import menu_shots as M
    e = M.emulator(rom)
    m = C.Mem(e, rom)
    tmp = Path(f"x_tmp_gs{os.getpid()}")
    M.play(e, f"w{1500 + 53 * n} START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
    M.play(e, "START w240 START w200 w2400", tmp)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(GMCLOCK) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    m.setw(C.OPTPEN, 2)
    C.computer_only(m)
    m.setw(C.SEED, (0x9E37 * (n + 1)) & 0xFFFF or 1)
    m.setw(C.SEED + 2, (0x7F4A * (n + 3)) & 0xFFFF or 1)
    rows, cur, frame, still, last = [], None, 0, 0, None
    while m.w(GSP) < 3 and frame < 200000:
        e.run(1)
        frame += 1
        if frame % 600 == 0:
            C.computer_only(m)
            lowload.breathe()
        c = m.w(CLOCK)
        still = still + 1 if c == last and m.w(GMCLOCK) else 0
        last = c
        if still >= 900:
            e.run(4, hold=["START"]); frame += 4; still = 0
        pc = m.w(PUCKC)
        k = pc // 2 if pc < 24 else None
        goalie = k is not None and m.w(POSITION + 2 * k) == 0
        stopped = bool(m.w(GMCLOCK))
        if cur:
            if cur["anim_end"] is None and not m.w(PF2AIP + 2 * cur["k"]):
                cur["anim_end"] = frame - cur["start"]
            if stopped or not goalie or k != cur["k"]:
                cur["frames"] = frame - cur["start"]
                cur["end"] = "whistle" if stopped and goalie and k == cur["k"] else "release"
                rows.append({a: b for a, b in cur.items() if a != "start"})
                cur = None
        if goalie and cur is None and not stopped:
            cur = {"k": k, "start": frame, "temp5": s16(m.w(TEMP5 + 2 * k)), "spa": m.w(SPA + 2 * k),
                   "aip": m.w(PF2AIP + 2 * k), "anim_end": None}
    return dict(game=n, rom=Path(rom).name, pickups=rows, frames=frame)


def same(a, b):
    A = {json.loads(x)["game"]: json.loads(x) for x in Path(a).read_text().splitlines() if x.strip()}
    B = {json.loads(x)["game"]: json.loads(x) for x in Path(b).read_text().splitlines() if x.strip()}
    for n in sorted(set(A) & set(B)):
        ha, hb = A[n]["hashes"], B[n]["hashes"]
        first = next((i for i, (x, y) in enumerate(zip(ha, hb)) if x != y), None)
        print(f"game {n}: {len(ha)} / {len(hb)} hashes, first difference at "
              f"{'none' if first is None else f'{first * 600} frames'}; goals {A[n]['goals']} / {B[n]['goals']}, "
              f"shots {A[n]['shots']} / {B[n]['shots']}")


def report(paths):
    for p in paths:
        G = [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
        tick = Counter()
        for g in G:
            for st, d, v in g["ticks"]:
                tick[(st, d)] += v
        play = sorted(((d, v) for (st, d), v in tick.items() if st == "play"), key=lambda t: -t[1])[:3]
        other = Counter(st for (st, d), v in tick.items() for _ in range(v) if st != "play")
        box = [b for g in G for b in g["boxes"] if b["clock_s"]]
        print(f"{Path(p).stem}: {len(G)} games; clock ticks in play, frames apart (most common) {play}; ticks outside "
              f"play {dict(other)}")
        print(f"   period starts {[g['period_start'] for g in G][:3]}")
        print(f"   box stays (frames, clock s): {sorted((b['frames'], b['clock_s']) for b in box)[:12]}")
        print(f"   icing armed {sum(g['icing_armed'] for g in G)}, called {sum(g['icing_calls'] for g in G)}; stars came up "
              f"{sum(g['stars_frame'] is not None for g in G)}/{len(G)}; goals {[g['goals'] for g in G]}")
        for g in G:
            names = []
            for s in g["stars"]:
                if s >= 52:
                    names.append(f"?{s:#x}")
                    continue
                gl, a, sh = g["players"][s]
                team = "H" if s < 26 else "A"
                names.append(f"{team}{s % 26}({gl}g {a}a {sh}s)")
            print(f"   game {g['game']}: {' '.join(names)} scores {g['star_scores']}")


def main():
    part = sys.argv[1]
    if part == "same":
        same(sys.argv[2], sys.argv[3])
        return
    if part == "report":
        report(sys.argv[2:])
        return
    lowload.gentle()
    if part == "dive":
        rom, games, out = sys.argv[2], int(sys.argv[3]), Path(sys.argv[4])
        for n in range(games):
            r = dive_game(rom, n)
            with out.open("a") as fh:
                fh.write(json.dumps(r) + "\n")
            print(n, len(r["pickups"]), flush=True)
        return
    if part == "cvc":
        rom, games, out = sys.argv[2], int(sys.argv[3]), Path(sys.argv[4])
        first = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        for n in range(first, first + games):
            r = cvc_game(rom, n)
            with out.open("a") as fh:
                fh.write(json.dumps(r) + "\n")
            print(n, r["goals"], r["frames"], r["stars"], flush=True)
        return
    out = Path(sys.argv[2])
    fn = {"goalie": goalie_part, "skate": skate_part, "puck": puck_part}[part]
    for rom in sys.argv[3:]:
        G = Game(rom)
        for r in fn(G):
            r["rom"] = Path(rom).name
            with out.open("a") as fh:
                fh.write(json.dumps(r) + "\n")
            print(json.dumps(r), flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
