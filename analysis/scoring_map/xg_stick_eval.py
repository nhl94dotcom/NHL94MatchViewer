"""Does the goalie's stick (xg.play_out's `stick`) make the Genesis xG model better? python xg_stick_eval.py [map|games|both]

map: the model with and without the stick against the Genesis scoring map (the game itself, exact, a set goalie), in
     the middle of the ice (within 30 of the centre line) and for five aims (Up, Right, Down, Left, none), 100 shots
     each: the Down slapshot from the middle, each band's average over those aims and its best (as compare_xg.py).
games: shot by shot on the recorded Genesis games (both game folders): log loss and totals with and without it, for
     shots and one-timers apart. A change is kept only if this gets better.
Gentle mode: one process at idle priority, resting as long as it works."""
import copy
import glob
import json
import math
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg  # noqa: E402
from lowload import breathe, gentle  # noqa: E402
from paths import RUNS, STATE_TOP  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def stick_rom():
    """Any of the Genesis ROMs: the hot points and animation scripts are the same in all of them (checked)."""
    for d in (ROOT / "roms", Path.home() / "Documents" / "NHL94 Viewer" / "roms"):
        for p in sorted(d.glob("*.bin")):
            return p.read_bytes()
    raise SystemExit("no Genesis ROM in roms/")


def map_goalie():
    """The map's goalie (Los Angeles's, record 11): drawn mirrored? From the saved state's work RAM (at state offset
    16, words byte-swapped): +$76 bit 0 set = shoots left = not mirrored."""
    s = open(STATE_TOP, "rb").read()
    a = (0xB04A + 11 * 0x80 + 0x76) & 0xFFFF
    return not (s[16 + (a ^ 1)] & 1)


def eval_map(rom):
    run = RUNS / "run1"
    rows = [json.loads(l) for f in glob.glob(f"{run}/w*.jsonl") for l in open(f)]
    valid = json.load(open(run / "validity.json"))
    rows = [r for r in rows if r["aims"] and valid.get(f"{r['net']},{r['hold']},{r['x']},{r['y']}", {"ok": True})["ok"]
            and abs(r["x"]) <= 30]                             # the middle of the ice: where the blind ring matters
    mirror = map_goalie()
    g_rom = xg.GenesisRom(rom)
    out = []
    for r in rows:
        top = r["net"] == "top"
        sg = 1 if top else -1
        px, py = r["x"], sg * r["y"]
        d3c = 260 * sg
        rx, ry = px, max(-259, min(259, py)) - d3c
        if rx * rx + ry * ry > 900:
            ln = math.isqrt(int(rx * rx + ry * ry)) + 1
            rx, ry = rx * 26 / ln, ry * 18 / ln
        gx, gy = rx, ry + d3c
        facing = xg.vtoa(px - gx, py - gy) % 8                 # set, facing the puck
        frame = g_rom.anim(xg.READY, facing)[0][0]
        reach = xg.REACH[(13 + 2) >> 1]
        for a in r["aims"]:
            if a["aim"] not in (0, 2, 4, 6, 8):                # Up, Right, Down, Left, nothing held
                continue
            tx, tz = xg.AIM[a["aim"]]
            res = {}
            for stick in (False, True):
                g = xg.Goalie(gx, gy, 0, 0, 48, 13, 13, 10, rom=g_rom, frame=frame, facing=facing, mirror=mirror)
                rng = random.Random(f"{r['net']}{r['hold']}{r['x']}{r['y']}{a['aim']}")
                n = 100
                res[stick] = sum(xg.play_out((px, py, 0), (tx, 264 * sg, tz), r["pout"], 15, 16 / 31, g, reach, 0, rng,
                                             stick=stick) == "goal" for _ in range(n)) / n
                breathe()
            out.append(dict(net=r["net"], hold=r["hold"], x=r["x"], y=r["y"], aim=a["aim"], game=a["chance"],
                            old=res[False], new=res[True]))
    json.dump(out, open(run / "xg_stick_map.json", "w"))
    band = lambda y: "88-168 out" if 88 <= 268 - y <= 168 else "58-87 out" if 268 - y >= 58 else "18-57 out" \
        if 268 - y >= 18 else None
    print("\nAgainst the map (the game, a set goalie): game / model before / model with the stick")
    for net in ("top", "bottom"):
        sel = [o for o in out if o["net"] == net and o["hold"] == 20 and o["aim"] == 4 and abs(o["x"]) <= 30
               and 88 <= 268 - o["y"] <= 168]
        m = lambda k: 100 * sum(o[k] for o in sel) / len(sel)
        print(f"  {net} net, slapshot holding Down from the middle (|x| <= 30, 88-168 out): "
              f"{m('game'):.1f}% / {m('old'):.1f}% / {m('new'):.1f}%  ({len(sel)} spots)")
        for hold, kind in ((3, "wrist"), (20, "slap")):
            for b in ("88-168 out", "58-87 out"):
                spots = {}
                for o in out:
                    if o["net"] == net and o["hold"] == hold and band(o["y"]) == b:
                        spots.setdefault((o["x"], o["y"]), []).append(o)
                if not spots:
                    continue
                avg = lambda k: 100 * sum(sum(o[k] for o in v) / len(v) for v in spots.values()) / len(spots)
                best = lambda k: 100 * sum(max(o[k] for o in v) for v in spots.values()) / len(spots)
                print(f"    {kind} {b}: mean of aims {avg('game'):.1f} / {avg('old'):.1f} / {avg('new'):.1f}%; "
                      f"best aim {best('game'):.1f} / {best('old'):.1f} / {best('new'):.1f}%")


def eval_games(rom):
    seen, files = set(), []
    for d in (ROOT / "matches", Path.home() / "Documents" / "NHL94 Viewer" / "matches"):
        for f in sorted(d.glob("*.js")):
            if f.name not in seen and not f.name.startswith("season") and not f.name.endswith(".summary.json"):
                seen.add(f.name)
                files.append(f)
    rows = []
    for f in files:
        text = open(f, encoding="utf-8").read()
        try:
            m = json.loads(text[text.index("{"):text.rindex("}") + 1])
        except ValueError:
            continue
        if m.get("system", "genesis") != "genesis" or not m.get("work"):
            continue
        res = {}
        for stick in (False, True):
            mm = copy.deepcopy(m)
            xg._CACHE.clear()
            xg.add_expected_goals(mm, stick_rom=rom if stick else None)
            res[stick] = mm["shotList"]
            breathe()
        for a, b in zip(res[False], res[True]):
            if "xg" in a and "xg" in b and a.get("result") != "blocked":
                rows.append((a["kind"], a.get("result") == "goal", a["xg"], b["xg"], f.name))
    print(f"\nRecorded Genesis shots: {len(rows)} from {len({r[4] for r in rows})} games")

    def ll(ps, ys):
        return -sum(math.log(min(0.999, max(0.001, p))) if y else math.log(1 - min(0.999, max(0.001, p)))
                    for p, y in zip(ps, ys)) / len(ys)
    for kind in ("shot", "one-timer", None):
        sel = [r for r in rows if kind is None or r[0] == kind]
        if not sel:
            continue
        ys = [r[1] for r in sel]
        print(f"  {kind or 'all'}: {len(sel)} shots, {sum(ys)} goals; expected {sum(r[2] for r in sel):.1f} before, "
              f"{sum(r[3] for r in sel):.1f} with the stick; log loss {ll([r[2] for r in sel], ys):.4f} before, "
              f"{ll([r[3] for r in sel], ys):.4f} with the stick")


def main():
    gentle()
    what = sys.argv[1] if len(sys.argv) > 1 else "both"
    rom = stick_rom()
    if what in ("map", "both"):
        eval_map(rom)
    if what in ("games", "both"):
        eval_games(rom)


if __name__ == "__main__":
    main()
