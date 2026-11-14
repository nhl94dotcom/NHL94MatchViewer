"""NOSE4Web's Genesis giveaways and takeaways, stage 1 (2026-11-14: nhl94_giveaways.bin, CDL_Season_12_giveaways.bin),
against the converter's (tools/export_match.py find_turnovers, whose definitions the build follows).

The build's RAM: LASTC $FFE800, CAUSE $FFE802 ($FFFF none); giveaways $FFE810 and takeaways $FFE850, a byte per
roster place, 32 a team, home first; team totals at team struct + $2232 / $2234 (home $FFE900 / $FFE902, visitors
$FFEC64 / $FFEC66).

  games ROM OUT N [FIRST]   cvc_record's computer games (its matchups, seeds, league settings), every frame watched:
                            each change of a count logged (frame, period, clock, team, place, kind, and whether
                            another game's highlight was on: the team ids, gmode's gmhl); each game converted, and
                            the ROM's counts compared with the converter's, per player, per team and event by event
                            (a ROM count and a converter turnover of the same kind, team and player within 1 s real)
  shootout ROM OUT          a game in play, regular season, overtime with 3 s left at 1-1 (gen_shootout_check's
                            'tie'): the counts through the season shootout (gmode2 $C2FA bit 0, the build's $FFF082)
  pair OUT ROM              the games already recorded in OUT converted again (today's converter) and paired again
  highlights ROM OUT        a whole computer game, START only after 5 s (real) at a menu (the intermission highlights
                            play): every count change, and any during another game's highlight
  stats ROM OUT             Game Stats from the pause menu with penalties on and off: the top and, scrolled to the
                            end, the bottom (screenshots), with the counts set to known values first

python gen_giveaways_check.py games|shootout|stats ..."""
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import lowload

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))

LASTC, CAUSE, GIVE, TAKE = 0xE800, 0xE802, 0xE810, 0xE850
TOTALS = {(0, "give"): 0xE900, (0, "take"): 0xE902, (1, "give"): 0xEC64, (1, "take"): 0xEC66}
TEAMS, GMODE, GMODE2, SO_FLAG = (0xC6F7, 0xCA5B), 0xC2EA, 0xC2FA, 0xF082
GSP, CLOCK, SCREEN = 0xC466, 0xC468, 0xFFF7


def counts(e):
    """{(team, kind, place): n} of the non-zero bytes."""
    out = {}
    for kind, base in (("give", GIVE), ("take", TAKE)):
        for i in range(64):
            v = e.b(0xFF0000 | (base + i))
            if v:
                out[(i // 32, kind, i % 32)] = v
    return out


class Watch:
    def __init__(self):
        self.ours, self.prev, self.events, self.bad = None, {}, [], []
        self.raw = None
        self.trace = []

    def __call__(self, e, frame):
        if self.ours is None and e.b(SCREEN) == 0:
            self.ours = tuple(e.b(a) for a in TEAMS)
        lc = (e.w(0xFF0000 | LASTC), e.w(0xFF0000 | CAUSE), e.w(0xB7AA))
        if lc != getattr(self, "lc", None):      # LASTC, CAUSE and puckc: every change, for tracing
            self.lc = lc
            self.trace.append((frame, *lc))
        raw = bytes(e.ram[GIVE:GIVE + 0x80])
        if raw == self.raw:
            return
        self.raw = raw
        now = counts(e)
        hl = self.ours is not None and (tuple(e.b(a) for a in TEAMS) != self.ours or e.b(GMODE) & 0x10)
        for key in set(now) | set(self.prev):
            d = now.get(key, 0) - self.prev.get(key, 0)
            if d:
                ev = {"frame": frame, "period": e.w(GSP), "clock": e.w(CLOCK), "team": key[0], "kind": key[1],
                      "place": key[2], "delta": d, "highlight": bool(hl), "shootout": bool(e.b(GMODE2) & 1)}
                self.events.append(ev)
                if hl or ev["shootout"] or d < 0:
                    self.bad.append(ev)
        self.prev = now


def converter_events(js):
    import season
    m = season.load_match(js)
    out = []
    for tv in m.get("turnovers", []):
        f = tv["f"]
        frame = round(m["t"][f] * 60 / 1000)
        if tv.get("kind") == "giveaway" and tv.get("giver", -1) >= 0:
            out.append({"frame": frame, "team": tv["from"], "kind": "give", "place": tv["giver"], "how": tv.get("how")})
        elif tv.get("kind") == "takeaway" and tv.get("by", -1) is not None and tv.get("by", -1) >= 0:
            out.append({"frame": frame, "team": 1 - tv["from"], "kind": "take", "place": tv["by"], "how": tv.get("how")})
    other = Counter(tv.get("kind") for tv in m.get("turnovers", []))
    return out, other, m


def pair(rom_ev, conv_ev, window=60):
    """Each ROM count with the nearest unpaired converter event of the same team, kind and player within window."""
    used, matched, rom_only = set(), [], []
    for r in rom_ev:
        best = None
        for k, c in enumerate(conv_ev):
            if k in used or (c["team"], c["kind"], c["place"]) != (r["team"], r["kind"], r["place"]):
                continue
            d = abs(c["frame"] - r["frame"])
            if d <= window and (best is None or d < best[0]):
                best = (d, k)
        if best:
            used.add(best[1])
            matched.append((r, conv_ev[best[1]]))
        else:
            rom_only.append(r)
    conv_only = [c for k, c in enumerate(conv_ev) if k not in used]
    return matched, rom_only, conv_only


def pair_again(out, rom):
    """Every game already recorded in OUT converted again (today's converter) and paired with its ROM events."""
    tot = Counter()
    how = Counter()
    for ev_file in sorted(out.glob("cvc_genesis_*_rom_events.json")):
        name = ev_file.name.replace("_rom_events.json", "")
        folder = out / "captures" / name
        subprocess.run([sys.executable, str(ROOT / "tools" / "export_match.py"), str(folder), "--rom", rom,
                        "--out", str(out / "matches")],
                       capture_output=True, text=True)
        events = json.loads(ev_file.read_text())
        rom_ev = [dict(ev, delta=1) for ev in events if ev["delta"] > 0 and not ev["highlight"] and not ev["shootout"]
                  for _ in range(ev["delta"])]
        conv_ev, other, m = converter_events(out / "matches" / f"{name}.js")
        matched, rom_only, conv_only = pair(rom_ev, conv_ev)
        print(f"{name}: ROM {len(rom_ev)}, converter {len(conv_ev)}; paired {len(matched)}, ROM only {len(rom_only)}, "
              f"converter only {len(conv_only)}", flush=True)
        tot.update(rom=len(rom_ev), conv=len(conv_ev), paired=len(matched), rom_only=len(rom_only), conv_only=len(conv_only))
        how.update("paired " + c["how"] for _, c in matched)
        how.update("converter only " + c["how"] for c in conv_only)
        how.update("ROM only " + r["kind"] for r in rom_only)
    print("all:", dict(tot))
    for k, v in sorted(how.items()):
        print(f"  {k}: {v}")


def games(rom, out, n, first):
    import cvc_record
    lowload.gentle()
    (out / "matches").mkdir(parents=True, exist_ok=True)
    tot = defaultdict(Counter)
    for g in range(first, first + n):
        w = Watch()
        folder = cvc_record.one("genesis", rom, g, out, w)
        if not folder:
            print(f"game {g}: never reached play")
            continue
        c = subprocess.run([sys.executable, str(ROOT / "tools" / "export_match.py"), str(folder), "--rom", rom,
                            "--out", str(out / "matches")], capture_output=True, text=True)
        js = out / "matches" / f"{folder.name}.js"
        if not js.exists():
            print(f"game {g}: not converted: {(c.stdout + c.stderr)[-300:]}")
            continue
        rom_ev = [ev for ev in w.events if ev["delta"] > 0 and not ev["highlight"] and not ev["shootout"]]
        rom_ev = [dict(ev, delta=1) for ev in rom_ev for _ in range(ev["delta"])]
        conv_ev, other, m = converter_events(js)
        matched, rom_only, conv_only = pair(rom_ev, conv_ev)
        final = w.prev
        per_team = {(t, k): sum(v for (tt, kk, _), v in final.items() if (tt, kk) == (t, k)) for t in (0, 1) for k in ("give", "take")}
        conv_team = Counter((c["team"], c["kind"]) for c in conv_ev)
        print(f"game {g} ({folder.name}): ROM counts {len(rom_ev)}, converter {len(conv_ev)} (dump-ins {other.get('dump-in', 0)});"
              f" paired {len(matched)}, ROM only {len(rom_only)}, converter only {len(conv_only)}; "
              f"increments in a highlight / shootout / negative: {len(w.bad)}", flush=True)
        print("   per team (home give, home take, away give, away take): ROM "
              f"{[per_team[(0, 'give')], per_team[(0, 'take')], per_team[(1, 'give')], per_team[(1, 'take')]]}, converter "
              f"{[conv_team[(0, 'give')], conv_team[(0, 'take')], conv_team[(1, 'give')], conv_team[(1, 'take')]]}", flush=True)
        for r in rom_only[:8]:
            print(f"   ROM only: {r}", flush=True)
        for cev in conv_only[:8]:
            print(f"   converter only: {cev}", flush=True)
        tot["all"].update(rom=len(rom_ev), conv=len(conv_ev), paired=len(matched), rom_only=len(rom_only),
                          conv_only=len(conv_only), bad=len(w.bad))
        tot["conv_only_how"].update(cev["how"] for cev in conv_only)
        tot["paired_how"].update(cv["how"] for _, cv in matched)
        (out / f"{folder.name}_rom_events.json").write_text(json.dumps(w.events))
        (out / f"{folder.name}_trace.json").write_text(json.dumps(w.trace))
    print("all games:", dict(tot["all"]))
    print("paired, by the converter's how:", dict(tot["paired_how"]))
    print("converter only, by how:", dict(tot["conv_only_how"]))


def stats(rom, out):
    """Game Stats with penalties on (OptPen $FFD056 = 1) and off (0): the totals set to known values (home 12 / 7,
    visitors 9 / 11), the page's top and, after holding DOWN, its bottom."""
    import gen_ot_check as G
    from emu import Emu
    out.mkdir(parents=True, exist_ok=True)
    for pen in (1, 0):
        e = Emu(rom)
        G.to_setup(e, out)
        e.setw(0xD056, pen)
        if not G.into_play(e):
            print("never reached play")
            return
        e.run(300)
        for (t, k), a, v in ((key, TOTALS[key], val) for key, val in
                             (((0, "give"), 12), ((0, "take"), 7), ((1, "give"), 9), ((1, "take"), 11))):
            e.setw(0xFF0000 | a, v)
        G.press(e, "START")
        e.run(60)
        for _ in range(30):
            if e.w(0xCF20) == 4:
                break
            G.press(e, "DOWN")
        G.press(e, "C")
        e.run(240)
        e.screenshot(out / f"stats_pen{pen}_top.png")
        e.run(300, hold=["DOWN"])
        e.run(30)
        e.screenshot(out / f"stats_pen{pen}_bottom.png")
        print(f"penalties {'on' if pen else 'off'}: scroll limit (matchupvis) {e.w(0xD59E):#x}", flush=True)


def play_watched(rom, out, setup=None, start_wait=300, max_frames=60 * 60 * 40, until=None, pre=None):
    """A computer game (5-minute periods, the pads let go every second, START at a menu that has waited
    start_wait frames: long enough for the intermission highlights) with Watch on every frame. setup(e) once in
    play; until(e) ends it."""
    import gen_ot_check as G
    from emu import Emu
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(0xD050, 0)
    if pre:
        pre(e)
    if not G.into_play(e):
        return None, None
    if setup:
        setup(e)
    w = Watch()
    still, last, info = 0, None, Counter()
    for f in range(max_frames):
        if f % 60 == 0:
            e.setw(0xC328, 0)
            e.setw(0xC32A, 0)
            for k in range(12):
                e.setb(0xB04A + 0x80 * k + 0x62, e.b(0xB04A + 0x80 * k + 0x62) & ~8)
            if f % 3600 == 0:
                lowload.breathe()
        c = e.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        e.run(1, hold=["START"] if still >= start_wait and f % 150 < 4 and e.b(SCREEN) != 0 else [])
        w(e, f)
        if w.ours and tuple(e.b(a) for a in TEAMS) != w.ours:
            info["frames of another game's highlight"] += 1
        if e.b(GMODE2) & 1:
            info["frames with gmode2 bit 0 (shootout)"] += 1
        if e.w(0xFF0000 | SO_FLAG):
            info["frames with the build's shootout flag $FFF082"] += 1
        if until and until(e):
            break
        if e.w(GSP) >= 4:
            info["game over seen"] = 1
        if e.w(GSP) >= 4 and e.b(SCREEN) != 0 and still > 600:
            break
        if w.ours and e.b(SCREEN) == 0 and e.w(GSP) == 0 and info["game over seen"]:
            break                                     # the attract mode's demo game after ours
    return w, info


def highlights(rom, out):
    w, info = play_watched(rom, out)
    print(f"{dict(info)}; count changes {len(w.events)}, in a highlight / shootout / negative {len(w.bad)}", flush=True)
    for ev in w.bad[:10]:
        print("  ", ev)


def shootout(rom, out):
    def setup(e):
        e.setw(0xD048, 0)                           # regular season
        e.setw(GSP, 3)                              # overtime, 3 s left, 1-1
        e.setw(CLOCK, 3)
        e.setw(0xC6DA, 1)
        e.setw(0xCA3E, 1)
    w, info = play_watched(rom, out, setup, start_wait=150, max_frames=60 * 60 * 15)
    print(f"{dict(info)}; count changes {len(w.events)}, in a highlight / shootout / negative {len(w.bad)}", flush=True)
    for ev in w.events[:20]:
        print("  ", ev)


def shootout_mode(rom, out):
    """The game's own Shootout mode (Play Mode 4 at Game Setup): gmode2 bit 0 set throughout; nothing should count."""
    w, info = play_watched(rom, out, pre=lambda e: e.setw(0xD048, 4), start_wait=150, max_frames=60 * 60 * 6,
                           until=lambda e: e.w(GSP) >= 4)
    if not w:
        print("never reached play (Shootout mode's menu waits for a pad's B with the computer on both sides)")
        return
    print(f"{dict(info)}; count changes {len(w.events)}", flush=True)
    for ev in w.events[:10]:
        print("  ", ev)


def main():
    mode = sys.argv[1]
    if mode == "games":
        games(sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]) if len(sys.argv) > 5 else 0)
    elif mode == "pair":
        pair_again(Path(sys.argv[2]), sys.argv[3])
    elif mode == "highlights":
        highlights(sys.argv[2], Path(sys.argv[3]))
    elif mode == "shootout_mode":
        shootout_mode(sys.argv[2], Path(sys.argv[3]))
    elif mode == "shootout":
        shootout(sys.argv[2], Path(sys.argv[3]))
    elif mode == "stats":
        stats(sys.argv[2], Path(sys.argv[3]))
    else:
        raise SystemExit(f"{mode}: not yet")


if __name__ == "__main__":
    main()
