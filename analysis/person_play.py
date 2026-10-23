"""What each person did with the skater they controlled (2026-10-21, the user: did NYI's player use his skaters more
cleverly than BOS's?). Both teams measured the same way, per game:
offence (the person always has the carrier): carries, how long, whether they reach the slot, how they end; passes;
the person's turnovers. Defence (the other team has the puck): bursts and what a missed one costs, pokes and from how
far, control switches, whether the controlled skater is the one nearest the puck, the gap at the other team's entries.
python analysis/person_play.py   (the BOS-NYI games; coach_report.py runs these measures on any games)"""
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
from export_match import own_end  # noqa: E402

K = 12
GAMES = [("P", "2026-10-21_1137_NYI-BOS", "series"), ("P", "2026-10-21_1147_NYI-BOS", "series"),
         ("P", "2026-10-21_1156_BOS-NYI", "series"), ("D", "2026-10-21_1054_BOS-NYI", "contrast"),
         ("D", "2026-10-21_1121_BOS-NYI", "contrast")]
BASE = {"D": Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches")), "P": Path("matches")}


def roster(m, f, k):
    c = m["roster"][f * K + k]
    return int(c, 36) if c not in "x-" else -1


def pos(m, f, k):
    return m["pos"][(f * K + k) * 2], m["pos"][(f * K + k) * 2 + 1]


def anim(m, f, k):
    return m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4]


def ctrl_skater(m, f, team):
    c = m["ctrl"][f]
    for k in range(team * 6, team * 6 + 6):
        if c >> k & 1 and m["role"][f * K + k] in "12345":
            return k
    return None


def measure(m, team):
    t, N, opp = m["t"], len(m["t"]), 1 - team
    mine = range(team * 6, team * 6 + 6)
    theirs = range(opp * 6, opp * 6 + 6)
    shots = [s for s in m.get("shotList", []) if s["team"] == team]
    passes = [p for p in m.get("passes", []) if p["team"] == team]
    turnovers = [g for g in m.get("turnovers", []) if g["from"] == team]
    out = Counter()
    # ---- offence: carries by the person's skater
    f = 0
    while f < N:
        o = m["owner"][f]
        if o in mine and m["ctrl"][f] >> o & 1 and m["role"][f * K + o] in "12345":
            s0 = f
            while f < N and m["owner"][f] == o:
                f += 1
            e = f - 1
            dur = (t[e] - t[s0]) / 1000
            if dur < 0.3:
                continue
            end = own_end(m, e, team)
            if end is None:
                continue
            net_y = -268 * end                          # the net attacked
            near = min(math.hypot(m["puck"][3 * q], net_y - m["puck"][3 * q + 1]) for q in range(s0, e + 1))
            idx = roster(m, e, o)
            how = "other"
            if any(s["idx"] == idx and -5 <= s["f"] - e <= 25 for s in shots):
                how = "shot"
            elif any(p["idx"] == idx and -5 <= p["f"] - e <= 25 for p in passes):
                how = "pass"
            elif any(g["giver"] == idx and -5 <= g.get("lost", g["f"]) - e <= 25 for g in turnovers):
                how = "lost"
            out["carries"] += 1
            out["carry_s"] += dur
            out["carry_" + how] += 1
            out["carry_slot"] += near < 60
            out["slot_then_" + how] += near < 60
            continue
        f += 1
    hp = [p for p in passes if p.get("human")]
    out["passes"] = len(hp)
    out["pass_ok"] = sum(p["result"] in ("completed", "one-timer") for p in hp)
    out["pass_onetimer"] = sum(p["result"] == "one-timer" for p in hp)
    out["pass_picked"] = sum(p["result"] == "intercepted" for p in hp)
    out["pass_att_cross"] = sum(1 for p in hp if p.get("zone") == "att" and p["x0"] * p["x1"] < 0 and abs(p["x1"] - p["x0"]) >= 60)
    hum_to = [g for g in turnovers if m["ctrl"][g.get("lost", g["f"])] >> next((k for k in mine if roster(m, g.get("lost", g["f"]), k) == g["giver"]), 0) & 1]
    for g in hum_to:
        out["person_to_" + g["how"].split()[0]] += 1
    out["person_to"] = len(hum_to)
    # ---- defence
    prev_k, prev_a = None, {}
    for f in range(1, N - 1):
        dt = min(100, t[f + 1] - t[f]) / 1000
        o = m["owner"][f]
        if o not in theirs or m["puck"][3 * f + 2] < -100:
            continue
        out["def_s"] += dt
        k = ctrl_skater(m, f, team)
        if k is None:
            continue
        if prev_k is not None and k != prev_k:
            out["switches"] += 1
        prev_k = k
        px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
        nearest = min((kk for kk in mine if m["role"][f * K + kk] in "12345"), key=lambda kk: math.hypot(pos(m, f, kk)[0] - px, pos(m, f, kk)[1] - py))
        out["nearest_s"] += dt * (nearest == k)
        a, b = anim(m, f, k), anim(m, f - 1, k)
        if a == "0c5e" and b != "0c5e":
            out["bursts"] += 1
            x, y = pos(m, f, k)
            out["burst_close"] += math.hypot(x - px, y - py) < 30
            landed = any(h["team"] == team and h.get("human") and 0 <= t[h["f"]] - t[f] <= 700 for h in m.get("hits", []))
            out["burst_landed"] += landed
            if not landed:
                shot_after = any(s["team"] == opp and 0 <= t[s["f"]] - t[f] <= 4000 for s in m.get("shotList", []))
                out["burst_miss_then_shot"] += shot_after
        if a == "0b24" and b != "0b24":
            out["pokes"] += 1
            x, y = pos(m, f, k)
            out["poke_close"] += math.hypot(x - px, y - py) < 30
            out["poke_won"] += any(m["owner"][q] in mine for q in range(f, min(N, f + 45)) if t[q] - t[f] <= 700)
    # the gap at the other team's entries: the person's skater's distance to the carrier as the puck crosses
    gaps = []
    for e in m.get("zoneEntries", []):
        if e["team"] != opp or e["kind"] != "carried":
            continue
        k = ctrl_skater(m, e["f"], team)
        if k is None:
            continue
        x, y = pos(m, e["f"], k)
        gaps.append(math.hypot(x - m["puck"][3 * e["f"]], y - m["puck"][3 * e["f"] + 1]))
    out["entry_gap_n"] = len(gaps)
    out["entry_gap_sum"] = sum(gaps)
    out["entry_gap_close"] = sum(g < 40 for g in gaps)
    return out


def team_index(m, abbr):
    return m["abbr"].index(abbr) if "abbr" in m else (0 if m["team1"] == {"BOS": "Boston", "NYI": "New York"}[abbr] else 1)


def report(c):
    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "-"
    car = c["carries"]
    return {
        "carries (avg s)": f"{car} ({c['carry_s'] / max(1, car):.1f})",
        "· end in shot / pass / lost": f"{pct(c['carry_shot'], car)} / {pct(c['carry_pass'], car)} / {pct(c['carry_lost'], car)}",
        "· reach the slot (puck within 60)": pct(c["carry_slot"], car),
        "· of those: shot / pass / lost": f"{c['slot_then_shot']} / {c['slot_then_pass']} / {c['slot_then_lost']}",
        "person's passes: completed": f"{c['pass_ok']}/{c['passes']} ({pct(c['pass_ok'], c['passes'])})",
        "· to a one-timer / picked off": f"{c['pass_onetimer']} / {c['pass_picked']}",
        "· cross-ice in the attacking zone": c["pass_att_cross"],
        "person's turnovers (picked/lost/stolen..)": f"{c['person_to']} " + str({k[10:]: v for k, v in c.items() if k.startswith('person_to_')}),
        "defending (s)": round(c["def_s"]),
        "· controls the skater nearest the puck": pct(c["nearest_s"], c["def_s"]),
        "· switches a minute": f"{60 * c['switches'] / max(1, c['def_s']):.1f}",
        "· bursts (within 30 of the puck)": f"{c['bursts']} ({c['burst_close']})",
        "· bursts that landed a check": f"{c['burst_landed']} ({pct(c['burst_landed'], c['bursts'])})",
        "· missed bursts followed by a shot against": f"{c['burst_miss_then_shot']} of {c['bursts'] - c['burst_landed']}",
        "· pokes (within 30) -> puck won": f"{c['pokes']} ({c['poke_close']}) -> {c['poke_won']}",
        "· gap at carried entries against (avg, <40)": f"{c['entry_gap_sum'] / max(1, c['entry_gap_n']):.0f}, {c['entry_gap_close']}/{c['entry_gap_n']}",
    }


def main():
    tot = {("series", "BOS"): Counter(), ("series", "NYI"): Counter(), ("contrast", "BOS"): Counter(), ("contrast", "NYI"): Counter()}
    for w, n, grp in GAMES:
        m = json.loads(load_js_object(BASE[w] / f"{n}.js"))
        for ab in ("BOS", "NYI"):
            tot[(grp, ab)] += measure(m, team_index(m, ab))
    for grp in ("series", "contrast"):
        rb, rn = report(tot[(grp, "BOS")]), report(tot[(grp, "NYI")])
        print(f"\n==== {grp} ({'the three NYI wins' if grp == 'series' else 'the two Boston wins'}), totals")
        wdt = max(len(k) for k in rb)
        print(f"{'':{wdt}}  {'BOS':>28} {'NYI':>28}")
        for k in rb:
            print(f"{k:{wdt}}  {str(rb[k]):>28} {str(rn[k]):>28}")


if __name__ == "__main__":
    main()
