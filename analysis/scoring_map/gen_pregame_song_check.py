"""NOSE4Web's home-team pre-game song (2026-11-27; nhl94_pregame.bin, NHL_95_pregame.bin): the matchup (scouting)
screen plays a song chosen by HomeTeam from a 1-word-a-team table instead of the fixed one (NHL '94 $7A, NHL '95 3),
-1 for silence. Played against retail, the same presses on both.

Each ROM: power-on to Game Setup once (a saved state), then for each team: the teams set on Game Setup (NHL '94
Opt1team $D04C / Opt2team $D04E; NHL '95 setupvalues+1 / +2 $D283 / $D284, which SetupStart copies to Opt1team and
HomeTeam), DOWN / UP, START into the matchup screen, held there SCOUT frames, then START through the screens after it
into play and PLAY frames of play. Every frame the sound driver's slots: NHL '94 fm_track_slots $D3D4 (stream
pointers, mapped to the song whose stream they're in: the song table $2C648; below song $30's a sound effect); NHL '95
the sequencer slots' ids SndSeqId $FE3E and positions SndSeqPos $FE1E (pointers $FDFE, -1 free). Logged: each change in
the set of songs playing (frame, phase), loops (a slot's position going back inside the same song), and the core's
audio: a WAV per run and its loudness every 0.5 s. HomeTeam read on the matchup screen (NHL '94 $C330, '95 $BF54).

NHL '95's boot presses START until the screen matches a Game Setup screenshot (env PREGAME95_SETUP: the retail
ROM's checksum check makes it miss presses the build takes), and goes through Controller Setup to the matchup screen.

python gen_pregame_song_check.py OUT RETAIL BUILD TEAM [TEAM ...]   (the system by the ROM's size: 2 MB NHL '95)"""
import json
import os
import struct
import sys
import wave
from pathlib import Path

import numpy as np

from emu import Emu
from gen_midi_song_check import capture, slots, TABLE
import lowload

SCOUT, PLAY = 6600, 2400                  # 110 s on the matchup screen (NHL '94's $7A runs about 87 s before it loops)


class Sys94:
    HOME, OPT1, OPT2, SCREEN = 0xC330, 0xD04C, 0xD04E, 0xFFF7

    def __init__(self, rom):
        self.st = {s: struct.unpack_from(">I", rom, TABLE + 4 * s)[0] for s in range(0x30, 0x80)}
        self.order = sorted(self.st.items(), key=lambda kv: kv[1])

    def boot(self, e):
        e.run(900); e.run(4, hold=["START"]); e.run(120); e.run(4, hold=["START"]); e.run(320)

    def set_teams(self, e, h, v):
        e.setw(self.OPT1, h); e.setw(self.OPT2, v)

    def to_scout(self, step):
        step(4, "scout", ["START"])

    def playing(self, e):
        out = []
        for k, p in enumerate(slots(e)):
            if p & 0x80000000:
                continue
            if p < self.st[0x30]:
                out.append((k, "sfx", p))
                continue
            sid = None
            for s, a in self.order:
                if a <= p:
                    sid = s
            out.append((k, hex(sid), p))
        return out

    def in_play(self, e):
        return e.b(self.SCREEN) == 0


class Sys95:
    HOME, SV1, SV2, CLOCK = 0xBF54, 0xD283, 0xD284, 0xC022
    PTR, POS, SID = 0xFDFE, 0xFE1E, 0xFE3E

    TEMPLATE = None                      # a Game Setup screenshot (the boot presses until the screen matches it)

    def boot(self, e):
        import tempfile
        from PIL import Image
        ref = np.asarray(Image.open(self.TEMPLATE).convert("RGB")).astype(int)
        e.run(1500)
        tmp = Path(tempfile.gettempdir()) / "pregame95_look.png"
        for _ in range(12):
            e.screenshot(tmp)
            a = np.asarray(Image.open(tmp).convert("RGB")).astype(int)
            if a.shape == ref.shape and np.abs(a - ref).mean() < 12:
                return
            e.run(6, hold=["START"]); e.run(200)
        raise SystemExit("NHL '95: Game Setup not reached")

    def to_scout(self, step):
        step(6, "scout", ["START"]); step(200, "scout")      # Game Setup -> Controller Setup
        step(6, "scout", ["START"])                           # -> the matchup screen

    def set_teams(self, e, h, v):
        e.setb(self.SV1, h); e.setb(self.SV2, v)

    def playing(self, e):
        out = []
        for k in range(8):
            if e.l(self.PTR + 4 * k) == 0xFFFFFFFF:
                continue
            out.append((k, hex(e.w(self.SID + 2 * k)), e.l(self.POS + 4 * k)))
        return out

    def in_play(self, e):
        c = e.w(self.CLOCK)
        e.run(30)
        return e.w(self.CLOCK) != c and c != 0


def loud(pcm):
    a = np.asarray(pcm, dtype=np.float64)
    step = 2 * 22050
    return [round(float(np.sqrt(np.mean(a[i:i + step] ** 2)))) if len(a[i:i + step]) else 0 for i in range(0, len(a), step)]


def one(e, sysm, state, team, vis, out, tag):
    e.unserialize(state)
    buf = e._pcm
    del buf[:]
    sysm.set_teams(e, team, vis)
    log, prev, loops, f = [], None, {}, 0
    last_pos = {}
    marks = {}

    def step(n, phase, hold=()):
        nonlocal prev, f
        for _ in range(n):
            e.run(1, hold=list(hold))
            f += 1
            now = sysm.playing(e)
            songs = sorted({s for _, s, _ in now if s != "sfx"})
            for k, s, p in now:
                if s == "sfx":
                    continue
                q = last_pos.get(k)
                if q and q[0] == s and p < q[1] - 64:
                    loops[(phase, s)] = loops.get((phase, s), 0) + 1
                last_pos[k] = (s, p)
            for k in list(last_pos):
                if k not in {kk for kk, _, _ in now}:
                    del last_pos[k]
            if songs != prev:
                log.append(dict(f=f, phase=phase, songs=songs))
                prev = songs

    step(4, "setup", ["DOWN"]); step(30, "setup"); step(4, "setup", ["UP"]); step(60, "setup")
    marks["scout"] = len(buf)
    sysm.to_scout(step)
    step(120, "scout")
    home = e.w(sysm.HOME)
    e.screenshot(out / f"{tag}_scout.png")
    step(SCOUT - 120, "scout")
    marks["after"] = len(buf)
    for _ in range(40):
        if isinstance(sysm, Sys94) and sysm.in_play(e):
            break
        if isinstance(sysm, Sys95) and sysm.in_play(e):
            break
        step(4, "to_play", ["START"]); step(150, "to_play")
    marks["play"] = len(buf)
    play_f = f
    e.screenshot(out / f"{tag}_play.png")
    step(PLAY, "play")
    pcm = list(buf)
    with wave.open(str(out / f"{tag}.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
    res = dict(tag=tag, team=team, home_on_scout=home, play_from=play_f, events=log,
               loops={f"{p} {s}": n for (p, s), n in loops.items()},
               loud_scout=loud(pcm[marks["scout"]:marks["after"]]),
               loud_after=loud(pcm[marks["after"]:marks["play"]]),
               loud_play=loud(pcm[marks["play"]:]))
    print(json.dumps({k: v for k, v in res.items() if not k.startswith("loud")}), flush=True)
    print("   loudness scout (every 2 s):", res["loud_scout"][::4], flush=True)
    print("   loudness after START (every 2 s):", res["loud_after"][::4], flush=True)
    print("   loudness in play (every 2 s):", res["loud_play"][::4], flush=True)
    lowload.breathe()
    return res


def main():
    out, retail, build = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    Sys95.TEMPLATE = os.environ.get("PREGAME95_SETUP", "")
    teams = [int(t) for t in sys.argv[4:]]
    out.mkdir(parents=True, exist_ok=True)
    allres = {}
    for name, rom in (("retail", retail), ("build", build)):
        data = Path(rom).read_bytes()
        sysm = Sys95() if len(data) > 0x100000 else Sys94(data)
        e = Emu(rom)
        e._pcm = capture(e)
        sysm.boot(e)
        e.screenshot(out / f"{name}_setup.png")
        state = e.serialize()
        allres[name] = [one(e, sysm, state, t, 22 if t != 22 else 4, out, f"{name}_team{t:02d}") for t in teams]
    (out / "results.json").write_text(json.dumps(allres, indent=1))


if __name__ == "__main__":
    main()
