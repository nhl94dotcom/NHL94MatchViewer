"""NOSE4Web's Genesis skate marks, played (2026-11-14: nhl94_skate_marks.bin, CDL_Season_12_skate_marks.bin).

A computer game (gen_ot_check's boot and into_play; 5-minute periods; both pads taken off every second; START at a
waiting menu; other games' intermission highlights told by team ids): three periods, the scores set level with 3 s
left, overtime. Logged in another game's highlight: the count and record should not change (2026-11-14 second build:
nothing marked or cleared while gmode's gmhl bit is set); at each period's faceoff (the clock's first tick) the count
and record should be empty. Logged:
- the mark count (the build's word at $FFFD4C) and gsp every 2 s (real), and at each change of period;
- the rink plane in video memory (plane B, $C000, 64 x 32 cells; the state's VRAM, gen_score_logo_check's VRAM_AT)
  against the marks record ($FFF800, 2 bits a cell, 48 x 113 cells, the bit order found from the screen) and the ROM
  map (Rinktilelist's map at $599A4): each plane row matched to its map row; marked plain-ice cells ($8F in the ROM
  map) should show $8E or $F4 / $18F4 (either flip), unmarked cells the ROM's word, and no mark tile on any other
  cell. Every 30 s (real) and after the pause menu's Player Stats (pause, 5 down, C, back with START twice);
- lag: the game's frame counter ($B03E) against frames run: each frame it moved by other than 1;
- screenshots every 20 s (real);
- --replay: at 3:20 left in period 1, the pause menu's Instant Replay instead (instant_replay), then stop.
Run on the original too (--lag-only) for its lag.

python gen_skate_marks_check.py ROM OUT [--lag-only | --replay] [--delay=FRAMES]"""
import struct
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

VRAM_AT, PLANE_B = 74789, 0xC000
COUNT, MARKS, FRAMECTR, GSP, CLOCK, SCREEN = 0xFD4C, 0xF800, 0xB03E, 0xC466, 0xC468, 0xFFF7
CONT1, CONT2, BASE, SZ = 0xC328, 0xC32A, 0xB04A, 0x80
MARK_TILES = {0x8E, 0xF4}
W, H = 48, 113


def rom_map(rom, a=0x5605A):
    """Rinktilelist's map ($5605A); the reverse angle's RevRinkTilelist is at $B5180 (updatescroll)."""
    p, m = struct.unpack(">II", rom[a:a + 8])
    w, h = struct.unpack(">HH", rom[a + m:a + m + 4])
    return list(struct.unpack(f">{w * h}H", rom[a + m + 4:a + m + 4 + 2 * w * h]))


def plane(e):
    st = bytes(e.serialize())
    v = st[VRAM_AT:VRAM_AT + 0x10000]
    return [[v[PLANE_B + 2 * (r * 64 + c)] | v[PLANE_B + 2 * (r * 64 + c) + 1] << 8 for c in range(W)] for r in range(32)]


def marks(e, order):
    """{(row, col)} marked, by one of four bit orders (byte from the cell index / 4, two bits each, low or high
    first; the record's bytes as the 68000 sees them)."""
    out = set()
    for idx in range(W * H):
        b = e.b(0xFF0000 | (MARKS + idx // 4))
        sh = (idx % 4) * 2 if order == 0 else 6 - (idx % 4) * 2
        if (b >> sh) & 3:
            out.add(divmod(idx, W))
    return out


def check(e, rmap, order=None, none_expected=False):
    """none_expected: the reverse angle (RevRinkTilelist's rows, no marks by design): every mark tile not in the
    map is stray."""
    pl = plane(e)
    rows = {}
    for pr, words in enumerate(pl):            # each plane row: the map row it holds (most words the same)
        best = max(range(H), key=lambda r: sum(1 for c in range(W) if (words[c] & 0x7FF) == (rmap[r * W + c] & 0x7FF)))
        same = sum(1 for c in range(W) if (words[c] & 0x7FF) == (rmap[best * W + c] & 0x7FF))
        if same >= W * 0.7:
            rows[pr] = best
    orders = [order] if order is not None else [0, 1]
    best = None
    for o in orders:
        mk = set() if none_expected else marks(e, o)
        res = {"shown": 0, "missing": 0, "stray": 0, "stray_on_lines": 0, "rows": len(rows)}
        for pr, r in rows.items():
            for c in range(W):
                v, rv = pl[pr][c], rmap[r * W + c]
                is_mark = (v & 0x7FF) in MARK_TILES and (v & 0x7FF) != (rv & 0x7FF)
                if (r, c) in mk and (rv & 0x7FF) == 0x8F:
                    res["shown" if is_mark else "missing"] += 1
                elif is_mark:
                    res["stray_on_lines" if (rv & 0x7FF) != 0x8F else "stray"] += 1
        res["order"] = o
        if best is None or res["shown"] - res["missing"] > best["shown"] - best["missing"]:
            best = res
    return best


def record(e):
    return bytes(e.b(0xFF0000 | (MARKS + i)) for i in range(W * H // 4)), e.w(COUNT)


def instant_replay(e, rmap, order, out, rev):
    """The pause menu's Instant Replay ($CF20 the menu item, 1): back (LEFT) and forward (RIGHT), then the replay
    menu's C (reverse angle), back and forward again; the marks record and count compared before and after each part,
    the screen checked after return, screenshots throughout."""
    rec0 = record(e)
    print(f"before the replay: count {rec0[1]}, check {check(e, rmap, order)}", flush=True)
    G.press(e, "START")
    e.run(60)
    for _ in range(30):
        if e.w(0xCF20) == 1:
            break
        G.press(e, "DOWN")
    G.press(e, "C")
    e.run(200)
    n = 0
    for part, moves in (("normal", ("LEFT", "RIGHT")), ("reverse", ("LEFT", "RIGHT"))):
        if part == "reverse":
            G.press(e, "START")
            e.run(120)
            e.screenshot(out / "replay_menu.png")
            G.press(e, "C")
            e.run(120)
        for mv in moves:
            for k in range(6):
                e.run(50, hold=[mv])
                e.screenshot(out / f"replay_{part}_{n:02d}_{mv}.png")
                n += 1
            r = record(e)
            print(f"  {part} {mv}: record {'unchanged' if r[0] == rec0[0] else 'CHANGED'}, count {r[1]}, "
                  + f"screen {check(e, rmap if part == 'normal' else rev, order, none_expected=part == 'reverse')}", flush=True)
    for k in range(6):                                # START out of the replay, then out of the pause menu
        G.press(e, "START")
        e.run(200)
        e.screenshot(out / f"exit_{k}.png")
        if e.b(SCREEN) == 0:
            break
    r = record(e)
    r = record(e)
    e.screenshot(out / "after_replay.png")
    print(f"after the replay (screen {e.b(SCREEN)}, clock {e.w(CLOCK)}): record {'unchanged' if r[0] == rec0[0] else 'CHANGED'}, "
          f"count {r[1]}, check {check(e, rmap, order)}", flush=True)


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    lag_only = "--lag-only" in sys.argv
    replay = "--replay" in sys.argv
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    rmap = rom_map(Path(rom).read_bytes())
    e = Emu(rom)
    G.to_setup(e, out)
    delay = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--delay=")), 0))
    e.run(delay)                                # another game (the highlights drawn differ)
    e.setw(0xD050, 0)                           # 5-minute periods
    print("period length setting", e.w(0xD050), flush=True)
    if not G.into_play(e):
        print("never reached play")
        return
    G.OURS.append(tuple(e.b(a) for a in G.TEAMS))    # our teams: an intermission highlight of another game has its own
    order, last_gsp, last_ctr, lag, frames, shots = None, e.w(GSP), e.w(FRAMECTR), 0, 0, 0
    stats_done = False
    lag_at, drops, stopped = [], [], 0
    still, last_clk = 0, None
    in_hl, hl_rec, hl_count, fresh_pending, tied, started = False, None, None, False, False, 0
    for f in range(60 * 60 * 30):
        if f % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            if f % 3600 == 0:
                lowload.breathe()
        clk = e.w(CLOCK)
        if clk == last_clk:
            stopped += 1
        else:
            if stopped >= 60 and e.b(SCREEN) == 0:
                drops.append(f)                     # the clock starts after a stop: a puck drop
            stopped = 0
        still = still + 1 if clk == last_clk else 0
        last_clk = clk
        e.run(1, hold=["START"] if still >= 300 and f % 150 < 4 and e.b(SCREEN) != 0 else [])   # a menu waiting
        ctr = e.w(FRAMECTR)
        if e.b(SCREEN) == 0:
            frames += 1
            if (ctr - last_ctr) & 0xFFFF != 1:
                lag += 1
                lag_at.append((f, e.w(CLOCK), (ctr - last_ctr) & 0xFFFF))
        last_ctr = ctr
        if not G.ours(e):                            # another game's highlight: the marks should stand still
            if not lag_only:
                c = e.w(COUNT)
                if not in_hl:
                    hl_rec, in_hl = record(e)[0], True
                    print(f"f{f}: highlight of another game starts: count {c}, stored gsp {e.w(0xFD4E)}, gsp {e.w(GSP)}",
                          flush=True)
                elif c != hl_count:
                    print(f"f{f}:   in the highlight the count changed to {c}", flush=True)
                hl_count = c
            continue
        if in_hl:
            print(f"f{f}: highlight over: count {e.w(COUNT)}, record "
                  f"{'unchanged' if record(e)[0] == hl_rec else 'CHANGED'}, stored gsp {e.w(0xFD4E)}", flush=True)
            in_hl = False
        g = e.w(GSP)
        if g != last_gsp:
            print(f"f{f}: period {last_gsp + 1} -> {g + 1}: count before {count_before}, now {e.w(COUNT) if not lag_only else '-'}",
                  flush=True)
            last_gsp = g
            if g >= 4:
                break
            gsp_changed_at = f
            fresh_pending = True
        if fresh_pending and e.b(SCREEN) == 0 and clk is not None and clk >= 295 and e.w(CLOCK) == clk - 1                 and not lag_only:
            print(f"f{f}: period {g + 1} faceoff (the clock starts): count {e.w(COUNT)}, record "
                  f"{'empty' if not any(record(e)[0]) else 'NOT EMPTY'}", flush=True)
            fresh_pending = False
            started = g
        if g == 2 and started == 2 and not tied and e.w(CLOCK) <= 3 and e.b(SCREEN) == 0:
            e.setw(0xC6DA, e.w(0xCA3E))                 # a tie at the end of period 3: overtime
            tied = True
            print(f"f{f}: scores set level ({e.w(0xCA3E)}-{e.w(0xC6DA)}) for overtime", flush=True)
        if g == 3 and f - gsp_changed_at >= 6000:
            break                                        # enough overtime
        if g >= 1 and "gsp_changed_at" in locals() and f - gsp_changed_at in (1200, 2400) and not lag_only:
            print(f"f{f}: {f - gsp_changed_at} frames into period {g + 1}: count {e.w(COUNT)}, clock {e.w(CLOCK)}", flush=True)
        count_before = e.w(COUNT) if not lag_only else 0
        if lag_only:
            continue
        if f % 120 == 0 and e.b(SCREEN) == 0:
            print(f"f{f}: period {g + 1} clock {e.w(CLOCK)} marks {e.w(COUNT)}", flush=True)
        if f % 1800 == 900 and e.b(SCREEN) == 0:
            r = check(e, rmap, order)
            order = r["order"]
            print(f"f{f}: screen check {r}", flush=True)
        if f % 1200 == 0:
            e.screenshot(out / f"s{shots:03d}_f{f}.png")
            shots += 1
        if replay and g == 0 and e.w(CLOCK) < 200 and e.b(SCREEN) == 0:
            instant_replay(e, rmap, order, out, rom_map(Path(rom).read_bytes(), 0xB5180))
            break
        if not stats_done and g == 0 and e.w(CLOCK) < 120 and e.b(SCREEN) == 0:
            before = check(e, rmap, order)
            G.press(e, "START")
            e.run(60)
            G.press(e, "DOWN", 5)
            G.press(e, "C")
            e.run(120)
            e.screenshot(out / "stats.png")
            G.press(e, "START")
            e.run(120)
            G.press(e, "START")
            e.run(120)
            after = check(e, rmap, order)
            print(f"f{f}: Player Stats and back: before {before}, after {after}", flush=True)
            stats_done = True
    print(f"lag: {lag} of {frames} frames of play the frame counter moved by other than 1", flush=True)
    import bisect
    near = [x for x in lag_at if (i := bisect.bisect_right(drops, x[0] + 120)) and x[0] + 120 >= drops[i - 1] >= x[0] - 0]
    print(f"  {len(drops)} puck drops; late frames within 120 frames before a drop (the faceoff's camera jump and "
          f"setup): {len(near)}; elsewhere {lag - len(near)}", flush=True)
    from collections import Counter
    print(f"  late frames by the counter's step: {dict(Counter(x[2] for x in lag_at))}", flush=True)
    print(f"  the first 40: {lag_at[:40]}", flush=True)


if __name__ == "__main__":
    main()
