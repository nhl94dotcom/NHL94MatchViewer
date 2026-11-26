"""NOSE4Web's "Offer only these teams in the menu" on a Genesis season ROM (2026-11-26: nhl94_1987_88.bin, 21 teams
of 1987-88 and two All-Star teams offered, five moved behind them and not offered).

  teams ROM OUT OFFERED      Game Setup's Home and Visitor lines: RIGHT pressed 2 x OFFERED + 4 times, then LEFT as
                             often, the team word (Opt1team $D04C / Opt2team $D04E) after each press: the order,
                             the wrap, any number at or past OFFERED; a screenshot of each Home choice (OUT/home_NN.png)
                             with the ROM's name for that number.
  draws ROM OUT OFFERED N    the playoff draws: the ROM's draw table found by the tree the game shows (New Playoffs
                             started N times at different waits: the 16 team numbers of the tree read from RAM as
                             the bytes the screen's team blocks were built from are not known, the tree is kept as a
                             screenshot each time, OUT/tree_NN.png) and, from the ROM, every run of 16 distinct
                             bytes below OFFERED that repeats as a table of 16-byte rows: rows, teams used, any
                             row with a team twice or a number not offered.
  screens ROM OUT [SECONDS]  a computer game played SECONDS of clock and paused (gen_toi_page_check.play), then from
                             the pause menu each item opened with C (OUT/item_N.png) and, for the stats pages and
                             Edit Lines, their pages (RIGHT / A / DOWN: OUT/item_N_pNN.png); the two teams' rosters
                             from the ROM printed beside, for reading the names and numbers against the pictures.

python gen_offer_teams_check.py teams|draws|screens ROM OUT ..."""
import sys
from collections import Counter
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from systems import genesis  # noqa: E402

TEAM1, TEAM2, ITEM = 0xD04C, 0xD04E, 0xCF20


def press(e, b):
    e.run(4, hold=[b])
    e.run(26)


def teams(rom, out, offered):
    names = genesis.read_teams(Path(rom))
    print("teams in the ROM:", len(names), [(i, t["abbr"]) for i, t in enumerate(names)])
    e = Emu(rom)
    G.to_setup(e, out)
    press(e, "DOWN"); press(e, "DOWN")
    for line, addr in (("home", TEAM1), ("visitor", TEAM2)):
        seq = {"RIGHT": [e.w(addr)], "LEFT": []}
        for k in range(2 * offered + 4):
            before = e.w(addr)
            for _ in range(4):
                press(e, "RIGHT")
                if e.w(addr) != before:
                    break
            seq["RIGHT"].append(e.w(addr))
            if line == "home" and k < offered:
                e.run(40)
                v = e.w(addr)
                e.screenshot(out / f"home_{v:02d}.png")
        seq["LEFT"].append(e.w(addr))
        for k in range(2 * offered + 4):
            before = e.w(addr)
            for _ in range(4):
                press(e, "LEFT")
                if e.w(addr) != before:
                    break
            seq["LEFT"].append(e.w(addr))
        for d in ("RIGHT", "LEFT"):
            s = seq[d]
            steps = Counter((b - a) % offered for a, b in zip(s, s[1:]))
            print(f"{line} line, {d}: {s}")
            print(f"   distinct {len(set(s))}, highest {max(s)}, any at or past {offered}: {any(v >= offered for v in s)}, "
                  f"steps (mod {offered}): {dict(steps)}")
        press(e, "DOWN")
    print("offered by number:", [(i, names[i]["name"]) for i in range(min(offered, len(names)))])
    print("behind them:", [(i, names[i]["name"]) for i in range(offered, len(names))])


def draws(rom, out, offered, n):
    data = Path(rom).read_bytes()
    names = genesis.read_teams(Path(rom))
    # tables of 16-byte rows, each row 16 distinct team numbers: three rows running or more
    found = []
    i = 0
    while i < len(data) - 48:
        k = 0
        while i + 16 * (k + 1) <= len(data):
            row = data[i + 16 * k:i + 16 * k + 16]
            if len(set(row)) != 16 or max(row) >= len(names):
                break
            k += 1
        if k >= 8:
            found.append((i, k))
            i += 16 * k
        else:
            i += 1
    for at, k in found:
        rows = [list(data[at + 16 * j:at + 16 * j + 16]) for j in range(k)]
        bad = [(j, r) for j, r in enumerate(rows) if max(r) >= offered or len(set(r)) != 16]
        used = Counter(t for r in rows for t in r)
        print(f"table at ${at:06X}: {k} rows of 16; rows with a team at or past {offered} or a team twice: {len(bad)} {bad[:3]}")
        print("   teams used (number: rows):", dict(sorted(used.items())))
        print("   never drawn:", [(t, names[t]["name"]) for t in range(len(names)) if t not in used])
        print("   row 1:", " | ".join(f"{t + 1} {names[t]['name']}" for t in rows[0]))
        print("   row 2:", " | ".join(f"{t + 1} {names[t]['name']}" for t in rows[1]))
        (out / f"draws_{at:06X}.txt").write_text("\n".join(" ".join(str(t + 1) for t in r) for r in rows))
    for j in range(n):
        e = Emu(rom)
        e.run(900 + 137 * j)
        e.run(4, hold=["START"]); e.run(120)
        e.run(4, hold=["START"]); e.run(320)
        e.setw(G.PLAYMODE, 2)
        for _ in range(6):
            press(e, "RIGHT")                              # Play Mode to New Playoffs by the pad as well
            if e.w(G.PLAYMODE) in (1, 2, 3):
                break
        pm = e.w(G.PLAYMODE)
        e.run(4, hold=["START"]); e.run(400)
        e.screenshot(out / f"tree_{j:02d}.png")
        e.run(4, hold=["START"]); e.run(300)
        e.screenshot(out / f"tree_{j:02d}_next.png")
        print(f"start {j}: play mode word {pm}, team words after the tree {e.w(TEAM1)} / {e.w(TEAM2)}", flush=True)


def screens(rom, out, seconds):
    import gen_toi_page_check as T
    names = genesis.read_teams(Path(rom))
    if not (out / "paused.state").exists():
        T.play(rom, out, seconds)
    e = Emu(rom)
    e.unserialize((out / "paused.state").read_bytes())
    ids = [e.b(0xC6F7), e.b(0xCA5B)]
    for t in ids:
        print(names[t]["name"], [(p["num"], p["name"], "G" if p.get("g") else "") for p in names[t]["players"]])
    base = e.serialize()
    e.screenshot(out / "pause_menu.png")
    seen_items = []
    for _ in range(14):
        it = e.w(ITEM)
        if it in seen_items:
            break
        seen_items.append(it)
        press(e, "DOWN")
    print("pause menu items (the item word going down):", seen_items)
    for it in seen_items:
        e.unserialize(base)
        for _ in range(20):
            if e.w(ITEM) == it:
                break
            press(e, "DOWN")
        e.run(20)
        e.screenshot(out / f"item_{it}_menu.png")
        press(e, "C")
        e.run(240)
        e.screenshot(out / f"item_{it}.png")
        first = e.screenshot  # noqa: F841
        for k in range(1, 9):                               # its pages to the right
            press(e, "RIGHT")
            e.run(90)
            e.screenshot(out / f"item_{it}_right{k:02d}.png")
        press(e, "A")
        e.run(120)
        e.screenshot(out / f"item_{it}_a.png")
        e.run(200, hold=["DOWN"])
        e.run(30)
        e.screenshot(out / f"item_{it}_a_down.png")
    print("done", out)


def main():
    mode, rom, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    if mode == "teams":
        teams(rom, out, int(sys.argv[4]))
    elif mode == "draws":
        draws(rom, out, int(sys.argv[4]), int(sys.argv[5]) if len(sys.argv) > 5 else 3)
    else:
        screens(rom, out, int(sys.argv[4]) if len(sys.argv) > 4 else 240)


if __name__ == "__main__":
    main()
