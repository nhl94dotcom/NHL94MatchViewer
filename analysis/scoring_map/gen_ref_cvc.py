"""Penalties by type in computer games, any Genesis ROM (2026-11-19, for NOSE4Web's referee strictness option:
checkagr's range multiplier, mulu.w #$D,d0 at $13E30, word $13E32, and goalie interference's threshold, cmp.w #4,d0,
word $13CAA).

Each game: power-on to Game Setup (gen_ot_check.to_setup), line changes off, the shortest periods (5 minutes),
penalties On Except Off-sides, START into play, the seed $D066 from the game's number, the computer on both sides
(cont1team / cont2team cleared and the person flag taken off every second), three periods. The penalty summary
($C5DC: its length word, then 4 bytes each: time, team | rule, roster index) is read every second and its entries
kept as they come.

`build RETAIL OUT_DIR` writes the four levels on RETAIL with only those two words changed (the boot
self-check's call at $300 made NOPs, the header checksum set):
ref_veryLenient (26, 2), ref_lenient (17, 3), ref_strict (9, 6), ref_veryStrict (6, 10).

python gen_ref_cvc.py ROM GAMES OUT.jsonl [FIRST]   |   report OUT.jsonl ...   |   build RETAIL OUT_DIR"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

OPTPEN, OPTLINE, PERLEN, SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD056, 0xD058, 0xD050, 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
BASE, SZ, PENS = 0xB04A, 0x80, 0xC5DC
RULES = {0x12: "roughing (injury)", 0x16: "charging", 0x18: "slashing", 0x1A: "roughing", 0x1C: "cross-checking",
         0x1E: "hooking", 0x20: "tripping", 0x22: "interference", 0x24: "holding", 0x26: "fighting", 0x28: "fighting",
         0x2A: "instigating"}
LEVELS = {"veryLenient": (26, 2), "lenient": (17, 3), "strict": (9, 6), "veryStrict": (6, 10)}


def game(rom, n):
    e = Emu(rom)
    G.to_setup(e, Path(rom).parent)
    e.setw(PERLEN, 0)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    pens, seen = [], 0
    frame, still, last = 0, 0, None
    while e.w(GSP) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            ln = e.w(PENS)
            if 0 < ln <= 240:
                while seen + 4 <= ln:
                    t, code = e.w(PENS + 2 + seen), e.b(PENS + 4 + seen)
                    pens.append(dict(period=t >> 14, secs=t & 0x3FFF, team=1 if code & 0x80 else 0,
                                     rule=RULES.get(code & 0x7F, hex(code & 0x7F))))
                    seen += 4
            if frame % 3600 == 0:
                lowload.breathe()
        e.run(1, hold=["START"] if still >= 8 and frame % 60 < 2 else [])
        frame += 1
    return {"game": n, "rom": Path(rom).name, "frames": frame, "penalties": pens,
            "goals": [e.w(0xC6CE + 0xC), e.w(0xCA32 + 0xC)]}


def report(paths):
    rows = []
    for path in paths:
        R = [json.loads(line) for line in open(path) if line.strip()]
        R = [r for r in R if not r.get("error")]
        c = Counter(p["rule"] for r in R for p in r["penalties"])
        rows.append((Path(path).stem, len(R), c, sum(sum(r["goals"]) for r in R)))
    base = rows[0]
    rules = sorted({k for _, _, c, _ in rows for k in c}, key=lambda k: -base[2][k])
    print(f"{'':22s}" + "".join(f"{nm[:14]:>16s}" for nm, *_ in rows))
    print(f"{'games':22s}" + "".join(f"{n:16d}" for _, n, _, _ in rows))
    for k in rules + ["all"]:
        line = f"{k:22s}"
        for nm, n, c, _ in rows:
            v = sum(c.values()) if k == "all" else c[k]
            b = sum(base[2].values()) if k == "all" else base[2][k]
            ratio = (v / n) / (b / base[1]) if b else float("nan")
            se = ratio * math.sqrt(1 / max(v, 1) + 1 / max(b, 1)) if b else 0
            line += f"  {v / n:5.2f} {ratio:4.0%}±{se:3.0%}" if nm != base[0] else f"  {v / n:5.2f}         "
        print(line)
    print(f"{'goals a game':22s}" + "".join(f"{g / n:16.2f}" for _, n, _, g in rows))


def build(retail, out_dir):
    b = Path(retail).read_bytes()
    assert b[0x13E30:0x13E34] == bytes.fromhex("C0FC000D") and b[0x13CA8:0x13CAC] == bytes.fromhex("B07C0004")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, (mul, thr) in LEVELS.items():
        r = bytearray(b)
        r[0x13E32:0x13E34] = mul.to_bytes(2, "big")
        r[0x13CAA:0x13CAC] = thr.to_bytes(2, "big")
        r[0x300:0x306] = bytes.fromhex("4E714E714E71")      # the boot self-check (jsr $FFAC0) off: a changed ROM stops there
        s = sum(int.from_bytes(r[i:i + 2], "big") for i in range(0x200, len(r), 2)) & 0xFFFF
        r[0x18E:0x190] = s.to_bytes(2, "big")
        (out_dir / f"nhl94_ref_{name}.bin").write_bytes(r)
        print(name, mul, thr)


def main():
    if sys.argv[1] == "report":
        report(sys.argv[2:])
        return
    if sys.argv[1] == "build":
        build(sys.argv[2], sys.argv[3])
        return
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    lowload.gentle()
    for n in range(first, first + games):
        r = game(rom, n)
        with open(out, "a") as fo:
            fo.write(json.dumps(r) + "\n")
        print(n, len(r.get("penalties", [])), r.get("goals"), flush=True)


if __name__ == "__main__":
    main()
