"""SNES hooks, holds and pokes, and the B button's poke-or-switch, against the recordings (2026-10-21; SNES_MECHANICS 7.3).
Code (NHL94SNES): Y without the puck -> Holdplayer: the nearest opponent in front (distance + 16 x facing difference)
is hooked (SPAhook), or held (SPAHold) when he faces you. On contact (holdcheck, from checkcheck) with him within 45
degrees of where you face: both velocities averaged, he flails (SPAflail) and keeps the puck, a hooking / holding roll.
A poke (SPAsweepchk) whose body touches a skater within 45 degrees in front (Bcheck): with penalties on, or by a
computer skater, he always falls; a person's poke with penalties off needs randoma8(16 + Checking - his Stickhandling)
>= 12. B without the puck (doinput -> findpc): a poke when the puck is carried and the skater is within about 20 of it,
else the team's skater with the lowest distance to the puck (+32 a direction step beyond the first away from up-ice
while carried) gets control (the current one pokes).
python analysis/snes_hook_poke_study.py"""
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402

K = 12
HOOK, HOOK2, HOLD, HOLD2, FLAIL, POKE, BURST = "f864", "f3d8", "f374", "f3a6", "f46a", "f208", "f342"
DOWN = {"f49c", "f54e", "f6c0", "f7b2"}  # falls, upended, stumble
B, Y = 0x8000, 0x4000
FOLDERS = [Path("matches"), Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches"))]


def games():
    seen = set()
    for folder in FOLDERS:
        for p in sorted(folder.glob("*.js")):
            if p.stem in seen or p.stem.startswith("_") or "_state" in p.stem or p.stem == "season":
                continue
            m = json.loads(load_js_object(p))
            if m.get("system") != "snes" or not m.get("padSnes"):
                continue
            seen.add(p.stem)
            yield p.stem, m


def main():
    c = Counter()
    rule = Counter()
    for name, m in games():
        t, N, own, P = m["t"], len(m["t"]), m["owner"], m["puck"]
        anim = lambda i, k: m["anim"][(i * K + k) * 4:(i * K + k) * 4 + 4]
        pos = lambda i, k: (m["pos"][(i * K + k) * 2], m["pos"][(i * K + k) * 2 + 1])
        role = lambda i, k: m["role"][i * K + k]
        after = lambda i, ms: next((q for q in range(i, N) if t[q] - t[i] > ms), N - 1)
        # hooks and holds: every start, by whom, and whether it caught someone (holder into hook2 / hold2, a flail nearby)
        for k in range(K):
            for i in range(1, N):
                a = anim(i, k)
                if a in (HOOK, HOLD) and anim(i - 1, k) != a and role(i, k) in "12345":
                    kind = "hook" if a == HOOK else "hold"
                    person = bool(m["ctrl"][i] >> k & 1)
                    c[(kind, "person" if person else "cpu")] += 1
                    end = after(i, 700)
                    caught = next((q for q in range(i, end) if anim(q, k) in (HOOK2, HOLD2)), None)
                    if caught is None:
                        continue
                    c[(kind, "caught")] += 1
                    opp = range(6, 12) if k < 6 else range(6)
                    victim = min((v for v in opp if role(caught, v) in "12345"),
                                 key=lambda v: math.hypot(pos(caught, v)[0] - pos(caught, k)[0], pos(caught, v)[1] - pos(caught, k)[1]))
                    flail = any(anim(q, victim) == FLAIL for q in range(caught, after(caught, 300)))
                    c[(kind, "victim flailed")] += flail
                    had = any(own[q] == victim for q in range(max(0, caught - 20), caught + 1))
                    if had:
                        c[(kind, "on the carrier")] += 1
                        w = after(caught, 1500)
                        nxt = next((own[q] for q in range(caught + 1, w) if own[q] >= 0 and own[q] != victim), None)
                        kept = all(own[q] in (victim, -1) for q in range(caught, w))
                        c[(kind, "carrier kept it 1.5 s")] += kept
                        c[(kind, "hooker's team got it")] += nxt is not None and (nxt < 6) == (k < 6)
                        # speed before and after: the averaging slows the carrier to the hooker's pace
                        sp = lambda q: math.hypot(pos(q, victim)[0] - pos(q - 4, victim)[0], pos(q, victim)[1] - pos(q - 4, victim)[1]) / max(1e-3, (t[q] - t[q - 4]) / 1000)
                        if caught > 8 and caught + 12 < N:
                            c[(kind, "carrier speed before")] += sp(caught - 1)
                            c[(kind, "carrier speed after")] += sp(caught + 12)
        # pokes: trips (a skater in front going down) and takeaways
        for k in range(K):
            for i in range(1, N):
                if anim(i, k) == POKE and anim(i - 1, k) != POKE and role(i, k) in "12345":
                    person = bool(m["ctrl"][i] >> k & 1)
                    who = "person" if person else "cpu"
                    c[("poke", who)] += 1
                    x, y = pos(i, k)
                    d = math.hypot(P[3 * i] - x, P[3 * i + 1] - y)
                    if d > 30:
                        c[("poke", who, "out of reach")] += 1
                        continue
                    end = after(i, 500)
                    opp = range(6, 12) if k < 6 else range(6)
                    carrier = own[i] if own[i] in opp else None
                    tripped = any(anim(q, v) in DOWN for q in range(i, end) for v in opp
                                  if math.hypot(pos(q, v)[0] - pos(q, k)[0], pos(q, v)[1] - pos(q, k)[1]) < 25)
                    took = any(own[q] >= 0 and (own[q] < 6) == (k < 6) for q in range(i, end))
                    c[("poke", who, "in reach")] += 1
                    c[("poke", who, "tripped")] += tripped
                    c[("poke", who, "won it")] += took
                    c[("poke", who, "on the carrier")] += carrier is not None
        # the B button without the puck: poke or switch, against the rule
        pads = [(0, m.get("padTeam", -1)), (1, m.get("pad2Team", -1))]
        rows = m["padSnes"]
        for which, team in pads:
            if team not in (0, 1):
                continue
            mine = range(team * 6, team * 6 + 6)
            for j in range(1, len(rows)):
                f = rows[j][0]
                if not (rows[j][1 + which] & B and not rows[j - 1][1 + which] & B):
                    continue
                # a press soon after another (mashing) lands on a skater still in the last one's poke: left out
                if any(rows[q][1 + which] & B and not rows[q - 1][1 + which] & B and t[f] - t[rows[q][0]] < 500 for q in range(max(1, j - 12), j)):
                    rule[("mashed",)] += 1
                    continue
                if P[3 * f + 2] < -100 or own[f] in mine:
                    continue  # play stopped, or his team has the puck (a pass)
                cur = next((k for k in mine if m["ctrl"][f] >> k & 1 and role(f, k) in "12345"), None)
                if cur is None:
                    continue
                end = after(f, 250)
                poked = any(anim(q, cur) == POKE for q in range(f, end))
                switched = next((k for q in range(f, end) for k in mine if k != cur and m["ctrl"][q] >> k & 1), None)
                outcome = "poke" if poked else "switch" if switched is not None else "nothing"
                carried = own[f] >= 0  # by the other team (his own team's puck was left out above)
                px, py = P[3 * f], P[3 * f + 1]
                approx = lambda dx, dy: (lambda a, b: a + (b >> 2) if (a >> 1) >= b else a + ((b + (b >> 1)) >> 2))(max(abs(int(dx)), abs(int(dy))), min(abs(int(dx)), abs(int(dy))))
                dcur = math.hypot(px - pos(f, cur)[0], py - pos(f, cur)[1])
                up = 1 if next((pos(f, g)[1] < 0 for g in mine if role(f, g) == "0"), True) else -1  # up-ice: away from his goalie
                locked = anim(f, cur) in (HOOK, HOOK2, HOLD, HOLD2) or anim(f, cur) in DOWN
                for sense, pref in (("puck up-ice preferred", 0), ("puck down-ice preferred", 180)):
                    def score(k):
                        x, y = pos(f, k)
                        s = approx(px - x, py - y)
                        if carried:  # findpc: (direction difference - 1) x 32 against the preferred direction
                            ang = (math.degrees(math.atan2(px - x, (py - y) * up)) - pref) % 360
                            steps = round(min(ang, 360 - ang) / 45)
                            s += 32 * max(0, steps - 1)
                        return s
                    if carried and dcur < 20 and not locked:
                        predicted = "poke"
                    else:
                        # findpc skips locked skaters (falls, hooks, holds), his own current one included
                        pool = [k for k in mine if role(f, k) in "12345" and anim(f, k) not in DOWN | {HOOK, HOOK2, HOLD, HOLD2}]
                        best = min(pool, key=score) if pool else cur
                        predicted = ("nothing" if locked else "poke") if best == cur else "switch"
                    rule[(sense, predicted, outcome)] += 1
                    if sense.startswith("puck up") and predicted != outcome:
                        rule[("miss", predicted, outcome, anim(f, cur), "carried" if carried else "loose", "near" if dcur < 20 else "far")] += 1
    print("Hooks and holds (all games):")
    for kind in ("hook", "hold"):
        n = c[(kind, "person")] + c[(kind, "cpu")]
        on = c[(kind, "on the carrier")]
        print(f"  {kind}: {n} started (person {c[(kind, 'person')]}, computer {c[(kind, 'cpu')]}); caught someone {c[(kind, 'caught')]}, "
              f"victim flailed {c[(kind, 'victim flailed')]}; on the carrier {on}: kept it 1.5 s {c[(kind, 'carrier kept it 1.5 s')]}, "
              f"hooker's team got it {c[(kind, 'hooker\'s team got it')]}"
              + (f"; carrier speed {c[(kind, 'carrier speed before')] / on:.0f} -> {c[(kind, 'carrier speed after')] / on:.0f} units/s" if on else ""))
    print("Pokes:")
    for who in ("person", "cpu"):
        r = c[("poke", who, "in reach")]
        print(f"  {who}: {c[('poke', who)]}, out of reach (over 30) {c[('poke', who, 'out of reach')]}; in reach {r}: "
              f"tripped someone {c[('poke', who, 'tripped')]}, won the puck {c[('poke', who, 'won it')]} (on a carrier {c[('poke', who, 'on the carrier')]})")
    misses = sorted(((k[1:], n) for k, n in rule.items() if k[0] == "miss"), key=lambda kv: -kv[1])[:15]
    print("Misses by the skater's animation at the press:", *[f"{k}: {n}" for k, n in misses], sep=chr(10) + '   ')
    print("B without the puck (the other team's puck or a loose one): predicted -> what happened")
    for sense in ("puck up-ice preferred", "puck down-ice preferred"):
        part = {k[1:]: n for k, n in rule.items() if k[0] == sense}
        print(f"  (presses within 0.5 s of another, left out: {rule[('mashed',)]})") if sense.startswith("puck up") else None
        ok = sum(n for (p, o), n in part.items() if p == o)
        print(f"  {sense}: agree {ok} of {sum(part.values())} ({100 * ok / max(1, sum(part.values())):.0f}%)")
        for (p, o), n in sorted(part.items(), key=lambda kv: -kv[1]):
            print(f"     {p:7} -> {o:7}: {n}")


if __name__ == "__main__":
    main()
