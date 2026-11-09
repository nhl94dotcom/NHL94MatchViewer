"""The same skater twice on one line (SNES, 2026-11-09, for NOSE4Web): NHL94_line_dup.smc has Adam Oates at both LW and
C on Boston's NLC and Sc1 lines; NHL94.smc is the control. The SNES twin of gen_line_dup_check.py.

Four runs per ROM: line changes Off (NLC) and On (Sc1), Boston controlled by pad 1 (at home, random presses every 20
frames: directions, B, Y) and by the computer (Boston visiting, pad 1 on Montreal). From the opening faceoff, the
clock set to 240 s; every 10 frames of play Boston's skaters (objects of its team, pfteam $1503: position $0F43, roster
place $12A3, sprite frame $0D97), the puck carrier (puckc $0AD9), whether the clock moves (600 frames of play without
it). At the end, from the game's per-player bytes (Home's 26 places then Away's: goals $18EE, assists $1922, shots
$1956, checks $168E; goalies, places 0 and 1, left out of the sums) against the team's goals ($178E), shots ($176A,
by period) and checks ($17B6); the lines ($1CE4 home, 8 bytes a line: goalie, LD, RD, LW, C, RW, extra). The SNES keeps
no per-player ice time. In the human runs, the pause menu's Edit Lines (four down, B) is opened and screenshotted,
then two picks (down to LW, B, down, B), with screenshots, and the lines read back. Gentle (lowload).

python snes_line_dup_check.py ROM OUT"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

import lowload
import menu_shots as M
from snes_score_logo_check import Check, CLOCK, PSITEM

TEAMS = ["Montreal", "New Jersey", "NY Islanders", "NY Rangers", "Ottawa", "Philadelphia", "Pittsburgh", "Quebec",
         "San Jose", "St. Louis", "Tampa Bay", "Toronto", "Vancouver", "Washington", "Winnipeg", "All Stars East",
         "All Stars West", "Anaheim", "Boston", "Buffalo", "Calgary", "Chicago", "Dallas", "Detroit", "Edmonton",
         "Florida", "Hartford", "Los Angeles"]
POSITION, PNUM, FRAME, PFTEAM, PUCKC = 0x0F43, 0x12A3, 0x0D97, 0x1503, 0x0AD9
LINES = 0x1CE4
POS = {1: "LD", 2: "RD", 3: "LW", 4: "C", 5: "RW"}


def run(rom, out, lines_on, human):
    out.mkdir(parents=True, exist_ok=True)
    c = Check(rom, out)
    e = c.e
    if human:
        keys = f"DOWN RIGHT*{TEAMS.index('Boston')} " + ("DOWN*4 RIGHT " if lines_on else "")
    else:
        keys = f"DOWN*2 RIGHT*{(TEAMS.index('Boston') - TEAMS.index('Los Angeles')) % 28} " + ("DOWN*3 RIGHT " if lines_on else "")
    M.play(e, "w1500 START w240 START w240 " + keys + "w60 S:setup START w240 START w120 w2400", out)
    for _ in range(12):
        clock = e.w(CLOCK)
        c.step(240)
        if not c.state()["hor"] and e.w(CLOCK) != clock:
            break
        c.press("START", 60)
    e.setw(CLOCK, 240)
    side = 0 if human else 1
    rnd = random.Random(7)
    hold, frames, samples, dup, fewer, still, freeze = [], 0, 0, 0, 0, 0, 0
    vis, carrier, sets = Counter(), Counter(), Counter()
    first_four, freeze_states, edit_done, lines_after = None, [], False, None
    linesnow = lambda: [[e.b(LINES + 8 * l + i) for i in range(8)] for l in range(7)]
    lines_start = linesnow()
    while frames < 60 * 60 * 6 and e.w(CLOCK) > 0:
        if human and frames % 20 == 0:
            hold = rnd.choice([["UP"], ["DOWN"], ["LEFT"], ["RIGHT"], ["UP", "LEFT"], ["DOWN", "RIGHT"], ["B"], ["Y"], []])
        c0 = e.w(CLOCK)
        for _ in range(10):
            e.run(1, hold=hold if human else [])
        frames += 10
        if frames % 600 == 0:
            lowload.breathe()
        st = c.state()
        if st["paused"] or st["replay"] or st["hor"]:
            if frames % 300 == 0:
                e.run(4, hold=["START"])
            continue
        still = still + 10 if e.w(CLOCK) == c0 else 0
        if still >= 600:
            freeze += 1
            still = 0
            if len(freeze_states) < 3:
                freeze_states.append(dict(frame=frames, clock=e.w(CLOCK)))
                e.screenshot(out / f"freeze_{len(freeze_states)}.png")
        samples += 1
        objs = [k for k in range(12) if (e.w(PFTEAM + 2 * k) != 0) == bool(side)]
        sk = [(e.w(POSITION + 2 * k), e.w(PNUM + 2 * k) & 0xFF, e.w(FRAME + 2 * k)) for k in objs]
        sk = [s for s in sk if 1 <= s[0] <= 5]
        roster = [s[1] for s in sk]
        sets[tuple(sorted((POS[p], r) for p, r, _ in sk))] += 1
        twice = [r for r, n in Counter(roster).items() if n > 1]
        if twice:
            dup += 1
            vis[sum(1 for p, r, fr in sk if r in twice and fr)] += 1
        if len(sk) < 5:
            fewer += 1
            if first_four is None:
                first_four = dict(frame=frames, objects=[(k, e.w(POSITION + 2 * k), e.w(PNUM + 2 * k) & 0xFF) for k in objs])
                e.screenshot(out / "four_skaters.png")
        k = e.w(PUCKC)
        if k < 0x18 and k % 2 == 0 and (k // 2) in objs:
            carrier[(POS.get(e.w(POSITION + k), "?"), e.w(PNUM + k) & 0xFF)] += 1
        if human and not edit_done and frames > 60 * 60:
            edit_done = True
            c.press("START", 90)
            for _ in range(30):
                if e.w(PSITEM) == 4:
                    break
                c.press("DOWN")
            c.press("B", 200)
            e.screenshot(out / "edit_lines.png")
            for key, name in (("DOWN", "edit_down1"), ("DOWN", "edit_down2"), ("DOWN", "edit_down3"), ("B", "edit_pick"),
                              ("DOWN", "edit_list_down"), ("B", "edit_pick2")):
                c.press(key, 90)
                e.screenshot(out / f"{name}.png")
            lines_after = linesnow()
            for k2 in range(8):
                c.press("START" if k2 % 2 == 0 else "A", 200)
                if c.state()["paused"]:
                    break
            for _ in range(30):
                if e.w(PSITEM) == 0:
                    break
                c.press("UP")
            c.press("START", 240)
    e.screenshot(out / "end.png")
    base = 26 * side
    per = lambda a: [e.b(a + base + i) for i in range(26)]
    shots = sum(e.w(0x176A + 4 * p + 2 * side) for p in range(3))
    return dict(rom=Path(rom).name, lines_on=lines_on, human=human, samples=samples, frames=frames,
                samples_with_a_player_twice=dup, sprites_drawn_when_twice=dict(vis), samples_under_5_skaters=fewer,
                freezes=freeze, freeze_states=freeze_states, first_four=first_four,
                on_ice_most=[(list(k), n) for k, n in sets.most_common(4)],
                puck_carried_by=[(f"{p} #{r}", n) for (p, r), n in carrier.most_common(8)],
                team_goals=e.w(0x178E + 2 * side), skater_goal_sum=sum(per(0x18EE)[2:]), team_shots=shots,
                skater_shot_sum=sum(per(0x1956)[2:]), team_checks=e.w(0x17B6 + 2 * side), check_sum=sum(per(0x168E)),
                goals=per(0x18EE), assists=per(0x1922), shots=per(0x1956), checks=per(0x168E),
                lines_start=lines_start, lines_end=linesnow(), lines_after_edit=lines_after)


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    lowload.gentle()
    results = []
    for lines_on in (False, True):
        for human in (True, False):
            tag = f"{'on' if lines_on else 'off'}_{'human' if human else 'cpu'}"
            r = run(rom, out / tag, lines_on, human)
            results.append(r)
            print(json.dumps(r), flush=True)
    (out / "results.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
