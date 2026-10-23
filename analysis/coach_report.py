"""How the two people played, beyond the box score (2026-10-23, the user: metrics for the people themselves, their
decisions). Both teams measured the same way over a set of Genesis games between them, totals and per game. Only what
the person's own skater (or goalie) did counts. Shots in a period's last END_S game-clock seconds are left out of the
judging (everyone throws the puck at the net then) unless they were a decent chance (xG 0.10 or more).
- Decisions with the puck: at each of the person's passes and shots in the attacking zone (within 180 of the goal line),
  the options he had, valued the same way: shoot (the xG model from that spot at the goalie as he was, the game's own
  aim, a wrist shot), pass to each teammate (the league's completion rate for that length and gap to the nearest
  opponent, times how often a completed pass received where the teammate stands led to a goal within 5 s), keep it
  (how often possession where he is led to a goal within 5 s). League tables from every recorded Genesis game
  (coach_models.py). Did he pick the
  best option, and how much did he leave on the table.
- Shot selection: the person's shots, their xG, at a goalie off the shot line or a set one.
- Passing: completed and picked off by zone; passes that set up a shot; passes across the slot (the one-timer study).
- Bursts (C without the puck) by what they were for: a check attempt (an opponent within reach ahead of him), a
  recovery (caught up ice, bursting back toward his net), positioning (toward the middle with no one to hit). Check
  attempts: landed or not; recoveries and positioning: did they get him goal-side within 1.5 s. Risky checks: a check
  attempt as the last skater goal-side of the puck, missed, and a shot against within 4 s.
- Pokes by what they were for: a steal (within reach of the carrier), the passing lane (out of reach and aimed away from
  the carrier, or beside a pass by the other team), wasted (out of reach, aimed at the carrier).
- Defensive position: while the other team has the puck in his end, his skater in position (goal-side and within 25 of
  the line from the puck to his net), goal-side but off that line, or caught up ice; the same at each shot against
  from his end, with its xG. Switch timing: a switch that took him from out of position to in position, or the reverse.
- The goalie when the person took him, by the reason (the user's list): an opposing breakaway (their carrier in our half
  with none of our skaters nearer our net), a one-timer coming (their pass in the air toward our end), a carrier driving
  at the net (within 130, closing), the puck fired down the ice (theirs last, moving fast toward our end, 100+ out), a
  loose puck near the net (within 100), a carrier behind or beside the net (within 45, or behind the goal line); then
  whether a shot followed within 3 s, goals, xG, and whether his team had the puck next. Times the game handed him the
  goalie because the goalie caught the puck are not decisions and are counted apart. Person against computer in net
  for the same kinds of shot.
python analysis/coach_report.py <TEAM> <TEAM> <match name> ...  -> reports/coach_<first match>.md"""
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_match import own_end  # noqa: E402
from match_report import find  # noqa: E402
from share_game import load_js_object  # noqa: E402
from coach_models import Models, lane_gap  # noqa: E402
import xg as XG  # noqa: E402

K, END_S, DECENT, ZONE, SAMPLES = 12, 5, 0.10, 180, 150
CHECK_REACH, CHECK_CONE = 70, 35       # a burst at an opponent this close and this many degrees off his facing
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def P(m, f, k):
    return m["pos"][(f * K + k) * 2], m["pos"][(f * K + k) * 2 + 1]


def anim(m, f, k):
    return m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4]


def facing(m, f, k):
    a = math.radians(45 * int(m["facing"][f * K + k]))
    return math.sin(a), math.cos(a)             # 0 = up the screen (+Y), clockwise


def angle_to(fx, fy, dx, dy):
    d = math.hypot(dx, dy) or 1
    return math.degrees(math.acos(max(-1, min(1, (fx * dx + fy * dy) / d))))


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy or 1
    u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + u * dx), py - (ay + u * dy))


def ctrl_skater(m, f, team):
    c = m["ctrl"][f]
    return next((k for k in range(team * 6, team * 6 + 6) if c >> k & 1 and m["role"][f * K + k] in "12345"), None)


def skaters(m, f, team):
    return [k for k in range(team * 6, team * 6 + 6) if m["role"][f * K + k] in "12345"]


def roster(m, f, k):
    c = m["roster"][f * K + k]
    return DIGITS.index(c) if c in DIGITS else -1


def goalie(m, f, team):
    return next((k for k in range(team * 6, team * 6 + 6) if m["role"][f * K + k] == "0"), None)


def late(m, f, xg=None):
    """A throw at the net in a period's last END_S game-clock seconds (everyone shoots then): left out of the judging
    unless it was a decent chance (xG DECENT or more)."""
    return m["clock"][f] <= END_S and (xg is None or xg < DECENT)


def position_state(m, f, k, ny):
    """'in' (goal-side: nearer his net than the puck is, and within 25 of the line puck -> his net), 'off' (goal-side,
    off that line) or 'up' (no nearer his net than the puck: caught up ice)."""
    x, y = P(m, f, k)
    px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
    if math.hypot(x, ny - y) >= math.hypot(px, ny - py):
        return "up"
    return "in" if seg_dist(x, y, px, py, 0, ny) < 25 else "off"


class Shooter:
    """The xG model's shot from a spot at a moment (as add_expected_goals, the game's own aim, a wrist shot)."""

    def __init__(self, m):
        self.m, self.rows = m, {}
        for r in m.get("work", []):
            self.rows.setdefault(r[1], []).append(r)

    def xg(self, f, k, team):
        m = self.m
        e = own_end(m, f, 1 - team)
        gk = goalie(m, f, 1 - team)
        if e is None or gk is None:
            return None
        gl = 264 * e
        px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
        w = XG._work(self.rows, f, k)
        sha = w[5] if w else 15
        gw = XG._work(self.rows, f, gk) or [64, 15, 15, 11, 15, 0]
        gx, gy = P(m, f, gk)
        vgx, vgy = XG._velocity(m, f, gk)
        reach = 15 if (m["ctrl"][f] >> gk) & 1 else XG.REACH[min(19, (gw[1] + 2) >> 1)]
        d = XG.auto_aim(px, py, gx + 8 * vgx, gy + 8 * vgy, gl)
        tx, tz = XG.AIM[d]
        goalie_ = XG.Goalie(gx, gy, vgx * 4096, vgy * 4096, *gw[:4])
        rng = random.Random(f"{m.get('name', '')}:{f}:{k}")
        goals = sum(XG.play_out((px, py, 0), (tx, gl, tz), 20000 / 68, sha, (sha + 1) / (sha + 16), goalie_, reach, 0,
                                rng) == "goal" for _ in range(SAMPLES))
        return goals / SAMPLES


def decisions(m, team, M, S, c):
    """Idea 1: at each of the person's passes and shots in the attacking zone, the value of each option."""
    t, N = m["t"], len(m["t"])
    events = [("pass", p) for p in m.get("passes", []) if p["team"] == team and p.get("human") and p.get("result") != "pass shot"]
    events += [("shot", s) for s in m.get("shotList", []) if s["team"] == team and s.get("human") and s["kind"] == "shot"]
    for what, ev in events:
        f = max(1, ev["f"] - 1)
        k = m["owner"][f]
        if k not in skaters(m, f, team) or (what == "shot" and late(m, f, ev.get("xg") or 0)):
            continue
        e = own_end(m, f, 1 - team)
        if e is None:
            continue
        ny = 268 * e
        px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
        if abs(ny - py) > ZONE:
            continue
        up = e > 0
        opts = {"keep": M.threat_at(px, abs(ny - py), up)}
        shoot = S.xg(f, k, team)
        if shoot is not None:
            opts["shoot"] = shoot
        target = None
        for j in skaters(m, f, team):
            if j == k:
                continue
            x, y = P(m, f, j)
            if abs(ny - y) > 268:
                continue
            v = M.completion(math.hypot(x - px, y - py), lane_gap(m, f, team, px, py, x, y)) * M.after_pass(x, abs(ny - y), up)
            opts[f"pass{j}"] = v
            if what == "pass" and roster(m, f, j) == ev.get("to"):
                target = f"pass{j}"
        chosen = "shoot" if what == "shot" else target
        if chosen is None or chosen not in opts:
            continue
        best = max(opts, key=opts.get)
        kind = lambda o: "pass" if o.startswith("pass") else o
        c["dec"] += 1
        c["dec_" + kind(chosen)] += 1
        c["dec_best"] += opts[chosen] >= opts[best] - 0.02
        c["dec_lost"] += opts[best] - opts[chosen]
        c["dec_bestwas_" + kind(best)] += 1
        if kind(chosen) != kind(best) and opts[best] - opts[chosen] > 0.05:
            c[f"dec_{kind(chosen)}_not_{kind(best)}"] += 1


def measure(m, team, M):
    t, N, opp = m["t"], len(m["t"]), 1 - team
    mine, theirs = range(team * 6, team * 6 + 6), range(opp * 6, opp * 6 + 6)
    c = Counter()
    shots = m.get("shotList", [])
    hits = [h for h in m.get("hits", []) if h["team"] == team and h.get("human")]
    opp_shots = [s for s in shots if s["team"] == opp]
    decisions(m, team, M, Shooter(m), c)
    # ---- shot selection (the person's own shots and one-timers; not in a period's last seconds)
    for s in shots:
        if s["team"] != team or not s.get("human") or s["kind"] not in ("shot", "one-timer"):
            continue
        if late(m, s["f"], s.get("xg") or 0):
            c["sh_late"] += 1
            continue
        e = own_end(m, s["f"], opp)
        gk = goalie(m, s["f"], opp)
        if e is None or gk is None:
            continue
        ny = 268 * e
        off = seg_dist(*P(m, s["f"], gk), s["x"], s["y"], 0, ny)
        xg = s.get("xg") or 0
        c["sh"] += 1
        c["sh_xg"] += xg
        c["sh_goal"] += s["result"] == "goal"
        c["sh_ot"] += s["kind"] == "one-timer"
        c["sh_off10"] += off >= 10
        c["sh_set"] += off < 5
        c["sh_low"] += xg < 0.05
        c["sh_far"] += math.hypot(s["x"], ny - s["y"]) >= 120
    # ---- passing
    for p in m.get("passes", []):
        if p["team"] != team or not p.get("human") or p.get("result") == "pass shot":
            continue
        z = p.get("zone", "?")
        ok = p["result"] in ("completed", "one-timer")
        c["pa_" + z] += 1
        c["pa_ok_" + z] += ok
        c["pa_pick_" + z] += p["result"] == "intercepted"
        e = own_end(m, p["f"], opp)
        if e is None:
            continue
        ny = 268 * e
        nxt = next((s for s in shots if s["team"] == team and 0 < t[s["f"]] - t[p["f"]] <= 3000), None)
        if nxt and any(m["owner"][q] in theirs for q in range(p["f"], nxt["f"])):
            nxt = None
        if ok and nxt:
            c["pa_shot"] += 1
            c["pa_shot_xg"] += nxt.get("xg") or 0
        if z == "att" and p["x0"] * p["x1"] < 0 and abs(p["x1"] - p["x0"]) >= 40 and abs(ny - p["y1"]) < 90:
            c["pa_across"] += 1
            c["pa_across_ok"] += ok
            c["pa_across_shot"] += bool(ok and nxt)
            c["pa_across_xg"] += (nxt.get("xg") or 0) if ok and nxt else 0
    # ---- bursts and pokes by purpose; defensive position; switch timing (the other team has the puck)
    prev_k, prev_state, last_sample = None, None, -10 ** 9
    for f in range(1, N - 1):
        if m["owner"][f] not in theirs or m["puck"][3 * f + 2] < -100:
            prev_k = None
            continue
        k = ctrl_skater(m, f, team)
        e = own_end(m, f, team)
        if k is None or e is None:
            prev_k = None
            continue
        ny = 268 * e
        x, y = P(m, f, k)
        px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
        fx, fy = facing(m, f, k)
        a, b = anim(m, f, k), anim(m, f - 1, k)
        goal_side = lambda q, kk: math.hypot(P(m, q, kk)[0], ny - P(m, q, kk)[1]) < math.hypot(m["puck"][3 * q], ny - m["puck"][3 * q + 1])
        if a == "0c5e" and b != "0c5e":
            target = any(math.hypot(*(d := (P(m, f, o)[0] - x, P(m, f, o)[1] - y))) < CHECK_REACH
                         and angle_to(fx, fy, *d) <= CHECK_CONE for o in skaters(m, f, opp))
            later = next((q for q in range(f, N) if t[q] - t[f] >= 1500), N - 1)
            if target:
                c["b_check"] += 1
                landed = any(0 <= t[h["f"]] - t[f] <= 700 for h in hits)
                c["b_check_landed"] += landed
                last_man = not any(goal_side(f, kk) for kk in skaters(m, f, team) if kk != k)
                if last_man:
                    c["b_lastman"] += 1
                    if not landed:
                        c["b_lastman_miss"] += 1
                        c["b_lastman_shot"] += any(0 < t[s["f"]] - t[f] <= 4000 for s in opp_shots)
            elif not goal_side(f, k) and fy * (ny - y) > 0:
                c["b_recover"] += 1
                c["b_recover_ok"] += goal_side(later, k)
            elif angle_to(fx, fy, -x, (ny - 70 * (1 if ny > 0 else -1)) - y) <= 50:
                c["b_position"] += 1
                c["b_position_ok"] += goal_side(later, k) and seg_dist(*P(m, later, k), m["puck"][3 * later],
                                                                      m["puck"][3 * later + 1], 0, ny) < 30
            else:
                c["b_other"] += 1
        if a == "0b24" and b != "0b24":
            d = math.hypot(px - x, py - y)
            away = angle_to(fx, fy, px - x, py - y) > 45
            near_pass = any(abs(t[p["f"]] - t[f]) <= 600 and seg_dist(x, y, p["x0"], p["y0"], p["x1"], p["y1"]) < 25
                            for p in m.get("passes", []) if p["team"] == opp)
            zone = "own" if abs(ny - py) <= ZONE else ("att" if abs(ny - py) >= 536 - ZONE else "neu")
            cost = any(0 < t[s["f"]] - t[f] <= 4000 for s in opp_shots)
            if d <= 30:
                kind = "steal"
            elif away or near_pass:
                kind = "lane"
            else:
                kind = "wasted"
            c[f"k_{kind}_{zone}"] += 1
            c[f"k_{kind}_cost"] += cost
            if d <= 30:
                c["k_steal"] += 1
                c["k_steal_won"] += any(m["owner"][q] in mine for q in range(f, N) if t[q] - t[f] <= 700)
            elif away or near_pass:
                c["k_lane"] += 1
                c["k_lane_won"] += any(g["from"] == opp and g["how"].startswith("pass") and 0 <= t[g["f"]] - t[f] <= 1000
                                       for g in m.get("turnovers", []))
            else:
                c["k_wasted"] += 1
        # defensive position in his end, four times a second
        if abs(ny - py) <= ZONE and t[f] - last_sample >= 250:
            last_sample = t[f]
            st = position_state(m, f, k, ny)
            c["pos_n_" + st] += 1
        # switch timing: the controlled skater changes and stays for 0.3 s
        if prev_k is not None and k != prev_k and abs(ny - py) <= ZONE:
            after = next((q for q in range(f, N) if t[q] - t[f] >= 300), None)
            if after and ctrl_skater(m, after, team) == k:
                s_old, s_new = prev_state, position_state(m, after, k, ny)
                c["sw"] += 1
                c["sw_good"] += s_old != "in" and s_new == "in"
                c["sw_bad"] += s_old == "in" and s_new != "in"
        prev_k, prev_state = k, position_state(m, f, k, ny)
    # ---- where his skater was at each shot against from his end
    for s in opp_shots:
        if s["kind"] not in ("shot", "one-timer") or late(m, s["f"], s.get("xg") or 0):
            continue
        f = max(0, s["f"] - 1)
        k, e = ctrl_skater(m, f, team), own_end(m, f, team)
        if k is None or e is None or abs(268 * e - m["puck"][3 * f + 1]) > ZONE:
            continue
        st = position_state(m, f, k, 268 * e)
        c["sa_" + st] += 1
        c["sa_xg_" + st] += s.get("xg") or 0
    # ---- the person's checks that the game counted
    for h in hits:
        c["hit"] += 1
        c["hit_down"] += h.get("outcome") == "knocked down"
    # ---- the goalie when the person took him
    gk_prev = False
    for f in range(N):
        gk = goalie(m, f, team)
        on = gk is not None and bool(m["ctrl"][f] >> gk & 1)
        if on and not gk_prev:
            e = own_end(m, f, team)
            if e is not None:
                why = takeover_reason(m, f, team, 268 * e)
                if why == "auto":
                    c["gt_auto"] += 1
                    gk_prev = on
                    continue
                c["gt"] += 1
                c["gt_" + why] += 1
                end = next((q for q in range(f, N) if t[q] - t[f] > 3000), N - 1)
                nxt = next((s for s in opp_shots if 0 <= t[s["f"]] - t[f] <= 3000 and s["kind"] in ("shot", "one-timer")), None)
                if nxt:
                    c[f"gt_{why}_shot"] += 1
                    c[f"gt_{why}_goal"] += nxt["result"] == "goal"
                    c[f"gt_{why}_xg"] += nxt.get("xg") or 0
                won = next((q for q in range(f, end) if m["owner"][q] >= 0), None)
                c[f"gt_{why}_ours"] += won is not None and m["owner"][won] in mine
        gk_prev = on
    for s in opp_shots:
        if s["kind"] not in ("shot", "one-timer") or late(m, s["f"], s.get("xg") or 0):
            continue
        who = "p" if s.get("gctl") == "human" else "c"
        kind = "onetimer" if s["kind"] == "one-timer" else s["type"].split()[0]
        c[f"g{who}_{kind}"] += 1
        c[f"g{who}_{kind}_goal"] += s["result"] == "goal"
        c[f"g{who}_{kind}_xg"] += s.get("xg") or 0
    return c


REASONS = [("breakaway", "1 an opposing breakaway"), ("onetimer", "2 a one-timer coming (their pass in the air)"),
           ("drive", "3 a carrier driving at the net (shot or deke)"), ("dump", "4 the puck fired down the ice"),
           ("loose", "5 a loose puck near the net"), ("behind", "6 a carrier behind or beside the net"),
           ("other", "none of these")]
# also "auto": the goalie caught the puck and the game gave the person control of him (not a decision)


def takeover_reason(m, f, team, ny):
    """Why the person took the goalie (the user's six reasons), from the moment he did."""
    t, opp = m["t"], 1 - team
    theirs = range(opp * 6, opp * 6 + 6)
    gk = goalie(m, f, team)
    if any(m["owner"][q] == gk for q in range(max(0, f - 6), min(len(t), f + 7))):
        return "auto"                          # he caught it: the game hands the person his goalie
    o = m["owner"][f]
    px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
    if o in theirs:
        cx, cy = P(m, f, o)
        near = math.hypot(cx, ny - cy)
        if near < 45 or abs(cy) >= 264 and cy * ny > 0:
            return "behind"
        if abs(ny - cy) < 268 and not any(math.hypot(*P(m, f, k)[:1], ny - P(m, f, k)[1]) < near
                                          for k in skaters(m, f, team)):
            return "breakaway"
        b = next((q for q in range(f, 0, -1) if t[f] - t[q] >= 150), f)
        bx, by = P(m, b, o)
        if near < 130 and math.hypot(bx, ny - by) - near > 3:
            return "drive"
        return "other"
    if o >= 0:
        return "other"
    if any(p["team"] == opp and 0 <= t[f] - t[p["f"]] <= 1200 and abs(ny - p["y1"]) < ZONE for p in m.get("passes", [])):
        return "onetimer"
    last = next((m["owner"][q] for q in range(f, 0, -1) if m["owner"][q] >= 0), -1)
    vy = m["puckV"][2 * f + 1] * 100 if "puckV" in m else 0
    if last in theirs and math.hypot(px, ny - py) > 100 and vy * ny > 0 and abs(vy) > 8000:
        return "dump"
    if math.hypot(px, ny - py) < 100:
        return "loose"
    return "other"


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


def rows(c):
    """(section, label, value, + more is better / - less is better / '' neither)."""
    sh, dec = c["sh"], c["dec"]
    pos_n = sum(c["pos_n_" + s] for s in ("in", "off", "up"))
    g = lambda who, kind: (f"{c[f'g{who}_{kind}']} / {c[f'g{who}_{kind}_goal']} / {c[f'g{who}_{kind}_xg'] / max(1, c[f'g{who}_{kind}']):.2f}"
                           if c[f"g{who}_{kind}"] else "-")
    return [
        ("Decisions with the puck", "passes and shots judged (attacking zone)", f"{dec} ({c['dec_shoot']} shots)", ""),
        ("Decisions with the puck", "picked the best option (within 0.02)", pct(c["dec_best"], dec), "+"),
        ("Decisions with the puck", "value left on the table, per decision", f"{c['dec_lost'] / max(1, dec):.3f}", "-"),
        ("Decisions with the puck", "shot when a pass was clearly better", c["dec_shoot_not_pass"], "-"),
        ("Decisions with the puck", "passed when a shot was clearly better", c["dec_pass_not_shoot"], "-"),
        ("Decisions with the puck", "passed when keeping it was clearly better", c["dec_pass_not_keep"], "-"),
        ("Shot selection", "the person's shots (one-timers); end-of-period shots left out",
         f"{sh} ({c['sh_ot']}); {c['sh_late']}", ""),
        ("Shot selection", "xG per shot", f"{c['sh_xg'] / max(1, sh):.2f}", "+"),
        ("Shot selection", "goals / xG", f"{c['sh_goal']} / {c['sh_xg']:.1f}", ""),
        ("Shot selection", "at a goalie 10+ off the shot line", f"{c['sh_off10']} ({pct(c['sh_off10'], sh)})", "+"),
        ("Shot selection", "at a set goalie (within 5)", f"{c['sh_set']} ({pct(c['sh_set'], sh)})", "-"),
        ("Shot selection", "low-value (xG under 0.05) / from 40+ ft", f"{c['sh_low']} / {c['sh_far']}", "-"),
        ("Passing", "attacking zone: completed / picked off", f"{c['pa_ok_att']}/{c['pa_att']} / {c['pa_pick_att']}", "+"),
        ("Passing", "neutral zone: completed / picked off", f"{c['pa_ok_neu']}/{c['pa_neu']} / {c['pa_pick_neu']}", "+"),
        ("Passing", "own zone: completed / picked off", f"{c['pa_ok_def']}/{c['pa_def']} / {c['pa_pick_def']}", "+"),
        ("Passing", "passes that set up a shot within 3 s (xG)", f"{c['pa_shot']} ({c['pa_shot_xg']:.1f})", "+"),
        ("Passing", "across the slot: tried / completed / shot (xG)",
         f"{c['pa_across']} / {c['pa_across_ok']} / {c['pa_across_shot']} ({c['pa_across_xg']:.1f})", "+"),
        ("Bursts (C without the puck)", "check attempts / landed", f"{c['b_check']} / {c['b_check_landed']} ({pct(c['b_check_landed'], c['b_check'])})", "+"),
        ("Bursts (C without the puck)", "recoveries / got him goal-side", f"{c['b_recover']} / {c['b_recover_ok']} ({pct(c['b_recover_ok'], c['b_recover'])})", "+"),
        ("Bursts (C without the puck)", "positioning / got him into position", f"{c['b_position']} / {c['b_position_ok']} ({pct(c['b_position_ok'], c['b_position'])})", "+"),
        ("Bursts (C without the puck)", "other bursts", c["b_other"], ""),
        ("Bursts (C without the puck)", "the game's counted checks: knockdowns", f"{c['hit_down']} of {c['hit']}", "+"),
        ("Bursts (C without the puck)", "risky: check attempts as the last man back / missed / shot against in 4 s",
         f"{c['b_lastman']} / {c['b_lastman_miss']} / {c['b_lastman_shot']}", "-"),
        ("Pokes (B)", "steal attempts (within reach) / won the puck", f"{c['k_steal']} / {c['k_steal_won']} ({pct(c['k_steal_won'], c['k_steal'])})", "+"),
        ("Pokes (B)", "passing-lane pokes / a pass picked off within 1 s", f"{c['k_lane']} / {c['k_lane_won']}", "+"),
        ("Pokes (B)", "wasted (out of reach, at the carrier, no pass near)", c["k_wasted"], "-"),
        ("Pokes (B)", "passing-lane pokes in their end / neutral zone / his end",
         f"{c['k_lane_att']} / {c['k_lane_neu']} / {c['k_lane_own']}", ""),
        ("Pokes (B)", "a shot against within 4 s: after a steal attempt / lane poke / wasted",
         f"{pct(c['k_steal_cost'], c['k_steal'])} / {pct(c['k_lane_cost'], c['k_lane'])} / {pct(c['k_wasted_cost'], c['k_wasted'])}", "-"),
        ("Defensive position", "his skater in position / goal-side off the line / caught up ice",
         f"{pct(c['pos_n_in'], pos_n)} / {pct(c['pos_n_off'], pos_n)} / {pct(c['pos_n_up'], pos_n)}", ""),
        ("Defensive position", "at shots against: in position / off the line / up ice (xG of those shots)",
         " / ".join(f"{c['sa_' + st]} ({c['sa_xg_' + st]:.1f})" for st in ("in", "off", "up")), ""),
        ("Defensive position", "switches: into position / out of position (of all)", f"{c['sw_good']} / {c['sw_bad']} (of {c['sw']})", ""),
        ("Goalie", "takeovers (and times the game handed him the goalie, who had caught the puck)", f"{c['gt']} ({c['gt_auto']})", ""),
    ] + [("Goalie", f"· {label}: takeovers / a shot within 3 s / goals (xG) / his team had the puck next",
          f"{c['gt_' + key]} / {c[f'gt_{key}_shot']} / {c[f'gt_{key}_goal']} ({c[f'gt_{key}_xg']:.1f}) / {c[f'gt_{key}_ours']}", "")
         for key, label in REASONS] + [
        ("Goalie", "one-timers faced, person in net: shots / goals / xG each", g("p", "onetimer"), ""),
        ("Goalie", "one-timers faced, computer in net", g("c", "onetimer"), ""),
        ("Goalie", "slapshots faced, person in net", g("p", "slapshot"), ""),
        ("Goalie", "slapshots faced, computer in net", g("c", "slapshot"), ""),
        ("Goalie", "wrist shots faced, person in net", g("p", "wrist"), ""),
        ("Goalie", "wrist shots faced, computer in net", g("c", "wrist"), ""),
    ]


def main():
    a, b, names = sys.argv[1], sys.argv[2], sys.argv[3:]
    M = Models()
    tot = {a: Counter(), b: Counter()}
    per = []
    for n in names:
        m = json.loads(load_js_object(find(n)[0]))
        row = {}
        for ab in (a, b):
            got = measure(m, m["abbr"].index(ab), M)
            tot[ab].update(got)
            row[ab] = rows(got)
        per.append((n, row))
        print(n, flush=True)
    ra, rb = rows(tot[a]), rows(tot[b])
    out = [f"# How the people played: {a} vs {b}", "", "Games: " + ", ".join(names), "",
           "Both people measured the same way; only their own skater or goalie counts. "
           "+ more is better, - less is better. How each is measured: analysis/coach_report.py.", ""]
    section = None
    for (sec, label, va, way), (_, _, vb, _) in zip(ra, rb):
        if sec != section:
            out += ["", f"## {sec}", "", f"| | {a} | {b} | |", "|---|---|---|---|"]
            section = sec
        out.append(f"| {label} | {va} | {vb} | {way} |")
    out += ["", "## Per game", ""]
    for n, row in per:
        out += [f"### {n}", "", f"| | {a} | {b} |", "|---|---|---|"]
        out += [f"| {x[1]} | {x[2]} | {y[2]} |" for x, y in zip(row[a], row[b])]
        out.append("")
    path = Path("reports") / f"coach_{names[0]}.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
