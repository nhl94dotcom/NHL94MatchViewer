"""NOSE4Web's per-home-team crowd colours, played (2026-11-27; NHL_95_crowd.bin BB527F78, NHL94_crowd.smc C3C91C98,
nhl94_2026_crowd.sfc 34ACFAB3: "every team's crowd in its banner's two colours"), each build against its base ROM.

Static: the bytes that differ from the base (runs), the hook and its table (4 words a team: the banner's two colours
each with a darker shade; $FFFF keeps the base's), the checksum handling.
- SNES: setplayercolors' `jsl SetTeamColors` ($9F:B902 retail) becomes a jsl to the hook, which calls SetTeamColors
  and then writes palbuffer row 1 colours 8-11 and their sprite copy (row 9 colours 8-11) from the table by HomeTeam
  ($1C98); setplayercolors then sends all 256 colours. setplayercolors runs from setupice, ExitStatsScreen and
  StartHL2 (highlights), so every reload of the uniforms reloads the crowd too.
- Genesis (NHL '95): setupIceRinkPal ($7D6F0) jumps to the hook, which copies the rink palette as before and then by
  HomeTeam ($FFBF54) moves up to 4 words from its table.

Run time, each (ROM, home team) in its own process (one core a process):
- SNES: a computer game (snes_momentum_blocks_check.boot, Opt1team $7E34BE set to the team before START); moments:
  play, a pause into the instant replay and back, a pause into the stats and back, the period's end, the break and
  period 2. At each: HomeTeam, colour memory (CGDATA in the state's PPU block, +64, big-endian words) and palbuffer
  ($7E35F4) rows 0-15, the flags, a screenshot, and the crowd's pixels (those that change when every BG2 cell naming
  a crowd tile, 1-65 (showcrowd's frames), is put on an all-zero tile). At one play moment the colour poke: each of
  the 8 entries the hook writes set to magenta in a copy of the state, the frame drawn: the pixels that change, split
  by the crowd's pixels, the rest of BG2 (the ice) and everything else (BG1, sprites).
- Genesis: Game Setup with the home team set, START until the clock runs: whether play is reached (the clock
  counting down, HomeTeam the team), palfadenew and colour memory lines 0-3.
Then each build against its base, team by team: the colour entries that differ at each moment (expected: only the 8,
holding the table's values or the base's where $FFFF), the screenshots' differing pixels inside and outside the
crowd's pixels, and whether the two games ran alike (the moments' flags and clock).

python crowd_colours_check.py BASE BUILD OUT [TEAM ...]
python crowd_colours_check.py run ROM OUT TAG TEAM   (one game: what the first form runs in a subprocess)"""
import ctypes as C
import json
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SN_PALBUF, SN_HOMETEAM, SN_OPT1, SN_SFLAGS, SN_SFHOR, SN_GSP, SN_CLOCK, SN_PSITEM = 0x35F4, 0x1C98, 0x34BE, 0x15D8, 0x15DA, 0x1630, 0x1632, 0x0D15
CROWD_TILES = range(1, 66)


def runs(a, b, gap=8):
    out = []
    for i in (k for k in range(min(len(a), len(b))) if a[k] != b[k]):
        if out and i - out[-1][1] < gap:
            out[-1][1] = i
        else:
            out.append([i, i])
    return [(x, y - x + 1) for x, y in out]


def static(base, build):
    a, b = Path(base).read_bytes(), Path(build).read_bytes()
    R = dict(base=Path(base).name, build=Path(build).name, sizes=[len(a), len(b)],
             runs=[(f"${x:X}", n, a[x:x + min(n, 12)].hex(), b[x:x + min(n, 16)].hex()) for x, n in runs(a, b)])
    if build.lower().endswith((".smc", ".sfc")):
        # the hook: a jsl (22 lo hi bank) replacing setplayercolors' jsl SetTeamColors; its table: lda.l tbl,x (BF)
        for x, n in runs(a, b):
            if n <= 4 and a[x - 1:x] == b"\x22" if x else False:
                tgt = b[x] | b[x + 1] << 8 | b[x + 2] << 16
                old = a[x] | a[x + 1] << 8 | a[x + 2] << 16
                R["call"] = dict(at=f"${x - 1:X}", was=f"jsl ${old:06X}", now=f"jsl ${tgt:06X}")
                f = snes_file(b, tgt)
                code = b[f:f + 0x60]
                R["hook_bytes"] = code.hex()
                k = code.find(b"\xbf")
                tbl = code[k + 1] | code[k + 2] << 8 | code[k + 3] << 16
                R["table"] = f"${tbl:06X}"
                R["writes"] = [f"$7E{code[j + 1] | code[j + 2] << 8:04X}" for j in range(len(code) - 3) if code[j] == 0x8F and code[j + 3] == 0x7E]
                R["team_reg"] = f"${code[code.find(b'\xad') + 1] | code[code.find(b'\xad') + 2] << 8:04X}"
                tf = snes_file(b, tbl)
                n_teams = 32 if len(b) > 0x100000 else 28
                R["table_words"] = [list(struct.unpack_from("<4H", b, tf + 8 * t)) for t in range(n_teams)]
    else:
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
        hook = next((x for x, n in runs(a, b) if b[x:x + 2] == b"\x4e\xf9"), None)
        if hook is not None:
            tgt = struct.unpack_from(">I", b, hook + 2)[0]
            R["jump"] = dict(at=f"${hook:X}", to=f"${tgt:X}")
            lines, pc = [], tgt
            for _ in range(40):
                ins = next(md.disasm(b[pc:pc + 10], pc), None)
                if ins is None:
                    lines.append(f"${pc:X}: {b[pc:pc + 4].hex()} not an instruction")
                    break
                lines.append(f"${pc:X}: {ins.mnemonic} {ins.op_str}")
                if ins.mnemonic in ("rts", "jmp"):
                    break
                pc += ins.size
            R["hook"] = lines
            R["vectors"] = {"line-F $2C": f"${struct.unpack_from('>I', b, 0x2C)[0]:08X}", "illegal $10": f"${struct.unpack_from('>I', b, 0x10)[0]:08X}"}
    return R


def snes_file(data, addr):
    """File offset of a SNES address: LoROM banks $80-$BF (retail), or the SA-1 builds' mapping (banks $00-$3F /
    $80-$BF LoROM-style through the Super MMC's default: bank $80 + n -> file n * $8000)."""
    bank, off = addr >> 16, addr & 0xFFFF
    return ((bank & 0x7F) * 0x8000) + (off - 0x8000)


# ------------------------------------------------------------------ SNES game
class Snes:
    def __init__(self, rom, out, team):
        import snes_momentum_blocks_check as B
        self.e, self.m = B.boot(rom, 0, before_start=lambda e, m: (m.setw(SN_OPT1, team), m.setw(SN_HOMETEAM, team)))
        self.restore = None                         # the base's values of the hooked entries (set by main)
        self.out, self.team = out, team
        self.vram = (C.c_ubyte * self.e.lib.retro_get_memory_size(3)).from_address(self.e.lib.retro_get_memory_data(3))
        self.moments, self.f = [], 0

    def raw(self):
        n = self.e.lib.retro_serialize_size()
        buf = (C.c_ubyte * n)()
        self.e.lib.retro_serialize(buf, n)
        return bytes(buf)

    def ppu(self, raw=None):
        raw = raw or self.raw()
        i = raw.index(b"PPU:")
        return raw[i + 11:i + 11 + int(raw[i + 4:i + 10])], i + 11

    def flags(self):
        m = self.m
        s = m.w(SN_SFLAGS)
        return dict(paused=bool(s & 1), replay=bool(s & 0x0800), hor=m.w(SN_SFHOR) != 0, gsp=m.w(SN_GSP),
                    clock=m.w(SN_CLOCK), home=m.w(SN_HOMETEAM))

    def step(self, n=1, hold=()):
        for _ in range(n):
            self.e.run(1, hold=list(hold))
            self.f += 1

    def press(self, b, after=40):
        self.step(4, [b])
        self.step(after)

    def bg2(self, p):
        o = 14 + 11
        sc, scs = struct.unpack_from(">H", p, o)[0], struct.unpack_from(">H", p, o + 9)[0]
        nb = struct.unpack_from(">H", p, o + 7)[0]
        return sc, (0x1000 if scs == 3 else 0x800 if scs in (1, 2) else 0x400), nb

    def shot(self, st, poke=None, hide_crowd=False, put=None):
        e = self.e
        s2 = bytearray(st)
        p, pi = self.ppu(st)
        if poke is not None:
            s2[pi + 64 + 2 * poke:pi + 66 + 2 * poke] = (0x7C1F).to_bytes(2, "big")
        for entry, v in (put or {}).items():       # colour memory entries given values
            s2[pi + 64 + 2 * entry:pi + 66 + 2 * entry] = v.to_bytes(2, "big")
        e.lib.retro_unserialize(C.cast(C.create_string_buffer(bytes(s2), len(s2)), C.c_void_p), len(s2))
        if hide_crowd:
            sc, words, nb = self.bg2(p)
            vr = bytes(self.vram)
            zero = next(t for t in range(1024) if not any(vr[2 * nb + 32 * t:2 * nb + 32 * t + 32]))
            for a in range(sc, sc + words):
                v = self.vram[2 * a] | self.vram[2 * a + 1] << 8
                if (v & 0x3FF) in CROWD_TILES:
                    v = v & ~0x3FF | zero
                    self.vram[2 * a], self.vram[2 * a + 1] = v & 0xFF, v >> 8
        q = self.out / "_shot.png"
        e.screenshot(q)
        return np.asarray(Image.open(q).convert("RGB"))

    def moment(self, tag, poke=False):
        st = self.raw()
        p, _ = self.ppu(st)
        cg = [struct.unpack_from(">H", p, 64 + 2 * i)[0] for i in range(256)]
        pal = [self.m.w(SN_PALBUF + 2 * i) for i in range(256)]
        base = self.shot(st)
        crowd = (self.shot(st, hide_crowd=True) != base).any(axis=2)
        n = len(self.moments)
        Image.fromarray(base).save(self.out / f"{n:02d}_{tag.replace(' ', '_')}.png")
        np.save(self.out / f"{n:02d}_crowdmask.npy", crowd)
        M = dict(n=n, tag=tag, frame=self.f, **self.flags(), cgram=[f"{x:04X}" for x in cg], palbuffer=[f"{x:04X}" for x in pal],
                 crowd_px=int(crowd.sum()), rink_palette_on=cg[:16] == pal[:16])
        if self.restore:
            # the hook's own effect on this frame: the same state with the 8 entries put back to the base's values
            back = self.shot(st, put=self.restore)
            d = (back != base).any(axis=2)
            M["hook_px_crowd"], M["hook_px_elsewhere"] = int((d & crowd).sum()), int((d & ~crowd).sum())
            if M["hook_px_elsewhere"] or n == 0:
                img = base.copy()
                img[d & crowd] = (0, 255, 0)
                img[d & ~crowd] = (255, 0, 0)
                Image.fromarray(img).save(self.out / f"{n:02d}_hook_pixels.png")
                ys, xs = np.nonzero(d & ~crowd)
                M["elsewhere_box"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None
        if poke:
            # the other BG2 pixels (the ice): those that change when all of BG2 is hidden, less the crowd's
            sc, words, nb = self.bg2(p)
            self.e.lib.retro_unserialize(C.cast(C.create_string_buffer(st, len(st)), C.c_void_p), len(st))
            vr = bytes(self.vram)
            zero = next(t for t in range(1024) if not any(vr[2 * nb + 32 * t:2 * nb + 32 * t + 32]))
            for a in range(sc, sc + words):
                v = self.vram[2 * a] | self.vram[2 * a + 1] << 8
                v = v & ~0x3FF | zero
                self.vram[2 * a], self.vram[2 * a + 1] = v & 0xFF, v >> 8
            q = self.out / "_shot.png"
            self.e.screenshot(q)
            bg2 = (np.asarray(Image.open(q).convert("RGB")) != base).any(axis=2)
            res = {}
            for entry in [16 + c for c in range(8, 12)] + [144 + c for c in range(8, 12)]:
                d = (self.shot(st, poke=entry) != base).any(axis=2)
                res[f"{entry // 16},{entry % 16}"] = dict(crowd=int((d & crowd).sum()), ice=int((d & bg2 & ~crowd).sum()),
                                                          other=int((d & ~bg2).sum()))
            M["poke"] = res
        self.e.lib.retro_unserialize(C.cast(C.create_string_buffer(st, len(st)), C.c_void_p), len(st))
        self.moments.append(M)

    def pause_item(self, item, tag):
        m = self.m
        self.press("START", 90)
        self.moment(f"{tag} pause menu")
        for _ in range(40):
            if m.w(SN_PSITEM) == item:
                break
            self.press("DOWN")
        self.press("A", 300)
        self.moment(f"{tag} item {item}")
        for k in range(10):
            self.press("START" if k % 2 == 0 else "A", 240)
            if m.w(SN_SFLAGS) & 1 and not m.w(SN_SFLAGS) & 0x0800:
                break
        for _ in range(40):
            if m.w(SN_PSITEM) == 0:
                break
            self.press("UP")
        self.press("START", 240)
        self.moment(f"{tag} after item {item}")


def run_snes(rom, out, team, restore=None):
    g = Snes(rom, out, team)
    g.restore = restore
    g.step(300)
    g.moment("play", poke=True)
    g.step(900)
    g.moment("play later")
    g.pause_item(1, "replay")
    g.step(300)
    g.pause_item(4, "stats")
    g.step(300)
    g.moment("after the pauses")
    m = g.m
    m.setw(SN_CLOCK, 2)
    first, between = None, 0
    for k in range(160):
        fl = g.flags()
        g.step(30, ["START"] if k % 4 == 3 and (fl["paused"] or fl["hor"] or fl["gsp"] == 0) else [])
        fl = g.flags()
        if k % 8 == 4 and fl["gsp"] == 0 and between < 6:
            g.moment(f"period end {k}")
            between += 1
        if fl["gsp"] == 1:
            first = fl["clock"] if first is None else first
            if not fl["paused"] and not fl["hor"] and fl["clock"] < first:
                break
    g.step(600)
    g.moment("period 2")
    return g.moments


# ------------------------------------------------------------------ Genesis (NHL '95)
def run_gen95(rom, out, team):
    from emu import Emu
    from gen95_fight_check import to_setup, ROW
    from gen_title_screen_check import gen_word, state
    e = Emu(rom)
    to_setup(e)
    e.setb(ROW + 1, team)
    e.setb(ROW + 2, (team + 1) % 26)
    e.run(30)
    last, f = None, 0
    for f in range(60 * 120):
        e.run(1, hold=["START"] if f % 240 == 0 else [])
        c = e.w(0xC022)
        if e.w(0xC020) == 0 and last is not None and 0 < c < last:
            break
        last = c
    reached = e.w(0xC020) == 0 and last is not None and 0 < e.w(0xC022) <= 600
    e.run(300)
    _, cram, _, _ = state(e)
    e.screenshot(out / "00_play.png")
    return [dict(n=0, tag="play", frame=f, reached_play=bool(reached), home=e.w(0xBF54), clock=e.w(0xC022),
                 palfadenew=[f"{e.w(0xB942 + 2 * i):03X}" for i in range(64)], cgram=[f"{gen_word(c):03X}" for c in cram[:64]])]


def compare(base_dir, build_dir, st):
    A = json.loads((base_dir / "moments.json").read_text())
    B = json.loads((build_dir / "moments.json").read_text())
    rows = []
    hooked = [16 + c for c in range(8, 12)] + [144 + c for c in range(8, 12)]
    words = None
    if "table_words" in st:
        words = st["table_words"]
    for a, b in zip(A, B):
        r = dict(tag=b["tag"], same_moment=all(a.get(k) == b.get(k) for k in ("gsp", "clock", "paused", "replay", "hor", "home")),
                 home=b.get("home"))
        if "cgram" in a and len(a["cgram"]) == 256:
            # palbuffer (the game's own colours, the same whatever the game's course): only the 8 may differ
            pdiff = [i for i in range(256) if a["palbuffer"][i] != b["palbuffer"][i]]
            r["palbuffer_differs_outside_the_8"] = [i for i in pdiff if i not in hooked]
            r["rink_palette_on"] = b["rink_palette_on"]
            if words is not None and b.get("home") is not None and b["home"] < len(words):
                tw = words[b["home"]]
                bad = {}
                for i in hooked:
                    k = (i % 16) - 8
                    want = int(a["palbuffer"][i], 16) if tw[k] == 0xFFFF else tw[k]
                    if int(b["palbuffer"][i], 16) & 0x7FFF != want & 0x7FFF:
                        bad[f"palbuffer {i // 16},{i % 16}"] = [b["palbuffer"][i], f"{want:04X}"]
                    if b["rink_palette_on"] and int(b["cgram"][i], 16) & 0x7FFF != want & 0x7FFF:
                        bad[f"CGRAM {i // 16},{i % 16}"] = [b["cgram"][i], f"{want:04X}"]
                r["not_as_table"] = bad
            if r["same_moment"]:
                r["cgram_differs_outside_the_8"] = [i for i in range(256) if a["cgram"][i] != b["cgram"][i] and i not in hooked]
            for k in ("hook_px_crowd", "hook_px_elsewhere", "elsewhere_box", "crowd_px"):
                r[k] = b.get(k)
            if "poke" in b:
                r["poke"] = b["poke"]
        else:
            r.update(reached_play=b.get("reached_play"), base_reached_play=a.get("reached_play"), home=b.get("home"))
        rows.append(r)
    return rows


def main():
    if sys.argv[1] == "run":
        rom, out, tag, team = sys.argv[2], Path(sys.argv[3]), sys.argv[4], int(sys.argv[5])
        out.mkdir(parents=True, exist_ok=True)
        restore = {int(k): v for k, v in json.loads(sys.argv[6]).items()} if len(sys.argv) > 6 else None
        M = run_snes(rom, out, team, restore) if rom.lower().endswith((".smc", ".sfc")) else run_gen95(rom, out, team)
        (out / "moments.json").write_text(json.dumps(M))
        return
    base, build, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    teams = [int(t) for t in sys.argv[4:]] or [1]
    out.mkdir(parents=True, exist_ok=True)
    st = static(base, build)
    (out / "static.json").write_text(json.dumps(st, indent=1))
    res = {}
    for team in teams:
        restore = []
        if base.lower().endswith((".smc", ".sfc")):
            # the base's values of the 8 entries: RinkPalette row 1 colours 8-11, as palbuffer holds them on the base
            a = Path(base).read_bytes()
            pal = 0xD50B6
            restore = [json.dumps({str(r * 16 + c): struct.unpack_from("<H", a, pal + 2 * (16 + c))[0] for r in (1, 9) for c in range(8, 12)})]
        procs = [subprocess.Popen([sys.executable, __file__, "run", rom, str(out / f"{tag}_{team}"), tag, str(team)] + (restore if tag == "build" else []))
                 for tag, rom in (("base", base), ("build", build))]
        for p in procs:
            p.wait()
        res[team] = compare(out / f"base_{team}", out / f"build_{team}", st)
        print(f"team {team}:", flush=True)
        for r in res[team]:
            print("  ", json.dumps({k: v for k, v in r.items() if k != "poke"}), flush=True)
            if "poke" in r:
                print("     poke:", r["poke"], flush=True)
    (out / "compare.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
