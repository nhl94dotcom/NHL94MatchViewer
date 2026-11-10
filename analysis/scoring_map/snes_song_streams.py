"""SNES songs decoded (2026-11-10, for NOSE4Web's MIDI-made SNES songs). From the code (sound/MusicStart, StepTrack,
ReadTrackEvent, ReadVarLen): the header's byte 1 is the tempo (TempoTick = $2760 / it; one tick a frame at 157),
byte 6 the track count, and from byte 8 word offsets to the tracks (from the song's start), ended by 0. A track is
[delta][event][delta][event] ...: deltas are variable-length (7 bits a byte, top bit = more) ticks, the first one
read and dropped (every track's first event is at tick 0). Events: a code below $D9 is a note (a velocity byte, then
a variable-length length in ticks); $D9 / $DA stop the whole song; $DB loop end; $E3 no data; $DC (instrument),
$EA, $DD (tempo), $DE (volume), $E2 (loop start) one byte; $DF (controller) two; $E5 two; $E7 a length byte and
that much text; the rest none.

python snes_song_streams.py ROM BANK:ADDR [BANK:ADDR ...]   (a LoROM address, e.g. 99:BB80)"""
import sys


def lorom(addr):
    bank, a = addr >> 16, addr & 0xFFFF
    return (bank & 0x7F) * 0x8000 + (a - 0x8000)


def varlen(rom, at):
    v = 0
    while True:
        b = rom[at]
        at += 1
        v = (v << 7) | (b & 0x7F)
        if not b & 0x80:
            return v, at


def decode(rom, addr):
    base = lorom(addr)
    tempo, ntracks = rom[base + 1], rom[base + 6]
    offs, k = [], 8
    while True:
        o = rom[base + k] | rom[base + k + 1] << 8
        if not o:
            break
        offs.append(o)
        k += 2
    tracks = []
    for o in offs:
        at = base + o
        _, at = varlen(rom, at)                   # the first delta, dropped
        t, notes, cmds, end = 0, [], [], None
        for _ in range(5000):
            code = rom[at]
            at += 1
            if code < 0xD9:
                vel = rom[at]
                at += 1
                length, at = varlen(rom, at)
                notes.append((t, code, vel, length))
            elif code in (0xD9, 0xDA):
                end = t
                break
            elif code == 0xE7:
                at += rom[at] + 1
            elif code in (0xDC, 0xEA, 0xDD, 0xDE, 0xE2):
                cmds.append((t, hex(code), rom[at]))
                at += 1
            elif code in (0xDF, 0xE5):
                cmds.append((t, hex(code), rom[at], rom[at + 1]))
                at += 2
            else:
                cmds.append((t, hex(code)))
            d, at = varlen(rom, at)
            t += d
        tracks.append(dict(offset=hex(o), end=end, notes=notes, cmds=cmds[:12],
                           last_note_end=max((n[0] + n[3] for n in notes), default=0)))
    return tempo, ntracks, tracks


def main():
    rom = open(sys.argv[1], "rb").read()
    if len(rom) % 0x8000 == 0x200:
        rom = rom[0x200:]
    for a in sys.argv[2:]:
        tempo, n, tracks = decode(rom, int(a.replace(":", ""), 16))
        print(f"{a}: tempo {tempo} (TempoTick {0x2760 // tempo}), {n} tracks")
        for i, tr in enumerate(tracks):
            print(f"   track {i} at +{tr['offset']}: {len(tr['notes'])} notes, $D9 at tick {tr['end']}, last note ends "
                  f"{tr['last_note_end']}; commands {tr['cmds']}; first notes {tr['notes'][:6]}")


if __name__ == "__main__":
    main()
