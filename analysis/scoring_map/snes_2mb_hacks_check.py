"""NOSE4Web's original-layout SNES hacks in McMarkis's 2 MB builds (2026-11-12, bbe2758): snes_vault_hacks_test.py's
parts (Edit Lines on the Best Line, Scoring 1 and the penalty-kill lines; the extra attacker in play; the pick list's
ratings for show max boost; L+R goalie pull; L+R during a whistle or a pause) run on a 2 MB build and its original. The
retail test starts from the retail saved state; here each ROM boots through its own menus with pad 1 on the home team
(snes_shootout_lock_check.person_start) and every read and write goes through Snes (the SA-1 builds' low RAM in BW-RAM).

python snes_2mb_hacks_check.py ORIGINAL HACK OUT [part ...]   (as snes_vault_hacks_test.py: lines play ratings lr ghost)"""
import ctypes as C
import sys
import tempfile
from pathlib import Path

import snes_vault_hacks_test as V
from faceoff_fix_test import Snes

_states = {}


class Game2(V.Game):
    def __init__(self, rom):
        if rom not in _states:
            # pad 1 on the home team, as in the retail state: snes_shootout_lock_check.person_start's menus (Snes.boot's
            # START taps left the LoROM 32-team build with no pad on a team, the computer on both sides)
            from snes_shootout_lock_check import person_start
            e, m = person_start(rom, Path(tempfile.gettempdir()))
            e.run(300)
            # on into play with the clock running (a person's game waits for START at a faceoff)
            last, still = None, 0
            for f in range(4000):
                e.run(1)
                c = m.w(0x1632)
                still = still + 1 if c == last else 0
                last = c
                if still == 0 and f > 120 and m.w(0x15D6) == 0:
                    break
                if still and still % 240 == 0:
                    e.run(8, hold=["START"])
            e.run(60)
            f = Path(tempfile.gettempdir()) / f"nhl94_2mb_{Path(rom).stem}.state"
            f.write_bytes(e.serialize())
            _states[rom] = str(f)
        s = Snes(rom, state=_states[rom])
        self.s, self.e = s, s.e
        self.state = s.bases[0]
        self.e.b = lambda a: s.w(a) & 0xFF
        self.e.w = s.w
        self.e.setw = s.setw
        self.audio = []
        self._acb = C.CFUNCTYPE(C.c_size_t, C.POINTER(C.c_int16), C.c_size_t)(self._audio)
        self.e.lib.retro_set_audio_sample_batch(self._acb)


    def text(self, r, c0, c1):
        # the 2 MB builds' font: lower case 2 past retail's tiles, capitals and digits 3 (2026-11-12)
        out = ""
        for c in range(c0, c1):
            t = self.e.w(V.TEXTMAP + 64 * r + 2 * c)
            # lower case: the SA-1 builds 1 before retail's tile, the LoROM 32-team build 2 past; capitals and digits one
            # further on both (O and 0 share a glyph)
            ch = (t & 0x1FF) - (0x8C if self.s.sa1 else 0x8F)
            if chr(ch).isupper() or chr(ch).isdigit() or chr(ch) in "/:":
                ch -= 1
            out += chr(ch) if 0x20 <= ch < 0x7F else " "
        return out.strip(" ")


V.Game = Game2

if __name__ == "__main__":
    V.main()
