"""NOSE4Web's NHL94SNESVault hacks (2026-11-09, NOSE4Web 44ab460), played in the game: NHL94_vault_hacks.smc (retail
NHL94.smc with the extra attacker fix, ForwardsAndDefenseHack, ShowMaxBoost, ManualPullGoalie and the computer's pull
at 1-3 goals behind with 120 s or less) against NHL94.smc. From the saved state SNES_STATE_TOP (Montreal at home on
pad 1 against Los Angeles, first period, in play). Parts, each from that state:

- lines: Edit Lines (START, down 4, B) on line 1 (the Best Line, Line Changes Off as in the state) and line 6 (Pen.
  Kill 1: Line Changes set On in RAM first, then RIGHT x 5), every row, every pick of the
  list (UP to its top, DOWN n, B): the list's size and first player (listcount $1DA3, pickfirst $1DAB), each line read
  back (home lines $1CE4, 8 bytes: goalie, LD, RD, LW, C, RW, extra attacker, 0), a player twice, a player dropped
  (one who was on the line and isn't after a pick of someone already on it).
- play (the hack): line 1's LD given the line's extra attacker (a forward: the fix swaps, the old LD becomes the extra
  attacker) and C a defenceman off the line; back to play (START, B, START); each skater's position ($0F43) and roster
  place ($12A3) once the line is on; then L+R pulls the goalie and the extra attacker's position is read.
- ratings: the pick list's rating columns (RIGHT through them; the text map at $7E:37F4, tiles - $8D) for all 22
  skaters (the LD list on the hack, LD and LW on retail), against the hot / cold table ($1A12, 12 bytes a player):
  which cells read 100 on the hack and which cold values they match.
- lr: L+R held h frames after o frames, then 60 frames: is the goalie out (tmgoalie $17AA)? Pulled then L+R again;
  during a stoppage (gmclock $15D6 set by play); tmgoalie $FF00 (pulled by the game) and 1 (the backup); both pads
  on the home team (cont2team $1C86 = 1) with pad 2 alone pressing, then pad 1; pad 2 alone on the home team; the
  sound (part_sound: the audio frame by frame from the press, against the same frames without it).
- cpu: both teams by the computer (snes_60fps_cvc.computer_only), third period ($1630 = 2), home behind by 1-4
  (tmscore $178E / $1790), the clock held at 125 / 115 / 65 / 55 s for 60 game seconds: did home pull its goalie?

Gentle (lowload). python snes_vault_hacks_test.py RETAIL HACK OUT [part ...]"""
import ctypes as C
import json
import sys
from collections import Counter
from pathlib import Path

import lowload
from paths import SNES_STATE_TOP
from snes_emu import SnesEmu

SFLAGS, PSITEM, CLOCK, GMCLOCK, GSP = 0x15D8, 0x0D15, 0x1632, 0x15D6, 0x1630
TMGOALIE, CONT1, CONT2, TEAMPADS, SCORE = 0x17AA, 0x1C84, 0x1C86, 0x19D0, 0x178E
POSITION, PNUM, PFTEAM, LINES, HOTCOLD = 0x0F43, 0x12A3, 0x1503, 0x1CE4, 0x1A12
LISTCOUNT, PICKFIRST, PICKROWS, PICKTOP = 0x1DA3, 0x1DAB, 0x1DAF, 0x1DA7
TEXTMAP, OPTLINE, LINESEL = 0x37F4, 0x34C6, 0x0D43
ROWS = ["LD", "RD", "LW", "C", "RW"]


class Game:
    def __init__(self, rom):
        self.e = SnesEmu(rom)
        self.state = open(SNES_STATE_TOP, "rb").read()
        self.audio = []
        self._acb = C.CFUNCTYPE(C.c_size_t, C.POINTER(C.c_int16), C.c_size_t)(self._audio)
        self.e.lib.retro_set_audio_sample_batch(self._acb)

    def _audio(self, data, frames):
        self.audio.append(sum(abs(data[i]) for i in range(0, 2 * frames, 8)))
        return frames

    def reset(self):
        self.e.unserialize(self.state)
        self.e.run(30)

    def tap(self, b, wait=20, pad2=False):
        self.e.run(3, **({"hold2": [b]} if pad2 else {"hold": [b]}))
        self.e.run(wait)

    def editor(self, line=1):
        if line > 1:                      # with Line Changes Off the editor shows only line 1 (the Best Line)
            self.e.setw(OPTLINE, 1)
        self.tap("START", 60)
        for b in ("DOWN",) * 4 + ("B",):
            self.tap(b, 40)
        self.e.run(150)
        for _ in range(line - 1):
            self.tap("RIGHT", 40)

    def line(self, n=1):
        return [self.e.b(LINES + 8 * (n - 1) + j) for j in range(1, 7)]

    def back_to_play(self):
        for b in ("START", "B", "START"):
            self.tap(b, 90)

    def text(self, r, c0, c1):
        return "".join(" " if (t := self.e.w(TEXTMAP + 64 * r + 2 * c)) == 0x029F else chr((t & 0x1FF) - 0x8D)
                       for c in range(c0, c1)).strip(" \x13")


def part_lines(rom):
    g = Game(rom)
    out = {}
    for line in (1, 6):
        g.reset()
        g.editor(line)
        base = g.e.serialize()
        before = g.line(line)
        rows = ROWS[:5] if line < 6 else ROWS[:4]
        res = {"editor_line": g.e.w(LINESEL), "before": before, "rows": {}}
        for r, name in enumerate(rows):
            g.e.unserialize(base)
            for _ in range(r):
                g.tap("DOWN", 15)
            g.tap("B", 60)
            n, first = g.e.w(LISTCOUNT), g.e.w(PICKFIRST)
            picks, twice, dropped, changed = [], 0, 0, 0
            for k in range(n):
                g.e.unserialize(base)
                for _ in range(r):
                    g.tap("DOWN", 15)
                g.tap("B", 60)
                for _ in range(n + 1):
                    g.tap("UP", 10)
                for _ in range(k):
                    g.tap("DOWN", 10)
                g.tap("B", 60)
                after = g.line(line)
                changed += after != before
                dup = [p for p, c in Counter(after).items() if c > 1 and p]
                # someone on the line before is missing although nobody new came on (a pick from the line itself)
                lost = set(before) - set(after)
                drop = bool(lost) and not (set(after) - set(before))
                twice += bool(dup)
                dropped += drop
                picks.append(dict(pick=k, line=after, twice=dup, dropped=sorted(lost) if drop else []))
            res["rows"][name] = dict(listcount=n, pickfirst=first, picks=len(picks), lines_changed=changed,
                                     with_a_player_twice=twice,
                                     with_a_player_dropped=dropped, examples=[p for p in picks if p["twice"] or p["dropped"]][:4])
            lowload.breathe()
        out[f"line{line}"] = res
    return out


def part_play(rom):
    g = Game(rom)
    g.reset()
    g.editor(1)
    base_line = g.line(1)
    ea, ld_old = base_line[5], base_line[0]
    # LD: the extra attacker (a forward); C: the first defenceman off the line
    def pick(row, want):
        g.tap("DOWN", 15) if row else None
        for _ in range(row - 1):
            g.tap("DOWN", 15)
        g.tap("B", 60)
        first = g.e.w(PICKFIRST)
        for _ in range(g.e.w(LISTCOUNT) + 1):
            g.tap("UP", 10)
        for _ in range(want - 1 - first):
            g.tap("DOWN", 10)
        g.tap("B", 60)
        for _ in range(6):
            g.tap("UP", 15)
    pick(0, ea)
    after_ld = g.line(1)
    d_off = next(p for p in range(17, 25) if p not in after_ld)          # roster place + 1 of a defenceman off it
    pick(3, d_off)
    edited = g.line(1)
    g.back_to_play()
    want = {1: edited[0] - 1, 4: edited[3] - 1}
    seen, frames = None, 0
    while frames < 60 * 120:
        g.e.run(10)
        frames += 10
        on = {g.e.w(POSITION + 2 * k): g.e.w(PNUM + 2 * k) & 0xFF for k in range(6)}
        if all(on.get(p) == r for p, r in want.items()):
            seen = frames
            break
    on_ice = {ROWS[p - 1] if 1 <= p <= 5 else p: r + 1 for p, r in
              ((g.e.w(POSITION + 2 * k), g.e.w(PNUM + 2 * k) & 0xFF) for k in range(6))}
    # pull the goalie: where does the extra attacker (the old LD) play?
    pulled_at, clock_ran = None, g.e.w(GMCLOCK) == 0
    for o in range(600):
        g.e.run(1, hold=["L", "R"] if o % 60 < 20 else [])
        if g.e.w(TMGOALIE) & 0x8000:
            pulled_at = o
            break
    g.e.run(240)
    with_ea = {g.e.w(POSITION + 2 * k): (g.e.w(PNUM + 2 * k) & 0xFF) + 1 for k in range(6)}
    return dict(line_before=base_line, after_ld_pick=after_ld, edited=edited, old_ld=ld_old, extra_attacker_before=ea,
                frames_until_on=seen, on_ice=on_ice, clock_running=clock_ran, pulled_after_frames=pulled_at, tmgoalie=hex(g.e.w(TMGOALIE)),
                positions_with_goalie_out=with_ea)


def part_ratings(rom, rows):
    g = Game(rom)
    res = {}
    for row in rows:
        g.reset()
        g.editor(1)
        for _ in range(ROWS.index(row)):
            g.tap("DOWN", 15)
        g.tap("B", 60)
        n = g.e.w(LISTCOUNT)
        heads = []
        for col in range(16):
            head = g.text(2, 15, 31).strip("\\^[] ")
            if head in heads:
                break
            heads.append(head)
            for _ in range(n + 2):
                g.tap("UP", 12)
            for _ in range(n + 2):
                top = g.e.w(PICKTOP)
                for r in range(3, 3 + g.e.w(PICKROWS)):
                    res.setdefault(head, {})[top + r - 3] = g.text(r, 24, 31)
                g.tap("DOWN", 12)
            g.tap("RIGHT", 20)
        lowload.breathe()
    hc = [[g.e.b(HOTCOLD + 12 * p + i) for i in range(12)] for p in range(26)]
    return res, hc


def ratings(retail, hack):
    a, _ = part_ratings(retail, ["LD", "LW"])
    b, hc = part_ratings(hack, ["LD"])
    sg = lambda v: v - 256 if v > 127 else v
    out = {}
    for head in a:
        cells = [p for p in a[head] if p in b.get(head, {})]
        to100 = {p for p in cells if a[head][p] != b[head][p]}
        other = [p for p in to100 if b[head][p] != "100"]
        best = min(range(12), key=lambda c: len(to100 ^ {p for p in cells if sg(hc[p][c]) < -1}))
        neg = {p for p in cells if sg(hc[p][best]) < 0}
        out[head] = dict(players=len(cells), shown_100=len(to100), changed_not_to_100=other, hot_cold_column=best,
                         cold_not_100=sorted((p, sg(hc[p][best]), b[head][p]) for p in neg - to100),
                         to100_not_cold=sorted(to100 - neg))
    return out


def part_lr(rom):
    g = Game(rom)
    res = {}
    # timing: hold h frames after o frames
    timing = {}
    for h in (2, 4, 8, 12, 16, 24, 30, 36, 48):
        pulled = 0
        for o in range(0, 24, 2):
            g.reset()
            g.e.run(o)
            g.e.run(h, hold=["L", "R"])
            g.e.run(60)
            pulled += bool(g.e.w(TMGOALIE) & 0x8000)
        timing[h] = f"{pulled} of 12"
        lowload.breathe()
    res["pulled_by_hold_frames"] = timing

    def hold_until(state_ok, pad2=False, frames=120):
        for f in range(frames):
            g.e.run(1, **({"hold2": ["L", "R"]} if pad2 else {"hold": ["L", "R"]}))
            if state_ok():
                return f
        return None
    # pull, release, press again
    g.reset()
    f1 = hold_until(lambda: g.e.w(TMGOALIE) == 0xFFFF)
    g.e.run(60)
    f2 = hold_until(lambda: g.e.w(TMGOALIE) == 0)
    res["pull_then_return"] = dict(pulled_after=f1, returned_after=f2, tmgoalie=hex(g.e.w(TMGOALIE)))
    res["sound"] = part_sound(g)
    # a stoppage: play on until the clock stops, then L+R
    g.reset()
    for f in range(60 * 60 * 3):
        g.e.run(1, hold=["UP"] if f % 120 < 60 else ["DOWN", "B"])
        if g.e.w(GMCLOCK) and not g.e.w(SFLAGS) & 1:
            break
    stopped = g.e.w(GMCLOCK)
    t0 = g.e.w(TMGOALIE)
    n = 0
    while g.e.w(GMCLOCK) and n < 200:
        g.e.run(1, hold=["L", "R"])
        n += 1
    res["stoppage"] = dict(clock_stopped=bool(stopped), frames_held_while_stopped=n, tmgoalie_before=hex(t0),
                           tmgoalie_after=hex(g.e.w(TMGOALIE)))
    # pulled by the game ($FF00) and the backup in net (1)
    for v in (0xFF00, 0x0001):
        g.reset()
        g.e.setw(TMGOALIE, v)
        g.e.run(60, hold=["L", "R"])
        res[f"tmgoalie_{v:04X}"] = hex(g.e.w(TMGOALIE))
    # both pads on the home team
    for who in ("pad2", "pad1"):
        g.reset()
        g.e.setw(CONT2, 1)
        g.e.run(2)
        f = hold_until(lambda: bool(g.e.w(TMGOALIE) & 0x8000), pad2=(who == "pad2"), frames=72)
        res[f"both_pads_home_{who}_presses"] = dict(pulled_after=f, tmgoalie=hex(g.e.w(TMGOALIE)))
    # pad 2 alone on home (pad 1 on the visitors)
    g.reset()
    g.e.setw(CONT1, 2)
    g.e.setw(CONT2, 1)
    g.e.run(2)
    f = hold_until(lambda: bool(g.e.w(TMGOALIE) & 0x8000), pad2=True, frames=72)
    res["pad2_alone_on_home"] = dict(pulled_after=f, tmgoalie=hex(g.e.w(TMGOALIE)))
    return res


def part_sound(g):
    """The audio (a sum of sample sizes per frame) for 40 frames from the L+R press that pulls the goalie, against the
    same frames with nothing pressed: the frames that differ and the loudness of each."""
    def run(press):
        g.reset()
        frames = []
        for f in range(40):
            n = len(g.audio)
            g.e.run(1, hold=["L", "R"] if press and f < 24 else [])
            frames.append((sum(g.audio[n:]), g.e.w(TMGOALIE)))
        return frames
    a, b = run(True), run(False)
    pulled = next((f for f, (_, t) in enumerate(a) if t == 0xFFFF), None)
    return dict(pulled_at_frame=pulled, loudness_with=[x for x, _ in a], loudness_without=[x for x, _ in b],
                first_frame_that_differs=next((f for f in range(40) if a[f][0] != b[f][0]), None))


def part_cpu(rom):
    import snes_60fps_cvc as V
    g = Game(rom)
    out = {}
    for behind in (1, 2, 3, 4):
        for clock in (125, 115, 65, 55):
            g.reset()
            m = V.Mem(g.e, rom)
            g.e.setw(GSP, 2)
            g.e.setw(SCORE, 0)
            g.e.setw(SCORE + 2, behind)
            pulled = None
            for f in range(0, 24 * 60, 6):
                if f % 60 == 0:
                    V.computer_only(m)
                g.e.setw(CLOCK, clock)
                g.e.run(6)
                if g.e.w(TMGOALIE) & 0x8000:
                    pulled = f
                    break
            out[f"behind {behind}, {clock} s"] = "pulled" if pulled is not None else "-"
        lowload.breathe()
    return out


def main():
    retail, hack, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    parts = sys.argv[4:] or ["lines", "play", "ratings", "lr", "cpu"]
    lowload.gentle()
    res = json.loads(out.read_text()) if out.exists() else {}
    for part in parts:
        if part == "ratings":
            res["ratings"] = ratings(retail, hack)
        else:
            fn = globals()[f"part_{part}"]
            res[part] = {Path(r).name: fn(r) for r in ((retail, hack) if part in ("lines", "cpu", "lr") else (hack,))}
        out.write_text(json.dumps(res, indent=1, default=str))
        print(part, json.dumps(res[part], default=str)[:3000], flush=True)


if __name__ == "__main__":
    main()
