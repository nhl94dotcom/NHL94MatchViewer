"""NOSE4Web's SNES "Goalie poke check reaches the ice" (2026-11-10, c545a2e), played against the original.

From the code (collide/checkpuckcoll_ccx .9): a goalie's stick reaches a puck by the frame's stick spot (GetFrameHot):
reach |x|, height window (2/3)|y| +- (2/3)|x| (the top at least 5); a carried puck within about 6 units of the tip
(puckstick: dx^2 + dy^2 < 37) is knocked loose (.3: a2touchpuck, deflect). Straight up or down the ice the poke
(SPAgpoke) can't touch a puck on the ice. The option, only in SPAgpoke: reach max(|x|, |y|), the window from the ice
up to the same top.

- `trials ORIGINAL OPTION OUT`: in live play (snes_assist_stick_test.Game, both base states: the two nets), the pad-1
  skater with the puck and the goalie he attacks pinned in place, the carrier straight in front 12-16 units (outside
  the goalie's body box, +-11), to the side 25-30 or on the diagonals, until the computer goalie pokes on his own
  (assgoalie's roll, 1 in 25.6 a think, within 35 units): whether the puck came loose within 22 frames and by what
  (the goalie's lockout: his stick or his body), and the poke's direction (its frame). The same trials (state, spot, seed) on both ROMs, each in its own process.
- `cvc ROM GAMES OUT`: snes_60fps_cvc's computer games (5-minute periods, penalties on, each its own seed): every
  goalie poke at a carried puck, whether it came loose, and who had the puck next (the goalie, his team, the other
  team), within 2 s (real).

python snes_goalie_poke_check.py trials ORIGINAL OPTION OUT | cvc ROM GAMES OUT"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import lowload
from snes_assist_stick_test import Game, POSITION, PUCK, XPOS, YPOS, XVEL, YVEL

PUCKC, SPA, FRAME, PFTEAM, FACE, NOPUCK = 0x0AD9, 0x11A3, 0x0D97, 0x1503, 0x1163, 0x1203
SEED = 0x0792
GPOKE = 0xE528
SA1_SHIFT = 0xEA06 - 0xF46A
SPOTS = [("straight", 0, f) for f in (16, 20, 24, 28)] + \
        [("sideways", s * x, 2) for s in (1, -1) for x in (25, 30)] + \
        [("diagonal", s * x, f) for s in (1, -1) for x, f in ((18, 14), (22, 18))]


def gpoke(G):
    return (GPOKE + (SA1_SHIFT if G.g.sa1 else 0)) & 0xFFFF


def trial(G, base, spot, seed):
    """The goalie and the carrier pinned where they are put for the whole trial (the goalie still animates), the puck
    on the carrier's spot; the cause of a puck coming loose from the goalie's lockout then: his nopuck over 15 = his
    stick (puckstick's steal: Stickhandling + 20), 8-15 = his body (puckgoalie: 10)."""
    kind, sx, fwd = spot
    G.e.unserialize(base)
    a, team, up = G.me()
    g = next(k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if G.w(POSITION + 2 * k) == 0)
    poke = gpoke(G)
    G.setw(SEED, (0x9E37 * (seed + 1)) & 0xFFFF or 1)
    G.setw(SEED + 2, (0x7F4A * (seed + 3)) & 0xFFFF or 1)
    gx, gy = G.sw(XPOS + 2 * g), G.sw(YPOS + 2 * g)
    G.park(a, up)
    start, d, how, prel = None, None, None, None
    for f in range(1200):
        G.put(g, gx, gy)
        G.put(a, gx + sx, gy - up * fwd)                 # "in front" of the goalie: toward centre ice
        if start is None:
            G.setw(PUCKC, 2 * a)
            G.put(PUCK, gx + sx, gy - up * fwd)
        G.run()
        if start is None and G.w(SPA + 2 * g) == poke:
            start = f
        if start is not None:
            fr = G.w(FRAME + 2 * g)
            if 678 <= fr < 694:
                d = (fr - 678) // 2
            if how is None and G.w(PUCKC) >= 0x8000:
                np = G.w(NOPUCK + 2 * g)
                how = "stick" if np > 15 else "body" if np >= 8 else "other (%d)" % np
                prel = (G.sw(XPOS + 2 * PUCK) - gx, (gy - G.sw(YPOS + 2 * PUCK)) * up)
            if f - start >= 22:
                break
    if start is None:
        return {"poke": False}
    return {"poke": True, "dir": d, "loose": how is not None, "how": how, "puck": prel}


def run_trials(rom, out, label):
    G = Game(rom)
    res = []
    for bi, base in enumerate(G.g.bases[:2]):
        for spot in SPOTS:
            for sd in range(4):
                r = trial(G, base, spot, 0x4100 + 37 * sd + 11 * SPOTS.index(spot) + 101 * bi)
                res.append(dict(base=bi, kind=spot[0], sx=spot[1], fwd=spot[2], seed=sd, **r))
        lowload.breathe()
    (out / f"trials_{label}.json").write_text(json.dumps(res))


def trials(orig, option, out):
    for rom, label in ((orig, "original"), (option, "option")):
        subprocess.run([sys.executable, __file__, "--one", rom, str(out), label], check=True)
    a = json.loads((out / "trials_original.json").read_text())
    b = json.loads((out / "trials_option.json").read_text())
    t = Counter()
    for x, y in zip(a, b):
        same_poke = x["poke"] and y["poke"] and x.get("dir") == y.get("dir")
        t[(x["kind"], "base %d" % x["base"], "poked on both, same dir" if same_poke else "pokes differ",
           "original " + (x.get('how') or '-'), "option " + (y.get('how') or '-'))] += 1
    for k, v in sorted(t.items()):
        print(k, v)
    dirs = Counter((y["kind"], y.get("dir"), y.get("how"), x.get("how")) for x, y in zip(a, b) if y["poke"])
    print("by the option's poke direction (kind, dir, option, original):")
    for k, v in sorted(dirs.items(), key=str):
        print("  ", k, v)
    print("where the puck was (x, how far in front) when the option's stick knocked it loose:",
          sorted(tuple(y["puck"]) for y in b if y.get("how") == "stick"))


def cvc(rom, games, out):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import menu_shots as M
    import snes_60fps_cvc as cvc_mod
    st = {"pokes": Counter(), "live": False}
    orig_emulator, orig_mem, orig_co = M.emulator, cvc_mod.Mem, cvc_mod.computer_only

    def emulator(r):
        e = orig_emulator(r)
        run = e.run

        def watched(n=1, **kw):
            run(n, **kw)
            m = st.get("m")
            if m is None or not st["live"]:
                return
            poke = (GPOKE + (SA1_SHIFT if getattr(m, "sa1", False) else 0)) & 0xFFFF
            for k in range(12):
                spa = m.w(SPA + 2 * k)
                if m.w(POSITION + 2 * k) == 0 and spa == poke and st["prev"][k] != poke:
                    pc = m.w(PUCKC)
                    if pc < 0x8000 and pc != 2 * k:
                        st["open"].append({"g": k, "age": 0, "loose": False, "next": None})
                st["prev"][k] = spa
            for o in st["open"]:
                o["age"] += 1
                pc = m.w(PUCKC)
                if o["age"] <= 22 and pc >= 0x8000:
                    o["loose"] = True
                if o["loose"] and o["next"] is None and pc < 0x8000:
                    o["next"] = ("the goalie" if pc == 2 * o["g"] else
                                 "his team" if m.w(PFTEAM + pc) == m.w(PFTEAM + 2 * o["g"]) else "the other team")
            for o in [o for o in st["open"] if o["age"] >= 120]:
                st["pokes"][("knocked loose, next: " + (o["next"] or "nobody")) if o["loose"] else "missed"] += 1
                st["open"].remove(o)
        e.run = watched
        return e

    class Mem(orig_mem):
        def __init__(self, e, r):
            super().__init__(e, r)
            st["m"] = self

    def computer_only(m):
        orig_co(m)
        st["live"] = True
    M.emulator, cvc_mod.Mem, cvc_mod.computer_only = emulator, Mem, computer_only
    for n in range(games):
        st.update(live=False, prev=[0] * 12, open=[])
        cvc_mod.game(rom, n, lambda e, m: {})
        print(n, dict(st["pokes"]), flush=True)
    (out / f"cvc_{Path(rom).stem}.json").write_text(json.dumps(dict(st["pokes"])))


def main():
    if sys.argv[1] == "--one":
        run_trials(sys.argv[2], Path(sys.argv[3]), sys.argv[4])
        return
    lowload.gentle()
    if sys.argv[1] == "trials":
        out = Path(sys.argv[4])
        out.mkdir(parents=True, exist_ok=True)
        trials(sys.argv[2], sys.argv[3], out)
    else:
        out = Path(sys.argv[4])
        out.mkdir(parents=True, exist_ok=True)
        cvc(sys.argv[2], int(sys.argv[3]), out)


if __name__ == "__main__":
    main()
