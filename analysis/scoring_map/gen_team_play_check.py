"""A team picked through Game Setup and played (Genesis, 2026-11-19; a league member's report on a franchise ROM: a
team that couldn't be chosen, all-black players, players turning into #0 and skating slowly).

1. Power-on to Game Setup (gen_ot_check.to_setup). On the Home and then the Visitor line, RIGHT is pressed (a press
   that changes nothing is pressed again) until Opt1team $D04C / Opt2team $D04E is TEAM, 40 presses at most: every
   value seen is printed with a screenshot when TEAM is reached (OUT/home.png, OUT/visitor.png).
2. GAMES games from there, the computer on both sides (cont1team / cont2team cleared, the person flag off, every
   second), line changes on (OptLine $D058 = 0; NHL94_LINES=off sets 1, off: the first line all game, the power-play and penalty-kill units at penalties), PERLEN (Optperlen $D050, 0 the shortest), penalties on, the seed
   $D066 from the game's number. Every second of play: each record's position (+$35), roster index (+$66), jersey
   number (the ROM's roster, genesis.read_teams), working Speed (+$69) and speed (+$28 / +$2A). Flagged: a roster
   index past the team's roster, a skater on roster index 0 or a goalie's slot, two records on one roster index, a
   skater's working Speed 0, any skater record whose roster changes outside a whistle. A screenshot each period's
   start (OUT/g<n>_p<period>.png) shows the colours.

python gen_team_play_check.py ROM OUT TEAM [GAMES] [PERLEN] [FIRST]   (FIRST: the first game's number, for its seed)"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from systems import genesis  # noqa: E402

TEAM1, TEAM2, PERLEN, OPTPEN, OPTLINE = 0xD04C, 0xD04E, 0xD050, 0xD056, 0xD058
SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
TEAM_IDS = (0xC6F7, 0xCA5B)
BASE, SZ, POS, ROSTER, SPD = 0xB04A, 0x80, 0x35, 0x66, 0x69


def press(e, b):
    e.run(4, hold=[b])
    e.run(26)


def pick(e, addr, team, out, name):
    seen = [e.w(addr)]
    for _ in range(40):
        if e.w(addr) == team:
            break
        before = e.w(addr)
        for _ in range(4):
            press(e, "RIGHT")
            if e.w(addr) != before:
                break
        seen.append(e.w(addr))
    e.run(30)
    e.screenshot(out / f"{name}.png")
    print(f"{name}: values after each RIGHT {seen}; reached {team}: {e.w(addr) == team}", flush=True)
    return e.w(addr) == team


def game(rom, teams, n, team, perlen, out):
    e = Emu(rom)
    G.to_setup(e, out)
    press(e, "DOWN")
    press(e, "DOWN")
    ok = [pick(e, TEAM1, team, out, "home")]
    press(e, "DOWN")
    ok.append(pick(e, TEAM2, team, out, "visitor"))
    e.setw(PERLEN, perlen)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1 if os.environ.get("NHL94_LINES") == "off" else 0)
    if not G.into_play(e):
        return {"game": n, "picked": ok, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    ids = [e.b(a) for a in TEAM_IDS]
    print("team ids in play", ids, [teams[i]["abbr"] if i < len(teams) else "?" for i in ids], flush=True)
    flags, rosters_seen = Counter(), [Counter(), Counter()]
    examples = []
    frame, still, last, shot_period = 0, 0, None, -1
    prev = {}
    speeds = []
    while e.w(GSP) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            running = c != last
            still = still + 1 if not running else 0
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
            if e.b(SCREEN) == 0 and e.w(GSP) != shot_period and running:
                shot_period = e.w(GSP)
                e.screenshot(out / f"g{n}_p{shot_period + 1}.png")
            if e.b(SCREEN) == 0 and running:
                for side in (0, 1):
                    roster = teams[ids[side]]["players"] if ids[side] < len(teams) else []
                    on = []
                    for k in range(6 * side, 6 * side + 6):
                        r = BASE + SZ * k
                        pos = e.b(r + POS)
                        if pos == 0xFF:
                            continue
                        idx, spd = e.b(r + ROSTER), e.b(r + SPD)
                        on.append(idx)
                        rosters_seen[side][idx] += 1
                        num = roster[idx]["num"] if idx < len(roster) else None
                        bad = []
                        if idx >= len(roster):
                            bad.append("roster index past the roster")
                        elif pos != 0 and roster[idx]["g"]:
                            bad.append("skater on a goalie's slot")
                        if pos != 0 and spd == 0:
                            bad.append("skater Speed 0")
                        if pos != 0 and num == 0:
                            bad.append("jersey #0")
                        if pos != 0:
                            v = (e.sw(r + 0x28) ** 2 + e.sw(r + 0x2A) ** 2) ** 0.5
                            speeds.append(v)
                        if k in prev and prev[k][0] == pos and prev[k][1] != idx and running and still == 0:
                            bad.append("roster changed at the same position (a line change)")
                        prev[k] = (pos, idx)
                        for b in bad:
                            flags[b] += 1
                            if len(examples) < 30:
                                examples.append(dict(period=e.w(GSP) + 1, clock=c, record=k, pos=pos, roster=idx,
                                                     num=num, spd=spd, why=b))
                    dup = [i for i, m in Counter(on).items() if m > 1]
                    if dup:
                        flags["two records on one roster index"] += 1
                        if len(examples) < 30:
                            examples.append(dict(period=e.w(GSP) + 1, clock=c, side=side, on=on, why="duplicate"))
        e.run(2, hold=["START"] if still >= 8 and frame % 60 < 2 else [])
        frame += 2
    return {"game": n, "picked": ok, "ids": ids, "periods": e.w(GSP), "flags": dict(flags), "examples": examples,
            "rosters_used": [dict(sorted(r.items())) for r in rosters_seen],
            "mean_skater_speed": round(sum(speeds) / max(len(speeds), 1)),
            "score": [e.w(0xC6DA), e.w(0xCA3E)]}


def main():
    rom, out, team = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
    games = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    perlen = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    first = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    lowload.gentle()
    out.mkdir(parents=True, exist_ok=True)
    teams = genesis.read_teams(Path(rom))
    print("team", team, teams[team]["abbr"], [(p["num"], p["name"][:12], "G" if p["g"] else "") for p in teams[team]["players"]])
    for n in range(first, first + games):
        r = game(rom, teams, n, team, perlen, out)
        print(json.dumps(r), flush=True)
        with open(out / "results.jsonl", "a") as f:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
