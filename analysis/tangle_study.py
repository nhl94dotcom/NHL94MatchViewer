"""Players tangled together (2026-10-21, the user: two SNES overtime winners came after a defender and the carrier
overlapped and the defender couldn't knock him over; SNES_MECHANICS 7.6). Every recorded game, both systems, each game
once: stretches of live play (puck in play) where two opposing skaters stay within NEAR units (bodies normally stop about
16 apart) for at least MIN_MS. For each: how close, how long, whether one of them had the puck, whether the other was in a
burst / check animation during it (a check that didn't land), who controlled each (a person or the computer), and what
came of it within 5 s: the carrier's team kept the puck, took a shot, scored; or a knockdown on either.
python analysis/tangle_study.py"""
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
import systems  # noqa: E402

K = 12
NEAR, DEEP, MIN_MS, JOIN_MS = 14, 8, 700, 300  # bodies normally stop about 16 apart; pieces of one contact joined
FOLDERS = [Path("matches"), Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches"))]


def games():
    seen = set()
    for folder in FOLDERS:
        for p in sorted(folder.glob("*.js")):
            n = p.stem
            if n in seen or n == "season" or n.startswith("_") or "_state" in n or n in ("explore1_menus", "full_buttons"):
                continue
            seen.add(n)
            yield n, p


def study(name, path):
    m = json.loads(load_js_object(path))
    sysm = systems.of_match(m)
    act = sysm.ACTIONS
    checking = set(act.get("lunge", ())) | set(getattr(sysm, "CHECK_MOVES", {}))
    down = set(act.get("down", ()))
    t, N, P, own = m["t"], len(m["t"]), m["puck"], m["owner"]
    pos = lambda i, k: (m["pos"][(i * K + k) * 2], m["pos"][(i * K + k) * 2 + 1])
    skater = lambda i, k: m["role"][i * K + k] in "12345"
    anim = lambda i, k: m["anim"][(i * K + k) * 4:(i * K + k) * 4 + 4]
    out, cur = [], {}
    for i in range(N):
        live = P[3 * i + 2] > -100
        now = set()
        if live:
            for a in range(6):
                if not skater(i, a):
                    continue
                for b in range(6, 12):
                    if not skater(i, b):
                        continue
                    d = math.hypot(pos(i, a)[0] - pos(i, b)[0], pos(i, a)[1] - pos(i, b)[1])
                    if d < NEAR:
                        now.add((a, b))
                        r = cur.setdefault((a, b), {"a": i, "b": i, "min": d})
                        r["b"], r["min"] = i, min(r["min"], d)
        for key in list(cur):
            if key not in now and t[i] - t[cur[key]["b"]] > JOIN_MS:  # apart long enough: the contact is over
                r = cur.pop(key)
                if t[r["b"]] - t[r["a"]] >= MIN_MS:
                    out.append((key, r))
    events = []
    for (a, b), r in out:
        s, e = r["a"], r["b"]
        holders = Counter(own[q] for q in range(s, e + 1) if own[q] in (a, b))
        carrier = holders.most_common(1)[0][0] if holders else None
        defender = (b if carrier == a else a) if carrier is not None else None
        ev = {"game": name, "system": m.get("system", "genesis"), "f": s, "ms": t[e] - t[s], "min": r["min"],
              "carrier": carrier is not None}
        if carrier is not None:
            ct = 0 if carrier < 6 else 1
            before = next((q for q in range(s, -1, -1) if t[s] - t[q] > 1000), 0)  # the check that started it
            ev["check_tried"] = any(anim(q, defender) in checking for q in range(before, e + 1))
            ev["carrier_person"] = bool(m["ctrl"][s] >> carrier & 1)
            ev["defender_person"] = bool(m["ctrl"][s] >> defender & 1)
            horizon = next((q for q in range(e, N) if t[q] - t[e] > 5000), N - 1)
            ev["knocked"] = any(anim(q, carrier) in down for q in range(s, horizon))
            ev["kept"] = not any(own[q] >= 0 and own[q] // 6 != ct for q in range(s, horizon))
            ev["shot"] = any(sh["team"] == ct and s <= sh["f"] <= horizon for sh in m.get("shotList", []))
            ev["goal"] = any(g["team"] == ct and s <= g["f"] <= horizon for g in m.get("goals", []))
            ev["zone"] = "attacking" if abs(pos(s, carrier)[1]) > 89 and (pos(s, carrier)[1] > 0) != (
                next((pos(s, k)[1] > 0 for k in range(ct * 6, ct * 6 + 6) if m["role"][s * K + k] == "0"), True)) else "other"
        events.append(ev)
    return events, (t[-1] - t[0]) / 60000


def main():
    allev, minutes = [], Counter()
    for name, path in games():
        ev, mins = study(name, path)
        m_sys = ev[0]["system"] if ev else json.loads(load_js_object(path)).get("system", "genesis")
        minutes[m_sys] += mins
        allev += ev
    for system in ("genesis", "snes"):
        ev = [e for e in allev if e["system"] == system]
        car = [e for e in ev if e["carrier"]]
        deep = [e for e in car if e["min"] < DEEP]
        print(f"\n== {system}: {len(ev)} stretches of {NEAR}- for {MIN_MS} ms+ in {minutes[system]:.0f} min of recording "
              f"({len(ev) / max(1, minutes[system]) * 60:.1f} an hour); with the puck carrier {len(car)}, of those under {DEEP}: {len(deep)}")
        if not car:
            continue
        f = lambda key, sel: f"{sum(1 for e in sel if e.get(key))}/{len(sel)}"
        print(f"   carrier: kept the puck {f('kept', car)}, shot within 5 s {f('shot', car)}, goal {f('goal', car)}, knocked down {f('knocked', car)}")
        print(f"   the defender tried a check meanwhile {f('check_tried', car)}; carrier a person {f('carrier_person', car)}; defender a person {f('defender_person', car)}")
        tried = [e for e in car if e["check_tried"]]
        print(f"   when the defender tried a check: knocked down {f('knocked', tried)}, carrier's team shot {f('shot', tried)}, goal {f('goal', tried)}")
        long_ = sorted(car, key=lambda e: -e["ms"])[:8]
        for e in long_:
            print(f"   {e['game']} f{e['f']}: {e['ms'] / 1000:.1f} s, closest {e['min']:.1f}, {e['zone']}, check tried {e['check_tried']}, "
                  f"kept {e['kept']}, shot {e['shot']}, goal {e['goal']}, carrier {'person' if e['carrier_person'] else 'cpu'}, defender {'person' if e['defender_person'] else 'cpu'}")


if __name__ == "__main__":
    main()
