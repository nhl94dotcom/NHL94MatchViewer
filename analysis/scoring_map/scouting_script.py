"""Ron Barr's matchup-screen script as a ROM holds it (2026-11-12, for NOSE4Web 6806a72's text editor): found the way
NOSE4Web finds it (Genesis: the movea.l #ScoutingReportText,a1 after the timer test; SNES: lda #bank / lda #address
before PlayerScrollCtr), every line up to the last $0D before non-text bytes, numbered, and the bytes after the
script (the Genesis main menu picture, the SNES music) so two ROMs can be compared past it.

python scouting_script.py ROM [ROM2]   (two: the lines that differ, and whether the bytes after the room match)"""
import re
import sys
from pathlib import Path

GEN = re.compile(rb"\x0c\x78\x10\x00..\x6e\x00..\x4a\x78..\x6b\x00..\x53\x78..\x6a\x00..\x22\x7c(....)", re.S)
SNES = re.compile(rb"\xce..\x10.\xa9(.)\x00\x85.\xa9(..)\x85.\xad..\x85.\x10", re.S)


def lorom(bank, addr):
    return ((bank & 0x7F) << 15) | (addr & 0x7FFF)


def locate(rom):
    m = GEN.search(rom)
    if m:
        return "genesis", int.from_bytes(m.group(1), "big")
    places = {lorom(m.group(1)[0], int.from_bytes(m.group(2), "little")) for m in SNES.finditer(rom)
              if int.from_bytes(m.group(2), "little") >= 0x8000}
    if len(places) == 1:
        return "snes", places.pop()
    raise SystemExit(f"script not found ({len(places)} SNES places)")


def script(rom):
    system, at = locate(rom)
    end = -1
    for o in range(at, min(len(rom), at + 0x1000)):
        if rom[o] == 0x0D:
            end = o + 1
        elif not 0x20 <= rom[o] < 0x7F:
            break
    lines = rom[at:end - 1].decode("latin-1").split("\r")
    return system, at, end, lines


def main():
    roms = [Path(a).read_bytes() for a in sys.argv[1:]]
    found = [script(r) for r in roms]
    for path, (system, at, end, lines) in zip(sys.argv[1:], found):
        print(f"{Path(path).name}: {system}, script at ${at:X}-${end:X} ({end - at} bytes), {len(lines)} lines")
    if len(found) == 1:
        for i, t in enumerate(found[0][3]):
            if t:
                print(f"  {i:2d} [{len(t):3d}] {t!r}")
        return
    (_, a1, e1, l1), (_, a2, e2, l2) = found
    extra = 0
    for i in range(max(len(l1), len(l2))):
        x, y = (l1[i] if i < len(l1) else None), (l2[i] if i < len(l2) else None)
        if x is None and y == "" or y is None and x == "":
            extra += 1
        elif x != y:
            print(f"  line {i}:\n    1: {x!r}\n    2: {y!r}")
    if extra:
        print(f"  {extra} more empty lines in one of them (the room's fill)")
    end = max(e1, e2)
    print(f"same start: {a1 == a2}; the 256 bytes after the room (${end:X}) equal: {roms[0][end:end + 256] == roms[1][end:end + 256]}")
    if len(roms[0]) == len(roms[1]):
        diff = [k for k in range(len(roms[0])) if roms[0][k] != roms[1][k] and not a1 <= k < end]
        runs = []
        for k in diff:
            if runs and k == runs[-1][1] + 1:
                runs[-1][1] = k
            else:
                runs.append([k, k])
        print("bytes changed outside the room: " + (", ".join(f"${a:X}-${b:X}" for a, b in runs[:20]) or "none"))


if __name__ == "__main__":
    main()
