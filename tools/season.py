"""Stats across games: a small summary of each converted game (matches/<name>.summary.json, made once and remade when
the match file is newer), and all of them together for the season page (season.html).

    python tools/season.py           ->  matches/season.js (window.NHL94_SEASON), so season.html also works opened
                                         straight from the folder; the helper serves the same at /api/season

A summary holds what totals across games: the result, the teams' numbers, and a line per player who played (skaters:
goals, assists, shots, plus/minus, penalty minutes, checks, hits taken, turnovers, ice time; goalies: shots and goals
against, split by whether a person or the computer was in net at the shot). Goals, assists and shots are the game's
own per-player counts (goalies: against), as on the viewer's cards; the rest comes from the converter's event lists.
"""
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from systems.common import ROOT, STAT_FIELDS  # noqa: E402
import deserve  # noqa: E402
from export_match import PASS_DIRS, PUCK_SPEED_SCALE, ZONES, clock_ticks, game_weights, own_end, zone_of  # noqa: E402

VERSION = 24  # 24: SNES controller presses by the SNES button names (A, B, X, Y, L, R, Select); 23: missed tapestries (team tapMiss / tapMissA, skater tapMiss); 22: tapestries (team tap / tapA, skater tapG / tapIn); 21: posts (team posts / postsA, skater posts); 20: the Deserve to Win meter (dtw); 19: checks a person threw (checksHuman); 18: screen sides by direction (sides); 17: expected goals (no xg key without xG); 16: expected goals (tools/xg.py); 15: where shots were aimed; 14: shot speeds, checks that paid off, goalie giveaway goals; 13: nets knocked off; 12: possession by zone (attacking-zone possession per goal); 11: puck time and carried entries by position; 10: passing by zone and direction, puck time by zone; 9: bobbled passes; 8: pucks lost skating into a goalie, apart; 7: pucks lost on body contact (bumps); 6: injuries; 5: person vs computer, controller habits, chance origins, odd-man rushes, wraparounds, pass pairs, shot maps; 4: high danger, shot assists, rebounds, flip rebounds, costly turnovers, zone entries; 2: advanced stats (on-ice Corsi, Fenwick, shots and goals, zone starts); 3: off-ice numbers as "bench"
MATCHES = ROOT / "matches"
PLAYERS = 12


def load_match(path):
    text = path.read_text(encoding="utf-8")
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def played_periods(m):
    """Period indices in which the clock ran (after the final horn the index moves on to 3 and 4 with nothing
    played, which is not overtime)."""
    out = set()
    for i in range(1, len(m["t"])):
        if m["period"][i] == m["period"][i - 1] and m["clock"][i] < m["clock"][i - 1]:
            out.add(m["period"][i])
    return out


def aim_grid(shots):
    """Shots counted on a 3 x 3 grid of where they were aimed, as the shooter sees the net: row 0 high, 1 middle, 2 along
    the ice; column 0 his left, 1 middle, 2 his right (index row * 3 + column)."""
    out = [0] * 9
    for s in shots:
        a = s["aim"]
        row = 0 if a["z"] >= 10 else 1 if a["z"] >= 3 else 2
        col = 0 if a["x"] < 0 else 1 if a["x"] == 0 else 2
        out[row * 3 + col] += 1
    return out


def shot_mph(speed):
    """A shot's speed (the shot list's, in the game's speed units) in mph at the skating scale."""
    return speed * PUCK_SPEED_SCALE / (536 / 178) * 3600 / 5280


def puck_seconds_by_zone(m):
    """Game seconds with the puck on a skater's stick: ({(team, roster index): [in his defensive, neutral, attacking
    zone]}, [per team: 15 = zone x the carrier's position then, LD, RD, LW, C, RW]). Each second the game clock ticks
    off (a new low in the period, at most 3 at a time, as the viewer's possession) goes to the skater who has the puck
    then, by where it is and the position he is playing (line changes move players between positions)."""
    out, t, P, own, K = {}, m["t"], m["puck"], m.get("owner") or [], 12
    by_pos = [[0] * 15, [0] * 15]
    tick = clock_ticks(m)
    for i in range(len(t)):
        if tick[i]:
            ticks = tick[i]
            k = own[i] if i < len(own) else -1
            if k < 0 or m["role"][i * K + k] in "0x" or P[3 * i + 2] < -100:
                continue
            team = 0 if k < 6 else 1
            end = own_end(m, i, team)
            if end is None:
                continue
            idx = int(m["roster"][i * K + k], 36)
            zone = ZONES.index(zone_of(P[3 * i + 1], -end))
            out.setdefault((team, idx), [0, 0, 0])[zone] += ticks
            by_pos[team][zone * 5 + int(m["role"][i * K + k]) - 1] += ticks
    return out, by_pos


SIDE_MIDDLE = 20  # a shot within this of the middle (across) is from the middle, not a side: the posts' width
SIDES_LEN = 19  # numbers per direction in screen_sides


def screen_side_aim(d):
    """The screen side of an aim direction (the stick on the screen: 0 up, 1 up-right ... 7 up-left, 8 none):
    0 left, 1 middle, 2 right."""
    return 2 if d in (1, 2, 3) else 0 if d in (5, 6, 7) else 1


def screen_sides(m):
    """Left / right on the screen, split by which way the team was going (the user: people, maybe the computer too,
    may favour one side of the screen whichever way they attack; Home goes up in periods 1 and 3, Away in 2 and OT).
    Per team, 2 x SIDES_LEN numbers: going up the screen, then going down, each: game seconds with the puck on a
    skater's stick by his position (LD, RD, LW, C, RW: going up the left wing is the screen's left, going down its
    right), then by the puck's half of the screen (left, right); shot attempts from the screen's left / middle / right
    (within SIDE_MIDDLE of the middle) and the goals from them; shots aimed at the screen's left / middle / right (the
    stick at the release) and the goals from them."""
    out = [[0] * (2 * SIDES_LEN), [0] * (2 * SIDES_LEN)]
    t, P, own, K = m["t"], m["puck"], m.get("owner") or [], 12
    tick = clock_ticks(m)
    for i in range(len(t)):
        if not tick[i]:
            continue
        k = own[i] if i < len(own) else -1
        if k < 0 or m["role"][i * K + k] in "0x" or P[3 * i + 2] < -100:
            continue
        team = 0 if k < 6 else 1
        end = own_end(m, i, team)
        if end is None:
            continue
        base = (0 if end < 0 else 1) * SIDES_LEN  # its own goal at the bottom: going up
        out[team][base + int(m["role"][i * K + k]) - 1] += tick[i]
        out[team][base + (5 if P[3 * i] < 0 else 6)] += tick[i]
    for sh in m.get("shotList") or []:
        end = own_end(m, sh["f"], sh["team"])
        if end is None:
            continue
        row, goal = out[sh["team"]], sh.get("result") == "goal"
        base = (0 if end < 0 else 1) * SIDES_LEN
        side = 0 if sh["x"] < -SIDE_MIDDLE else 2 if sh["x"] > SIDE_MIDDLE else 1
        row[base + 7 + side] += 1
        row[base + 10 + side] += goal
        if sh.get("aim"):
            side = screen_side_aim(sh["aim"]["d"])
            row[base + 13 + side] += 1
            row[base + 16 + side] += goal
    return out


def possession_by_zone(m):
    """Each team's possession in game seconds by where the puck was, in its own view: [[attacking, neutral, defensive]
    for Home, for Away], as the viewer counts it: each second the clock ticks off goes to the team with the puck on a
    stick; a loose puck to the team that had it before and gets it next, to neither (transition) if they differ, to the
    one that had it or gets it when only one is known (a whistle or a period's end closes a stretch)."""
    n, own, P = len(m["t"]), m.get("owner") or [], m["puck"]
    team = lambda k: 0 if k < 6 else 1
    hidden = lambda i: P[3 * i + 2] < PUCK_HIDDEN_Z
    before, after = [-1] * n, [-1] * n
    last = -1
    for i in range(n):
        if hidden(i) or (i and m["period"][i] != m["period"][i - 1]):
            last = -1
        if not hidden(i) and own[i] >= 0:
            last = team(own[i])
        before[i] = last
    nxt = -1
    for i in range(n - 1, -1, -1):
        if hidden(i) or (i < n - 1 and m["period"][i] != m["period"][i + 1]):
            nxt = -1
        if not hidden(i) and own[i] >= 0:
            nxt = team(own[i])
        after[i] = nxt
    out, tick = [[0, 0, 0], [0, 0, 0]], clock_ticks(m)
    for i in range(n):
        if not tick[i]:
            continue
        if own[i] >= 0:
            c = team(own[i])
        else:
            a, b = before[i], after[i]
            c = 2 if a < 0 and b < 0 else b if a < 0 else a if b < 0 else a if a == b else 2
        if c == 2:
            continue
        end = own_end(m, i, c)
        if end is None:
            end = next((-e for e in [own_end(m, i, 1 - c)] if e is not None), None)
        if end is None:
            continue
        out[c][["att", "neu", "def"].index(zone_of(P[3 * i + 1], -end))] += tick[i]
    return out


def carried_entries_by_position(m):
    """Per team: carried zone entries by the carrier's position then [LD, RD, LW, C, RW]."""
    out, K = [[0] * 5, [0] * 5], 12
    for e in m.get("zoneEntries", []):
        if e.get("kind") != "carried" or e.get("idx", -1) < 0:
            continue
        f, team = e["f"], e["team"]
        k = next((k for k in range(team * 6, team * 6 + 6) if int(m["roster"][f * K + k], 36) == e["idx"]), None)
        if k is not None and m["role"][f * K + k] not in "0x":
            out[team][int(m["role"][f * K + k]) - 1] += 1
    return out


def summarize(m, name, date=None):
    t, period, clock = m["t"], m["period"], m["clock"]
    n = len(t)
    sides = screen_sides(m)  # left / right on the screen, going up and going down
    dtw = deserve.deserve(m) if m.get("shotList") else None  # the Deserve to Win meter (tools/deserve.py)
    puck_zone, puck_pos = puck_seconds_by_zone(m)  # game seconds with the puck, by skater and zone, and by position
    entry_pos = carried_entries_by_position(m)
    poss = possession_by_zone(m)  # game seconds, [attacking, neutral, defensive] per team in its own view
    score = m["score"][-2:]
    periods = played_periods(m)
    last = max(period) if period else 0
    # The whole game: recorded from the opening faceoff, and on past the end of regulation (the index goes to 3 at
    # the horn; 4 after overtime or, on both systems, a moment after the final horn).
    from_start = bool(n) and period[0] == 0 and m["score"][0] == m["score"][1] == 0
    finished = last >= 4 or (last >= 3 and 3 not in periods and score[0] != score[1])
    overtime = 3 in periods
    seconds = sum(max(0, min(3, clock[i - 1] - clock[i])) for i in range(1, n) if period[i] == period[i - 1])

    st = m.get("stats") or {}
    per, base = st.get("p", 7), st.get("n", len(STAT_FIELDS))
    final = [st["home"][-1], st["away"][-1]] if st.get("f") else [[], []]
    team_value = lambda team, field: final[team][STAT_FIELDS.index(field)] if len(final[team]) > STAT_FIELDS.index(field) else 0

    rosters = m.get("rosters") or [[], []]
    # Who was on the ice at frame f: roster indices per team
    def on_ice(f):
        out = (set(), set())
        for k in range(PLAYERS):
            c = m["role"][f * PLAYERS + k] if m.get("role") else "x"
            if c != "x":
                idx = int(m["roster"][f * PLAYERS + k], 36)
                if idx < len(rosters[k // 6]):
                    out[k // 6].add(idx)
        return out

    # Teams a person played: a controller drove it (padTeam, pad2Team), or failing that one of its skaters carried
    # the joystick marker for most of the game.
    humans = [False, False]
    for key in ("padTeam", "pad2Team"):
        if m.get(key, -1) in (0, 1):
            humans[m[key]] = True
    if not any(humans) and m.get("ctrl"):
        for team in (0, 1):
            mask = 0x3F << (6 * team)
            humans[team] = sum(1 for c in m["ctrl"] if c & mask) > 0.5 * n

    shots, goals, hits = m.get("shotList", []), m.get("goals", []), m.get("hits", [])
    xg_shots = [s for s in shots if "xg" in s and s["result"] != "blocked"]  # expected goals: unblocked shots the model played out
    turnovers, penalties, rules = m.get("turnovers", []), m.get("penalties", []), m.get("rules", {})
    faceoffs = [e for e in m.get("faceoffs", []) if e.get("won") in (0, 1)]
    entries = m.get("zoneEntries", [])
    # Odd-man rushes: carried or passed entries with more attackers than defenders back, at least two attackers.
    odd_rushes = lambda team: [e for e in entries if e["team"] == team and e["kind"] in ("carried", "passed")
                               and len(e.get("odd") or []) == 2 and e["odd"][0] >= 2 and e["odd"][0] > e["odd"][1]]
    rush_shots = lambda e: [s for s in shots if s["team"] == e["team"] and s.get("origin") == "rush" and e["f"] <= s["f"] <= e.get("end", e["f"])]

    def pass_pairs(team):
        # Passes between each pair of teammates: "passer>receiver": [passes, completed, shot attempts off them]
        out = {}
        for p in m.get("passes", []):
            if p["team"] != team or p.get("to", -1) < 0:
                continue
            row = out.setdefault(f'{p["idx"]}>{p["to"]}', [0, 0, 0])
            row[0] += 1
            row[1] += p["result"] in ("completed", "one-timer")
        for s in shots:
            if s["team"] == team and "assist" in s:
                out.setdefault(f'{s["assist"]}>{s["idx"]}', [0, 0, 0])[2] += 1
        return out
    entry_shot = lambda e: any(s["team"] == e["team"] and e["f"] <= s["f"] <= e.get("end", e["f"]) for s in shots)
    # High-danger attempts by a team: all of them, the goals, or the shots on goal (as the game counts them)
    hd_of = lambda side, want: sum(1 for s in shots if s["team"] == side and s.get("danger") == "high" and
                                   (want is None or (want == "goal" and s["result"] == "goal") or
                                    (want == "sog" and (s.get("counted") or s["result"] == "goal"))))

    # The game-winning goal: the winner's goal that took them past the loser's final total.
    gwg = None
    if finished and score[0] != score[1]:
        winner = 0 if score[0] > score[1] else 1
        mine = [g for g in goals if g["team"] == winner]
        if len(mine) > score[1 - winner]:
            gwg = mine[score[1 - winner]]

    teams = []
    for team in (0, 1):
        other = 1 - team
        teams.append({
            "gf": score[team], "ga": score[other],
            "sog": team_value(team, "shots"), "sa": team_value(other, "shots"),
            "att": sum(1 for s in shots if s["team"] == team), "attA": sum(1 for s in shots if s["team"] == other),
            "posts": sum(1 for s in shots if s["team"] == team and s["result"] == "post"),
            "postsA": sum(1 for s in shots if s["team"] == other and s["result"] == "post"),
            "tap": sum(1 for g in goals if g["team"] == team and g.get("tapestry")),
            "tapA": sum(1 for g in goals if g["team"] == other and g.get("tapestry")),
            "tapMiss": sum(1 for s in shots if s["team"] == team and s.get("tapestry") and s["result"] != "goal"),
            "tapMissA": sum(1 for s in shots if s["team"] == other and s.get("tapestry") and s["result"] != "goal"),
            "ppg": team_value(team, "ppGoals"), "ppTries": team_value(team, "ppTries"),
            "ppgA": team_value(other, "ppGoals"), "pkTimes": team_value(other, "ppTries"),
            "shg": team_value(team, "shGoals"),
            "pen": sum(1 for p in penalties if p["team"] == team),
            "pim": sum((rules.get(str(p["code"])) or {}).get("min", 0) for p in penalties if p["team"] == team),
            "fow": sum(1 for e in faceoffs if e["won"] == team), "fo": len(faceoffs),
            "checks": team_value(team, "checks"),
            "bigHits": sum(1 for h in hits if h["team"] == team and h.get("outcome") in ("upended", "into the boards", "into the bench")),
            "puckPos": puck_pos[team],  # game seconds with the puck: zone (def, neu, att) x carrier's position (LD, RD, LW, C, RW)
            "entryPos": entry_pos[team],  # carried zone entries by the carrier's position
            "sides": sides[team],  # screen sides going up, then going down (screen_sides)
            # Deserve to Win: [win (incl. overtime), overtime win, tie, overtime loss], each a chance
            **({"dtw": [round(dtw["win"][team], 4), round(dtw["otWin"][team], 4), round(dtw["tie"], 4), round(dtw["otWin"][1 - team], 4)]} if dtw else {}),
            "possZones": poss[team],  # its possession in game seconds: attacking, neutral, defensive zone
            "possAtt": poss[team][0], "possAttAgainst": poss[1 - team][0],  # attacking-zone possession, its own and its opponent's
            "bumped": sum(1 for e in m.get("bumps", []) if e["team"] == team and e.get("kind") != "goalie"),  # its carriers bumped off the puck
            "onGoalie": sum(1 for e in m.get("bumps", []) if e["team"] == team and e.get("kind") == "goalie"),  # ... or losing it on a goalie
            "bobbled": sum(1 for e in m.get("bobbles", []) if e["team"] == team),  # passes that bounced off the receiver
            "netsOff": sum(1 for e in m.get("netsOff", []) if e.get("byTeam") == team and e.get("side") != "defender"),  # the other team's net knocked off
            "chkGain": sum(1 for h in hits if h["team"] == team and "gain" in h),  # checks that paid off: the puck, a shot, a goal
            "chkShot": sum(1 for h in hits if h["team"] == team and "shotAfter" in h),
            "chkGoal": sum(1 for h in hits if h["team"] == team and "goalAfter" in h),
            "gkGiveGoals": sum(1 for e in turnovers if e["from"] == team and "goalAfterFast" in e),  # goals off its goalies' giveaways
            "ownNetsOff": sum(1 for e in m.get("netsOff", []) if e.get("byTeam") == team and e.get("side") == "defender"),  # its own
            "passTried": team_value(team, "passTried"), "passMade": team_value(team, "passMade"),
            "attackZone": team_value(team, "attackZone"),
            "breakTried": team_value(team, "breakTried"), "breakGoals": team_value(team, "breakGoals"),
            "oneTimerTried": team_value(team, "oneTimerTried"), "oneTimerGoals": team_value(team, "oneTimerGoals"),
            "give": sum(1 for e in turnovers if e["kind"] == "giveaway" and e["from"] == team),
            "take": sum(1 for e in turnovers if e["kind"] == "takeaway" and e["from"] == other),
            # From the converter's shot context (add_shot_context): high-danger attempts, goals and shots on goal for
            # and against; rebound attempts, rebound goals and rebounds this team's goalies gave up; flip rebounds
            # (for, goals, against, goals against); attempts that came from a shot assist; its turnovers that led to
            # an attempt / a goal against; zone entries (all, carried, passed, dumped, led to an attempt).
            "hd": [hd_of(side, want) for want in (None, "goal", "sog") for side in (team, other)],
            "reb": [sum(1 for s in shots if s["team"] == team and s.get("rebound")),
                    sum(1 for s in shots if s["team"] == team and s.get("rebound") and s["result"] == "goal"),
                    sum(1 for s in shots if s["team"] == other and s["result"] == "save" and s.get("after") == "rebound")],
            "flip": [sum(1 for s in shots if s["team"] == side and s.get(key) and (not goal or s["result"] == "goal"))
                     for side in (team, other) for key, goal in (("flip", False), ("afterFlip", True))],
            "assisted": sum(1 for s in shots if s["team"] == team and "assist" in s),
            # Expected goals (tools/xg.py; Genesis), over unblocked attempts: xG for, goals from those shots, xG against,
            # goals against from those shots. Left out when the game has no xG (the SNES).
            **({"xg": [round(sum(s["xg"] for s in xg_shots if s["team"] == side), 3) if not goal
                       else sum(1 for s in xg_shots if s["team"] == side and s["result"] == "goal")
                       for side in (team, other) for goal in (False, True)]} if xg_shots else {}),
            "toShot": [sum(1 for e in turnovers if e["from"] == team and e.get("shotAfter") is not None),
                       sum(1 for e in turnovers if e["from"] == team and e.get("goalAfter"))],
            "entries": [sum(1 for e in entries if e["team"] == team and (kind is None or e["kind"] == kind)) for kind in (None, "carried", "passed", "dumped")]
                       + [sum(1 for e in entries if e["team"] == team and entry_shot(e))],
            # From the converter's play context (add_play_context): checks and penalties by the skater a person
            # controlled and by the computer's; shot attempts and goals by where they came from (rush, sustained
            # pressure, faceoff, other); odd-man rushes, with the attempts and goals off them; wraparounds; what the
            # person did with the controller (None for the computer's team); passes between each pair of players.
            "persHits": [sum(1 for h in hits if h["team"] == team and h.get("human") is v) for v in (True, False)],
            "persPen": [sum(1 for p in penalties if p["team"] == team and p.get("human") is v) for v in (True, False)],
            "origin": [sum(1 for s in shots if s["team"] == team and s.get("origin") == o and (not goal or s["result"] == "goal"))
                       for goal in (False, True) for o in ("rush", "zone", "faceoff", "other")],
            "oddMan": [len(odd_rushes(team)), sum(1 for e in odd_rushes(team) if rush_shots(e)),
                       sum(1 for e in odd_rushes(team) if any(s["result"] == "goal" for s in rush_shots(e)))],
            "wrap": [sum(1 for s in shots if s["team"] == team and s.get("wrap")), sum(1 for s in shots if s["team"] == team and s.get("wrap") and s["result"] == "goal")],
            "habits": (m.get("habits") or [None, None])[team],
            "humanPasses": [sum(1 for p in m.get("passes", []) if p["team"] == team and p.get("human")),
                            sum(1 for p in m.get("passes", []) if p["team"] == team and p.get("human") and p["result"] in ("completed", "one-timer"))],
            "pairs": pass_pairs(team),
            # Every attempt, turned so the team attacks up: [x, y, result (g goal, s save, p post, w wide, b blocked),
            # goalie faced (roster index), type, flags (r rebound, o one-timer pass, e EA Special rebound, h high danger)]
            "shotMap": [[round(s["x"] * (1 if s["y"] >= 0 else -1)), round(abs(s["y"])), (s["result"] or "w")[0], s.get("goalie", -1),
                         s.get("type") or s["kind"], ("r" if s.get("rebound") else "") + ("e" if s.get("afterFlip") else "") +
                         ("h" if s.get("danger") == "high" else "") + ("x" if s.get("wrap") else "")]
                        for s in shots if s["team"] == team],
        })

    # On the ice at each goal, for plus/minus (as the NHL counts it: not power-play or penalty-shot goals)
    goal_ice = [(g, on_ice(g["f"])) for g in goals if 0 <= g["f"] < n]

    # Advanced stats, as the NHL's analysts count them, for each team and for each skater while on the ice: eight
    # numbers, ADV = CF, CA (Corsi: every shot attempt), FF, FA (Fenwick: attempts not blocked), SF, SA (shots on
    # goal, as the game counts them), GF, GA; in all situations and at even strength (the same number of players
    # serving penalties on both sides). Zone starts: the faceoffs a skater was on the ice for, in his team's
    # attacking, neutral and defensive zones.
    pen = penalty_counts(m)
    even = lambda f: pen[0][f] == pen[1][f]
    events = []  # (frame, team, slots it fills for that team: 0 CF, 2 FF, 4 SF, 6 GF; the other team gets +1)
    for s in shots:
        slots = [0] + ([2] if s["result"] != "blocked" else []) + ([4] if s.get("counted") or s["result"] == "goal" else [])
        events.append((s["f"], s["team"], slots))
    for g in goals:
        events.append((g["f"], g["team"], [6]))
    events = [(f, team, slots, on_ice(f), even(f)) for f, team, slots, in events if 0 <= f < n]
    team_adv = [[[0] * 8, [0] * 8] for _ in (0, 1)]  # [team][all, even]
    for f, team, slots, ice, ev in events:
        for side in (0, 1):
            for slot in slots:
                at = slot if side == team else slot + 1
                team_adv[side][0][at] += 1
                if ev:
                    team_adv[side][1][at] += 1
    for team in (0, 1):
        teams[team]["adv"], teams[team]["advEv"] = team_adv[team]

    def skater_adv(team, idx):
        out = [[0] * 8, [0] * 8]
        for f, shooter, slots, ice, ev in events:
            if idx not in ice[team]:
                continue
            for slot in slots:
                at = slot if shooter == team else slot + 1
                out[0][at] += 1
                if ev:
                    out[1][at] += 1
        zs = [0, 0, 0]
        for e in m.get("faceoffs", []):
            if 0 <= e["f"] < n and idx in on_ice(e["f"])[team]:
                zone = e.get("zone", "neu")
                if team == 1:
                    zone = {"att": "def", "def": "att"}.get(zone, zone)  # zones are in Home's view
                zs[{"att": 0, "neu": 1, "def": 2}.get(zone, 1)] += 1
        return {"oi": out[0], "oiEv": out[1], "zs": zs,
                # The team's numbers while he was off the ice, for "relative" stats
                "bench": [a - b for a, b in zip(team_adv[team][0], out[0])],
                "benchEv": [a - b for a, b in zip(team_adv[team][1], out[1])]}

    players = [[], []]
    for team in (0, 1):
        other = 1 - team
        for idx, p in enumerate(rosters[team]):
            at = base + per * idx
            v = final[team][at:at + per] if len(final[team]) >= at + per else [0] * per
            toi = v[5] if per > 5 else 0
            line = {"idx": idx, "name": p["name"], "num": p["num"], "goalie": bool(p.get("g")), "ovr": p.get("ovr"), "toi": toi}
            if p.get("g"):
                faced = [s for s in shots if s["team"] == other and s.get("goalie") == idx and (s.get("counted") or s["result"] == "goal")]
                faced_all = [s for s in shots if s["team"] == other and s.get("goalie") == idx]
                line.update({"hdSa": sum(1 for s in faced if s.get("danger") == "high"),
                             "hdGa": sum(1 for s in faced if s.get("danger") == "high" and s["result"] == "goal"),
                             "rebAllowed": sum(1 for s in faced_all if s["result"] == "save" and s.get("after") == "rebound"),
                             "saves": sum(1 for s in faced_all if s["result"] == "save"),
                             # his passes picked off and scored from within 6 s
                             "giveGoals": sum(1 for e in turnovers if e["from"] == team and e.get("giver") == idx and "goalAfterFast" in e)})
                if xg_shots:  # expected goals against him (unblocked attempts) and the goals those shots scored
                    mine = [s for s in xg_shots if s["team"] == other and s.get("goalie") == idx]
                    line["xga"] = [round(sum(s["xg"] for s in mine), 3), sum(1 for s in mine if s["result"] == "goal")]
                line.update({"sa": v[2], "ga": v[0], "a": v[1],
                             "human": [sum(1 for s in faced if s.get("gctl") == "human"),
                                       sum(1 for s in faced if s.get("gctl") == "human" and s["result"] == "goal")],
                             "cpu": [sum(1 for s in faced if s.get("gctl") != "human"),
                                     sum(1 for s in faced if s.get("gctl") != "human" and s["result"] == "goal")]})
            else:
                pm = 0
                for g, ice in goal_ice:
                    if idx in ice[team] and not any(k in ("PPG", "penalty shot") for k in g.get("kinds", [])):
                        pm += 1 if g["team"] == team else -1
                line.update({
                    "g": v[0], "a": v[1], "sog": v[2], "pm": pm,
                    "att": sum(1 for s in shots if s["team"] == team and s["idx"] == idx),
                    "posts": sum(1 for s in shots if s["team"] == team and s["idx"] == idx and s["result"] == "post"),
                    "tapG": sum(1 for g in goals if g["team"] == team and g["scorer"] == idx and g.get("tapestry")),
                    "tapMiss": sum(1 for s in shots if s["team"] == team and s["idx"] == idx and s.get("tapestry") and s["result"] != "goal"),
                    "tapIn": sum(1 for g in goals if g["team"] == team and g.get("tapestry") and idx in g["tapestry"]["chain"][:-1]),
                    "ppg": sum(1 for g in goals if g["team"] == team and g["scorer"] == idx and "PPG" in g.get("kinds", [])),
                    "shg": sum(1 for g in goals if g["team"] == team and g["scorer"] == idx and "SHG" in g.get("kinds", [])),
                    "gwg": int(bool(gwg) and gwg["team"] == team and gwg["scorer"] == idx),
                    "pim": sum((rules.get(str(q["code"])) or {}).get("min", 0) for q in penalties if q["team"] == team and q["idx"] == idx),
                    "checks": sum(1 for h in hits if h["team"] == team and h["by"] == idx),
                    # of those, thrown while a person controlled him (the hit's `human`: the controlled-skater marker)
                    "checksHuman": sum(1 for h in hits if h["team"] == team and h["by"] == idx and h.get("human")),
                    "hitsTaken": sum(1 for h in hits if h["team"] == other and h["on"] == idx),
                    "give": sum(1 for e in turnovers if e["kind"] == "giveaway" and e["from"] == team and e.get("giver") == idx),
                    "take": sum(1 for e in turnovers if e["kind"] == "takeaway" and e["from"] == other and e.get("by") == idx),
                    "injured": sum(1 for e in m.get("injuries", []) if e["team"] == team and e["idx"] == idx and not e.get("atStart")),
                    "injuredOthers": sum(1 for e in m.get("injuries", []) if e["team"] == other and e.get("by") == idx),
                    "bumpedOff": sum(1 for e in m.get("bumps", []) if e.get("kind") != "goalie" and e["team"] == team and e["idx"] == idx),
                    "bumpedLoose": sum(1 for e in m.get("bumps", []) if e.get("kind") != "goalie" and e["team"] == other and e.get("by") == idx),
                    "onGoalie": sum(1 for e in m.get("bumps", []) if e.get("kind") == "goalie" and e["team"] == team and e["idx"] == idx),
                    "bobbled": sum(1 for e in m.get("bobbles", []) if e["team"] == team and e["idx"] == idx),
                    "netsOff": sum(1 for e in m.get("netsOff", []) if e.get("byTeam") == team and e.get("by") == idx),
                    # shot speeds in mph (shots and one-timers): their sum and count for an average, and the hardest
                    "shotMphSum": round(sum(shot_mph(s["speed"]) for s in shots if s["team"] == team and s["idx"] == idx and s.get("speed") and s["kind"] in ("shot", "one-timer")), 1),
                    "shotMphN": sum(1 for s in shots if s["team"] == team and s["idx"] == idx and s.get("speed") and s["kind"] in ("shot", "one-timer")),
                    "shotTop": round(max([shot_mph(s["speed"]) for s in shots if s["team"] == team and s["idx"] == idx and s.get("speed") and s["kind"] in ("shot", "one-timer")] or [0]), 1),
                    # his checks that paid off: the puck within 2 s, a shot within 5 s of that, a goal within 8 s
                    # where his shots were aimed, a 3 x 3 grid as he sees the net (rows high, middle, along the ice;
                    # columns his left, middle, right): attempts and goals in each
                    "aimShots": aim_grid([s for s in shots if s["team"] == team and s["idx"] == idx and "aim" in s]),
                    "aimGoals": aim_grid([s for s in shots if s["team"] == team and s["idx"] == idx and "aim" in s and s["result"] == "goal"]),
                    "chkGain": sum(1 for h in hits if h["team"] == team and h["by"] == idx and "gain" in h),
                    "chkShot": sum(1 for h in hits if h["team"] == team and h["by"] == idx and "shotAfter" in h),
                    "chkGoal": sum(1 for h in hits if h["team"] == team and h["by"] == idx and "goalAfter" in h),
                })
                if xg_shots:  # his expected goals (unblocked attempts) and the goals those shots scored
                    mine = [s for s in xg_shots if s["team"] == team and s["idx"] == idx]
                    line["xg"] = [round(sum(s["xg"] for s in mine), 3), sum(1 for s in mine if s["result"] == "goal")]
                if any("dir" in q for q in m.get("passes", [])):
                    # Passing by zone (def, neu, att) and direction (forward, diagonal forward, sideways, diagonal back,
                    # backward); from each zone to each; and his game seconds with the puck in each zone
                    mine_p = [q for q in m["passes"] if q["team"] == team and q["idx"] == idx and "dir" in q]
                    line["passDir"] = [sum(1 for q in mine_p if q["zone"] == z and q["dir"] == d) for z in ZONES for d in PASS_DIRS]
                    line["passZones"] = [sum(1 for q in mine_p if q["zone"] == z and q["toZone"] == z2) for z in ZONES for z2 in ZONES]
                    line["puckZone"] = puck_zone.get((team, idx), [0, 0, 0])
                line.update(skater_adv(team, idx))
                mine = [s for s in shots if s["team"] == team and s["idx"] == idx]
                my_entries = [e for e in entries if e["team"] == team and e.get("idx") == idx]
                line.update({
                    "hdAtt": sum(1 for s in mine if s.get("danger") == "high"),
                    "hdG": sum(1 for s in mine if s.get("danger") == "high" and s["result"] == "goal"),
                    "shotAssists": sum(1 for s in shots if s["team"] == team and s.get("assist") == idx),
                    "rebAtt": sum(1 for s in mine if s.get("rebound")),
                    "rebG": sum(1 for s in mine if s.get("rebound") and s["result"] == "goal"),
                    "flips": sum(1 for s in mine if s.get("flip")),
                    "flipG": sum(1 for s in mine if s.get("afterFlip") and s["result"] == "goal"),
                    "costlyGv": sum(1 for e in turnovers if e["kind"] == "giveaway" and e["from"] == team and e.get("giver") == idx and e.get("shotAfter") is not None),
                    "ent": len(my_entries), "entC": sum(1 for e in my_entries if e["kind"] == "carried"),
                    "entShot": sum(1 for e in my_entries if entry_shot(e)),
                })
            if toi > 0 or any(line.get(k) for k in ("g", "a", "sog", "sa", "pim", "checks", "att")):
                players[team].append(line)
        # The goalie with the most ice time gets the decision
        goalies = [p for p in players[team] if p["goalie"]]
        if goalies and finished:
            main = max(goalies, key=lambda p: p["toi"])
            main["dec"] = "W" if score[team] > score[other] else "T" if score[team] == score[other] else "OTL" if overtime else "L"
            main["so"] = int(score[other] == 0)

    return {
        "v": VERSION, "name": name, "date": date, "system": m.get("system", "genesis"), "rom": m.get("rom"),
        "names": [m.get("team1"), m.get("team2")], "abbr": m.get("abbr"), "score": score,
        "overtime": overtime, "finished": finished, "fromStart": from_start, "seconds": seconds,
        "humans": humans, "you": m.get("padTeam", -1), "teams": teams, "players": players,
    }


def dates():
    try:
        return {g["name"]: g.get("date") for g in json.loads((MATCHES / "games.json").read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return {}


def summary(name, date=None):
    """The summary of matches/<name>.js, made if missing or older than the match file."""
    src, out = MATCHES / f"{name}.js", MATCHES / f"{name}.summary.json"
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        try:
            s = json.loads(out.read_text(encoding="utf-8"))
            if s.get("v") == VERSION:
                if date and s.get("date") != date:
                    s["date"] = date
                return s
        except ValueError:
            pass
    date = date or datetime.datetime.fromtimestamp(src.stat().st_mtime).isoformat(timespec="minutes")
    s = summarize(load_match(src), name, date)
    out.write_text(json.dumps(s, separators=(",", ":")), encoding="utf-8")
    return s


# Seasons are named by the user: a ROM, the team they play, and when it starts (and ends, if set). Several seasons can
# share a ROM (every GENS Classic season is played on nhl94.bin), so a season runs until it ends or the same ROM's next
# season starts. Kept beside the games, so a backup of matches/ keeps them.
SEASONS = MATCHES / "seasons.json"


def load_seasons():
    try:
        seasons = json.loads(SEASONS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return seasons if isinstance(seasons, list) else []


def save_seasons(seasons):
    """Store the seasons the page sends, keeping only the known fields."""
    clean = []
    for s in seasons if isinstance(seasons, list) else []:
        if not isinstance(s, dict) or not s.get("name") or not s.get("rom"):
            continue
        clean.append({"id": str(s.get("id") or "")[:40], "name": str(s["name"])[:80], "rom": str(s["rom"])[:40],
                      "team": str(s.get("team") or "")[:8], "start": str(s.get("start") or "")[:16],
                      "end": str(s.get("end") or "")[:16],
                      "excluded": [n[:120] for n in s.get("excluded") or [] if isinstance(n, str)]})
    SEASONS.write_text(json.dumps(clean, indent=1), encoding="utf-8")
    return clean


_rom_teams = {}


def rom_teams():
    """Every team of each ROM the helper has copied into roms/, keyed as the page keys ROMs (system:crc32 as the
    converter takes it), so a new season can pick a team that has not played yet."""
    import zlib
    from systems import genesis, snes
    out, folder = {}, ROOT / "roms"
    for path in sorted(folder.glob("*")) if folder.exists() else []:
        system = {".bin": "genesis", ".smc": "snes"}.get(path.suffix.lower())
        if not system:
            continue
        stamp = (path.name, path.stat().st_mtime)
        if stamp not in _rom_teams:
            try:
                data = path.read_bytes()
                crc = zlib.crc32(snes.strip_header(data) if system == "snes" else data)
                teams = (snes if system == "snes" else genesis).read_teams(path)
                _rom_teams[stamp] = (f"{system}:{crc:08x}", [[t["abbr"], t["name"]] for t in teams])
            except Exception as e:
                print(f"season: could not read the teams of {path.name}: {e}", file=sys.stderr)
                _rom_teams[stamp] = None
        if _rom_teams[stamp]:
            out[_rom_teams[stamp][0]] = _rom_teams[stamp][1]
    return out


# ------------------------------------------------------------------------------------------------------- heat maps
# Each game's heat maps, for the season page to add up: matches/heat/<name>.js (a folder of their own, so nothing
# that lists the match files takes them for games). Time in live play (the puck hidden at whistles is left out), in
# tenths of a second, on a 10-unit grid (26 x 60 over X -130..130, Y -300..300), each team turned to attack up the
# screen. Slices, as in the viewer's filters: skate (a team's skaters, goalies left out, or one player, on the ice),
# att / def (skating while that team / the other team has the puck), pp / sh (a team's skating on the power play /
# shorthanded: more of the other team / of its own players serving a penalty), puck (where the puck was while that
# team or player had it). Teams have all six, players skate, att, def and puck. A grid is stored sparse: pairs of
# (cells skipped since the last one, tenths of a second).
HEAT_VERSION = 2  # 2: game time (1 was real time)
HEAT_CELL, HEAT_COLS, HEAT_ROWS = 10, 26, 60
HEAT_DIR = MATCHES / "heat"
PUCK_HIDDEN_Z = -100


def penalty_counts(m):
    """pen[team][f]: that team's players serving a penalty (not delayed calls) at frame f, from the stat snapshots."""
    n, stats = len(m["t"]), m.get("stats") or {}
    out = [[0] * n, [0] * n]
    frames, per, first = stats.get("f") or [], stats.get("p") or 7, stats.get("n") or 7
    if per <= 7:
        return out
    for s, fr in enumerate(frames):
        to = frames[s + 1] if s + 1 < len(frames) else n
        for team, side in enumerate(("home", "away")):
            v, c = stats[side][s], 0
            for idx in range(26):
                at = first + per * idx
                if at + per > len(v):
                    break
                word = v[at + 7]
                if word >> 8 != 0xFF and not word & 0x2000:
                    c += 1
            if c:
                out[team][fr:to] = [c] * (to - fr)
    return out


def game_heat(m):
    t, pos, puck, owner = m["t"], m["pos"], m["puck"], m["owner"]
    role, roster, n = m.get("role"), m.get("roster"), len(m["t"])
    if not role or not roster:
        return None
    # ends[f]: 1 while Home's goalie is at the top (Home attacking down), as the viewer works it out
    ends, last, first = [0] * n, -1, -1
    for f in range(n):
        for k in range(6):
            if role[f * PLAYERS + k] == "0":
                last = 1 if pos[(f * PLAYERS + k) * 2 + 1] > 0 else 0
                break
        if last >= 0 and first < 0:
            first = last
        ends[f] = max(0, last)
    for f in range(n):
        if first < 0 or any(role[f * PLAYERS + k] == "0" for k in range(6)):
            break
        ends[f] = first
    pen = penalty_counts(m)
    size = HEAT_COLS * HEAT_ROWS
    teams = [{"g": {}, "s": {}} for _ in range(2)]
    players = [{}, {}]

    def cell(x, y, turn):
        if turn:
            x, y = -x, -y
        c, r = int((x + 130) // HEAT_CELL), int((300 - y) // HEAT_CELL)
        return r * HEAT_COLS + c if 0 <= c < HEAT_COLS and 0 <= r < HEAT_ROWS else None

    def add(entity, slices, c, dt):
        for sl in slices:
            grid = entity["g"].get(sl)
            if grid is None:
                grid = entity["g"][sl] = [0.0] * size
            grid[c] += dt

    def tick(entity, slices, dt):
        for sl in slices:
            entity["s"][sl] = entity["s"].get(sl, 0) + dt

    weight = game_weights(m)  # game milliseconds each sample stands for (nothing while the clock is stopped)
    for i in range(n - 1):
        if puck[3 * i + 2] < PUCK_HIDDEN_Z or not weight[i]:
            continue
        dt = weight[i]
        k_own = owner[i]
        has = -1 if k_own < 0 else 0 if k_own < 6 else 1
        for team in (0, 1):
            turn = ends[i] if team == 0 else 1 - ends[i]  # keep this team attacking up
            mine, theirs = pen[team][i], pen[1 - team][i]
            side = ["att"] if has == team else ["def"] if has == 1 - team else []
            strength = [] if mine == theirs else ["pp"] if theirs > mine else ["sh"]
            on = False
            for k in range(team * 6, team * 6 + 6):
                r = role[i * PLAYERS + k]
                if r in ("x", "0"):
                    continue  # off the ice, or the goalie
                c = cell(pos[(i * PLAYERS + k) * 2], pos[(i * PLAYERS + k) * 2 + 1], turn)
                if c is None:
                    continue
                on = True
                add(teams[team], ["skate"] + side + strength, c, dt)
                idx = int(roster[i * PLAYERS + k], 36)
                p = players[team].get(idx)
                if p is None:
                    p = players[team][idx] = {"g": {}, "s": {}}
                add(p, ["skate"] + side, c, dt)
                tick(p, ["skate"] + side, dt)
            if on:
                tick(teams[team], ["skate"] + side + strength, dt)
            if has == team:
                c = cell(puck[3 * i], puck[3 * i + 1], turn)
                if c is not None:
                    add(teams[team], ["puck"], c, dt)
                    tick(teams[team], ["puck"], dt)
                    p = players[team].get(int(roster[i * PLAYERS + k_own], 36))
                    if p is not None:
                        add(p, ["puck"], c, dt)
                        tick(p, ["puck"], dt)

    def pack(entity):
        grids = {}
        for sl, grid in entity["g"].items():
            out, skipped = [], 0
            for v in grid:
                tenths = round(v / 100)
                if tenths:
                    out += [skipped, tenths]
                    skipped = 0
                else:
                    skipped += 1
            grids[sl] = out
        return {"g": grids, "s": {sl: round(v / 1000, 1) for sl, v in entity["s"].items()}}

    return {"v": HEAT_VERSION, "cell": HEAT_CELL, "cols": HEAT_COLS, "rows": HEAT_ROWS,
            "teams": [pack(e) for e in teams],
            "players": [{str(idx): pack(e) for idx, e in side.items()} for side in players]}


def heat_file(name):
    """Make matches/heat/<name>.js if it is missing, older than the match file, or from an older HEAT_VERSION."""
    src, out = MATCHES / f"{name}.js", HEAT_DIR / f"{name}.js"
    head = f"// heat v{HEAT_VERSION}\n"
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        with open(out, encoding="utf-8") as fh:
            if fh.readline() == head:
                return
    data = game_heat(load_match(src))
    if data is None:
        return
    HEAT_DIR.mkdir(exist_ok=True)
    out.write_text(head + "(window.NHL94_HEAT = window.NHL94_HEAT || {})[" + json.dumps(name) + "] = "
                   + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")


def season():
    """Every converted game's summary, newest first, with the seasons and the teams of the ROMs played. Makes any
    heat-map file that is missing on the way."""
    when, games = dates(), []
    for path in sorted(MATCHES.glob("*.js")):
        if path.name == "season.js" or path.name.startswith("_"):  # "_": the live broadcast's work and tests, never games
            continue
        try:
            games.append(summary(path.stem, when.get(path.stem)))
        except Exception as e:  # a broken or very old match file: leave it out
            print(f"season: skipped {path.stem}: {e}", file=sys.stderr)
            continue
        try:
            heat_file(path.stem)
        except Exception as e:
            print(f"season: no heat map for {path.stem}: {e}", file=sys.stderr)
    seasons, teams = load_seasons(), rom_teams()
    keys = {f"{g.get('system', 'genesis')}:{g.get('rom') or '?'}" for g in games} | set(teams) | {s["rom"] for s in seasons}
    try:
        import romnames
        names = {k: v for k, v in romnames.names(sorted(keys)).items() if k in keys}
    except Exception as e:
        print(f"season: no ROM names: {e}", file=sys.stderr)
        names = {}
    return {"games": sorted(games, key=lambda g: g.get("date") or "", reverse=True), "seasons": seasons,
            "romTeams": teams, "romNames": names}


def write_season_file():
    data = season()
    (MATCHES / "season.js").write_text("window.NHL94_SEASON = " + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    data = write_season_file()
    for g in data["games"]:
        print(f"{g['name']:32s} {g['abbr'][0]:>4s} {g['score'][0]}-{g['score'][1]} {g['abbr'][1]:<4s}"
              f"{' OT' if g['overtime'] else '   '} {'whole game' if g['fromStart'] and g['finished'] else 'part of a game'}")
