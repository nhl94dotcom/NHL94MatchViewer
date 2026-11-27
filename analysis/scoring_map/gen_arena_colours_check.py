"""NOSE4Web's per-home-team arena colours, played (Genesis NHL '94, 2026-11-27; nhl94_arena_colours.bin B446AC6C:
setupIceRinkPal ($16C96) jumps to a hook at $FFAC0 that copies the rink palettes as before, then by HomeTeam ($C330)
puts a word from its table ($FFAFC, 4 bytes a team: colour 5 then colour 9 of palette line 0, $FFFF = keep) into
palfadenew ($BD28 + 10 / + 18). Boston: black trim, blue markings; Montreal: red trim; Toronto: green markings).

The control is a scratch copy of retail with the build's two other changes (the checksum call at $300 NOPed, the
checksum word), so both ROMs run the same frames. For each home team (the visitor Detroit; Opt1team / Opt2team set
on Game Setup) each ROM: power-on, Game Setup, into play; the colour memory (Genesis Plus GX's state) and palfadenew
at the opening faceoff, every 300 frames of play, after a horizontal-rink stretch (sflags bit 7: penalties, the
pause screens), after an instant replay (pause, Instant Replay, back to play), and across the end of period 1 into
period 2 (the clock set to 0:02). Screenshots at each; the two ROMs' screenshots compared pixel by pixel: the colour
pairs that differ, and where.

`highlight`: Playoffs: the game reached through the menu, then at period 1's end every other game structure
(gstruct $CE66, 16 bytes each: home team at +0, visitor +2, flags +$E bit 1 = highlight wanted) given a home team
and a highlight request, so Intermission plays them (setupice_highlight): the colours during each highlight against
its home team, and the real game's colours after.

python gen_arena_colours_check.py OUT CONTROL ARENA [highlight]"""
import json
import subprocess
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu
from gen_score_logo_check import VRAM_AT

TEAM1, TEAM2, PLAYMODE = 0xD04C, 0xD04E, 0xD04A
HOMETEAM, VISTEAM, GSP, CLOCK, SFLAGS, SCREEN, PAL = 0xC330, 0xC332, 0xC466, 0xC468, 0xC2EC, 0xFFF7, 0xBD28
GSTRUCT, GSSIZE = 0xCE66, 0x10
CASES = {"BOS": 1, "MTL": 11, "TOR": 22, "CHI": 4, "LA": 10}
DET = 6


def gen_word(v9):
    """Genesis Plus GX keeps colours as 9 bits BBBGGGRRR; the 68000's form is $0BGR (each 3 bits, shifted by 1)."""
    r, g, b = v9 & 7, v9 >> 3 & 7, v9 >> 6 & 7
    return f"${b << 9 | g << 5 | r << 1:04X}"


def colours(e):
    st = bytes(e.serialize())
    cram = [st[VRAM_AT + 0x10000 + 2 * i] | st[VRAM_AT + 0x10001 + 2 * i] << 8 for i in range(16)]
    return {"cram5": gen_word(cram[5]), "cram9": gen_word(cram[9]), "ram5": f"${e.w(PAL + 10):04X}",
            "ram9": f"${e.w(PAL + 18):04X}", "home": e.w(HOMETEAM), "vis": e.w(VISTEAM), "gsp": e.w(GSP),
            "screen": e.b(SCREEN), "hor": e.b(SFLAGS) >> 7 & 1}


class Run:
    def __init__(self, rom, out):
        self.e = Emu(rom)
        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        self.log = []

    def snap(self, name):
        e = self.e
        c = colours(e)
        c["name"] = name
        self.log.append(c)
        e.screenshot(self.out / f"{name}.png")

    def press(self, b, n=1):
        G.press(self.e, b, n)

    def to_play(self, home, vis, playoffs=False):
        e = self.e
        G.to_setup(e, self.out)
        if playoffs:
            for _ in range(6):
                if e.w(PLAYMODE) == 1:
                    break
                self.press("RIGHT")
            e.screenshot(self.out / "setup_mode.png")
        else:
            from gen_team_play_check import pick
            self.press("DOWN", 2)
            pick(e, TEAM1, home, self.out, "setup_home")
            self.press("DOWN")
            pick(e, TEAM2, vis, self.out, "setup_visitor")
        return G.into_play(e)

    def play(self, frames, tag, every=300):
        """Plays on, a snapshot every `every` frames and after each horizontal stretch ends."""
        e = self.e
        hor = e.b(SFLAGS) >> 7 & 1
        k = n = 0
        for f in range(frames):
            e.run(1)
            h = e.b(SFLAGS) >> 7 & 1
            if hor and not h:
                n += 1
                e.run(90)
                self.snap(f"{tag}_after_hor{n}")
            if h and not hor:
                self.snap(f"{tag}_hor{n + 1}")
            hor = h
            if f % every == every - 1:
                k += 1
                self.snap(f"{tag}_{k:02d}")

    def replay(self):
        e = self.e
        self.press("START")
        e.run(60)
        self.press("DOWN")
        e.run(20)
        e.screenshot(self.out / "pause_menu.png")
        self.press("C")
        e.run(120)
        self.snap("in_replay")
        e.run(240)
        self.snap("in_replay_2")
        G.into_play(e)                          # START until play runs again
        e.run(60)
        self.snap("after_replay")

    def pause_resume(self):
        e = self.e
        self.press("START")
        e.run(90)
        self.snap("paused")
        G.into_play(e)
        e.run(60)
        self.snap("after_pause")

    def period_end(self, tag, highlight_teams=None):
        e = self.e
        e.setw(CLOCK, 2)
        start = e.w(GSP)
        home0 = e.w(HOMETEAM)
        if highlight_teams:
            for i, t in highlight_teams.items():    # the first flagged game from the top (index 5 here) plays; the rest are skipped
                a = GSTRUCT + i * GSSIZE
                e.setw(a, t)
                e.setw(a + 0xE, (e.w(a + 0xE) | 0x0200) & ~0x0400)    # gsflags is the byte at +$E: bit 1 highlight wanted, bit 2 series over
        still = last = 0
        shots = 0
        seen_hl = set()
        for f in range(30000):
            wait = 4000 if highlight_teams else 300      # START during the ticker skips the highlights
            hold = ["START"] if still >= wait and still % wait == 0 and e.w(HOMETEAM) == home0 else []
            e.run(1, hold=hold)
            if e.w(HOMETEAM) != home0 and f % 30 == 0:
                seen_hl.add(e.w(HOMETEAM))
                self.snap(f"{tag}_hl_{f:05d}_home{e.w(HOMETEAM)}")
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if f % 120 == 0:
                shots += 1
                self.snap(f"{tag}_inter_{shots:03d}")
            if e.w(GSP) != start:
                if highlight_teams:                 # no presses: the ticker, then the highlights, then back
                    back = None
                    for g in range(25000):
                        e.run(1)
                        h = e.w(HOMETEAM)
                        if h != home0 and g % 30 == 0:
                            seen_hl.add(h)
                            self.snap(f"{tag}_hl_{g:05d}_home{h}")
                        elif g % 300 == 0:
                            self.snap(f"{tag}_wait_{g:05d}")
                        if seen_hl and h == home0:
                            back = g if back is None else back
                            if g - back == 30:
                                self.snap(f"{tag}_after_highlights")
                            if g - back > 600:
                                break
                ok = G.into_play(e)
                e.run(60)
                self.snap(f"{tag}_next_period")
                return ok
        return False


def one(rom, out, case):
    r = Run(rom, out / case)
    if case == "highlight":
        ok = r.to_play(None, None, playoffs=True)
        r.snap("start")
        r.log.append({"gstruct": [[r.e.w(GSTRUCT + i * GSSIZE + k) for k in (0, 2, 0xE)] for i in range(8)]})
        r.period_end("p1", highlight_teams={5: 1})        # Boston home in the highlight
        r.period_end("p2", highlight_teams={5: 22})       # Toronto home
    else:
        ok = r.to_play(CASES[case], DET if CASES[case] != DET else 4)
        r.snap("faceoff")
        r.play(1800, "play")
        r.pause_resume()
        r.replay()
        r.play(600, "after_replay_play")
        r.period_end("p1")
        r.play(600, "p2")
    (out / case / "log.json").write_text(json.dumps({"reached_play": ok, "log": r.log}, indent=1))
    lowload.breathe()


def compare(out, case):
    from PIL import Image, ImageChops
    a, b = out / "control" / case, out / "arena" / case
    rows = []
    pairs_all = {}
    sheet = []
    for p in sorted(a.glob("*.png")):
        q = b / p.name
        if not q.exists():
            continue
        x, y = Image.open(p).convert("RGB"), Image.open(q).convert("RGB")
        if x.size != y.size:
            rows.append((p.stem, "size differs"))
            continue
        box = ImageChops.difference(x, y).getbbox()
        pairs = {}
        if box:
            px, py = x.load(), y.load()
            for j in range(box[1], box[3]):
                for i in range(box[0], box[2]):
                    if px[i, j] != py[i, j]:
                        k = (px[i, j], py[i, j])
                        pairs[k] = pairs.get(k, 0) + 1
            sheet.append((x, y, p.stem))
        for k, v in pairs.items():
            pairs_all[k] = pairs_all.get(k, 0) + v
        rows.append((p.stem, box, sorted(((f"{k[0]}->{k[1]}", v) for k, v in pairs.items()), key=lambda t: -t[1])[:4]))
    return rows, pairs_all, sheet


def main():
    out = Path(sys.argv[1])
    control, arena = sys.argv[2], sys.argv[3]
    cases = ["highlight"] if "highlight" in sys.argv[4:] else list(CASES)
    for case in cases:
        for name, rom in (("control", control), ("arena", arena)):
            subprocess.run([sys.executable, __file__, "--one", rom, str(out / name), case], check=True)
        for name in ("control", "arena"):
            log = json.loads((out / name / case / "log.json").read_text())
            print(f"== {case} {name}: reached play {log['reached_play']}")
            last = None
            for c in log["log"]:
                if "gstruct" in c:
                    print("   gstruct", c["gstruct"])
                    continue
                key = (c["cram5"], c["cram9"], c["ram5"], c["ram9"], c["home"], c["vis"])
                if key != last or c["name"] in ("faceoff", "after_pause", "after_replay", "p1_next_period"):
                    print("  ", c)
                last = key
        rows, pairs, sheet = compare(out, case)
        print(f"-- {case}: screenshots differing {sum(1 for r in rows if r[1])} of {len(rows)}; colour pairs over all:",
              sorted(((f"{k[0]}->{k[1]}", v) for k, v in pairs.items()), key=lambda t: -t[1])[:8])
        for r in rows:
            if r[1]:
                print("   ", r)
        if sheet:
            from PIL import Image
            w, h = sheet[0][0].size
            pick = sheet[:: max(1, len(sheet) // 6)][:6]
            img = Image.new("RGB", (w * len(pick), 2 * h))
            for k, (x, y, _) in enumerate(pick):
                img.paste(x, (k * w, 0))
                img.paste(y, (k * w, h))
            img.save(out / f"sheet_{case}.png")


if __name__ == "__main__":
    if sys.argv[1] == "--one":
        one(sys.argv[2], Path(sys.argv[3]), sys.argv[4])
    else:
        main()
