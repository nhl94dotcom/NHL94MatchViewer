"""The Deserve to Win meter (after MoneyPuck's, moneypuck.com/about.htm#meter): how often each team would win if the
game's shots were replayed, each going in with the chance it had. Worked out exactly, not by random replays:

- Every attempt that wasn't blocked counts with its expected goals (tools/xg.py, xg_snes.py). Attempts without one
  get a typical chance (FALLBACK): pass shots and shots / one-timers from games without xG by their recorded rates;
  deflections and scrambles a flat 25% (the converter only finds those when the game counted them, so their recorded
  rate is mostly goals and would copy the result into the meter).
- A team's shots within FLURRY_MS of its previous one form a flurry: one chance that scores if any shot in it does
  (MoneyPuck drops a flurry's later shots once one scores).
- Regulation: each team's goals are the sum of its flurries' chances (exact distribution). Overtime is sudden death:
  if regulation is tied, the real overtime flurries are taken in order, then, for any overtime the game didn't play
  (OT_SECONDS: 10 minutes on the Genesis, 5 on the SNES, the user's), each team scores at its regulation rate (a race
  between two steady scorers). Still tied: a tie (the game allows them).
- Before the end (a replay under way) only the shots so far count and nothing is added for time to come: the meter then
  says who deserved to be ahead.
The viewer has the same rule in JavaScript (deserveToWin); keep the two in step."""
import math

FLURRY_MS = 3000
OT_SECONDS = {"genesis": 600, "snes": 300}
FALLBACK = {
    "genesis": {"shot": 0.17, "one-timer": 0.32, "pass shot": 0.19, "deflection": 0.25, "other": 0.25},
    "snes": {"shot": 0.19, "one-timer": 0.17, "pass shot": 0.19, "deflection": 0.25, "other": 0.25},
}


def chance(shot, system):
    if shot.get("xg") is not None:
        return shot["xg"]
    return FALLBACK.get(system, FALLBACK["genesis"]).get(shot.get("kind"), 0.2)


def flurries(m, upto=None):
    """[(frame, team, chance it scores)] in time order, from the attempts that weren't blocked (up to frame upto)."""
    t, system = m["t"], m.get("system", "genesis")
    shots = sorted((s for s in m.get("shotList") or [] if s.get("result") != "blocked" and (upto is None or s["f"] <= upto)),
                   key=lambda s: s["f"])
    out, last = [], {}
    for s in shots:
        team, p = s["team"], chance(s, system)
        prev = last.get(team)
        if prev is not None and t[s["f"]] - t[out[prev][3]] <= FLURRY_MS:
            f, tm, miss, _ = out[prev]
            out[prev] = [f, tm, miss * (1 - p), s["f"]]
        else:
            last[team] = len(out)
            out.append([s["f"], team, 1 - p, s["f"]])
    return [(f, team, 1 - miss) for f, team, miss, _ in out]


def goal_distribution(chances):
    dist = [1.0]
    for p in chances:
        dist = [(dist[k] if k < len(dist) else 0) * (1 - p) + (dist[k - 1] * p if k else 0) for k in range(len(dist) + 1)]
    return dist


def deserve(m, upto=None):
    """{"win": [home, away] (regulation or overtime), "otWin": [home, away], "tie"}, or with final False (a game under
    way at frame upto): who deserved to be ahead so far, {"win": [...], "tie": level}."""
    system = m.get("system", "genesis")
    period = m["period"]
    last = len(m["t"]) - 1 if upto is None else upto
    final = upto is None or upto >= len(m["t"]) - 1
    fl = flurries(m, upto)
    reg = [[p for f, team, p in fl if team == side and period[f] < 3] for side in (0, 1)]
    dh, da = goal_distribution(reg[0]), goal_distribution(reg[1])
    cum_a = [sum(da[:k]) for k in range(len(dh) + 1)]
    p_home = sum(dh[k] * cum_a[min(k, len(da))] for k in range(len(dh)))
    p_tie = sum(dh[k] * (da[k] if k < len(da) else 0) for k in range(len(dh)))
    p_away = max(0.0, 1 - p_home - p_tie)
    # overtime, sudden death: the real overtime chances in order, then (at the end) the overtime the game didn't play
    ot_win, alive = [0.0, 0.0], 1.0
    for f, team, p in fl:
        if period[f] == 3:
            ot_win[team] += alive * p
            alive *= 1 - p
    if final:
        length = OT_SECONDS.get(system, 600)
        ot_clocks = [m["clock"][i] for i in range(len(m["t"])) if period[i] == 3]
        played = (max(ot_clocks) - min(ot_clocks)) if ot_clocks else 0
        rest = max(0, length - played)
        reg_seconds = sum(max([m["clock"][i] for i in range(len(m["t"])) if period[i] == p] or [0]) for p in (0, 1, 2)) or 1
        rate = [sum(reg[s]) / reg_seconds for s in (0, 1)]
        both = rate[0] + rate[1]
        if both > 0 and rest > 0:
            scored = 1 - math.exp(-both * rest)
            for s in (0, 1):
                ot_win[s] += alive * scored * rate[s] / both
            alive *= 1 - scored
    return {"win": [p_home + p_tie * ot_win[0], p_away + p_tie * ot_win[1]], "otWin": [p_tie * ot_win[0], p_tie * ot_win[1]],
            "tie": p_tie * alive, "final": final}
