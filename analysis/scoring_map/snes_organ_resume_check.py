"""SNES: NOSE4Web's organ resume after a pause, played (2026-11-16, 8a0b31f). Pausemode's jsl FadeOutSound saves, with
SoundLock up, the song's CPU-side state (SongPtr, TempoAcc / TempoTick, MusicOn, TrackCount, $0804-$08F1, DP $58 and
$34) at $7E:FF00 (LoROM) or $40:5C00 (SA-1); its jsl SoundInit calls SoundInit, then puts it back when a song was
kept and DP $34 (the sample set) is unchanged, MusicOn last.

From a live moment per ROM (snes_assist_stick_test.Game), the same presses on the original and the build:
  song cases: a home goal (the puck slid into the net, snes_midi_song_check's), its song playing 120 frames; then
    resume (START, B on Resume Game), stats (Game Stats, B, START / B back), replay (Instant Replay, 400 frames of
    it, START out): against the same moment played on unpaused: MusicOn and SongPtr after, track 0's pointer
    (TrackPtr $0804) changes against the reference's from the same pointer, the music tracks' instruments (TrackInst
    $086A) and the music voices sounding (VoiceState $08F2 nonzero, VoiceTrack $08FA under $10) at the same song
    positions, the sound ($0804-$08F1 and the voices) compared there, and the audio's loudness.
  nosong: a pause in live play with no song; exit: Exit Game (and its Yes), then START into a new game, 1,500 frames
    of it; many: 30 pauses in a row (Resume, Game Stats, Instant Replay in turn) 30-200 frames apart, then 1,800
    frames: music voices sounding with no song on (stuck notes), the clock running.
  Every frame, in every case, the kept area ($7E:FF00-$FFF7, or $40:5C00-$5CF7 on SA-1): each change, and whether
  the game was paused (sflags $15D8 bit 0).

python snes_organ_resume_check.py OUT ORIGINAL BUILD"""
import json
import sys
from pathlib import Path

import numpy as np

from snes_assist_stick_test import Game, POSITION, PFGOAL, PUCKC, CARRIER2, PUCK, ZPOS, GOALS, CLOCK
from gen_midi_song_check import capture
import lowload

SFLAGS, MUSICON, SONGPTR, TRACKCOUNT, TRACKPTR, TRACKINST = 0x15D8, 0x07F3, 0x07ED, 0x0801, 0x0804, 0x086A
VSTATE, VTRACK, PSITEM = 0x08F2, 0x08FA, 0x0D15


class R:
    def __init__(self, rom):
        self.G = Game(rom)
        self.e = self.G.e
        self.sa1 = self.G.g.sa1
        self.buf = capture(self.e)

    def b(self, a):
        return self.G.w(a) & 0xFF

    def keep(self):
        if self.sa1:
            return bytes(self.G.g.bw[0x5C00:0x5CF8])
        return bytes(self.e.ram[0xFF00:0xFFF8])

    def voices(self):
        return sum(1 for v in range(8) if self.b(VSTATE + v) and self.b(VTRACK + v) < 0x10)

    def frame(self, n=1, hold=()):
        out = []
        for _ in range(n):
            self.G.run(1, hold=list(hold))
            on = self.G.w(MUSICON) & 0xFF
            out.append(dict(pz=bool(self.G.w(SFLAGS) & 1), on=on, song=self.G.w(SONGPTR), pos=self.G.w(TRACKPTR),
                            v=self.voices(), keep=self.keep(), clock=self.G.w(CLOCK), a=len(self.buf)))
        return out

    def press(self, b, w):
        return self.frame(4, [b]) + self.frame(w)

    def paused(self):
        return bool(self.G.w(SFLAGS) & 1)

    def menu(self, kind, wait=120):
        t = self.press("START", 90)
        item = {"resume": 0, "replay": 1, "stats": 2}[kind]
        for _ in range(item):
            t += self.press("DOWN", 16)
        if kind == "resume":
            t += self.frame(wait)
        t += self.press("B", 400 if kind == "replay" else 200)
        if kind != "resume":
            t += self.press("START", 150)               # back to the menu (B would open the item again)
            for _ in range(4):
                t += self.press("UP", 16)
            t += self.press("B", 60)
        for _ in range(4):
            if not self.paused():
                break
            t += self.press("START", 90)
        return t

    def goal_song(self, base):
        """A home goal; S = its song 120 frames in."""
        G = self.G
        e = self.e
        e.unserialize(base)
        G.setw(CLOCK, 250)
        hk = next(k for k in range(6) if G.w(POSITION + 2 * k) not in (0, 0xFFFF))
        up = 1 if G.w(PFGOAL + 2 * hk) else -1
        gk = next(k for k in range(6, 12) if G.w(POSITION + 2 * k) == 0)
        g0 = G.w(GOALS)
        for f in range(3000):
            if f < (1 if self.sa1 else 60) and G.w(GOALS) == g0:
                G.put(gk, 90, 240 * up)
                G.put(PUCK, 0, 240 * up, 0, 0x2000 * up)
                G.setw(ZPOS, 0); G.setw(PUCKC, 0xFFFF); G.setw(CARRIER2, 0xFFFF)
            G.run(1)
            if G.w(GOALS) != g0 and G.w(MUSICON) & 0xFF:
                self.frame(120)
                return e.serialize() if G.w(MUSICON) & 0xFF else None
        return None


def changes(tr, start=0):
    out, last = [], None
    for i in range(start, len(tr)):
        p = tr[i]["pos"] if tr[i]["on"] else None
        if p is not None and p != last:
            out.append((i, p))
        last = p
    return out


def rms(r, a0, a1):
    x = np.asarray(r.buf[a0:a1], dtype=np.float32)
    return round(float(np.sqrt((x * x).mean())), 1) if len(x) else None


def sound_state(r):
    return [r.b(a) for a in range(0x0804, 0x08F2)], [r.G.w(TRACKINST + 2 * t) for t in range(4)]


def song_case(r, S, kind):
    e = r.e
    e.unserialize(S)
    ref = r.frame(1500)
    rp = changes(ref)
    e.unserialize(S)
    tr = r.menu(kind)
    pz = [i for i, t in enumerate(tr) if t["pz"]]
    row = dict(kind=kind, song=hex(r.G.w(SONGPTR)))
    if not pz:
        row["res"] = "no pause"
        return row
    last = pz[-1]
    tr += r.frame(1200)
    after = tr[last + 1:]
    back = next((i for i, t in enumerate(after) if t["on"]), None)
    row.update(pause_frames=last - pz[0] + 1, left_paused=r.paused(),
               keep_changes=[(i, t["pz"]) for i, t in enumerate(tr[1:], 1) if t["keep"] != tr[i - 1]["keep"]][:6])
    if back is None:
        row.update(res="no song after the pause", rms_after=rms(r, after[0]["a"], after[min(len(after) - 1, 600)]["a"]),
                   music_voices_after=sorted(set(t["v"] for t in after[:300])))
        return row
    bi = last + 1 + back
    cp = changes(tr, bi)
    j = next((j for j, (_, q) in enumerate(rp) if q == cp[0][1]), None) if cp else None
    row.update(res="song back", frames_after_pause=back, song_after=hex(tr[bi]["song"]),
               same_song=tr[bi]["song"] == ref[0]["song"])
    if j is not None:
        n = min(30, len(rp) - j, len(cp))
        row["next_positions_same"] = f"{sum(rp[j + t][1] == cp[t][1] for t in range(n))} of {n}"
        row["timing_from_the_second_same"] = f"{sum(rp[j + t][0] - rp[j + 1][0] == cp[t][0] - cp[1][0] for t in range(1, n))} of {n - 1}"
        row["music_voices_ref"] = [ref[rp[j + t][0]]["v"] for t in range(0, n, 3)]
        row["music_voices_after"] = [tr[cp[t][0]]["v"] for t in range(0, n, 3)]
        row["rms_ref"] = rms(r, ref[rp[j][0]]["a"], ref[min(len(ref) - 1, rp[j][0] + 600)]["a"])
        row["rms_after"] = rms(r, tr[cp[0][0]]["a"], tr[min(len(tr) - 1, cp[0][0] + 600)]["a"])
        # the sequencer's state at the same song positions: the unpaused game against the paused one
        diffs = []
        for step in (3, 8, 15):
            if j + step >= len(rp) or step >= len(cp):
                break
            target = rp[j + step][1]
            e.unserialize(S)
            for _ in range(1500):
                r.G.run(1)
                if r.G.w(TRACKPTR) == target and r.G.w(MUSICON) & 0xFF:
                    break
            a_state = sound_state(r)
            e.unserialize(S)
            r.menu(kind)
            for _ in range(2500):
                r.G.run(1)
                if not r.paused() and r.G.w(TRACKPTR) == target and r.G.w(MUSICON) & 0xFF:
                    break
            b_state = sound_state(r)
            diffs.append(dict(step=step, track_bytes_differing=sum(x != y for x, y in zip(a_state[0], b_state[0])),
                              instruments_same=a_state[1] == b_state[1]))
        row["at_the_same_positions"] = diffs
    else:
        row["pointer_not_in_reference"] = hex(cp[0][1]) if cp else None
    return row


def other_case(r, base, kind):
    e = r.e
    e.unserialize(base)
    t = r.frame(60)
    if kind == "nosong":
        r.G.setw(MUSICON, r.G.w(MUSICON) & 0xFF00)
        t += r.menu("resume") + r.frame(900)
    elif kind == "exit":
        t += r.press("START", 90)
        last = -1
        for _ in range(25):                         # Exit Game: the last item
            t += r.press("DOWN", 16)
            if r.G.w(PSITEM) == last:
                break
            last = r.G.w(PSITEM)
        t += r.press("B", 120) + r.press("DOWN", 30) + r.press("B", 120)   # "Exit Game?": Yes
        lastc = None
        for f in range(60 * 150):
            t += r.frame(1, ["START"] if f % 240 == 0 else [])
            c = r.G.w(CLOCK)
            if lastc is not None and 0 < c < lastc and not r.paused() and f > 600:
                break
            lastc = c
        t += r.frame(1500)
    elif kind == "many":
        rng = np.random.default_rng(5)
        for i in range(30):
            t += r.frame(int(rng.integers(30, 200)))
            if r.G.w(CLOCK) < 40:
                r.G.setw(CLOCK, 250)
            t += r.menu(("resume", "stats", "replay")[i % 3], wait=int(rng.integers(20, 120)))
            if i % 5 == 4:
                lowload.breathe()
        t += r.frame(1800)
    stuck = sum(1 for x in t if not x["on"] and x["v"] and not x["pz"])
    return dict(kind=kind, frames=len(t), left_paused=r.paused(), clock_end=r.G.w(CLOCK),
                frames_music_voice_with_no_song=stuck,
                songs=sorted(set(hex(x["song"]) for x in t if x["on"])),
                keep_changes=[(i, x["pz"]) for i, x in enumerate(t[1:], 1) if x["keep"] != t[i - 1]["keep"]][:8],
                keep_change_count=sum(1 for i in range(1, len(t)) if t[i]["keep"] != t[i - 1]["keep"])), t


def main():
    out, orig, build = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    res, traces = {}, {}
    for name, rom in (("orig", orig), ("build", build)):
        r = R(rom)
        base = r.G.g.bases[0]
        S = r.goal_song(base)
        rows = []
        if S is None:
            print(name, "no goal song")
        else:
            for kind in ("resume", "stats", "replay"):
                row = song_case(r, S, kind)
                rows.append(row)
                print(name, json.dumps(row), flush=True)
                lowload.breathe()
        for kind in ("nosong", "exit", "many"):
            row, tr = other_case(r, base, kind)
            traces[(name, kind)] = tr
            rows.append(row)
            print(name, json.dumps(row), flush=True)
            lowload.breathe()
        res[name] = rows
        del r
    for kind in ("nosong", "exit"):
        a, b = traces[("orig", kind)], traces[("build", kind)]
        n = min(len(a), len(b))
        key = lambda t: (t["pz"], t["on"], t["song"], t["pos"], t["v"], t["clock"])  # noqa: E731
        d = [i for i in range(n) if key(a[i]) != key(b[i])]
        line = f"{kind}: {len(a)} / {len(b)} frames; pause, song, position, music voices and clock differ in {len(d)}" + (f", first at {d[0]}" if d else "")
        res.setdefault("compare", []).append(line)
        print(line, flush=True)
    (out / f"organ_{Path(build).stem}.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
