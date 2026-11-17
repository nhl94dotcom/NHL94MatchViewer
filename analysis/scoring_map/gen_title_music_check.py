"""NOSE4Web's MIDI-made Genesis non-organ pieces (2026-11-17: the title music $78, end of period $79, scouting report
$7A; nhl94_title_is_scouting.bin, nhl94_title_roundtrip_eop_brass.bin), played against retail nhl94.bin.

`patches BUILD OUT`: each FM patch heard alone (see patches()).

`tour ROM OUT`: from power-on, the screens that play music, each for long enough to loop: the title (9,500 frames),
the menu after it and Game Setup, the screens between Game Setup and play, the pause menu (3,000 frames in a game),
the intermission after period 1 (6,000 frames, then on into period 2) and, from a second power-on, Play Mode New
Playoffs into its screens. Every frame the sound driver's 8 track slots (fm_track_slots $D3D4, 6 bytes, the stream
pointer's top word negative when free) are read: a pointer inside one of the three pieces' streams (start to its end
event + 8) counts for that piece (frames playing, loops: the pointer going back by more than 64 bytes inside it, and
pointers outside the events), one below song $30's stream is a sound effect (each new start counted), any other is
another song. The game's frame counter ($FFB03E) is checked to move every frame (no hang). The audio of each step is
kept as a WAV, and screenshots every 600 frames.

python gen_title_music_check.py tour ROM OUT | patches BUILD OUT"""
import json
import struct
import sys
import wave
from collections import Counter
from pathlib import Path

from emu import Emu
import gen_midi_song_check as M
import lowload

TABLE, SLOTS = 0x2C648, 0xD3D4
PLAYMODE, GSP, CLOCK, SCREEN, FRAMES = 0xD048, 0xC466, 0xC468, 0xFFF7, 0xB03E
PIECES = {0x78: "title", 0x79: "end of period", 0x7A: "scouting"}


def ranges(rom):
    out = {}
    for s, name in PIECES.items():
        p = struct.unpack_from(">I", rom, TABLE + 4 * s)[0]
        at = p
        while rom[at + 1] != 0:
            at += 4
        out[name] = (p, at + 8)
    return out, struct.unpack_from(">I", rom, TABLE + 4 * 0x30)[0]


class Watch:
    def __init__(self, e, rom, out):
        self.e, self.out = e, out
        self.r, self.song30 = ranges(rom)
        self.buf = M.capture(e)
        self.prev = [None] * 8
        self.step_name, self.log = None, []

    def begin(self, name):
        self.step_name = name
        self.s = dict(step=name, frames=0, pieces=Counter(), loops=Counter(), sfx=0, other_songs=Counter(),
                      stray=0, stuck_frames=0, first=None)
        self.cut = len(self.buf)
        self.fc = self.e.w(FRAMES)

    def run(self, n, hold=()):
        e = self.e
        for f in range(n):
            e.run(1, hold=list(hold))
            s = self.s
            s["frames"] += 1
            fc = e.w(FRAMES)
            s["stuck_frames"] += fc == self.fc
            self.fc = fc
            for k, p in enumerate(M.slots(e)):
                if p & 0x80000000:
                    self.prev[k] = None
                    continue
                name = next((nm for nm, (a, b) in self.r.items() if a <= p < b), None)
                if name:
                    s["pieces"][name] += 1
                    if s["first"] is None:
                        s["first"] = (name, s["frames"])
                    q = self.prev[k]
                    if q is not None and q[0] == name and p < q[1] - 64:
                        s["loops"][name] += 1
                elif p < self.song30:
                    if self.prev[k] is None:
                        s["sfx"] += 1
                else:
                    near = next((nm for nm, (a, b) in self.r.items() if a - 0x400 <= p < b + 0x400), None)
                    if near:
                        s["stray"] += 1
                    else:
                        s["other_songs"][hex(p)] += 1
                self.prev[k] = (name, p) if name else ("x", p)
            if s["frames"] % 600 == 0:
                e.screenshot(self.out / f"{self.step_name}_{s['frames']:05d}.png")

    def end(self):
        s = self.s
        pcm = self.buf[self.cut:]
        with wave.open(str(self.out / f"{self.step_name}.wav"), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
            w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
        step = 2 * 44100
        s["loudness_per_s"] = [round((sum(x * x for x in pcm[i:i + step:7]) / max(1, len(pcm[i:i + step:7]))) ** 0.5)
                               for i in range(0, len(pcm), step)]
        s["other_songs"] = dict(s["other_songs"].most_common(4))
        s["pieces"], s["loops"] = dict(s["pieces"]), dict(s["loops"])
        self.log.append(s)
        print(json.dumps({k: v for k, v in s.items() if k != "loudness_per_s"}), flush=True)
        del self.buf[:]
        lowload.breathe()


def press(w, b, n=1, wait=26):
    for _ in range(n):
        w.run(4, hold=[b])
        w.run(wait)


def tour(rom_path, out):
    rom = Path(rom_path).read_bytes()
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom_path)
    w = Watch(e, rom, out)
    w.begin("title"); w.run(6500); w.end()                       # the EA intro, then the title music past a loop
    w.begin("game_setup"); press(w, "START", 1, 120); press(w, "START", 1, 320); w.run(5000); w.end()
    w.begin("scouting"); press(w, "START", 1, 60); w.run(5700); w.end()
    w.begin("pregame_menu"); press(w, "START", 1, 60); w.run(5200); w.end()
    w.begin("to_play")
    for _ in range(30):
        if e.b(SCREEN) == 0:
            break
        press(w, "START", 1, 120)
    w.run(600)
    w.end()
    w.begin("pause"); press(w, "START", 1, 60); w.run(3000); w.end()
    w.begin("resume")
    for _ in range(4):
        if e.b(SCREEN) == 0:
            break
        press(w, "START", 1, 60)
    w.run(600); w.end()
    w.begin("intermission"); e.setw(CLOCK, 1); w.run(5600); w.end()
    w.begin("period2")
    for _ in range(40):
        if e.b(SCREEN) == 0 and e.w(GSP) == 1:
            break
        press(w, "START", 1, 150)
    w.run(1800)
    w.end()
    e2 = Emu(rom_path)
    w2 = Watch(e2, rom, out)
    w2.begin("playoffs_boot"); w2.run(900); press(w2, "START", 1, 120); press(w2, "START", 1, 320)
    e2.setw(PLAYMODE, 1)
    press(w2, "DOWN", 1, 30); press(w2, "UP", 1, 30)
    w2.end()
    w2.begin("playoff_tree"); press(w2, "START", 1, 60); w2.run(5200); w2.end()
    w2.begin("playoff_next"); press(w2, "START", 1, 60); w2.run(2400); w2.end()
    (out / "tour.json").write_text(json.dumps(w.log + w2.log))


PATCHES = (1, 3, 4, 5, 9, 10, 11, 13, 14, 20)
NOTES = (36, 48, 60, 72)                  # C2, C3, C4, C5 (MIDI numbers; the driver's 0-95)
ON, OFF = 90, 30                          # frames held, frames of release before the next


def patches(build, out):
    """Each FM patch heard alone: a scratch copy of BUILD (the original untouched) whose title music ($78) is a test
    piece: for each patch a program change on channel 0, then C2, C3, C4, C5 at velocity 100, each held ON frames and
    released for OFF. Recorded from power-on; each note measured from the audio: its loudness at the start, after 0.25
    s, 1 s (real) and in the release, the attack (time to the peak), the fundamental's share of the energy and the
    brightness (spectral centroid against the fundamental: about 1-2 a pure or soft tone, 4+ bright or buzzy)."""
    import numpy as np
    data = bytearray(Path(build).read_bytes())
    start = struct.unpack_from(">I", data, TABLE + 4 * 0x78)[0]
    ev = [bytes((0x14, 0xFF, 0xFF, 0xFF))]
    for p in PATCHES:
        ev.append(bytes((0, 0xC0, p, 0)))
        wait = 0
        for n in NOTES:
            ev.append(bytes((wait, 0x90, n, 100)))
            ev.append(bytes((ON, 0x80, n, 0)))
            wait = OFF
        ev[-1] = ev[-1]
        ev.append(bytes((OFF, 0xB0, 7, 127)))          # a controller event as a spacer after the last release
    ev.append(bytes((0, 0)) + struct.pack(">I", start + 4) + bytes(2))
    blob = b"".join(ev)
    data[start:start + len(blob)] = blob
    out.mkdir(parents=True, exist_ok=True)
    scratch = out / f"scratch_patches_{Path(build).stem}.bin"
    scratch.write_bytes(bytes(data))
    e = Emu(str(scratch))
    buf = M.capture(e)
    cut = None
    for f in range(3000):
        e.run(1)
        if any(start <= q < start + len(blob) for q in M.slots(e) if not q & 0x80000000):
            cut = len(buf)
            break
    total = len(PATCHES) * len(NOTES) * (ON + OFF) + 40
    e.run(total + 60)
    x = np.array(buf[cut:], float).reshape(-1, 2).mean(1)
    sr = 44100
    fpf = sr / 59.92
    res = []
    t = 20.0                                       # the header's wait
    for p in PATCHES:
        for n in NOTES:
            a, b = int(t * fpf), int((t + ON) * fpf)
            seg, rel = x[a:b], x[b:int((t + ON + OFF) * fpf)]
            env = [float(np.sqrt((seg[i:i + 441] ** 2).mean())) for i in range(0, len(seg) - 441, 441)]
            pk = max(env) if env else 0
            w = seg[int(0.1 * sr):int(0.1 * sr) + 8192]
            ac = np.correlate(w, w, "full")[len(w) - 1:]
            lo, hi = int(sr / 1200), int(sr / 40)
            lag = lo + int(np.argmax(ac[lo:hi])) if len(ac) > hi else None
            f0 = sr / lag if lag else 440 * 2 ** ((n - 69) / 12)
            w = seg[:min(len(seg), 16384)]
            spec = np.abs(np.fft.rfft(w * np.hanning(len(w)))) ** 2
            fr = np.fft.rfftfreq(len(w), 1 / sr)
            cen = float((spec * fr).sum() / max(spec.sum(), 1e-9))
            fund = float(spec[(fr > f0 * 0.94) & (fr < f0 * 1.06)].sum() / max(spec.sum(), 1e-9))
            res.append(dict(patch=p, note=n, peak=round(pk), attack_ms=10 * int(np.argmax(env)) if env else None,
                            at_250ms=round(env[25] / pk, 2) if len(env) > 25 and pk else None,
                            at_1s=round(env[min(len(env) - 1, 100)] / pk, 2) if pk else None,
                            release=round(float(np.sqrt((rel[:4410] ** 2).mean())) / pk, 2) if pk and len(rel) else None,
                            brightness=round(cen / f0, 1), fundamental_share=round(fund, 2), f0=round(f0, 1),
                            midi_f0=round(440 * 2 ** ((n - 69) / 12), 1)))
            t += ON + OFF
        t += OFF if False else 0
    import wave
    pcm = buf[cut:]
    with wave.open(str(out / "patches.wav"), "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(sr)
        wv.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
    return res


def main():
    lowload.gentle()
    if sys.argv[1] == "patches":
        for r in patches(sys.argv[2], Path(sys.argv[3])):
            print(json.dumps(r))
        return
    if sys.argv[1] == "tour":
        tour(sys.argv[2], Path(sys.argv[3]))


if __name__ == "__main__":
    main()
