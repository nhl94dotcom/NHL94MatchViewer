"""The Genesis game's sound effects as references for audio_events.py (2026-11-14): a computer game on the ROM in our
own headless Genesis Plus GX with its audio kept (gen_midi_song_check.capture), every effect's start logged by
lastsfx ($FFC016 on retail: sfx stores each effect's number there; the instant-replay recorder sets bit 7 of its low
byte once a frame is saved, so a low byte with bit 7 clear is an effect started this frame).

Writes OUT.npz: audio (int16 stereo, the core's rate), rate, events [(frame, sfx number, audio frame index)].
Gentle (lowload). One period of 5 minutes by default.

python analysis/vision/sfx_refs.py ROM OUT.npz [PERIODS]"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
LASTSFX, GSP, CLOCK, SCREEN = 0xC016, 0xC466, 0xC468, 0xFFF7


def main():
    import gen_midi_song_check as M
    import gen_ot_check as G
    import lowload
    from emu import Emu
    rom, out = sys.argv[1], Path(sys.argv[2])
    periods = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    lowload.gentle()
    e = Emu(rom)
    G.to_setup(e, out.parent)
    e.setw(0xD050, 0)
    if not G.into_play(e):
        print("never reached play")
        return
    buf = M.capture(e)
    events, still, last = [], 0, None
    for f in range(60 * 60 * 30):
        if f % 60 == 0:
            e.setw(0xC328, 0)
            e.setw(0xC32A, 0)
            for k in range(12):
                e.setb(0xB04A + 0x80 * k + 0x62, e.b(0xB04A + 0x80 * k + 0x62) & ~8)
            if f % 3600 == 0:
                lowload.breathe()
        c = e.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        at = len(buf) // 2
        e.run(1, hold=["START"] if still >= 300 and f % 150 < 4 and e.b(SCREEN) != 0 else [])
        v = e.w(0xFF0000 | LASTSFX)
        if v != 0xFFFF and not v & 0x80:
            events.append((f, v & 0x7F, at))
        if e.w(GSP) >= periods:
            break
    rate = 44100
    try:
        rate = int(round(e.av_info.timing.sample_rate))
    except Exception:
        pass
    np.savez_compressed(out, audio=np.array(buf, np.int16).reshape(-1, 2), rate=np.array(rate),
                        events=np.array(events, np.int64))
    from collections import Counter
    print(f"{len(events)} effects, {len(buf) // 2} audio frames; by number: "
          f"{sorted(Counter(n for _, n, _ in events).items())}", flush=True)


if __name__ == "__main__":
    main()
