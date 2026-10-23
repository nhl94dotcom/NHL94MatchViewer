"""Do the goalie's stick and the rebound rule (xg.play_out's `stick`, `rebound`) make the Genesis xG model better?
python xg_stick_eval.py [map|games|both]. Three versions compared: before, with the stick, with the stick and rebounds.

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
    """The map's goalie (Los Angeles's, record 11): drawn mirrored, and his Puck Control (the Shot Power slot, +$6C),
    from the saved state's work RAM (at state offset 16, words byte-swapped): +$76 bit 0 set = shoots left."""
    s = open(STATE_TOP, "rb").read()
    byte = lambda off: s[16 + (((0xB04A + 11 * 0x80 + off) & 0xFFFF) ^ 1)]
    return not (byte(0x76) & 1), byte(0x6C)


VERSIONS = (("before", False, False), ("stick", True, False), ("stick+rebound", True, True))


def eval_map(rom):
    """The map's goalie is exactly where the game put him: no position blur (GOALIE_SPREAD stands for the error of
    reading a recorded goalie, and a 4-unit blur hides the blind ring, a few units wide)."""
    xg.GOALIE_SPREAD = 0.0
    run = RUNS / "run1"
    rows = [json.loads(l) for f in glob.glob(f"{run}/w*.jsonl") for l in open(f)]
    valid = json.load(open(run / "validity.json"))
    rows = [r for r in rows if r["aims"] and valid.get(f"{r['net']},{r['hold']},{r['x']},{r['y']}", {"ok": True})["ok"]
            and abs(r["x"]) <= 30]                             # the middle of the ice: where the blind ring matters
    mirror, pc = map_goalie()
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
            for name, stick, rebound in VERSIONS:
                g = xg.Goalie(gx, gy, 0, 0, 48, 13, 13, 10, rom=g_rom, frame=frame, facing=facing, mirror=mirror,
                              puck_control=pc)
                rng = random.Random(f"{r['net']}{r['hold']}{r['x']}{r['y']}{a['aim']}")
                n = 100
                res[name] = sum(xg.play_out((px, py, 0), (tx, 264 * sg, tz), r["pout"], 15, 16 / 31, g, reach, 0, rng,
                                            stick=stick, rebound=rebound) == "goal" for _ in range(n)) / n
                breathe()
            out.append(dict(net=r["net"], hold=r["hold"], x=r["x"], y=r["y"], aim=a["aim"], game=a["chance"], **res))
    json.dump(out, open(run / "xg_stick_map.json", "w"))
    band = lambda y: "88-168 out" if 88 <= 268 - y <= 168 else "58-87 out" if 268 - y >= 58 else "18-57 out" \
        if 268 - y >= 18 else None
    print("\nAgainst the map (the game, a set goalie): game / before / stick / stick + rebound")
    for net in ("top", "bottom"):
        sel = [o for o in out if o["net"] == net and o["hold"] == 20 and o["aim"] == 4 and abs(o["x"]) <= 30
               and 88 <= 268 - o["y"] <= 168]
        m = lambda k: 100 * sum(o[k] for o in sel) / len(sel)
        print(f"  {net} net, slapshot holding Down from the middle (|x| <= 30, 88-168 out): "
              f"{m('game'):.1f}% / {m('before'):.1f}% / {m('stick'):.1f}% / {m('stick+rebound'):.1f}%  ({len(sel)} spots)")
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
                ks = ("game", "before", "stick", "stick+rebound")
                print(f"    {kind} {b}: mean of aims " + " / ".join(f"{avg(k):.1f}" for k in ks)
                      + "%; best aim " + " / ".join(f"{best(k):.1f}" for k in ks) + "%")


GAME_VERSIONS = (("before, blur 4", False, False, 4.0), ("stick+rebound, blur 4", True, True, 4.0),
                 ("stick+rebound, blur 2", True, True, 2.0), ("stick+rebound, blur 1", True, True, 1.0),
                 ("stick+rebound, blur 0", True, True, 0.0))


def eval_games(rom):
    """GOALIE_SPREAD was fitted to the recordings before the stick was modelled, so the new model is tried at several
    blurs."""
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
        res = []
        for name, stick, rebound, spread in GAME_VERSIONS:
            xg.GOALIE_SPREAD = spread
            mm = copy.deepcopy(m)
            xg._CACHE.clear()
            xg.add_expected_goals(mm, stick_rom=rom if stick else None, rebound=rebound)
            res.append(mm["shotList"])
            breathe()
        for shots in zip(*res):
            if all("xg" in s for s in shots) and shots[0].get("result") != "blocked":
                rows.append((shots[0]["kind"], shots[0].get("result") == "goal", *(s["xg"] for s in shots), f.name))
    print(f"\nRecorded Genesis shots: {len(rows)} from {len({r[-1] for r in rows})} games; versions: "
          + " | ".join(v[0] for v in GAME_VERSIONS))

    def ll(ps, ys):
        return -sum(math.log(min(0.999, max(0.001, p))) if y else math.log(1 - min(0.999, max(0.001, p)))
                    for p, y in zip(ps, ys)) / len(ys)
    for kind in ("shot", "one-timer", None):
        sel = [r for r in rows if kind is None or r[0] == kind]
        if not sel:
            continue
        ys = [r[1] for r in sel]
        k = len(GAME_VERSIONS)
        exp = " / ".join(f"{sum(r[2 + i] for r in sel):.1f}" for i in range(k))
        lls = " / ".join(f"{ll([r[2 + i] for r in sel], ys):.4f}" for i in range(k))
        print(f"  {kind or 'all'}: {len(sel)} shots, {sum(ys)} goals; expected {exp}; log loss {lls}")


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
