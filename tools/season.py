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

VERSION = 1
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


def summarize(m, name, date=None):
    t, period, clock = m["t"], m["period"], m["clock"]
    n = len(t)
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
    turnovers, penalties, rules = m.get("turnovers", []), m.get("penalties", []), m.get("rules", {})
    faceoffs = [e for e in m.get("faceoffs", []) if e.get("won") in (0, 1)]

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
            "ppg": team_value(team, "ppGoals"), "ppTries": team_value(team, "ppTries"),
            "ppgA": team_value(other, "ppGoals"), "pkTimes": team_value(other, "ppTries"),
            "shg": team_value(team, "shGoals"),
            "pen": sum(1 for p in penalties if p["team"] == team),
            "pim": sum((rules.get(str(p["code"])) or {}).get("min", 0) for p in penalties if p["team"] == team),
            "fow": sum(1 for e in faceoffs if e["won"] == team), "fo": len(faceoffs),
            "checks": team_value(team, "checks"),
            "bigHits": sum(1 for h in hits if h["team"] == team and h.get("outcome") in ("upended", "into the boards", "into the bench")),
            "passTried": team_value(team, "passTried"), "passMade": team_value(team, "passMade"),
            "attackZone": team_value(team, "attackZone"),
            "breakTried": team_value(team, "breakTried"), "breakGoals": team_value(team, "breakGoals"),
            "oneTimerTried": team_value(team, "oneTimerTried"), "oneTimerGoals": team_value(team, "oneTimerGoals"),
            "give": sum(1 for e in turnovers if e["kind"] == "giveaway" and e["from"] == team),
            "take": sum(1 for e in turnovers if e["kind"] == "takeaway" and e["from"] == other),
        })

    # On the ice at each goal, for plus/minus (as the NHL counts it: not power-play or penalty-shot goals)
    goal_ice = [(g, on_ice(g["f"])) for g in goals if 0 <= g["f"] < n]

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
                    "ppg": sum(1 for g in goals if g["team"] == team and g["scorer"] == idx and "PPG" in g.get("kinds", [])),
                    "shg": sum(1 for g in goals if g["team"] == team and g["scorer"] == idx and "SHG" in g.get("kinds", [])),
                    "gwg": int(bool(gwg) and gwg["team"] == team and gwg["scorer"] == idx),
                    "pim": sum((rules.get(str(q["code"])) or {}).get("min", 0) for q in penalties if q["team"] == team and q["idx"] == idx),
                    "checks": sum(1 for h in hits if h["team"] == team and h["by"] == idx),
                    "hitsTaken": sum(1 for h in hits if h["team"] == other and h["on"] == idx),
                    "give": sum(1 for e in turnovers if e["kind"] == "giveaway" and e["from"] == team and e.get("giver") == idx),
                    "take": sum(1 for e in turnovers if e["kind"] == "takeaway" and e["from"] == other and e.get("by") == idx),
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


def season():
    """Every converted game's summary, newest first, with the seasons and the teams of the ROMs played."""
    when, games = dates(), []
    for path in sorted(MATCHES.glob("*.js")):
        if path.name == "season.js":
            continue
        try:
            games.append(summary(path.stem, when.get(path.stem)))
        except Exception as e:  # a broken or very old match file: leave it out
            print(f"season: skipped {path.stem}: {e}", file=sys.stderr)
    return {"games": sorted(games, key=lambda g: g.get("date") or "", reverse=True), "seasons": load_seasons(),
            "romTeams": rom_teams()}


def write_season_file():
    data = season()
    (MATCHES / "season.js").write_text("window.NHL94_SEASON = " + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    data = write_season_file()
    for g in data["games"]:
        print(f"{g['name']:32s} {g['abbr'][0]:>4s} {g['score'][0]}-{g['score'][1]} {g['abbr'][1]:<4s}"
              f"{' OT' if g['overtime'] else '   '} {'whole game' if g['fromStart'] and g['finished'] else 'part of a game'}")
