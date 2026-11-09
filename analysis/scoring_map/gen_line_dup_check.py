"""The same skater twice on one line (Genesis, 2026-11-09, for NOSE4Web): nhl94_line_dup.bin has Adam Oates (roster
place 2) at both LW and C on Boston's NLC and Sc1 lines; nhl94.bin is the control.

Four runs per ROM: line changes Off (NLC) and On (Sc1), Boston controlled by pad 1 (at home, random presses every 20
frames: directions, B, C) and by the computer (Boston visiting, pad 1 on Montreal). Each run: from the opening
faceoff, the clock set to 240 s (four game minutes), every 10 frames of play Boston's skaters (records' position
+$35, roster place +$66, sprite frame +$06), the puck carrier, and whether the clock moves (a freeze: 600 frames of play
without it). At the end of the run, from Boston's team stat block (+$B4 goals, +$CE assists, +$E8 shots, +$11C checks
thrown, +$136 ice time, word per place; goalies (places 0 and 1) left out of the sums, their goals and shots are against; the lines at +$16A, 7 x 8 bytes, values roster place + 1), the per-player sums
against the team's goals, shots and checks, and Oates's ice time against the others'. In the human runs, the pause
menu's Edit Lines (item 3) is opened and screenshotted, then two picks are tried (down to LW, C; C), with
screenshots, and the lines read back. Gentle (lowload).

python gen_line_dup_check.py ROM OUT"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

import lowload
import menu_shots as M
from gen_score_logo_check import Watch, CLOCK, MENUITEM

REC = 0xB04A
TEAMS = ["Montreal", "New Jersey", "NY Islanders", "NY Rangers", "Ottawa", "Philadelphia", "Pittsburgh", "Quebec",
         "San Jose", "St. Louis", "Tampa Bay", "Toronto", "Vancouver", "Washington", "Winnipeg", "All Stars East",
         "All Stars West", "Anaheim", "Boston", "Buffalo", "Calgary", "Chicago", "Dallas", "Detroit", "Edmonton",
         "Florida", "Hartford", "Los Angeles"]
OATES = 2
POS = {1: "LD", 2: "RD", 3: "LW", 4: "C", 5: "RW"}


def run(rom, out, lines_on, human):
    out.mkdir(parents=True, exist_ok=True)
    g = Watch(rom, out)
    e = g.e
    w = lambda a: e.w(0xFF0000 | a)
    b = lambda a: e.b(0xFF0000 | a)
    if human:   # Boston at home (team 1), pad 1 on it
        keys = f"DOWN*2 RIGHT*{TEAMS.index('Boston')} "
    else:       # Boston visiting (team 2), pad 1 on Montreal
        keys = f"DOWN*3 RIGHT*{(TEAMS.index('Boston') - TEAMS.index('Los Angeles')) % 28} "
    lc = "DOWN*6 RIGHT RIGHT " if human else "DOWN*5 RIGHT RIGHT "       # row 8, Line Changes: On
    script = "w900 START w120 START w120 " + keys + (lc if lines_on else "") + "w60 S:setup"
    M.play(e, script, out)
    for _ in range(40):
        if e.b(0xFFF7) == 0:
            break
        e.run(4, hold=["START"])
        e.run(200)
    g.wait_play()
    e.setw(0xFF0000 | CLOCK, 240)
    side = 0 if human else 1
    team = 0xC6CE if side == 0 else 0xCA32
    recs = range(0, 6) if side == 0 else range(6, 12)
    rnd = random.Random(7)
    samples, dup, fewer, oates_vis, carrier, still, freeze, lines_seen = 0, 0, 0, Counter(), Counter(), 0, 0, Counter()
    on_ice_sets = Counter()
    hold, frames, shots_taken = [], 0, 0
    edit_done = False
    first_four, freeze_states = None, []
    while frames < 60 * 60 * 6 and w(CLOCK) > 0:
        if human and frames % 20 == 0:
            hold = rnd.choice([["UP"], ["DOWN"], ["LEFT"], ["RIGHT"], ["UP", "LEFT"], ["DOWN", "RIGHT"], ["B"], ["C"], []])
        c0 = w(CLOCK)
        for _ in range(10):
            e.run(1, hold=hold if human else [])
        frames += 10
        lowload.breathe() if frames % 600 == 0 else None
        if not g.in_play():
            if frames % 300 == 0:
                e.run(4, hold=["START"])
            continue
        still = still + 10 if w(CLOCK) == c0 else 0
        if still >= 600:
            freeze += 1
            still = 0
            if len(freeze_states) < 3:
                freeze_states.append(dict(frame=frames, state=g.state(), clock=w(CLOCK)))
                e.screenshot(out / f"freeze_{len(freeze_states)}.png")
        samples += 1
        sk = [(b(REC + k * 0x80 + 0x35), b(REC + k * 0x80 + 0x66), w(REC + k * 0x80 + 6) & 0x7FF) for k in recs]
        sk = [s for s in sk if 1 <= s[0] <= 5]
        roster = [s[1] for s in sk]
        on_ice_sets[tuple(sorted((POS[p], r) for p, r, _ in sk))] += 1
        if roster.count(OATES) > 1:
            dup += 1
            oates_vis[sum(1 for p, r, fr in sk if r == OATES and fr)] += 1
        if len(sk) < 5:
            fewer += 1
            if first_four is None:
                first_four = dict(frame=frames, records=[(k, b(REC + k * 0x80 + 0x35), b(REC + k * 0x80 + 0x66),
                                  w(REC + k * 0x80 + 0x58), w(REC + k * 0x80 + 6) & 0x7FF) for k in recs])
                e.screenshot(out / "four_skaters.png")
        lines_seen[w(team + 0x16)] += 1
        k = b(REC + 14 * 0x80 + 0x61)
        if b(REC + 14 * 0x80 + 0x60) == 0 and k in recs:
            carrier[(POS.get(b(REC + k * 0x80 + 0x35), "?"), b(REC + k * 0x80 + 0x66))] += 1
        if human and not edit_done and frames > 60 * 60 and g.in_play():
            edit_done = True
            g.press("START", 90)
            for _ in range(30):
                if w(MENUITEM) == 3:
                    break
                g.press("DOWN")
            g.press("C", 240)
            e.screenshot(out / "edit_lines.png")
            for key, name in (("DOWN", "edit_down1"), ("DOWN", "edit_down2"), ("DOWN", "edit_down3"), ("C", "edit_pick"),
                              ("DOWN", "edit_list_down"), ("C", "edit_pick2")):
                g.press(key, 90)
                e.screenshot(out / f"{name}.png")
            lines_after_edit = [[b(team + 0x16A + 8 * l + i) for i in range(8)] for l in range(7)]
            for k2 in range(8):
                g.press("START" if k2 % 2 == 0 else "C", 200)
                if g.state()["paused"]:
                    break
            for _ in range(30):
                if w(MENUITEM) == 0:
                    break
                g.press("UP")
            g.press("C", 240)
    e.screenshot(out / "end.png")
    per = lambda off, n=26: [b(team + off + i) for i in range(n)]
    ice = [w(team + 0x136 + 2 * i) for i in range(26)]
    res = dict(rom=Path(rom).name, lines_on=lines_on, human=human, samples=samples, frames=frames,
               samples_with_oates_twice=dup, oates_sprites_drawn_when_twice=dict(oates_vis),
               samples_under_5_skaters=fewer, freezes=freeze, line_numbers_seen=dict(lines_seen),
               on_ice_most=[(list(k), n) for k, n in on_ice_sets.most_common(4)],
               puck_carried_by=[(f"{p} #{r}", n) for (p, r), n in carrier.most_common(8)],
               team_goals=w(team + 0x0C), skater_goal_sum=sum(per(0xB4)[2:]), team_shots=w(team + 0x00),
               skater_shot_sum=sum(per(0xE8)[2:]), team_checks=w(team + 0x10), check_sum=sum(per(0x11C)),
               goals=per(0xB4), assists=per(0xCE), shots=per(0xE8), first_four=first_four, freeze_states=freeze_states,
               ice=ice, oates=dict(goals=per(0xB4)[OATES], assists=per(0xCE)[OATES], shots=per(0xE8)[OATES],
                                    ice=ice[OATES]),
               lines=[[b(team + 0x16A + 8 * l + i) for i in range(8)] for l in range(7)])
    if human and edit_done:
        res["lines_after_edit_picks"] = lines_after_edit
    return res


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
