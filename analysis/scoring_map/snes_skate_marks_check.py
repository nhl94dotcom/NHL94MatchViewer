"""NOSE4Web's SNES skate marks, played (2026-11-14: NHL94_skate_marks.smc, nhl94snes_2026_skate_marks.sfc;
gen_skate_marks_check.py is the Genesis one).

The build writes each mark into the rink map in RAM (rinkmapbuf $7F:C800, 48 x 113 words after a 6-byte header): a
plain-ice word (tile 0, no flips) becomes tile $BA, palette and priority kept, flipped ($4000) for the other diagonal;
the count at $7F:F400, the period it is for $7F:F402, the list of marks (offset, bit 15 the flip) from $7F:F410.

A computer game (snes_60fps_cvc's boot: Montreal at home against Los Angeles, 5-minute periods, every pad taken off
the teams), START through the breaks, the scores set level with 3 s left in period 3 (overtime), until overtime's
first 100 s (real) or the game's end. Checked:
- the map: the first map of play (count 0) kept as the plain map; every cell that differs later must be a mark (tile 0
  -> $BA, the rest of the word the same but the flip), as many as the count, the same cells as the list;
- video memory (Snes9x memory 3): the rink rows at word $400 + 32 v (map columns 0-31) and $800 + 32 v (32-47),
  v = 0-31 (updatescroll_rows); each video row matched to its map row, every mark on it shown, no $BA anywhere the
  map hasn't one (stray; on lines and logos when the plain map's tile there isn't 0). Every 30 s (real);
- another game's highlight (gmode $15D4 bit $10): the count, the list and the map unchanged from before it (map
  rebuilt for it, the marks laid back);
- each period's puck drop (the clock's first tick): the count 0 and the map plain;
- the pause menu's stats (item 2) and instant replay (item 1) in period 2: the map, list and count the same after;
- slowdown: timestep ($0ADB, the frames a game step covers: 2 at the game's 30 steps a second) each frame of play.
Run on the original too (--lag-only) for its timesteps.

python snes_skate_marks_check.py ROM OUT [--lag-only] [--seed=N] [--patient] [--stop=FRAME] [--scoreboard-probe]"""
import sys
from collections import Counter
from pathlib import Path

import lowload
import menu_shots as M
import snes_60fps_cvc as cvc

MAP, COUNT, FORP, LIST = 0x1C800 + 6, 0x1F400, 0x1F402, 0x1F410
W, H = 48, 113
GSP, CLOCK, CLOCKSTOP, SFLAGS, GMODE, PSITEM, TIMESTEP = 0x1630, 0x1632, 0x15D6, 0x15D8, 0x15D4, 0x0D15, 0x0ADB
GOALS, TEAMS = 0x178E, (0x1C98, 0x1C9A)
MARK_TILE = 0xBA


def rmap(e):
    return [e.w(MAP + 2 * i) for i in range(W * H)]


def listed(e):
    return {e.w(LIST + 2 * i) for i in range(e.w(COUNT))} if e.w(COUNT) <= 240 else None


def plain_from_list(e):
    """The plain map when marks are already down: each listed cell put back to tile 0 unflipped (the list's offset
    form chosen as the one whose every cell holds $BA)."""
    now = rmap(e)
    lst = listed(e) or set()
    for k, d in ((2, 0), (1, 0), (2, 6)):
        idx = [((v & 0x7FFF) - d) // k for v in lst]
        if all(0 <= i < W * H and (now[i] & 0x3FF) == MARK_TILE for i in idx):
            for i in idx:
                now[i] &= ~0x43FF
            return now, (k, d)
    return None, None


def map_check(e, plain):
    """The map against the plain map: (marks, bad cells, count, list agrees)."""
    now = rmap(e)
    marks, bad = set(), []
    for i, (a, b) in enumerate(zip(plain, now)):
        if a != b:
            if (a & 0x43FF) == 0 and (b & 0x3FF) == MARK_TILE and (a & ~0x43FF) == (b & ~0x43FF):
                marks.add((i, bool(b & 0x4000)))
            else:
                bad.append((divmod(i, W), hex(a), hex(b)))
    lst = listed(e)
    agrees = lst is not None and {(2 * i) | (0x8000 if f else 0) for i, f in marks} == lst
    for k, d in ((1, 0), (2, 6)):                 # the list's offsets: words, or bytes from the header
        if lst is not None and not agrees:
            agrees = {(k * i + d) | (0x8000 if f else 0) for i, f in marks} == lst
    return dict(marks=len(marks), count=e.w(COUNT), list_agrees=agrees, bad=len(bad), bad_first=bad[:4])


def vram_check(e, vram, plain):
    now = rmap(e)

    def vw(a):
        return vram[2 * a] | vram[2 * a + 1] << 8
    res = Counter()
    top = (e.w(0x07DC) // 8) % 32                 # BG2VScroll: the top video row on the screen (28 rows show)
    where = []
    for v in range(32):
        row = [vw(0x400 + 32 * v + c) for c in range(32)] + [vw(0x800 + 32 * v + c) for c in range(16)]
        best = max(range(H), key=lambda r: sum(row[c] == now[r * W + c] for c in range(W)))
        same = sum(row[c] == now[best * W + c] for c in range(W))
        if same < W * 0.7:
            continue
        res["rows"] += 1
        for c in range(W):
            m, p, s = now[best * W + c], plain[best * W + c], row[c]
            on = (v - top) % 32 < 29
            if m != p:
                res["shown" if s == m else "missing"] += 1
                if s != m:
                    where.append(("missing", best, c, v, "on screen" if on else "off screen", hex(s), hex(m)))
            elif (s & 0x3FF) == MARK_TILE and s != m:
                res["stray" if (p & 0x3FF) == 0 else "stray_on_lines"] += 1
                where.append(("stray", best, c, v, "on screen" if on else "off screen", hex(s), hex(m), same))
    out = dict(res)
    if where:
        out["where"] = where[:6]
        out["sfhormode"] = e.w(0x15DA)
    return out


def kept(before, after, plain):
    """Every mark before still in the map after (new ones may have come with the play since)."""
    gone = [i for i, (p, b) in enumerate(zip(plain, before)) if p != b and after[i] != b]
    return "every mark kept" if not gone else f"{len(gone)} marks GONE"


def video(e, vram, plain):
    r = vram_check(e, vram, plain)
    if r.get("missing"):
        e.run(2)
        r["missing_2_frames_later"] = vram_check(e, vram, plain).get("missing", 0)
    return r


def press(e, b, after=40):
    e.run(4, hold=[b])
    e.run(after)


def in_play(e):
    return e.w(SFLAGS) & 0x0801 == 0 and not e.w(GMODE) & 0x10


def pause_item(e, item, log, out, tag):
    press(e, "START", 90)
    for _ in range(40):
        if e.w(PSITEM) == item:
            break
        press(e, "DOWN")
    press(e, "A", 300)
    seen = []
    if item == 1:                                  # the replay: back and forward a while
        for b in ("LEFT", "RIGHT"):
            for k in range(4):
                e.run(60, hold=[b])
                seen.append((e.w(COUNT), tuple(sorted(listed(e) or ()))))
        e.screenshot(out / f"{tag}_in.png")
    else:
        e.screenshot(out / f"{tag}_in.png")
    for k in range(10):                            # out: START / A until the pause menu, then Resume (item 0)
        press(e, "START" if k % 2 == 0 else "A", 240)
        if e.w(SFLAGS) & 1 and not e.w(SFLAGS) & 0x0800:
            break
    for _ in range(40):
        if e.w(PSITEM) == 0:
            break
        press(e, "UP")
    press(e, "START", 240)
    return seen


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    lag_only = "--lag-only" in sys.argv
    wait = 9000 if "--patient" in sys.argv else 600     # START after this many frames of a stopped clock (the SNES's
    # intermission highlights come after its ticker has shown every game, $150 frames each: --patient waits for them)
    probe, hor_frames = "--scoreboard-probe" in sys.argv, 0
    stop = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--stop=")), 0))
    seed = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--seed=")), 0))
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    import ctypes as C
    e = M.emulator(rom)
    m = cvc.Mem(e, rom)
    vram = (C.c_ubyte * e.lib.retro_get_memory_size(3)).from_address(e.lib.retro_get_memory_data(3))
    tmp = out / "_menu"
    if m.sa1:
        M.play(e, f"w{1800 + 53 * seed} START w240", tmp)
    else:
        M.play(e, f"w{1500 + 53 * seed} START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
    M.play(e, "START w240 START w200 w2400", tmp)
    for _ in range(12):
        c = e.w(CLOCK)
        e.run(240)
        if e.w(CLOCK) != c and e.w(CLOCKSTOP) == 0:
            break
        press(e, "START", 60)
    cvc.computer_only(m)
    teams = tuple(e.w(a) for a in TEAMS)
    print(f"in play: period {e.w(GSP) + 1} clock {e.w(CLOCK)} count {e.w(COUNT)} teams {teams}", flush=True)
    plain = rmap(e) if e.w(COUNT) == 0 else None
    if plain is None:
        plain, form = plain_from_list(e)
        print(f"marks already at the start ({e.w(COUNT)}): the plain map from the list (offset form {form}; "
              f"list {sorted(hex(v) for v in listed(e))})", flush=True)
    steps = Counter()
    bands = [Counter() for _ in range(4)]          # the timesteps by the count: 0-79, 80-159, 160-239, 240
    still, last_clk, shots = 0, e.w(CLOCK), 0
    last_gsp, fresh_pending, tied, started, ot_from = e.w(GSP), False, False, 0, None
    in_hl, hl_before, last_count = False, None, 0
    done_stats = done_replay = False
    for f in range(60 * 60 * 40):
        if f % 300 == 0:
            cvc.computer_only(m)
            if f % 3600 == 0:
                lowload.breathe()
        clk = e.w(CLOCK)
        still = still + 1 if clk == last_clk else 0
        last_clk = clk
        e.run(1, hold=["START"] if still >= wait and f % 150 < 4 else [])
        if e.w(CLOCK) > 300 and e.w(GSP) < 3:
            e.setw(CLOCK, 300)                       # 5-minute periods whatever the menu set
        if in_play(e) and e.w(CLOCKSTOP) == 0:
            steps[e.w(TIMESTEP)] += 1
            bands[min(e.w(COUNT), 240) // 80][e.w(TIMESTEP)] += 1
        g = e.w(GSP)
        hl = bool(e.w(GMODE) & 0x10) or tuple(e.w(a) for a in TEAMS) != teams
        if hl and not in_hl:
            in_hl, hl_before = True, (e.w(COUNT), listed(e))
            print(f"f{f}: another game's highlight starts: count {e.w(COUNT)}", flush=True)
        if in_hl:
            if not hl:
                in_hl = False
                same = (e.w(COUNT), listed(e)) == hl_before
                print(f"f{f}: highlight over: count {e.w(COUNT)}, list {'unchanged' if same else 'CHANGED'}"
                      + ("" if lag_only or plain is None else f", map {map_check(e, plain)}"), flush=True)
            elif (e.w(COUNT), listed(e)) != hl_before and f % 60 == 0:
                print(f"f{f}:   in the highlight: count {e.w(COUNT)}", flush=True)
            continue
        if g != last_gsp:
            print(f"f{f}: period {last_gsp + 1} -> {g + 1}: count {e.w(COUNT)}", flush=True)
            last_gsp = g
            if g >= 4:
                break
            fresh_pending = True
            if g == 3:
                ot_from = f
        if fresh_pending and not lag_only and e.w(COUNT) != last_count:
            print(f"f{f}:   before the puck drop: count {e.w(COUNT)} (clock {e.w(CLOCK)}, stopped {e.w(CLOCKSTOP)}, "
                  f"stored period {e.w(FORP)}, sflags {e.w(SFLAGS):04x})", flush=True)
        last_count = e.w(COUNT)
        if fresh_pending and in_play(e) and clk >= 295 and e.w(CLOCK) == clk - 1:
            fresh_pending = False
            started = g
            if not lag_only:
                print(f"f{f}: period {g + 1} puck drop: count {e.w(COUNT)}"
                      + (f", map {map_check(e, plain)}" if plain else ""), flush=True)
        if g == 2 and started == 2 and not tied and e.w(CLOCK) <= 3 and in_play(e):
            e.setw(GOALS, e.w(GOALS + 2))
            tied = True
            print(f"f{f}: scores set level ({e.w(GOALS)}-{e.w(GOALS + 2)}) for overtime", flush=True)
        if ot_from is not None and f - ot_from >= 6000:
            break
        if stop and f >= stop:
            break
        if probe:                                    # the scoreboard view between periods: $BA in its rows
            hor = e.w(0x15DA)
            hor_frames = hor_frames + 1 if hor else 0
            if hor_frames == 120:
                def vw(a):
                    return vram[2 * a] | vram[2 * a + 1] << 8
                ba = [(v, c) for v in range(32) for c in range(48)
                      if (vw((0x400 if c < 32 else 0x800) + 32 * v + c % 32) & 0x3FF) == MARK_TILE]
                print(f"f{f}: scoreboard view (period {g + 1}, count {e.w(COUNT)}): $BA in {len(ba)} video cells, "
                      f"rows {sorted(set(v for v, _ in ba))}: {ba[:12]}", flush=True)
                e.screenshot(out / f"scoreboard_f{f}.png")
        if lag_only or plain is None:
            continue
        if f % 120 == 0 and in_play(e):
            print(f"f{f}: period {g + 1} clock {e.w(CLOCK)} marks {e.w(COUNT)}", flush=True)
        if f % 1800 == 900 and in_play(e):
            print(f"f{f}: check map {map_check(e, plain)} video {video(e, vram, plain)}", flush=True)
        if f % 1200 == 0 and in_play(e):
            e.screenshot(out / f"s{shots:03d}_f{f}.png")
            shots += 1
        if g == 1 and started == 1 and in_play(e) and e.w(CLOCK) < 200 and not done_stats:
            before = map_check(e, plain), rmap(e)
            pause_item(e, 2, None, out, "stats")
            after = map_check(e, plain), rmap(e)
            print(f"f{f}: stats screen and back: before {before[0]}, after {after[0]}, map "
                  f"{kept(before[1], after[1], plain)}; video {video(e, vram, plain)}", flush=True)
            done_stats = True
        if g == 1 and started == 1 and in_play(e) and e.w(CLOCK) < 150 and not done_replay:
            before = (e.w(COUNT), listed(e)), rmap(e)
            seen = pause_item(e, 1, None, out, "replay")
            after = (e.w(COUNT), listed(e)), rmap(e)
            print(f"f{f}: instant replay: in it {sorted(set(c for c, _ in seen))} (count before {before[0][0]}), list "
                  f"{'unchanged' if all(set(l) == (before[0][1] or set()) for _, l in seen) else 'CHANGED'}; after: "
                  f"count {after[0][0]}, map {kept(before[1], after[1], plain)}; "
                  f"video {video(e, vram, plain)}", flush=True)
            done_replay = True
    print(f"timesteps over frames of play: {dict(sorted(steps.items()))}", flush=True)
    for k, b in enumerate(bands):
        n = sum(b.values())
        if n:
            print(f"  count {80 * k}-{min(80 * k + 79, 240)}: {n} frames, in 3+ frame steps "
                  f"{sum(v for t, v in b.items() if t >= 3) / n:.1%}", flush=True)


if __name__ == "__main__":
    main()
