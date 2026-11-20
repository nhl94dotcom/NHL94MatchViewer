"""When does a save state taken after NOSE4Web's season shootout hold the whole game's stats? (2026-11-20, for
NOSE4Web: a league that keeps save states of its shootout games.) NHL '94 (seasonTies shootout / shootoutNow), NHL '95
(seasonShootout / seasonShootoutNow) and the SNES (seasonShootout 1 / 2).

Computer games (short periods, penalties on, regular season), seed after seed, until one goes into the season
shootout by itself: so every stat in it is the game's own. The stats (the regions below) are read every frame from
the last frame before the shootout starts (the build's mark not yet set) to the post-game menu, and compared with that
frame: a frame is "full" when everything is the same but the winners' score, one more. The frames are told apart by
what the game is doing: the shootout (each attempt), the build's end code (the mark cleared: the stats put back), the
game-over screens (START pressed every 4 s, as a player would), until the menus. Save states are written at named
points and every 60 frames after the game is over, with a screenshot each, and read back from their files at the end:
the same comparison from the file.

Regions (the stats a save state is read for):
  NHL '94: $C472-$CD95 (scoring summary, penalty summary, both team structs: team and player stats, lines, time on
           ice, bodychecks; the hot / cold table inside them reported apart), the plus-minus log $DEF4-$DFFF, the
           giveaways / takeaways and bodycheck counts $E800-$E90F, $EC60-$EC6F, the injury counts and lines
           $F000-$F07F.
  NHL '95: $C02C-$C953 (ScoreSumbytes, the scoring summary, both team structs).
  SNES:    $15D3-$1D52 (team and player stats, lines, $168E / $16C2 the bodychecks) and $30F4-$347B (scoring summary),
           time on ice $E800-$E867; the game's running state inside the first (clock, gsp, flags) reported apart.

python shootout_savestate_check.py ROM OUT [STATE] [FIRST_SEED] [MAX_GAMES]   (STATE: NHL '95's live state)"""
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

import lowload


def s16(v):
    return v - 0x10000 if v > 0x7FFF else v


class G94:
    name = "NHL '94"
    REGIONS = [(0xC472, 0xCD96), (0xDEF4, 0xE000), (0xE800, 0xE910), (0xEC60, 0xEC70), (0xF000, 0xF080)]
    HM, AW, GSP, CLOCK, SCREEN, GMODE2, MARK = 0xC6DA, 0xCA3E, 0xC466, 0xC468, 0xFFF7, 0xC2FA, 0xF082
    ROUND, HSO, ASO, SOCLOCK, SOTEAM, CONT = 0xD578, 0xD574, 0xD576, 0xD454, 0xD594, (0xC328, 0xC32A)
    BASE, PLAYMODE = 0xB04A, 0xD048
    TM = [(0xC6CE, "home"), (0xCA32, "away")]

    def __init__(self, rom, seed, state=None):
        from emu import Emu
        self.rom = rom
        self.e = Emu(rom)
        self.boot = self.e.serialize()

    def new_game(self, n):
        import gen_ot_check as G
        import gen_goalie_hold_check as H
        e = self.e
        e.unserialize(self.boot)
        G.to_setup(e, Path(self.rom).parent)
        e.setw(H.PERLEN, 0)
        e.setw(H.OPTPEN, 2)
        e.setw(H.OPTLINE, 1)
        e.setw(self.PLAYMODE, 0)
        if not G.into_play(e):
            return False
        e.setl(H.SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
        return True

    def read(self):
        r = np.frombuffer(self.e.ram, np.uint8)
        return np.concatenate([r[lo:hi] for lo, hi in self.REGIONS]).copy()

    def addr(self, i):
        """Index into read() -> the 68000 address of that byte."""
        for lo, hi in self.REGIONS:
            if i < hi - lo:
                return 0xFF0000 | ((lo + i) ^ 1)
            i -= hi - lo
        return None

    def label(self, a):
        a &= 0xFFFF
        if 0xC472 <= a < 0xC5DC:
            return "scoring summary"
        if 0xC5DC <= a < 0xC6CE:
            return "penalty summary"
        for t, side in self.TM:
            if t <= a < t + 0x364:
                o = a - t
                if 0x66 <= o < 0x9A:
                    return f"{side} players' status (tmpdst, +$066)"
                return f"{side} team struct +${o:03X}" + (" (hot / cold table)" if 0x1A2 <= o < 0x342 else "")
        if 0xDEF4 <= a < 0xE000:
            return "plus-minus log"
        if 0xE800 <= a < 0xEC70:
            return "giveaways / bodycheck counts"
        if 0xF000 <= a < 0xF040:
            return "injury counts"
        return "lines ($F040)"

    def score(self):
        return self.e.w(self.HM), self.e.w(self.AW)

    def is_score(self, a):
        return (a & 0xFFFF) in (self.HM, self.HM + 1, self.AW, self.AW + 1)

    def not_stat(self, a):
        """Kept in the regions but not a stat: the players' status words (on the ice, on the bench) and the hot /
        cold table, which the game rewrites by itself."""
        lab = self.label(a)
        return "tmpdst" in lab or "hot / cold" in lab

    def shootout_on(self):
        return bool(self.e.b(self.GMODE2) & 1)

    def mark(self):
        return self.e.b(self.MARK)

    def attempt(self):
        e = self.e
        return e.w(self.ROUND), e.w(self.SOTEAM) & 1, e.w(self.HSO), e.w(self.ASO)

    def shoot_goals(self):
        return self.e.w(self.HSO), self.e.w(self.ASO)

    def gsp(self):
        return self.e.w(self.GSP)

    def screen(self):
        return self.e.b(self.SCREEN)

    def computer(self):
        e = self.e
        for c in self.CONT:
            e.setw(c, 0)
        for k in range(12):
            e.setb(self.BASE + 0x80 * k + 0x62, e.b(self.BASE + 0x80 * k + 0x62) & ~8)

    def in_attempt(self):
        return self.shootout_on() and self.e.w(self.SOCLOCK) != 0

    def menus(self):
        return self.gsp() == 0 and self.screen() not in (0, 0x80, 100)

    def clock(self):
        return self.e.w(self.CLOCK)

    def drive(self):
        return False

    def sig(self):
        return self.clock()

    def want_start(self, still, f, so, started):
        """START when the clock has stood 2.5 s (real), but not once a shootout's attempts are under way (a press then
        opens the pause menu: gen_shootout_check)."""
        return still >= 150 and f % 150 == 0 and not (so and started)


class G95(G94):
    name = "NHL '95"
    REGIONS = [(0xC02C, 0xC954)]
    HM, AW, GSP, CLOCK, GMODE2, MARK = 0xC294, 0xC5FA, 0xC020, 0xC022, 0xBF00, 0xF000
    ROUND, TEAMW, HSO, ASO, CONT, BASE, MODE = 0xD184, 0xD1A0, 0xD180, 0xD182, (0xBF4C, 0xBF4E), 0xAC62, 0xCC4C
    TM = [(0xC288, "home"), (0xC5EE, "away")]

    def __init__(self, rom, seed, state=None):
        from emu import Emu
        self.rom = rom
        self.e = Emu(rom)
        self.e.run(1500)                     # powered on first: states leave out save RAM (the shooter lists)
        self.live = Path(state).read_bytes()

    def new_game(self, n):
        """From the live state (gen95_assist_check's: a Regular Game, period 1 just after the opening faceoff, pad 1
        on the home team; the computer takes over every second): the regular season's mode, the season flags clear,
        a seed for each game. (Computer-only games set up from the menus hung as the first attempt started: a
        harness case, as gen95_shootout_check's games from this state play their shootouts through.)"""
        import gen95_ref_cvc as R
        e = self.e
        e.unserialize(self.live)
        e.setw(self.MODE, 0)
        e.setb(0xBF08, e.b(0xBF08) & ~8)
        e.setb(0xD1A7, e.b(0xD1A7) & ~0x20)
        e.setl(R.SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
        return True

    def label(self, a):
        a &= 0xFFFF
        if a < 0xC288:
            return "ScoreSumbytes / scoring and penalty summaries"
        for t, side in self.TM:
            if t <= a < t + 0x366:
                return f"{side} team struct +${a - t:03X}"
        return "?"

    def attempt(self):
        e = self.e
        return e.w(self.ROUND), e.w(self.TEAMW), e.w(self.HSO), e.w(self.ASO)

    def in_attempt(self):
        return self.shootout_on() and self.e.b(self.BASE + 14 * 0x80 + 0x60) == 0

    def screen(self):
        return 0

    def menus(self):
        return False

    def sig(self):
        p = self.BASE + 14 * 0x80
        return self.clock(), self.e.w(p), self.e.w(p + 0x14)

    def want_start(self, still, f, so, started):
        """As gen95_shootout_check: START when nothing has moved for 5 s (real), in the shootout too."""
        return still >= 300 and still % 300 == 0


class Snes(G94):
    name = "SNES"
    REGIONS = [(0x15D3, 0x1D53), (0x30F4, 0x347C), (0xE800, 0xE868)]
    HM, AW, GSP, CLOCK, SHOOTMODE, ROUND, SFLAGS, PLAYMODE = 0x178E, 0x1790, 0x1630, 0x1632, 0x1D81, 0x1D85, 0x15D8, 0x34BC

    def __init__(self, rom, seed, state=None):
        import menu_shots as M
        from snes_60fps_cvc import Mem
        self.rom = rom
        self.e = M.emulator(rom)
        self.m = Mem(self.e, rom)
        self.boot = self.e.serialize()
        self.menu_pressed = False
        self.sym = {}
        try:
            from paths import SNES_SYM
            src = SNES_SYM
        except ImportError:
            src = Path.home() / "NHL94_disasm" / "NHL94SNES" / "output" / "retail" / "obj" / "nhl94snes.sym"
        try:
            for line in Path(src).read_text(errors="replace").splitlines():
                parts = line.split()
                if len(parts) >= 2 and ":" in parts[0]:
                    bank, ad = parts[0].split(":")
                    if bank.lower() in ("7e", "00") and int(ad, 16) < 0x10000:
                        self.sym.setdefault(int(ad, 16), parts[1])
        except OSError:
            pass
        self.names = sorted(self.sym)

    def new_game(self, n):
        import menu_shots as M
        from snes_60fps_cvc import CLOCKSTOP, OPTPEN, SEED, computer_only
        e, m = self.e, self.m
        e.unserialize(self.boot)
        out = Path("x_tmp_sosave")
        if m.sa1:
            M.play(e, f"w{1800 + 53 * n} START w240", out)
        else:
            M.play(e, f"w{1500 + 53 * n} START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", out)
        M.play(e, "START w240 START w200 w2400", out)
        for _ in range(12):
            c = m.w(self.CLOCK)
            e.run(240)
            if m.w(self.CLOCK) != c and m.w(CLOCKSTOP) == 0:
                break
            e.run(4, hold=["START"])
            e.run(60)
        m.setw(OPTPEN, 2)
        m.setw(self.PLAYMODE, 0)
        computer_only(m)
        m.setw(SEED, (0x9E37 * (n + 1)) & 0xFFFF or 1)
        m.setw(SEED + 2, (0x7F4A * (n + 3)) & 0xFFFF or 1)
        self.menu_pressed = False
        return True

    def read(self):
        out = []
        for lo, hi in self.REGIONS:
            buf, o = self.m.at(lo)
            out.append(np.frombuffer(buf, np.uint8)[o:o + hi - lo])
        return np.concatenate(out).copy()

    def addr(self, i):
        for lo, hi in self.REGIONS:
            if i < hi - lo:
                return lo + i
            i -= hi - lo
        return None

    def label(self, a):
        import bisect
        if 0xE800 <= a < 0xE868:
            return "time on ice ($E800)"
        if 0x168E <= a < 0x16C2:
            return "bodychecks given ($168E)"
        if 0x16C2 <= a < 0x16F6:
            return "bodychecks taken ($16C2)"
        k = bisect.bisect_right(self.names, a) - 1
        if k >= 0:
            b = self.names[k]
            return f"{self.sym[b]}+{a - b}" if a - b < 0x80 else f"${a:04X}"
        return f"${a:04X}"

    def is_score(self, a):
        return a in (self.HM, self.HM + 1, self.AW, self.AW + 1)

    def score(self):
        return self.m.w(self.HM), self.m.w(self.AW)

    def shootout_on(self):
        return bool(self.m.w(self.SHOOTMODE) & 0xFF)

    def mark(self):
        return self.shootout_on()

    def attempt(self):
        return self.m.w(self.ROUND), 0, self.m.w(self.HM), self.m.w(self.AW)

    def in_attempt(self):
        from snes_60fps_cvc import CLOCKSTOP
        return self.shootout_on() and self.m.w(CLOCKSTOP) == 0

    def gsp(self):
        return self.m.w(self.GSP)

    def clock(self):
        return self.m.w(self.CLOCK)

    def screen(self):
        return 0

    def menus(self):
        return False

    def computer(self):
        from snes_60fps_cvc import computer_only
        computer_only(self.m)

    def want_start(self, still, f, so, started):
        """As snes_shootout_check: START when the clock has stood 15 s (real), never in the shootout (its menus go on
        by themselves, or by B: drive)."""
        return still >= 900 and still % 900 == 0 and not so

    def drive(self):
        """The shootout's opening menu (sflags $0400) waits for pad 1's B, held 8 frames (snes_shootout_check)."""
        if self.shootout_on() and not self.menu_pressed and self.m.w(self.SFLAGS) & 0x400:
            self.e.run(30)
            self.e.run(8, hold=["B"])
            self.menu_pressed = True
            return True
        return False


def run(sysobj, out, first, games):
    e = sysobj.e
    out.mkdir(parents=True, exist_ok=True)
    for n in range(first, first + games):
        if not sysobj.new_game(n):
            print(f"game {n}: never reached play", flush=True)
            continue
        res = one_game(sysobj, out, n)
        if res is not None:
            return res
        print(f"game {n}: no shootout (final {sysobj.score()})", flush=True)
        lowload.breathe()
    return None


FORCE = __import__("os").environ.get("SOSAVE_FORCE", "")
TIE = __import__("os").environ.get("SOSAVE_TIE", "") == "1"   # with FORCE: tie the deciding period's last 10 s


def force(S, done):
    """SOSAVE_FORCE (Genesis): in a tied third period or overtime, 'away5': the visitors' tmap 5 in the last 2 s (a
    man short as the shootout starts); 'pull': gmode's gmpendel (a delayed penalty) set once with 30 s left, so the
    computer's ChkGoalies pulls the goalie of the team with the puck (tmgoalie $FFFF); logged when it happens."""
    e = S.e
    if S.mark():
        return                       # the shootout's start code has run: leave what it set
    g, c = S.gsp(), S.clock()
    h, a = S.score()
    running = c < done.get("last_clock", -1)            # the clock moved down since the last frame
    if TIE and g == 3 and 10 < c < done.get("last_clock", 0) and (3, "cut") not in done:
        e.setw(S.CLOCK, 10)                              # overtime's clock running: 10 s left (sudden death)
        done[(3, "cut")] = True
        print(f"overtime clock {c} cut to 10", flush=True)
        c = 10
    done["last_clock"] = c
    if FORCE == "pull" and g >= 2 and 0 < c <= 30 and running and (g, "pull") not in done:
        gm = 0xC2EA if S.GMODE2 == 0xC2FA else 0xBEF0
        e.setb(gm, e.b(gm) | 8)                          # a delayed penalty: whatever the score
        done[(g, "pull")] = True
        print(f"gsp {g} clock {c}: gmpendel set", flush=True)
    if FORCE == "pull" and (g, "pulled") not in done and 0xFFFF in [e.w(t + 0x26) for t, _ in S.TM]:
        done[(g, "pulled")] = True
        print(f"gsp {g} clock {c}: a goalie pulled, tmgoalie {['%04X' % e.w(t + 0x26) for t, _ in S.TM]}", flush=True)
    if TIE and g >= 2 and c <= 10 and h != a:
        e.setw(S.HM if h < a else S.AW, max(h, a))      # tied with 10 s left (the team score words only)
        if (g, "tie") not in done:
            done[(g, "tie")] = True
            print(f"gsp {g} clock {c}: score {h}-{a} made {max(h, a)}-{max(h, a)}", flush=True)
        h = a = max(h, a)
    if g < 2 or h != a:
        return
    if FORCE == "away5" and c <= 2:
        e.setw(S.TM[1][0] + 0x24, 5)
    if FORCE.startswith("box:") and c <= 2:
        side, k = FORCE.split(":")[1], int(FORCE.split(":")[2])     # box:home|away:roster index
        tm = S.TM[0 if side == "home" else 1][0]
        dst, lst = (0x66, 0x9A) if isinstance(S, G95) is False else (0x68, 0x9C)
        e.setw(tm + dst + 2 * k, 100)                    # in the box, 100 s to serve
        e.setb(tm + lst, k)
        e.setb(tm + lst + 1, 0xFF)
        e.setw(tm + 0x24, 5)                             # a man short
        recs = range(6) if side == "home" else range(6, 12)
        for r in recs:                                   # and off the ice, as a penalty takes him
            rec = S.BASE + 0x80 * r
            if e.b(rec + 0x66) == k and e.b(rec + 0x35) != 0xFF and e.b(rec + 0x35) != 0:
                e.setb(rec + 0x35, 0xFF)


def one_game(S, out, n):
    e = S.e
    pre, pre_info, before, base_score = None, None, None, None
    events, runs, states = [], [], {}
    ring = deque(maxlen=3)
    still, last_clock, started = 0, None, False
    f, over_at, end_at, last_att, last_goal_f, next_press = 0, None, None, None, None, None
    cur_key = None
    was_in = False
    pre_tm, forced = [], {}
    prev_scr = None
    while f < 60 * 60 * 40:
        if f % 60 == 0 and over_at is None:
            S.computer()
        if f % 3600 == 0:
            lowload.breathe()
            print(f"game {n} f{f}: gsp {S.gsp()} clock {S.clock()} score {S.score()} shootout {S.shootout_on()}",
                  flush=True)
            e.screenshot(out / f"g{n}_progress_{f:06d}.png")
        so = S.shootout_on()
        if so and S.in_attempt():
            started = True
        if not so:
            started = False
        press = False
        if over_at is None:
            press = S.want_start(still, f, so, started)

        ring.append((f, e.serialize()) if before is not None and end_at is None else None)
        if S.drive():
            f += 38
        e.run(1, hold=["START"] if press else [])
        f += 1
        c = S.sig()
        still = still + 1 if c == last_clock else 0
        last_clock = c
        now = S.read()
        if before is None and hasattr(S, "TM") and FORCE:
            force(S, forced)
        if before is None:
            if S.mark():
                if hasattr(S, "TM") and not isinstance(S, Snes):
                    events.append((f, "before the shootout (the frame before): tmap / tmgoalie "
                                   + ", ".join(f"{side} {v[0]} / {v[1]:04X}" for side, v in pre_tm)
                                   + "; now " + ", ".join(f"{side} {e.w(t + 0x24)} / {e.w(t + 0x26):04X}" for t, side in S.TM)))
                    print(events[-1][1], flush=True)
                    dst = 0x68 if isinstance(S, G95) else 0x66
                    events.append((f, "in the box at the start code: " + ", ".join(
                        f"{side} {[k for k in range(26) if e.sw(t + dst + 2 * k) >= 0]}" for t, side in S.TM)))
                    print(events[-1][1], flush=True)
                before, base_score = pre, pre_info
                np.save(out / f"g{n}_before_shootout.npy", before)
                states["first frame of the shootout (the mark set)"] = (f, e.serialize())
                events.append((f, f"shootout starts (the mark set), score {base_score[0]}-{base_score[1]}, gsp {S.gsp()}"))
                print(f"game {n} f{f}: shootout starts at {base_score}", flush=True)
            elif S.gsp() >= 4:
                return None
            else:
                pre, pre_info = now, S.score()
                if hasattr(S, "TM") and not isinstance(S, Snes):
                    pre_tm = [(side, (e.w(t + 0x24), e.w(t + 0x26))) for t, side in S.TM]
                continue
        # in or after the shootout
        if end_at is None:
            a = S.attempt()
            ina = S.in_attempt()
            if was_in and not ina:
                states["right after the last attempt"] = (f, e.serialize())
            was_in = ina
            if a != last_att:
                if last_att is not None and a[2:] != last_att[2:]:
                    last_goal_f = f
                    states["right after the last shootout goal"] = (f, e.serialize())
                events.append((f, f"round {a[0]}, {'visitors' if a[1] else 'home'} to shoot, shootout goals {a[2]}-{a[3]}"))
                last_att = a
            if "during" not in states and S.in_attempt() and a[0] == 1:
                states["during"] = (f, e.serialize())
            if not S.mark():
                end_at = f
                events.append((f, f"the build's end code ran (mark cleared): score {S.score()}, gsp {S.gsp()}"))
                if ring and ring[0] is not None:
                    states["last frame of the shootout"] = ring[-1] if ring[-1] else ring[0]
                states["first frame after the end code"] = (f, e.serialize())
                over_at = f
                next_press = f + 240
        if over_at is not None:
            scr = (S.gsp(), S.screen())
            if scr != prev_scr:
                events.append((f, f"gsp {scr[0]} screen {scr[1]}"))
                prev_scr = scr
                states[f"screen change f{f}"] = (f, e.serialize())
                e.screenshot(out / f"g{n}_f{f:05d}_screen.png")
            elif (f - over_at) % 60 == 0:
                states[f"f{f}"] = (f, e.serialize())
                e.screenshot(out / f"g{n}_f{f:05d}.png")
        d = np.nonzero(now != before)[0]
        key = tuple(int(x) for x in d)
        if key != cur_key:
            runs.append([f, f, [(S.addr(i), int(before[i]), int(now[i])) for i in d[:400]], len(d)])
            cur_key = key
        else:
            runs[-1][1] = f
        if over_at is not None and f - over_at > 60 * 60:
            events.append((f, "60 s after the end code (nothing pressed)"))
            break
    # winners: the score word that is one more
    return finish(S, out, n, before, base_score, events, runs, states)


def finish(S, out, n, before, base_score, events, runs, states):
    e = S.e
    base = {"game": n, "rom": Path(S.rom).name, "score before the shootout": base_score, "events": events}
    rows = []
    for f0, f1, diffs, nd in runs:
        sc = [a for a in diffs if S.is_score(a[0])]
        other = [a for a in diffs if a not in sc]
        labels = sorted({S.label(a[0]) for a in other})
        rows.append({"frames": [f0, f1], "bytes different": nd, "score bytes": [[hex(a), b, c] for a, b, c in sc],
                     "other": len(other), "other where": labels[:20],
                     "others": [[hex(a), S.label(a), b, c] for a, b, c in other]})
    base["runs"] = rows
    # the save states, read back from their files
    chk = {}
    for name, (f, st) in states.items():
        p = out / f"g{n}_{name.replace(' ', '_')}.state"
        p.write_bytes(st)
        e.unserialize(p.read_bytes())
        now = S.read()
        d = np.nonzero(now != before)[0]
        other = [S.addr(i) for i in d if not S.is_score(S.addr(i))]
        stat = [a for a in other if not S.not_stat(a)]
        chk[name] = {"frame": f, "score": S.score(), "gsp": S.gsp(), "bytes different (not the score)": len(other),
                     "stat bytes different": len(stat), "where (stats)": sorted({S.label(a) for a in stat})[:16],
                     "where (not stats)": sorted({S.label(a) for a in other if S.not_stat(a)})[:8]}
        e.screenshot(out / f"g{n}_{name.replace(' ', '_')}.png")
    base["states"] = chk
    (out / f"g{n}.json").write_text(json.dumps(base, indent=1))
    for k, v in chk.items():
        print(k, json.dumps(v), flush=True)
    return base


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    state = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    games = int(sys.argv[5]) if len(sys.argv) > 5 else 30
    lowload.gentle()
    data = Path(rom).read_bytes()
    if rom.lower().endswith((".smc", ".sfc")):
        S = Snes(rom, first)
    elif b"NHL 95" in data[0x100:0x200].replace(b"'", b"") or "95" in Path(rom).name:
        S = G95(rom, first, state)
    else:
        S = G94(rom, first)
    run(S, out, first, games)


if __name__ == "__main__":
    main()
