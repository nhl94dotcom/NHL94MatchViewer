"""How often the bugs NOSE4Web has fixes for happen in the recorded league games (2026-11-08): which fixes matter most
in real play. The recorded games in the game folder (people's league games, on the original ROMs); counts per game.
Aggregates only.

Genesis:
- rocket passes (pass `rocket`, export_match.add_quirks), runaways (`runaways`), goals through the legs (`five-hole`)
  and shoulder-save bobble goals (`goalie bobble`);
- saves not counted as shots on goal (shotList: a save, not counted), by the direction the shooting team attacked;
- shots with the shooter's own goalie off the ice (doshot shots and one-timers: every one within 200 exact, bug 13);
- faceoffs held off the game's dots (foSpot rows not at centre, a neutral dot or an end dot);
- penalty shots awarded (their codes, $2E and up: each one named for the wrong foul, bug 11).
SNES:
- a person's skater going straight from a fall into the hook / hold (animations $F864 / $F374, what Y starts while
  down: snes_y_button_test), bug 29;
- knocked-off nets (`netsOff`) and penalty shots (bug 27 needs a knocked net or a still puck during one).
Both: the comeback bonus (bugs 3 / 25) is wrong in every game's third period whenever a team is tied or behind, and
the awareness slip (20) and crowd bonus (21, Genesis) are always on; not counted here.

python analysis/bug_frequency.py"""
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402
from xg import attacks_top  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
DOTS = {(0, 0)} | {(x, y) for x in (-70, 70) for y in (-206, -65, 65, 206)}
DOWN_SNES = {"f49c", "f54e", "f6c0", "f90e", "fd3a", "fd9c", "fc76"}   # the falls (not $F46A: about 24 frames, over
# before anyone could cut in). In the recordings the falls that ended on their own lasted a median 106-153 frames
# (608 for $F90E); the ones that went straight into a person's hook / hold, a median 29-38 frames in (22 at the
# least): mid-fall, the bug, not a hook as he got up
Y_ANIMS = {"f864", "f374"}


def games():
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season":
            continue
        try:
            m = json.loads(load_js_object(p))
        except (ValueError, OSError):
            continue
        if "role" in m:
            yield m


def genesis(ms):
    c = Counter()
    for m in ms:
        c["games"] += 1
        c["rocket passes"] += sum(1 for p in m.get("passes", []) if p.get("rocket"))
        c["rocket passes by people"] += sum(1 for p in m.get("passes", []) if p.get("rocket") and p.get("human"))
        c["runaways"] += len(m.get("runaways", []))
        for g in m.get("goals", []):
            c["goals"] += 1
            c["goals through the legs"] += "five-hole" in g.get("kinds", [])
            c["shoulder-bobble goals"] += "goalie bobble" in g.get("kinds", [])
        for s in m.get("shotList", []):
            f, team = s["f"], s["team"]
            up = attacks_top(m, f, team)
            if s["result"] == "save":
                c["saves going " + ("up" if up else "down")] += 1
                if not s.get("counted"):
                    c["uncounted saves going " + ("up" if up else "down")] += 1
            own_in = any(m["role"][f * 12 + k] == "0" for k in range(team * 6, team * 6 + 6))
            if not own_in and s["kind"] in ("shot", "one-timer"):
                aim = s.get("aim") or {}
                if math.hypot(aim.get("x", 0) - s["x"], (264 if up else -264) - s["y"]) <= 200:
                    c["exact shots, own goalie off"] += 1
                    c["  goals from them"] += s["result"] == "goal"
        spots = [(x, y) for _, x, y in m.get("foSpot", [])]
        c["faceoffs"] += len(spots)
        c["faceoffs off a dot"] += sum(1 for s in spots if s not in DOTS)
        c["penalty shots awarded"] += sum(1 for p in m.get("penalties", []) if p.get("code", 0) >= 0x2E)
    return c


def snes(ms):
    c = Counter()
    for m in ms:
        c["games"] += 1
        anim, ctrl, K = m["anim"], m["ctrl"], 12
        n = len(m["t"])
        A = lambda f, k: anim[(f * K + k) * 4:(f * K + k) * 4 + 4]
        for k in range(12):
            for f in range(1, n):
                a0, a1 = A(f - 1, k), A(f, k)
                if a0 in DOWN_SNES and a1 in Y_ANIMS and (ctrl[f] >> k) & 1:
                    c["hooks / holds straight from a fall, people"] += 1
        c["knocked-off nets"] += len(m.get("netsOff", []))
        c["penalty shots"] += sum(1 for g in m.get("goals", []) if "penalty shot" in g.get("kinds", [])) + \
            sum(1 for p in m.get("penalties", []) if p.get("code") == 0x24)
    return c


def show(name, c):
    n = c.pop("games")
    print(f"\n{name}: {n} recorded games")
    for k, v in c.items():
        print(f"  {k:45} {v:5}   ({v / n:.2f} a game)")


def main():
    ms = list(games())
    show("Genesis", genesis([m for m in ms if m.get("system") == "genesis"]))
    show("SNES", snes([m for m in ms if m.get("system") == "snes"]))


if __name__ == "__main__":
    main()
