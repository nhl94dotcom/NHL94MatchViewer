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

2026-11-21 (NOSE4Web's follow-up): also "x", by period and end: hook / hold starts (any computer skater entering a hook
or hold animation; the end named by the net his opponents attack) with the hooker's assignment and position, the
nearest opponent's travel (from behind / in front, heading to the net or not); burst starts ($0C5E), defending (his
team without the puck) or attacking, and defending ones within 40 of and facing an opponent; penalties drawn (a team's
stat-block penalty count going up, drawn by the other team at the end it attacks); each chance's defender assignment
and every skater's assignment every 2nd frame. The report gives Down / Up with 95% ranges from resampling whole games.

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
BURST = 0x0C5E
PEN_COUNT = (0xC6CE + 6, 0xCA32 + 6)         # each team's penalties (stat block +$06): Home, Away


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
    x = Counter()                             # 2026-11-21 (NOSE4Web): starts, penalties, assignments, by period and end
    prev_anim = None
    pens = [e.w(a) for a in PEN_COUNT]
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
        per = e.w(GSP)
        if per < 3:
            for t in (0, 1):                      # a penalty on team t is drawn by the other team, at the end it attacks
                c = e.w(PEN_COUNT[t])
                if 0 < c - pens[t] < 4:
                    d = 1 - t
                    pend = "Up" if (d == 0) == (per % 2 == 0) else "Down"
                    x[f"P{per + 1} {pend} pen"] += c - pens[t]
                    x[f"{pend} pen"] += c - pens[t]
                pens[t] = c
        if e.b(SCREEN) != 0 or still:
            prev_flail = [False] * 12
            prev_anim = None
            hist.clear()
            continue
        rec = [BASE + SZ * k for k in range(12)]
        pos = [e.b(r + 0x35) for r in rec]
        anim = [e.w(r + 0x58) for r in rec]
        xy = [(e.sw(r), e.sw(r + 0x14)) for r in rec]
        face = [e.b(r + 0x55) & 7 for r in rec]
        ass = [e.b(r + 0x38 + e.w(r + 0x36)) if e.w(r + 0x36) < 8 else 255 for r in rec]
        pc = e.w(PUCKC)
        hist.append((anim, pos, ass, pc))
        # the end a skater defends, named by the net his opponents attack (home attacks up in periods 1 and 3)
        dend = ["Up" if (k >= 6) == (per % 2 == 0) else "Down" for k in range(12)]
        if prev_anim is not None:
            for k in range(12):
                if pos[k] in (0, 0xFF) or anim[k] == prev_anim[k]:
                    continue
                a_name = ASS[ass[k]] if ass[k] < len(ASS) else str(ass[k])
                opps = [v for v in (range(6, 12) if k < 6 else range(6)) if pos[v] not in (0, 0xFF)]
                near = min(opps, key=lambda v: abs(xy[v][0] - xy[k][0]) + abs(xy[v][1] - xy[k][1]), default=None)
                if anim[k] in HOOK | HOLD and prev_anim[k] not in HOOK | HOLD:
                    end = dend[k]
                    x[f"P{per + 1} {end} hookstart"] += 1
                    x[f"{end} hookstart"] += 1
                    x[f"{end} hookstart {a_name}"] += 1
                    x[f"{end} hookstart {POS.get(pos[k], '?')}"] += 1
                    if near is not None:
                        dx, dy = xy[k][0] - xy[near][0], xy[k][1] - xy[near][1]
                        vx, vy = e.sw(rec[near] + 0x28), e.sw(rec[near] + 0x2A)
                        if vx or vy:
                            x[f"{end} hookstart {'from behind' if dx * vx + dy * vy < 0 else 'from in front'}"] += 1
                        sgn = 1 if end == "Up" else -1
                        x[f"{end} hookstart victim {'heading to the net' if vy * sgn > 0 else 'not heading to the net'}"] += 1
                if anim[k] == BURST and prev_anim[k] != BURST:
                    defending = not (0 <= pc < 12 and (pc < 6) == (k < 6))
                    end = dend[k] if defending else ("Up" if dend[k] == "Down" else "Down")
                    kind = "burst def" if defending else "burst off"
                    x[f"P{per + 1} {end} {kind}"] += 1
                    x[f"{end} {kind}"] += 1
                    if defending and near is not None:
                        dx, dy = xy[near][0] - xy[k][0], xy[near][1] - xy[k][1]
                        if abs(dx) <= 40 and abs(dy) <= 40:
                            x[f"{end} burst def near"] += 1
                            if vtoa(dx, dy) == face[k]:
                                x[f"{end} burst def facing"] += 1
        prev_anim = anim
        if frame % 2 == 0:
            for k in range(12):
                if pos[k] not in (0, 0xFF):
                    x[f"{dend[k]} on {ASS[ass[k]] if ass[k] < len(ASS) else ass[k]}"] += 1
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
                        x[f"{end} chance {ASS[ass[k]] if ass[k] < len(ASS) else ass[k]}"] += 1
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
    return {"game": n, "periods": e.w(GSP), "frames": frame, "opp": dict(opp), "hooks": dict(hooks), "x": dict(x),
            "listed": listed}


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
        if any("x" in r for r in R):
            report_x(R)


def _boot(R, num, den=None, n=2000):
    """Down / Up of a count (or of num per den), with a 95% range from resampling whole games."""
    import random
    def ratio(rs):
        X = Counter()
        for r in rs:
            X.update(r.get("x", {}))
            X.update({"opp " + k: v for k, v in r.get("opp", {}).items()})
        u, d = X["Up " + num], X["Down " + num]
        if den:
            uu, dd = X["Up " + den] or X["opp Up " + den], X["Down " + den] or X["opp Down " + den]
            return (d / dd) / (u / uu) if u and uu and dd else float("nan"), u, d
        return d / u if u else float("nan"), u, d
    est, u, d = ratio(R)
    rnd = random.Random(1)
    bs = sorted(v for v in (ratio([rnd.choice(R) for _ in R])[0] for _ in range(n)) if v == v)
    lo, hi = (bs[int(0.025 * len(bs))], bs[int(0.975 * len(bs)) - 1]) if bs else (float("nan"),) * 2
    return est, lo, hi, u, d


def report_x(R):
    """NOSE4Web's 2026-11-21 questions: hook / hold and burst starts by period and end, penalties drawn, the
    assignments' chances; Down / Up with 95% ranges (whole games resampled)."""
    X = Counter()
    for r in R:
        X.update(r.get("x", {}))
    print("  by period (Up / Down):")
    for per in (1, 2, 3):
        print(f"    P{per}: hook starts {X[f'P{per} Up hookstart']} / {X[f'P{per} Down hookstart']}, defending bursts "
              f"{X[f'P{per} Up burst def']} / {X[f'P{per} Down burst def']}, penalties drawn {X[f'P{per} Up pen']} / "
              f"{X[f'P{per} Down pen']}")
    rows = [("hook and hold starts", "hookstart", None), ("  by defencemen", "hookstart D", None),
            ("  on assdefd", "hookstart assdefd", None), ("  on assnearest", "hookstart assnearest", None),
            ("  per chance (any defender facing)", "hookstart", "any"),
            ("defending bursts", "burst def", None), ("  near and facing an opponent", "burst def facing", None),
            ("attacking bursts", "burst off", None), ("penalties drawn", "pen", None),
            ("chances (facing within 30), any", "any", None),
            ("  assdefd's", "chance assdefd", None), ("  assnearest's", "chance assnearest", None),
            ("samples on assdefd", "on assdefd", None), ("samples on assnearest", "on assnearest", None)]
    for label, num, den in rows:
        if num == "any":
            O = Counter()
            for r in R:
                O.update(r.get("opp", {}))
            u, d = O["Up any"], O["Down any"]
            print(f"  {label:38s} Up {u:7d} Down {d:7d}  Down/Up {d / max(u, 1):.3f}")
            continue
        est, lo, hi, u, d = _boot(R, num, den)
        print(f"  {label:38s} Up {u:7d} Down {d:7d}  Down/Up {est:.3f} ({lo:.2f}-{hi:.2f})")
    for end in ("Up", "Down"):
        h, b = X[f"{end} hookstart"], X[f"{end} burst def facing"]
        print(f"  {end}: hook share of hook starts + facing defending bursts {h / max(h + b, 1):.1%}; hooks from behind "
              f"{X[f'{end} hookstart from behind']}, from in front {X[f'{end} hookstart from in front']}; victim heading "
              f"to the net {X[f'{end} hookstart victim heading to the net']} of {h}")


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
