"""NOSE4Web's "goalie hold after a dive catch" (2026-11-20), NHL '94 and NHL '95 on the Genesis (the SNES's is
snes_gen_settings_check.py's goalie part). puckglue sets a goalie's count (temp5, +$48) when he takes the puck: 140
($8C, "Goalie hold time"), or 5 when his animation is SPAgdive (a catch in a dive); the option makes the 5 an amount.
assgoalie counts temp5 down by the frames (d7) while he holds and no animation runs, and calls the whistle at 0.

- `cvc ROM GAMES OUT [FIRST]`: computer games (NHL '94: gen_goalie_hold_check's set-up; NHL '95: gen95_ref_cvc's),
  shortest periods, penalties on. Every goalie pickup: temp5 on the first frame he has the puck (the value puckglue
  set, less a frame or two), his animation word (+$58), the frames he keeps it, and how it ends: the whistle (gmode's
  gmclock bit set while he still has it) or a release (a pass, a drop).
- `person ROM OUT [SPA]`: the home goalie made pad 1's (cont1team, c1playernum, the person flag), the others parked, the
  puck put on his stick while he's in a dive (SPA set to SPAgdive, its first frame, locked: the dive plays out),
  then: no buttons (the frames to the whistle, and from the dive's end), or the pass button (B) pressed a number of
  frames after the dive ends (released before the whistle?). A normal catch (no dive) as the control. SPA: SPAgdive's
  value (from the cvc rows' dive pickups); NHL '94 only (from its live state).

python gen_dive_hold_check.py cvc ROM GAMES OUT [FIRST] | person ROM OUT SPA | report OUT ..."""
import json
import sys
from collections import Counter
from pathlib import Path

import lowload
from emu import Emu

TEMP5, SPA, POS, PFLAGS = 0x48, 0x58, 0x35, 0x62
import os
BUTTON = os.environ.get("PASS_BUTTON", "B")
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


def person(rom, out, spa):
    """NHL '94, from its live state."""
    from paths import STATE_TOP
    A = G94
    B = A["BASE"]
    rows = []
    for case in [("dive", None), ("dive", 2), ("dive", 10), ("dive", 20), ("dive", 28), ("dive", 40), ("normal", None)]:
        e = Emu(rom)
        e.unserialize(open(STATE_TOP, "rb").read())
        k = next(j for j in range(6) if e.b(B + SZ * j + POS) == 0)
        for j in range(12):
            e.setb(B + SZ * j + PFLAGS, e.b(B + SZ * j + PFLAGS) & ~8)
        e.setb(B + SZ * k + PFLAGS, e.b(B + SZ * k + PFLAGS) | 8)
        e.setw(0xC328, 1)                       # cont1team: home
        e.setw(0xC32A, 0)
        e.setw(0xC320, k)                       # c1playernum
        gy = e.sw(B + SZ * k + 0x14)
        own = 1 if gy > 0 else -1
        for j in range(12):                     # the others far away
            if j != k and e.b(B + SZ * j + POS) != 0xFF:
                e.setw(B + SZ * j, (-100 + 18 * (j % 6)) & 0xFFFF)
                e.setw(B + SZ * j + 0x14, (-own * 150) & 0xFFFF)
        gx = e.sw(B + SZ * k)
        if case[0] == "dive":
            e.setw(B + SZ * k + SPA, spa)
            e.setw(B + SZ * k + 0x5A, 0)                                  # SPAnum: its first frame
            e.setb(B + SZ * k + PFLAGS, e.b(B + SZ * k + PFLAGS) | 0x20)  # locked while it plays
            e.setb(B + SZ * k + PFLAGS + 1, e.b(B + SZ * k + PFLAGS + 1) | 0x01)
        P = B + SZ * 14
        e.setw(P, gx & 0xFFFF); e.setw(P + 0x14, (gy - own * 4) & 0xFFFF); e.setw(P + 0x18, 0)
        e.setw(P + 0x28, 0); e.setw(P + 0x2A, 0)
        picked, t5, dive_end, whistle, released, f = None, None, None, None, None, 0
        for f in range(600):
            if picked is None and (f < 30 or e.b(B + SZ * k + PFLAGS) & 0x20):   # on his stick until he has it
                e.setw(P, e.w(B + SZ * k)); e.setw(P + 0x14, (e.sw(B + SZ * k + 0x14) - own * 4) & 0xFFFF)
            press = picked is not None and dive_end is not None and case[1] is not None and f == dive_end + case[1]
            press = press or (picked is not None and dive_end is not None and case[1] is not None and dive_end + case[1] <= f < dive_end + case[1] + 4)
            e.run(1, hold=[BUTTON] if press else [])
            pc = e.w(A["PUCKC"])
            if picked is None and pc == k:
                picked, t5 = f, e.sw(B + SZ * k + TEMP5)
            if picked is not None:
                if dive_end is None and not (e.b(B + SZ * k + PFLAGS) & 0x20):
                    dive_end = f
                if e.w(A["GMODE"]) & 0x100:
                    whistle = f
                    break
                if pc != k and released is None:
                    released = f
                    break
        rows.append(dict(rom=Path(rom).name, case=case[0], press_after_dive_end=case[1], picked=picked, temp5=t5,
                         dive_end=dive_end, whistle=whistle, released=released))
        print(rows[-1], flush=True)
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
    if sys.argv[1] == "person":
        person(sys.argv[2], sys.argv[3], int(sys.argv[4], 0))
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
