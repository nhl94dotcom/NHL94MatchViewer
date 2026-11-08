"""What hot / cold is worth, Genesis (2026-11-08; docs/GAME_VARIABLES_PLAN.md study 2: "he's cold").

Each player's working ratings are rating x 5 + his hot / cold value (-3 to +2, one value for all his ratings on the
original ROM's bug: GENESIS_MECHANICS 2.2) + bonuses. The match files keep each player's value (rosters' `hc`) and the
working Agility, Speed, awareness, Shot Power and Shot Accuracy as they played (`work`), which the expected-goals
model reads (the shooter's Shot Accuracy; the goalie's Agility, Speed, awareness and puck control). Every recorded
Genesis game's shots are played out again with the hot / cold taken out of the working values: the shooters only, the
goalies only, and both; the change in each team's expected goals is what hot / cold did that game. Games on ROMs whose
hot / cold couldn't be read (no `hc`) are left out. Gentle (lowload).

python analysis/hot_cold_worth.py [genesis | snes]   (SNES: the sign bug's maxed ratings back to their step, aidef as
                                                    played; SA-1 games have no xG)"""
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "analysis" / "scoring_map"))
import xg  # noqa: E402
import xg_snes  # noqa: E402
import systems  # noqa: E402
from share_game import load_js_object  # noqa: E402
from systems.common import DIGITS  # noqa: E402
import lowload  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
WHICH = sys.argv[1] if len(sys.argv) > 1 else "genesis"


def neutral(m, who):
    """A copy of match m with hot / cold taken out of the working ratings of who: 'shooters' (skaters), 'goalies', or
    'both'."""
    m2 = copy.deepcopy(m)
    rows = []
    for row in m2["work"]:
        f, k = row[0], row[1]
        team = k // 6
        ch = m2["roster"][f * 12 + k]
        idx = DIGITS.index(ch) if ch in DIGITS else -1
        r = m2["rosters"][team][idx] if 0 <= idx < len(m2["rosters"][team]) else None
        goalie = m2["role"][f * 12 + k] == "0"
        hc = (r or {}).get("hc")
        if hc is not None and (who == "both" or (who == "goalies") == goalie):
            row = row[:2] + [row[2]] + [max(0, min(30, v - hc)) for v in row[3:]]   # weight takes no hot / cold
        rows.append(row)
    m2["work"] = rows
    return m2


SNES_COLS = {3: 1, 4: 2, 6: 5, 7: 9}     # work row column -> rating number (Agility, Speed, Shot Power / puck control,
                                         # Shot Accuracy); weight takes no hot / cold, aidef (column 5) is left as played


def neutral_snes(m, who):
    """The SNES version: each rating's hot / cold (rosters' `hcs`: 0, +1..+3, or 'max' where the sign bug maxed it,
    SNES_MECHANICS 2.2) taken out of the working values; a maxed rating goes back to its step's (step x 5) / 2 plus the
    team's bonus for it, read from teammates at the same moment whose rating wasn't maxed."""
    m2 = copy.deepcopy(m)
    info = []
    for row in m2["work"]:
        f, k = row[0], row[1]
        team = k // 6
        ch = m2["roster"][f * 12 + k]
        idx = DIGITS.index(ch) if ch in DIGITS else -1
        r = m2["rosters"][team][idx] if 0 <= idx < len(m2["rosters"][team]) else None
        info.append((row, team, r, m2["role"][f * 12 + k] == "0"))
    bonus = {}
    for row, team, r, goalie in info:                     # the team's bonus per rating at each moment
        if not r or "hcs" not in r:
            continue
        for col, ri in SNES_COLS.items():
            hc = r["hcs"][ri]
            if hc != "max" and row[col] < 15:
                bonus.setdefault((row[0], team, ri), []).append(row[col] - (r["a"][ri] * 5 // 2 + hc))
    rows = []
    for row, team, r, goalie in info:
        if r and "hcs" in r and (who == "both" or (who == "goalies") == goalie):
            row = list(row)
            for col, ri in SNES_COLS.items():
                hc = r["hcs"][ri]
                if hc == "max":
                    b = sorted(bonus.get((row[0], team, ri), [0]))
                    row[col] = max(0, min(15, r["a"][ri] * 5 // 2 + b[len(b) // 2]))
                elif hc:
                    row[col] = max(0, min(15, row[col] - hc))
        rows.append(row)
    m2["work"] = rows
    return m2


def team_xg(m):
    out = [0.0, 0.0]
    for sh in m.get("shotList", []):
        if sh.get("xg") is not None and sh["team"] in (0, 1) and sh["result"] != "blocked":
            out[sh["team"]] += sh["xg"]
    return out


def run(m, rom):
    if m.get("system") == "snes":
        xg_snes._CACHE.clear()
        xg_snes.add_expected_goals(m, rom)
    else:
        xg._CACHE.clear()
        xg.add_expected_goals(m, stick_rom=rom, lock=True)
    return team_xg(m)


def main():
    lowload.gentle()
    rows = []
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season" or p.stem.endswith(".heat") or not (HOME / "captures" / p.stem).is_dir():
            continue
        m = json.loads(load_js_object(p))
        snes = m.get("system") == "snes"
        if (snes != (WHICH == "snes")) or not m.get("work"):
            continue
        if not any(r.get("hcs" if snes else "hc") is not None for side in m["rosters"] for r in side):
            continue
        system = systems.of_match(m)
        rom_path, _ = system.find_rom(HOME / "captures" / p.stem)
        rom = Path(rom_path).read_bytes() if rom_path and Path(rom_path).exists() else None
        stored = team_xg(m)
        base = run(copy.deepcopy(m), rom)
        if max(abs(stored[t] - base[t]) for t in (0, 1)) > 0.05:
            print(f"{p.stem}: the rerun's xG {base} differs from the stored {stored}", flush=True)
        res = {who: run((neutral_snes if snes else neutral)(m, who), rom) for who in ("shooters", "goalies", "both")}
        goals = [m["score"][-2], m["score"][-1]]
        rows.append((p.stem, goals, base, res))
        d = [base[t] - res["both"][t] for t in (0, 1)]
        print(f"{p.stem:32s} goals {goals[0]}-{goals[1]}  xG {base[0]:.2f}-{base[1]:.2f}; hot / cold added "
              f"{d[0]:+.2f} / {d[1]:+.2f} (shooters {base[0] - res['shooters'][0]:+.2f} / {base[1] - res['shooters'][1]:+.2f}, "
              f"goalies against {base[0] - res['goalies'][0]:+.2f} / {base[1] - res['goalies'][1]:+.2f})", flush=True)
        lowload.breathe()
    if not rows:
        return
    n = len(rows)
    swing = [abs((b[0] - r["both"][0]) - (b[1] - r["both"][1])) for _, _, b, r in rows]
    team = [abs(b[t] - r["both"][t]) for _, _, b, r in rows for t in (0, 1)]
    xgd = [abs(b[0] - b[1]) for _, _, b, _ in rows]
    print(f"\n{n} games: hot / cold changed a team's expected goals by {sum(team) / len(team):.2f} on average "
          f"(largest {max(team):.2f}); the expected-goal difference between the teams by {sum(swing) / n:.2f} a game "
          f"(largest {max(swing):.2f}), against an average expected-goal difference of {sum(xgd) / n:.2f}")
    flips = sum(1 for _, _, b, r in rows if (b[0] - b[1]) * (r["both"][0] - r["both"][1]) < 0)
    print(f"games where hot / cold changed which team had the better chances: {flips} of {n}")


if __name__ == "__main__":
    main()
