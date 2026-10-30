"""A minimal headless libretro frontend for Genesis Plus GX: load a ROM, load a RetroArch savestate, poke and read work
RAM, hold buttons, run frames, grab the screen. Work RAM is the core's SYSTEM_RAM buffer (64 KB, $FF0000-$FFFFFF),
stored as little-endian words: the byte at address A is at (A & $FFFF) ^ 1."""
import ctypes as C
import os
from pathlib import Path

from paths import CORE, ROM

# Joypad ids (libretro): B 0, Y 1, SELECT 2, START 3, UP 4, DOWN 5, LEFT 6, RIGHT 7, A 8, X 9. Genesis Plus GX's
# default 3-button map: Y -> A, B -> B, A -> C.
PAD = {"A": 1, "B": 0, "C": 8, "START": 3, "UP": 4, "DOWN": 5, "LEFT": 6, "RIGHT": 7}

ENV_CB = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO_CB = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
AUDIO_BATCH_CB = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
POLL_CB = C.CFUNCTYPE(None)
STATE_CB = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)


class GameInfo(C.Structure):
    _fields_ = [("path", C.c_char_p), ("data", C.c_void_p), ("size", C.c_size_t), ("meta", C.c_char_p)]


class Emu:
    def __init__(self, rom=ROM, core=CORE):
        """One per process: the core is a single DLL, and a second Emu would take over its callbacks."""
        self.lib = C.CDLL(str(core))
        self.held = set()
        self.held2 = set()                                  # pad 2 (port 1)
        self.frame = None
        self._sysdir = C.c_char_p(str(Path(core).parent).encode())
        self._cbs = [ENV_CB(self._env), VIDEO_CB(self._video), AUDIO_CB(lambda l, r: None),
                     AUDIO_BATCH_CB(lambda d, n: n), POLL_CB(lambda: None), STATE_CB(self._state)]
        L = self.lib
        L.retro_set_environment(self._cbs[0])
        L.retro_init()
        L.retro_set_video_refresh(self._cbs[1])
        L.retro_set_audio_sample(self._cbs[2])
        L.retro_set_audio_sample_batch(self._cbs[3])
        L.retro_set_input_poll(self._cbs[4])
        L.retro_set_input_state(self._cbs[5])
        self._rom = Path(rom).read_bytes()
        self._rombuf = C.create_string_buffer(self._rom, len(self._rom))
        info = GameInfo(str(rom).encode(), C.cast(self._rombuf, C.c_void_p), len(self._rom), None)
        if not L.retro_load_game(C.byref(info)):
            raise RuntimeError("retro_load_game failed")
        L.retro_get_memory_data.restype = C.c_void_p
        L.retro_get_memory_size.restype = C.c_size_t
        L.retro_serialize_size.restype = C.c_size_t
        L.retro_serialize.restype = C.c_bool
        L.retro_unserialize.restype = C.c_bool
        ptr, size = L.retro_get_memory_data(2), L.retro_get_memory_size(2)
        self.ram = (C.c_ubyte * size).from_address(ptr)

    # --- callbacks
    def _env(self, cmd, data):
        cmd &= 0xFFFF
        if cmd in (9, 31):                                  # system / save directory
            C.cast(data, C.POINTER(C.c_char_p))[0] = self._sysdir.value
            return True
        if cmd == 10:                                       # pixel format: accept what the core asks
            self.pixfmt = C.cast(data, C.POINTER(C.c_int))[0]
            return True
        if cmd == 3:                                        # can dupe
            C.cast(data, C.POINTER(C.c_bool))[0] = True
            return True
        return False

    def _video(self, data, w, h, pitch):
        if data and self.want_frame:
            self.frame = (C.string_at(data, h * pitch), w, h, pitch)

    def _state(self, port, device, index, id_):
        if device == 1 and port in (0, 1):
            return 1 if id_ in (self.held if port == 0 else self.held2) else 0
        return 0

    want_frame = False
    PAD = PAD

    # --- control
    def run(self, n=1, hold=(), hold2=()):
        self.held = {self.PAD[b] for b in hold}
        self.held2 = {self.PAD[b] for b in hold2}
        for _ in range(n):
            self.lib.retro_run()

    def load_state(self, path):
        raw = Path(path).read_bytes()
        if raw[:7] == b"RASTATE":
            i = 8
            while i < len(raw):
                tag, size = raw[i:i + 4], int.from_bytes(raw[i + 4:i + 8], "little")
                if tag == b"MEM ":
                    raw = raw[i + 8:i + 8 + size]
                    break
                i += 8 + size + ((-size) & 7)
        self.unserialize(raw)

    def serialize(self):
        n = self.lib.retro_serialize_size()
        buf = C.create_string_buffer(n)
        assert self.lib.retro_serialize(buf, n)
        return buf.raw

    def unserialize(self, raw):
        buf = C.create_string_buffer(raw, len(raw))
        if not self.lib.retro_unserialize(buf, len(raw)):
            raise RuntimeError("unserialize failed")

    # --- RAM ($FFxxxx addresses, or offsets)
    def b(self, a):
        return self.ram[(a & 0xFFFF) ^ 1]

    def setb(self, a, v):
        self.ram[(a & 0xFFFF) ^ 1] = v & 0xFF

    def w(self, a):
        a &= 0xFFFF
        return self.ram[a] | self.ram[a + 1] << 8

    def sw(self, a):
        v = self.w(a)
        return v - 0x10000 if v & 0x8000 else v

    def setw(self, a, v):
        a &= 0xFFFF
        v &= 0xFFFF
        self.ram[a], self.ram[a + 1] = v & 0xFF, v >> 8

    def l(self, a):
        return self.w(a) << 16 | self.w(a + 2)

    def setl(self, a, v):
        self.setw(a, v >> 16)
        self.setw(a + 2, v)

    def screenshot(self, out):
        from PIL import Image
        self.want_frame = True
        self.lib.retro_run()
        self.want_frame = False
        data, w, h, pitch = self.frame
        if getattr(self, "pixfmt", 0) == 2:                 # RGB565
            img = Image.frombuffer("RGB", (w, h), data, "raw", "BGR;16", pitch, 1)
        else:                                               # XRGB8888
            img = Image.frombuffer("RGBX", (w, h), data, "raw", "BGRX", pitch, 1).convert("RGB")
        img.save(out)
