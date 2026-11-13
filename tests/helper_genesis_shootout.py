"""The helper's Genesis shootout reading (2026-11-13: NOSE4Web's season shootout runs the game's own Shootout mode,
with its flag $FFF082 set and gsp 3). No season-shootout build at hand, so the retail ROM's Shootout mode (Play Mode
4, the computer on both sides) is played headless and read as the helper reads RetroArch, through genesis.View, with
the flag and gsp 3 shown to it while gmode2 bit 0 (Shootout mode) is on. Each frame's View goes to
Recording.shootout_attempt; at the end the attempts must alternate home / away within each round, take their shooters
from the teams' lists in order, and their goals must add up to the game's own shootout goals (homeshootgoals /
awayshootgoals).

--season (with a season-shootout build, e.g. NOSE4Web's nhl94_season_shootout.bin): the real thing, nothing shown to
the View: a regular-season game put at 1-1 with 3 s of overtime left (as gen_shootout_check's `tie`), every frame through
a whole nhl94_helper.Recording until it ends; it must end "final" with shootout.json holding the game's final score
(the overtime score plus the winners' goal) and the attempts as above.

python tests/helper_genesis_shootout.py [ROM] [--season]   (default: the retail ROM analysis/scoring_map's emu.py uses)"""
import os
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = os.path.join(tempfile.gettempdir(), "nhl94_helper_home_gshootout")
os.environ["NHL94_HOME"] = HOME
for sub in ("matches", "captures", "sprites", "roms", "shared", "sounds"):
    os.makedirs(os.path.join(HOME, sub), exist_ok=True)
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "analysis" / "scoring_map"))
import nhl94_helper as H  # noqa: E402
from systems import genesis  # noqa: E402
import gen_ot_check as G  # noqa: E402
import lowload  # noqa: E402
from emu import Emu  # noqa: E402

PLAYMODE, GMODE2, CONT1, CONT2, BASE, SZ = 0xD048, 0xC2FA, 0xC328, 0xC32A, 0xB04A, 0x80


HM, AW, GSP_, CLOCK_ = 0xC6DA, 0xCA3E, 0xC466, 0xC468
SEASON = "--season" in sys.argv


class Seen:
    """The headless core's work RAM as RetroArch's reader gives it (little-endian words: Emu.ram's layout), with the
    season shootout's flag and gsp 3 shown while Shootout mode runs."""

    system, teams = "genesis", 28

    def __init__(self, e):
        self.e = e

    def read(self, start, length):
        raw = bytearray(self.e.ram[(start + i) & 0xFFFF] for i in range(length))
        if SEASON:
            return bytes(raw)
        on = self.e.b(GMODE2) & 1
        if on and start <= genesis.PERIOD < start + length:
            raw[genesis.PERIOD - start], raw[genesis.PERIOD + 1 - start] = 3, 0
        if start == genesis.SO_FLAG ^ 1 and length == 1:
            return bytes([0xFF if on else 0])
        return bytes(raw)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rom = args[0] if args else None
    lowload.gentle()
    e = Emu(rom) if rom else Emu()
    tmp = Path(HOME) / "_boot"
    tmp.mkdir(exist_ok=True)
    G.to_setup(e, tmp)
    if SEASON:
        return season(e)
    e.setw(PLAYMODE, 4)
    for _ in range(4):
        e.run(4, hold=["START"])
        e.run(300)
    rec = types.SimpleNamespace()
    seen, started, lists, game_goals = Seen(e), False, None, None
    for f in range(60 * 60 * 30):
        if f % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            if f % 3600 == 0:
                lowload.breathe()
        on = e.b(GMODE2) & 1
        e.run(1, hold=["START"] if not on and f % 150 == 0 else [])
        if not on:
            if started:
                break
            continue
        v = genesis.View(seen)
        if v.shootout:
            started = True
            lists = [[e.w(a + 2 * i) for i in range(6)] for a in genesis.SO_LISTS]
            game_goals = v.score
            H.Recording.shootout_attempt(rec, v)
        if e.b(GMODE2) & 8:                       # shootout over (CountShootoutGoals' gmode2 bit 3)
            started = True
    H.Recording.shootout_attempt(rec, None)
    att = getattr(rec, "so_attempts", [])
    for a in att:
        print(a)
    print("lists (home, away):", lists, "the game's shootout goals:", game_goals)
    ok = check(att, lists, game_goals)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


def check(att, lists, goals):
    ok = bool(att) and goals is not None
    for i, a in enumerate(att):
        ok &= a["team"] == i % 2 and a["round"] == i // 2 + 1
        ok &= a["shooter"] == lists[a["team"]][(a["round"] - 1) % 5]
        ok &= a["goalie"] == lists[1 - a["team"]][5]
    run = [0, 0]                                       # each attempt's score: the running shootout score after it
    for a in att:
        run[a["team"]] += a["goal"]
        ok &= a["score"] == run
    return ok and [sum(a["goal"] for a in att if a["team"] == t) for t in (0, 1)] == list(goals)


def season(e):
    if not G.into_play(e):
        print("never reached play")
        sys.exit(1)
    e.setw(PLAYMODE, 0)
    e.setw(GSP_, 3)
    e.setw(CLOCK_, 3)
    e.setw(HM, 1)
    e.setw(AW, 1)
    H.FINAL_WAIT_S = 0.0
    seen = Seen(e)
    rec = H.Recording(seen, genesis.View(seen), None, None)
    ended, lists, goals, still, last, so_frames, started = None, None, None, 0, None, 0, False
    for f in range(60 * 60 * 40):
        if f % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK_)
            still = still + 1 if c == last else 0
            last = c
            if f % 3600 == 0:
                lowload.breathe()
        on = e.b(GMODE2) & 1
        started = bool(on and (started or e.w(0xD454)))     # the first attempt's clock (shootoutclock) has run:
        e.run(1, hold=["START"] if not started and f % 150 == 0 and f > 300 else [])   # no presses after (pause menu)
        v = genesis.View(seen)
        if v.shootout:
            so_frames += 1
            lists = [[e.w(a + 2 * i) for i in range(6)] for a in genesis.SO_LISTS]
            goals = v.score
        why = rec.step(v)
        if os.environ.get("NHL94_SO_DEBUG") and f % 600 == 0:
            print(f, "gsp", e.w(GSP_), "screen", e.b(0xFFF7), "gmode2", hex(e.b(GMODE2)), "round", e.w(genesis.SO_ROUND),
                  "so goals", v.score if v.shootout else None, "clock", e.w(CLOCK_), "still", still, flush=True)
        if why:
            ended = (f, why, v.describe())
            break
    so = rec.folder / "shootout.json"
    data = __import__("json").loads(so.read_text()) if so.exists() else {}
    for a in data.get("attempts", []):
        print(a)
    print("shootout frames", so_frames, "ended", ended, "final", data.get("final"), "lists", lists, "goals", goals)
    win = goals is not None and goals[0] != goals[1]
    want = [1 + (goals[0] > goals[1]), 1 + (goals[1] > goals[0])] if win else None
    ok = ended is not None and ended[1] == "final" and data.get("final") == want and check(data.get("attempts"), lists, goals)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
