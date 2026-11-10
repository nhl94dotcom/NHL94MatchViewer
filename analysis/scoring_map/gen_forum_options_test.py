"""NOSE4Web's five Genesis forum options (NOSE4Web 92a30a9, 2026-11-09), played in the game: each built into a scratch
copy of retail nhl94.bin as NOSE4Web describes (the boot's ROM sum at $300 off, as its builds), against retail.

- injuries: every fall of a puck carrier made an injury chance that always succeeds (FallDown's fall-back, facing and
  random tests at $1440E / $1441A / $14436 NOP'd, as gen_injury_check), then the option: "never" ($14440 bne.w .22 ->
  bra.w), "period" ($14508 bne.w .not0 -> NOPs, with getFgtbyte at $FEC98 returning 3: a checker with Fighting 12+),
  "game" ($14508 and $14520 -> bra.w), and the base (retail's own type rules). Pad 1 on the home team, no presses;
  every injury (a player in SPAinjuryfall / SPAinjury1): the game-injury bit (sflags7 bit 5) and the injured
  player's tmpdst (team struct +$66: $FFFD the period, $FFFC the game).
- penaltynoinjury, hotcold, icing, bcheck, goaliedelay: see their functions.

python gen_forum_options_test.py RETAIL OUT part [part ...]"""
import json
import sys
from pathlib import Path

import lowload
import menu_shots as M
from gen_score_logo_check import Watch, CLOCK, MENUITEM

REC, SFLAGS7 = 0xB04A, 0xC2FC
FALL, INJ1 = 0x145C, 0x1AF4
TEAMS = (0xC6CE, 0xCA32)


def build(retail, out, name, patches):
    data = bytearray(Path(retail).read_bytes())
    for at, old, new in patches:
        old, new = bytes.fromhex(old), bytes.fromhex(new)
        assert data[at:at + len(old)] == old, f"{name}: ${at:X} is {data[at:at + len(old)].hex()}, not {old.hex()}"
        data[at:at + len(new)] = new
    data[0x300:0x306] = bytes.fromhex("4e714e714e71")
    p = out / f"{name}.bin"
    p.write_bytes(data)
    return str(p)


FORCE_INJURY = [(at, "", "4e714e71") for at in (0x1440E, 0x1441A, 0x14436)]


def force(patches):
    return [(at, "", new) for at, _, new in FORCE_INJURY] + patches


def to_play(rom, out, script="w900 START w120 START w120 DOWN*7 RIGHT w60"):
    g = Watch(rom, out)
    e = g.e
    M.play(e, script, out)
    for _ in range(40):
        if e.b(0xFFF7) == 0:
            break
        e.run(4, hold=["START"])
        e.run(200)
    g.wait_play()
    return g, e


def part_injuries(retail, out):
    runs = {
        "base": [],
        "never": [(0x14440, "66000052", "60000052")],
        "period": [(0x14508, "66000012", "4e714e71"), (0xFEC98, "4240102a0074e4484e75", "70034e754e714e714e71")],
        "game": [(0x14508, "66000012", "60000012"), (0x14520, "67000018", "60000018")],
    }
    res = {}
    for name, patches in runs.items():
        rom = build(retail, out, f"inj_{name}", force(patches))
        g, e = to_play(rom, out / name)
        injuries, seen, frames = [], set(), 0
        while frames < 60 * 60 * 12 and len(injuries) < 4:
            e.run(5)
            frames += 5
            for k in range(12):
                anim = e.w(0xFF0000 | REC + k * 0x80 + 0x58)
                if anim in (FALL, INJ1) and (k, "inj") not in seen:
                    seen.add((k, "inj"))
                    team = TEAMS[0 if k < 6 else 1]
                    pn = e.b(0xFF0000 | REC + k * 0x80 + 0x66)
                    e.run(2)
                    injuries.append(dict(frame=frames, record=k, game_bit=bool(g.b(SFLAGS7) & 0x20),
                                         tmpdst=hex(e.w(0xFF0000 | team + 0x66 + 2 * pn))))
            if frames % 600 == 0:
                lowload.breathe()
                if not g.in_play():
                    e.run(4, hold=["START"])
        res[name] = dict(injuries=injuries, frames=frames)
        print(name, json.dumps(res[name]), flush=True)
    return res


def part_penaltynoinjury(retail, out):
    """The injury left out but its penalty kept: setInjuryType's call ($14450) and the injury countdown's
    `move.w #4,(InjCntDown)` ($1446A) NOP'd, the injury forced as in part_injuries. On retail and the option: after
    each forced injury, the player's animation and tmpdst, the team's penalty count (team struct +6), InjCntDown
    ($C3EC) and the screen, for 60 s real; does play go on?"""
    runs = {"base": [], "option": [(0x14450, "6100005a", "4e714e71"), (0x1446A, "31fc0004c3ec", "4e714e714e71")]}
    res = {}
    for name, patches in runs.items():
        rom = build(retail, out, f"pni_{name}", force(patches))
        g, e = to_play(rom, out / f"pni_{name}")
        w = lambda a: e.w(0xFF0000 | a)
        got, frames = [], 0
        while frames < 60 * 60 * 10 and len(got) < 2:
            e.run(5)
            frames += 5
            hit = next((k for k in range(12) if w(REC + k * 0x80 + 0x58) in (FALL, INJ1)), None)
            if hit is None:
                if frames % 600 == 0 and not g.in_play():
                    e.run(4, hold=["START"])
                continue
            team = TEAMS[0 if hit < 6 else 1]
            pn = e.b(0xFF0000 | REC + hit * 0x80 + 0x66)
            pens0 = [w(t + 6) for t in TEAMS]
            trace, last = [], None
            for t in range(0, 60 * 60, 10):
                st = (hex(w(REC + hit * 0x80 + 0x58)), hex(w(team + 0x66 + 2 * pn)), w(0xC3EC), e.b(0xFFF7), w(CLOCK))
                if st[:4] != last:
                    trace.append((t,) + st)
                    last = st[:4]
                e.run(10)
                if t % 600 == 0 and e.b(0xFFF7) == 0 and not g.in_play():
                    e.run(4, hold=["START"])
            got.append(dict(record=hit, penalties_before=pens0, penalties_after=[w(t + 6) for t in TEAMS],
                            clock_after=w(CLOCK), in_play=g.in_play(), trace=trace[:14]))
            e.screenshot(out / f"pni_{name}_{len(got)}.png")
            frames += 3600
        res[name] = got
        print(name, json.dumps(got), flush=True)
    return res


def part_hotcold(retail, out):
    """$F70AD (Create_HotCold_Table's range n: randomd0s gives -n .. n-1) at 9 (retail), 4, 3, 2 and 0. randomd0s draws the same number of values
    whatever the range, so the games are the same but for the table; 0 makes it all zeros (no hot / cold at all).
    At the opening faceoff: every record's working ratings (+$67-$75) against range 0's; then Edit Lines from the pause
    menu (item 3), C on the first slot, and the player list's 8 rating pages (RIGHT), each against range 0's."""
    from PIL import Image, ImageChops
    res, ratings, shots = {}, {}, {}
    for n in (9, 4, 3, 2, 0):
        rom = build(retail, out, f"hc_{n}", [(0xF70AD, "09", f"{n:02x}")])
        g, e = to_play(rom, out / f"hc_{n}")
        e.run(120)
        ratings[n] = [[e.b(0xFF0000 | REC + k * 0x80 + o) for o in range(0x67, 0x76)] for k in range(12)]
        g.press("START", 90)
        for _ in range(30):
            if e.w(0xFF0000 | MENUITEM) == 3:
                break
            g.press("DOWN")
        g.press("C", 240)                           # Edit Lines
        g.press("C", 240)                           # the player list for the first slot: one rating column a page
        shots[n] = []
        for page in range(8):
            shots[n].append(out / f"hc_{n}_list{page}.png")
            e.screenshot(shots[n][-1])
            g.press("RIGHT", 60)
    for n in (9, 4, 3, 2):
        diff = sum(1 for a, b in zip(sum(ratings[n], []), sum(ratings[0], [])) if a != b)
        pages = [i for i, (a, b) in enumerate(zip(shots[n], shots[0]))
                 if ImageChops.difference(Image.open(a).convert("RGB"), Image.open(b).convert("RGB")).getbbox()]
        res[n] = dict(working_ratings_that_differ_from_range_0=diff, list_pages_that_differ=pages)
        print(n, res[n], flush=True)
    return res


def part_icing(retail, out):
    """No icing: $1023E (a2touchpuck's `bset #ifok,(iflags)`) as `bra.s` over it, NOSE4Web's 6004 (to the rts) and the
    forum's 6002 (onto the operand $BF80, which runs as `eor.l d7,d0`), against retail; on copies of the scoring-map
    test ROM and its state (home shoots at the top net). The home skater (record 2) with the puck at (-80, -40), his
    own half and wide of the net, everyone else parked but the away skater 6, put on the puck once it is loose past
    the top goal line (y 264); C held 3 frames with the d-pad up, then 300 frames: iflags ($BF80: bit 0 crossed, 2 icing), the clock
    stopped (gmode $C2EA bit 0), who touched the puck, and how far the away goalie (record 11) came out."""
    import harness as H
    from paths import ROM
    res = {}
    for name, new in (("retail", None), ("6004", "6004"), ("6002", "6002")):
        rom = ROM if new is None else build(ROM, out, f"icing_{name}", [(0x1023E, "08f8", new)])
        h = H.Harness(rom=rom)
        e = h.e
        rows = []
        for x, y, aim in ((-80, -40, ["UP"]), (80, -40, ["UP"]), (-90, -60, ["UP"]), (90, -20, ["UP"])):
            e.unserialize(h.base)
            def place():
                h.park()
                e.setw(H.rec(6), x)
                e.setw(H.rec(6) + 0x14, 280)
                for off in (0x28, 0x2A):
                    e.setw(H.rec(6) + off, 0)
            for _ in range(90):
                e.setw(H.rec(2), x)
                e.setw(H.rec(2) + 0x14, y)
                for off in (0x28, 0x2A, 0x2C):
                    e.setw(H.rec(2) + off, 0)
                place()
                e.setw(H.PUCKC, 2)
                e.run(1)
            touched, flags, stopped, out_most = [], set(), None, 0
            for f in range(300):
                h.park(keep_shooter=False)
                py = e.sw(H.PUCK + 0x14)
                if py > 264 and e.w(H.PUCKC) >= 0x100 and not any(t == 6 for t in touched):
                    e.setw(H.rec(6), e.sw(H.PUCK))  # past the goal line and loose: the away skater onto it
                    e.setw(H.rec(6) + 0x14, py)
                    for off in (0x28, 0x2A):
                        e.setw(H.rec(6) + off, 0)
                elif not any(t == 6 for t in touched):
                    e.setw(H.rec(6), x)
                    e.setw(H.rec(6) + 0x14, 290)
                e.run(1, hold=(["C"] if f < 3 else []) + aim)
                c = e.w(H.PUCKC)
                if c < 0x100 and (not touched or touched[-1] != c):
                    touched.append(c)
                flags.add(e.b(0xBF80))
                out_most = max(out_most, 268 - e.sw(H.rec(11) + 0x14))
                if stopped is None and e.b(0xC2EA) & 1:
                    stopped = f
            rows.append(dict(start=(x, y), touched=touched, iflags_seen=sorted(hex(v) for v in flags),
                             clock_stopped_at=stopped, goalie_out_most=out_most, puck=(e.sw(H.PUCK), e.sw(H.PUCK + 0x14))))
        res[name] = rows
        print(name, json.dumps(rows), flush=True)
    return res


def part_bcheck(retail, out):
    """B-checks with penalties off: $13FDC (Bcheck's `bne.w .checkdir` when penalties are on) -> `bra.w`, against retail,
    on copies of the scoring-map test ROM and its state. The home skater (record 2, pad 1) 30 or 50 units behind the
    away carrier (record 6), both facing up, everyone else parked; he skates up (UP held) and pokes (B for 3 frames at
    frame 5 or 20): the poke is the B sweep (animation $0B24) that reaches Bcheck when they touch. Each setting x 24
    random seeds ($D066), penalties On (OptPen $D056 = 2) and Off (0): pokes, and trips (the carrier knocked down:
    $0DD8 / $0D26)."""
    import harness as H
    from paths import ROM
    DOWN = {0xDD8, 0xD26}
    res = {}
    for name, rom in (("retail", ROM), ("option", build(ROM, out, "bcheck_option", [(0x13FDC, "66", "60")]))):
        h = H.Harness(rom=rom)
        e = h.e

        def park():
            for k in range(12):
                if k not in (2, 6, H.GOALIE):
                    e.setw(H.rec(k), -100 + 18 * k)
                    e.setw(H.rec(k) + 0x14, h.park_y)
                    for off in (0x28, 0x2A, 0x2C):
                        e.setw(H.rec(k) + off, 0)

        def trial(seed, optpen, dy, bat):
            e.unserialize(h.base)
            e.setw(0xD056, optpen)
            for _ in range(30):
                park()
                for k, (x, y) in ((2, (0, 0)), (6, (0, dy))):
                    e.setw(H.rec(k), x)
                    e.setw(H.rec(k) + 0x14, y)
                    for off in (0x28, 0x2A, 0x2C):
                        e.setw(H.rec(k) + off, 0)
                e.setb(H.rec(2) + 0x55, 0)
                e.setb(H.rec(6) + 0x55, 0)
                e.setw(H.PUCKC, 6)
                e.run(1)
            e.setl(0xD066, seed)
            poke = down = False
            for f in range(70):
                park()
                e.run(1, hold=["UP"] + (["B"] if bat <= f < bat + 3 else []))
                poke |= e.w(H.rec(2) + 0x58) == 0xB24
                down |= e.w(H.rec(6) + 0x58) in DOWN
            return poke, down

        rows = {}
        for optpen in (2, 0):
            tot = [0, 0, 0]
            for dy, bat in ((30, 5), (50, 5), (30, 20)):
                for sd in range(24):
                    p_, d_ = trial(0x1000 + sd * 7919 + dy, optpen, dy, bat)
                    tot[0] += 1
                    tot[1] += p_
                    tot[2] += d_
                lowload.breathe()
            rows["penalties on" if optpen else "penalties off"] = dict(tries=tot[0], pokes=tot[1], trips=tot[2])
        res[name] = rows
        print(name, json.dumps(rows), flush=True)
    return res


def part_goaliedelay(retail, out):
    """The goalie control delay (the B hold timers' start, $11) at 12 in all eight places ($AD04 / $AD0A words $0C0C,
    $B12F $B139 $B36D $B377 $B39B $B3C3 bytes $0C), against retail, on copies of the scoring-map test ROM and its
    state. Pad 1 controls the home skater (record 2) without the puck, the away carrier far up the ice; B held from
    frame 0 (after settling 30 frames, 8 random seeds and 4 start frames): the frame pad 1's control (record +$62 bit
    3) reaches the home goalie (record 5), and how many game loops that is (the timer counts one a pass of doinput).
    Pads 3 and 4 (2-on-2, EA's 4-Way Play): gen_pad34_goalie.py."""
    import harness as H
    from paths import ROM
    places = [(0xAD04, "1111", "0c0c"), (0xAD0A, "1111", "0c0c")] + [(a, "11", "0c") for a in
                                                                  (0xB12F, 0xB139, 0xB36D, 0xB377, 0xB39B, 0xB3C3)]
    res = {}
    for name, rom in (("retail", ROM), ("12", build(ROM, out, "goaliedelay_12", places))):
        h = H.Harness(rom=rom)
        e = h.e
        times = []
        for sd in range(8):
            for start in range(4):
                e.unserialize(h.base)
                for _ in range(30 + start):
                    h.park()
                    e.setw(H.rec(2), 0)
                    e.setw(H.rec(2) + 0x14, -150)
                    e.setw(H.rec(6), 0)
                    e.setw(H.rec(6) + 0x14, 150)
                    e.setw(H.PUCKC, 6)
                    e.run(1)
                e.setl(0xD066, 0x2000 + sd * 101)
                got = None
                for f in range(120):
                    e.run(1, hold=["B"])
                    if e.b(H.rec(5) + 0x62) & 8:
                        got = f
                        break
                times.append(got)
        ok = [t for t in times if t is not None]
        res[name] = dict(frames_to_goalie=sorted(set(ok)), mean=round(sum(ok) / len(ok), 1) if ok else None,
                         never=len(times) - len(ok))
        print(name, json.dumps(res[name]), flush=True)
    return res


def main():
    retail, out, parts = sys.argv[1], Path(sys.argv[2]), sys.argv[3:]
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    res = {}
    for part in parts:
        res[part] = globals()[f"part_{part}"](retail, out)
    (out / "results.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
