"""NOSE4Web's SNES music player (by ear: the game's sequencer, sound chip and samples worked through frame by frame)
against the console (2026-11-17). The console here is Snes9x running the game.

`songs ROM`: the team-song tables (PlayTeamSong's TeamSongs, then DefaultSongs; found by NOSE4Web's code patterns) and
each song's name by the FNV-1a sum of its first 64 bytes (NOSE4Web's snessongs.ts list).
`record ROM OUT NAME ...`: each named song played in the game: a scratch copy of ROM (the original untouched) whose
Boston slot 1 (a home power play's faceoff) is that song; live play (snes_assist_stick_test.Game), a home goal slid in,
the faceoff with PBnum $01, from MusicStart to MusicOn 0 (or 90 s real), into OUT/<name>.wav (32,040 Hz, Snes9x's rate).
`pieces ROM OUT`: from power-on, every song the game starts on its own (SongPtr $07ED with its bank), START pressed
now and then: the title, the menu and what follows, each into a WAV.
`compare A.wav B.wav`: the two aligned by their loudness envelopes (cross-correlation), then: lengths, the pitch of
the first note (the strongest spectral peak in its first 0.3 s), brightness (spectral centroid), peaks and RMS, the
envelope correlation, loudness a second, and what sounds after the other has gone quiet.

python snes_music_compare.py songs ROM | record ROM OUT NAME ... | pieces ROM OUT | compare A.wav B.wav"""
import struct
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

NAMES = {
    0xd1256abb: "Blue Danube Waltz [C]", 0x4f7a4b3e: "Brass Bonanza", 0x3fa3eb03: "Hava Nagila",
    0x9f380714: "Jaws Theme", 0x77e6ad22: "What Do You Do With A Drunken Sailor?",
}


def lorom(bank, addr):
    return ((bank & 0x7F) << 15) | (addr & 0x7FFF)


def fnv(b):
    h = 0x811C9DC5
    for x in b:
        h = ((h ^ x) * 0x01000193) & 0xFFFFFFFF
    return h


def find(rom, pat):
    import re
    rx = re.compile(bytes.fromhex(pat.replace("..", "2e")).replace(b".", b"(?s:.)"))
    return [m.start() for m in rx.finditer(rom)]


def tables(rom):
    play = find(rom, "bf......30..85..bf......85..22")
    rnd = find(rom, "a9080022......0a0aaabf......")
    assert len(play) == 1 and len(rnd) == 1, (play, rnd)
    p = lambda at: rom[at] | rom[at + 1] << 8 | rom[at + 2] << 16  # noqa: E731
    ts = lorom(p(play[0] + 9) >> 16, p(play[0] + 9))
    ds = lorom(p(rnd[0] + 11) >> 16, p(rnd[0] + 11))
    return ts, ds


def songs(rom):
    ts, ds = tables(rom)
    out = {}
    for at in range(ts, ds + 32, 4):
        ptr = struct.unpack_from("<I", rom, at)[0]
        if ptr >> 16 >= 0x8000:
            continue
        off = lorom(ptr >> 16, ptr)
        out.setdefault(ptr, (NAMES.get(fnv(rom[off:off + 64])), fnv(rom[off:off + 64]), []))[2].append((at - ts) // 4)
    return ts, out


def record(rom_path, out, names):
    from snes_assist_stick_test import Game, POSITION, PFGOAL
    from snes_songs_check import HOMETEAM, CURSONG, MUSICON, PBNUM, GOALS, song
    from snes_midi_song_check import slide_goal, team_index
    from gen_midi_song_check import capture
    rom = Path(rom_path).read_bytes()
    ts, sg = songs(rom)
    boston = team_index(rom_path, "Boston")
    res = []
    for name in names:
        ptr = next(p for p, v in sg.items() if v[0] and v[0].startswith(name))
        b = bytearray(rom)
        struct.pack_into("<I", b, ts + 4 * (boston * 6 + 1), ptr)
        scratch = out / f"scratch_{Path(rom_path).stem}.{Path(rom_path).suffix[1:]}"
        scratch.write_bytes(bytes(b))
        G = Game(str(scratch))
        e = G.e
        e.unserialize(G.g.bases[0])
        G.setw(HOMETEAM, boston)
        G.setw(0x1632, 250)
        hk = next(k for k in range(6) if G.w(POSITION + 2 * k) not in (0, 0xFFFF))
        up = 1 if G.w(PFGOAL + 2 * hk) else -1
        gk = next(k for k in range(6, 12) if G.w(POSITION + 2 * k) == 0)
        g0 = G.w(GOALS)
        buf = capture(e)
        start, cut, seen_goal_song, pin = None, 0, False, None
        for f in range(60 * 150):
            if start is None:
                if f < 60:
                    slide_goal(G, up, gk)
                if G.w(GOALS) != g0 and G.w(CURSONG) == 4:
                    seen_goal_song = True
                if seen_goal_song:
                    G.setw(MUSICON, 0)
                    G.setw(PBNUM, 0x01)
            G.run(hold=["B"] if start is None and f % 40 == 0 and f > 300 else [])
            G.setw(0x1632, max(G.w(0x1632), 200))          # no horn
            if start is not None:                            # every player pinned where he stood when the song
                if pin is None:                              # started: no skating or hit sounds, the crowd's
                    pin = [(G.w(0x0D55 + 2 * k), G.w(0x0DB7 + 2 * k)) for k in range(16)]   # ambience (RMS about
                for k in range(16):                                                     # 210) left
                    G.setw(0x0D55 + 2 * k, pin[k][0]); G.setw(0x0DB7 + 2 * k, pin[k][1])
            cur = song(G)
            if start is None and G.w(CURSONG) == 2 and cur == (ptr & 0xFFFFFF if ptr >> 16 < 0x100 else cur):
                start, cut = f, len(buf)
            if start is not None and (not G.w(MUSICON) or f - start > 60 * 90):
                end = f
                break
        if start is None:
            res.append(dict(name=name, error="never started"))
            continue
        pcm = buf[cut:]
        path = out / f"console_{Path(rom_path).stem}_{name.split()[0]}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(32040)
            w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
        res.append(dict(name=name, pointer=hex(ptr), frames=end - start, wav=str(path)))
        print(res[-1], flush=True)
    return res


def load(path):
    w = wave.open(str(path))
    sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
    x = np.frombuffer(w.readframes(n), np.int16).astype(float)
    x = x.reshape(-1, ch).mean(1) if ch > 1 else x
    return x, sr


def resample(x, sr, to):
    if sr == to:
        return x
    t = np.arange(0, len(x) / sr, 1 / to)
    return np.interp(t, np.arange(len(x)) / sr, x)


def envelope(x, sr, hop=0.01):
    h = int(sr * hop)
    return np.array([np.sqrt((x[i:i + h] ** 2).mean()) for i in range(0, len(x) - h, h)])


def compare(a_path, b_path, sr=32040):
    a, sa = load(a_path)
    b, sb = load(b_path)
    pa, pb = np.abs(a).max(), np.abs(b).max()
    a, b = resample(a, sa, sr), resample(b, sb, sr)
    ea, eb = envelope(a, sr), envelope(b, sr)
    # align: lag of b against a by the envelopes' cross-correlation (+-5 s)
    na, nb = (ea - ea.mean()) / (ea.std() + 1e-9), (eb - eb.mean()) / (eb.std() + 1e-9)
    best = max(range(-500, 501), key=lambda L: float(np.dot(na[max(0, L):min(len(na), len(nb) + L)],
                                                               nb[max(0, -L):max(0, -L) + min(len(na), len(nb) + L) - max(0, L)])))
    L = best
    n = min(len(ea) - max(0, L), len(eb) - max(0, -L))
    A, B = ea[max(0, L):max(0, L) + n], eb[max(0, -L):max(0, -L) + n]
    corr = float(np.corrcoef(A, B)[0, 1])

    def first_pitch(x):
        i0 = int(np.argmax(envelope(x, sr) > 0.1 * envelope(x, sr).max())) * int(sr * 0.01)
        seg = x[i0 + int(0.02 * sr):i0 + int(0.32 * sr)]
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 8 * len(seg)))
        fr = np.fft.rfftfreq(8 * len(seg), 1 / sr)
        m = (fr > 60) & (fr < 4000)
        return float(fr[m][np.argmax(sp[m])])

    def centroid(x):
        h = 8192
        cs = []
        for i in range(0, len(x) - h, h):
            s = np.abs(np.fft.rfft(x[i:i + h] * np.hanning(h))) ** 2
            if s.sum() > 0:
                fr = np.fft.rfftfreq(h, 1 / sr)
                cs.append((s * fr).sum() / s.sum())
        return float(np.median(cs)) if cs else 0.0

    def tail(e):
        loud = np.nonzero(e > 0.02 * e.max())[0]
        return (loud[-1] + 1) * 0.01 if len(loud) else 0.0

    return dict(
        lengths_s=(round(len(a) / sr, 2), round(len(b) / sr, 2)), sounding_until_s=(round(tail(ea), 2), round(tail(eb), 2)),
        b_lags_a_s=round(L * 0.01, 2), envelope_correlation=round(corr, 3),
        first_pitch_hz=(round(first_pitch(a), 1), round(first_pitch(b), 1)),
        brightness_hz=(round(centroid(a)), round(centroid(b))),
        rms=(round(float(np.sqrt((a ** 2).mean()))), round(float(np.sqrt((b ** 2).mean())))),
        peak=(int(pa), int(pb)), at_full_scale=(int((np.abs(a) >= 32760).sum()), int((np.abs(b) >= 32760).sum())),
        loudness_ratio_by_s=[round(float(B[i:i + 100].mean() / max(1e-9, A[i:i + 100].mean())), 2) for i in range(0, n - 99, 100)][:40])


def main():
    mode = sys.argv[1]
    if mode == "songs":
        rom = Path(sys.argv[2]).read_bytes()
        ts, sg = songs(rom)
        print("TeamSongs at", hex(ts))
        for p, (name, h, ents) in sorted(sg.items(), key=lambda kv: str(kv[1][0])):
            print(hex(p), name or f"fnv {h:08x}", "entries", ents[:6])
    elif mode == "record":
        import lowload
        lowload.gentle()
        out = Path(sys.argv[3])
        out.mkdir(parents=True, exist_ok=True)
        record(sys.argv[2], out, sys.argv[4:])
    elif mode == "compare":
        import json
        print(json.dumps(compare(sys.argv[2], sys.argv[3])))


if __name__ == "__main__":
    main()
