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
  snes_games ROM OUT N [FIRST]   the same on NOSE4Web's SNES build (SnesWatch; the SA-1 build's counts in BW-RAM)
  shootout ROM OUT          a game in play, regular season, overtime with 3 s left at 1-1 (gen_shootout_check's
                            'tie'): the counts through the season shootout (gmode2 $C2FA bit 0, the build's $FFF082)
  pair OUT ROM              the games already recorded in OUT converted again (today's converter) and paired again
  highlights ROM OUT        a whole computer game, START only after 5 s (real) at a menu (the intermission highlights
                            play): every count change, and any during another game's highlight
  stats ROM OUT             Game Stats from the pause menu with penalties on and off: the top and, scrolled to the
                            end, the bottom (screenshots), with the counts set to known values first

  build RETAIL HACKS_TS OUT [--goalie-fix]   a scratch giveaways build: the hack's code from NOSE4Web's hacks.ts
                            (its first GT_VERSIONS entry) laid over RETAIL as apply() does; --goalie-fix adds the
                            suggested fix (a pass the goalie touches forgotten like a shot, at puckgoalie's $154EE)
  passshot ROM OUT [N]      passes at the net with nobody to pass to (pass shots), N trials from bot_live.state: what
                            became of each (goalie held, off the goalie, goal, picked off) and the counts it made

                            NHL94_PASS_CASE=zone: passes up the middle from the passer's own end or the neutral zone
                            with visitors in line; =dump: dump-ins from y 40-80 at the net, defencemen by the net
  snes_passshot ROM OUT [N]  the same on a SNES giveaways build (retail or SA-1): what became of each pass, the counts,
                            and NOSE4Web's at-the-net rule worked out at the release against what the build did

  genpass 94|95 ROM OUT N [STATE]   NOSE4Web's version 3 (a pass at the net marked $FFFD / $FFFC at the release,
                            cleared at the goal line, a goalie's touch or the net): both ends, NHL94_PASS_CASE net / slot
                            / post / wide / zone / dump / shot; each trial the rule against the mark, the clear, the first
                            pick-up and the counts; NHL '95 / W18 from gen95_assist_check's live STATE
  snespass ROM OUT N        the same on a SNES build (retail or SA-1)

python gen_giveaways_check.py games|shootout|stats|build|passshot|snes_passshot|genpass|snespass ..."""
import json
import math
import os
import re
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
GVBASE = 0xFD10        # NOSE4Web's SNES counts in bank $7E (not the SA-1): $E68C in the first builds, $FD10 since


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


class SnesWatch(Watch):
    """NOSE4Web's SNES build (2026-11-14; GVBASE: $7E:E68C in the first builds, $7E:FD10 since): last carrier +0, cause +2,
    giveaways +4 and takeaways +$6C (a
    word per roster player, the visitors at +$34), totals $E760; on the SA-1 the same from BW-RAM $40:5500."""
    def __call__(self, e, frame, m):
        def raw(off, n):
            if m.sa1:
                return bytes(m.bw[0x5500 + off:0x5500 + off + n])
            return bytes(e.ram[GVBASE + off:GVBASE + off + n])
        if self.ours is None and not m.w(0x15D8) & 0x0801:
            self.ours = (m.w(0x1C98), m.w(0x1C9A))
        lc = tuple(int.from_bytes(raw(o, 2), "little") for o in (0, 2)) + (m.w(0x0AD9),)
        if lc != getattr(self, "lc", None):
            self.lc = lc
            self.trace.append((frame, *lc))
        block = raw(4, 0xD0)
        if block == self.raw:
            return
        self.raw = block
        now = {}
        for kind, off in (("give", 0), ("take", 0x68)):
            for t in (0, 1):
                for pl in range(26):
                    v = block[off + 0x34 * t + 2 * pl] | block[off + 0x34 * t + 2 * pl + 1] << 8
                    if v:
                        now[(t, kind, pl)] = v
        hl = self.ours is not None and ((m.w(0x1C98), m.w(0x1C9A)) != self.ours or m.w(0x15D4) & 0x10)
        for key in set(now) | set(self.prev):
            d = now.get(key, 0) - self.prev.get(key, 0)
            if d:
                ev = {"frame": frame, "period": m.w(0x1630), "clock": m.w(0x1632), "team": key[0], "kind": key[1],
                      "place": key[2], "delta": d, "highlight": bool(hl), "shootout": False}
                self.events.append(ev)
                if hl or d < 0:
                    self.bad.append(ev)
        self.prev = now


def converter_events(js):
    import season
    m = season.load_match(js)
    out = []
    for tv in m.get("turnovers", []):
        f = tv["f"]
        frame = round(m["t"][f] * 60 / 1000)
        pc = {"period": m["period"][f], "clock": m["clock"][f]}
        if tv.get("kind") == "giveaway" and tv.get("giver", -1) >= 0:
            out.append({"frame": frame, "team": tv["from"], "kind": "give", "place": tv["giver"], "how": tv.get("how"), **pc})
        elif tv.get("kind") == "takeaway" and tv.get("by", -1) is not None and tv.get("by", -1) >= 0:
            out.append({"frame": frame, "team": 1 - tv["from"], "kind": "take", "place": tv["by"], "how": tv.get("how"), **pc})
    other = Counter(tv.get("kind") for tv in m.get("turnovers", []))
    return out, other, m


def pair(rom_ev, conv_ev, window=60, by_clock=False):
    """Each ROM count with the nearest unpaired converter event of the same team, kind and player within window
    frames (by_clock: the same period and within 2 game seconds: the SNES converter closes up pauses in its times)."""
    used, matched, rom_only = set(), [], []
    for r in rom_ev:
        best = None
        for k, c in enumerate(conv_ev):
            if k in used or (c["team"], c["kind"], c["place"]) != (r["team"], r["kind"], r["place"]):
                continue
            if by_clock:
                if c.get("period") != r.get("period") or abs(c["clock"] - r["clock"]) > 2:
                    continue
                d = abs(c["clock"] - r["clock"])
                if best is None or d < best[0]:
                    best = (d, k)
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
    for ev_file in sorted(out.glob("cvc_*_rom_events.json")):
        name = ev_file.name.replace("_rom_events.json", "")
        folder = out / "captures" / name
        subprocess.run([sys.executable, str(ROOT / "tools" / "export_match.py"), str(folder), "--rom", rom,
                        "--out", str(out / "matches")],
                       capture_output=True, text=True)
        events = json.loads(ev_file.read_text())
        rom_ev = [dict(ev, delta=1) for ev in events if ev["delta"] > 0 and not ev["highlight"] and not ev["shootout"]
                  for _ in range(ev["delta"])]
        conv_ev, other, m = converter_events(out / "matches" / f"{name}.js")
        matched, rom_only, conv_only = pair(rom_ev, conv_ev, by_clock="snes" in name)
        print(f"{name}: ROM {len(rom_ev)}, converter {len(conv_ev)}; paired {len(matched)}, ROM only {len(rom_only)}, "
              f"converter only {len(conv_only)}", flush=True)
        tot.update(rom=len(rom_ev), conv=len(conv_ev), paired=len(matched), rom_only=len(rom_only), conv_only=len(conv_only))
        how.update("paired " + c["how"] for _, c in matched)
        how.update("converter only " + c["how"] for c in conv_only)
        how.update("ROM only " + r["kind"] for r in rom_only)
    print("all:", dict(tot))
    for k, v in sorted(how.items()):
        print(f"  {k}: {v}")


def games(rom, out, n, first, system="genesis"):
    import cvc_record
    lowload.gentle()
    (out / "matches").mkdir(parents=True, exist_ok=True)
    tot = defaultdict(Counter)
    for g in range(first, first + n):
        w = Watch() if system == "genesis" else SnesWatch()
        folder = cvc_record.one(system, rom, g, out, w)
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
        matched, rom_only, conv_only = pair(rom_ev, conv_ev, by_clock=system == "snes")
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


def snes_highlights(rom, out):
    """A whole SNES playoff game (Play Mode 2 in RAM: other games' highlights play only in the playoffs), START only
    after 150 s (real) at a stopped clock (the intermission's highlights come after its ticker), SnesWatch every frame:
    any count change during a highlight (gmode's gmhl, or the score box's teams not ours)."""
    import menu_shots as M
    import snes_60fps_cvc as cvc
    import snes_skate_marks_check as SK
    out.mkdir(parents=True, exist_ok=True)
    e = M.emulator(rom)
    m = cvc.Mem(e, rom)
    tmp = out / "_menu"
    if m.sa1:
        M.play(e, "w1800 START w240", tmp)
    else:
        M.play(e, "w1500 START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
    m.setw(0x34BC, 2)
    M.play(e, "START w240 START w200 w2400", tmp)
    for _ in range(12):
        c = m.w(0x1632)
        e.run(240)
        if m.w(0x1632) != c and m.w(0x15D6) == 0:
            break
        SK.press(e, "START", 60)
    cvc.computer_only(m)
    w = SnesWatch()
    still, last, hl_frames = 0, None, 0
    for f in range(60 * 60 * 45):
        if f % 300 == 0:
            cvc.computer_only(m)
            if f % 3600 == 0:
                lowload.breathe()
        c = m.w(0x1632)
        still = still + 1 if c == last else 0
        last = c
        e.run(1, hold=["START"] if still >= 9000 and f % 150 < 4 else [])
        if m.w(0x1632) > 300 and m.w(0x1630) < 3:
            m.setw(0x1632, 300)
        w(e, f, m)
        if w.ours and ((m.w(0x1C98), m.w(0x1C9A)) != w.ours or m.w(0x15D4) & 0x10):
            hl_frames += 1
        if m.w(0x1630) >= 4:
            break
    print(f"play mode {m.w(0x34BC)}; frames of another game's highlight {hl_frames}; count changes {len(w.events)}, "
          f"in a highlight or negative {len(w.bad)}", flush=True)
    for ev in w.bad[:10]:
        print("  ", ev)


def snes_stats(rom, out, item=2):
    """SNES Game Stats with penalties on (OptPen $34C4 = 2) and off (0): the four totals set (home giveaways 12,
    visitors' 9, home takeaways 7, visitors' 11), the pause menu's item ITEM, the top and, holding DOWN, the bottom."""
    import menu_shots as M
    import snes_60fps_cvc as cvc
    import snes_skate_marks_check as SK
    out.mkdir(parents=True, exist_ok=True)
    for pen in (2, 0):
        e = M.emulator(rom)
        m = cvc.Mem(e, rom)
        tmp = out / "_menu"
        if m.sa1:
            M.play(e, "w1800 START w240", tmp)
        else:
            M.play(e, "w1500 START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
        m.setw(0x34BC, 0)                          # Play Mode: regular season (a lost press can leave Password)
        M.play(e, "START w240 START w200 w2400", tmp)
        for _ in range(12):
            c = m.w(0x1632)
            e.run(240)
            if m.w(0x1632) != c and m.w(0x15D6) == 0:
                break
            SK.press(e, "START", 60)
        m.setw(0x34C4, pen)
        cvc.computer_only(m)
        e.run(300)
        for k, v in enumerate((12, 9, 7, 11)):
            if m.sa1:
                m.bw[0x55D4 + 2 * k], m.bw[0x55D4 + 2 * k + 1] = v, 0
            else:
                e.ram[GVBASE + 0xD4 + 2 * k], e.ram[GVBASE + 0xD4 + 2 * k + 1] = v, 0
        SK.press(e, "START", 90)
        for _ in range(40):
            if e.w(0x0D15) == item:
                break
            SK.press(e, "DOWN")
        SK.press(e, "A", 300)
        e.screenshot(out / f"stats_pen{pen}_top.png")
        e.run(400, hold=["DOWN"])
        e.run(60)
        e.screenshot(out / f"stats_pen{pen}_bottom.png")
        print(f"penalties {'on' if pen else 'off'}: done", flush=True)


# ---------------------------------------------------------------- pass shots (2026-11-18, NOSE4Web's question)
GT_HOOKS = ((0x15288, 0, 8), (0x151BC, 4, 6), (0x15548, 4, 6), (0x143FA, 8, 10), (0xC340, 0xC, 6), (0x77B8, 0x10, 8),
            (0xFDE5E, 0x14, 6), (0xFDE6C, 0x18, 8), (0xBC6E, 0x1C, 10))
GT_LIMITS = ((0xFDCBC, 0x80), (0xFDCCA, 0x40))


GOALIE_TOUCH_FIX = bytes.fromhex("08B80002C2F4" "0C78FFFEE802" "6606" "31FCFFFFE800" "4E75")


def lay_giveaways(retail, hacks_ts, out, at=0xFFB14, goalie_fix=False):
    """A scratch build: NOSE4Web's giveaways code (the first GT_VERSIONS entry of its hacks.ts, given at run time) with
    the ROM's two Game Stats tables and the new row after each, laid at `at` (free room in the retail ROM) and hooked
    as its apply() does (jsr abs.l, the rest NOPs; the scroll limits)."""
    import struct
    rom = bytearray(Path(retail).read_bytes())
    ts = Path(hacks_ts).read_text(encoding="utf-8")
    m = re.search(r"const GT_VERSIONS[^=]*=\s*\[\s*\{ code: bytes\('([0-9A-Fa-f ]+)'\), tableA: (0x[0-9a-f]+), tableB: (0x[0-9a-f]+)", ts)
    body, ta, tb = bytes.fromhex(m.group(1).replace(" ", "")), int(m.group(2), 16), int(m.group(3), 16)

    def table(a, rows):
        end = a
        for _ in range(rows):
            end += struct.unpack_from(">H", rom, end)[0] + 4
        return bytes(rom[a:end])
    row = struct.pack(">H", 16) + b"Give/Takeaways" + bytes.fromhex("22322234")
    wp, np_ = table(0xFDFAA, 15), table(0xFE098, 11)
    code = bytearray(body + wp + row + np_ + row)
    struct.pack_into(">H", code, ta, len(body) - ta)
    struct.pack_into(">H", code, tb, len(body) + len(wp) + len(row) - tb)
    assert all(b in (0xFF,) for b in rom[at - 4:at + len(code)]), "no room"
    rom[at:at + len(code)] = code
    for site, entry, n in GT_HOOKS:
        rom[site:site + 6] = bytes.fromhex("4EB9") + struct.pack(">I", at + entry)
        for o in range(6, n, 2):
            rom[site + o:site + o + 2] = bytes.fromhex("4E71")
    for site, v in GT_LIMITS:
        struct.pack_into(">H", rom, site, v)
    if goalie_fix:      # the suggested fix: puckgoalie's bclr #2,(sflags4).w ($154EE, every touch, holds too): a pass
        fx = at + len(code) + 4                  # the goalie touches is a shot (the carrier forgotten, as doshot's)
        assert rom[0x154EE:0x154F4] == bytes.fromhex("08B80002C2F4") and all(b == 0xFF for b in rom[fx:fx + 24])
        rom[fx:fx + len(GOALIE_TOUCH_FIX)] = GOALIE_TOUCH_FIX
        rom[0x154EE:0x154F4] = bytes.fromhex("4EB9") + struct.pack(">I", fx)
    Path(out).write_bytes(bytes(rom))
    return out


CASE = os.environ.get("NHL94_PASS_CASE", "net")     # passshot: net (passes at the net), zone, dump


def passshot(rom, out, n=24):
    """Passes at the net, played on a giveaways build: bot_live.state (open play, the home team attacking up), the
    home centre with the puck in the slot on pad 1, a teammate behind the net in line with it, the other home
    skaters back at their own blue line, two visiting defencemen by the posts; UP and B (a pass to the man behind the
    net, through the crease), then up to 900 frames (after a goal on through the next faceoff and 600 frames more).
    Per trial: what happened to the pass (the goalie's touches: his no-touch timer set to $A by puckgoalie; puckc;
    the score), every LASTC / CAUSE / puckc change and every count change."""
    from emu import Emu
    from paths import WORK
    from bot import rec
    from bot_scenario import reset_ai
    import random
    out.mkdir(parents=True, exist_ok=True)
    base = (WORK / "bot_live.state").read_bytes()
    rng = random.Random(7)
    e = Emu(str(rom))
    results = []
    for t in range(n):
        e.unserialize(base)
        e.setw(0xC468, 250)
        e.setl(0xD066, rng.randrange(1 << 31))
        cx, cy = rng.choice((-30, -15, 0, 15, 30)), rng.choice((175, 195, 215))
        push = rng.choice((["UP"], ["UP"], ["UP", "LEFT"], ["UP", "RIGHT"]))   # at the net, or at a post
        rx = rng.choice((-25, -10, 0, 10, 25))
        near = t % 3 == 0                         # visiting defencemen by the posts (they take rebounds), or back
        place = {2: (cx, cy), 0: (60, -40), 1: (-60, -40), 3: (40, -60), 4: (-40, -60),
                 6: (-90, -20), 7: (90, -20), 8: (0, -10),
                 9: (-28, 238) if near else (-35, 60), 10: (28, 238) if near else (35, 60)}
        if CASE == "zone":      # a pass up the middle from the passer's own end or the neutral zone, two visitors in line
            cx, cy = rng.choice((-10, 0, 10)), rng.choice((-150, -100, -40, 20, 60))
            push = ["UP"]
            place = {2: (cx, cy), 0: (-90, cy - 40), 1: (90, cy - 40), 3: (40, cy - 80), 4: (-40, cy - 80),
                     6: (-100, cy + 30), 7: (100, cy + 30), 8: (cx, cy + 55), 9: (cx - 12, cy + 100), 10: (cx + 12, cy + 140)}
        elif CASE == "dump":    # a dump-in from outside the zone (y 40-80, the blue line at 88) at the net, the visiting
            cx, cy = rng.choice((-20, 0, 20)), rng.choice((40, 60, 80))     # defencemen by the net to collect it
            push = rng.choice((["UP"], ["UP", "LEFT"], ["UP", "RIGHT"]))
            place = {2: (cx, cy), 0: (-90, cy - 40), 1: (90, cy - 40), 3: (40, cy - 80), 4: (-40, cy - 80),
                     6: (-100, cy - 20), 7: (100, cy - 20), 8: (0, cy - 30), 9: (-30, 215), 10: (30, 215)}
        for k, (x, y) in place.items():
            r = rec(k)
            e.setw(r, x & 0xFFFF); e.setw(r + 2, 0); e.setw(r + 0x14, y & 0xFFFF); e.setw(r + 0x16, 0); e.setw(r + 0x18, 0)
            e.setl(r + 0x1C, (x & 0xFFFF) << 16); e.setl(r + 0x20, (y & 0xFFFF) << 16)
            e.setw(r + 0x28, 0); e.setw(r + 0x2A, 0); e.setw(r + 0x2C, 0)
            e.setb(r + 0x55, 0)
        for k in range(12):
            role = str(e.b(rec(k) + 0x35))
            if role in "012345":
                reset_ai(e, k, role, k < 6, k == 2)
        for k in range(6):
            e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
        e.setb(rec(2) + 0x62, e.b(rec(2) + 0x62) | 8)
        e.setw(0xC320, 2)
        pr = rec(14)
        e.setw(pr, cx & 0xFFFF); e.setw(pr + 0x14, cy & 0xFFFF); e.setw(pr + 0x18, 0)
        e.setw(0xB7AA, 2)
        e.setw(0xFF0000 | LASTC, 2); e.setb(0xFF0000 | 0xE804, e.b(rec(2) + 0x66))
        e.setw(0xFF0000 | CAUSE, 0xFFFF); e.setb(0xFF0000 | 0xE805, 0xFF)
        for a in range(0x80):
            e.setb(0xFF0000 | (GIVE + a), 0)
        e.run(4, hold=["UP"])
        score0 = (e.w(0xC6DA), e.w(0xCA3E))
        w = Watch()
        w.prev = counts(e)
        trace, touches, goal_at, fo_at, end = [], [], None, None, 900
        last = None
        gnp = e.b(rec(11) + 0x5E)
        mouth = None                               # the converter's test for a pass shot: it reached the goal mouth
        pick = None                                # where the puck was when the pass was first picked up
        path = []                                  # the puck every 4 frames until then
        for f in range(4000):
            e.run(1, hold=push + ["B"] if f < 3 else [])
            w(e, f)
            st = (e.w(0xFF0000 | LASTC), e.w(0xFF0000 | CAUSE), e.w(0xB7AA))
            if st != last:
                trace.append((f, *[x if x < 0x8000 else x - 0x10000 for x in st]))
                last = st
            if mouth is None and e.sw(0xB7AA) < 0 and e.sw(rec(14) + 0x14) >= 264 and abs(e.sw(rec(14))) <= 40:
                mouth = f                          # through the goal mouth: the goal line within PASS_MOUTH (40)
            if pick is None and len(trace) > 1 and trace[-1][3] >= 0 and trace[-1][0] == f:
                pick = (e.sw(rec(14)), e.sw(rec(14) + 0x14))
            if pick is None and f % 4 == 0:
                path.append((f, e.sw(rec(14)), e.sw(rec(14) + 0x14), e.sw(rec(14) + 0x18)))
            np_ = e.b(rec(11) + 0x5E)
            if np_ == 0x0A and gnp != 0x0A:
                touches.append(f)
            gnp = np_
            if goal_at is None and (e.w(0xC6DA), e.w(0xCA3E)) != score0:
                goal_at, end = f, 4000
            if goal_at is not None and fo_at is None and e.b(0xC2F0) & 0x10:
                fo_at, end = f, f + 600
            if f >= end:
                break
        first = next(((f, p) for f, _, _, p in trace[1:] if p >= 0), None)
        if goal_at is not None and (first is None or first[0] > goal_at):
            what = "goal"
        elif first is None:
            what = "unresolved"
        else:
            k = first[1]
            who = ("home " if k < 6 else "visitors' ") + ("goalie" if e.b(rec(k) + 0x35) == 0 else "skater")
            what = ("goalie touched, then " if any(x < first[0] for x in touches) else "") + who + " took it"
        pshot = goal_at is not None and what == "goal" or (first is not None and (
            (mouth is not None and mouth < first[0]) or any(x < first[0] for x in touches)))
        if what == "goal":                          # up to the first pickup after the next faceoff's drop
            resolved = next((f for f, _, _, p in trace if fo_at is not None and f >= fo_at and p >= 0), 4000)
        else:                                      # up to the first pickup of the pass
            resolved = first[0] if first else 4000
        early = [(ev["frame"], ev["team"], ev["kind"], ev["place"]) for ev in w.events if ev["frame"] <= resolved + 2]
        res = dict(trial=t, carrier=(cx, cy), near=near, what=what, pass_shot=pshot, picked_up_at=pick, path=path, counts_by_then=early, goal_at=goal_at, faceoff_drop_at=fo_at,
                   goalie_touches=touches[:6], trace=trace[:40], counts=w.events)
        results.append(res)
        print(t, "defence near" if near else "defence back", (cx, cy), "->", what, "(a pass shot)" if pshot else "(not at the net)", "at", pick, "| counts by then:", early,
              "| trace:", trace[:6], flush=True)
    (out / "passshot.json").write_text(json.dumps(results, indent=1))
    tally = Counter((r["what"], r["pass_shot"], bool(r["counts_by_then"])) for r in results)
    for (what, ps, counted), c in sorted(tally.items()):
        print(f"{c:3} {what}{' (a pass shot)' if ps else ''}: {'a count' if counted else 'no count'}")


# ------------------------------------------------- passes at the net, version 3 (2026-11-18: the slot pick-off kept)
GAMES = {
    "94": dict(base=0xB04A, puckc=0xB7AA, c1p=0xC320, c2p=0xC322, cont=(0xC328, 0xC32A), lastc=0xE800, cause=0xE802,
               lastp=0xE804, give=0xE810, seed=0xD066, clock=0xC468, team=(0xC6CE, 0xCA32), fo=(0xC2F0, 0x10),
               goal=0x108, blue=0x58, face=0x55),
    "95": dict(base=0xAC62, puckc=0xB3C2, c1p=0xBF44, c2p=0xBF46, cont=(0xBF4C, 0xBF4E), lastc=0xEA00, cause=0xEA02,
               lastp=0xEA04, give=0xEA10, seed=0xCC6A, clock=0xC022, team=(0xC288, 0xC5EE), fo=(0xBEF6, 0x10),
               goal=0x10B, blue=0x56, face=0x54),
}
PASS_END = os.environ.get("NHL94_PASS_END", "both")      # up (home on pad 1 at the top net), down (away on pad 2), both


def genpass(game, rom, out, n, state=None):
    """NOSE4Web's pass-at-the-net rule, version 3, played on a Genesis giveaways build of NHL '94 (bot_live.state) or
    NHL '95 / W18 (STATE: gen95_assist_check's live state, the ROM powered on first). The attacking side's centre has
    the puck (pad 1 home toward the top net, or pad 2 away toward the bottom one: both marks), the case (NHL94_PASS_CASE:
    net, slot, post, wide, zone, dump, shot) places the rest, B with the pad toward the net (C for 'shot'). Each trial:
    the rule worked out at the release from the puck's place and speed against the build's mark ($FFFD top, $FFFC
    bottom), when and where the mark was cleared (the goal line, by the goalie, else a post or the net front), who first
    took the puck, and the counts then, against the rule (a giveaway when the other team's skater takes a pass that was
    never marked, or is still marked). 'shot' counts the team's shots on goal (run it on the original too: same seeds)."""
    import random
    from emu import Emu
    G = GAMES[game]

    def rec(k):
        return G["base"] + k * 0x80
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(str(rom))
    if game == "95":
        e.run(1500)                               # powered on first: the states leave out save RAM
        base = Path(state).read_bytes()
    else:
        from paths import WORK
        base = (WORK / "bot_live.state").read_bytes()
    rng = random.Random(11)

    def W(a):
        return e.w(0xFF0000 | a)
    results = []
    for t in range(n):
        e.unserialize(base)
        e.setw(G["clock"], 250)
        e.setl(G["seed"], rng.randrange(1 << 31))
        down = PASS_END == "down" or (PASS_END == "both" and t % 2 == 1)
        s = -1 if down else 1
        A, D = (list(range(6, 12)), list(range(6))) if down else (list(range(6)), list(range(6, 12)))

        def role(team, p):
            return next(k for k in team if e.b(rec(k) + 0x35) == p)
        me, gk = role(A, 4), role(D, 0)
        dmen = [role(D, 1), role(D, 2)]
        others_a = [k for k in A if k != me and e.b(rec(k) + 0x35) not in (0, 0xFF)]
        others_d = [k for k in D if k not in dmen + [gk] and e.b(rec(k) + 0x35) != 0xFF]
        near = t % 3 == 0
        cx, cy = rng.choice((-30, -15, 0, 15, 30)), rng.choice((175, 195, 215))
        push = rng.choice((["UP"], ["UP"], ["UP", "LEFT"], ["UP", "RIGHT"]))
        dpos = [(-28, 238), (28, 238)] if near else [(-35, 60), (35, 60)]
        fwd = [(-90, -20), (90, -20), (0, -10)]
        mates = [(60, -40), (-60, -40), (40, -60), (-40, -60)]
        if CASE == "slot":                        # a defenceman in the slot between the passer and the net
            cx, cy, push = rng.choice((-15, 0, 15)), rng.choice((150, 170, 190)), ["UP"]
            dpos = [(cx + rng.choice((-6, 0, 6)), cy + rng.choice((25, 35, 45))), (-35, 40)]
        elif CASE == "post":                      # at a post, close in; the defencemen by the corners take rebounds
            cx, cy, push = rng.choice((-18, -17, -16, 16, 17, 18)), rng.choice((200, 215, 225)), ["UP"]
            dpos = [(-60, 240), (60, 240)]
        elif CASE == "wide":                      # just inside the rule's 40, past the post: off the end boards
            cx, cy, push = rng.choice((-40, -34, 34, 40)), rng.choice((170, 195, 220)), ["UP"]
            dpos = [(-55, 200), (55, 200)] if near else [(-35, 120), (35, 120)]
        elif CASE == "zone":
            cx, cy, push = rng.choice((-10, 0, 10)), rng.choice((-150, -100, -40, 20, 60)), ["UP"]
            dpos = [(cx - 12, cy + 100), (cx + 12, cy + 140)]
            fwd = [(-100, cy + 30), (100, cy + 30), (cx, cy + 55)]
            mates = [(-90, cy - 40), (90, cy - 40), (40, cy - 80), (-40, cy - 80)]
        elif CASE == "dump":
            cx, cy = rng.choice((-20, 0, 20)), rng.choice((40, 60, 76))
            push = rng.choice((["UP"], ["UP", "LEFT"], ["UP", "RIGHT"]))
            dpos = [(-30, 215), (30, 215)]
            fwd = [(-100, cy - 20), (100, cy - 20), (0, cy - 30)]
            mates = [(-90, cy - 40), (90, cy - 40), (40, cy - 80), (-40, cy - 80)]
        elif CASE == "shot":
            push = rng.choice((["UP"], ["UP", "LEFT"], ["UP", "RIGHT"], []))
        place = {me: (cx, cy)}
        place.update(dict(zip(dmen, dpos)))
        place.update(dict(zip(others_d, fwd)))
        place.update(dict(zip(others_a, mates)))
        for k, (x, y) in place.items():
            r = rec(k)
            y *= s
            e.setw(r, x & 0xFFFF); e.setw(r + 2, 0); e.setw(r + 0x14, y & 0xFFFF); e.setw(r + 0x16, 0); e.setw(r + 0x18, 0)
            e.setl(r + 0x1C, (x & 0xFFFF) << 16); e.setl(r + 0x20, (y & 0xFFFF) << 16)
            e.setw(r + 0x28, 0); e.setw(r + 0x2A, 0); e.setw(r + 0x2C, 0)
            if G["face"] == 0x55:
                e.setb(r + 0x55, 0 if s > 0 else 4)
            else:
                e.setw(r + 0x54, 0 if s > 0 else 4)
        for k in range(12):                       # every player's leftovers cleared, a new assignment
            if e.b(rec(k) + 0x35) == 0xFF:
                continue
            r = rec(k)
            for a in range(0x2E, 0x34):
                e.setb(r + a, 0)
            e.setw(r + 0x5E, 0)
            e.setb(r + 0x62, (e.b(r + 0x62) & 0xC0) | 0x02)
        e.setb(rec(me) + 0x62, e.b(rec(me) + 0x62) | 8)
        if down:
            e.setw(G["cont"][0], 0); e.setw(G["cont"][1], 2); e.setw(G["c2p"], me)
        else:
            e.setw(G["cont"][0], 1); e.setw(G["cont"][1], 0); e.setw(G["c1p"], me)
        pr = rec(14)
        e.setw(pr, cx & 0xFFFF); e.setw(pr + 0x14, (cy * s) & 0xFFFF); e.setw(pr + 0x18, 0)
        e.setw(G["puckc"], me)
        e.setb(G["fo"][0], e.b(G["fo"][0]) & ~G["fo"][1] & 0xFF)
        e.setw(0xFF0000 | G["lastc"], me); e.setb(0xFF0000 | G["lastp"], e.b(rec(me) + 0x66))
        e.setw(0xFF0000 | G["cause"], 0xFFFF); e.setb(0xFF0000 | (G["lastp"] + 1), 0xFF)
        for a in range(0x80):
            e.setb(0xFF0000 | (G["give"] + a), 0)
        pad = [{"UP": "DOWN", "LEFT": "LEFT", "RIGHT": "RIGHT"}[b] for b in push] if down else push
        btn = ["C"] if CASE == "shot" else ["B"]

        def step(f):
            h = (pad + btn) if f < 3 else []
            e.run(1, hold=[] if down else h, hold2=h if down else [])
        e.run(4, hold=[] if down else pad, hold2=pad if down else [])
        team_a = 1 if down else 0
        shots0 = e.w(G["team"][team_a])
        score0 = (e.w(G["team"][0] + 0x0C), e.w(G["team"][1] + 0x0C))
        prev = bytes(e.ram[G["give"]:G["give"] + 0x80])
        rel = clear = pick = goal_at = None
        counts_ev, trace, last = [], [], None
        for f in range(1500):
            step(f)
            px, py = e.sw(pr), e.sw(pr + 0x14)
            lc, cause, pc = W(G["lastc"]), W(G["cause"]), e.w(G["puckc"])
            if (lc, cause, pc) != last:
                trace.append((f, *[x - 0x10000 if x >= 0x8000 else x for x in (lc, cause, pc)], px, py))
                last = (lc, cause, pc)
            loose = pc >= 0x8000
            if rel is None and loose:
                x0, y0 = px, py * s
                vx0, vy0 = e.sw(pr + 0x28), e.sw(pr + 0x2A) * s
                d = G["goal"] - y0
                at_net = y0 >= G["blue"] and vy0 > 0 and d >= 20 and abs(x0 + int(vx0 * d / vy0)) <= 40
                mark = cause - 0x10000 if cause >= 0x8000 else cause
                rel = dict(f=f, x=x0, y=y0, vx=vx0, vy=vy0, rule=at_net, mark=mark,
                           mark_ok=(mark == (-3 if s > 0 else -4)) == at_net)
            if rel is not None and clear is None and rel["mark"] in (-2, -3, -4) and lc == 0xFFFF and loose and f > rel["f"]:
                gx, gy = e.sw(rec(gk)), e.sw(rec(gk) + 0x14)
                why = ("goalie (any pass)" if cause == 0xFFFE else "goal line" if py * s >= G["goal"] else
                       "goalie" if math.hypot(px - gx, py - gy) < 26 else "post / net")
                clear = dict(f=f, x=px, y=py * s, why=why)
            if rel is not None and pick is None and not loose and f > rel["f"]:
                k = pc & 0xFF
                pick = dict(f=f, k=k, who=("own " if k in A else "their ") + ("goalie" if e.b(rec(k) + 0x35) == 0 else "skater"),
                            x=px, y=py * s, clock=e.w(G["clock"]), faceoff=bool(e.b(G["fo"][0]) & G["fo"][1]))
            raw = bytes(e.ram[G["give"]:G["give"] + 0x80])
            if raw != prev:
                counts_ev += [(f, "give" if i < 64 else "take", (i % 64) // 32, i % 32) for i in range(0x80) if raw[i] > prev[i]]
                prev = raw
            if goal_at is None and (e.w(G["team"][0] + 0x0C), e.w(G["team"][1] + 0x0C)) != score0:
                goal_at = f
            if CASE == "shot" and f > 240:
                break
            if pick is not None and f > pick["f"] + 3:
                break
            if goal_at is not None and f > goal_at + 30:
                break
        if CASE == "shot":
            results.append(dict(trial=t, down=down, shots=e.w(G["team"][team_a]) - shots0, goal=goal_at is not None))
            print(t, "down" if down else "up", (cx, cy), push, "shots on goal +", results[-1]["shots"],
                  "goal" if goal_at is not None else "", flush=True)
            continue
        got = [c for c in counts_ev if pick is None or c[0] <= pick["f"] + 2]
        before_goal = pick is not None and (goal_at is None or pick["f"] < goal_at)
        uncleared = clear is None or clear["f"] > pick["f"] if pick else False      # (a goalie touch clears any pass)
        expect = bool(before_goal and pick["who"] == "their skater" and rel and uncleared and rel["mark"] in (-2, -3, -4))
        if rel and rel["mark"] not in (-2, -3, -4):   # not a pass: lost before the B (into the goalie: his giveaway)
            expect = bool(before_goal and [c for c in counts_ev if c[1] == "give"])
        gave = bool([c for c in got if c[1] == "give"])
        r = dict(trial=t, end="down" if down else "up", carrier=(cx, cy), push=push, near=near, release=rel, clear=clear,
                 pick=pick, goal=goal_at, counts=got, expected=expect, ok=expect == gave, trace=trace[:20])
        results.append(r)
        print(t, r["end"], (cx, cy), push, "| rule", rel and rel["rule"], "mark", rel and rel["mark"],
              "ok" if rel and rel["mark_ok"] else "MARK?", "| cleared", clear and (clear["why"], clear["x"], clear["y"]),
              "| taken", pick and (pick["who"], pick["x"], pick["y"]), "| goal" if goal_at is not None else "",
              "| counts", got, "| expected" if expect else "| none expected", "" if r["ok"] else "  <-- DIFFERS", flush=True)
    (out / f"genpass_{game}_{CASE}.json").write_text(json.dumps(results, indent=1))
    if CASE == "shot":
        print("shots on goal:", sum(r["shots"] for r in results), "goals:", sum(r["goal"] for r in results))
        return
    rr = [r for r in results if r["release"]]
    print(f"marks as the rule: {sum(r['release']['mark_ok'] for r in rr)} of {len(rr)} (at the net: up "
          f"{sum(r['release']['rule'] for r in rr if r['end'] == 'up')}, down {sum(r['release']['rule'] for r in rr if r['end'] == 'down')})")
    print(f"counts as expected: {sum(r['ok'] for r in results)} of {len(results)}")
    tally = Counter((("at the net" if r["release"] and r["release"]["rule"] else "not at the net"),
                     (r["clear"]["why"] if r["clear"] else "-"),
                     (r["pick"]["who"] if r["pick"] else ("goal" if r["goal"] is not None else "nobody")),
                     bool([c for c in r["counts"] if c[1] == "give"])) for r in results)
    for (a, c, w, g), k in sorted(tally.items()):
        print(f"  {k:3}  {a}, cleared: {c}, taken by {w}: {'a giveaway' if g else 'no count'}")


def snespass(rom, out, n):
    """genpass on a SNES giveaways build (retail or SA-1; snes_assist_stick_test.Game's live moments: pad 1 home, the
    two retail states attack the top and the bottom net, so both marks). The pad-1 skater has the puck; the cases and
    the per-trial checks are genpass's (the rule at the release against the mark, the clear, the first pick-up, the
    counts against the rule). 'shot' (A) counts the team's shots on goal: run it on the original too."""
    import random
    from snes_assist_stick_test import Game, POSITION, PUCKC, CARRIER2, GOALS, SHOTS
    out.mkdir(parents=True, exist_ok=True)
    gm = Game(str(rom))
    g, e = gm.g, gm.e
    rng = random.Random(11)

    def gv(off):
        if g.sa1:
            return g.bw[0x5500 + off] | g.bw[0x5501 + off] << 8
        return e.ram[GVBASE + off] | e.ram[GVBASE + off + 1] << 8

    def setgv(off, v):
        if g.sa1:
            g.bw[0x5500 + off], g.bw[0x5501 + off] = v & 0xFF, v >> 8
        else:
            e.ram[GVBASE + off], e.ram[GVBASE + off + 1] = v & 0xFF, v >> 8

    def block():
        return [gv(4 + 2 * i) for i in range(0x68)]           # giveaways (52 words), then takeaways (52)
    results = []
    for t in range(n):
        e.unserialize(g.bases[t % len(g.bases)])
        gm.setw(0x1632, 250)
        me, team, s = gm.me()
        A = list(range(6 * team, 6 * team + 6))
        D = list(range(6 * (1 - team), 6 * (1 - team) + 6))
        pos = lambda k: gm.w(POSITION + 2 * k)                # noqa: E731
        gk = next(k for k in D if pos(k) == 0)
        dmen = [k for k in D if pos(k) in (1, 2)][:2]
        others_d = [k for k in D if k not in dmen + [gk] and pos(k) != 0xFFFF]
        others_a = [k for k in A if k != me and pos(k) not in (0, 0xFFFF)]
        near = t % 3 == 0
        cx, cy = rng.choice((-30, -15, 0, 15, 30)), rng.choice((175, 195, 215))
        push = rng.choice((["UP"], ["UP"], ["UP", "LEFT"], ["UP", "RIGHT"]))
        dpos = [(-28, 238), (28, 238)] if near else [(-35, 60), (35, 60)]
        fwd = [(-90, -20), (90, -20), (0, -10)]
        mates = [(60, -40), (-60, -40), (40, -60), (-40, -60)]
        if CASE == "slot":
            cx, cy, push = rng.choice((-15, 0, 15)), rng.choice((150, 170, 190)), ["UP"]
            dpos = [(cx + rng.choice((-6, 0, 6)), cy + rng.choice((25, 35, 45))), (-35, 40)]
        elif CASE == "post":
            cx, cy, push = rng.choice((-26, -20, 20, 26)), rng.choice((215, 225, 235)), ["UP"]
            dpos = [(-60, 240), (60, 240)]
        elif CASE == "wide":
            cx, cy, push = rng.choice((-40, -34, 34, 40)), rng.choice((170, 195, 220)), ["UP"]
            dpos = [(-55, 200), (55, 200)] if near else [(-35, 120), (35, 120)]
        elif CASE == "zone":
            cx, cy, push = rng.choice((-10, 0, 10)), rng.choice((-150, -100, -40, 20, 60)), ["UP"]
            dpos = [(cx - 12, cy + 100), (cx + 12, cy + 140)]
            fwd = [(-100, cy + 30), (100, cy + 30), (cx, cy + 55)]
            mates = [(-90, cy - 40), (90, cy - 40), (40, cy - 80), (-40, cy - 80)]
        elif CASE == "dump":
            cx, cy = rng.choice((-20, 0, 20)), rng.choice((40, 60, 76))
            push = rng.choice((["UP"], ["UP", "LEFT"], ["UP", "RIGHT"]))
            dpos = [(-30, 215), (30, 215)]
            fwd = [(-100, cy - 20), (100, cy - 20), (0, cy - 30)]
            mates = [(-90, cy - 40), (90, cy - 40), (40, cy - 80), (-40, cy - 80)]
        elif CASE == "shot":
            push = rng.choice((["UP"], ["UP", "LEFT"], ["UP", "RIGHT"], []))
        place = {me: (cx, cy)}
        place.update(dict(zip(dmen, dpos)))
        place.update(dict(zip(others_d, fwd)))
        place.update(dict(zip(others_a, mates)))
        for k, (x, y) in place.items():
            gm.put(k, x, y * s)
        gm.put(14, cx, cy * s)
        gm.setw(PUCKC, 2 * me)
        gm.setw(CARRIER2, 2 * me)
        setgv(0, 2 * me)
        setgv(2, 0xFFFF)
        setgv(0xDC, gm.w(0x12A3 + 2 * me))
        gm.setw(0x15DC, gm.w(0x15DC) & ~0x10)                # sf3fo (the saved moments still have it)
        pad = [{"UP": "DOWN", "LEFT": "LEFT", "RIGHT": "RIGHT"}[b] for b in push] if s < 0 else push
        btn = ["A"] if CASE == "shot" else ["B"]
        gm.run(2, hold=pad)
        shots0 = sum(gm.w(a + 2 * team) for a in SHOTS)
        g0 = (gm.w(GOALS), gm.w(GOALS + 2))
        prev = block()
        rel = clear = pick = goal_at = None
        counts_ev, trace, last = [], [], None
        for f in range(1500):
            gm.run(1, hold=(pad + btn) if f < 3 else [])
            px, py = gm.sw(0x0D55 + 28), gm.sw(0x0DB7 + 28)
            lc, cause, pc = gv(0), gv(2), gm.w(PUCKC)
            if (lc, cause, pc) != last:
                trace.append((f, *[x - 0x10000 if x >= 0x8000 else x for x in (lc, cause, pc)], px, py))
                last = (lc, cause, pc)
            loose = pc >= 0x8000
            if rel is None and loose:
                x0, y0 = px, py * s
                vx0, vy0 = gm.sw(0x0EC3 + 28), gm.sw(0x0EE3 + 28) * s
                d = 264 - y0
                at_net = y0 >= 88 and vy0 > 0 and d >= 20 and abs(x0 + vx0 * d / vy0) <= 40
                mark = cause - 0x10000 if cause >= 0x8000 else cause
                rel = dict(f=f, x=x0, y=y0, vx=vx0, vy=vy0, rule=at_net, mark=mark,
                           mark_ok=(mark == (-3 if s > 0 else -4)) == at_net)
            if rel is not None and clear is None and rel["mark"] in (-2, -3, -4) and lc == 0xFFFF and loose and f > rel["f"]:
                gx, gy = gm.sw(0x0D55 + 2 * gk), gm.sw(0x0DB7 + 2 * gk)
                why = ("goalie (any pass)" if cause == 0xFFFE else "goal line" if py * s >= 264 else
                       "goalie" if math.hypot(px - gx, py - gy) < 26 else "post / net")
                clear = dict(f=f, x=px, y=py * s, why=why)
            if rel is not None and pick is None and not loose and f > rel["f"]:
                k = pc // 2
                pick = dict(f=f, k=k, who=("own " if k in A else "their ") + ("goalie" if pos(k) == 0 else "skater"),
                            x=px, y=py * s)
            now = block()
            if now != prev:
                counts_ev += [(f, "give" if i < 52 else "take", (i % 52) // 26, i % 26) for i in range(0x68) if now[i] > prev[i]]
                prev = now
            if goal_at is None and (gm.w(GOALS), gm.w(GOALS + 2)) != g0:
                goal_at = f
            if CASE == "shot" and f > 240:
                break
            if pick is not None and f > pick["f"] + 3:
                break
            if goal_at is not None and f > goal_at + 30:
                break
        if CASE == "shot":
            results.append(dict(trial=t, up=s, shots=sum(gm.w(a + 2 * team) for a in SHOTS) - shots0, goal=goal_at is not None))
            print(t, "up" if s > 0 else "down", (cx, cy), push, "shots on goal +", results[-1]["shots"],
                  "goal" if goal_at is not None else "", flush=True)
            continue
        got = [c for c in counts_ev if pick is None or c[0] <= pick["f"] + 2]
        before_goal = pick is not None and (goal_at is None or pick["f"] < goal_at)
        uncleared = clear is None or clear["f"] > pick["f"] if pick else False      # (a goalie touch clears any pass)
        expect = bool(before_goal and pick["who"] == "their skater" and rel and uncleared and rel["mark"] in (-2, -3, -4))
        if rel and rel["mark"] not in (-2, -3, -4):   # not a pass: lost before the B (into the goalie: his giveaway)
            expect = bool(before_goal and [c for c in counts_ev if c[1] == "give"])
        gave = bool([c for c in got if c[1] == "give"])
        r = dict(trial=t, end="up" if s > 0 else "down", carrier=(cx, cy), push=push, near=near, release=rel, clear=clear,
                 pick=pick, goal=goal_at, counts=got, expected=expect, ok=expect == gave, trace=trace[:20])
        results.append(r)
        print(t, r["end"], (cx, cy), push, "| rule", rel and rel["rule"], "mark", rel and rel["mark"],
              "ok" if rel and rel["mark_ok"] else "MARK?", "| cleared", clear and (clear["why"], clear["x"], clear["y"]),
              "| taken", pick and (pick["who"], pick["x"], pick["y"]), "| goal" if goal_at is not None else "",
              "| counts", got, "| expected" if expect else "| none expected", "" if r["ok"] else "  <-- DIFFERS", flush=True)
    (out / f"snespass_{CASE}.json").write_text(json.dumps(results, indent=1))
    if CASE == "shot":
        print("shots on goal:", sum(r["shots"] for r in results), "goals:", sum(r["goal"] for r in results))
        return
    rr = [r for r in results if r["release"]]
    print(f"marks as the rule: {sum(r['release']['mark_ok'] for r in rr)} of {len(rr)} (at the net: up "
          f"{sum(r['release']['rule'] for r in rr if r['end'] == 'up')}, down {sum(r['release']['rule'] for r in rr if r['end'] == 'down')})")
    print(f"counts as expected: {sum(r['ok'] for r in results)} of {len(results)}")
    tally = Counter((("at the net" if r["release"] and r["release"]["rule"] else "not at the net"),
                     (r["clear"]["why"] if r["clear"] else "-"),
                     (r["pick"]["who"] if r["pick"] else ("goal" if r["goal"] is not None else "nobody")),
                     bool([c for c in r["counts"] if c[1] == "give"])) for r in results)
    for (a, c, w, gv_), k in sorted(tally.items()):
        print(f"  {k:3}  {a}, cleared: {c}, taken by {w}: {'a giveaway' if gv_ else 'no count'}")


def snes_passshot(rom, out, n=24):
    """passshot on a SNES giveaways build (retail or SA-1: snes_assist_stick_test.Game's live play, pad 1 on the home
    side): the pad-1 skater with the puck (x -30..30, 175-215 toward the net he attacks), his teammates parked at the far
    end, the visiting defencemen by the posts (every third trial) or at centre; B with UP (UP-LEFT / UP-RIGHT) toward that
    net; the same cases as passshot (NHL94_PASS_CASE net / zone / dump). Counts read as SnesWatch reads them."""
    import random
    from snes_assist_stick_test import Game, POSITION, PUCKC, CARRIER2, GOALS
    out.mkdir(parents=True, exist_ok=True)
    gm = Game(str(rom))
    g, e = gm.g, gm.e
    rng = random.Random(7)
    results = []

    def gv(off):                                  # the hack's words (last carrier, cause)
        if g.sa1:
            return g.bw[0x5500 + off] | g.bw[0x5501 + off] << 8
        return e.ram[GVBASE + off] | e.ram[GVBASE + off + 1] << 8

    def setgv(off, v):
        if g.sa1:
            g.bw[0x5500 + off], g.bw[0x5501 + off] = v & 0xFF, v >> 8
        else:
            e.ram[GVBASE + off], e.ram[GVBASE + off + 1] = v & 0xFF, v >> 8
    for t in range(n):
        e.unserialize(g.bases[t % len(g.bases)])
        gm.setw(0x1632, 250)
        me, team, up = gm.me()
        near = t % 3 == 0
        cx, cy = rng.choice((-30, -15, 0, 15, 30)), rng.choice((175, 195, 215))
        push = rng.choice((["UP"], ["UP"], ["UP", "LEFT"], ["UP", "RIGHT"]))
        if CASE == "zone":
            cx, cy, push = rng.choice((-10, 0, 10)), rng.choice((-150, -100, -40, 20, 60)), ["UP"]
        elif CASE == "dump":
            cx, cy = rng.choice((-20, 0, 20)), rng.choice((40, 60, 80))
        if up < 0:
            push = [{"UP": "DOWN", "LEFT": "LEFT", "RIGHT": "RIGHT"}[b] for b in push]
        gm.park(me, up)
        theirs = [k for k in range(6 * (1 - team), 6 * (1 - team) + 6) if gm.w(POSITION + 2 * k) not in (0, 0xFFFF)]
        gk = next(k for k in range(6 * (1 - team), 6 * (1 - team) + 6) if gm.w(POSITION + 2 * k) == 0)
        for i, k in enumerate(theirs):
            if CASE == "zone":
                x, y = (cx, cy + 55 + 45 * i) if i < 3 else (-100 + 200 * (i % 2), cy + 30)
            elif CASE == "dump" or near:
                x, y = ((-30, 215), (30, 215))[i] if i < 2 else (-100 + 200 * (i % 2), 0)
            else:
                x, y = (-35 + 70 * (i % 2), 60 - 30 * (i // 2))
            gm.put(k, x, y * up)
        gm.put(me, cx, cy * up)
        gm.put(14, cx, cy * up)
        gm.setw(PUCKC, 2 * me)
        gm.setw(CARRIER2, 2 * me)
        setgv(0, 2 * me)                          # the last carrier and his roster place (kept from his pickup)
        setgv(2, 0xFFFF)
        setgv(0xDC, gm.w(0x12A3 + 2 * me))
        gm.setw(0x15DC, gm.w(0x15DC) & ~0x10)    # sf3fo: the saved moments still have the faceoff's (the puck put on
                                                 # him here never went through puckglue, which clears it)
        gm.run(2, hold=push)
        w = SnesWatch()
        w(e, 0, g)
        w.events = []                             # the counts already in the saved moment (the SA-1's BW-RAM) aren't new
        g0 = gm.w(GOALS + 2 * team)
        trace, touches, goal_at, end, last, gnp = [], [], None, 900, None, gm.w(0x1203 + 2 * gk)
        mouth = pick = rel = None
        for f in range(3000):
            gm.run(1, hold=push + ["B"] if f < 3 else [])
            w(e, f, g)
            st = (gv(0), gv(2), gm.w(PUCKC))
            if st != last:
                trace.append((f, *[x - 0x10000 if x >= 0x8000 else x for x in st]))
                last = st
            if rel is None and gm.w(PUCKC) >= 0x8000:     # the release: NOSE4Web's rule worked out here, against the build
                s_ = 1 if gm.w(0x14C3 + 2 * me) else -1
                x0, y0 = gm.sw(0x0D55 + 28), gm.sw(0x0DB7 + 28) * s_
                vx0, vy0 = gm.sw(0x0EC3 + 28), gm.sw(0x0EE3 + 28) * s_
                d = 264 - y0
                exp = y0 >= 88 and vy0 > 0 and d >= 20 and abs(x0 + vx0 * d / vy0) <= 40
                rel = dict(f=f, x=x0, y=y0, vx=vx0, vy=vy0, cross=round(x0 + vx0 * d / vy0, 1) if vy0 > 0 else None,
                           rule=exp, cleared=gv(0) == 0xFFFF)
            py, px = gm.sw(0x0DB7 + 28) * up, gm.sw(0x0D55 + 28)
            if mouth is None and gm.w(PUCKC) >= 0x8000 and py >= 264:
                mouth = (f, px)                    # where it crossed the goal line (Match Viewer: within 40)
            if pick is None and gm.w(PUCKC) < 0x8000 and f > 3:
                pick = (f, px, py)
            np_ = gm.w(0x1203 + 2 * gk)
            if np_ == 0x0A and gnp != 0x0A:
                touches.append(f)
            gnp = np_
            if goal_at is None and gm.w(GOALS + 2 * team) != g0:
                goal_at, end = f, 3000
            if goal_at is not None and gm.w(0x15D6) == 0 and gm.w(PUCKC) < 0x8000 and f > goal_at + 60:
                end = f
            if f >= end:
                break
        first = next(((f, p) for f, _, _, p in trace[1:] if p >= 0), None)
        if goal_at is not None and (first is None or first[0] > goal_at):
            what, resolved = "goal", end
        elif first is None:
            what, resolved = "unresolved", 3000
        else:
            k = first[1] // 2
            who = ("his team's " if k // 6 == team else "the other team's ") + ("goalie" if gm.w(POSITION + 2 * k) == 0 else "skater")
            what = ("goalie touched, then " if any(x < first[0] for x in touches) else "") + who + " took it"
            resolved = first[0]
        early = [(ev["frame"], ev["team"], ev["kind"], ev["place"]) for ev in w.events if ev["frame"] <= resolved + 2]
        mouthed = mouth is not None and abs(mouth[1]) <= 40 and (first is None or mouth[0] < first[0])
        results.append(dict(trial=t, carrier=(cx, cy), near=near, what=what, through_mouth=mouthed, crossed=mouth, release=rel,
                            picked=pick, counts=early, trace=trace[:30], touches=touches[:4]))
        print(t, "defence near" if near else "defence back", (cx, cy), push, "->", what, "(through the mouth)" if mouthed else "",
              "picked", pick, "| counts:", early, "| trace:", trace[:5], flush=True)
    (out / "snes_passshot.json").write_text(json.dumps(results, indent=1))
    rr = [r["release"] for r in results if r["release"]]
    print(f"the rule at the release: {sum(r['rule'] == r['cleared'] for r in rr)} of {len(rr)} as worked out "
          f"(at the net {sum(r['rule'] for r in rr)}, cleared {sum(r['cleared'] for r in rr)}); differing:",
          [r for r in rr if r["rule"] != r["cleared"]][:6])
    tally = Counter((r["what"], r["through_mouth"], bool(r["counts"])) for r in results)
    for (what, mo, counted), c in sorted(tally.items()):
        print(f"{c:3} {what}{' (through the mouth first)' if mo else ''}: {'a count' if counted else 'no count'}")


def main():
    mode = sys.argv[1]
    if mode in ("games", "snes_games"):
        games(sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]) if len(sys.argv) > 5 else 0,
              "genesis" if mode == "games" else "snes")
    elif mode == "pair":
        pair_again(Path(sys.argv[2]), sys.argv[3])
    elif mode == "highlights":
        highlights(sys.argv[2], Path(sys.argv[3]))
    elif mode == "shootout_mode":
        shootout_mode(sys.argv[2], Path(sys.argv[3]))
    elif mode == "shootout":
        shootout(sys.argv[2], Path(sys.argv[3]))
    elif mode == "snes_highlights":
        snes_highlights(sys.argv[2], Path(sys.argv[3]))
    elif mode == "snes_stats":
        snes_stats(sys.argv[2], Path(sys.argv[3]))
    elif mode == "stats":
        stats(sys.argv[2], Path(sys.argv[3]))
    elif mode == "build":
        lay_giveaways(sys.argv[2], sys.argv[3], sys.argv[4], goalie_fix="--goalie-fix" in sys.argv)
    elif mode == "genpass":
        lowload.gentle()
        genpass(sys.argv[2], sys.argv[3], Path(sys.argv[4]), int(sys.argv[5]), sys.argv[6] if len(sys.argv) > 6 else None)
    elif mode == "snespass":
        lowload.gentle()
        snespass(sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]))
    elif mode == "snes_passshot":
        lowload.gentle()
        snes_passshot(sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 24)
    elif mode == "passshot":
        lowload.gentle()
        passshot(sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 24)
    else:
        raise SystemExit(f"{mode}: not yet")


if __name__ == "__main__":
    main()
