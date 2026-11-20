"""NOSE4Web's "goalie hold after a dive catch" (2026-11-20), NHL '94 and NHL '95 on the Genesis (the SNES's is
snes_gen_settings_check.py's goalie part). puckglue sets a goalie's count (temp5, +$48) when he takes the puck: 140
($8C, "Goalie hold time"), or 5 when his animation is SPAgdive (a catch in a dive); the option makes the 5 an amount.
assgoalie counts temp5 down by the frames (d7) while he holds and no animation runs, and calls the whistle at 0.

- `cvc ROM GAMES OUT [FIRST]`: computer games (NHL '94: gen_goalie_hold_check's set-up; NHL '95: gen95_ref_cvc's),
  shortest periods, penalties on. Every goalie pickup: temp5 on the first frame he has the puck (the value puckglue
  set, less a frame or two), his animation word (+$58), the frames he keeps it, and how it ends: the whistle (gmode's
  gmclock bit set while he still has it) or a release (a pass, a drop).
- `pad ROM STATE OUT`: from a live state (NHL '94: paths.STATE_TOP; NHL '95: a live state, the ROM powered on
  first), the home goalie made pad 1's (cont1team, c1playernum, the person flag), the others parked up the ice, a
  loose puck sliding at him from the side; pad 1 dives with A and a direction (doinput's goalie dive: SPAgdive,
  nopuck 8) and the puck reaches his stick in the dive (puckstick -> puckglue: a loose puck on the body of a diving
  goalie bounces off, puckgoalie's .chkanim, so a dive catch is always a stick catch). Then: nothing pressed (the
  frames from the catch to standing up, pfalock and pf2aip clear, and from standing up to the whistle), and B or C
  pressed 5, 25 or 100 frames after he stands up (released? who has the puck next).

python gen_dive_hold_check.py cvc ROM GAMES OUT [FIRST] | pad ROM STATE OUT | report OUT ..."""
import json
import sys
from collections import Counter
from pathlib import Path

import lowload
from emu import Emu

TEMP5, SPA, POS, PFLAGS = 0x48, 0x58, 0x35, 0x62
G94 = dict(BASE=0xB04A, PUCKC=0xB7AA, GMODE=0xC2EA, GSP=0xC466, CLOCK=0xC468, CONT=(0xC328, 0xC32A), SCREEN=0xFFF7)
G95 = dict(BASE=0xAC62, PUCKC=0xB3C2, GMODE=0xBEF0, GSP=0xC020, CLOCK=0xC022, CONT=(0xBF4C, 0xBF4E), SCREEN=None)
SZ = 0x80


def is95(rom):
    return Path(rom).stat().st_size > 0x180000 and b"NHL 95" in Path(rom).read_bytes()[0x100:0x200].replace(b"'", b"") \
        or "95" in Path(rom).name


def start(rom, n):
    if is95(rom):
        import gen95_ref_cvc as R
        import gen95_fight_check as F
        e = Emu(rom)
        F.to_setup(e)
        e.setb(F.ROW + 3, 0)
        e.setb(F.ROW + 6, 2)
        e.setb(F.ROW + 7, 1)
        e.run(6, hold=["START"]); e.run(300); e.run(6, hold=["START"]); e.run(60); e.run(1800)
        for _ in range(6):
            e.run(6, hold=["START"]); e.run(300)
        e.setl(R.SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
        return e, G95
    import gen_ot_check as G
    import gen_goalie_hold_check as H
    e = Emu(rom)
    G.to_setup(e, Path(rom).parent)
    e.setw(H.PERLEN, 0)
    e.setw(H.OPTPEN, 2)
    e.setw(H.OPTLINE, 1)
    if not G.into_play(e):
        return None, G94
    e.setl(H.SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    return e, G94


def cvc_game(rom, n):
    e, A = start(rom, n)
    if e is None:
        return {"game": n, "error": "never reached play"}
    B = A["BASE"]
    rows, cur = [], None
    frame, still, last = 0, 0, None
    while e.w(A["GSP"]) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            for c in A["CONT"]:
                e.setw(c, 0)
            for k in range(12):
                e.setb(B + SZ * k + PFLAGS, e.b(B + SZ * k + PFLAGS) & ~8)
            c = e.w(A["CLOCK"])
            still = still + 1 if c == last else 0
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
        e.run(1, hold=["START"] if still >= 8 and frame % 60 < 2 else [])
        frame += 1
        if A["SCREEN"] is not None and e.b(A["SCREEN"]) != 0:
            continue
        pc = e.w(A["PUCKC"])
        carrier = None if pc & 0xFF00 else pc
        goalie = carrier is not None and carrier < 12 and e.b(B + SZ * carrier + POS) == 0
        stopped = bool(e.w(A["GMODE"]) & 0x100)
        if cur and (not goalie or carrier != cur["k"] or stopped):
            cur["frames"] = frame - cur["start"]
            cur["end"] = "whistle" if stopped and goalie and carrier == cur["k"] else "release"
            rows.append(cur)
            cur = None
        if goalie and cur is None and not stopped:
            r = B + SZ * carrier
            cur = {"k": carrier, "start": frame, "temp5": e.sw(r + TEMP5), "spa": e.w(r + SPA)}
    return {"game": n, "rom": Path(rom).name, "pickups": [{k: v for k, v in r.items() if k != "start"} for r in rows],
            "frames": frame}


def pad_setup(e, base, A, dx, dy, vy):
    """From the live state: the home goalie made pad 1's (cont1team, c1playernum, the person flag), the others parked
    up the ice, the puck loose and sliding at him: dx to his side, dy out from him, vy toward the goal line."""
    B = A["BASE"]
    e.unserialize(base)
    k = next(j for j in range(6) if e.b(B + SZ * j + POS) == 0)
    e.setw(A["CONT"][0], 1)
    e.setw(A["CONT"][1], 0)
    e.setw(A["C1P"], k)
    for j in range(12):
        e.setb(B + SZ * j + PFLAGS, (e.b(B + SZ * j + PFLAGS) & ~8) | (8 if j == k else 0))
    gx, gy = e.sw(B + SZ * k), e.sw(B + SZ * k + 0x14)
    own = 1 if gy > 0 else -1
    for j in range(12):
        if j != k and e.b(B + SZ * j + POS) != 0xFF:
            e.setw(B + SZ * j, (-100 + 18 * (j % 6)) & 0xFFFF)
            e.setw(B + SZ * j + 0x14, (-own * 150) & 0xFFFF)
    P = B + SZ * 14
    e.setw(A["PUCKC"], 0xFFFF)
    e.setb(P + 0x60, 0xFF)
    e.setw(P, (gx + dx) & 0xFFFF); e.setw(P + 0x14, (gy - own * dy) & 0xFFFF); e.setw(P + 0x18, 0)
    e.setw(P + 0x28, 0); e.setw(P + 0x2A, (own * vy) & 0xFFFF); e.setw(P + 0x2C, 0)
    return k


def pad_trial(e, base, A, setup, button=None, after=None, frames=900):
    """setup (dx, dy, vy, press): pad 1 holds RIGHT / LEFT (toward the puck's side) and presses A at frame press: the
    dive (SPAgdive). Then from the catch: when he stands up (the animation lock, pfalock, and pf2aip clear), the
    whistle (gmode's gmclock bit) or, with a button (B or C) pressed `after` frames after he stands up, the release
    and who has the puck next."""
    B = A["BASE"]
    dx, dy, vy, press = setup
    k = pad_setup(e, base, A, dx, dy, vy)
    r = B + SZ * k
    d = "RIGHT" if dx > 0 else "LEFT"
    dive_spa, caught, up, whistle, released, nxt, t5 = None, None, None, None, None, None, None
    for f in range(frames):
        hold = []
        if caught is None:
            if press - 2 <= f < press + 10:
                hold.append(d)
            if press <= f < press + 2:
                hold.append("A")
        elif up is not None and button and after is not None and up + after <= f < up + after + 4:
            hold.append(button)
        if released is None:
            e.setw(A["C1P"], k)
        e.run(1, hold=hold)
        if f == press + 3:
            dive_spa = e.w(r + SPA)
        pc = e.w(A["PUCKC"])
        if caught is None:
            if pc == k:
                caught, t5, spa_at = f, e.sw(r + TEMP5), e.w(r + SPA)
                if spa_at != dive_spa:
                    return dict(dive=False, spa_at_catch=hex(spa_at), dive_spa=hex(dive_spa or 0))
            elif f > press + 120:
                return dict(dive=None)
            continue
        if up is None and not (e.b(r + PFLAGS) & 0x20) and not (e.b(r + PFLAGS + 1) & 0x02):
            up = f
        if released is None:
            if e.w(A["GMODE"]) & 0x100:
                whistle = f
                break
            if pc != k:
                released = f
        elif pc < 12 and nxt is None:
            nxt = dict(rec=pc, team="own" if (pc < 6) == (k < 6) else "other", frames=f - released)
            break
        elif released is not None and f - released > 120:
            break
    rel = lambda v: None if v is None or up is None else v - up
    return dict(dive=True, temp5_at_catch=t5, up_after_catch=None if up is None else up - caught,
                whistle_after_up=rel(whistle), released_after_up=rel(released), next=nxt,
                button=button, pressed_after_up=after)


def pad(rom, state, out):
    """NHL '94 (its live state, paths.STATE_TOP) or NHL '95 (a live state; powered on first): pad 1's goalie catches
    a sliding puck in a dive. The first set-up that gives a dive catch on this ROM, then: nothing pressed, and B or C
    pressed some frames after he stands up."""
    if is95(rom):
        A = dict(G95, C1P=0xBF44)
        e = Emu(rom)
        e.run(1500)
        base = Path(state).read_bytes()
    else:
        A = dict(G94, C1P=0xC320)
        e = Emu(rom)
        base = Path(state).read_bytes()
    found = None
    for setup in [(40, 60, 0x1800, 8), (40, 40, 0x1000, 8), (40, 60, 0x1000, 12), (30, 90, 0x2400, 20),
                  (-40, 60, 0x1800, 8), (40, 90, 0x1800, 12), (22, 60, 0x1800, 8)]:
        r = pad_trial(e, base, A, setup, frames=200)
        if r.get("dive"):
            found = setup
            break
    rows = []
    if found is None:
        rows.append(dict(rom=Path(rom).name, error="no dive catch"))
    else:
        cases = [(None, None)] + [(b, a) for b in ("B", "C") for a in (5, 25, 100)]
        for b, a in cases:
            r = pad_trial(e, base, A, found, b, a)
            r.update(rom=Path(rom).name, setup=found)
            rows.append(r)
            print(json.dumps(r), flush=True)
            lowload.breathe()
    with open(out, "a") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def report(paths):
    for p in paths:
        G = [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
        G = [g for g in G if "pickups" in g]
        for rom in sorted({g["rom"] for g in G}):
            P = [r for g in G if g["rom"] == rom for r in g["pickups"]]
            # the value puckglue set: temp5 on his first frame is it less a frame or two
            kind = lambda r: "dive" if 0 <= r["temp5"] < 60 else "hold" if r["temp5"] >= 60 else "other"
            c = Counter((kind(r), r["end"]) for r in P)
            print(f"{rom}: {sum(1 for g in G if g['rom'] == rom)} games, {len(P)} goalie pickups: {dict(c)}")
            for kd in ("dive", "hold"):
                rr = [r for r in P if kind(r) == kd]
                if rr:
                    fr = sorted(r["frames"] for r in rr)
                    print(f"   {kd}: temp5 at pickup {Counter(r['temp5'] for r in rr).most_common(4)}, animation "
                          f"{Counter(hex(r['spa']) for r in rr).most_common(3)}; frames kept median {fr[len(fr) // 2]}, "
                          f"range {fr[0]}-{fr[-1]}; whistled {sum(r['end'] == 'whistle' for r in rr)}")


def main():
    if sys.argv[1] == "report":
        report(sys.argv[2:])
        return
    lowload.gentle()
    if sys.argv[1] == "pad":
        pad(sys.argv[2], sys.argv[3], sys.argv[4])
        return
    rom, games, out = sys.argv[2], int(sys.argv[3]), Path(sys.argv[4])
    first = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    for n in range(first, first + games):
        r = cvc_game(rom, n)
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(n, len(r.get("pickups", [])), r.get("error", ""), flush=True)


if __name__ == "__main__":
    main()
