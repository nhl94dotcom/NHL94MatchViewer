"""NOSE4Web's Genesis "any skater at any position" option, played (2026-11-09, 68134c4: SelectLinePlayer lists every
skater for every slot; EncodeTeamLines also writes a byte a slot, counted from the first skater, to save RAM $1EC0
(team + 1 first, 34 bytes); DecodeTeamLines reads it when its team byte matches the old block's).

`any ROM OUT`: power-on to play (line changes off: line 0 plays), the pause menu's Edit Lines:
  - the C slot of line 0 opened (C on it): the list (Satt $C018, screentimer $D5B6 = rows - 1) against the team's
    skaters; the last row (a defenceman: roster order is goalies, forwards, defence) picked with C;
  - the LW slot opened and the player now at C picked: the swap (the LW's old player goes to C);
  - Save Team Line from the exit menu (START, menuitem $CF20 = 2, C): the save RAM bytes that changed (save RAM byte
    X is at 2X + 1 of the core's save RAM: ReadSRAM), with a pattern written first into the old block's playoff bytes
    (block bytes 18-27, `passbits`) to see that they survive;
  - back to play: at the next faceoff, the skater playing C (position +$35 = 4) and whether he is the defenceman;
  - the console reset, back to play, Edit Lines, Load Team Line: line 0 against the lines saved.
`orig ORIGINAL_ROM ANY_ROM OUT`: lines saved on the original ROM (the LW and RW of line 0 swapped through the editor),
  its save RAM put into the option ROM's before power-on, then Load Team Line there: the lines against the saved ones.
`compat ANY_ROM ORIGINAL_ROM OUT`: the other way round. On the option ROM, line 0's LW and RW swapped (fits the old
  format) and saved, then a defenceman put at C (doesn't fit) and saved again; each save RAM given to the original ROM,
  Load Team Line there: the lines against the saved ones, and the old block's bytes after each save. 68134c4 doesn't
  write the old block's nibbles, so both load wrong there; a build that also writes them when every player fits should
  load the first exactly (and the second as whatever it chose to leave).

python gen_any_position_check.py any ROM OUT | orig ORIGINAL_ROM ANY_ROM OUT | compat ANY_ROM ORIGINAL_ROM OUT"""
import ctypes as C
import json
import sys
from pathlib import Path

from gen_1on1_edit_lines import Run, OPTLINE, MENUITEM, TESTLIST

SATT, ROWS, CURSOR = 0xC018, 0xD5B6, 0xD5AE
TEAMS = (0xC6CE, 0xCA32)
TMLINES, TMTEAM = 0x16A, 0x28
CONT1 = 0xC328
BASE, SZ = 0xB04A, 0x80
LINEBLOCK, NEWBLOCK = 0x1EF6, 0x1EC0


def sram(e):
    lib = e.lib
    lib.retro_get_memory_data.restype = C.c_void_p
    lib.retro_get_memory_size.restype = C.c_size_t
    ptr, size = lib.retro_get_memory_data(0), lib.retro_get_memory_size(0)
    return (C.c_ubyte * size).from_address(ptr)


def sbyte(buf, x):
    return buf[2 * x + 1]


def team_struct(e):
    return TEAMS[0] if e.w(CONT1) in (0, 1) else TEAMS[1]


def line0(e):
    t = team_struct(e)
    return [e.b(t + TMLINES + i) for i in range(8)]


def to_slot(r, slot):
    for _ in range(20):
        if r.e.w(TESTLIST) & 7 == slot and r.e.w(TESTLIST) < 8:
            return True
        r.press("DOWN" if (r.e.w(TESTLIST) & 7) < slot else "UP", 30)
    return False


def pick_row(r, row):
    for _ in range(40):
        cur = r.e.w(CURSOR)
        if cur == row:
            break
        r.press("DOWN" if cur < row else "UP", 20)
    r.press("C", 120)


def exit_menu(r, item):
    r.press("START", 120)
    for _ in range(10):
        if r.e.w(MENUITEM) == item:
            break
        r.press("DOWN", 30)
    r.press("C", 240)


def open_edit_lines(r):
    r.press("START", 90)
    r.menu(3)


def plant(r):
    """The old block's playoff bytes (block bytes 18-27, passbits) set to a pattern in save RAM, the checksum fixed
    ($1FFF the sum of bytes 0-$1FFD, $1FFE its complement: MakeSRAMChecksum), then a reset, so ReadLineData loads it."""
    buf = sram(r.e)
    for i in range(18, 28):
        buf[2 * (LINEBLOCK + i) + 1] = 0x40 + i
    total = sum(buf[2 * x + 1] for x in range(0x1FFE)) & 0xFF
    buf[2 * 0x1FFF + 1] = total
    buf[2 * 0x1FFE + 1] = total ^ 0xFF
    r.e.lib.retro_reset()


def back_to_play(r):
    for k in range(30):
        c = r.e.w(0xC468)
        r.step(60)
        if r.e.b(0xFFF7) == 0 and r.e.w(0xC468) != c:
            return True
        r.press("START" if k % 2 == 0 else "C", 90)
    return False


def any_part(rom, out):
    r = Run(rom, out)
    res = {}
    r.to_play()
    plant(r)
    r.to_play()
    r.e.setw(OPTLINE, 1)                  # line changes off: line 0 is the one on the ice
    t = team_struct(r.e)
    res["team struct"] = hex(t)
    open_edit_lines(r)
    res["line 0 before"] = line0(r.e)
    to_slot(r, 4)
    r.press("C", 120)
    rows = r.e.w(ROWS) + 1
    lst = [r.e.b(SATT + i) for i in range(rows)]
    res["C slot list (roster places)"] = lst
    r.shot("c_list")
    pick_row(r, rows - 1)
    res["line 0 after picking the last row for C"] = line0(r.e)
    d = lst[-1] + 1
    to_slot(r, 3)
    r.press("C", 120)
    lst3 = [r.e.b(SATT + i) for i in range(r.e.w(ROWS) + 1)]
    res["LW slot list"] = lst3
    old_lw = line0(r.e)[3]
    pick_row(r, lst3.index(d - 1))
    res["line 0 after picking him (now at C) for LW"] = line0(r.e)
    res["swap ok"] = line0(r.e)[3] == d and line0(r.e)[4] == old_lw
    # put him back at C for the faceoff check and the save
    to_slot(r, 4)
    r.press("C", 120)
    lst4 = [r.e.b(SATT + i) for i in range(r.e.w(ROWS) + 1)]
    pick_row(r, lst4.index(d - 1))
    saved = line0(r.e)
    res["line 0 saved"] = saved
    before = bytes(sram(r.e))
    exit_menu(r, 2)
    after = bytes(sram(r.e))
    changed = [i for i in range(len(before)) if before[i] != after[i]]
    xs = sorted({(i - 1) // 2 for i in changed if i % 2 == 1})
    res["save RAM bytes changed by Save Team Line"] = [hex(x) for x in xs][:80]
    res["new block"] = [sbyte(after, NEWBLOCK + i) for i in range(34)]
    res["old block bytes 0-27"] = [sbyte(after, LINEBLOCK + i) for i in range(28)]
    res["playoff bytes kept"] = res["old block bytes 0-27"][18:28] == [0x40 + i for i in range(18, 28)]
    # back to play: the next faceoff's centre
    res["back in play"] = back_to_play(r)
    cs, faceoff = [], None
    for _ in range(90):                    # until a faceoff: the two centres at the dot
        r.step(30)
        cs = [(k, r.e.b(BASE + SZ * k + 0x66)) for k in range(12) if r.e.b(BASE + SZ * k + 0x35) == 4]
        if any(p == d - 1 for _, p in cs) and r.e.w(0xC2EA) & 0x100:
            faceoff = True
            r.shot("faceoff")
            break
    res["records playing C now (record, roster place)"] = cs
    res["defenceman (roster place) playing C"] = any(p == d - 1 for _, p in cs)
    res["seen at a stoppage (clock stopped)"] = bool(faceoff)
    r.shot("after_save_play")
    # reset, back to play, load
    r.e.lib.retro_reset()
    r.to_play()
    open_edit_lines(r)
    res["line 0 after reset, before Load"] = line0(r.e)
    exit_menu(r, 3)
    res["line 0 after Load"] = line0(r.e)
    res["loaded = saved"] = line0(r.e)[1:6] == saved[1:6]
    return res


def orig_part(orig, anyrom, out):
    import subprocess
    p = out / "orig_sram.bin"
    if not p.exists():
        subprocess.run([sys.executable, __file__, "--orig-save", orig, str(out)], check=True)
    saved = json.loads((out / "orig_saved.json").read_text())
    r = Run(anyrom, out / "orig_load")
    buf = sram(r.e)
    data = p.read_bytes()
    for i in range(min(len(data), len(buf))):
        buf[i] = data[i]
    r.e.lib.retro_reset()
    r.to_play()
    open_edit_lines(r)
    before = line0(r.e)
    exit_menu(r, 3)
    return {"saved on the original": saved, "before Load": before, "after Load": line0(r.e),
            "loaded = saved": line0(r.e)[1:6] == saved[1:6]}


def orig_save(orig, out):
    r = Run(orig, out / "orig_save")
    r.to_play()
    r.e.setw(OPTLINE, 0)
    open_edit_lines(r)
    to_slot(r, 5)
    r.press("C", 120)
    lst = [r.e.b(SATT + i) for i in range(r.e.w(ROWS) + 1)]
    lw = line0(r.e)[3]
    pick_row(r, lst.index(lw - 1))                     # the LW picked for RW: swapped
    saved = line0(r.e)
    exit_menu(r, 2)
    (out / "orig_sram.bin").write_bytes(bytes(sram(r.e)))
    (out / "orig_saved.json").write_text(json.dumps(saved))


def compat_save(anyrom, out):
    """On the option ROM: line 0's LW and RW swapped (both forwards: fits the old format), saved; then a defenceman put
    at C (doesn't fit), saved again. Each save's save RAM and lines kept."""
    r = Run(anyrom, out / "compat_save")
    r.to_play()
    r.e.setw(OPTLINE, 1)
    open_edit_lines(r)
    to_slot(r, 5)
    r.press("C", 120)
    lst = [r.e.b(SATT + i) for i in range(r.e.w(ROWS) + 1)]
    pick_row(r, lst.index(line0(r.e)[3] - 1))
    fit = line0(r.e)
    exit_menu(r, 2)
    (out / "compat_fit.bin").write_bytes(bytes(sram(r.e)))
    open_edit_lines(r)
    to_slot(r, 4)
    r.press("C", 120)
    lst = [r.e.b(SATT + i) for i in range(r.e.w(ROWS) + 1)]
    pick_row(r, len(lst) - 1)                          # the last row: a defenceman
    unfit = line0(r.e)
    exit_menu(r, 2)
    (out / "compat_unfit.bin").write_bytes(bytes(sram(r.e)))
    # the defenceman moved to LW (the LW goes to C by the swap), then the first forward put at RW:
    # a stand-in for LW (the first forward) who is already on the line
    open_edit_lines(r)
    to_slot(r, 3)
    r.press("C", 120)
    lst = [r.e.b(SATT + i) for i in range(r.e.w(ROWS) + 1)]
    pick_row(r, lst.index(line0(r.e)[4] - 1))
    to_slot(r, 5)
    r.press("C", 120)
    lst = [r.e.b(SATT + i) for i in range(r.e.w(ROWS) + 1)]
    pick_row(r, 0)                                     # the first row: the first forward
    unfit2 = line0(r.e)
    exit_menu(r, 2)
    (out / "compat_unfit2.bin").write_bytes(bytes(sram(r.e)))
    (out / "compat_saved.json").write_text(json.dumps({"fit": fit, "unfit": unfit, "unfit2": unfit2}))


def load_on(rom, sram_path, out):
    """A save RAM given to a ROM before power-on, then Load Team Line: line 0 before and after."""
    r = Run(rom, out)
    buf = sram(r.e)
    data = Path(sram_path).read_bytes()
    for i in range(min(len(data), len(buf))):
        buf[i] = data[i]
    r.e.lib.retro_reset()
    r.to_play()
    open_edit_lines(r)
    before = line0(r.e)
    exit_menu(r, 3)
    r.shot("after_load")
    after = line0(r.e)
    open_edit_lines(r)                                 # the C slot's list there: its first row is the first forward
    to_slot(r, 4)
    r.press("C", 120)
    first = r.e.b(SATT) + 1
    (out / "load.json").write_text(json.dumps({"before Load": before, "after Load": after,
                                               "first row of the C list (first forward)": first}))


def compat_part(anyrom, orig, out):
    import subprocess
    subprocess.run([sys.executable, __file__, "--compat-save", anyrom, str(out)], check=True)
    saved = json.loads((out / "compat_saved.json").read_text())
    res = {"saved on the option ROM": saved}
    for kind in ("fit", "unfit", "unfit2"):
        where = out / f"compat_load_{kind}"
        subprocess.run([sys.executable, __file__, "--load", orig, str(out / f"compat_{kind}.bin"), str(where)], check=True)
        got = json.loads((where / "load.json").read_text())
        old = [sbyte((out / f"compat_{kind}.bin").read_bytes(), LINEBLOCK + i) for i in range(28)]
        res[f"{kind}: the old block's bytes 0-27 after the save"] = old
        res[f"{kind}: on the original ROM"] = dict(got, **{"loaded = saved": got["after Load"][1:6] == saved[kind][1:6]})
    return res


def main():
    if sys.argv[1] == "--orig-save":
        orig_save(sys.argv[2], Path(sys.argv[3]))
        return
    if sys.argv[1] == "--compat-save":
        compat_save(sys.argv[2], Path(sys.argv[3]))
        return
    if sys.argv[1] == "--load":
        load_on(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
        return
    if sys.argv[1] == "compat":
        out = Path(sys.argv[4])
        out.mkdir(parents=True, exist_ok=True)
        res = compat_part(sys.argv[2], sys.argv[3], out)
        print(json.dumps(res, indent=1))
        (out / "compat.json").write_text(json.dumps(res, indent=1))
        return
    if sys.argv[1] == "any":
        out = Path(sys.argv[3])
        out.mkdir(parents=True, exist_ok=True)
        res = any_part(sys.argv[2], out)
    else:
        out = Path(sys.argv[4])
        out.mkdir(parents=True, exist_ok=True)
        res = orig_part(sys.argv[2], sys.argv[3], out)
    print(json.dumps(res, indent=1))
    (out / f"{sys.argv[1]}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
