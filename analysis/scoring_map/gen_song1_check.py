"""NOSE4Web's song 1 ($30) replacement, played (Genesis NHL '94, 2026-11-27; nhl94_song1.bin FF99D3D3: song $30's
table entry kept at $2CEF2, its first 6 bytes made an end event whose loop pointer goes to the new song in free room
($FFAC0, song 6's notes), so stop_current_song's test (a slot pointer at or past song $30's stream is the song) still
holds).

Against a control that plays song 6 ($35) itself at the same moments: the control is a scratch copy of the first ROM
with Boston's six TeamSongs bytes ($FE5B6) all $35; the build is played as it is, and (`--six-build`) as a scratch copy
with Boston's six bytes all $30. Each ROM in its own process, from the same game moment, Boston (1) and Chicago (4) at
home. Cases, each from the same state:
  period    the clock run out: the next period's start (slot 0) and its first faceoff (slot 2)
  goal      a home goal at 2:00 (slot 3), then the faceoff after it: a song stopped and another started
  pp        a home goal, then the faceoff with the home team a man up (slot 4)
  late      the 3rd period with 40 s left (slot 5)
  pause     the period start's song, START 200 frames in, 150 frames in the menu, START
Each frame: SongNum ($D6C8, ChooseSong's pick), the driver's 8 track slots (fm_track_slots $D3D4) read as (song, event
index in its stream: the jump at $30's head followed to its target, whose extra first event, kept for song 6's
opening delay, is counted off), the channels keyed on (fm_channel_structs $D3A4, 6 x 8 bytes, ch_flags +6 bit 0) and
on the song's track (ch_key & 7 = 7 - slot), and the sound (the core's audio). The build against the control, frame by
frame: the same picks, the same (song 6 / song 1) event index every frame, the channels on, the song's channels left
on after its slot is freed (beside the control's), the frame the play drifts apart (the puck's spot differs: the
build's vblank runs one more event, the jump, so the two can part over a long stretch), and the sound up to then
(the same samples, or the 0.1 s (real) spectra correlated).

python gen_song1_check.py OUT CONTROL_BASE_ROM BUILD_ROM [--six-build]
python gen_song1_check.py play ROM OUT TAG   (one ROM: what the first form runs in a subprocess)"""
import json
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

import gen_1on1_edit_lines as G
import gen_songs_check as SC
from gen_midi_song_check import capture, slots

TABLE = 0x2C648
TEAMSONGS_BOS = 0xFE5B6
CHANNELS = 0xD3A4
BOSTON, CHICAGO = 1, 4
CASES = ("period", "goal", "pp", "late", "pause")


def streams(data):
    st = {s: struct.unpack_from(">I", data, TABLE + 4 * s)[0] for s in range(0x30, 0x7B)}
    s30 = st[0x30]
    jump = None
    if data[s30 + 1] == 0 and struct.unpack_from(">h", data, s30 + 2)[0] >= 0:
        jump = struct.unpack_from(">I", data, s30 + 2)[0]
    return st, jump


def where(p, st, jump):
    if jump is not None and jump <= p < jump + 0x2000:
        return 0x30, (p - jump) // 4 - 1
    best = max((s for s, q in st.items() if q <= p), key=lambda s: st[s])
    return best, (p - st[best]) // 4


def scratch(rom, out, song):
    data = bytearray(Path(rom).read_bytes())
    data[TEAMSONGS_BOS:TEAMSONGS_BOS + 6] = bytes([song] * 6)
    p = out / f"{Path(rom).stem}_bos_six_{song:02X}.bin"
    p.write_bytes(data)
    return p


def run_case(r, base, case, team, buf):
    e = r.e
    e.unserialize(base)
    e.setw(SC.HOMETEAM, team)
    if case in ("period", "pause"):
        e.setw(SC.CLOCK, 2)
    elif case == "late":
        e.setw(SC.PERIOD, 2)
        e.setw(SC.CLOCK, 40)
    else:
        e.setw(SC.CLOCK, 120)
        SC.goal(r, [], "goal")
    a0 = len(buf)
    trace, picks, song_start, paused_at = [], [], None, None
    e.setw(SC.SONGNUM, 0x7FFF)
    for f in range(6000 if case in ("period", "pause") else 2400):
        e.setw(SC.HOMETEAM, team)
        if case == "pp":
            e.setw(SC.TMAP_H, 6)
            e.setw(SC.TMAP_A, 5)
            e.setb(0xC2EE, e.b(0xC2EE) & 0xDF)
        if case == "pause" and song_start is not None and paused_at is None and f - song_start == 200:
            r.step(4, hold=["START"])
            r.step(150)
            r.step(4, hold=["START"])
            paused_at = f
        elif case in ("period", "pause") and song_start is None and f % 60 == 0:
            r.step(4, hold=["C"])
        else:
            r.step(1)
        s = e.w(SC.SONGNUM)
        if s != 0x7FFF:
            picks.append([f, s, e.w(SC.SONGIDX)])
            e.setw(SC.SONGNUM, 0x7FFF)
        row = []
        for k, p in enumerate(slots(e)):
            if p & 0x80000000 or p < r.st[0x30]:
                continue
            row.append([k, *where(p, r.st, r.jump)])
            if song_start is None and picks:        # a song begun after ChooseSong's pick (not one left playing)
                song_start = f
        on = [c for c in range(6) if e.b(CHANNELS + 8 * c + 6) & 1]
        tracks = sorted({e.b(CHANNELS + 8 * c) & 7 for c in on})
        trace.append([row, len(on), tracks, len(buf) - a0, e.w(SC.PUCK), e.w(SC.PUCK + 0x14)])
    return dict(trace=trace, picks=picks, paused_at=paused_at, a0=a0)


def play(rom, out, tag):
    r = G.Run(rom, out)
    r.st, r.jump = streams(Path(rom).read_bytes())
    buf = capture(r.e)
    r.to_play()
    r.step(120)
    base = r.e.serialize()
    res = {}
    for team in (BOSTON, CHICAGO):
        for case in CASES:
            res[f"{team}_{case}"] = run_case(r, base, case, team, buf)
    np.save(out / f"audio_{tag}.npy", np.asarray(buf, dtype=np.int16))
    (out / f"trace_{tag}.json").write_text(json.dumps(res))


def spectra(x, n):
    x = x.reshape(-1, 2).mean(axis=1).astype(float)
    w = 4410
    return np.array([np.log1p(np.abs(np.fft.rfft(x[i * w:(i + 1) * w] * np.hanning(w)))[:2000]) for i in range(min(n, len(x) // w))])


def compare(out, tags):
    T = {t: json.loads((out / f"trace_{t}.json").read_text()) for t in tags}
    A = {t: np.load(out / f"audio_{t}.npy") for t in tags}
    ctl = tags[0]
    lines = []
    for key in T[ctl]:
        c = T[ctl][key]
        for t in tags[1:]:
            b = T[t][key]
            norm = lambda row: [(s if s != 0x35 else "S", i) for _, s, i in row]   # noqa: E731
            normb = lambda row: [(s if s != 0x30 else "S", i) for _, s, i in row]  # noqa: E731
            diff = [f for f, (x, y) in enumerate(zip(c["trace"], b["trace"])) if norm(x[0]) != normb(y[0])]
            ondiff = [f for f, (x, y) in enumerate(zip(c["trace"], b["trace"])) if x[1] != y[1]]
            picks_c = [(f, s if s != 0x35 else "S", i) for f, s, i in c["picks"]]
            picks_b = [(f, s if s != 0x30 else "S", i) for f, s, i in b["picks"]]
            # the song's frames: start, end (its slot freed), channels on after
            def span(tr, song):
                fr = [f for f, x in enumerate(tr) if any(s == song for _, s, _ in x[0])]
                return (fr[0], fr[-1]) if fr else None
            sc, sb = span(c["trace"], 0x35), span(b["trace"], 0x30)
            after = None
            if sb:
                after = [b["trace"][f][1] for f in range(sb[1] + 1, min(len(b["trace"]), sb[1] + 30))]
            # the play drifting apart (the puck's spot): the first frame it differs; the sound compared up to then
            drift = next((f for f, (x, y) in enumerate(zip(c["trace"], b["trace"])) if x[4:6] != y[4:6]), None)
            # sound: the case, 0.1 s (real) windows
            n = len(c["trace"])
            xa = A[ctl][c["a0"]:c["a0"] + c["trace"][-1][3]]
            xb = A[t][b["a0"]:b["a0"] + b["trace"][-1][3]]
            m = min(len(xa), len(xb)) // 2 * 2
            upto = c["trace"][drift][3] if drift is not None else m
            upto = min(m, upto) // 2 * 2
            sa, sb2 = spectra(xa[:upto], 1000), spectra(xb[:upto], 1000)
            cors = [float(np.corrcoef(p, q)[0, 1]) if p.std() and q.std() else (1.0 if not p.std() and not q.std() else 0.0) for p, q in zip(sa, sb2)]
            lines.append(dict(rom=t, case=key, picks_same=picks_c == picks_b, picks=picks_b[:6], song6_span_control=sc, song1_span_build=sb,
                              frames_slot_differs=len(diff), first_differs=diff[:3], frames_channels_on_differ=len(ondiff),
                              channels_on_after_song_freed=after[:10] if after else None,
                              sound_corr_min=round(min(cors), 3) if cors else None, sound_corr_mean=round(float(np.mean(cors)), 4) if cors else None,
                              exact_audio_until_drift=bool(upto and (xa[:upto] == xb[:upto]).all()), play_drifts_at=drift,
                              channels_after_song6_control=[c["trace"][f][1] for f in range(sc[1] + 1, min(n, sc[1] + 11))] if sc else None,
                              frames=n))
    (out / "song1_compare.json").write_text(json.dumps(lines, indent=1, default=str))
    for x in lines:
        print(json.dumps(x, default=str))


def main():
    if sys.argv[1] == "play":
        play(sys.argv[2], Path(sys.argv[3]), sys.argv[4])
        return
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    roms = {"control": scratch(sys.argv[2], out, 0x35), "build": Path(sys.argv[3])}
    if "--six-build" in sys.argv:
        roms["build_six30"] = scratch(sys.argv[3], out, 0x30)
    procs = [subprocess.Popen([sys.executable, __file__, "play", str(p), str(out), t]) for t, p in roms.items()]
    for p in procs:
        p.wait()
    compare(out, list(roms))


if __name__ == "__main__":
    main()
