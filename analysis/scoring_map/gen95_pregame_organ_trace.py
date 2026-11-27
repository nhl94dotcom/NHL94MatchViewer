"""Why the organ song is silent on NHL '95's matchup screen in NOSE4Web's pre-game song build (2026-11-27,
NHL_95_pregame.bin 4A8C9D24: Buffalo at home plays song $37, Gypsy Spain; its slot steps through the song for 14 s
with the audio at 0), and a fix tried in a scratch copy.

The sound driver plays only patches uploaded to the Z80 by a load list (SndLoadList, SoundCmd 7; bank item type $B).
The bank has two: list 0 (patches $0B $0D $0E $11 $13-$16 $18 $1B-$1D: the front end's: songs 0, 2, 3 use only
these) and list 1 ($00-$0A $0C $19 $33-$49: the organ $19 and the effects). ScoutingReport restarts the driver with
list 0 before its song (as Opening2 and the intermission do); StartGame and each period start restart it with list
1 before the organ's period tune. NOSE4Web's hook (jsr at $9F5E4 in place of `move.w #3,-(sp) / jsr song`, the
routine at $1A72C6, the team table at $1A72E4) starts the table's song with list 0 still loaded, so an organ song's
notes ask for patch $19, which isn't there.

`tables ROM`: the two load lists, the patches (program changes) each song asks for, the hook's bytes.
`fix BUILD OUT_ROM`: a scratch copy with the hook moved to a new routine that, for a song $32 or above (the organ
  songs), first loads list 1 too (SoundCmd 7, d1 = 1), then starts the song as before.
`z80 ROM TEAM`: power-on to Game Setup (PREGAME95_SETUP, as gen_pregame_song_check), TEAM at home, into the matchup
  screen; the Z80's loaded patch table ($0100: 6-byte entries 0, id, size, address) and the sequencer slots.

python gen95_pregame_organ_trace.py tables ROM | fix BUILD OUT_ROM | z80 ROM TEAM"""
import struct
import sys
from pathlib import Path

import numpy as np

import gen95_music_check as G

HOOK_AT, TABLE = 0x9F5E4, 0x1A72E4
SOUNDCMD, SONG, HOMETEAM = 0x676D8, 0x678C2, 0xBF54
NEW_AT = 0x1A7340
Z80 = 16 + 0x10000                       # Z80 RAM in Genesis Plus GX's state, after work RAM


def lists(rom):
    out = {}
    for x in G.items(rom):
        if x["type"] == 0xB:
            d = rom[x["at"]:x["at"] + x["size"]]
            i, pairs = 0, []
            while d[i] != 0xFF:
                pairs.append(d[i + 1])
                i += 2
            out[x["id"]] = pairs
    return out


def song_patches(rom, sid):
    x = next((x for x in G.items(rom) if x["type"] == 3 and x["id"] == sid), None)
    if x is None:
        return None
    d = rom[x["at"]:x["at"] + x["size"]]
    return sorted({d[i + 1] for i in range(len(d) - 1) if d[i] & 0xF0 == 0xC0})


def tables(path):
    rom = Path(path).read_bytes()
    L = lists(rom)
    for k, v in L.items():
        print(f"load list {k}:", " ".join(f"{p:02X}" for p in v))
    for s in (0, 2, 3, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38):
        ps = song_patches(rom, s)
        where = {p: [k for k, v in L.items() if p in v] for p in ps or []}
        print(f"song {s:02X}: patches {' '.join(f'{p:02X}' for p in ps or [])}   in lists {where}")
    print("hook call:", rom[HOOK_AT:HOOK_AT + 10].hex(" ", 2))
    print("hook routine:", rom[0x1A72C6:TABLE].hex(" ", 2))
    print("table:", [hex(struct.unpack_from(">h", rom, TABLE + 2 * t)[0] & 0xFFFF) for t in range(28)])


def fix(build, out):
    rom = bytearray(Path(build).read_bytes())
    assert rom[HOOK_AT:HOOK_AT + 6] == bytes.fromhex("4eb9001a72c6"), "not the hook expected"
    assert all(b == 0xFF for b in rom[NEW_AT:NEW_AT + 0x40]), "the new routine's room isn't free"
    code = bytes.fromhex(
        "48E7E0E0"            # movem.l d0-d2/a0-a2,-(sp)
        "41F9" + f"{TABLE:08X}" +   # lea TABLE,a0
        "3038" + f"{HOMETEAM:04X}" +  # move.w (HomeTeam).w,d0
        "D040"                # add.w d0,d0
        "30300000"            # move.w 0(a0,d0.w),d0
        "0C400032"            # cmpi.w #$32,d0
        "6D12"                # blt.s .go   (-1 = silence and songs 0-3 skip the load)
        "2F00"                # move.l d0,-(sp)
        "303C0007"            # move.w #7,d0      SndLoadList
        "323C0001"            # move.w #1,d1      list 1: the organ ($19) and the effects
        "4EB9" + f"{SOUNDCMD:08X}" +  # jsr SoundCmd
        "201F"                # move.l (sp)+,d0
        "3F00"                # .go: move.w d0,-(sp)
        "4EB9" + f"{SONG:08X}" +      # jsr song (pops its word, as the original call)
        "4CDF0707"            # movem.l (sp)+,d0-d2/a0-a2
        "4E75")               # rts
    rom[NEW_AT:NEW_AT + len(code)] = code
    rom[HOOK_AT + 2:HOOK_AT + 6] = struct.pack(">I", NEW_AT)
    Path(out).write_bytes(bytes(rom))
    print(out, "routine at", hex(NEW_AT), len(code), "bytes:", code.hex(" ", 2))


def z80(path, team):
    import os
    from emu import Emu
    import gen_pregame_song_check as P
    P.Sys95.TEMPLATE = os.environ.get("PREGAME95_SETUP", "")
    e = Emu(path)
    s = P.Sys95()
    s.boot(e)
    s.set_teams(e, team, 22 if team != 22 else 4)
    e.run(4, hold=["DOWN"]); e.run(30); e.run(4, hold=["UP"]); e.run(60)
    e.run(6, hold=["START"]); e.run(200); e.run(6, hold=["START"]); e.run(240)
    z = np.frombuffer(e.serialize()[Z80:Z80 + 0x2000], np.uint8)
    ents = []
    for i in range(64):
        a = 0x100 + 6 * i
        if z[a] != 0 or (z[a + 1] == 0 and z[a + 2] == 0 and z[a + 3] == 0 and i):
            break
        ents.append(f"{z[a + 1]:02X}")
    print(f"home {e.w(HOMETEAM)}: Z80 patches loaded ({len(ents)}):", " ".join(ents))
    print("   slots:", s.playing(e), "  FM voice patches $79-$7E:", " ".join(f"{v:02X}" for v in z[0x79:0x7F]))


if __name__ == "__main__":
    {"tables": lambda: tables(sys.argv[2]), "fix": lambda: fix(sys.argv[2], sys.argv[3]),
     "z80": lambda: z80(sys.argv[2], int(sys.argv[3]))}[sys.argv[1]]()
