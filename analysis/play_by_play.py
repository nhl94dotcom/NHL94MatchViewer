"""A play-by-play of a game, in hockey terms, as raw material for a written match story (2026-10-21, the user: a
narrative write-up from what the recording shows, not a box score). Chronological moments: every goal with its
build-up (who carried the puck where, the passes, the shot, the goalie), big saves, posts, near misses, big hits,
injuries, breakaways and odd-man rushes, turnovers that led to chances, penalties; then the flow of the game minute by
minute. Places are named from the attacking team's view (its left wing, the slot, the right circle, the point ...),
distances in feet (3 game units a foot).
python analysis/play_by_play.py <match name>   (matches/ or Documents/NHL94 Viewer/matches)"""
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
from export_match import own_end  # noqa: E402

K = 12
DIRS = [Path("matches"), Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches"))]
NET = 268
FT = 3.0  # game units a foot (536 between the goal lines, 178 ft)


class Game:
    def __init__(self, name):
        path = next(d / f"{name}.js" for d in DIRS if (d / f"{name}.js").exists())
        self.m = m = json.loads(load_js_object(path))
        self.t, self.N = m["t"], len(m["t"])
        self.ab = m.get("abbr") or [m["team1"][:3].upper(), m["team2"][:3].upper()]

    def clock(self, f):
        p, c = self.m["period"][f], self.m["clock"][f]
        return f"{'P' + str(p + 1) if p < 3 else 'OT'} {c // 60}:{c % 60:02d}"

    def name(self, team, idx):
        r = self.m["rosters"][team]
        return r[idx]["name"].split()[-1] if idx is not None and 0 <= idx < len(r) else "?"

    def full(self, team, idx):
        r = self.m["rosters"][team]
        return r[idx]["name"] if idx is not None and 0 <= idx < len(r) else "?"

    def pos(self, f, k):
        return self.m["pos"][(f * K + k) * 2], self.m["pos"][(f * K + k) * 2 + 1]

    def roster(self, f, k):
        c = self.m["roster"][f * K + k]
        return int(c, 36) if c != "z" else -1

    def role(self, f, k):
        return self.m["role"][f * K + k]

    def goalie(self, f, team):
        return next((k for k in range(team * 6, team * 6 + 6) if self.role(f, k) == "0"), None)

    def up(self, f, team):
        """+1 if `team` attacks toward +Y at frame f, -1 toward -Y."""
        e = own_end(self.m, f, team)
        if e is None:
            e = -(own_end(self.m, f, 1 - team) or 1)
        return -e

    def where(self, f, team, x, y):
        """A place on the ice from `team`'s attacking view."""
        d = self.up(f, team)
        ya = y * d                      # toward the net it attacks: +
        side = "left" if x * d < 0 else "right"  # its left wing is -X when attacking up
        dist = math.hypot(x, NET - ya)
        if ya > NET:
            return "from behind the net"
        if ya >= 89:
            if dist < 45 and abs(x) < 22:
                return "from the doorstep"
            if dist < 70 and abs(x) < 30:
                return "from the slot"
            if abs(x) >= 95:
                return f"from the {side} half-boards" if ya < 220 else f"from deep in the {side} corner"
            if ya < 125:
                return "from the point" if abs(x) < 50 else f"from the {side} point"
            if abs(x) >= 40:
                return f"from the {side} circle"
            return "from the high slot"
        if ya > -89:
            return "from the neutral zone"
        return "from its own end"

    def feet(self, x, y, f, team):
        d = self.up(f, team)
        return round(math.hypot(x, NET - y * d) / FT)

    def owner_runs(self, a, b):
        """Who had the puck from frame a to b: [(team, idx, first, last)]."""
        own, out = self.m["owner"], []
        for i in range(max(0, a), min(self.N, b + 1)):
            k = own[i]
            if k < 0:
                continue
            team, idx = (0 if k < 6 else 1), self.roster(i, k)
            if out and tuple(out[-1][:2]) == (team, idx):
                out[-1][3] = i
            else:
                out.append([team, idx, i, i])
        return out


def net_spot(net, aim):
    """Where it went in, as the shooter sees the net."""
    if not net:
        return ""
    x, z = net["x"], net["z"]
    side = "low" if z < 4 else "high" if z >= 9 else "waist-high"
    lr = "his left" if x < -8 else "his right" if x > 8 else "the middle"
    return f"{side}, {lr} of the net" if lr != "the middle" else f"{side} through the middle"


def describe_goal(G, g, shots, passes, entries, turnovers, hits, faceoffs):
    m, team = G.m, g["team"]
    opp, f = 1 - team, g["f"]
    sh = min((s for s in shots if s["team"] == team and s["result"] == "goal" and abs(G.t[s["f"]] - G.t[f]) < 3000),
             key=lambda s: abs(s["f"] - f), default=None)
    lines = [f"GOAL {G.clock(f)} {G.ab[team]} {G.full(team, g['scorer'])}"
             + (f" (assists {', '.join(G.full(team, a[0]) for a in g.get('assists', []))})" if g.get("assists") else " (unassisted)")
             + f" -> {G.ab[0]} {m['score'][2 * f]}-{m['score'][2 * f + 1]} {G.ab[1]}; kinds: {', '.join(g.get('kinds', [])) or 'none'}"]
    # The build-up: from the team's last gain of the puck (or the faceoff), at most 15 s before
    start = max(0, next((q for q in range(f, -1, -1) if G.t[f] - G.t[q] > 15000), 0))
    stop = next((q for q in range(f, start, -1) if m["puck"][3 * q + 2] < -100), None)
    if stop is not None:
        start = stop + 1
    runs = [r for r in G.owner_runs(start, f)]
    # trim to the last stretch the scoring team kept it
    cut = max((i for i, r in enumerate(runs) if r[0] != team), default=-1)
    if cut >= 0:
        lost = runs[cut]
        tov = next((e for e in turnovers if abs(e["f"] - lost[3]) < 40 and e["from"] == opp), None)
        how = f" ({tov['how']}{' by ' + G.name(team, tov.get('by')) if tov.get('by') is not None else ''})" if tov else ""
        lines.append(f"  won the puck off {G.name(opp, lost[1])}{how} {G.where(lost[3], team, m['puck'][3 * lost[3]], m['puck'][3 * lost[3] + 1]).replace('from ', 'in ')}, "
                     f"{(G.t[f] - G.t[lost[3]]) / 1000:.1f} s before the goal")
        runs = runs[cut + 1:]
    else:
        fo = next((e for e in reversed(faceoffs) if e["f"] <= f and G.t[f] - G.t[e["f"]] < 15000), None)
        if fo:
            lines.append(f"  off a faceoff {G.where(fo['f'], team, fo['x'], fo['y']).replace('from ', 'in ')} "
                         f"({'won' if fo['won'] == team else 'lost' if fo['won'] == opp else 'unclear'}), "
                         f"{(G.t[f] - G.t[fo['f']]) / 1000:.1f} s before")
    for t_, idx, a, b in runs:
        x0, y0, x1, y1 = m["puck"][3 * a], m["puck"][3 * a + 1], m["puck"][3 * b], m["puck"][3 * b + 1]
        carried = math.hypot(x1 - x0, y1 - y0) / FT
        p = next((p for p in passes if p["team"] == team and p["idx"] == idx and abs(p["f"] - b) <= 3), None)
        what = (f"passed {p['dir'] if p.get('dir') else ''} to {G.name(team, p['to'])}" if p and p.get("to", -1) >= 0
                else "shot" if sh and abs(sh["f"] - b) <= 3 else "lost it")
        lines.append(f"  {G.name(team, idx)} had it {(G.t[b] - G.t[a]) / 1000:.1f} s, {G.where(a, team, x0, y0).replace('from ', '')}"
                     f"{' -> ' + G.where(b, team, x1, y1).replace('from ', '') + f' ({carried:.0f} ft)' if carried > 8 else ''}, then {what}")
    ent = next((e for e in reversed(entries) if e["team"] == team and e["f"] <= f and G.t[f] - G.t[e["f"]] < 10000), None)
    if ent:
        lines.append(f"  zone entry {G.clock(ent['f'])}: {ent['kind']} by {G.name(team, ent.get('idx'))}"
                     + (f", {ent['odd'][0]} attackers on {ent['odd'][1]} back" if ent.get("odd") else ""))
    if sh:
        lines.append("  " + shot_line(G, sh))
    if g.get("tapestry"):
        lines.append("  passing chain: " + " -> ".join(G.name(team, i) for i in g["tapestry"]["chain"]))
    if g.get("net"):
        lines.append(f"  in {net_spot(g['net'], g.get('aim'))} (crossed at x {g['net']['x']}, height {g['net']['z']})")
    # the defenders: who was near the shooter, where the other team's controlled skater was
    if sh:
        sf = sh["f"]
        near = sorted((math.hypot(G.pos(sf, k)[0] - sh["x"], G.pos(sf, k)[1] - sh["y"]), k) for k in range(opp * 6, opp * 6 + 6)
                      if G.role(sf, k) in "12345")
        if near:
            d, k = near[0]
            ctl = m["ctrl"][sf] >> k & 1
            lines.append(f"  nearest defender {G.name(opp, G.roster(sf, k))} {d / FT:.0f} ft from the shooter"
                         f"{' (the person controlling him)' if ctl else ''}")
        ck = next((k for k in range(opp * 6, opp * 6 + 6) if m["ctrl"][sf] >> k & 1), None)
        if ck is not None and (not near or ck != near[0][1]):
            x, y = G.pos(sf, ck)
            lines.append(f"  {G.ab[opp]}'s controlled player was {G.name(opp, G.roster(sf, ck))}"
                         f"{' (the goalie)' if G.role(sf, ck) == '0' else ''}, {math.hypot(x - sh['x'], y - sh['y']) / FT:.0f} ft from the shooter")
    return lines


def shot_line(G, s):
    m, team, f = G.m, s["team"], s["f"]
    opp = 1 - team
    gk = G.goalie(f, opp)
    gtxt = ""
    if gk is not None:
        gx, gy = G.pos(f, gk)
        ny = -NET * G.up(f, team) * -1
        dx, dy = -s["x"], ny - s["y"]
        off = abs((gx - s["x"]) * dy - (gy - s["y"]) * dx) / (math.hypot(dx, dy) or 1)
        q = next((q for q in range(f, -1, -1) if G.t[f] - G.t[q] >= 250), 0)
        px, py = G.pos(q, gk)
        speed = math.hypot(gx - px, gy - py) / max(0.05, (G.t[f] - G.t[q]) / 1000) / FT
        gtxt = (f"; goalie {G.name(opp, G.roster(f, gk))} ({'a person' if s.get('gctl') == 'human' else 'the computer'}) "
                f"{off / FT:.0f} ft off the shot's line{', moving ' + str(round(speed)) + ' ft/s' if speed > 8 else ', set'}"
                f"{', save move ' + s['save'] if s.get('save') and s['save'] != 'none' else ''}")
    tags = [x for x in (s.get("origin") and f"{s['origin']}", s.get("rebound") and "rebound", s.get("wrap") and "wraparound",
                        s.get("danger") == "high" and "high danger") if x]
    assist = f", set up by {G.name(team, s['assist'])}" if s.get("assist") is not None else ""
    aim = ""
    if s.get("aim"):
        a = s["aim"]
        aim = f", aimed {'high' if a['z'] >= 10 else 'at the ice' if a['z'] < 3 else 'waist-high'} {'to his left' if a['x'] < 0 else 'to his right' if a['x'] > 0 else 'middle'}"
    return (f"{s['type']} by {G.name(team, s['idx'])} {G.where(f, team, s['x'], s['y'])}, {G.feet(s['x'], s['y'], f, team)} ft, "
            f"{s.get('speed', 0) * 0.015 / (536 / 178) * 3600 / 5280:.0f} mph{aim}{assist} -> {s['result']}"
            f"{'' if s.get('counted') or s['result'] != 'save' else ' (not counted)'}, xG {s.get('xg', '-')}"
            f"{' [' + ', '.join(tags) + ']' if tags else ''}{gtxt}")


def main(name):
    G = Game(name)
    m = G.m
    shots, passes = m.get("shotList", []), m.get("passes", [])
    entries, turnovers, hits = m.get("zoneEntries", []), m.get("turnovers", []), m.get("hits", [])
    faceoffs = m.get("faceoffs", [])
    print(f"{m['team1']} (home, {G.ab[0]}) vs {m['team2']} (away, {G.ab[1]}): final {m['score'][-2]}-{m['score'][-1]}")
    for team in (0, 1):
        r = m["rosters"][team]
        hc = ", ".join(f"{p['name']} {p.get('hc', 0):+d}" for p in r if p.get("hc") not in (None, 0))
        print(f"  {G.ab[team]} hot / cold as played (non-zero): {hc or 'none'}")
    goalies = {team: {G.roster(i, k) for i in range(0, G.N, 50) for k in range(team * 6, team * 6 + 6) if G.role(i, k) == '0'} for team in (0, 1)}
    print("  goalies: " + "; ".join(f"{G.ab[t]} {', '.join(G.full(t, i) for i in goalies[t])}" for t in (0, 1)))
    who_human = [m.get("padTeam"), m.get("pad2Team")]
    print(f"  controllers: pad 1 {G.ab[who_human[0]] if who_human[0] in (0, 1) else '-'}, pad 2 {G.ab[who_human[1]] if who_human[1] in (0, 1) else '-'}")
    moments = []
    for g in m.get("goals", []):
        moments.append((g["f"], describe_goal(G, g, shots, passes, entries, turnovers, hits, faceoffs)))
    for s in shots:
        if s["result"] == "goal":
            continue
        if s["result"] == "post":
            moments.append((s["f"], [f"POST {G.clock(s['f'])} {G.ab[s['team']]}: " + shot_line(G, s)]))
        elif (s.get("xg") or 0) >= 0.3 or (s["result"] == "save" and s.get("danger") == "high"):
            moments.append((s["f"], [f"CHANCE {G.clock(s['f'])} {G.ab[s['team']]}: " + shot_line(G, s)]))
    for h in hits:
        if h.get("outcome") in ("upended", "into the boards", "into the bench") or h.get("goalAfter"):
            moments.append((h["f"], [f"HIT {G.clock(h['f'])} {G.ab[h['team']]} {G.name(h['team'], h['by'])} {h.get('how', 'check')}s "
                                     f"{G.name(1 - h['team'], h['on'])} ({h.get('outcome')}){' on the puck carrier' if h.get('onCarrier') else ''}"
                                     f"{', led to a goal' if h.get('goalAfter') else ', led to a shot' if h.get('shotAfter') else ''}"]))
    for e in m.get("injuries", []):
        if not e.get("atStart"):
            moments.append((e["f"], [f"INJURY {G.clock(e['f'])} {G.ab[e['team']]} {G.full(e['team'], e['idx'])} hurt"
                                     f"{' by ' + G.name(1 - e['team'], e['by']) if e.get('by') is not None else ''}, out for the {e['out']}"]))
    for e in entries:
        if e["kind"] in ("carried", "passed") and e.get("odd") and e["odd"][0] >= 2 and e["odd"][0] > e["odd"][1]:
            got = [s for s in shots if s["team"] == e["team"] and e["f"] <= s["f"] <= e.get("end", e["f"])]
            moments.append((e["f"], [f"ODD-MAN {G.clock(e['f'])} {G.ab[e['team']]} {e['odd'][0]}-on-{e['odd'][1]} led by {G.name(e['team'], e.get('idx'))}: "
                                     + (f"{len(got)} attempt(s), best xG {max((s.get('xg') or 0) for s in got):.2f}"
                                        + (", GOAL" if any(s["result"] == "goal" for s in got) else "") if got else "no shot")]))
    for e in turnovers:
        if e.get("goalAfter") or (e.get("shotAfter") is not None and any(s["f"] == e["shotAfter"] and (s.get("xg") or 0) >= 0.25 for s in shots)):
            moments.append((e["f"], [f"TURNOVER {G.clock(e['f'])} {G.ab[e['from']]} {G.name(e['from'], e.get('giver'))} {e['kind']} ({e['how']}"
                                     f"{', by ' + G.name(1 - e['from'], e.get('by')) if e.get('by') is not None else ''}) "
                                     f"{G.where(e['f'], 1 - e['from'], e['x'], e['y'])} -> {'GOAL' if e.get('goalAfter') else 'a good chance'}"]))
    for p in m.get("penalties", []):
        moments.append((max(0, p["f"]), [f"PENALTY {G.clock(max(0, p['f']))} {G.ab[p['team']]} {G.full(p['team'], p['idx'])} code {p['code']}"]))
    for b in m.get("bobbles", []):
        if any(s["team"] == 1 - b["team"] and 0 <= G.t[s["f"]] - G.t[b["f"]] <= 5000 and (s.get("xg") or 0) >= 0.25 for s in shots):
            moments.append((b["f"], [f"BOBBLE {G.clock(b['f'])} {G.ab[b['team']]} {G.name(b['team'], b['idx'])} bobbled {G.name(b['team'], b['by'])}'s pass, the other team got a chance"]))
    print()
    for f, lines in sorted(moments, key=lambda x: x[0]):
        print("\n".join(lines))
    # the flow: attempts and xG per team, minute by minute of game time
    print("\nFLOW (each line one game minute: attempts H / A, xG H / A, score after)")
    for p in sorted({m["period"][s["f"]] for s in shots}):
        if p > 3:
            continue
        for minute in range(10, -1, -1):
            lo, hi = minute * 60, minute * 60 + 59
            sel = [s for s in shots if m["period"][s["f"]] == p and lo <= m["clock"][s["f"]] <= hi]
            if not sel:
                continue
            a = [sum(1 for s in sel if s["team"] == t) for t in (0, 1)]
            x = [sum((s.get("xg") or 0) for s in sel if s["team"] == t and s["result"] != "blocked") for t in (0, 1)]
            last = max(s["f"] for s in sel)
            print(f"  {'P' + str(p + 1) if p < 3 else 'OT'} {minute + 1}:00-{minute}:00  {a[0]} / {a[1]}   {x[0]:.2f} / {x[1]:.2f}"
                  f"   {m['score'][2 * last]}-{m['score'][2 * last + 1]}")


if __name__ == "__main__":
    main(sys.argv[1])
