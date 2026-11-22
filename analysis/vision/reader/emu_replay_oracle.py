"""The oracle test of "replay the game in the emulator to follow a video" (2026-11-22). A recorded Genesis game's true
memory snapshot (full.bin, all of work RAM but the stack's end) put into the headless emulator in play, then the
recorded controller bytes ($BEEF / $BEF1) fed frame by frame, matched by the game's frame counter $B03E (three
alignments). Printed: the step each record first leaves the recording (position over 4 units or speed over 600 off),
person or computer. Result (VIEWER_NOTES): exact for about 10 frames, then the computer's skaters leave one by one at
the same steps whatever the pads' alignment: their decisions take state a recording (and a video) doesn't hold.
python emu_replay_oracle.py CAPTURE_NAME SNAPSHOT_INDEX"""
import gzip, json, struct, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scoring_map"))
import gen_ot_check as G
from emu import Emu

HOME = Path.home() / "Documents/NHL94 Viewer"
name = sys.argv[1]
cap = HOME / "captures" / name
meta = json.loads((cap / "capture.json").read_text())
blocks = meta["blocks"]
rec = 8 + sum(n for _, n in blocks)
fast = gzip.open(cap / "fast.bin.gz").read()
full = gzip.open(cap / "full.bin.gz").read()
NF, NU = len(fast) // rec, len(full) // (8 + 65536)
fa = np.frombuffer(fast[:NF * rec], np.uint8).reshape(NF, rec)
ft = np.array([struct.unpack_from("<q", fast, i * rec)[0] for i in range(NF)])
ut = np.array([struct.unpack_from("<q", full, i * (8 + 65536))[0] for i in range(NU)])
off = {}
p = 8
for a, n in blocks:
    off[a] = (p, n); p += n
def fb(i, addr):                       # a byte of fast sample i at 68000 address addr (low 16 bits)
    a = (addr & 0xFFFF) ^ 1
    for base, (p0, n) in off.items():
        if base <= a < base + n:
            return int(fa[i, p0 + a - base])
    raise KeyError(hex(addr))
def fw(i, addr):
    a = addr & 0xFFFF
    for base, (p0, n) in off.items():
        if base <= a < base + n - 1:
            return int(fa[i, p0 + a - base]) | int(fa[i, p0 + a - base + 1]) << 8
    raise KeyError(hex(addr))
def sw(v): return v - 0x10000 if v & 0x8000 else v
FRAME, PAD1, PAD2, SCREEN, CLOCK, GSP = 0xB03E, 0xBEEF, 0xBEF1, 0xFFF7, 0xC468, 0xC466
BASE, SZ = 0xB04A, 0x80
BITS = [(0x01, "UP"), (0x02, "DOWN"), (0x04, "LEFT"), (0x08, "RIGHT"), (0x10, "B"), (0x20, "C"), (0x40, "A"), (0x80, "START")]
def held(v): return [n for b, n in BITS if v & b]
print(name, "fast samples", NF, "full snapshots", NU, "seconds", round((ft[-1] - ft[0]) / 1000))
fc = np.array([fw(i, FRAME) for i in range(NF)])
print("frame counter steps (first 2000):", dict(zip(*np.unique(np.diff(fc[:2000]).astype(np.int16), return_counts=True))))

rom = str(HOME / "roms" / (meta["rom_crc32"][0] + "_" + meta["rom_crc32"][1] + ".bin"))
e = Emu(rom)
G.to_setup(e, Path.home() / "NHL94_scoring_map/runs/replay_recon")
assert G.into_play(e), "never reached play"
base_state = e.serialize()

def positions_emu():
    return [(e.sw(BASE + SZ * k), e.sw(BASE + SZ * k + 0x14)) for k in range(15)]
def positions_rec(i):
    return [(sw(fw(i, BASE + SZ * k)), sw(fw(i, BASE + SZ * k + 0x14))) for k in range(15)]

u = int(sys.argv[2])
snap = np.frombuffer(full, np.uint8, 65536, u * (8 + 65536) + 8)
i0 = int(np.searchsorted(ft, ut[u]))
f_snap = int(snap[0xB03E]) | int(snap[0xB03F]) << 8
samp = {}
for q in range(i0, min(NF, i0 + 800)):
    samp.setdefault(int(fc[q]), q)
FIELDS = dict(x=0x00, y=0x14, vx=0x28, vy=0x2A, anim=0x58, ass=0x38, assn=0x36, face=0x54, timer=0x40)
for shift in (0, 1, -1):
    e.unserialize(base_state)
    for a in range(0xFEC0):
        e.ram[a] = int(snap[a])
    first = {}
    print("pad shift", shift)
    for step in range(1, 140):
        want = (f_snap + step) & 0xFFFF
        q = samp.get((want + shift) & 0xFFFF, samp.get(want))
        p1, p2 = (fb(q, PAD1), fb(q, PAD2)) if q is not None else (0, 0)
        e.run(1, hold=held(p1), hold2=held(p2))
        q = samp.get(want)
        if q is None: continue
        for k in list(range(12)) + [14]:
            if k in first: continue
            r = BASE + SZ * k
            dx = abs(e.sw(r) - sw(fw(q, r))) + abs(e.sw(r + 0x14) - sw(fw(q, r + 0x14)))
            dv = abs(e.sw(r + 0x28) - sw(fw(q, r + 0x28))) + abs(e.sw(r + 0x2A) - sw(fw(q, r + 0x2A)))
            da = e.w(r + 0x58) != fw(q, r + 0x58)
            if dx > 4 or dv > 600:
                first[k] = step
                ctl = bool(fb(q, r + 0x62) & 8)
                print(f"  step {step}: record {k} ({'person' if ctl else 'computer'}) leaves: position off {dx}, speed off {dv}, anim emu ${e.w(r + 0x58):04X} rec ${fw(q, r + 0x58):04X}, assignment emu {e.b(r + 0x38 + e.w(r + 0x36))} rec {fb(q, r + 0x38 + fw(q, r + 0x36))}, seed emu ${e.l(0xD066):08X}")
    print("  never left in 140 frames:", [k for k in list(range(12)) + [14] if k not in first])
