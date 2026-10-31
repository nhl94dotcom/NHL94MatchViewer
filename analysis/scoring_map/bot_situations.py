"""Real game situations for the scripted bot (2026-10-31, docs/BOT_PLAN.md phase 1): moments from the user's recorded
Genesis games (the match files in Documents\\NHL94 Viewer\\matches, or NHL94_HOME), each turned into the positions,
speeds and facings of all 12 records and the puck, for bot_scenario.py to place in the harness and let the bot play
on from. Kinds: "entry", every carried zone entry (the converter's zoneEntries, kind "carried"), at the sample the
carrier crosses the blue line; "pass", every one-timer in the games (the shot list's kind "one-timer"), PASS_LAG
samples before its pass left the stick (the passer still has the puck), with the passer and the receiver (who struck
it) and whether it scored: the bot then makes that pass (B toward him) and the one-timer. (A puck placed in flight
doesn't work: the game starts a one-timer only for a pass it made itself, passReceiverPlayerNum, with C pressed by
the passer's pad; so the bot makes the pass.) "zone": possessions already in the attacking zone (not entries: a check on the
others), the sample 0.5 s into each spell with the puck on one skater, if he is then 40-180 out from the goal line and
no zone entry by his team falls within 2 s.

Each situation is put in the bot's frame: the attacking team's records become Home (records 0-5 by position: 0 G,
1 LD, 2 RD, 3 LW, 4 C, 5 RW), the other team's Away, and the rink is turned 180 degrees when the attackers were going
down the ice, so that the attack is always up the ice (Home in period 1, as in bot_start.state). Speeds come from the
positions over the samples around the moment (the match file samples about every 15 ms; units a game frame, 60 a
second). Skips moments with a player missing (a penalty, a pulled goalie). Positions only, no names: the output stays
in the work folder, not the repo.
python bot_situations.py   -> paths.WORK / bot_situations.json"""
import json
import math
import os
import sys
from pathlib import Path

from paths import WORK

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from share_game import load_js_object  # noqa: E402

K = 12
HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
FRAME_MS = 1000 / 60


def xy(m, f, k):
    return m["pos"][(f * K + k) * 2], m["pos"][(f * K + k) * 2 + 1]


def speed(m, f, k, span=4):
    """Units a game frame over about span samples before f."""
    a = max(0, f - span)
    dt = (m["t"][f] - m["t"][a]) / FRAME_MS
    if dt <= 0:
        return 0.0, 0.0
    (x0, y0), (x1, y1) = xy(m, a, k), xy(m, f, k)
    return (x1 - x0) / dt, (y1 - y0) / dt


PASS_LAG = -2


def situation(m, f, team, kind, name, owner=None):
    roles = m["role"][f * K:(f + 1) * K]
    owner = m["owner"][f] if owner is None else owner
    if owner < 0 or not team * 6 <= owner < team * 6 + 6:
        return None
    up = (m["period"][f] % 2 == 0) == (team == 0)        # Home attacks up in periods 1 and 3 (0-based 0, 2)
    r = 1 if up else -1                                  # 180 degrees when going down
    out = {"kind": kind, "src": [name, f], "us": {}, "them": {}}
    for k in range(K):
        if roles[k] not in "012345":
            continue
        x, y = xy(m, f, k)
        vx, vy = speed(m, f, k)
        side = "us" if k // 6 == team else "them"
        out[side][roles[k]] = [round(r * x, 1), round(r * y, 1), round(r * vx, 3), round(r * vy, 3),
                               (int(m["facing"][f * K + k]) + (0 if up else 4)) % 8]
        if k == owner:
            out["carrier"] = roles[k]
    if len(out["us"]) < 6 or len(out["them"]) < 6:
        return None
    px, py, pz = m["puck"][f * 3:f * 3 + 3]
    out["puck"] = [round(r * px, 1), round(r * py, 1)]
    if kind == "pass":
        a = max(0, f - 2)
        dt = (m["t"][f] - m["t"][a]) / FRAME_MS
        qx, qy = m["puck"][a * 3:a * 3 + 2]
        out["pv"] = [round(r * (px - qx) / dt, 3), round(r * (py - qy) / dt, 3)] if dt > 0 else [0, 0]
    return out


def main():
    rows = []
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.name.endswith(".summary.json") or p.stem == "season":
            continue
        try:
            m = json.loads(load_js_object(p))
        except (ValueError, OSError):
            continue
        if m.get("system") != "genesis" or "pos" not in m:
            continue
        n0 = len(rows)
        for z in m.get("zoneEntries", []):
            if z.get("kind") == "carried":
                s = situation(m, z["f"], z["team"], "entry", p.stem)
                if s:
                    rows.append(s)
        entries = [m["t"][z["f"]] for z in m.get("zoneEntries", [])]
        f, n = 0, len(m["t"])
        while f < n:
            o = m["owner"][f]
            if o < 0 or m["role"][f * K + o] == "0":
                f += 1
                continue
            g = f
            while g + 1 < n and m["owner"][g + 1] == o:
                g += 1
            h = next((q for q in range(f, g + 1) if m["t"][q] - m["t"][f] >= 500), None)
            if h is not None:
                team = o // 6
                up = (m["period"][h] % 2 == 0) == (team == 0)
                out = 264 - (1 if up else -1) * xy(m, h, o)[1]
                if 40 < out < 180 and not any(abs(t - m["t"][h]) < 2000 for t in entries):
                    s = situation(m, h, team, "zone", p.stem)
                    if s:
                        rows.append(s)
            f = g + 1
        for sh in m.get("shotList", []):
            if sh.get("kind") != "one-timer":
                continue
            pa = max((q for q in m.get("passes", []) if q["team"] == sh["team"] and q["f"] <= sh["f"]
                      and sh["f"] - q["f"] < 120), key=lambda q: q["f"], default=None)
            if pa is None:
                continue
            f = max(0, pa["f"] + PASS_LAG)
            passer = next((k for k in range(sh["team"] * 6, sh["team"] * 6 + 6)
                           if int(m["roster"][pa["f"] * K + k], 36) == pa["idx"]), None)
            striker = next((k for k in range(sh["team"] * 6, sh["team"] * 6 + 6)
                            if int(m["roster"][sh["f"] * K + k], 36) == sh["idx"]), None)
            if passer is None or striker is None:
                continue
            s = situation(m, f, sh["team"], "pass", p.stem, owner=passer)
            if s:
                s["receiver"] = m["role"][f * K + striker]
                s["passer"], s["scored"] = s.pop("carrier"), sh["result"] == "goal"
                s["gctl"] = sh.get("gctl")
                rows.append(s)
        print(p.stem, len(rows) - n0)
    (WORK / "bot_situations.json").write_text(json.dumps(rows))
    print(len(rows), "situations ->", WORK / "bot_situations.json")


if __name__ == "__main__":
    main()
