"""NHL '95 (Genesis): the game's own pieces (title 0, end of period 2, scouting report 3: songs of the sound bank at
$D8EC, item type 3) decoded, against NOSE4Web's MIDI exports of them (2026-11-17), and each patch's sounding pitch.

`streams ROM`: each piece's channels: patch, notes (count, range as written, lengths in frames), velocities.
`vsmidi ROM MIDI SONG`: every stream channel matched to the MIDI channel holding the same notes (start frame and pitch,
any octave shift): which MIDI channel, the shift, how many notes match.
`pitch ROM OUT PATCH ...`: a scratch copy (the original untouched) whose song 0 is a test piece: for each patch a
program change on channel 0 and the notes 24, 36, 48, 60, 72 held 60 frames, played from power-on (the title screen
starts song 0); each note's fundamental from the audio (autocorrelation), as the MIDI note that pitch is.

The stream format (NOSE4Web's readNhl95Stream): a word of loop points, the loop words, then events: a wait (7 bits a
byte, high bit = more), a status byte when it changes (running status), $9x note velocity length (length as a wait),
$Bx two bytes (controller $75: loop), $Cx / $Ex one byte, $FF the end.

python gen95_music_check.py streams ROM | vsmidi ROM MIDI SONG | pitch ROM OUT PATCH ..."""
import struct
import sys
from collections import Counter
from pathlib import Path

BANK = 0xD8EC


def u16(b, a):
    return b[a] << 8 | b[a + 1]


def items(rom, bank=BANK):
    n = u16(rom, bank)
    out, at = [], bank + 2 + 4 * n
    for i in range(n):
        h = bank + 2 + 4 * i
        size = u16(rom, h + 2)
        out.append(dict(type=rom[h], id=rom[h + 1], at=at, size=size))
        at += size
    return out


def wait(d, p):
    v = 0
    while d[p] & 0x80:
        v = (v << 7) | (d[p] & 0x7F)
        p += 1
    return (v << 7) | d[p], p + 1


def own_bank(rom):
    """NOSE4Web's own bank of new songs (its list, which SndFindBankItem is pointed at: list = list + 16, the game's
    bank, -1, -1, then the items), or None."""
    import re
    pat = re.compile(re.escape(bytes([0x48, 0xE7, 0x78, 0x60, 0x43, 0xF9])) + b"(?s:....)" + re.escape(bytes([0x34, 0x3C, 0x00, 0x03])))
    m = pat.search(rom)
    if not m:
        return None
    lst = struct.unpack_from(">I", rom, m.start() + 6)[0]
    if lst + 16 > len(rom) or struct.unpack_from(">I", rom, lst)[0] != lst + 16:
        return None
    return lst + 16


def stream(rom, song):
    own = own_bank(rom)
    pool = (items(rom, own) if own else []) + items(rom)
    it = next(i for i in pool if i["type"] == 3 and i["id"] == song)
    d = rom[it["at"]:it["at"] + it["size"]]
    nl = u16(d, 0)
    p = 2 + 2 * nl
    frame, st, first, ev = 0, 0, True, []
    while p < len(d):
        w, p = wait(d, p)
        if first:
            first = False
        else:
            frame += w
        if d[p] & 0x80:
            st = d[p]
            p += 1
        c, ch = st & 0xF0, st & 15
        if c == 0x90:
            note, vel = d[p], d[p + 1]
            ln, p = wait(d, p + 2)
            ev.append((frame, "note", ch, note, vel, ln))
        elif c == 0xB0:
            ev.append((frame, "ctl", ch, d[p], d[p + 1], 0))
            p += 2
        elif c in (0xC0, 0xE0):
            ev.append((frame, "prog" if c == 0xC0 else "bend", ch, d[p], 0, 0))
            p += 1
        else:
            break
    return ev, it


def channels(ev):
    out = {}
    prog = {}
    for f, k, ch, a, b, ln in ev:
        if k == "prog":
            prog[ch] = a
        if k == "note":
            out.setdefault((ch, prog.get(ch)), []).append((f, a, b, ln))
    return out


def main():
    mode = sys.argv[1]
    rom = Path(sys.argv[2]).read_bytes()
    if mode == "streams":
        for song in (0, 2, 3):
            ev, it = stream(rom, song)
            print(f"## song {song} at {it['at']:#x}, {it['size']} bytes, {ev[-1][0] if ev else 0} frames")
            for (ch, pg), ns in sorted(channels(ev).items(), key=lambda kv: kv[0][0]):
                print(f"  channel {ch} patch {pg if pg is None else hex(pg)}: {len(ns)} notes, written {min(n[1] for n in ns)}-"
                      f"{max(n[1] for n in ns)}, lengths {Counter(n[3] for n in ns).most_common(3)}, velocities "
                      f"{Counter(n[2] for n in ns).most_common(2)}")
    elif mode == "vsmidi":
        import midi_notes
        mid = midi_notes.read(sys.argv[3])
        song = int(sys.argv[4])
        ev, _ = stream(rom, song)
        # MIDI ticks to frames: division ticks a beat at the file's tempo; the exports write 60 ticks a second at 60 bpm
        tick_frames = lambda t: round(midi_notes.seconds(mid, t) * 60)          # noqa: E731
        mch = {}
        for s, ln, ch, n, v, tr in mid["notes"]:
            mch.setdefault(ch, Counter())[(tick_frames(s), n)] += 1
        for (ch, pg), ns in sorted(channels(ev).items(), key=lambda kv: kv[0][0]):
            mine = Counter((f, n) for f, n, _, _ in ns)
            best = max(((sum((mine & Counter({(f, n - k): c for (f, n), c in m.items()})).values()), mc, k)
                        for mc, m in mch.items() for k in (-24, -12, 0, 12, 24)), default=(0, None, 0))
            print(f"stream channel {ch} patch {pg if pg is None else hex(pg)} ({len(ns)} notes) -> MIDI channel {best[1]}, "
                  f"written {best[2]:+d} in the MIDI, {best[0]} notes match")
    elif mode == "pitch":
        pitch(sys.argv[2], Path(sys.argv[3]), [int(x, 16) for x in sys.argv[4:]])


import os
NOTES = tuple(int(n) for n in os.environ.get("NOTES", "24,36,48,60,72").split(","))
ON, OFF = 60, 20


def pitch(rom_path, out, patches):
    import numpy as np
    from emu import Emu
    from gen_midi_song_check import capture
    rom = bytearray(Path(rom_path).read_bytes())
    _, it = stream(bytes(rom), 0)
    ev = [0, 0]                                         # no loop points
    first = True

    def w(v):
        b = [v & 0x7F]
        v >>= 7
        while v:
            b.insert(0, 0x80 | (v & 0x7F))
            v >>= 7
        return b
    t = 0
    for pg in patches:
        ev += w(0 if first else ON + OFF) + [0xC0, pg]
        first = False
        for i, n in enumerate(NOTES):
            ev += w(0 if i == 0 else ON + OFF) + [0x90, n, 100] + w(ON)
    ev += w(ON + OFF) + [0xFF]
    assert len(ev) <= it["size"], (len(ev), it["size"])
    rom[it["at"]:it["at"] + len(ev)] = bytes(ev)
    if rom[0x690:0x696] == bytes.fromhex("4eb9001a72c0"):   # the boot's ROM self-check call NOPped, as NOSE4Web's
        rom[0x690:0x696] = bytes.fromhex("4e714e714e71")       # builds do (it fails on any changed byte)
    import numpy as _np                                 # the header checksum too
    words = _np.frombuffer(bytes(rom[0x200:]), ">u2")
    struct.pack_into(">H", rom, 0x18E, int(words.sum()) & 0xFFFF)
    out.mkdir(parents=True, exist_ok=True)
    scratch = out / "scratch_pitch.bin"
    scratch.write_bytes(bytes(rom))
    e = Emu(str(scratch))
    buf = capture(e)
    e.run(1200 + len(patches) * len(NOTES) * (ON + OFF) + 600)
    x = np.array(buf, float).reshape(-1, 2).mean(1)
    sr = 44100
    import wave
    with wave.open(str(out / "patches.wav"), "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(sr)
        wv.writeframes(struct.pack(f"<{len(buf)}h", *buf))
    hop = 441
    env = np.array([np.sqrt((x[i:i + hop] ** 2).mean()) for i in range(0, len(x) - hop, hop)])
    t0 = next(i for i in range(200, len(env)) if env[i] > 500) * hop / sr      # the first test note (after the boot)
    j = 0
    for pg in patches:
        res = []
        for n in NOTES:
            a = int((t0 + j * (ON + OFF) / 59.92 + 0.08) * sr)
            j += 1
            seg = x[a:a + int(0.4 * sr)]
            if len(seg) < 1000:
                res.append((n, None))
                continue
            sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 4 * len(seg)))
            fr = np.fft.rfftfreq(4 * len(seg), 1 / sr)
            cands = np.exp(np.linspace(np.log(20), np.log(2000), 600))       # harmonic sum: the fundamental
            hs = [sum(np.interp(f * k, fr, sp) / k ** 0.5 for k in range(1, 6)) for f in cands]
            f0 = cands[int(np.argmax(hs))]
            flat = float(np.exp(np.mean(np.log(sp[(fr > 50) & (fr < 8000)] + 1e-9))) / (np.mean(sp[(fr > 50) & (fr < 8000)]) + 1e-9))
            res.append((n, round(float(69 + 12 * np.log2(f0 / 440)), 1), round(flat, 2), int(np.sqrt((seg ** 2).mean()))))
        print(f"patch {pg:#04x}: (written note, sounds as MIDI note, spectral flatness (1 noise, 0 a tone), rms) {res}", flush=True)


if __name__ == "__main__":
    main()
