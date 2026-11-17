"""NHL '95 (Genesis): NOSE4Web's replaced organ song prototypes, played (2026-11-16). SndFindBankItem's
lea (SndBanks).l,a1 ($BAD0) points at a ROM list {override bank, $0000D8EC, -1, -1}: the override bank (free room,
the normal bank layout) holds only the replaced songs and is searched first. NHL_95_song4F_medley.bin (song $4F; list
$1A7314, bank $1A7324), W18_song3A_medley.bin (song $3A; $1DADF8); every team's period-start slot (the team song
table, 6 bytes a team, slot 0) set to the new song: Brass Bonanza then William Tell, 461 notes, 42.7 s.

Modes (results printed, WAVs to OUT):
  medley ORIG BUILD STATE OUT   the clock run out twice (periods 1 -> 2 -> 3), C through the intermissions: the
      period-start song on each ROM (its id, slot, pointer, how long it plays, how it ends), the song's events walked
      from its data (notes by channel, program changes, velocities), the most notes pending at once (SndNoteCount
      $FFFF1E; SndNotes holds 32), notes left pending 300 frames after it ends, and a WAV of the build's.
  same ORIG BUILD STATE OUT     what must not change: the title music (power-on, 3,000 frames), a home goal's song,
      and 1,800 frames of live play: the core's audio sample for sample, and the slots' ids frame by frame.
  pitch NHL94ROM NHL95ROM STATE OUT
      Brass Bonanza on both games: NHL '94's $40 (Hartford's period-start song: HomeTeam set to Hartford), NHL '95's
      $3D (a scratch copy with every period-start slot $3D): each played into a WAV; the pitch of every note's
      strongest peak; the semitone shift that best lines the two up; and the songs' stored notes.
  resume ORGAN_RESUME_ROM MEDLEY_ROM STATE OUT
      a scratch copy of the organ-resume build with the medley's override list and bank moved to free room ($BAD0
      repointed) and the period-start slots set: gen95_organ_resume_check's song cases (Resume, Game Stats, Instant
      Replay) on the medley."""
import json
import struct
import sys
import wave
from pathlib import Path

import numpy as np

from emu import Emu
from gen_midi_song_check import capture
import gen95_organ_resume_check as O
import lowload

NOTECOUNT, SNDNOTES = 0xFF1E, 0xFE9E
TABLE95 = 0x67A20                    # retail NHL '95 / the medley: the period-start bytes (team x 6)


def walk(rom, ptr):
    """NHL '95 song events from its start (SndUpdate's parsing): notes by channel, programs, velocities, loops."""
    s = rom[ptr:ptr + 0x8000]
    d5 = ((s[0] << 8) | s[1]) * 2 + 2
    st, ch_notes, progs, vel, n, loop, end = 0, {}, [], {}, 0, None, None
    while n < 20000:
        n += 1
        while s[d5] & 0x80:
            d5 += 1
        d5 += 1
        if s[d5] & 0x80:
            st = s[d5]
            d5 += 1
        t, ch = st & 0xF0, st & 0xF
        if t == 0x90:
            ch_notes[ch] = ch_notes.get(ch, 0) + 1
            vel.setdefault(ch, set()).add(s[d5 + 1])
            d5 += 2
            while s[d5] & 0x80:
                d5 += 1
            d5 += 1
        elif t == 0xB0:
            if s[d5] == 0x75:
                loop = hex(d5)
                break
            d5 += 2
        elif t in (0xC0, 0xE0):
            if t == 0xC0:
                progs.append((ch, s[d5]))
            d5 += 1
        elif st == 0xFF:
            end = hex(d5)
            break
        else:
            end = f"other status {st:#x} at {d5:#x}"
            break
    return dict(notes_by_channel=ch_notes, programs=progs, velocities={c: sorted(v)[:6] for c, v in vel.items()},
                loop=loop, end=end)


def period_songs(rom, state, out, wav_name=None, periods=2):
    r = O.R(rom, state)
    e = r.e
    e.unserialize(r.base)
    data = Path(rom).read_bytes()
    res = []
    for p in range(periods):
        e.setw(O.CLOCK, 2)
        g0 = e.w(O.GSP)
        a_start = None
        for f in range(60 * 120):
            r.frame(1, ["C"] if f % 120 < 4 else [])
            if e.w(O.GSP) > g0 and O.song_slot(e) is not None:
                break
        k = O.song_slot(e)
        if k is None:
            res.append(dict(period=p + 2, res="no song"))
            continue
        fl = O.fields(e, k)
        a_start = len(r.buf)
        most, frames, ended = 0, 0, None
        for f in range(60 * 70):
            r.frame(1)
            most = max(most, e.w(NOTECOUNT))
            if O.song_slot(e) != k or O.l(e, O.PTR + 4 * k) != fl["ptr"]:
                ended = f
                break
        a_end = len(r.buf)
        r.frame(300)
        left = e.w(NOTECOUNT)
        row = dict(period=p + 2, song=hex(fl["id"]), slot=k, ptr=hex(fl["ptr"]), frames=ended,
                   seconds=round((ended or 0) / 59.92, 1), how_it_ended=("slot freed / changed" if ended is not None else "still on"),
                   most_notes_pending=most, notes_pending_300_frames_after=left,
                   walk=walk(data, fl["ptr"]))
        if wav_name and p == 0:
            pcm = r.buf[a_start:a_end]
            path = out / f"{wav_name}.wav"
            with wave.open(str(path), "wb") as w:
                w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
                w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
            row["wav"] = str(path)
        res.append(row)
        print(Path(rom).name, json.dumps(row, default=str), flush=True)
        lowload.breathe()
    return res


def same(orig, build, state):
    out = {}
    for name, rom in (("orig", orig), ("build", build)):
        rec = {}
        e = Emu(rom)
        buf = capture(e)
        ids = []
        for f in range(3000):                       # power-on: the title music
            e.run(1)
            ids.append(tuple(e.w(O.SID + 2 * j) for j in range(8) if O.l(e, O.PTR + 4 * j) != 0xFFFFFFFF))
        rec["title"] = (np.asarray(buf, np.int16).tobytes(), ids)
        del e
        r = O.R(rom, state)
        r.goal()
        n0 = len(r.buf)
        tr = r.frame(1500)
        rec["goal"] = (np.asarray(r.buf[n0:], np.int16).tobytes(), [t["ids"] for t in tr])
        r.e.unserialize(r.base)
        n0 = len(r.buf)
        tr = r.frame(1800)
        rec["play"] = (np.asarray(r.buf[n0:], np.int16).tobytes(), [t["ids"] for t in tr])
        out[name] = rec
        del r
        lowload.breathe()
    for k in ("title", "goal", "play"):
        a, b = out["orig"][k], out["build"][k]
        n = min(len(a[0]), len(b[0]))
        sa, sb = np.frombuffer(a[0][:n], np.int16), np.frombuffer(b[0][:n], np.int16)
        diff = np.nonzero(sa != sb)[0]
        print(f"{k}: audio {len(sa)} values, differing {len(diff)}" + (f" (first at {diff[0] / 88200:.2f} s)" if len(diff) else "")
              + f"; slot ids differing in {sum(x != y for x, y in zip(a[1], b[1]))} of {min(len(a[1]), len(b[1]))} frames", flush=True)


def pitches(path):
    """(note number, seconds) of the strongest spectral peak in each loud 40 ms window, 80 Hz-2 kHz."""
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).mean(1)
        sr = w.getframerate()
    n = 4096
    hop = int(sr * 0.04)
    win = np.hanning(n)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    band = (freqs > 80) & (freqs < 2000)
    rms = [np.sqrt((x[i:i + n] ** 2).mean()) for i in range(0, len(x) - n, hop)]
    thr = np.percentile(rms, 40)
    out = []
    for j, i in enumerate(range(0, len(x) - n, hop)):
        if rms[j] < thr:
            continue
        sp = np.abs(np.fft.rfft(x[i:i + n] * win))
        sp[~band] = 0
        f = freqs[sp.argmax()]
        out.append((69 + 12 * np.log2(f / 440), i / sr))
    return out


def pitch(rom94, rom95, state, out):
    import gen_1on1_edit_lines as G
    import gen_songs_check as SC
    from gen_midi_song_check import slots as slots94
    data94 = Path(rom94).read_bytes()
    target = struct.unpack_from(">I", data94, 0x2C648 + 4 * 0x40)[0]
    r = G.Run(rom94, out / "_94")
    r.to_play()
    r.step(120)
    e = r.e
    buf = capture(e)
    e.setw(SC.HOMETEAM, 9)                        # Hartford: period-start song $40
    e.setw(SC.CLOCK, 2)
    start = None
    for f in range(9000):
        e.setw(SC.HOMETEAM, 9)
        if start is None and f % 60 == 0:
            r.step(4, hold=["C"])
        else:
            r.step(1)
        if start is None and any(target <= p < target + 0x3000 and not p & 0x80000000 for p in slots94(e)):
            start, cut = f, len(buf)
        if start is not None and f - start >= 60 * 30:
            break
    pcm = buf[cut:]
    p94 = out / "brass_bonanza_nhl94_40.wav"
    with wave.open(str(p94), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
    # NHL '95: a scratch copy with every period-start slot $3D
    d95 = bytearray(Path(rom95).read_bytes())
    for t in range(28):
        d95[TABLE95 + 6 * t] = 0x3D
    scratch = out / "scratch_NHL_95_all_3D.bin"
    scratch.write_bytes(bytes(d95))
    rows = period_songs(str(scratch), state, out, wav_name="brass_bonanza_nhl95_3D", periods=1)
    a, b = pitches(p94), pitches(out / "brass_bonanza_nhl95_3D.wav")
    ha = np.histogram([p for p, _ in a], bins=np.arange(20, 110))[0].astype(float)
    hb = np.histogram([p for p, _ in b], bins=np.arange(20, 110))[0].astype(float)
    scores = {s: float(np.dot(ha, np.roll(hb, -s))) for s in range(-24, 25)}
    best = sorted(scores.items(), key=lambda kv: -kv[1])[:4]
    print(f"pitch: NHL '94 $40 median note {np.median([p for p, _ in a]):.1f}, NHL '95 $3D median note "
          f"{np.median([p for p, _ in b]):.1f}; shifts (semitones, NHL '95 down) lining them up best: {best}", flush=True)
    print("NHL '95 $3D walk:", rows[0].get("walk") if rows else None)


def resume(organ_rom, medley_rom, state, out):
    org = bytearray(Path(organ_rom).read_bytes())
    med = Path(medley_rom).read_bytes()
    lst = struct.unpack_from(">I", med, 0xBAD0)[0]
    bank = struct.unpack_from(">I", med, lst)[0]
    size = 1912
    blob = med[lst:lst + size]
    new = 0x1A8000
    assert all(b == 0xFF for b in org[new:new + size + 0x100]), "the room is not free"
    blob = bytearray(blob)
    struct.pack_into(">I", blob, 0, new + (bank - lst))       # the list's bank pointer, moved
    org[new:new + size] = blob
    struct.pack_into(">I", org, 0xBAD0, new)
    for t in range(28):
        org[TABLE95 + 6 * t] = med[TABLE95 + 6 * t]
    scratch = out / "scratch_organ_resume_plus_medley.bin"
    scratch.write_bytes(bytes(org))
    r = O.R(str(scratch), state)
    S = O.moment_period(r)
    if S is None:
        print("no period song")
        return
    for kind in ("resume", "stats", "replay"):
        row = O.song_case(r, S, kind)
        row["song"] = hex(r.e.w(O.PLAYING))
        print("organ resume + medley", json.dumps(row), flush=True)


def main():
    mode = sys.argv[1]
    out = Path(sys.argv[-1])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    a = sys.argv[2:-1]
    if mode == "medley":
        orig, build, state = a
        period_songs(orig, state, out, None)
        period_songs(build, state, out, Path(build).stem + "_period2")
    elif mode == "same":
        same(*a)
    elif mode == "pitch":
        pitch(*a, out)
    elif mode == "resume":
        resume(*a, out)


if __name__ == "__main__":
    main()
