"""NOSE4Web's MIDI-made SNES organ songs, played (2026-11-10: NHL94_songs_midi.smc, nhl94snes_SA1_songs_midi.sfc; San
Jose's Jaws Theme replaced by Brass Bonanza, Boston's power-play song by a Charge fanfare). From the code: MusicStart
sets TempoTick = $2760 / the header's tempo byte; SequencerTick (from SoundUpdate, called by the NMI every frame) adds
$40 a frame and runs a tick each time it passes TempoTick, so tempo 157 is one tick a frame on any build; StepTrack
stops the whole song (MusicStop) at the first $D9 / $DA any track reaches.

In live play (snes_assist_stick_test.Game) with HomeTeam ($1C98) the team, the faceoff on a home power play (PBnum
$1624 = $01: TeamSongs slot 1, as snes_songs_check.py drives it): the song MusicStart gets (SongPtr $07ED, bank at
$58), the frames until MusicOn ($07F3) goes 0, whether the effects track (TrackPtr + 32: track 16) runs meanwhile, and
the audio into a WAV; `interrupt`: the period run out 100 frames into the song (PeriodOver starts its song).

python snes_midi_song_check.py OUT ROM [ROM ...]"""
import struct
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from snes_assist_stick_test import Game, PUCKC, CARRIER2, POSITION, PFGOAL, PUCK, ZPOS  # noqa: E402
from gen_midi_song_check import capture  # noqa: E402
from snes_songs_check import HOMETEAM, CURSONG, SONGPTR, BANK, MUSICON, PBNUM, GOALS, song  # noqa: E402

TRACKPTR = 0x0804


def team_index(rom, city):
    from systems import snes
    teams = snes.read_teams(Path(rom))
    return next(i for i, t in enumerate(teams) if t["name"] == city)


def slide_goal(G, up, gk):
    G.put(gk, 90, 240 * up)
    G.put(PUCK, 0, 240 * up, 0, 0x2000 * up)
    G.setw(ZPOS, 0)
    G.setw(PUCKC, 0xFFFF)
    G.setw(CARRIER2, 0xFFFF)


def play(G, base, team, out, label, interrupt=False):
    e = G.e
    e.unserialize(base)
    G.setw(HOMETEAM, team)
    G.setw(0x1632, 250)
    hk = next(k for k in range(6) if G.w(POSITION + 2 * k) not in (0, 0xFFFF))
    up = 1 if G.w(PFGOAL + 2 * hk) else -1
    gk = next(k for k in range(6, 12) if G.w(POSITION + 2 * k) == 0)
    g0 = G.w(GOALS)
    buf = capture(e)
    start, songs, cut, fx, ended, last_fx = None, [], 0, 0, None, None
    for f in range(4000):
        if start is None:
            if f < 60:
                slide_goal(G, up, gk)
            if G.w(GOALS) != g0 and any(c == 4 for c, _ in songs):
                G.setw(MUSICON, 0)
                G.setw(PBNUM, 0x01)
        G.run(hold=["B"] if start is None and f % 40 == 0 and f > 300 else [])
        cur = (G.w(CURSONG), song(G))
        if not songs or cur != songs[-1]:
            songs.append(cur)
            if start is None and cur[0] == 2:          # slot 1 + 1
                start, cut, target = f, len(buf), cur[1]
        if start is not None:
            tp = G.w(TRACKPTR + 32)
            fx += tp != last_fx and tp not in (0, 0xFFFF)
            last_fx = tp
            if f - start == 60:
                G.setw(0x1632, 3)                       # an effect to hear: the clock running out sounds the horn
            if interrupt and f - start == 100:
                G.setw(0x1632, 1)                       # the period ends: PeriodOver starts its own song
            if ended is None and (not G.w(MUSICON) or song(G) != target):
                ended = f
                if not interrupt:
                    break
            if interrupt and ended is not None and f - ended > 120:
                break
    if start is None:
        return {"label": label, "error": "no power-play song", "songs": [(c, hex(s)) for c, s in songs]}
    pcm = buf[cut:]
    path = out / f"{label}.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(32040)
        w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))
    left = sum(abs(pcm[i]) for i in range(0, len(pcm), 2))
    right = sum(abs(pcm[i]) for i in range(1, len(pcm), 2))
    return {"label": label, "song": hex(target), "frames": (ended or f) - start,
            "ended by": ("the next song" if ended and song(G) != target else "MusicOn 0") if ended else "still on",
            "songs after": [(c, hex(s)) for c, s in songs[-3:]], "effect starts on track 16 during the song": fx,
            "left / right loudness": round(left / max(1, right), 2), "wav": str(path)}


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for rom in sys.argv[2:]:
        G = Game(rom)
        base = G.g.bases[0]
        for city in ("San Jose", "Boston"):
            t = team_index(rom, city)
            stem = Path(rom).stem
            for inter in (False, True):
                r = play(G, base, t, out, f"{stem}_{city.replace(' ', '')}{'_interrupt' if inter else ''}", inter)
                print(stem, city, r, flush=True)


if __name__ == "__main__":
    main()
