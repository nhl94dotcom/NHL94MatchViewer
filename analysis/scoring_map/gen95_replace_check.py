"""NHL '95 (Genesis): NOSE4Web's MIDI-made title / end-of-period / scouting music (2026-11-17, mv_review_2026-11-17/
nhl95_replace), played. The piece's stream (NOSE4Web's own bank, gen95_music_check.stream) gives what should sound each
frame; the Z80's voice tables (gen95_driver_check: FM $78-$96, square $C4-$D2) show what does.

`voices ROM SONG STATE OUT`: song 0 from power-on (the title screen), song 2 from a live state with the clock run out;
for two loops: each frame the FM patches that should be sounding with their notes against the table (a note there
late, missing, or its voice holding another patch's note while it should still sound: stolen), and the square notes
the same; each loop's start (the piece's first note again) and its length; SndNoteCount's peak; the audio (RMS a second).

python gen95_replace_check.py voices ROM SONG [STATE] OUT"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

import gen95_music_check as G
import lowload

FMP = {0x0D, 0x0E, 0x11, 0x15, 0x18, 0x1B, 0x1C, 0x1D}


def schedule(rom, song):
    ev, it = G.stream(rom, song)
    prog, notes = {}, []
    for fr, k, ch, a, b, ln in ev:
        if k == "prog":
            prog[ch] = a
        elif k == "note":
            notes.append((fr, fr + max(1, ln), prog.get(ch), a))
    return notes, max(e[0] for e in ev)


def run(rom_path, song, state, out, loops=2):
    from emu import Emu
    from gen_midi_song_check import capture
    from gen95_organ_resume_check import z80, R as OR
    rom = Path(rom_path).read_bytes()
    notes, end = schedule(rom, song)
    if song == 0:
        e = Emu(rom_path)
    else:
        r = OR(rom_path, state)
        e = r.e
        e.unserialize(r.base)
        e.setw(0xC022, 2)
    buf = capture(e)
    first = next(n for n in notes if n[2] in FMP)            # the piece's first FM note marks its start
    tab, peak, started = [], 0, None
    for f in range(1500 + loops * (end + 60)):
        e.run(1)
        if started is None:
            Z = z80(e)
            fm = {(int(Z[0x79 + v]), int(Z[0x85 + v])) for v in range(6) if not (Z[0x78] >> v) & 1}
            if (first[2], first[3]) in fm:
                started = f - first[0]
                cut = len(buf)
            else:
                continue
        Z = z80(e)
        tab.append((f - started, {(int(Z[0x79 + v]), int(Z[0x85 + v])) for v in range(6) if not (Z[0x78] >> v) & 1},
                    {(int(Z[0xC4 + v]), int(Z[0xC8 + v])) for v in range(3) if Z[0xC4 + v]}))
        peak = max(peak, e.w(0xFF1E))
        if f - started > loops * (end + 1) + 30:
            break
    if started is None:
        return dict(error="the piece never started")
    # loop starts: the first note's (patch, note) appearing again after an absence
    loop_at, last = [], True
    for t, fm, sq in tab:
        now = (first[2], first[3]) in fm or (first[2], first[3]) in sq
        if now and not last:
            loop_at.append(t)
        last = now
    period = end - 1                                         # the loop point is the $74 marker at frame 1
    # the second pass's timing: the shift that best lines the table up with the piece after the loop
    def score_shift(d):
        hit = 0
        for t, fm, sq in tab:
            if not end + 60 <= t < end + 1200:
                continue
            tt = 1 + (t - end - d) % period
            due = {(p, n) for s, e_, p, n in notes if s + 1 <= tt < e_ - 1 and p in FMP}
            hit += len(due & fm) - len(due - fm)
        return hit
    shift = max(range(-6, 7), key=score_shift)
    stats, bad, examples = Counter(), Counter(), []
    for t, fm, sq in tab:
        tt = t % period if t >= end else t                   # frame within the piece (after the first pass: from 1)
        if t >= end:
            tt = 1 + (t - end - shift) % period
        due = {(p, n) for s, e_, p, n in notes if s + 1 <= tt < e_ - 1 and p in FMP}   # inside the note, a frame's slack
        start_due = {(p, n) for s, e_, p, n in notes if s == tt - 1 and p in FMP}
        for x in due:
            stats["fm note-frames due"] += 1
            if x in fm:
                stats["fm present"] += 1
            elif any(p == x[0] for p, _ in fm):
                stats["fm voice holding another note of the patch"] += 1
                bad[t // 600] += 1
                if len(examples) < 6:
                    examples.append(dict(frame=t, due=x, table=sorted(fm)))
            else:
                stats["fm missing"] += 1
                bad[t // 600] += 1
                if len(examples) < 6:
                    examples.append(dict(frame=t, due=x, table=sorted(fm)))
        sq_due = {(p, n) for s, e_, p, n in notes if s + 1 <= tt < e_ - 1 and p == 0x14}
        for x in sq_due:
            stats["square note-frames due"] += 1
            stats["square present"] += x in sq
    x = np.array(buf[cut:], float).reshape(-1, 2).mean(1)
    rms = [round(float(np.sqrt((x[i:i + 44100] ** 2).mean()))) for i in range(0, len(x) - 44100, 44100)]
    import wave
    with wave.open(str(out / f"{Path(rom_path).stem}_song{song}.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes(np.clip(x, -32768, 32767).astype("<i2").tobytes())
    return dict(rom=Path(rom_path).name, song=song, piece_frames=end, loops_heard_at=loop_at[:4],
                loop_lengths=[b - a for a, b in zip([0] + loop_at, loop_at)][:4], note_list_peak=peak,
                second_pass_shift=shift, rms_mean=round(float(np.mean(rms))), rms_by_10s=rms[::10], bad_by_10s=[bad[k] for k in range(max(bad, default=0) + 1)],
                examples=examples, **stats)


def main():
    lowload.gentle()
    if sys.argv[1] == "voices":
        rom, song = sys.argv[2], int(sys.argv[3])
        state = sys.argv[4] if len(sys.argv) > 5 else None
        out = Path(sys.argv[-1])
        out.mkdir(parents=True, exist_ok=True)
        print(json.dumps(run(rom, song, state, out)))


if __name__ == "__main__":
    main()
