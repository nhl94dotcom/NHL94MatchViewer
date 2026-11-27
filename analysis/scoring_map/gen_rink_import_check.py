"""NOSE4Web's rink import, played (NHL '94 Genesis, 2026-11-27: nhl94_rink_import.bin, a picture imported into the
rink's tiles and map in place, Rinktilelist $5605A / RevRinkTilelist $B5180 and their tiles).

Each ROM (retail first, the build after) from power-on: Game Setup's Home and Visitor lines picked by presses
(gen_team_play_check.pick), the shortest periods, penalties on, the computer on both sides, one fixed seed; so the
two games play alike frame for frame while their timing matches (checked: the frame counter, camera and puck).
- At the first faceoff: video memory and colours saved; the whole rink drawn from the tiles in video memory, the
  ROM's map ($5605A) and the colours (OUT/rink_normal.png); the rink tiles below the logo (0-429; the logo's 430-453 change with the highlights' home teams, so they are compared
  across ROMs in the digest only) kept as this game's
  reference.
- Every 60 frames: a screenshot, the screen, period, clock, camera ($BD18 / $BD1C), the frame counter, puck. Every 300
  frames of play, and after every return to play from another screen: the rink tiles against the reference (a
  reload that brought back other tiles shows here), plane B ($C000) against the ROM map row by row (the map row each
  plane row holds: words and priority bits), and a digest of video memory by region for the cross-ROM comparison.
- At 1,200 frames of play: the pause menu's Instant Replay, back and forward, its reverse angle (START, C), the rink
  then drawn from video memory and RevRinkTilelist (OUT/rink_reverse.png), out to play again.
- To the end of the game and 4,000 frames past it (the three stars), START pressed only at screens that wait.
Then (compare): the two ROMs' screenshots pair by pair while their timing matches: the box of differing pixels; the
video memory regions that differ at matched moments; the cells where the two ROM maps differ (word, priority) and
whether plane B followed them; a sheet of differing pairs.

python gen_rink_import_check.py run ROM OUT HOME VISITOR [FRAMES_AFTER]
python gen_rink_import_check.py compare OUT_RETAIL OUT_BUILD SHEET.png
python gen_rink_import_check.py maps RETAIL BUILD OUT   (the two ROMs' maps and priority bits, cell by cell)
python gen_rink_import_check.py glass ROM OUT   (a skater and the puck held at the bottom boards, and at the top, by
  pokes each frame: screenshots, to see him pass behind the glass)"""
import hashlib
import json
import struct
import sys
from pathlib import Path

from PIL import Image

import gen_ot_check as G
import gen_team_play_check as T
import lowload
from emu import Emu

VRAM_AT, PLANE_B = 74789, 0xC000
GSP, CLOCK, SCREEN, FRAMECTR = 0xC466, 0xC468, 0xFFF7, 0xB03E
VPOS, HPOS = 0xBD18, 0xBD1C
CONT1, CONT2, BASE, SZ = 0xC328, 0xC32A, 0xB04A, 0x80
PUCK = BASE + 14 * SZ
RINK_TILES = 454                       # rink tiles 0-453 (the logo at 430-453), EASN from 454
REGIONS = {"rink 0-429": (0, 430), "logo 430-453": (430, 454), "454-$5FF": (454, 0x600), "$600-$7FF": (0x600, 0x800)}


def rom_map(rom, a):
    p, m = struct.unpack(">II", rom[a:a + 8])
    w, h = struct.unpack(">HH", rom[a + m:a + m + 4])
    return w, h, list(struct.unpack(f">{w * h}H", rom[a + m + 4:a + m + 4 + 2 * w * h]))


def vstate(e):
    st = bytes(e.serialize())
    return st[VRAM_AT:VRAM_AT + 0x10000], st[VRAM_AT + 0x10000:VRAM_AT + 0x10080]


def vword(vr, a):
    a &= 0xFFFF
    return vr[a] | vr[a + 1] << 8


def tile(vr, t):
    out = []
    for r in range(8):
        row = []
        for k in range(2):
            v = vword(vr, 32 * t + 4 * r + 2 * k)
            row += [(v >> 12) & 15, (v >> 8) & 15, (v >> 4) & 15, v & 15]
        out.append(row)
    return out


def rgb(cram, i):
    v = cram[2 * i] | cram[2 * i + 1] << 8          # Genesis Plus GX keeps colours packed in 9 bits: BBBGGGRRR
    return (v & 7) * 36, ((v >> 3) & 7) * 36, ((v >> 6) & 7) * 36


def render(vr, cram, w, h, words):
    im = Image.new("RGB", (8 * w, 8 * h))
    px = im.load()
    cache = {}
    for r in range(h):
        for c in range(w):
            v = words[r * w + c]
            t, pal, hf, vf = v & 0x7FF, (v >> 13) & 3, v >> 11 & 1, v >> 12 & 1
            if t not in cache:
                cache[t] = tile(vr, t)
            p = cache[t]
            for y in range(8):
                for x in range(8):
                    ci = p[7 - y if vf else y][7 - x if hf else x]
                    px[8 * c + x, 8 * r + y] = rgb(cram, pal * 16 + ci) if ci else (0, 0, 0)
    return im


def plane(vr):
    return [[vword(vr, PLANE_B + 2 * (r * 64 + c)) for c in range(64)] for r in range(32)]


def plane_check(vr, w, h, words):
    """Each plane row matched to the map row it holds; cells (of matched rows) whose word differs from the map's."""
    pl = plane(vr)
    rows, bad = 0, []
    for pr, ws in enumerate(pl):
        best = max(range(h), key=lambda r: sum(1 for c in range(w) if ws[c] == words[r * w + c]))
        same = sum(1 for c in range(w) if ws[c] == words[best * w + c])
        if same >= w * 0.6:
            rows += 1
            bad += [(pr, best, c, hex(ws[c]), hex(words[best * w + c])) for c in range(w) if ws[c] != words[best * w + c]]
    return rows, bad


def digest(vr):
    return {k: hashlib.md5(vr[32 * lo:32 * hi]).hexdigest()[:12] for k, (lo, hi) in REGIONS.items()}


def instant_replay(e, out, rom, log):
    G.press(e, "START")
    e.run(60)
    for _ in range(30):
        if e.w(0xCF20) == 1:
            break
        G.press(e, "DOWN")
    e.screenshot(out / "pause_menu.png")
    G.press(e, "C")
    e.run(200)
    n = 0
    for part in ("normal", "reverse"):
        if part == "reverse":
            G.press(e, "START")
            e.run(120)
            e.screenshot(out / "replay_menu.png")
            G.press(e, "C")
            e.run(120)
            vr, cram = vstate(e)
            w, h, rev = rom_map(rom, 0xB5180)
            render(vr, cram, w, h, rev).save(out / "rink_reverse.png")
            (out / "vram_reverse.bin").write_bytes(vr + cram)
            rows, bad = plane_check(vr, w, h, rev)
            log.append({"event": "reverse angle", "plane rows matched": rows, "cells off the reverse map": len(bad),
                        "examples": bad[:8], "digest": digest(vr)})
        for mv in ("LEFT", "RIGHT"):
            for k in range(6):
                e.run(50, hold=[mv])
                e.screenshot(out / f"replay_{part}_{n:02d}_{mv}.png")
                n += 1
    for k in range(6):
        G.press(e, "START")
        e.run(200)
        e.screenshot(out / f"replay_exit_{k}.png")
        if e.b(SCREEN) == 0:
            break


def run(rom_path, out, home, visitor, after=4000):
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    rom = Path(rom_path).read_bytes()
    w, h, words = rom_map(rom, 0x5605A)
    e = Emu(rom_path)
    G.to_setup(e, out)
    T.press(e, "DOWN")
    T.press(e, "DOWN")
    T.pick(e, T.TEAM1, home, out, "home")
    T.press(e, "DOWN")
    T.pick(e, T.TEAM2, visitor, out, "visitor")
    e.setw(T.PERLEN, 0)
    e.setw(T.OPTPEN, 2)
    if not G.into_play(e):
        print("never reached play")
        return
    e.setl(T.SEED, 0x2545F491)
    vr, cram = vstate(e)
    render(vr, cram, w, h, words).save(out / "rink_normal.png")
    (out / "vram_start.bin").write_bytes(vr + cram)
    ref = vr[:32 * 430]
    rows, bad = plane_check(vr, w, h, words)
    log = [{"event": "first faceoff", "frame": 0, "plane rows matched": rows, "cells off the map": len(bad),
            "examples": bad[:8], "digest": digest(vr)}]
    samples = []
    frame, play_frames, last_clock, still, was_play, replayed, ended_at = 0, 0, None, 0, True, False, None
    while frame < 60 * 60 * 40:
        sc = e.b(SCREEN)
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last_clock else 0
            last_clock = c
            e.screenshot(out / f"s_{frame // 60:05d}.png")
            samples.append({"i": frame // 60, "screen": sc, "gsp": e.w(GSP), "clock": c, "cam": [e.w(VPOS), e.w(HPOS)],
                            "fc": e.w(FRAMECTR), "puck": [e.w(PUCK), e.w(PUCK + 0x14)]})
            if frame % 3600 == 0:
                lowload.breathe()
        back = sc == 0 and not was_play
        if sc == 0 and (play_frames % 300 == 0 or back) and frame % 2 == 0:
            vr, cram = vstate(e)
            rows, bad = plane_check(vr, w, h, words)
            log.append({"event": "back in play" if back else "play", "frame": frame, "gsp": e.w(GSP), "clock": e.w(CLOCK),
                        "rink tiles as at the faceoff": vr[:32 * 430] == ref, "plane rows matched": rows,
                        "cells off the map": len(bad), "examples": bad[:4], "digest": digest(vr)})
        was_play = sc == 0
        if sc == 0:
            play_frames += 2
        if play_frames >= 1200 and not replayed and sc == 0 and e.w(CLOCK) != 0:
            replayed = True
            instant_replay(e, out, rom, log)
            vr, cram = vstate(e)
            rows, bad = plane_check(vr, w, h, words)
            log.append({"event": "after the replay", "frame": frame, "screen": e.b(SCREEN),
                        "rink tiles as at the faceoff": vr[:32 * 430] == ref, "plane rows matched": rows,
                        "cells off the map": len(bad), "examples": bad[:4], "digest": digest(vr)})
        if ended_at is None and e.w(GSP) >= 3:
            ended_at = frame
        if ended_at is not None and frame - ended_at > after:
            break
        e.run(2, hold=["START"] if still >= 8 and frame % 60 < 2 and (ended_at is None or frame - ended_at > 1500) else [])
        frame += 2
    (out / "log.json").write_text(json.dumps({"samples": samples, "log": log}, indent=0))
    print(out, "frames", frame, "play frames", play_frames, "score", e.w(0xC6DA), e.w(0xCA3E))


def maps(retail, build, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    a, b = Path(retail).read_bytes(), Path(build).read_bytes()
    res = {}
    for name, at in (("normal", 0x5605A), ("reverse", 0xB5180)):
        w, h, ma = rom_map(a, at)
        w2, h2, mb = rom_map(b, at)
        diff = [(i // w, i % w) for i in range(w * h) if ma[i] != mb[i]]
        prio = [(i // w, i % w) for i in range(w * h) if (ma[i] ^ mb[i]) & 0x8000]
        pal = [(i // w, i % w) for i in range(w * h) if (ma[i] ^ mb[i]) & 0x6000]
        rows = sorted({r for r, c in diff})
        res[name] = {"size": [w, h, w2, h2], "cells differing": len(diff), "rows": rows,
                     "priority bit changed": prio, "palette line changed": pal,
                     "highest tile used": [max(x & 0x7FF for x in ma), max(x & 0x7FF for x in mb)],
                     "priority cells (retail, build)": [sum(1 for x in ma if x & 0x8000), sum(1 for x in mb if x & 0x8000)]}
        print(name, json.dumps({k: (v if k not in ("priority bit changed", "palette line changed") else len(v)) for k, v in res[name].items()}))
    (out / "maps.json").write_text(json.dumps(res, indent=1))


def compare(ra, rb, sheet):
    from PIL import ImageChops
    ra, rb = Path(ra), Path(rb)
    A, B = json.loads((ra / "log.json").read_text()), json.loads((rb / "log.json").read_text())
    sa = {s["i"]: s for s in A["samples"]}
    sb = {s["i"]: s for s in B["samples"]}
    synced, boxes, pairs, first_off = 0, {}, [], None
    for i in sorted(set(sa) & set(sb)):
        x, y = sa[i], sb[i]
        same = (x["screen"], x["gsp"], x["clock"], x["cam"], x["puck"]) == (y["screen"], y["gsp"], y["clock"], y["cam"], y["puck"])
        if not same:
            if first_off is None:
                first_off = i
            continue
        synced += 1
        p, q = ra / f"s_{i:05d}.png", rb / f"s_{i:05d}.png"
        if not (p.exists() and q.exists()):
            continue
        a, b = Image.open(p).convert("RGB"), Image.open(q).convert("RGB")
        box = ImageChops.difference(a, b).getbbox()
        boxes[i] = box
        if box:
            pairs.append((i, a, b))
    print(f"samples {len(sa)} / {len(sb)}; matched timing {synced}; first out of step {first_off}")
    print(f"pairs with differing pixels {len(pairs)} of {len(boxes)}")
    for i, box in boxes.items():
        if box:
            s = sa[i]
            print(f"  {i}: screen {s['screen']} period {s['gsp'] + 1} clock {s['clock']} cam {s['cam']}: {box}")
    da = {(l.get('event'), l.get('frame')): l.get("digest") for l in A["log"]}
    db = {(l.get('event'), l.get('frame')): l.get("digest") for l in B["log"]}
    for k in sorted(set(da) & set(db), key=lambda k: (k[1] is None, k[1] or 0)):
        if da[k] and db[k]:
            d = [r for r in da[k] if da[k][r] != db[k][r]]
            print("  vram", k, "differs in", d)
    for L, name in ((A, "retail"), (B, "build")):
        for l in L["log"]:
            if l.get("rink tiles as at the faceoff") is False or l.get("cells off the map") or l.get("cells off the reverse map"):
                print(f"  {name}: {l}")
    if pairs:
        pick = pairs[:: max(1, len(pairs) // 8)][:8]
        w, h = pick[0][1].size
        im = Image.new("RGB", (w * len(pick), 2 * h))
        for k, (i, a, b) in enumerate(pick):
            im.paste(a, (k * w, 0))
            im.paste(b, (k * w, h))
        im.save(sheet)


def glass(rom_path, out):
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom_path)
    G.to_setup(e, out)
    if not G.into_play(e):
        print("never reached play")
        return

    def put(k, x, y):
        r = BASE + SZ * k
        for off, v in ((0, x), (2, 0), (0x14, y), (0x16, 0), (0x28, 0), (0x2A, 0), (0x2C, 0)):
            e.setw(r + off, v & 0xFFFF)
    for tag, ys in (("bottom", (-262, -270, -278, -286)), ("top", (262, 270, 278, 286))):
        for y in ys:
            for f in range(150):
                e.setw(CONT1, 0)
                e.setw(CONT2, 0)
                put(1, 60, y)
                put(14, 20, y + (12 if y < 0 else -12))
                e.run(1)
            e.screenshot(out / f"glass_{tag}_{abs(y)}.png")


if __name__ == "__main__":
    if sys.argv[1] == "glass":
        glass(sys.argv[2], Path(sys.argv[3]))
        sys.exit()
    if sys.argv[1] == "run":
        run(sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]) if len(sys.argv) > 6 else 4000)
    elif sys.argv[1] == "maps":
        maps(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        compare(sys.argv[2], sys.argv[3], sys.argv[4])
