"""Assists that disappear (2026-11-09, the user: "sometimes assists just disappear from a goal", SNES). The game's
touch list (tmtouch1 the scorer, tmtouch2 / tmtouch3 the assists) and its "next touch overwrites" flag (SNES
tmflags bit 2, Genesis tmflast, byte +$30 bit 3), read from every recording with a match, both systems and both game
folders. An opponent picking the puck up (puckglue) wipes the team's assists and sets the flag; the team's next touch
should clear it. But a2touchpuck returns at once when the toucher is already tmtouch1 ("same player"), before the
flag is cleared, so when the last toucher before the turnover wins the puck back himself, the flag stays set and the
teammate he passes to overwrites him: his assist is lost. Counted: goals left unassisted where the scoring team's
first holder after the last opponent possession (the wipe) was the tmtouch1 at that moment and a different player
scored. Aggregates only (-v lists each case by game and roster number).

python analysis/assist_loss_study.py"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
from export_match import Capture  # noqa: E402
import systems  # noqa: E402

sw = lambda v: v - 0x10000 if v >= 0x8000 else v
SNES = dict(t1=lambda o: 0x179A + o, t2=lambda o: 0x179E + o, flag=lambda o: (0x17DE + o, 4), goals=lambda o: 0x178E + o)
GEN_TEAM = (0xC6CE, 0xCA32)


def folders(snes):
    seen = set()
    for home in (Path("."), Path.home() / "Documents" / "NHL94 Viewer"):
        for cap in sorted((home / "captures").glob("*")):
            cj = cap / "capture.json"
            if cj.exists() and (('"snes"' in cj.read_text()) == snes) and (home / "matches" / f"{cap.name}.js").exists() \
                    and cap.name not in seen:
                seen.add(cap.name)
                yield cap


def holder(cap, i, snes):
    """(team, roster number) of the player holding the puck at sample i, or None when it is loose."""
    if snes:
        pc = sw(cap.word(i, 0x0AD9))
        if 0 <= pc < 24 and pc % 2 == 0:
            return (1 if pc // 2 >= 6 else 0), cap.word(i, 0x12A3 + pc)
        return None
    puck = 0xB04A + 14 * 0x80
    if cap.byte(i, puck + 0x60) == 0:
        k = cap.byte(i, puck + 0x61)
        if k < 12:
            return (1 if k >= 6 else 0), cap.byte(i, 0xB04A + k * 0x80 + 0x66)
    return None


def study(snes, verbose=False):
    res, games = Counter(), 0
    for folder in folders(snes):
        try:
            cap = Capture(folder) if snes else Capture(folder, systems.of_capture(folder))
        except Exception:
            continue
        games += 1
        for team in (0, 1):
            if snes:
                o = 2 * team
                T1, T2, FL, FB, G = 0x179A + o, 0x179E + o, 0x17DE + o, 4, 0x178E + o
            else:
                b = GEN_TEAM[team]
                T1, T2, FL, FB, G = b + 0x18, b + 0x1A, b + 0x30, 0x800, b + 0xC
            prevg, wipe_t1, carriers = None, None, []
            for i in range(cap.count):
                h = holder(cap, i, snes)
                if h is not None and h[0] != team:          # an opponent holds it: puckglue wiped the assists
                    wipe_t1, carriers = sw(cap.word(i, T1)), []
                elif h is not None and (not carriers or carriers[-1] != h[1]):
                    carriers.append(h[1])
                g = cap.word(i, G)
                if prevg is not None and g == prevg + 1 and g < 30:
                    t1, t2 = sw(cap.word(i - 1, T1)), sw(cap.word(i - 1, T2))
                    res["goals"] += 1
                    if t2 < 0:
                        res["unassisted"] += 1
                        # the bug: the first of the team to hold it after the last opponent's possession was the
                        # last toucher before it, and then a different player scored
                        if wipe_t1 is not None and carriers and carriers[0] == wipe_t1 and t1 != wipe_t1:
                            res["unassisted by the bug"] += 1
                            if verbose:
                                print("  ", folder.name, "team", team, "re-taker", wipe_t1, "carriers", carriers, "scorer", t1)
                    wipe_t1, carriers = None, []
                prevg = g
    return games, dict(res)


if __name__ == "__main__":
    for snes in (True, False):
        g, r = study(snes, verbose="-v" in sys.argv)
        print("SNES" if snes else "Genesis", g, "games:", r)
