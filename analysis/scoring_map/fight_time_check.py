"""NOSE4Web's fighting penalty time (e5238ca: a fight's box time set in seconds, the minutes and PIM as before), played
(2026-11-13), both systems. Computer games with fights on; every player who goes to the box is followed once a second
(game clock): his tmpdst word when he goes in (box seconds: Genesis the low 11 bits, SNES the low 12; flags $4000
coincidental, $2000 just called, $1000 kept), whether he had just been in a fight (Genesis pf2fight +$63 bit 0, SNES
pflags $1283 bit $0400, within 30 s real before), his penalty minutes before and after (Genesis team block +$102 +
roster; SNES ppenmin $198A + roster, +$1A the visitors), both teams' tmap while he sits (Genesis team +$24; SNES $17A6),
the box seconds he served by the clock (counting only seconds the clock ran), and the word he leaves with ($FFFE bench,
0, $1000 ...).

Genesis: gen_ot_check's boot, the computer on both sides, Fighting On ($FFF080 = 1), penalties On Except Off-sides,
every player's fighting rating (+$74) 14; --force: +$75 at $7F so chaos's patch hurts the loser (gen_fight_injury_track).
SNES: snes_ot_goal_check.start, OptFights ($E708) 0 (On) where the build has the option (SA-1 / 2 MB: snes.SA1_MOVED).

--fighters (SNES): every skater's fighting rating ($1463) held at 14 (McMarkis's 1 MB fights come from it).
--injure (SNES): every skater's Aggression ($1443) at 60, so the fight's loser is always hurt (F_fightfall: hurt when a
random number under 60 is at most the winner's Aggression); a player who leaves the box at $FFFC is then followed to
the game's end ("after": every change of his word).
Penalty minutes are compared with the sample before he went in (half a second earlier).

python fight_time_check.py genesis|snes ROM GAMES OUT.jsonl [--force] [--option] [--fighters] [--injure]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import lowload  # noqa: E402

FORCE = "--force" in sys.argv
OPTION = "--option" in sys.argv
FIGHTERS = "--fighters" in sys.argv     # SNES: every skater's fighting rating ($1463) held at 14, so the 1 MB build fights
INJURE = "--injure" in sys.argv         # SNES: every skater's Aggression ($1443) at 60, so F_fightfall's roll always hurts
argv = [a for a in sys.argv if not a.startswith("--")]


def s16(v):
    return v - 0x10000 if v >= 0x8000 else v


class Gen:
    TEAMS, TMPDST, TMAP, PIM = (0xC6CE, 0xCA32), 0x66, 0x24, 0x102
    BASE, SZ = 0xB04A, 0x80
    SECS = 0x7FF

    def __init__(self, rom, n, tmp):
        import gen_ot_check as G
        from emu import Emu
        e = self.e = Emu(rom)
        G.to_setup(e, tmp)
        e.setw(0xD056, 2)
        e.setw(0xD050, 0)
        e.setw(0xF080, 1)
        self.ok = G.into_play(e)
        e.setl(0xD066, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)

    def frame(self, f):
        e = self.e
        for k in range(12):
            e.setb(self.BASE + self.SZ * k + 0x74, 14)
            if FORCE:
                e.setb(self.BASE + self.SZ * k + 0x75, 0x7F)
        e.setw(0xF080, 1)
        e.setw(0xD056, 2)
        if f % 60 == 0:
            e.setw(0xC328, 0)
            e.setw(0xC32A, 0)
            for k in range(12):
                e.setb(self.BASE + self.SZ * k + 0x62, e.b(self.BASE + self.SZ * k + 0x62) & ~8)

    def run(self, n, hold):
        self.e.run(n, hold=hold)

    gsp = property(lambda s: s.e.w(0xC466))
    clock = property(lambda s: s.e.w(0xC468))
    stopped = property(lambda s: bool(s.e.b(0xC2EA) & 1))

    def word(self, t, i):
        return self.e.w(self.TEAMS[t] + self.TMPDST + 2 * i)

    def pim(self, t, i):
        return self.e.b(self.TEAMS[t] + self.PIM + i)

    def tmap(self, t):
        return self.e.w(self.TEAMS[t] + self.TMAP)

    def fighters(self):
        e = self.e
        return {(0 if k < 6 else 1, e.b(self.BASE + self.SZ * k + 0x66)) for k in range(12)
                if e.b(self.BASE + self.SZ * k + 0x63) & 1}


class Snes:
    TMPDST, PIM, TMAP, PFLAGS, PNUM, PFTEAM = 0x1852, 0x198A, 0x17A6, 0x1283, 0x12A3, 0x1503
    SECS = 0xFFF

    def __init__(self, rom, n, tmp):
        from snes_ot_goal_check import start
        self.e, self.m = start(rom, n, tmp)
        self.ok = True

    def frame(self, f):
        from snes_60fps_cvc import computer_only
        if FIGHTERS or INJURE:
            for k in range(12):
                if FIGHTERS:
                    self.m.setw(0x1463 + 2 * k, 14)
                if INJURE:
                    self.m.setw(0x1443 + 2 * k, 60)
        if f % 300 == 0:
            computer_only(self.m)
            if OPTION:
                self.m.setw(0xE708, 0)

    def run(self, n, hold):
        self.e.run(n, hold=hold)

    gsp = property(lambda s: s.m.w(0x1630))
    clock = property(lambda s: s.m.w(0x1632))
    stopped = property(lambda s: s.m.w(0x15D6) != 0)

    def word(self, t, i):
        return self.m.w(self.TMPDST + 0x34 * t + 2 * i)

    def pim(self, t, i):
        return self.m.w(self.PIM + 0x1A * t + i) & 0xFF

    def tmap(self, t):
        return self.m.w(self.TMAP + 2 * t)

    def fighters(self):
        m = self.m
        return {(0 if m.w(self.PFTEAM + 2 * k) == 0 else 1, m.w(self.PNUM + 2 * k) & 0xFF) for k in range(12)
                if m.w(self.PFLAGS + 2 * k) & 0x0400}


def game(system, rom, n, tmp):
    g = (Gen if system == "genesis" else Snes)(rom, n, tmp)
    if not g.ok:
        return {"game": n, "error": "never reached play"}
    inbox, done, fought, last_pim, watch = {}, [], {}, {}, {}
    f, still, last = 0, 0, None
    while g.gsp < 3 and f < 60 * 60 * 40:
        g.frame(f)
        g.run(1, ["START"] if still >= 8 and f % 60 < 4 else [])
        f += 1
        for who in g.fighters():
            fought[who] = f
        if f % 30:
            continue
        c = g.clock
        if f % 60 == 0:
            still = still + 1 if c == last else 0
        for t in (0, 1):
            for i in range(26):
                w = g.word(t, i)
                key = (t, i)
                pos = 0 < w < 0x8000
                if pos and key not in inbox:
                    inbox[key] = {"team": t, "roster": i, "in": [g.gsp, c], "f": f, "first": f"{w:04X}", "words": [f"{w:04X}"],
                                  "fight": f - fought.get(key, -10 ** 9) < 1800, "pim_before": last_pim.get(key, g.pim(t, i)),
                                  "tmaps": set(), "served": 0, "lastc": c, "lastp": g.gsp}
                if key not in inbox:
                    last_pim[key] = g.pim(t, i)
                if key in inbox:
                    b = inbox[key]
                    if pos:
                        if f"{w:04X}" != b["words"][-1] and len(b["words"]) < 4:
                            b["words"].append(f"{w:04X}")
                        if g.gsp == b["lastp"] and c < b["lastc"]:
                            b["served"] += b["lastc"] - c
                        b["lastc"], b["lastp"] = c, g.gsp
                        if not g.stopped:
                            b["tmaps"].add((g.tmap(0), g.tmap(1)))
                        b["secs_now"] = w & g.SECS
                        if w & 0x1000 and (w & g.SECS) == 0:      # $1000 with no time: out of the box list for good
                            b["out"], b["left_word"] = [g.gsp, c], f"{w:04X}"
                            b["pim_after"] = g.pim(t, i)
                            done.append(b)
                            del inbox[key]
                    else:
                        b["out"], b["left_word"], b["pim_after"] = [g.gsp, c], f"{w:04X}", g.pim(t, i)
                        b["after"] = []
                        if w == 0xFFFC:                    # out for the game: follow his word to the end
                            watch[key] = b
                        done.append(b)
                        del inbox[key]
                if key in watch and not pos:
                    b = watch[key]
                    if not b["after"] or b["after"][-1][2] != f"{w:04X}":
                        b["after"].append([g.gsp, c, f"{w:04X}"])
        last = c
    for b in list(inbox.values()):
        b["out"], b["left_word"], b["pim_after"] = None, f"{g.word(b['team'], b['roster']):04X}", g.pim(b["team"], b["roster"])
        done.append(b)
    for b in done:
        b["tmaps"] = sorted(b["tmaps"])
        b.pop("lastc", None)
        b.pop("lastp", None)
    return {"game": n, "frames": f, "box": done}


def main():
    system, rom, games, out = argv[1], argv[2], int(argv[3]), Path(argv[4])
    lowload.gentle()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "_boot"
    tmp.mkdir(parents=True, exist_ok=True)
    for n in range(games):
        r = game(system, rom, n, tmp)
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        box = r.get("box", [])
        print(json.dumps({"game": n, "frames": r.get("frames"), "box entries": len(box),
                          "fight entries": sum(b["fight"] for b in box), "error": r.get("error")}), flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
