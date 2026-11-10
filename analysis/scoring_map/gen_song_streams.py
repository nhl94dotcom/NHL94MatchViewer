"""Genesis song event streams, decoded and compared (2026-11-10, for NOSE4Web's MIDI-to-organ songs).

The format (sound94; STUDY_NOTES "the song format"): 4-byte events, a delay in frames to the next (0-255), a status
byte (command in bits 6-4, MIDI channel in 3-0), two data bytes. Commands: 0 key off, 1 key on (note, velocity; 0 =
off), 3 controller (7 volume), 4 program change, 6 pitch bend; status 0 ends the stream (or loops to a long pointer).
SoundStreamTable at $2C648 in retail nhl94.bin (long pointers, sounds 0-$7A).

- `notes ROM SONG`: the song's events as notes: (start frame, length in frames, channel, note), the program changes
  and volumes, the most notes sounding at once, and the length in frames.
- `compare ROM_A SONG_A ROM_B SONG_B`: the two note lists side by side: notes in both at the same start and pitch, and
  the length and start differences; then which notes each has that the other doesn't.
- `find ROM_A SONG_A ROM_B`: which of ROM_B's songs $30-$7A shares the most notes (pitch and start) with ROM_A's song.

python gen_song_streams.py notes ROM SONG | compare ROM_A SONG_A ROM_B SONG_B | find ROM_A SONG_A ROM_B"""
import struct
import sys
from collections import Counter

TABLE = 0x2C648


def stream(rom, song):
    ptr = struct.unpack_from(">I", rom, TABLE + 4 * song)[0]
    return ptr


def decode(rom, song, limit=20000):
    at = stream(rom, song)
    t, events, programs, volumes = 0, [], [], []
    for _ in range(limit):
        if at + 4 > len(rom):
            break
        delay, status, a, b = rom[at:at + 4]
        if status == 0:
            break
        cmd, ch = (status >> 4) & 7, status & 15
        if cmd == 1 and b:
            events.append((t, "on", ch, a))
        elif cmd == 0 or (cmd == 1 and not b):
            events.append((t, "off", ch, a))
        elif cmd == 4:
            programs.append((t, ch, a))
        elif cmd == 3 and a == 7:
            volumes.append((t, ch, b))
        t += delay
        at += 4
    # pair the ons and offs into notes
    sounding, notes, most = {}, [], 0
    for tt, kind, ch, n in events:
        if kind == "on":
            if (ch, n) in sounding:
                notes.append((sounding.pop((ch, n)), tt))
            sounding[(ch, n)] = (tt, ch, n)
        elif (ch, n) in sounding:
            notes.append((sounding.pop((ch, n)), tt))
        most = max(most, len(sounding))
    for (ch, n), s in sounding.items():
        notes.append((s, t))
    out = sorted((s[0], e - s[0], s[1], s[2]) for s, e in notes)
    return {"notes": out, "programs": programs, "volumes": volumes, "frames": t, "most_at_once": most,
            "pointer": hex(stream(rom, song))}


def main():
    what = sys.argv[1]
    if what == "notes":
        rom, song = open(sys.argv[2], "rb").read(), int(sys.argv[3], 16)
        d = decode(rom, song)
        print({k: v for k, v in d.items() if k != "notes"}, len(d["notes"]), "notes")
        for n in d["notes"][:40]:
            print("  ", n)
    elif what == "find":
        a, sa, b = open(sys.argv[2], "rb").read(), int(sys.argv[3], 16), open(sys.argv[4], "rb").read()
        mine = Counter((s, n) for s, _, _, n in decode(a, sa)["notes"])
        scores = []
        for song in range(0x30, 0x7B):
            try:
                theirs = Counter((s, n) for s, _, _, n in decode(b, song)["notes"])
            except (struct.error, IndexError):
                continue
            # allow a constant shift in time: the best of the first 40 offsets of start against start
            best = 0
            for shift in {s2 - s1 for (s1, _) in list(mine)[:5] for (s2, _) in list(theirs)[:40]}:
                best = max(best, sum((mine & Counter((s - shift, n) for s, n in theirs.elements())).values()))
            scores.append((best, song))
        for sc, song in sorted(scores, reverse=True)[:5]:
            print(f"song ${song:02X}: {sc} of {sum(mine.values())} notes match (pitch and start, after a shift)")
    else:
        a, sa, b, sb = open(sys.argv[2], "rb").read(), int(sys.argv[3], 16), open(sys.argv[4], "rb").read(), int(sys.argv[5], 16)
        da, db = decode(a, sa), decode(b, sb)
        print("A:", {k: v for k, v in da.items() if k != "notes"}, len(da["notes"]), "notes")
        print("B:", {k: v for k, v in db.items() if k != "notes"}, len(db["notes"]), "notes")
        shift = db["notes"][0][0] - da["notes"][0][0]
        na = Counter((s, n) for s, _, _, n in da["notes"])
        nb = Counter((s - shift, n) for s, _, _, n in db["notes"])
        both = na & nb
        print(f"start shift {shift} frames; notes in both (start and pitch): {sum(both.values())}; only in A: "
              f"{sum((na - nb).values())}; only in B: {sum((nb - na).values())}")
        la = {(s, n): l for s, l, _, n in da["notes"]}
        lb = {(s - shift, n): l for s, l, _, n in db["notes"]}
        dl = Counter(lb[k] - la[k] for k in both)
        print("length differences (B - A, frames) over the shared notes:", dict(dl.most_common(8)))
        print("only in A (start, note):", sorted((na - nb).elements())[:20])
        print("only in B (start, note):", sorted((nb - na).elements())[:20])


if __name__ == "__main__":
    main()
