"""NHL '95 (Genesis): NOSE4Web's "any skater at any position" (2026-11-17; $95312's bgt.w / add.w d0,d1 NOPped: the
line editor's list for a slot was the defencemen for LD / RD and the forwards otherwise, now every skater).

The line editor (pause menu OPTIONS, Edit Lines; LineEditor): DOWN moves the slot ($D282 & 7: 1 LD .. 5 RW), C opens
its list (rows - 1 at $D280, the roster places from $BC1E), DOWN through the list ($D278 the row), C picks; START opens
the exit box (Start leaves, A Set Original Lines, and outside a Regular Game (sflags11 bit 6) B Load / C Save Team Line).

Modes (python gen95_lines_check.py MODE OUT ...):
  lists ORIG BUILD STATE         every slot's list, line changes on ($CC5C 0) and off (1), both ROMs
  centre ROM STATE               the last defenceman put at C on line 1, back to play, a whistle: the skater at C
                                 (+$35 = 4) at the faceoff, his roster place (+$66), and the faceoff's takers"""
import json
import sys
from pathlib import Path

import gen95_organ_resume_check as O
import lowload

BASE, SZ = 0xAC62, 0x80
SLOT, ROWS, ROW, LIST, OPTLINE = 0xD282, 0xD280, 0xD278, 0xBC1E, 0xCC5C
PENBUF, GMODE = 0xBFCE, 0xBEF0


def rec(k):
    return BASE + k * SZ


def editor(r):
    r.press("START", 120)
    r.press("DOWN", 30)
    r.press("DOWN", 30)
    r.press("C", 300)


def open_list(r, slot):
    e = r.e
    e.setw(SLOT, (e.w(SLOT) & ~7) | slot)
    r.press("C", 120)
    n = e.w(ROWS) + 1
    return [e.b(LIST + i) for i in range(n)]


def lists(rom, state):
    out = {}
    r = O.R(rom, state)
    e = r.e
    for lc in (0, 1):
        e.unserialize(r.base)
        e.setw(OPTLINE, lc)
        editor(r)
        ed = e.serialize()
        for slot in range(1, 6):
            e.unserialize(ed)
            out[f"line changes {'off' if lc else 'on'}, slot {'.LD RD LW C  RW'.split()[0] if False else slot}"] = open_list(r, slot)
    return out


def centre(rom, state):
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    editor(r)
    lst = open_list(r, 4)
    target = lst[-1]                              # the last row: a defenceman (roster order: goalies, forwards, defence)
    for _ in range(len(lst) + 2):
        if e.w(ROW) == len(lst) - 1:
            break
        r.press("DOWN", 16)
    r.press("C", 150)
    picked_row = e.w(ROW)
    r.press("START", 120)                         # the exit box
    r.press("START", 150)                         # leave the editor
    for _ in range(4):
        r.press("UP", 20)
    for _ in range(4):
        if not r.paused():
            break
        r.press("C", 90)
    r.frame(60)
    pad_team = e.w(0xBF4C)                        # cont1team: 1 home, 2 away
    side = range(0, 6) if pad_team == 1 else range(6, 12)
    k = next(k for k in side if e.b(rec(k) + 0x35) not in (0, 0xFF))
    e.setw(PENBUF, 0x0A << 8 | k)                 # a whistle
    e.setw(PENBUF + 2, 0)
    stopped = False
    for f in range(1500):
        e.run(1)
        if e.w(GMODE) & 0x100:
            stopped = True
        if stopped and not e.w(GMODE) & 0x100:     # the faceoff over: the clock runs again
            break
    cs = [(k, e.b(rec(k) + 0x66)) for k in side if e.b(rec(k) + 0x35) == 4]
    return dict(target_roster_place=target, picked_row=picked_row, list_rows=len(lst), pad_team=pad_team,
                centre_at_faceoff=cs, paused=r.paused())


import ctypes as C
from emu import Emu
import gen95_fight_check as F

HOME = 0xC288
LINES = 0x16C                                     # the team struct's line sets, 56 bytes
L3 = 0x5136                                       # SRSavedLines3 (playoffs: sflags10 bit 0), $39 bytes a team


def sram(e):
    lib = e.lib
    lib.retro_get_memory_data.restype = C.c_void_p
    p, n = lib.retro_get_memory_data(0), lib.retro_get_memory_size(0)
    return (C.c_ubyte * n).from_address(p)


class Game:
    """A New Playoffs game from power-on (pad 1 on the home team), optionally with save RAM put in first."""
    def __init__(self, rom, save=None):
        self.e = Emu(rom)
        if save is not None:
            buf = sram(self.e)
            buf[:len(save)] = save
        e = self.e
        F.to_setup(e)
        for _ in range(12):                        # retail's boot (the ROM self-check) runs longer: on to Game Setup
            if e.b(0xD283):                        # (its team rows set)
                break
            self.press("START", 200)
        e.setb(0xD282, 3)                          # Play Mode: New Playoffs (setupvalues row 0)
        self.press("DOWN", 30)
        self.press("UP", 60)
        self.press("START", 400)
        self.press("START", 400)
        last = None
        for f in range(60 * 150):
            e.run(1, hold=["START"] if f % 240 == 0 else [])
            c = e.w(0xC022)
            if e.w(0xC020) == 0 and last is not None and 0 < c < last:
                break
            last = c
        e.run(120)

    def press(self, b, w):
        self.e.run(6, hold=[b])
        self.e.run(w)

    def paused(self):
        return bool(self.e.w(0xBEF2) & 0x100)

    def lines(self):
        return [self.e.b(HOME + LINES + i) for i in range(56)]


def saveload(build, orig):
    g = Game(build)
    e = g.e
    before = g.lines()
    s0 = bytes(sram(e))
    r = g                                          # the editor helpers need press / paused
    editor(r)
    lst = open_list(r, 4)
    for _ in range(len(lst) + 2):
        if e.w(ROW) == len(lst) - 1:
            break
        g.press("DOWN", 16)
    g.press("C", 150)
    edited = g.lines()
    g.press("START", 150)
    exitbox_save = True
    g.press("C", 300)                              # C = Save Team Line
    s1 = bytes(sram(e))
    changed = [i for i in range(len(s0)) if s0[i] != s1[i]]
    g.press("START", 150)
    g.press("A", 300)                              # A = Set Original Lines
    original = g.lines()
    g.press("START", 150)
    g.press("B", 300)                              # B = Load Team Line
    loaded = g.lines()
    res = dict(target=lst[-1], lines_before=before, edited=edited, save_ram_bytes_changed=len(changed),
               changed_range=(hex(changed[0]), hex(changed[-1])) if changed else None,
               after_set_original=original, after_load=loaded,
               load_restores=loaded == edited, original_restores=original == before)
    # the build's saved block on the unhacked ROM: its own New Playoffs game (another matchup: the two ROMs' boots
    # differ), the block copied from the build's home team's slot to this game's home team's slot, then Load there
    o = Game(orig)
    ro = o
    lines0 = o.lines()
    sb = L3 + e.w(HOME + 0x28) * 0x39
    db = L3 + o.e.w(HOME + 0x28) * 0x39
    buf = sram(o.e)
    for i in range(0x39):
        buf[2 * (db + i) + 1] = s1[2 * (sb + i) + 1]
    res_teams = (e.w(HOME + 0x28), o.e.w(HOME + 0x28))
    editor(ro)
    o.press("START", 150)
    o.press("B", 300)
    lo = o.lines()
    o.press("START", 150)
    o.press("START", 150)
    for _ in range(4):
        o.press("UP", 20)
    for _ in range(4):
        if not o.paused():
            break
        o.press("C", 90)
    o.e.run(60)
    oe = o.e
    k = next(k for k in range(6) if oe.b(rec(k) + 0x35) not in (0, 0xFF))
    oe.setw(PENBUF, 0x0A << 8 | k)
    oe.setw(PENBUF + 2, 0)
    stopped = False
    for f in range(1500):
        oe.run(1)
        if oe.w(GMODE) & 0x100:
            stopped = True
        if stopped and not oe.w(GMODE) & 0x100:
            break
    cs = [(k, oe.b(rec(k) + 0x66)) for k in range(6) if oe.b(rec(k) + 0x35) == 4]
    res.update(unhacked_playoffs=bool(o.e.w(0xBF0A) & 0x100), teams_build_unhacked=res_teams, unhacked_before_load=lines0, unhacked_after_load=lo, unhacked_load_matches=lo == edited, unhacked_C_slot=lo[4],
               unhacked_centre_at_faceoff=cs)
    return res


def main():
    mode, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    if mode == "lists":
        orig, build, state = sys.argv[3:6]
        res = {}
        for name, rom in (("orig", orig), ("build", build)):
            res[name] = lists(rom, state)
            for k, v in res[name].items():
                print(f"{name} {Path(rom).name}: {k}: {len(v)} listed {v}", flush=True)
        (out / f"lists_{Path(build).stem}.json").write_text(json.dumps(res))
    elif mode == "saveload":
        res = saveload(sys.argv[3], sys.argv[4])
        for k, v in res.items():
            print(f"{k}: {v}", flush=True)
        (out / f"saveload_{Path(sys.argv[3]).stem}.json").write_text(json.dumps(res))
    elif mode == "centre":
        for rom, state in zip(sys.argv[3::2], sys.argv[4::2]):
            print(Path(rom).name, json.dumps(centre(rom, state)), flush=True)


if __name__ == "__main__":
    main()
