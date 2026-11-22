"""NOSE4Web's older NHL '94 options that hadn't been played (2026-11-21): ppPkFix, aggressionFix and comebackFix, each
build against the original with the same checksum changes (nhl94_retail_nop), the same games and seeds.

setplayer (collide94 ~2801) builds a player's working ratings each time he comes on (every faceoff, line change and
box exit): AttributeCalc gives each rating nibble x 5 plus his hot / cold value (0-30); then
- the power play (sflags2 $C2EE bit 5, bit 6 the team: set from the players on the ice): PPBonus from the team's
  srpppk byte (team data + ScoutReport word + 1), the low nibble in the original, or PKBonus, minus the high nibble;
  both added to Offensive Awareness (aioff, transformed) and Stickhandling (+$71, plain: the one read here);
- the third-period bonus: +2 to aioff and Checking (+$75) for a tied or trailing team; the original skips it when
  half the period is more than the clock (`bgt` at $15B70), so it comes in the first half, backwards; the fix's `blt`
  gives it in the second half;
- Aggression (+$73) = AttributeCalc's value & $F in the original (16-30 wrap to 0-14).

Each game: power-on to Game Setup, the teams set (Opt1team $D04C / Opt2team $D04E), the shortest periods, penalties
on, line changes on (more players come on), the seed $D066 from the game's number, the computer on both sides. At every
faceoff (the clock running again after a stoppage) 10 frames in: every on-ice record's team, position, roster index,
the working ratings, and sflags2. With --comeback, at each stoppage one of five cases is set before the faceoff
(nothing; period 3 with 90% or 20% of the period left, home trailing or leading by one) and put back after; the
home skaters on the ice are drained of energy then, so a fresh line comes on at the faceoff (setplayer builds only
players coming on: 2 of 35 faceoffs had any otherwise).
Roster bytes and the teams' srpppk / srhomeaway are read from the ROM through each team struct's tmdata ($C6CE /
$CA32 + $1E).

python gen_untested_fixes_check.py ROM OUT.jsonl GAMES [--comeback] [FIRST]
python gen_untested_fixes_check.py report ORIG.jsonl BUILD.jsonl agg|pppk|comeback"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

PERLEN, OPTPEN, OPTLINE, OPT1, OPT2 = 0xD050, 0xD056, 0xD058, 0xD04C, 0xD04E
SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
SFLAGS2, HOME, AWAY, GMODE = 0xC2EE, 0xC6CE, 0xCA32, 0xC2EA
HMGOALS, AWGOALS = HOME + 0xC, AWAY + 0xC
BASE, SZ = 0xB04A, 0x80
RAT = dict(aioff=0x6A, aidef=0x6B, stickhand=0x71, aggress=0x73, checking=0x75, legspd=0x69)
CASES = [None, ("first half", 0.9, "trailing"), ("first half", 0.9, "leading"), ("second half", 0.2, "trailing"),
         ("second half", 0.2, "leading")]


def team_data(e, rom, struct):
    """(roster bytes per roster index, srpppk, srhomeaway) from the ROM, through the team struct's tmdata."""
    td = (e.w(struct + 0x1E) << 16 | e.w(struct + 0x20)) & 0xFFFFFF
    w = lambda a: rom[a] << 8 | rom[a + 1]  # noqa: E731
    sr = td + w(td + 8)
    players, a = [], td + w(td)
    for _ in range(30):
        n = w(a)
        if n == 0 or n > 64:
            break
        a += n
        players.append(list(rom[a:a + 8]))
        a += 8
    return players, rom[sr + 1], rom[sr + 2]


def game(rom_path, n, comeback):
    rom = Path(rom_path).read_bytes()
    e = Emu(rom_path)
    G.to_setup(e, Path(rom_path).parent)
    home, away = (3 * n) % 26, (3 * n + 11) % 26
    e.setw(OPT1, home)
    e.setw(OPT2, away)
    e.setw(PERLEN, 0)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 0)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    teams = {t: team_data(e, rom, s) for t, s in ((0, HOME), (1, AWAY))}
    out = {"game": n, "teams": [home, away], "ids": [e.b(0xC6F7), e.b(0xCA5B)],
           "pppk": [teams[0][1], teams[1][1]], "homeaway": [teams[0][2], teams[1][2]],
           "roster": [teams[0][0], teams[1][0]], "faceoffs": []}
    plen = e.w(CLOCK) + 1                 # the period's length (the clock at the first faceoff, about)
    frame, still, last, case_i, saved, active = 0, 0, None, 0, None, None
    at_stop, stopped = None, False        # each record's roster index when the whistle went; gmode's clock bit
    while e.w(GSP) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0         # any screen: a menu or box waiting gets START
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
        now = bool(e.b(GMODE) & 1) and e.b(SCREEN) == 0     # gmclock: the clock stopped (a whistle)
        if now and not stopped:
            # the whistle's frame, before the faceoff is set up (puckfaceoff picks the line)
            at_stop = [e.b(BASE + SZ * k + 0x66) if e.b(BASE + SZ * k + 0x35) != 0xFF else None for k in range(12)]
            if comeback and saved is None:
                active = CASES[case_i % len(CASES)]
                case_i += 1
                saved = (e.w(GSP), e.w(CLOCK), e.w(HMGOALS), e.w(AWGOALS))
                # a fresh home line at this faceoff (setplayer builds only players coming on): the home skaters on
                # the ice drained (tmpde, team struct +$32, a word per roster index), so CompLine
                # (SetFaceoffComputerLine) takes the next line with energy over 3/4
                for k in range(6):
                    r = BASE + SZ * k
                    if e.b(r + 0x35) not in (0, 0xFF):
                        e.setw(HOME + 0x32 + 2 * e.b(r + 0x66), 0)
                if active:
                    part, frac, lead = active
                    e.setw(GSP, 2)
                    e.setw(CLOCK, int(plen * frac))
                    e.setw(HMGOALS, 1 if lead == "trailing" else 2)
                    e.setw(AWGOALS, 2 if lead == "trailing" else 1)
        elif stopped and not now and e.b(SCREEN) == 0:
            # the clock running again: the faceoff dropped
            e.run(10)
            frame += 10
            recs = []
            for k in range(12):
                r = BASE + SZ * k
                pos = e.b(r + 0x35)
                if pos == 0xFF:
                    continue
                pn = e.b(r + 0x66)
                recs.append(dict(k=k, team=0 if k < 6 else 1, pos=pos, pnum=pn,
                                 fresh=at_stop is None or at_stop[k] != pn,
                                 **{name: e.b(r + off) for name, off in RAT.items()}))
            out["faceoffs"].append(dict(frame=frame, gsp=e.w(GSP), clock=e.w(CLOCK), sflags2=e.b(SFLAGS2),
                                        case=list(active) if active else None, recs=recs))
            if saved is not None:
                g, cl, hg, ag = saved
                e.setw(GSP, g)
                e.setw(CLOCK, cl)
                e.setw(HMGOALS, hg)
                e.setw(AWGOALS, ag)
                saved, active = None, None
            now = bool(e.b(GMODE) & 1)
        stopped = now
        e.run(1, hold=["START"] if still >= 8 and frame % 60 < 2 else [])
        frame += 1
    out["frames"] = frame
    return out


def load(path):
    return {r["game"]: r for r in (json.loads(x) for x in open(path) if x.strip()) if "error" not in r}


def report(orig, build, what):
    A, B = load(orig), load(build)
    print(f"{len(A)} / {len(B)} games")
    if what == "agg":
        for name, R in (("original", A), ("build", B)):
            by = defaultdict(Counter)
            for r in R.values():
                for f in r["faceoffs"]:
                    for p in f["recs"]:
                        if p["pos"] == 0:
                            continue
                        nib = r["roster"][p["team"]][p["pnum"]][7] & 15 if p["pnum"] < len(r["roster"][p["team"]]) else -1
                        by[nib][p["aggress"]] += 1
            print(f"  {name}: roster Aggression nibble -> working Aggression seen (skaters, every faceoff)")
            for nib in sorted(by):
                print(f"    {nib}: " + ", ".join(f"{v}x{c}" for v, c in sorted(by[nib].items())))
    elif what == "pppk":
        for name, R in (("original", A), ("build", B)):
            tally = Counter()
            for r in R.values():
                even = defaultdict(Counter)
                for f in r["faceoffs"]:
                    if not f["sflags2"] & 0x20 and f["case"] is None:
                        for p in f["recs"]:
                            even[(p["team"], p["pnum"])][p["stickhand"]] += 1
                for f in r["faceoffs"]:
                    if not f["sflags2"] & 0x20 or f["case"] is not None:
                        continue
                    pp_team = 1 if f["sflags2"] & 0x40 else 0
                    for p in f["recs"]:
                        if p["pos"] == 0 or not p.get("fresh") or (p["team"], p["pnum"]) not in even:
                            continue
                        base = even[(p["team"], p["pnum"])].most_common(1)[0][0]
                        d = p["stickhand"] - base
                        byte = r["pppk"][p["team"]]
                        hi, lo = byte >> 4, byte & 15
                        role = "PP" if p["team"] == pp_team else "PK"
                        if base in (0, 30) or p["stickhand"] in (0, 30):
                            tally[(role, "clamped")] += 1
                            continue
                        want = {"PP": {"low": lo, "high": hi}, "PK": {"low": -lo, "high": -hi}}[role]
                        hit = [k for k, v in want.items() if v == d]
                        tally[(role, "+".join(hit) if hit else f"other ({d:+d}; lo {lo} hi {hi})")] += 1
            print(f"  {name}: Stickhandling on the power play / penalty kill minus the same player's at even strength, "
                  "matched to the team byte's nibbles")
            for k, v in sorted(tally.items()):
                print(f"    {k[0]} {k[1]:30s} {v}")
    elif what == "comeback":
        for name, R in (("original", A), ("build", B)):
            vals = defaultdict(list)
            for r in R.values():
                for f in r["faceoffs"]:
                    if not f["case"]:
                        continue
                    part, frac, lead = f["case"]
                    for p in f["recs"]:
                        if p["team"] == 0 and p["pos"] != 0 and p.get("fresh"):
                            vals[(part, lead, p["pnum"], r["game"])].append(p["checking"])
            # each home skater's Checking when built fresh with no bonus possible (periods 1-2, or leading)
            base = defaultdict(Counter)
            for r in R.values():
                for f in r["faceoffs"]:
                    lead = f["case"][2] if f["case"] else None
                    if (f["case"] is None and f["gsp"] < 2) or lead == "leading":
                        for p in f["recs"]:
                            if p["team"] == 0 and p["pos"] != 0 and p.get("fresh"):
                                base[(p["pnum"], r["game"])][p["checking"]] += 1
            diffs = defaultdict(Counter)
            for (part, lead, pnum, g), v in vals.items():
                if lead == "trailing" and (pnum, g) in base:
                    b = base[(pnum, g)].most_common(1)[0][0]
                    for x in v:
                        diffs[part][x - b] += 1
            print(f"  {name}: home skaters' working Checking when they came on trailing by one in period 3, minus the same "
                  "skater's with no bonus")
            for part in ("first half", "second half"):
                print(f"    {part}: " + ", ".join(f"{d:+d} x{c}" for d, c in sorted(diffs[part].items())))


def main():
    if sys.argv[1] == "report":
        report(sys.argv[2], sys.argv[3], sys.argv[4])
        return
    rom, out, games = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
    comeback = "--comeback" in sys.argv
    rest = [a for a in sys.argv[4:] if not a.startswith("--")]
    first = int(rest[0]) if rest else 0
    lowload.gentle()
    done = {json.loads(x)["game"] for x in open(out) if x.strip()} if out.exists() else set()
    for n in range(first, first + games):
        if n in done:
            continue
        r = game(rom, n, comeback)
        with open(out, "a") as f:
            f.write(json.dumps(r) + "\n")
        print(n, r.get("ids"), len(r.get("faceoffs", [])), "faceoffs", r.get("error", ""), flush=True)


if __name__ == "__main__":
    main()
