"""NHL '95 (Genesis): how the sound driver shares its voices, for NOSE4Web's MIDI import of bank songs 0, 2 and 3
(2026-11-17). The 68000 side is disassembled (sound95.asm); the Z80 program isn't, so this plays test pieces and
listens. A scratch copy of the ROM (the original untouched; the boot's self-check call at $690 NOPped and the
checksum redone, as NOSE4Web's builds) has a test piece in place of a bank song; the audio is kept and the 68000's
SndNoteCount ($FFFF1E) and slots (SndSeqPtr $FFFDFE) read every frame.

`piece`: the test piece, in blocks (each block's notes on their own MIDI channels; pitches chosen so that no
fundamental is near a harmonic of a lower one, so each can be heard apart):
  fm K    K notes at once on patch $0D (FM, sounds as written), K = 1..9, held 100 frames
  psg K   K notes at once on patch $14 (the square wave), K = 1..4
  mix     6 FM notes and 3 square-wave notes at once
  stagger 9 FM notes starting 25 frames apart, each held to the same end (frame 400 of the block); then a short 10th
          note (40 frames) to see what it takes and whether the taken note comes back after it
  cc      one held FM note with CC1 at 0, 32, 64, 127, then CC7 127 / 64 / 0, then CC10 0 / 64 / 127 (and back)
`front ROM OUT`: the piece as song 0, played from power-on (the title screen starts it); a second run pressing
  through the front-end menus (sound effects) while it plays.
`intermission ROM STATE OUT`: the piece as song 2 from a live state, the period run out (PeriodOver starts song 2).
`count ROM STATE OUT`: SndNoteCount every frame while the game's own songs 0, 2 and 3 play (front end, between
  periods; play with its effects).

The Z80's tables (found in its RAM, Genesis Plus GX's state at 16 + $10000): FM voices 0-5: $78 a free mask (bit set =
free), $79-$7E patch, $85-$8A note, $8B-$90 velocity, $91-$96 MIDI channel, $9D-$A2 a level ($F0); square-wave voices
0-2: $C4-$C6 patch, $C8-$CA note, $CC-$CE velocity, $D0-$D2 MIDI channel; the loaded patches from $0100 (6-byte
entries: 0, id, size, address). Findings (STUDY_NOTES "NHL '95's sound driver: voices"): 6 FM and 3 square voices;
one voice per FM patch; a note with no free voice takes voice 0, and a taken note never comes back.

python gen95_driver_check.py front|intermission|count ROM [STATE] OUT"""
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np

import gen95_music_check as G
import lowload

NOTECOUNT, SEQPTR = 0xFF1E, 0xFDFE
FM, SQ = 0x0D, 0x14
SR = 44100


def apart(lo, hi, k):
    """k notes in lo..hi, none within 60 cents of an integer multiple (2-8) of a lower one's frequency."""
    out = []
    for n in range(lo, hi + 1):
        f = 440 * 2 ** ((n - 69) / 12)
        ok = all(abs(1200 * math.log2(f / (440 * 2 ** ((m - 69) / 12) * h))) > 60 for m in out for h in range(1, 9))
        if ok:
            out.append(n)
        if len(out) == k:
            break
    return out


def w(v):
    b = [v & 0x7F]
    v >>= 7
    if v:
        b.insert(0, 0x80 | (v & 0x7F))
    return b


class Piece:
    def __init__(self):
        self.ev, self.t, self.blocks = [0, 0], 0, []        # no loop points
        self.last = 0

    def at(self, t, data):
        self.ev += w(t - self.last) + data
        self.last = t

    def block(self, name, length, notes):
        """notes: (start, length, channel, patch, note, velocity) relative to the block."""
        t0 = self.t
        evs = []
        for s, ln, ch, pg, n, v in notes:
            evs.append((t0 + s, 0, [0xC0 | ch, pg]))
            evs.append((t0 + s, 1, [0x90 | ch, n, v] + w(ln)))
        for t, _, d in sorted(evs, key=lambda e: (e[0], e[1])):
            self.at(t, d)
        self.blocks.append(dict(name=name, start=t0, length=length, notes=notes))
        self.t = t0 + length

    def cc(self, name, length, note, changes):
        t0 = self.t
        self.at(t0, [0xC0, FM])
        self.at(t0, [0x90, note, 100] + w(length - 10))
        for s, c, v in changes:
            self.at(t0 + s, [0xB0, c, v])
        self.blocks.append(dict(name=name, start=t0, length=length, notes=[(0, length - 10, 0, FM, note, 100)], changes=changes))
        self.t = t0 + length

    def bytes(self):
        return bytes(self.ev + w(30) + [0xFF])


def make_piece():
    p = Piece()
    fm = apart(45, 90, 10)
    sq = apart(50, 84, 5)
    for k in range(1, 10):
        p.block(f"fm {k}", 130, [(0, 100, c, FM, fm[c], 100) for c in range(k)])
    for k in range(1, 5):
        p.block(f"psg {k}", 130, [(0, 100, c, SQ, sq[c], 100) for c in range(k)])
    p.block("mix 6+3", 130, [(0, 100, c, FM, fm[c], 100) for c in range(6)] + [(0, 100, 6 + c, SQ, sq[c], 100) for c in range(3)])
    p.block("stagger", 520, [(25 * c, 400 - 25 * c, c, FM, fm[c], 100) for c in range(9)] + [(300, 40, 9, FM, fm[9], 100)])
    p.cc("cc", 900, fm[3], [(100, 1, 0), (150, 1, 32), (200, 1, 64), (250, 1, 127), (300, 1, 0),
                            (380, 7, 127), (430, 7, 64), (480, 7, 0), (530, 7, 127),
                            (600, 10, 0), (650, 10, 64), (700, 10, 127), (750, 10, 64)])
    return p


def scratch(rom_path, song, data, out):
    rom = bytearray(Path(rom_path).read_bytes())
    _, it = G.stream(bytes(rom), song)
    assert len(data) <= it["size"], (len(data), it["size"])
    rom[it["at"]:it["at"] + len(data)] = data
    if rom[0x690:0x696] == bytes.fromhex("4eb9001a72c0"):
        rom[0x690:0x696] = bytes.fromhex("4e714e714e71")
    words = np.frombuffer(bytes(rom[0x200:]), ">u2")
    struct.pack_into(">H", rom, 0x18E, int(words.sum()) & 0xFFFF)
    p = out / f"scratch_song{song}.bin"
    p.write_bytes(bytes(rom))
    return p


SOUNDS = {0x18: 12, 0x1B: 12, 0x1C: 24}          # patches that sound above the written note (gen95_music_check)


def sounding_hz(note, patch):
    return 440 * 2 ** ((note + SOUNDS.get(patch, 0) - 69) / 12)


def present(x, t0, t1, f0s):
    """For each frequency, its peak's height over the median of the spectrum around it (dB)."""
    seg = x[int(t0 * SR):int(t1 * SR)]
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 2 * len(seg)))
    fr = np.fft.rfftfreq(2 * len(seg), 1 / SR)
    out = []
    for f in f0s:
        m = (fr > f * 0.985) & (fr < f * 1.015)
        around = (fr > f * 0.85) & (fr < f * 1.15) & ~m
        out.append(round(float(20 * np.log10(sp[m].max() / (np.median(sp[around]) + 1e-9))), 1))
    return out


def analyse(x, start_s, p, counts):
    res = []
    for b in p.blocks:
        t0 = start_s + b["start"] / 59.92
        if b["name"] == "stagger":
            rows = []
            for k in range(0, 520, 25):
                hz = [sounding_hz(n[4], n[3]) for n in b["notes"]]
                lv = present(x, t0 + (k + 5) / 59.92, t0 + (k + 22) / 59.92, hz)
                due = [i for i, n in enumerate(b["notes"]) if n[0] <= k + 5 and k + 22 <= n[0] + n[1]]
                rows.append(dict(frame=k, due=due, heard=[i for i, v in enumerate(lv) if v >= 12], levels=lv))
            res.append(dict(block="stagger", windows=rows))
        elif b["name"] == "cc":
            seg_t = []
            for s, c, v in b["changes"] + [(b["length"] - 20, 0, 0)]:
                pass
            hz = 440 * 2 ** ((b["notes"][0][4] - 69) / 12)
            sts = [0] + [s for s, _, _ in b["changes"]]
            ends = sts[1:] + [b["length"] - 15]
            rows = []
            for (s, e), lab in zip(zip(sts, ends), ["start"] + [f"CC{c}={v}" for _, c, v in b["changes"]]):
                seg = x[int((t0 + (s + 5) / 59.92) * SR):int((t0 + (e - 2) / 59.92) * SR)] if e - s > 10 else None
                if seg is None or len(seg) < 2048:
                    continue
                # loudness, and the pitch wobble: instantaneous frequency of the fundamental band over 20 ms windows
                h = 2048
                fs = []
                for i in range(0, len(seg) - h, h // 2):
                    sp = np.abs(np.fft.rfft(seg[i:i + h] * np.hanning(h), 8 * h))
                    fr = np.fft.rfftfreq(8 * h, 1 / SR)
                    m = (fr > hz * 0.9) & (fr < hz * 1.1)
                    fs.append(float(fr[m][np.argmax(sp[m])]))
                rows.append(dict(at=lab, rms=round(float(np.sqrt((seg ** 2).mean()))),
                                 pitch_spread_cents=round(float(1200 * np.log2(max(fs) / min(fs))), 1) if fs else None))
            res.append(dict(block="cc", rows=rows))
        else:
            hz = [sounding_hz(n[4], n[3]) for n in b["notes"]]
            lv = present(x, t0 + 10 / 59.92, t0 + 90 / 59.92, hz)
            res.append(dict(block=b["name"], asked=len(b["notes"]), heard=sum(v >= 12 for v in lv), levels=lv))
    if counts:
        res.append(dict(max_note_count=max(counts)))
    return res


def record(e, frames, hold_fn=None, watch=None):
    from gen_midi_song_check import capture
    buf = capture(e)
    counts = []
    for f in range(frames):
        e.run(1, hold=hold_fn(f) if hold_fn else [])
        counts.append(e.w(NOTECOUNT))
        if watch:
            watch(f)
    x = np.array(buf, float).reshape(-1, 2).mean(1)
    return x, counts


def find_start(x):
    hop = 441
    env = np.array([np.sqrt((x[i:i + hop] ** 2).mean()) for i in range(0, len(x) - hop, hop)])
    i = next(i for i in range(len(env)) if env[i] > 300 and i > 100)
    return i * hop / SR


def front(rom_path, out, presses=False):
    from emu import Emu
    p = make_piece()
    rom = scratch(rom_path, 0, p.bytes(), out)
    e = Emu(str(rom))
    total = 900 + p.t + 200
    hold = (lambda f: ["DOWN"] if f > 1500 and f % 45 < 3 else []) if presses else None
    x, counts = record(e, total, hold)
    if presses:                                     # into the menus first: START at the title, then moving the cursor
        pass
    s = find_start(x)
    import wave
    with wave.open(str(out / f"front{'_presses' if presses else ''}.wav"), "wb") as wv:
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes(np.clip(x, -32768, 32767).astype("<i2").tobytes())
    return dict(start_s=round(s, 2), result=analyse(x, s, p, counts))


def intermission(rom_path, state, out):
    import gen95_organ_resume_check as O
    p = make_piece()
    rom = scratch(rom_path, 2, p.bytes(), out)
    r = O.R(str(rom), state)
    e = r.e
    e.unserialize(r.base)
    e.setw(0xC022, 2)                                # the clock nearly out: PeriodOver starts song 2
    x, counts = record(e, 600 + p.t + 300)
    s = find_start(x)
    return dict(start_s=round(s, 2), result=analyse(x, s, p, counts))


def count(rom_path, state, out):
    """SndNoteCount while the game's own pieces play: from power-on through the title (song 0), then a live state
    run to the period's end (song 2), and play with sound effects."""
    from emu import Emu
    import gen95_organ_resume_check as O
    res = {}
    e = Emu(rom_path)
    c = []
    for f in range(60 * 75):
        e.run(1)
        c.append(e.w(NOTECOUNT))
    res["power-on and title (song 0), 75 s"] = dict(max=max(c), over_24=sum(v > 24 for v in c))
    r = O.R(rom_path, state)
    e = r.e
    e.unserialize(r.base)
    c = []
    for f in range(60 * 60):
        e.run(1)
        c.append(e.w(NOTECOUNT))
    res["play, 60 s (organ songs, effects)"] = dict(max=max(c), over_24=sum(v > 24 for v in c))
    e.unserialize(r.base)
    e.setw(0xC022, 2)
    c = []
    for f in range(60 * 75):
        e.run(1, hold=["START"] if f > 600 and f % 600 == 0 else [])
        c.append(e.w(NOTECOUNT))
    res["period end and the intermission (song 2), 75 s"] = dict(max=max(c), over_24=sum(v > 24 for v in c))
    return res


def main():
    mode = sys.argv[1]
    lowload.gentle()
    if mode == "front":
        out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
        print(json.dumps(front(sys.argv[2], out, "--presses" in sys.argv)))
    elif mode == "intermission":
        out = Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
        print(json.dumps(intermission(sys.argv[2], sys.argv[3], out)))
    elif mode == "count":
        out = Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
        print(json.dumps(count(sys.argv[2], sys.argv[3], out)))


if __name__ == "__main__":
    main()
