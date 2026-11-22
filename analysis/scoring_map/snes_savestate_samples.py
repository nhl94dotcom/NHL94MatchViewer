"""SNES save states at a game's end, for a site that reads stats out of state files (2026-11-22, the league site's
PHP: it reads RetroArch Snes9x states at fixed positions and fails on the 2 MB and SA-1 builds).

A computer game on each ROM (snes_momentum_blocks_check.boot: regular season, penalties on, the computer on both
sides, periods capped at 5 minutes; seed after seed until one is decided in regulation), then 10 s (real) into the
game-over screens, the stats unchanged over them. Each state is the core's own (Snes9x: our copy of the user's
RetroArch core) in the layout RetroArch 1.17 writes, checked byte for byte against the user's own states' layout:
"RASTATE" 01, then blocks of a 4-letter tag, a 32-bit length and the data padded to 8 bytes: "MEM " (the core's
state), then "END " (length 0). The compressed one is the same file through RetroArch's rzip stream ("#RZIPv" 01 "#",
a 32-bit chunk size, a 64-bit whole length, then chunks: a 32-bit length and zlib data).

For each: NAME.state (and NAME_compressed.state for the first ROM) and NAME.json: the score, goals and shots by
period, the team checks, every player's goals and assists, each player's checks for and against where the build keeps
them, and where each of those sits in the file (found there again by the file reader below, which works from the
file's bytes alone: Snes9x's blocks "RAM" work RAM, "SRA" the cartridge RAM, which on the SA-1 build holds the
game's low RAM and the extra stats).

python snes_savestate_samples.py OUT ROM [ROM ...]"""
import json
import struct
import sys
import zlib
from pathlib import Path

import lowload
import snes_60fps_cvc as cvc
from snes_momentum_blocks_check import boot, CLOCK, GSP

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from systems import snes as S  # noqa: E402

MOVED = ((0x0100, 0x2000, 0x6100), (0x30F4, 0x35F4, 0x30F4), (0x37F4, 0x47F4, 0x37F4), (0xE700, 0xE868, 0xE700))
P_GOALS, P_ASSISTS = 0x18EE, 0x1922


def rastate(core):
    return b"RASTATE\x01" + b"MEM " + struct.pack("<I", len(core)) + core + b"\0" * (-len(core) & 7) + b"END " + b"\0" * 4


def rzip(data, chunk=131072):
    out = [b"#RZIPv\x01#", struct.pack("<IQ", chunk, len(data))]
    for i in range(0, len(data), chunk):
        z = zlib.compress(data[i:i + chunk], 6)
        out += [struct.pack("<I", len(z)), z]
    return b"".join(out)


def unrzip(raw):
    assert raw[:8] == b"#RZIPv\x01#"
    chunk, total = struct.unpack_from("<IQ", raw, 8)
    i, out = 20, []
    while i < len(raw):
        n, = struct.unpack_from("<I", raw, i)
        out.append(zlib.decompress(raw[i + 4:i + 4 + n]))
        i += 4 + n
    data = b"".join(out)
    assert len(data) == total
    return data


def blocks(raw):
    """Where Snes9x's blocks sit in a state file: (the file's bytes, {name: (file offset of the data, length)})."""
    if raw[:6] == b"#RZIPv":
        raw = unrzip(raw)
    assert raw[:8] == b"RASTATE\x01" and raw[8:12] == b"MEM "
    i = 16
    assert raw[i:i + 9] == b"#!s9xsnp:"
    i = raw.index(b"\n", i) + 1
    end = 16 + struct.unpack_from("<I", raw, 12)[0]
    out = {}
    while i + 11 <= end and raw[i + 3:i + 4] == b":" and raw[i + 10:i + 11] == b":":
        name, n = raw[i:i + 3].decode(), int(raw[i + 4:i + 10])
        out[name] = (i + 11, n)
        i += 11 + n
    return raw, out


class FileRam:
    """The game's RAM by its address, from a state file's bytes alone."""
    def __init__(self, raw, sa1):
        self.raw, self.blocks = blocks(raw)
        self.sa1 = sa1

    def offset(self, a):
        if self.sa1:
            for lo, hi, to in MOVED:
                if lo <= a < hi:
                    return self.blocks["SRA"][0] + to + a - lo
        return self.blocks["RAM"][0] + a

    def b(self, a):
        return self.raw[self.offset(a)]

    def w(self, a):
        o = self.offset(a)
        return self.raw[o] | self.raw[o + 1] << 8


def stats(r, extra):
    pair = lambda a: [r.w(a), r.w(a + 2)]  # noqa: E731
    per = lambda a: [[r.b(a + 26 * t + j) for j in range(26)] for t in (0, 1)]  # noqa: E731
    d = dict(teams=pair(S.TEAM_IDS[0]), score=pair(S.STAT_ADDRESSES["goals"]),
             goals_by_period=[pair(a) for a in S.GOALS_BY_PERIOD], shots_by_period=[pair(a) for a in S.SHOTS_BY_PERIOD],
             team_checks=pair(S.STAT_ADDRESSES["checks"]), player_goals=per(P_GOALS), player_assists=per(P_ASSISTS),
             at_168E=per(0x168E), at_16C2=per(0x16C2))
    if extra:
        d.update(at_E788=per(S.CHECKS_FOR), at_E7BC=per(S.CHECKS_AGAINST))
    d["scoring_bytes"] = [r.b(S.SCORING_COUNT + i) for i in range(2 + 6 * 12)]
    return d


class Live:
    def __init__(self, m):
        self.m = m

    def w(self, a):
        return self.m.w(a)

    def b(self, a):
        buf, o = self.m.at(a)
        return buf[o]


def run(out, rom, first):
    name = Path(rom).stem
    extra = Path(rom).stat().st_size > 0x100000
    for n in range(40):
        e, m = boot(rom, n)
        live = Live(m)
        frames, still, last = 0, 0, None
        while m.w(GSP) < 3 and frames < 60 * 60 * 40:
            if frames % 60 == 0:
                cvc.computer_only(m)
                if m.w(CLOCK) > 300:
                    m.setw(CLOCK, 300)
                still = still + 1 if m.w(CLOCK) == last else 0
                last = m.w(CLOCK)
                if frames % 3600 == 0:
                    lowload.breathe()
            e.run(1, hold=["START"] if still >= 15 and frames % 60 < 4 else [])
            frames += 1
        sc = [m.w(0x178E), m.w(0x1790)]
        print(name, "seed", n, "score", sc, "frames", frames, flush=True)
        if m.w(GSP) >= 3 and sc[0] != sc[1] and sum(sc) >= 3:
            break
    else:
        raise SystemExit("no decided game")
    at_end = stats(live, extra)
    e.run(600)
    after = stats(live, extra)
    core = e.serialize()
    raw = rastate(core)
    (out / f"{name}.state").write_bytes(raw)
    e.screenshot(out / f"{name}.png")
    fr = FileRam(raw, m.sa1)
    from_file = stats(fr, extra)
    info = dict(rom=Path(rom).name, rom_crc32=f"{zlib.crc32(Path(rom).read_bytes()):08X}", sa1=m.sa1, seed=n,
                file_bytes=len(raw), core_state_bytes=len(core),
                blocks={k: dict(offset=v[0], length=v[1]) for k, v in fr.blocks.items()},
                offsets={k: fr.offset(a) for k, a in (("score", 0x178E), ("goals_by_period", S.GOALS_BY_PERIOD[0]),
                                                       ("shots_by_period", S.SHOTS_BY_PERIOD[0]), ("team_checks", 0x17B6),
                                                       ("player_goals", P_GOALS), ("player_assists", P_ASSISTS),
                                                       ("$168E", 0x168E), ("$16C2", 0x16C2), ("$E788", S.CHECKS_FOR),
                                                       ("$E7BC", S.CHECKS_AGAINST), ("scoring_summary", S.SCORING_COUNT))},
                stats=from_file, same_as_live=from_file == after, unchanged_over_the_end_screens=at_end == after)
    if first:
        z = rzip(raw)
        (out / f"{name}_compressed.state").write_bytes(z)
        info["compressed_bytes"] = len(z)
        info["compressed_reads_the_same"] = stats(FileRam(z, m.sa1), extra) == from_file
    e2, m2 = boot(rom, 0)                                    # the file loads back into a fresh core
    e2.load_state(out / f"{name}.state")
    info["loads_back"] = stats(Live(m2), extra) == from_file
    (out / f"{name}.json").write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k != "stats"}), flush=True)


if __name__ == "__main__":
    lowload.gentle()
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for i, rom in enumerate(sys.argv[2:]):
        run(out, rom, i == 0)
