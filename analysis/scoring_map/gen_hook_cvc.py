"""Computer hooks and holds by end in computer-against-computer games, any ROM (Genesis NHL '94, 2026-11-19; the
Down lean of computer defenders' hooks in the recordings: is it the computer's own, and does NOSE4Web's
centreDefenceFix change it?).

Each game: power-on to Game Setup (gen_ot_check.to_setup), line changes off, the shortest periods, penalties on,
START into play, the seed $D066 from the game's number, the computer on both sides (cont1team / cont2team cleared and
the person flag taken off every second), three periods. Every other frame of play: opportunities, a defender (not a
goalie) within +-30 in x and y of an opponent skater and facing him exactly (facedir +$55 == vtoa, check4check's
test), per pair, against anyone and against the carrier; every frame: a skater going into the flail animation ($0CF4),
its catcher the opponent in a hold ($0C90 / $0CC2) or hook ($1122 / $1154) animation within 40 frames before; at the
frame before his hold or hook began: his position, assignment (asslist +$38 at assnum +$36), animation, and whether
the victim had the puck. End: the net the victim's team attacks (home attacks up in periods 1 and 3).

python gen_hook_cvc.py ROM GAMES OUT.jsonl [FIRST]   |   python gen_hook_cvc.py report OUT.jsonl [OUT2.jsonl]"""
import json
import sys
from collections import Counter, deque
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hook_by_end import ASS, POS, vtoa  # noqa: E402

PERLEN, OPTPEN, OPTLINE = 0xD050, 0xD056, 0xD058
SEED, CONT1, CONT2, GSP, CLOCK, SCREEN, PUCKC = 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7, 0xB7AA
BASE, SZ = 0xB04A, 0x80
FLAIL, HOLD, HOOK = 0x0CF4, {0x0C90, 0x0CC2}, {0x1122, 0x1154}


def game(rom, n):
    e = Emu(rom)
    G.to_setup(e, Path(rom).parent)
    e.setw(PERLEN, 0)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    opp, hooks, listed = Counter(), Counter(), []
    hist = deque(maxlen=60)                   # per frame: (anims, positions, facings, assignments, puckc)
    prev_flail = [False] * 12
    frame, still, last = 0, 0, None
    while e.w(GSP) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
        e.run(1, hold=["START"] if still >= 8 and frame % 60 < 2 else [])
        frame += 1
        if e.b(SCREEN) != 0 or still:
            prev_flail = [False] * 12
            hist.clear()
            continue
        per = e.w(GSP)
        rec = [BASE + SZ * k for k in range(12)]
        pos = [e.b(r + 0x35) for r in rec]
        anim = [e.w(r + 0x58) for r in rec]
        xy = [(e.sw(r), e.sw(r + 0x14)) for r in rec]
        face = [e.b(r + 0x55) & 7 for r in rec]
        ass = [e.b(r + 0x38 + e.w(r + 0x36)) if e.w(r + 0x36) < 8 else 255 for r in rec]
        pc = e.w(PUCKC)
        hist.append((anim, pos, ass, pc))
        if frame % 2 == 0:
            for k in range(12):
                if pos[k] in (0, 0xFF):
                    continue
                for v in (range(6, 12) if k < 6 else range(6)):
                    if pos[v] in (0, 0xFF):
                        continue
                    dx, dy = xy[v][0] - xy[k][0], xy[v][1] - xy[k][1]
                    if abs(dx) <= 30 and abs(dy) <= 30 and vtoa(dx, dy) == face[k]:
                        end = "Up" if (v < 6) == (per % 2 == 0) else "Down"
                        opp[f"{end} any"] += 1
                        if pc == v:
                            opp[f"{end} carrier"] += 1
        for v in range(12):
            now = anim[v] == FLAIL and pos[v] not in (0, 0xFF)
            if now and not prev_flail[v]:
                H = list(hist)
                found = None
                for j in range(len(H) - 1, max(-1, len(H) - 41), -1):
                    for k2 in (range(6, 12) if v < 6 else range(6)):
                        if H[j][0][k2] in HOLD or H[j][0][k2] in HOOK:
                            found = (j, k2, "hold" if H[j][0][k2] in HOLD else "hook")
                            break
                    if found:
                        break
                if found:
                    j, k2, kind = found
                    while j > 0 and (H[j - 1][0][k2] in HOLD or H[j - 1][0][k2] in HOOK):
                        j -= 1
                    b4 = H[j - 1] if j > 0 else H[j]
                    end = "Up" if (v < 6) == (per % 2 == 0) else "Down"
                    carrier = b4[3] == v
                    hooks[f"{end} any"] += 1
                    hooks[f"{end} {kind}"] += 1
                    hooks[f"{end} {POS.get(b4[1][k2], '?')}"] += 1
                    a = b4[2][k2]
                    hooks[f"{end} {ASS[a] if a < len(ASS) else a}"] += 1
                    if carrier:
                        hooks[f"{end} carrier"] += 1
                    if len(listed) < 30:
                        listed.append(dict(frame=frame, period=per + 1, end=end, hooker=k2, pos=POS.get(b4[1][k2], "?"),
                                           assignment=ASS[a] if a < len(ASS) else a, before=f"${b4[0][k2]:04X}",
                                           kind=kind, victim_carrier=carrier))
            prev_flail[v] = now
    return {"game": n, "periods": e.w(GSP), "frames": frame, "opp": dict(opp), "hooks": dict(hooks), "listed": listed}


def report(paths):
    for p in paths:
        R = [json.loads(line) for line in open(p) if line.strip()]
        O, Hk = Counter(), Counter()
        for r in R:
            O.update(r.get("opp", {}))
            Hk.update(r.get("hooks", {}))
        print(f"== {p}: {len(R)} games")
        for who in ("any", "carrier"):
            ou, od, hu, hd = O[f"Up {who}"], O[f"Down {who}"], Hk[f"Up {who}"], Hk[f"Down {who}"]
            ratio = (hd / od) / (hu / ou) if ou and od and hu else float("nan")
            print(f"  against {who:7s}: opportunities Up {ou} Down {od} ({od / max(ou, 1):.3f}); hooks Up {hu} Down {hd}; "
                  f"hooks per opportunity Down/Up {ratio:.3f}")
        keys = sorted({k.split(" ", 1)[1] for k in Hk} - {"any", "carrier"})
        for k in keys:
            print(f"    {k:14s} Up {Hk['Up ' + k]:4d} Down {Hk['Down ' + k]:4d}")


def main():
    if sys.argv[1] == "report":
        report(sys.argv[2:])
        return
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    lowload.gentle()
    done = set()
    if out.exists():
        done = {json.loads(line)["game"] for line in open(out) if line.strip()}
    for n in range(first, first + games):
        if n in done:
            continue
        r = game(rom, n)
        with open(out, "a") as f:
            f.write(json.dumps(r) + "\n")
        print(n, r.get("hooks"), flush=True)
    report([out])


if __name__ == "__main__":
    main()
