"""NOSE4Web's MIDI-made Genesis organ songs, played (2026-11-10, nhl94_songs_midi.bin: Boston's $31, a period's first
faceoff, Brass Bonanza re-encoded; $32, a home power play, a "Charge" fanfare; both in free room, SoundStreamTable
entries repointed). The sound driver's 8 track slots (fm_track_slots $D3D4, 6 bytes: the stream pointer, -1 free, and
a delay) are read every frame (a slot is free when its pointer's top word is negative: a stream's end sets the
top byte, st (a5)): a slot whose pointer is at or past song $30's stream plays a song
(stop_current_song's own test), one below it a sound effect.

From one play state of each ROM (retail and the build), Boston (1) at home:
- `period`: the clock run out and the next period started (TeamSongs slot 0): which song stream played, from when to
  when (frames), and whether its slot was freed at the end;
- `interrupt`: the same, then 300 frames into the song a home goal (the puck put into the net): whether the song's
  slot is freed and nothing plays on in it;
- in both, the sound effects that started while the song played.

python gen_midi_song_check.py ROM OUT"""
import json
import struct
import sys
from pathlib import Path

import gen_1on1_edit_lines as G
import gen_songs_check as SC

SLOTS, NSLOTS = 0xD3D4, 8
BOSTON = 1
TABLE = 0x2C648


def slots(e):
    out = []
    for k in range(NSLOTS):
        hi, lo = e.w(SLOTS + 6 * k), e.w(SLOTS + 6 * k + 2)
        out.append((hi << 16 | lo) & 0xFFFFFFFF)
    return out


def run(rom, outdir, scenario):
    data = Path(rom).read_bytes()
    song30 = struct.unpack_from(">I", data, TABLE + 4 * 0x30)[0]
    streams = {s: struct.unpack_from(">I", data, TABLE + 4 * s)[0] for s in range(0x30, 0x7B)}
    r = G.Run(rom, outdir)
    r.to_play()
    r.step(120)
    e = r.e
    e.setw(SC.HOMETEAM, BOSTON)
    e.setw(SC.CLOCK, 2)
    log, playing, sfx, goal_done = [], {}, set(), False
    period0 = e.w(SC.PERIOD)
    for f in range(6000):
        e.setw(SC.HOMETEAM, BOSTON)
        if f % 60 == 0 and not any(v["song"] in (0x31, 0x32) for v in playing.values()):
            r.step(4, hold=["C"])                       # through the end of the period and the intermission screens
        else:
            r.step(1)
        now = slots(e)
        for k, p in enumerate(now):
            if p & 0x80000000:                          # free: the driver's st (a5) sets the top byte at the end
                if k in playing:
                    log.append(dict(event="freed", slot=k, frame=f, song=playing.pop(k)["song"]))
                continue
            if song30 <= p < 0x400000:                  # a song: at or past song $30's stream
                start = max((s for s, q in streams.items() if q <= p), key=lambda s: streams[s], default=None)
                if k not in playing:
                    playing[k] = dict(song=start, frame=f)
                    log.append(dict(event="song starts", slot=k, frame=f, song=hex(start) if start else None,
                                    pointer=hex(p)))
            elif any(v for v in playing.values()):
                sfx.add(hex(p & 0xFFFF00))
        new = [v for v in playing.values() if v["song"] in (0x31, 0x32)]
        if scenario == "interrupt" and not goal_done and new and f - new[0]["frame"] == 300:
            log.append(dict(event="home goal sent", frame=f))
            SC.goal(r, [], "goal")
            goal_done = True
    res = dict(rom=Path(rom).name, scenario=scenario, log=log, still_playing=playing,
               sfx_starts_while_a_song_played=len(sfx))
    (outdir / f"{scenario}_{Path(rom).stem}.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, default=str), flush=True)


def capture(e):
    """Keep the core's audio (it normally goes nowhere): a list of int16 stereo frames, filled as frames run."""
    import ctypes as C
    from emu import AUDIO_BATCH_CB
    buf = []

    def batch(ptr, n):
        buf.extend((C.c_int16 * (2 * n)).from_address(ptr))
        return n
    cb = AUDIO_BATCH_CB(batch)
    e._audio_keep = cb
    e.lib.retro_set_audio_sample_batch(cb)
    return buf


def wav(rom, outdir, which):
    """`wav`: the song played into a WAV file (period: $31 at the next period's first faceoff; pp: $32 at the faceoff
    after a home goal with the home team a man up), 25 s (real) from its start, and each second's loudness."""
    import wave
    data = Path(rom).read_bytes()
    song30 = struct.unpack_from(">I", data, TABLE + 4 * 0x30)[0]
    target = struct.unpack_from(">I", data, TABLE + 4 * (0x31 if which == "period" else 0x32))[0]
    r = G.Run(rom, outdir)
    r.to_play()
    r.step(120)
    e = r.e
    e.setw(SC.HOMETEAM, BOSTON)
    if which == "period":
        e.setw(SC.CLOCK, 2)
    else:
        SC.goal(r, [], "goal")
    buf = capture(e)
    start = None
    for f in range(6000):
        e.setw(SC.HOMETEAM, BOSTON)
        if which == "pp":
            e.setw(SC.TMAP_H, 6)
            e.setw(SC.TMAP_A, 5)
            e.setb(0xC2EE, e.b(0xC2EE) & 0xDF)
        if start is None and f % 60 == 0:
            r.step(4, hold=["C"])
            n0 = len(buf)
        else:
            r.step(1)
        if start is None and any(abs(p - target) < 0x3000 and not p & 0x80000000 for p in slots(e)):
            start, cut = f, len(buf)
        if start is not None and f - start >= 1500:
            break
    if start is None:
        print(Path(rom).name, which, "never started")
        return
    pcm = buf[cut:]
    out = outdir / f"{which}_{Path(rom).stem}.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
    step = 2 * 44100 // 10
    rms = [round((sum(x * x for x in pcm[i:i + step]) / max(1, len(pcm[i:i + step]))) ** 0.5) for i in range(0, len(pcm), step)]
    print(Path(rom).name, which, "->", out, "loudness every 0.1 s (real):", rms[:60], flush=True)


def main():
    if sys.argv[1] == "wav":
        rom, outdir = sys.argv[2], Path(sys.argv[3])
        outdir.mkdir(parents=True, exist_ok=True)
        for which in sys.argv[4:] or ("period", "pp"):
            wav(rom, outdir, which)
        return
    rom, outdir = sys.argv[1], Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    for sc in ("period", "interrupt"):
        run(rom, outdir, sc)


if __name__ == "__main__":
    main()
