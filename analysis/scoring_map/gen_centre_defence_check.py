"""NOSE4Web's computer centres' defence fix (2026-11-18; chaos's forum topic "Player Assignments - Center"): in
asscenterd, with the puck outside his zone, the centre's target y should be halfway between his own high slot and the
puck, in his own end's frame. The code adds the raw (pucky) where it should add d2 (pucky flipped to his end), so for a
centre whose pfgoal is clear (shooting at the bottom net) the target is mirrored about y 64: (128 - pucky) / 2 for
(128 + pucky) / 2. The fix: add.w (pucky).w,d1 -> add.w d2,d1; nop (NHL '94 $D27A, NHL '95 / W18 $80E14).

In his own end's frame (his net at -y; p the puck's y there): the fixed target is (SLOT + p) / 2, the bug's for a
pfgoal-clear centre (SLOT - p) / 2. Each sample with the other team carrying or the puck loose, the clock running and
the puck outside his zone (p >= ZONE), the centre's own-frame y against both (the puck LAG samples earlier: he skates
toward the target), by the end he attacks.

  recorded DIR ...                    NHL '94: cvc_record.py's games (DIR/matches/*.js; role 4 = centre; the end each
                                      team attacks from the period: home up in periods 1 and 3)
  live 94|95 FRAMES GAMES ROM STATE [ROM STATE ...]   NHL '94 (STATE -: from power-on, cvc_record's matchups) or
                                      NHL '95 / W18: from a live state (gen95_assist_check's), nobody on a pad, every
                                      frame from RAM (pfgoal = pflags bit 7, gmode bit 0 the clock stopped; only a
                                      centre on asscenterd: 94 assignment 5, 95 $A; in his zone he should hold the
                                      slot); NHL '95's
                                      asscenterd takes its .cover path whenever someone carries the puck (HmDefMode /
                                      AwDefMode are 1 from Opening2 on), so the carried and loose cases are kept apart

python gen_centre_defence_check.py recorded DIR ... | live 94|95 FRAMES GAMES ROM STATE [ROM STATE ...]"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
LAG = 20


def report(name, res, slot):
    print("==", name, flush=True)
    for key in sorted(res):
        a = np.array(res[key])
        if not len(a):
            continue
        ef, eb = np.abs(a[:, 0] - a[:, 1]), np.abs(a[:, 0] - a[:, 2])
        far = a[:, 3] > 40                       # the puck well up the ice: where the two targets part most
        line = (f"  {key:18s} samples {len(a):6d}; median distance to the fixed target {np.median(ef):5.1f}, to the bug's "
                f"{np.median(eb):5.1f}; within 25 of the fixed {np.mean(ef < 25):4.0%}, of the bug's {np.mean(eb < 25):4.0%}")
        if far.sum():
            line += (f"; puck past +40: centre median {np.median(a[far, 0]):6.1f} (fixed {np.median(a[far, 1]):6.1f}, "
                     f"bug {np.median(a[far, 2]):6.1f})")
        if a.shape[1] > 4:                      # the two targets either side of him, skating (|Yvel| > 1000): toward which
            split = ((a[:, 1] - a[:, 0]) * (a[:, 2] - a[:, 0]) < 0) & (np.abs(a[:, 4]) > 1000)
            if split.sum():
                tofix = np.sign(a[split, 4]) == np.sign(a[split, 1] - a[split, 0])
                line += f"; targets either side ({int(split.sum())}): skating toward the fixed {tofix.mean():.0%}"
        print(line, flush=True)


def recorded(dirs, slot=-128, zone=-88):
    import season
    for d in dirs:
        res = defaultdict(list)
        for p in sorted(Path(d, "matches").glob("*.js")):
            if p.name == "season.js":
                continue
            m = season.load_match(p)
            P, own, pos, role, per = m["puck"], m["owner"], m["pos"], m["role"], m["period"]
            for i in range(LAG, len(m["t"])):
                if P[3 * i + 2] < -100 or P[3 * (i - LAG) + 2] < -100:
                    continue
                for team in (0, 1):
                    up = (team == 0) == (per[i] % 2 == 0)
                    o = own[i - LAG]
                    if o >= 0 and o // 6 == team:
                        continue
                    pp = P[3 * (i - LAG) + 1] * (1 if up else -1)
                    if pp < zone:
                        continue
                    k = next((k for k in range(team * 6, team * 6 + 6) if role[i * 12 + k] == "4"), None)
                    if k is None:
                        continue
                    y = pos[(i * 12 + k) * 2 + 1] * (1 if up else -1)
                    key = f"attacking {'up' if up else 'down'} {'loose' if o < 0 else 'carried'}"
                    res[key].append((y, (slot + pp) / 2, (slot - pp) / 2, pp))
        report(d, res, slot)


GAMES = {   # record base, pucky, puckc, gmode, asscenterd's assignment number, own high slot, own blue line
    "94": dict(base=0xB04A, pucky=0xB75E, puckc=0xB7AA, gmode=0xC2EA, ass=5, slot=-128, zone=-88),
    "95": dict(base=0xAC62, pucky=0xB376, puckc=0xB3C2, gmode=0xBEF0, ass=0xA, slot=-126, zone=-86),
}


def live(game, rom, state, frames, n=0):
    """NHL '94 (state "-": power-on, Game Setup, the league's settings, cvc_record's matchup n and seed) or NHL '95 /
    W18 (STATE: gen95_assist_check's live state): the computer on both sides, every frame from RAM; only a centre whose
    current assignment (asslist +$38 at assnum +$36) is asscenterd."""
    import lowload
    from emu import Emu
    g = GAMES[game]
    BASE, SZ = g["base"], 0x80
    s16 = lambda v: v - 65536 if v >= 32768 else v          # noqa: E731
    if game == "94":
        import gen_ot_check as G
        from cvc_record import teams_for
        e = Emu(rom)
        G.to_setup(e, Path(__file__).parent)
        h, a = teams_for(n)
        for addr, v in ((0xC330, h), (0xC332, a), (0xD050, 0), (0xD056, 2), (0xD058, 1)):
            e.setw(addr, v)
        if not G.into_play(e):
            return
        e.setl(0xD066, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
        pads = (0xC328, 0xC32A)
    else:
        import gen95_organ_resume_check as O
        r = O.R(rom, state)
        e = r.e
        e.unserialize(r.base)
        pads = (0xBF4C, 0xBF4E)
    res, hist, still, last = defaultdict(list), [], 0, None
    for f in range(frames):
        if f % 60 == 0:                                    # nobody on a pad (cvc_record's way)
            for a in pads:
                e.setw(a, 0)
            for k in range(12):
                e.setb(BASE + k * SZ + 0x62, e.b(BASE + k * SZ + 0x62) & ~8)
            if game == "94":
                c = e.w(0xC468)
                still = still + 1 if c == last else 0
                last = c
        e.run(1, hold=["START"] if game == "94" and still >= 8 and f % 60 < 4 else [])
        stopped = e.b(g["gmode"]) & 1                      # btst #gmclock,(gmode).w: the byte's bit 0
        hist.append((s16(e.w(g["pucky"])), e.w(g["puckc"]), stopped))
        if len(hist) <= LAG or stopped or hist[-1 - LAG][2]:
            continue
        py, pc, _ = hist[-1 - LAG]
        for team in (0, 1):
            if pc < 0x8000 and pc // 6 == team:
                continue
            k = next((k for k in range(team * 6, team * 6 + 6) if e.b(BASE + k * SZ + 0x35) == 4), None)
            if k is None or e.b(BASE + k * SZ + 0x38 + e.w(BASE + k * SZ + 0x36)) != g["ass"]:
                continue
            up = bool(e.b(BASE + k * SZ + 0x62) & 0x80)
            pp = py * (1 if up else -1)
            y = s16(e.w(BASE + k * SZ + 0x14)) * (1 if up else -1)
            vy = s16(e.w(BASE + k * SZ + 0x2A)) * (1 if up else -1)
            loose = "loose" if pc >= 0x8000 else "carried"
            if pp < g["zone"]:
                res[f"in his zone {'up' if up else 'down'}"].append((y, g["slot"], g["slot"], pp, vy))
                continue
            res[f"attacking {'up' if up else 'down'} {loose}"].append((y, (g["slot"] + pp) / 2, (g["slot"] - pp) / 2, pp, vy))
        if f % 3000 == 2999:
            lowload.breathe()
    return res


def main():
    import lowload
    lowload.gentle()
    if sys.argv[1] == "recorded":
        recorded(sys.argv[2:])
    elif sys.argv[1] == "live":                         # live 94|95 FRAMES GAMES ROM STATE [ROM STATE ...]
        game, frames, games = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        args = sys.argv[5:]
        for rom, state in zip(args[0::2], args[1::2]):
            tot = defaultdict(list)
            for n in range(games):
                for k, v in (live(game, rom, state, frames, n) or {}).items():
                    tot[k] += v
            report(Path(rom).name, tot, GAMES[game]["slot"])


if __name__ == "__main__":
    main()
