"""NHL '95 (Genesis): NOSE4Web's group 2 fixes played (2026-11-16): NHL 94's power-play / penalty-kill read, faceoff
spot, computer forwards' awareness and stick-deflection shot fixes at NHL '95's places. From gen95_assist_check's live
state per ROM (powered on first), the same presses on the original and the build.

Modes (python gen95_group2_check.py MODE OUT ORIG BUILD STATE [...]):
  pppk HOME AWAY   the team structs' data pointers (+$1E) set to two teams from the ROM's team table ($772: the
                   team's data + its +8 word; byte 1 the power-play / penalty-kill byte, high half PP, low half PK);
                   an away skater given the puck and called for hooking (a PenBuf entry): through the whistle to the
                   faceoff with the power play on (sflags2 sf2pwrplay): PPBonus ($FFCAF0) and PKBonus ($FFCAF1) as each
                   frame leaves them, and every skater's working ratings (+$67-$75) at the faceoff, original against
                   build."""
import json
import struct
import sys
from collections import Counter
from pathlib import Path

import gen95_organ_resume_check as O
import lowload

TEAMS_TABLE = 0x772
PPB, PKB, SFLAGS2, PENBUF, PUCKC = 0xCAF0, 0xCAF1, 0xBEF4, 0xBFCE, 0xB3C2
HOME, AWAY = 0xC288, 0xC5EE
PFL_ = 0x62
BASE, SZ = 0xAC62, 0x80


def rec(k):
    return BASE + k * SZ


def s8(v):
    return v - 256 if v >= 128 else v


def team_table(rom):
    out = []
    i = 0
    while True:
        p = struct.unpack_from(">I", rom, TEAMS_TABLE + 4 * i)[0]
        if not 0x200 < p < len(rom):
            break
        try:
            d = p + struct.unpack_from(">H", rom, p + 8)[0]
            no = struct.unpack_from(">H", rom, p + 4)[0]
            ln = struct.unpack_from(">H", rom, p + no)[0]
            name = rom[p + no + 2:p + no + min(ln, 30)].split(b"\x00")[0].decode("latin-1")
        except struct.error:
            break
        out.append(dict(i=i, name=name, ptr=p, byte=rom[d + 1]))
        i += 1
    return out


def pppk(rom, state, home_name, away_name):
    data = Path(rom).read_bytes()
    tt = {t["name"]: t for t in team_table(data)}
    h, a = tt[home_name], tt[away_name]
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    e.setl(HOME + 0x1E, h["ptr"])
    e.setl(AWAY + 0x1E, a["ptr"])
    k = next(k for k in range(6, 12) if e.b(rec(k) + 0x35) not in (0, 0xFF))   # an away skater
    e.setw(PUCKC, k)
    e.setw(PENBUF, 0x1E << 8 | k)                                             # hooking, on him
    e.setw(PENBUF + 2, 0)
    seen, after = Counter(), None
    pp_on_at = None
    for f in range(3000):
        e.run(1)
        if e.b(SFLAGS2) & 0x20 or e.w(SFLAGS2) & 0x2000:
            if pp_on_at is None:
                pp_on_at = f
            seen[(s8(e.b(PPB)), s8(e.b(PKB)))] += 1
        if pp_on_at is not None and f > pp_on_at + 30 and not e.w(O.GMODE) & 0x100:     # the clock running again
            after = [[e.b(rec(j) + o) for o in range(0x67, 0x76)] for j in range(12)]
            break
    return dict(home=(home_name, f"{h['byte']:02x}"), away=(away_name, f"{a['byte']:02x}"), pp_on_frame=pp_on_at,
                values_seen={str(k): v for k, v in seen.items()}, ratings=after, sflags2=f"{e.w(SFLAGS2):04x}")


LTX, LTY, FOX, FOY, GMODE = 0xBB82, 0xBB84, 0xBB9A, 0xBB9C, 0xBEF0
OOP, GHOLD, WHISTLE, ICING, GOAL, OFFSIDE = 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x10
CODES = [OOP, GHOLD, WHISTLE, ICING, OFFSIDE, 0x16, 0x18, 0x1A, 0x1C, 0x1E, 0x20, 0x22, 0x24]
PENALTIES = set(range(0x16, 0x2B))
POSITIONS = [(x, y) for x in (-100, -40, 40, 100) for y in (-250, -190, -140, -110, -70, -30, 30, 70, 110, 140, 190, 250)]
DOTS = {(0, 0)} | {(sx * 77, sy * 215) for sx in (-1, 1) for sy in (-1, 1)} | {(sx * 70, sy * 65) for sx in (-1, 1) for sy in (-1, 1)}


def sw(e, a):
    v = e.w(a)
    return v - 0x10000 if v >= 0x8000 else v


def fo_expected(code, raw, pfgoal):
    """The fix's rule (NOSE4Web's NHL 94 code at NHL '95's places, neutral dots +-70, +-65): a penalty to the
    offending team's own end dot on the puck's side; else past a blue line (|y| >= 87) that end's dot on the puck's
    side, in the neutral zone the nearest neutral dot (y 0 the top half); then limitfo for the entry's player (a spot
    past 86 toward the end he attacks moves to that side's neutral dot)."""
    x, y = raw
    if code == ICING:
        y = -600 if pfgoal else 600
    sx = 1 if x >= 0 else -1
    if code in PENALTIES:
        fx, fy = 77 * sx, (-215 if pfgoal else 215)
    elif abs(y) >= 87:
        fx, fy = 77 * sx, (215 if y > 0 else -215)
    else:
        fx, fy = 70 * sx, (65 if y >= 0 else -65)
    if pfgoal and fy > 86:
        fx, fy = 70 * sx, 65
    elif not pfgoal and fy < -86:
        fx, fy = 70 * sx, -65
    return fx, fy


def fo_trial(e, base, k, codes, x, y, extra=None):
    e.unserialize(base)
    for kk in (k, 14):
        e.setw(rec(kk), x & 0xFFFF)
        e.setw(rec(kk) + 0x14, y & 0xFFFF)
        e.setw(rec(kk) + 0x28, 0)
        e.setw(rec(kk) + 0x2A, 0)
    e.setw(PUCKC, k)
    e.setw(LTX, x & 0xFFFF)
    e.setw(LTY, y & 0xFFFF)
    e.setw(PENBUF, 0)
    e.run(2)
    puck = (sw(e, rec(14)), sw(e, rec(14) + 0x14))
    entries = [(c << 8 | kk) for c, kk in codes]
    for i, v in enumerate(entries + [0]):
        e.setw(PENBUF + 2 * i, v)
    e.setw(GMODE, e.w(GMODE) & ~0x0D00)
    pfgoal = bool(e.b(rec(k) + 0x62) & 0x80)
    for _ in range(6):
        e.run(1)
        if e.w(GMODE) & 0x0100:
            break
    else:
        return None
    return (sw(e, FOX), sw(e, FOY)), puck, (sw(e, LTX), sw(e, LTY)), pfgoal


def faceoff(rom, state):
    r = O.R(rom, state)
    e = r.e
    base = r.base
    rows = []
    for k in (3, 4, 9, 10):
        for code in CODES:
            for x, y in POSITIONS:
                t = fo_trial(e, base, k, [(code, k)], x, y)
                if t is None:
                    rows.append(dict(k=k, code=code, pos=(x, y), res="no stoppage"))
                    continue
                spot, puck, touch, pfgoal = t
                raw = touch if code == OOP else puck
                want = fo_expected(code, raw, pfgoal)
                near = abs(raw[0]) < 4 or any(abs(abs(raw[1]) - b) < 4 for b in (86, 87))
                rows.append(dict(k=k, code=code, pos=(x, y), raw=raw, spot=spot, want=want, on_dot=spot in DOTS,
                                 agree=spot == want, edge=near, pfgoal=pfgoal))
        lowload.breathe()
    # both teams penalised at one whistle: a home and an away skater, each code pair
    both = []
    for (x, y) in [(40, 30), (-40, -110), (100, 190), (-100, -250)]:
        t = fo_trial(e, base, 3, [(0x1A, 3), (0x1E, 9)], x, y)
        if t:
            both.append(dict(pos=(x, y), spot=t[0], on_dot=t[0] in DOTS))
    return rows, both


def delayed(rom, state):
    """A delayed penalty: an away skater called (PenBuf) while home has the puck; play on until an away player
    touches it, then the whistle: the spot."""
    r = O.R(rom, state)
    e = r.e
    out = []
    for x, y in [(40, 30), (-40, 120), (60, -150), (0, 200)]:
        e.unserialize(r.base)
        hk = 3
        for kk in (hk, 14):
            e.setw(rec(kk), x & 0xFFFF)
            e.setw(rec(kk) + 0x14, y & 0xFFFF)
        e.setw(PUCKC, hk)
        e.run(2)
        e.setw(PENBUF, 0x1E << 8 | 9)
        e.setw(PENBUF + 2, 0)
        delayed_seen, spot = False, None
        for f in range(1500):
            e.run(1)
            delayed_seen = delayed_seen or bool(e.w(GMODE) & 0x0800)
            if e.w(GMODE) & 0x0100 and delayed_seen and f > 5:
                spot = (sw(e, FOX), sw(e, FOY))
                break
        out.append(dict(pos=(x, y), delayed=delayed_seen, spot=spot, on_dot=spot in DOTS if spot else None))
    return out


def classify(t, off, de):
    if off == de:
        return "aioff = aidef"
    a, d = t in (off, off - 1), t in (de, de - 1)
    return "aioff" if a and not d else "aidef" if d and not a else "both" if a else "neither"


def aware(rom, state, frames):
    """awareness_test.py's count at NHL '95's places: nobody on a pad, every frame each computer winger or centre
    whose team has the puck, whose re-decision timer (+$40) jumps up (a reload), classified by which of aioff (+$6A)
    and aidef (+$6B) it equals (or one under: the crowd's quickening)."""
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    e.setw(0xBF4C, 0)
    e.setw(0xBF4E, 0)
    for k in range(12):
        e.setb(rec(k) + PFL_, e.b(rec(k) + PFL_) & ~8)
    out = Counter()
    last = [s8(e.b(rec(k) + 0x40)) for k in range(12)]
    for f in range(frames):
        e.run(1)
        pc = e.w(PUCKC)
        for k in range(12):
            t = s8(e.b(rec(k) + 0x40))
            lt, last[k] = last[k], t
            if e.b(rec(k) + 0x35) not in (3, 4, 5) or pc >= 0x8000 or pc // 6 != k // 6 or t <= lt + 1:
                continue
            out[classify(t, e.b(rec(k) + 0x6A), e.b(rec(k) + 0x6B))] += 1
        if f % 3000 == 2999:
            lowload.breathe()
    return out


CROWD = 0xB4BA
SHOOTER, AWAY_G = 2, 11


def park(e):
    for k in range(12):
        if k in (SHOOTER, AWAY_G):
            continue
        e.setw(rec(k), (-100 + 18 * k) & 0xFFFF)
        e.setw(rec(k) + 0x14, -230 & 0xFFFF)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(k) + off, 0)


AIMS = [None, ["UP"], ["UP", "LEFT"], ["UP", "RIGHT"], ["LEFT"], ["RIGHT"], ["DOWN"], ["DOWN", "LEFT"], ["DOWN", "RIGHT"]]


def struct_bytes(e):
    return [e.b(HOME + i) for i in range(2 * 0x366)]


def deflect_shot(e, base, rnd):
    """count_deflections_test's shot at NHL '95's places: the home shooter (pad 1) at a spot in front of the top
    net with the puck, everyone else parked but the away goalie, C held 3-12 frames with an aim, then 150 frames."""
    e.unserialize(base)
    e.setw(O.CLOCK, 250)
    e.setl(0xCC6A, rnd.getrandbits(32))
    x, y = rnd.choice((-60, -30, 0, 30, 60)), rnd.choice((150, 175, 200, 225))
    hold, aim = rnd.randint(3, 12), rnd.choice(AIMS)
    e.setw(0xBF4C, 1)
    for k in range(6):
        e.setb(rec(k) + PFL_, e.b(rec(k) + PFL_) & ~8)
    e.setb(rec(SHOOTER) + PFL_, e.b(rec(SHOOTER) + PFL_) | 8)
    e.setw(0xBF44, SHOOTER)
    for _ in range(60):
        e.setw(rec(SHOOTER), x & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x14, y & 0xFFFF)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(SHOOTER) + off, 0)
        park(e)
        e.setw(PUCKC, SHOOTER)
        e.run(1)
    s0 = struct_bytes(e)
    for f in range(80):
        park(e)
        e.run(1, hold=(["C"] if f < hold else []) + (aim or []))
        if e.w(PUCKC) >= 0x8000:
            break
    else:
        return None
    path = []
    for f in range(150):
        park(e)
        e.run(1)
        path.append((tuple(e.w(rec(k) + o) for k in (*range(12), 14) for o in (0, 0x14)), e.w(CROWD)))
    s1 = struct_bytes(e)
    up = [(("home" if i < 0x366 else "away") + f" +${i % 0x366:03X}", s1[i] - s0[i]) for i in range(len(s0)) if s1[i] != s0[i]]
    return dict(shots=e.w(HOME) - (s0[0] << 8 | s0[1]), up=up, path=path)


def deflect(orig, build, state, n):
    import random
    res = {}
    for name, rom in (("orig", orig), ("build", build)):
        r = O.R(rom, state)
        res[name] = [deflect_shot(r.e, r.base, random.Random(f"d{i}")) for i in range(n)]
        del r
        lowload.breathe()
    a, b = res["orig"], res["build"]
    both = [(x, y) for x, y in zip(a, b) if x and y]
    diff = [(x, y) for x, y in both if x["shots"] != y["shots"]]
    same_path = sum(x["path"] == y["path"] for x, y in both)
    print(f"{len(both)} shots on both ROMs; shots on goal counted: original {sum(x['shots'] for x, _ in both)}, build "
          f"{sum(y['shots'] for _, y in both)}; counted differently {len(diff)}; play (every skater, the puck, the crowd for "
          f"150 frames) the same {same_path} of {len(both)}", flush=True)
    kinds = Counter((x["shots"], y["shots"]) for x, y in diff)
    print("   (original, build) shots where they differ:", dict(kinds))
    ups = Counter()
    for x, y in diff:
        extra = sorted(set(map(tuple, y["up"])) - set(map(tuple, x["up"])))
        ups[tuple(extra)] += 1
    for k, v in ups.most_common(5):
        print(f"   bytes up on the build only ({v} shots): {list(k)}")
    paths_differ = [(x, y) for x, y in diff if x["path"] != y["path"]]
    print(f"   of those, play different afterwards: {len(paths_differ)}")


def main():
    mode, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    if mode == "deflect":
        orig, build, state, n = sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6])
        deflect(orig, build, state, n)
        return
    if mode == "aware":
        frames = int(sys.argv[-1])
        for rom, state in zip(sys.argv[3:-1:2], sys.argv[4:-1:2]):
            print(Path(rom).name, dict(aware(rom, state, frames)), flush=True)
        return
    if mode == "faceoff":
        orig, build, state = sys.argv[3:6]
        for name, rom in (("orig", orig), ("build", build)):
            rows, both = faceoff(rom, state)
            ok = [r for r in rows if "spot" in r]
            clean = [r for r in ok if not r["edge"]]
            print(f"{name}: {len(rows)} stoppages, {len(ok)} called; on a dot {sum(r['on_dot'] for r in ok)} of {len(ok)}; "
                  f"agree with the fix's rule {sum(r['agree'] for r in clean)} of {len(clean)} (away from boundaries)", flush=True)
            off = Counter(tuple(r["spot"]) for r in ok if not r["on_dot"])
            print("   spots not on a dot:", off.most_common(8))
            bad = [r for r in clean if not r["agree"]][:6]
            for r in bad:
                print("   differs:", {k: r[k] for k in ("k", "code", "pos", "raw", "spot", "want", "pfgoal")})
            by_code = Counter((r["code"], r["on_dot"]) for r in ok)
            print("   by code (code, on dot): count", sorted(by_code.items()))
            print("   both teams penalised:", both)
            print("   delayed penalty:", delayed(rom, state), flush=True)
        return
    if mode == "pppk":
        orig, build, state, home, away = sys.argv[3:8]
        res = {}
        for name, rom in (("orig", orig), ("build", build)):
            res[name] = pppk(rom, state, home, away)
            r = res[name]
            print(name, "home", r["home"], "away", r["away"], "PP on at frame", r["pp_on_frame"], "sflags2", r["sflags2"],
                  "(PPBonus, PKBonus) seen:", r["values_seen"], flush=True)
        a, b = res["orig"]["ratings"], res["build"]["ratings"]
        if a and b:
            for j in range(12):
                d = [y - x for x, y in zip(a[j], b[j])]
                if any(d):
                    print(f"  record {j} ({'home' if j < 6 else 'away'}): build - original by rating +$67..+$75: {d}")
            print("  (records with no difference not shown)")
        (out / f"pppk_{home}_{away}.json".replace(" ", "")).write_text(json.dumps(res))


if __name__ == "__main__":
    main()
