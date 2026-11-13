"""NOSE4Web's SNES shootout injury skip (8212db9, "shootoutInjuries": NHL94_shootout_injuries.smc,
nhl94snes_SA1_shootout_injuries.sfc; the season shootout after one overtime). At PlayShootout's .t1x / .t1xx the build
steps the round's list entry on (1-5, wrapping; all five out: the original) past a shooter whose saved tmpdst ($7E:F37F,
SA-1 $40:4A8F, (entry - 1) x 2, +$34 the visitors) is $FFFC (injured for the game), when its mark $7E:F0F0 is set.

From snes_shootout_check's `tie` (a computer game, period 3 at 2-2 with 3 s left, overtime's clock put at 3 s): once
the shootout's lists are built (homeshooters $1D71, awayshooters $1D79), the case's players are marked $FFFC in the
saved tmpdst; the shootout is kept level (both goals words 0 at every turn's start) until round 7 is over. Each turn:
the round $1D85, BA_Team $1E91, BA_Skater_Offset $1E8F (what the helper records as the shooter), against the entry
the build should take. Cases:
  default   home entries 1 and 5 and away entry 3 injured: home round 1 -> entry 2, round 5 -> 5, 1 out -> 2, round 6
            (entry 1) -> 2; away round 3 -> 4, round 8 not reached
  picked    home entry 2 replaced by another skater (as the lineup screen would put him) and him injured: round 2 -> 3
  unmarked  as default with the mark $7E:F0F0 cleared at the shootout's start: every listed shooter shoots (the
            original, as Shootout mode from the menu)
  fight     (2 MB builds, NOSE4Web 20149ad: fightinj kept in a copy, $7E:FE00 LoROM / $40:5800 SA-1, before
            StartGame_go clears it) home entries 1 and 4 hurt in a fight late in overtime, their majors still running
            at its end: fightinj ($E74E + roster, +26 the visitors) and fightinjany ($E782) set, tmpdst ($1852) box
            time $00B4 (not $FFFC), set when overtime's clock is put at 3 s; entry 1 and 4 skipped. Needs the lists
            from an earlier case in the same run (default first).
python snes_shootout_injury_check.py ROM OUT [case ...]"""
import json
import sys
from pathlib import Path

import lowload
from snes_60fps_cvc import CLOCK, GSP, computer_only
from snes_ot_goal_check import GOALS, GOALS_P, PLAYMODE, start
from snes_shootout_check import set_score, two_mb

SHOOTMODE, ROUND, BA_TEAM, BA_OBJ, BA_SKATER, SFLAGS = 0x1D81, 0x1D85, 0x1E91, 0x1E8D, 0x1E8F, 0x15D8
LISTS = (0x1D71, 0x1D79)
SAVED, MARK = 0xF37F, 0xF0F0
FIGHTINJ, FIGHTINJANY, TMPDST = 0xE74E, 0xE782, 0x1852
KNOWN = {}


def list_of(m, t):
    return [m.w(LISTS[t] + i) & 0xFF for i in range(8)]


def saved_tmpdst(m, t, entry_value, v):
    """Mark the player (list byte entry_value = roster + 1) of team t in the saved tmpdst."""
    off = (entry_value - 1) * 2 + 0x34 * t
    if m.sa1:
        m.bw[0x4A8F + off] = v & 0xFF
        m.bw[0x4A8F + off + 1] = v >> 8
    else:
        m.setw(SAVED + off, v)


def expected(lst, injured, r):
    y = r
    while y >= 6:
        y -= 5
    for _ in range(5):
        if lst[y] not in injured or lst[y] == 0:
            return lst[y] - 1
        y = y + 1 if y < 5 else 1
    return lst[r if r < 6 else r - 5] - 1


def run_case(e, m, base, case, pad):
    e.unserialize(base)
    m.setw(PLAYMODE, 0)
    m.setw(GSP, 2)
    m.setw(CLOCK, 3)
    set_score(m, 2, 2)
    e.run(2)
    ot_set, still, last, menu_pressed, marked = False, 0, None, False, False
    lists, injured, turns, seen, mark_values = None, [set(), set()], [], set(), set()
    for f in range(0, 60 * 60 * 40, 2):
        e.run(2)
        if f % 300 == 0 and not pad:
            computer_only(m)
        if f % 3600 == 0:
            lowload.breathe()
        g, so = m.w(GSP), m.w(SHOOTMODE) & 0xFF
        if g == 3 and not ot_set and 10 < m.w(CLOCK) < 299:
            m.setw(CLOCK, 3)
            set_score(m, 2, 2)
            ot_set = True
            if case == "fight":
                for entry in (1, 4):
                    r_ = KNOWN["lists"][0][entry] - 1
                    buf, o = m.at(FIGHTINJ + r_)               # his fightinj byte (the home team's 26 first)
                    buf[o] = 1
                    m.setw(TMPDST + 2 * r_, 0x00B4)
                m.setw(FIGHTINJANY, 1)
        c = m.w(CLOCK)
        still = still + 2 if c == last else 0
        last = c
        if still >= 900 and not so:
            e.run(4, hold=["START"])
            still = 0
        if so and not menu_pressed and m.w(SFLAGS) & 0x400:
            e.run(30)
            e.run(8, hold=["B"])
            menu_pressed = True
        if not so:
            continue
        mark_values.add(m.w(MARK))
        if not marked and list_of(m, 0)[1] and list_of(m, 1)[1]:
            lists = [list_of(m, 0), list_of(m, 1)]
            if case == "fight":
                injured = [{lists[0][1], lists[0][4]}, set()]
                copy = [(m.bw[0x5800 + i] if m.sa1 else m.e.ram[0xFE00 + i]) for i in range(52)]
                fight_seen = {"copy (bytes set)": [i for i, v in enumerate(copy) if v],
                              "saved tmpdst": [f"{(m.bw[0x4A8F + 2 * (v - 1)] | m.bw[0x4A90 + 2 * (v - 1)] << 8) if m.sa1 else m.w(SAVED + 2 * (v - 1)):04X}" for v in sorted(injured[0])]}
            elif case == "picked":
                spare = next(v for v in range(2, 27) if v not in lists[0])
                m.setw(LISTS[0] + 2, (m.w(LISTS[0] + 2) & 0xFF00) | spare)
                lists[0][2] = spare
                injured[0] = {spare}
            else:
                injured = [{lists[0][1], lists[0][5]}, {lists[1][3]}]
            for t in (0, 1):
                for v in injured[t] if case != "fight" else ():
                    saved_tmpdst(m, t, v, 0xFFFC)
            if case == "unmarked":
                m.setw(MARK, 0)
            marked = True
        r, team, obj = m.w(ROUND), 1 if m.w(BA_TEAM) else 0, m.w(BA_OBJ)
        if obj != 0xFFFF and (r, team) not in seen and marked:
            seen.add((r, team))
            want = expected(lists[team], set() if case == "unmarked" else injured[team], r)
            turns.append({"round": r, "team": team, "shooter": m.w(BA_SKATER) & 0xFF, "expected": want,
                          "listed": lists[team][r if r < 6 else r - 5] - 1})
            set_score(m, 0, 0)                     # level: the shootout goes on
            if r >= 8:
                break
    ok = bool(turns) and all(t["shooter"] == t["expected"] for t in turns)
    if lists:
        KNOWN["lists"] = lists
    res = {"case": case, "lists": lists, **({"fight": fight_seen} if case == "fight" and lists else {}), "injured (list bytes)": [sorted(s) for s in injured],
           "mark values in the shootout": sorted(mark_values), "turns": turns, "ok": ok}
    print(json.dumps(res), flush=True)
    return res


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    cases = sys.argv[3:] or ["default", "picked", "unmarked"] + (["fight"] if two_mb(rom) else [])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    pad = two_mb(rom)
    if pad:
        from snes_shootout_lock_check import person_start
        e, m = person_start(rom, out)
    else:
        e, m = start(rom, 0, out)
    e.run(600)
    base = e.serialize()
    for case in cases:
        run_case(e, m, base, case, pad)


if __name__ == "__main__":
    main()
