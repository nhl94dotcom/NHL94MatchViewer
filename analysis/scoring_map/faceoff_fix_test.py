"""NOSE4Web's faceoff spot fix, played in the game (2026-11-07, the user approved running the patched ROMs). The fix
replaces Stop4Pen's clamp (docs/FACEOFF_PLACEMENT.md "Decisions for the fix"). Here the game's own penalty check
places each faceoff: from a moment of live play, one player is given the puck at a chosen spot (his pfgoal flag says
which end he attacks), a new PenBuf entry is written with a chosen stoppage code and that player (with the puck on his
own team, every code is called at once: checkfornewpen -> Stop4Pen -> limitfo), and the spot the game sets (fox /
foy) is read. Each ROM is checked against its rule: the original's (the clamp: x to +/-70, the end dot from |y| 166;
icing at +/-600 toward the icing player's end; out of play at the last touch, set here to the same spot) or the
fix's (penalties to the offending team's own end-zone dot on the puck's side; everything else past a blue line, |y|
89, that end's dot on the puck's side, in the neutral zone the nearest neutral dot, y 0 counting as the top half),
then limitfo for the entry's player (a spot past 88 toward the end he attacks moves to that side's neutral dot).
Spots within 4 of a boundary are reported apart (the carried puck sits a unit or two from where it was put).

python faceoff_fix_test.py SYSTEM ROM fixed|original [STATE]   -> prints the agreement and the misses
SYSTEM genesis or snes; an SA-1 SNES ROM is told by its header (its low RAM in BW-RAM, as snes.Emulator reads it)."""
import json
import sys
from pathlib import Path

GOAL, OOP, ICING = 0x0E, 0x06, 0x0C
POSITIONS = [(x, y) for x in (-100, -40, 40, 100) for y in (-250, -190, -140, -110, -70, -30, 30, 70, 110, 140, 190, 250)]


def sgn70(x):
    return 70 if x >= 0 else -70


def expected(rule, code, raw, pfgoal, penalty, snes):
    x, y = raw
    if code == GOAL:
        return (0, 0)
    if code == OOP:
        pass                                     # the last touch: set to the same spot here
    if code == ICING:
        y = -600 if pfgoal else 600
    if rule == "original":
        fx = max(-70, min(70, x))
        fy = y
        if y >= 166:
            fx, fy = sgn70(x), 206
        elif y <= (-167 if snes else -166):
            fx, fy = sgn70(x), -206
    elif penalty:
        fx, fy = sgn70(x), (-206 if pfgoal else 206)
    elif abs(y) >= 89:
        fx, fy = sgn70(x), (206 if y > 0 else -206)
    else:
        fx, fy = sgn70(x), (65 if y >= 0 else -65)
    # limitfo for the entry's player
    if pfgoal and (fy > 88 if snes else fy >= 88):
        fx, fy = sgn70(fx), 65
    elif not pfgoal and fy <= -88:
        fx, fy = sgn70(fx), -65
    return (fx, fy)


def near_boundary(raw, code):
    x, y = raw
    if code == ICING:
        return abs(x) < 4
    return abs(x) < 4 or any(abs(abs(y) - b) < 4 for b in (88, 89, 166, 167))


class Genesis:
    snes = False
    CODES = [OOP, 0x08, 0x0A, ICING, GOAL, 0x10, 0x14, 0x16, 0x1E, 0x24, 0x2A]
    PENALTY = [c for c in range(0x12, 0x2B) if c != 0x14]   # $14: the injury stoppage, no penalty (FallDown)

    def __init__(self, rom):
        from emu import Emu
        from bot_scenario import live_state
        self.e = Emu(rom)
        self.bases = [live_state(self.e, j) for j in range(4)]

    def trial(self, base, k, code, x, y):
        from bot import rec
        e = self.e
        e.unserialize(base)
        for kk in (k, 14):
            e.setw(rec(kk), x & 0xFFFF)
            e.setw(rec(kk) + 0x14, y & 0xFFFF)
            e.setw(rec(kk) + 0x28, 0)
            e.setw(rec(kk) + 0x2A, 0)
        e.setw(0xB7AA, k)                         # puckc: he has the puck
        e.setw(0xBF7C, x & 0xFFFF)                # ltx / lty: he touched it last, here
        e.setw(0xBF7E, y & 0xFFFF)
        e.setw(0xC3A4, 0)
        e.run(2)                                  # settled: the puck at his stick
        sw = lambda a: (lambda v: v - 0x10000 if v >= 0x8000 else v)(e.w(a))
        puck = (sw(rec(14)), sw(rec(14) + 0x14))
        e.setw(0xC3A4, code << 8 | k)             # PenBuf: (penalty byte, player byte), then the end
        e.setw(0xC3A6, 0)
        e.setw(0xC2EA, e.w(0xC2EA) & ~0x0D00)     # gmode (its high byte): clock running, no penalty, none delayed
        pfgoal = bool(e.b(rec(k) + 0x62) & 0x80)
        for _ in range(4):
            e.run(1)
            if e.w(0xC2EA) & 0x0100:
                break
        else:
            return None
        return (sw(0xBF94), sw(0xBF96)), puck, (sw(0xBF7C), sw(0xBF7E)), pfgoal


class Snes:
    snes = True
    CODES = [OOP, 0x08, 0x0A, ICING, GOAL, 0x12, 0x14, 0x16, 0x1A, 0x24, 0x2E]
    PENALTY = [c for c in range(0x14, 0x2F) if c != 0x16]   # $16: the injury stoppage, no penalty (FallDown)
    MOVED = ((0x0100, 0x2000, 0x6100), (0x30F4, 0x35F4, 0x30F4), (0x37F4, 0x47F4, 0x37F4), (0xE700, 0xE868, 0xE700))

    def __init__(self, rom, state=None):
        import ctypes as C
        from snes_emu import SnesEmu
        self.e = SnesEmu(rom=rom)
        data = Path(rom).read_bytes()
        self.sa1 = len(data) > 0x7FD6 and data[0x7FD5] == 0x23
        self.bw = (C.c_ubyte * self.e.lib.retro_get_memory_size(0)).from_address(self.e.lib.retro_get_memory_data(0)) \
            if self.sa1 else None
        if state:
            self.bases = [open(state, "rb").read()]
        elif not self.sa1 and len(data) < 0x200000:   # the 1 MB ROMs: the retail states (2 MB builds boot their own)
            from paths import SNES_STATE_TOP, SNES_STATE_BOTTOM
            self.bases = [open(SNES_STATE_TOP, "rb").read(), open(SNES_STATE_BOTTOM, "rb").read()]
        else:
            self.bases = [self.boot()]

    def at(self, a):
        if self.sa1:
            for lo, hi, to in self.MOVED:
                if lo <= a < hi:
                    return self.bw, to + a - lo
        return self.e.ram, a

    def w(self, a):
        buf, o = self.at(a)
        return buf[o] | buf[o + 1] << 8

    def setw(self, a, v):
        buf, o = self.at(a)
        buf[o], buf[o + 1] = v & 0xFF, (v >> 8) & 0xFF

    def boot(self):
        """Through the menus with START taps until the clock runs, then a few seconds of play: the moment to use."""
        last, ran = None, 0
        for f in range(20000):
            clock = self.w(0x1632)
            ran = ran + 1 if last is not None and clock != last and clock < 300 else ran
            last = clock
            if ran > 3 and f > 2000:
                break
            self.e.held = {3} if (f // 30) % 4 == 0 and f > 300 and ran == 0 else set()
            self.e.lib.retro_run()
        self.e.held = set()
        for _ in range(300):
            self.e.lib.retro_run()
        return self.e.serialize()

    def trial(self, base, k, code, x, y):
        e = self.e
        e.unserialize(base)
        for kk in (k, 14):
            self.setw(0x0D55 + 2 * kk, x & 0xFFFF)
            self.setw(0x0DB7 + 2 * kk, y & 0xFFFF)
        self.setw(0x0AD9, 2 * k)                  # puckc: he has the puck (object x 2)
        self.setw(0x30F8, x & 0xFFFF)             # ltx / lty
        self.setw(0x30FA, y & 0xFFFF)
        self.setw(0x15DE, 0)
        for _ in range(2):
            e.lib.retro_run()                     # settled
        sw = lambda a: (lambda v: v - 0x10000 if v >= 0x8000 else v)(self.w(a))
        puck = (sw(0x0D55 + 28), sw(0x0DB7 + 28))
        self.setw(0x15DE, k << 8 | code)          # PenBuf: (penalty, object), then the end
        self.setw(0x15E0, 0)
        self.setw(0x15D6, 0)                      # gmclock: running
        self.setw(0x15D4, self.w(0x15D4) & ~0x000C)  # gmode: no penalty called, none delayed
        pfgoal = self.w(0x14C3 + 2 * k) != 0
        for _ in range(6):
            e.lib.retro_run()
            if self.w(0x15D6):
                break
        else:
            return None
        return (sw(0x3136), sw(0x3138)), puck, (sw(0x30F8), sw(0x30FA)), pfgoal


def main():
    system, rom, rule = sys.argv[1], sys.argv[2], sys.argv[3]
    state = sys.argv[4] if len(sys.argv) > 4 else None
    g = Genesis(rom) if system == "genesis" else Snes(rom, state)
    ok = bad = edge = none = 0
    misses = []
    for b, base in enumerate(g.bases):
        for k in (3, 4, 9, 10):                    # skaters of both teams: both ends attacked
            for code in g.CODES:
                for x, y in POSITIONS:
                    r = g.trial(base, k, code, x, y)
                    if r is None:
                        none += 1
                        continue
                    spot, puck, touch, pfgoal = r
                    raw = touch if code == OOP else puck  # what Stop4Pen reads: the last touch, or the settled puck
                    want = expected(rule, code, raw, pfgoal, code in g.PENALTY, g.snes)
                    if near_boundary(raw, code):
                        edge += 1
                        continue
                    dot = spot in {(0, 0)} | {(sx, sy) for sx in (-70, 70) for sy in (-206, -65, 65, 206)}
                    drift = rule == "original" and not dot and abs(spot[0] - want[0]) <= 6 and abs(spot[1] - want[1]) <= 6
                    if spot == want or drift:     # the original's off-dot spot follows the skating carrier a frame or two
                        ok += 1
                    else:
                        bad += 1
                        if len(misses) < 25:
                            misses.append(dict(base=b, k=k, code=hex(code), put=(x, y), puck=puck, pfgoal=pfgoal, spot=spot, want=want))
    print(json.dumps(dict(rom=Path(rom).name, rule=rule, agree=ok, differ=bad, near_a_boundary=edge, not_called=none)))
    for m in misses:
        print("  ", m)


if __name__ == "__main__":
    main()
