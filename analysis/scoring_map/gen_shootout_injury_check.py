"""NOSE4Web's Genesis shootout injury skip (f4ad85d: nhl94_shootout_injuries.bin, nhl94_shootout_injuries_fighting.bin;
the season shootout after one overtime). NextShooter's `move.w 0(a0,d0.w),(BA_Skater_Offset).w` ($FC504) becomes a jsr:
with the build's flag ($FFF082) and gsp 3, the list entry steps on (d0 += 2, wrapping at 10; all five out: the
original) past a player whose saved tmpdst ($FFF084 + $66 = $F0EA + 2 x roster, +$364 the visitors) is $FFFC, or is
positive with bit 12 ($1000: chaos's fight injury, serving $5xxx or served $1000).

A computer game put at 1-1 in overtime with 3 s left (regular season), START pressed until the shootout's first attempt
clock runs (shootoutclock $D454); once the lists are built (homeshooters $D57A / awayshooters $D588: five shooters,
then the goalie) and the build has saved the team structs, the case's marks go into the saved tmpdst (or, `fight`,
into the live tmpdst in overtime, before the save). The shootout is kept level (homeshootgoals / awayshootgoals $D574 /
$D576 at 0 at each turn) to round 7. Each turn (shootoutround $D578, BA_Team $D404): BA_Skater_Offset $D40A a few
frames after NextShooter, against the entry the build should take (homeshootnum (round - 1) mod 5, stepped past the
marked). The helper's reading (genesis.View, Recording.shootout_attempt) runs alongside: its shooters must be the same.
Cases:
  default   home entries 0 ($FFFC) and 4 ($1000, served fight major), away entry 2 ($512C, fight major running)
  picked    home entry 1 replaced by a skater not on the list (as the lineup screen would) and him $FFFC
  mode      Shootout mode from the menu (Play Mode 4, gsp 0, the flag clear), home entry 0 marked: the original order
  fight     (in overtime, before the shootout's save) home entry 0's live tmpdst $512C, entry 3's $1000: both skipped
            (the lists from an earlier case of the same run: default first)

python gen_shootout_injury_check.py ROM [case ...]"""
import json
import os
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
os.environ.setdefault("NHL94_HOME", os.path.join(tempfile.gettempdir(), "nhl94_helper_home_gsoinj"))
for sub in ("matches", "captures", "sprites", "roms", "shared", "sounds"):
    os.makedirs(os.path.join(os.environ["NHL94_HOME"], sub), exist_ok=True)
import nhl94_helper as H  # noqa: E402
from systems import genesis  # noqa: E402

import gen_ot_check as G  # noqa: E402
import lowload  # noqa: E402
from emu import Emu  # noqa: E402

PLAYMODE, GMODE2, CONT1, CONT2, BASE, SZ = 0xD048, 0xC2FA, 0xC328, 0xC32A, 0xB04A, 0x80
GSP, CLOCK, HM, AW = 0xC466, 0xC468, 0xC6DA, 0xCA3E
SOFLAG, SOCLOCK, SOGOALS, SOROUND, LISTS, BA_TEAM, BA_SHOOTER = 0xF082, 0xD454, 0xD574, 0xD578, (0xD57A, 0xD588), 0xD404, 0xD40A
SAVED, TMPDST, TEAMS, SOTEAM = 0xF0EA, 0x66, (0xC6CE, 0xCA32), 0xD594
KNOWN = {}


class Seen:
    system, teams = "genesis", 28

    def __init__(self, e):
        self.e = e

    def read(self, start, length):
        return bytes(self.e.ram[(start + i) & 0xFFFF] for i in range(length))


def lists_of(e):
    return [[e.w(a + 2 * i) for i in range(6)] for a in LISTS]


def is_out(v):
    return v == 0xFFFC or (v < 0x8000 and v & 0x1000)


def expected(lst, words, r):
    i0 = (r - 1) % 5
    i = i0
    for _ in range(5):
        if not is_out(words.get(lst[i], 0xFFFE)):
            return lst[i]
        i = (i + 1) % 5
    return lst[i0]


def run(rom, case):
    e = Emu(rom)
    tmp = Path(os.environ["NHL94_HOME"]) / "_boot"
    tmp.mkdir(exist_ok=True)
    G.to_setup(e, tmp)
    mode = case == "mode"
    if mode:
        e.setw(PLAYMODE, 4)
        for _ in range(4):
            e.run(4, hold=["START"])
            e.run(300)
    else:
        if not G.into_play(e):
            return {"case": case, "error": "never reached play"}
        e.setw(PLAYMODE, 0)
        e.setw(GSP, 3)
        e.setw(CLOCK, 3)
        e.setw(HM, 1)
        e.setw(AW, 1)
        if case == "fight":                        # hurt in fights: the live words, before the build's save
            kl = KNOWN["lists"]
            for roster, v in ((kl[0][0], 0x512C), (kl[0][3], 0x1000)):
                e.setw(TEAMS[0] + TMPDST + 2 * roster, v)
    seen, rec = Seen(e), types.SimpleNamespace()
    started, marked, lists, words, turns, key, pending = False, False, None, [{}, {}], [], None, None
    for f in range(60 * 60 * 40):
        if f % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            if f % 3600 == 0:
                lowload.breathe()
        on = e.b(GMODE2) & 1
        started = bool(on and (started or e.w(SOCLOCK)))
        e.run(1, hold=["START"] if not started and f % 150 == 0 and f > 300 else [])
        on = e.b(GMODE2) & 1
        if not on:
            if turns and not on:
                break
            continue
        if not marked and e.w(LISTS[0]) | e.w(LISTS[0] + 2) and (mode or e.b(SOFLAG)):
            lists = lists_of(e)
            marks = [{}, {}]
            if case in ("default", "mode"):
                marks[0] = {lists[0][0]: 0xFFFC} if mode else {lists[0][0]: 0xFFFC, lists[0][4]: 0x1000}
                if not mode:
                    marks[1] = {lists[1][2]: 0x512C}
            elif case == "picked":
                spare = next(v for v in range(2, 25) if v not in lists[0])
                e.setw(LISTS[0] + 2, spare)
                lists[0][1] = spare
                marks[0] = {spare: 0xFFFC}
            for t in (0, 1):
                for roster, v in marks[t].items():
                    e.setw(SAVED + 0x364 * t + 2 * roster, v)
            words = [{r_: e.w(SAVED + 0x364 * t + 2 * r_) for r_ in range(26)} for t in (0, 1)]
            marked = True
        if not marked:
            continue
        v = genesis.View(seen)
        if mode:                                   # Shootout mode: shown to the View as the season shootout
            v.shootout = True
        H.Recording.shootout_attempt(rec, v) if v.shootout_turn is not None or mode else None
        k_ = (e.w(SOROUND), e.w(SOTEAM) & 1)      # shootoutteam flips as an attempt ends
        if k_ != key:
            key, pending = k_, True
            e.setw(SOGOALS, 0)                     # level: the shootout goes on
            e.setw(SOGOALS + 2, 0)
        if pending and (e.w(BA_TEAM) & 1) == key[1] and e.w(SOCLOCK):   # NextShooter has set this turn up
            r_, t = key
            want = expected(lists[t], words[t] if not mode else {}, r_)
            turns.append({"round": r_, "team": t, "shooter": e.w(BA_SHOOTER), "expected": want,
                          "listed": lists[t][(r_ - 1) % 5]})
            pending = False
            if r_ >= 7 and t == 1:
                break
    H.Recording.shootout_attempt(rec, None)
    att = getattr(rec, "so_attempts", [])
    rec_shooters = {(a["round"], a["team"]): a["shooter"] for a in att}
    ok = bool(turns) and all(t["shooter"] == t["expected"] for t in turns)
    rec_ok = all(rec_shooters.get((t["round"], t["team"]), t["shooter"]) == t["shooter"] for t in turns)
    if lists:
        KNOWN["lists"] = lists
    res = {"case": case, "lists (roster index)": lists,
           **({"saved words of the fight cases": [f"{words[0].get(KNOWN['lists'][0][0], 0):04X}", f"{words[0].get(KNOWN['lists'][0][3], 0):04X}"]} if case == "fight" and lists else {}), "turns": turns, "ok": ok,
           "recorder shooters agree": rec_ok, "recorder attempts": len(att)}
    print(json.dumps(res), flush=True)
    return res


def main():
    rom = sys.argv[1]
    cases = sys.argv[2:] or ["default", "picked", "mode", "fight"]
    lowload.gentle()
    for c in cases:
        run(rom, c)


if __name__ == "__main__":
    main()
