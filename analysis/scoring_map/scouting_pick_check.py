"""Ron Barr's pick every game (2026-11-15, for NOSE4Web ebd693c: the hotter-team line's threshold lowered to 0), both
systems. Each run picks a matchup on Game Setup (RIGHT until the game's own HomeTeam / VisTeam word reads it, as
team_move_check does), waits a different number of frames on the title first (the hot / cold rolls are random), and
plays the matchup screen to the end of its text, read from video memory as scouting_text_check does. Then:
- the hotter-team line ("Lately ... has been playing (extremely) well.") in the typed text, and the team it names;
- the totals worked out again from RAM and the ROM. Genesis (CompareHotColdTotals / GetHotColdTotal /
  SortHotColdStarters): each starter of the team's first line set (the team data's LineSets) adds his hot / cold
  bytes 3-15 but 9 and 13 (tmHotCold, 16 a player), summed as a byte; the game's own TempWord1 / TempWord2 / awayhotter
  are read the frame the paragraph list is made. SNES (ScoutingReport .10 / .11): the game's own hotcoldsum (every
  player's rating less his base rating, both teams), hotterteam and hotextreme;
- which team should be named (Genesis: away total >= home total names the visitors; SNES: home >= visitors names
  the home team) and whether "extremely" should show (Genesis a gap of $BD or more, SNES 8 or more);
- frames from START to the text's end, the rows typed and any change the box-follower can't explain.
`--force=SPEC` sets the totals: a scratch copy of the ROM with the screen's own hot / cold re-roll skipped (Genesis
ScoutingReport's two Create_HotCold_Table calls, SNES StartGame_scout's), and the tables written into RAM before
START. Genesis SPEC = the gap wanted (away less home, e.g. 189, -189, 0); SNES SPEC = home:visitors table value
(-12 ... 12 for every byte of that team's half).

python scouting_pick_check.py ROM OUT RUNS [FIRST] [--teams=H:V,H:V,...] [--force=SPEC,SPEC,...]"""
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import lowload
import menu_shots as M
from scouting_text_check import Genesis, Snes, decode, follow
from team_move_check import pick, GEN_HOME, GEN_VIS, SNES_HOME, SNES_VIS

GEN_TEAM_TABLE = None
HEAD = bytes.fromhex("1b001d001a001d00")
G_STRUCT = (0xC6CE, 0xCA32)          # tmstruct, awtmstruct
G_HOTCOLD, G_TMDATA = 0x1A2, 0x1E
G_TW1, G_TW2, G_AWAYHOT = 0xBF12, 0xBF14, 0xBF50
S_HOTTER, S_EXTREME, S_SUM, S_TABLE = 0x1E41, 0x1E43, 0x1E45, 0x1A12
# Genesis "Lately X has been playing (extremely) well.", SNES "X has been playing (extremely) well recently."
LATELY = re.compile(r"^(?:Lately )?(.+?) ha(?:s|ve) been playing (extremely )?well(?: recently)?\.$")


def signed8(v):
    return v - 256 if v & 0x80 else v


def scratch(rom, out):
    """The ROM with the matchup screen's hot / cold re-roll skipped."""
    data = bytearray(Path(rom).read_bytes())
    if rom.lower().endswith(".bin"):
        # ScoutingReport's pair (the last; StartGame has the same pair first)
        m = list(re.finditer(rb"\x20\x7c\xff\xff\xc6\xce\x4e\xb9(....)\x20\x7c\xff\xff\xca\x32\x4e\xb9(....)", data, re.S))[-1]
        for at in (m.start() + 6, m.start() + 16):
            data[at:at + 6] = b"\x4e\x71" * 3
    else:
        # StartGame: jsl PlayoffScreen, jsl Create_HotCold_Table (StartGame_scout), jsl ScoutingReport, then
        # StartGame_go's lda #$FFFF / sta FrameByNumber (the first such run in all three builds, $F8330)
        m = next(re.finditer(rb"\x22...\x22...\x22...\xa9\xff\xff\x8d", data, re.S))
        data[m.start() + 4:m.start() + 8] = b"\xea" * 4
    p = out / ("scratch_" + Path(rom).name)
    p.write_bytes(bytes(data))
    return str(p)


class Mem:
    """Byte writes to SNES work RAM, through BW-RAM on SA-1 builds (faceoff_fix_test.Snes.MOVED)."""

    def __init__(self, e, rom):
        self.e, self.bw = e, None
        data = Path(rom).read_bytes()
        if not rom.lower().endswith(".bin") and len(data) > 0x7FD6 and data[0x7FD5] == 0x23:
            import ctypes as C
            from faceoff_fix_test import Snes as FS
            self.bw = (C.c_ubyte * e.lib.retro_get_memory_size(0)).from_address(e.lib.retro_get_memory_data(0))
            self.moved = FS.MOVED

    def setb(self, a, v):
        if self.bw is not None:
            for lo, hi, to in self.moved:
                if lo <= a < hi:
                    self.bw[to + a - lo] = v & 0xFF
                    return
        self.e.setb(a, v)


def gen_starters(rom, e, side):
    ptr = e.l(0xFF0000 + G_STRUCT[side] + G_TMDATA) & 0xFFFFFF
    off = struct.unpack_from(">H", rom, ptr + 6)[0]
    return [b - 1 for b in rom[ptr + off:ptr + off + 6]]


def gen_total(rom, e, side):
    tot = 0
    for p in gen_starters(rom, e, side):
        s = 0
        for i in range(3, 16):
            if i in (9, 13):
                continue
            s = (s + e.b(0xFF0000 + G_STRUCT[side] + G_HOTCOLD + 16 * p + i)) & 0xFF
        tot += signed8(s)
    return tot


def gen_force(rom, e, gap):
    """Home table all 0; the visitors' starters given `gap` between them (negative: the home starters)."""
    for side in (0, 1):
        for i in range(26 * 16):
            e.setb(0xFF0000 + G_STRUCT[side] + G_HOTCOLD + i, 0)
    side = 1 if gap >= 0 else 0
    left = abs(gap)
    for p in gen_starters(rom, e, side):
        give = min(left, 88)                     # 11 bytes of 8 at most; the sum stays a positive byte
        left -= give
        i = 3
        while give:
            if i not in (9, 13):
                b = min(give, 8)
                e.setb(0xFF0000 + G_STRUCT[side] + G_HOTCOLD + 16 * p + i, b)
                give -= b
            i += 1
    assert left == 0, gap


def snes_force(mem, home, vis):
    for i in range(52 * 12):
        mem.setb(S_TABLE + i, (home if i < 26 * 12 else vis) & 0xFF)


def one(rom, out, k, home, vis, force):
    data = Path(rom).read_bytes()
    gen = rom.lower().endswith(".bin")
    sysm = Genesis(rom, data) if gen else Snes(rom, data)
    e = M.emulator(rom)
    if gen:
        e.run(900)
        M.play(e, "START w120 START w120 DOWN*2", out)
        ok = [pick(e, GEN_HOME, home, out)]
        M.play(e, "DOWN w20", out)
        ok.append(pick(e, GEN_VIS, vis, out))
        M.play(e, "UP*3 w60", out)
        e.run(37 * k)                             # the hot / cold rolls are random: a different wait each run
        teams = [e.w(GEN_HOME), e.w(GEN_VIS)]
    else:
        e.run(1500)
        M.play(e, "START w240 START w240 DOWN", out)
        ok = []
        for addr, team in ((SNES_HOME, home), (SNES_VIS, vis)):
            ok.append(pick(e, addr, team, out))
            M.play(e, "DOWN w20", out)
        e.run(60 + 37 * k)
        for _ in range(5):                        # START can be lost on Game Setup: press until it has gone
            M.play(e, "START w240", out)
            if not any("Play Mode" in r for r in decode(sysm, *sysm.read(e)[:2])):
                break
        teams = [e.w(SNES_HOME), e.w(SNES_VIS)]
    if force is not None:
        if gen:
            gen_force(data, e, force)
        else:
            snes_force(Mem(e, rom), *force)
    e.run(4, hold=["START"])
    game = {}
    f = 4
    if gen:
        for _ in range(400):                      # the frame the paragraph list is made: the game's own totals
            e.run(1)
            f += 1
            if bytes(e.ram[:0x10000]).find(HEAD) >= 0:
                game = {"home": e.sw(G_TW1), "away": e.sw(G_TW2), "awayhotter": e.w(G_AWAYHOT)}
                break
    kept, prev, still, odd, done = [], None, 0, [], f
    while f < 9000:
        e.run(6)
        f += 6
        grid, fb, vr = sysm.read(e)
        cur = decode(sysm, grid, fb)
        if prev is None:
            prev = cur
            continue
        if cur == prev:
            still += 6
            if still > 700 and any(kept + cur):
                break
            continue
        still, done = 0, f
        s = follow(prev, cur)
        if s is None:
            odd.append(f)
            break
        kept += prev[:s]
        prev = cur
    kept += prev
    while kept and not kept[-1]:
        kept.pop()
    e.screenshot(out / f"box_{Path(rom).stem}_{k:03d}.png")
    paras = [re.sub(r"\s+", " ", p).strip() for p in "\n".join(kept).split("\n\n") if p.strip()]
    hits = [LATELY.match(p) for p in paras]
    hits = [h for h in hits if h]
    m = hits[0] if hits else None
    res = {"run": k, "teams": teams, "picked": ok, "force": force, "text done": done, "rows": len(kept), "odd": odd,
           "line": m.group(0) if m else None, "named": m.group(1) if m else None, "extremely": bool(m and m.group(2)),
           "lately count": len(hits), "paragraphs": len(paras)}
    if gen:
        mine = [gen_total(data, e, 0), gen_total(data, e, 1)]
        res.update(game=game, mine=mine, gap=mine[1] - mine[0])
        res["expect"] = "visitors" if mine[1] >= mine[0] else "home"
        res["expect extremely"] = abs(mine[1] - mine[0]) >= 0xBD
    else:
        sums = [e.sw(S_SUM), e.sw(S_SUM + 2)]
        res.update(game={"hotterteam": e.w(S_HOTTER), "hotextreme": e.w(S_EXTREME), "sums": sums}, gap=sums[0] - sums[1])
        res["expect"] = "home" if sums[0] >= sums[1] else "visitors"
        res["expect extremely"] = abs(sums[0] - sums[1]) >= 8
    res["rows text"] = kept
    return res


def names(rom):
    """(city, nickname) of each team: the first and third of the team's length-prefixed name strings."""
    from systems import genesis, snes
    if not rom.lower().endswith(".bin"):
        return [(x["name"], x["nickname"]) for x in snes.read_teams(Path(rom))]
    data = Path(rom).read_bytes()
    res = []
    for k in range(genesis.team_count(data)):
        team = struct.unpack_from(">I", data, genesis.TEAM_TABLE + 4 * k)[0]
        at = team + struct.unpack_from(">3H", data, team)[2]
        strs = []
        for _ in range(3):
            n = struct.unpack_from(">H", data, at)[0]
            strs.append(data[at + 2:at + n].decode("latin-1").rstrip(chr(0)))
            at += n
        res.append((strs[0], strs[2]))
    return res


def side_named(named, home, vis):
    """Which team the line names: by city, and by nickname where the two cities read alike (the New York teams)."""
    def fits(t):
        city, nick = t
        return named.startswith(city) or named.startswith("NY") and city.startswith(("New York", "NY"))
    h, v = fits(home), fits(vis)
    if h and v and home != vis:
        h, v = home[1] in named, vis[1] in named
    return "home" if h and not v else "visitors" if v and not h else "same team" if h and v else "?"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    rom, out, runs = args[0], Path(args[1]), int(args[2])
    first = int(args[3]) if len(args) > 3 else 0
    out.mkdir(parents=True, exist_ok=True)
    pairs = [tuple(map(int, p.split(":"))) for p in opts.get("teams", "0:1").split(",")]
    forces = [None]
    if "force" in opts:
        if rom.lower().endswith(".bin"):
            forces = [int(x) for x in opts["force"].split(",")]
        else:
            forces = [tuple(map(int, x.split(":"))) for x in opts["force"].split(",")]
        rom = scratch(rom, out)
    lowload.gentle()
    city = names(rom)
    log = open(out / f"{Path(rom).stem}.jsonl", "a")
    for k in range(first, first + runs):
        home, vis = pairs[k % len(pairs)]
        force = forces[k % len(forces)]
        r = one(rom, out, k, home, vis, force)
        ht, vt = city[r["teams"][0]], city[r["teams"][1]]
        hn, vn = " ".join(ht), " ".join(vt)
        r["home name"], r["visitors name"] = hn, vn
        side = side_named(r["named"] or "", ht, vt)
        if side == "same team":
            side = r["expect"]
        r["named side"] = side
        r["ok"] = bool(r["line"]) and r["lately count"] == 1 and side == r["expect"] and \
            r["extremely"] == r["expect extremely"] and not r["odd"]
        log.write(json.dumps(r) + "\n")
        log.flush()
        print(k, f"{vn} at {hn}", "gap", r["gap"], r.get("game"), "|", r["line"], "| named", side, "expect",
              r["expect"], "extreme" if r["expect extremely"] else "", "| done", r["text done"], "rows", r["rows"],
              "OK" if r["ok"] else "CHECK", flush=True)


if __name__ == "__main__":
    main()
