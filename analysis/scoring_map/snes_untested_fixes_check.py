"""NOSE4Web's SNES ppPkFix and hotColdFix, played (2026-11-21): each build against NHL94.smc, the same games and seeds.

setplayer (routines/collide/setplayer.asm) builds a player's working ratings when he comes on (faceoffs, line
changes, box exits). Each rating: a 3-bit roster value r, (r x 5) >> 1 (0-17), plus its bonuses, then `.8` adds the
player's hot / cold byte for that stat (HotColdTable $1A12 + team x 312 + roster index x 12 + stat) divided by 4 and
clamps to 0-15. The original divides with `lsr / lsr` on the byte, so a cold (negative) byte becomes 50-63 and the
rating 15 (the hot / cold bug); hotColdFix divides it signed. The power play (sflags $15D8 bit $2000, $4000 the
visitors' power play): PPBonus = the low nibble of the team's byte 1 (team data + the word at +8, then +1), the
penalty killers' PKBonus = minus its high nibble, added to aioff, stickhand, shotacc (passacc PP only); ppPkFix
takes the other nibble for each.

Each game: snes_60fps_cvc's set-up (Montreal at home against Los Angeles, 5-minute periods, penalties On, No Offside,
the computer on both sides, the seed from the game's number). At every faceoff (the clock running again: gmclock
$15D6 back to 0) 10 frames in: every on-ice object's team, position, roster index, working ratings, his 12 hot / cold
bytes, sflags and the boxes ($1624). Team data (bank $9C, through tmdata $1CDC / $1CDE): the roster bytes and the
team bytes.

python snes_untested_fixes_check.py ROM OUT.jsonl GAMES [FIRST]
python snes_untested_fixes_check.py report ORIG.jsonl BUILD.jsonl hotcold|pppk"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import lowload
import menu_shots as M
from snes_60fps_cvc import CLOCK, CLOCKSTOP, GSP, OPTPEN, SEED, Mem, computer_only

SFLAGS, INBOX, TMDATA, HOTCOLD, BANK = 0x15D8, 0x1624, 0x1CDC, 0x1A12, 0x9C
POS, PNUM, PFTEAM = 0x0F43, 0x12A3, 0x1503
# name: (array, stat, roster byte, high nibble?, bonuses outside period 3)
STATS = dict(legstr=(0x12E3, 0, 1, False, ""), legspd=(0x1303, 1, 2, True, ""), shotspd=(0x1363, 4, 3, False, ""),
             checking=(0x1483, 5, 4, True, ""), stickhand=(0x1403, 6, 5, True, "pp pk ha"),
             shotacc=(0x1383, 7, 5, False, "pp pk ha"), endurance=(0x1423, 8, 6, True, ""),
             spodds=(0x13E3, 9, 6, False, ""), aggress=(0x1443, 11, 7, False, ""))


def lorom(rom, bank, addr):
    return (bank & 0x7F) * 0x8000 + (addr - 0x8000)


def team_data(rom, td):
    a0 = lorom(rom, BANK, td)
    w = lambda o: rom[o] | rom[o + 1] << 8  # noqa: E731
    sr = a0 + w(a0 + 8)
    players, a = [], a0 + w(a0)
    for _ in range(30):
        n = w(a)
        if n == 0 or n > 64:
            break
        a += n + 8
        players.append(list(rom[a - 8:a]))
    return players, rom[sr + 1], rom[sr + 2]


def game(rom_path, n):
    rom = Path(rom_path).read_bytes()
    e = M.emulator(rom_path)
    m = Mem(e, rom_path)
    tmp = Path("x_tmp_untested")
    M.play(e, f"w{1500 + 53 * n} START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
    M.play(e, "START w240 START w200 w2400", tmp)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    m.setw(OPTPEN, 2)
    computer_only(m)
    m.setw(SEED, (0x9E37 * (n + 1)) & 0xFFFF or 1)
    m.setw(SEED + 2, (0x7F4A * (n + 3)) & 0xFFFF or 1)
    teams = [team_data(rom, m.w(TMDATA + 2 * t)) for t in (0, 1)]
    out = {"game": n, "roster": [t[0] for t in teams], "pppk": [t[1] for t in teams], "homeaway": [t[2] for t in teams],
           "faceoffs": []}
    frames, stopped, still, at_stop = 0, False, 0, None
    while m.w(GSP) < 3 and frames < 200000:
        c = m.w(CLOCK)
        e.run(1)
        frames += 1
        if m.w(CLOCKSTOP):
            if not stopped:
                at_stop = [m.w(PNUM + 2 * k) & 0xFF for k in range(12)]
            stopped = True
        elif stopped:
            stopped = False
            e.run(10)
            frames += 10
            recs = []
            for k in range(12):
                pos = m.w(POS + 2 * k)
                if pos == 0xFFFF:
                    continue
                team, pnum = (1 if m.w(PFTEAM + 2 * k) else 0), m.w(PNUM + 2 * k) & 0xFF
                hc0 = HOTCOLD + team * 312 + pnum * 12
                hc = [e.ram[hc0 + i] for i in range(12)]
                recs.append(dict(k=k, team=team, pos=pos, pnum=pnum, hc=hc, fresh=at_stop is None or at_stop[k] != pnum,
                                 **{s: m.w(arr + 2 * k) for s, (arr, *_r) in STATS.items()}))
            out["faceoffs"].append(dict(frame=frames, gsp=m.w(GSP), sflags=m.w(SFLAGS), box=m.w(INBOX), recs=recs))
        if frames % 300 == 0:
            computer_only(m)
            lowload.breathe()
            if m.w(CLOCK) > 300:
                m.setw(CLOCK, 300)
        still = still + 1 if m.w(CLOCK) == c else 0
        if still >= 900:
            e.run(4, hold=["START"])
            still = 0
    out["frames"] = frames
    return out


def expected(r, hc, signed):
    s = (r * 5) >> 1
    if signed:
        adj = hc >> 2 if hc < 0x80 else -((0x100 - hc) >> 2)
    else:
        adj = hc >> 2
    v = (s + adj) & 0xFF
    return 0 if v >= 0x80 else min(v, 15)


def load(path):
    return {r["game"]: r for r in (json.loads(x) for x in open(path) if x.strip())}


def report(orig, build, what):
    A, B = load(orig), load(build)
    print(f"{len(A)} / {len(B)} games")
    if what == "hotcold":
        for name, R in (("original", A), ("build", B)):
            tally = Counter()
            for r in R.values():
                for f in r["faceoffs"]:
                    for p in f["recs"]:
                        if p["pos"] == 0 or p["pnum"] >= len(r["roster"][p["team"]]):
                            continue
                        rec = r["roster"][p["team"]][p["pnum"]]
                        for s, (arr, stat, byte, hi, bon) in STATS.items():
                            if bon or (s in ("checking", "spodds") and f["gsp"] >= 2):
                                continue
                            raw = rec[byte]
                            rv = ((raw >> 4) if hi else raw) & 7
                            hc = p["hc"][stat]
                            cold = hc >= 0x80
                            got = p[s]
                            e_bug, e_fix = expected(rv, hc, False), expected(rv, hc, True)
                            key = ("cold" if cold else "hot/0",
                                   "as the bug" if got == e_bug and got != e_fix else
                                   "as signed" if got == e_fix and got != e_bug else
                                   "both agree" if got == e_bug == e_fix else f"neither")
                            tally[key] += 1
            print(f"  {name}: each bonus-free working rating against its roster value plus the hot / cold byte / 4")
            for k, v in sorted(tally.items()):
                print(f"    {k[0]:6s} {k[1]:12s} {v}")
    elif what == "pppk":
        for name, R, stat in [(n_, R_, st) for st in ("stickhand", "shotacc") for n_, R_ in (("original", A), ("build", B))]:
            tally = Counter()
            for r in R.values():
                even = defaultdict(Counter)
                for f in r["faceoffs"]:
                    if not f["sflags"] & 0x2000:
                        for p in f["recs"]:
                            even[(p["team"], p["pnum"])][p[stat]] += 1
                for f in r["faceoffs"]:
                    if not f["sflags"] & 0x2000:
                        continue
                    pp_team = 1 if f["sflags"] & 0x4000 else 0
                    for p in f["recs"]:
                        if p["pos"] == 0 or not p.get("fresh") or (p["team"], p["pnum"]) not in even:
                            continue
                        base = even[(p["team"], p["pnum"])].most_common(1)[0][0]
                        if base in (0, 15) or p[stat] in (0, 15):
                            tally[("PP" if p["team"] == pp_team else "PK", "clamped")] += 1
                            continue
                        byte = r["pppk"][p["team"]]
                        hi, lo = byte >> 4, byte & 15
                        role = "PP" if p["team"] == pp_team else "PK"
                        want = {"PP": {"low": lo, "high": hi}, "PK": {"low": -lo, "high": -hi}}[role]
                        d = p[stat] - base
                        hit = [k for k, v in want.items() if v == d]
                        tally[(role, "+".join(hit) if hit else f"other ({d:+d}; lo {lo} hi {hi})")] += 1
            print(f"  {name}, {stat}: on the power play / penalty kill minus at even strength, by the team byte")
            for k, v in sorted(tally.items()):
                print(f"    {k[0]} {k[1]:30s} {v}")


def main():
    if sys.argv[1] == "report":
        report(sys.argv[2], sys.argv[3], sys.argv[4])
        return
    rom, out, games = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    lowload.gentle()
    done = {json.loads(x)["game"] for x in open(out) if x.strip()} if out.exists() else set()
    for n in range(first, first + games):
        if n in done:
            continue
        r = game(rom, n)
        with open(out, "a") as f:
            f.write(json.dumps(r) + "\n")
        print(n, len(r["faceoffs"]), "faceoffs", flush=True)


if __name__ == "__main__":
    main()
