"""How a person's (or the bot's) controlled skater knocks players down, Genesis (2026-11-12, for the scripted bot's
checking: coaches rated 80%+ knock down 17.3 a game with the skater they control, the bot 12.4; ramming without C,
version 52, added none). For every knockdown by the controlled skater (match `hits`, human, "knocked down") of a side
with a pad (`pad` / `padTeam`; the bot's games keep its pad as Home's): the last C press before it (pad bit 32) within
1.5 s (real), the time from it to the knockdown, the distance between the two at the press, and the checker's speed and
the closing speed (the rate the gap shrinks) at the press and at the knockdown (positions over 4 samples, per frame of
1/60 s); the same for C presses near an opponent (within 60) that knocked nobody down within 1 s.

python analysis/knockdown_approach.py BOT_MATCHES"""
import json
import math
import os
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from recorded_coaches import ratings  # noqa: E402

PEOPLE = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents" / "NHL94 Viewer")) / "matches"
C = 32
DIG = "0123456789abcdefghijklmnopqrstuvwxyz"


def load(f):
    t = f.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def side(m, team):
    pad = m.get("pad") if m.get("padTeam", -1) == team else m.get("pad2") if m.get("pad2Team", -1) == team else None
    if not pad:
        return None
    N, t, pos, ros, ctrl = len(m["t"]), m["t"], m["pos"], m["roster"], m.get("ctrl")
    xy = lambda f, k: (pos[(f * 12 + k) * 2], pos[(f * 12 + k) * 2 + 1])

    def vel(f, k):
        a = max(0, f - 4)
        dt = max(1, (t[f] - t[a]) / (1000 / 60))
        (x0, y0), (x1, y1) = xy(a, k), xy(f, k)
        return (x1 - x0) / dt, (y1 - y0) / dt

    def closing(f, k, v):
        (x, y), (ox, oy) = xy(f, k), xy(f, v)
        (vx, vy), (wx, wy) = vel(f, k), vel(f, v)
        d = math.hypot(ox - x, oy - y) or 1
        return ((ox - x) * (vx - wx) + (oy - y) * (vy - wy)) / d, d, math.hypot(vx, vy)

    def obj(f, team_, roster_idx):
        for k in range(team_ * 6, team_ * 6 + 6):
            if ros[f * 12 + k] in DIG and DIG.index(ros[f * 12 + k]) == roster_idx:
                return k
        return None

    presses = [q for q in range(1, N) if pad[q] & C and not pad[q - 1] & C]
    rows, used = [], set()
    for h in m.get("hits", []):
        if h["team"] != team or not h.get("human") or h.get("outcome") != "knocked down":
            continue
        f = h["f"]
        k, v = obj(f, team, h["by"]), obj(f, 1 - team, h["on"])
        if k is None or v is None:
            continue
        before = [q for q in presses if q <= f and t[f] - t[q] <= 1500]
        r = {"how": h.get("how"), "carrier": bool(h.get("onCarrier"))}
        cl, d, sp = closing(max(0, f - 2), k, v)
        r.update(close_at_hit=cl, speed_at_hit=sp)
        if before:
            q = before[-1]
            used.add(q)
            cl, d, sp = closing(q, k, v)
            r.update(ms=t[f] - t[q], dist_at_press=d, close_at_press=cl, speed_at_press=sp)
        rows.append(r)
    # C presses near an opponent that knocked nobody down
    miss = []
    kd = sorted(h["f"] for h in m.get("hits", []) if h["team"] == team)
    for q in presses:
        if q in used or any(q <= f and t[f] - t[q] <= 1000 for f in kd):
            continue
        me = next((k for k in range(team * 6, team * 6 + 6) if ctrl and ctrl[q] >> k & 1), None)
        if me is None:
            continue
        opp = [(closing(q, me, v), v) for v in range((1 - team) * 6, (1 - team) * 6 + 6) if m["role"][q * 12 + v] in "12345"]
        if not opp:
            continue
        (cl, d, sp), v = min(opp, key=lambda o: o[0][1])
        if d < 60:
            miss.append({"dist_at_press": d, "close_at_press": cl, "speed_at_press": sp})
    return rows, miss


def report(name, rows, miss, games):
    print(f"\n{name}: {games} side-games, {len(rows) / games:.1f} controlled knockdowns a game; C presses near an "
          f"opponent that knocked nobody down {len(miss) / games:.1f} a game")
    pressed = [r for r in rows if "ms" in r]
    print(f"  with a C press in the 1.5 s before: {100 * len(pressed) / max(1, len(rows)):.0f}%")
    med = lambda xs: f"{st.median(xs):.1f}" if xs else "-"
    q = lambda xs: f"{med(xs)} ({sorted(xs)[len(xs) // 4]:.1f}-{sorted(xs)[3 * len(xs) // 4]:.1f})" if xs else "-"
    print(f"  press to knockdown (ms): {q([r['ms'] for r in pressed])}")
    print(f"  distance at the press: {q([r['dist_at_press'] for r in pressed])}; missed presses {q([r['dist_at_press'] for r in miss])}")
    print(f"  closing speed at the press: {q([r['close_at_press'] for r in pressed])}; missed {q([r['close_at_press'] for r in miss])}")
    print(f"  own speed at the press: {q([r['speed_at_press'] for r in pressed])}; missed {q([r['speed_at_press'] for r in miss])}")
    print(f"  at the knockdown: closing {q([r['close_at_hit'] for r in rows])}, own speed {q([r['speed_at_hit'] for r in rows])}")
    nop = [r for r in rows if "ms" not in r]
    if nop:
        print(f"  without a press: {len(nop) / games:.1f} a game, closing {q([r['close_at_hit'] for r in nop])}, "
              f"own speed {q([r['speed_at_hit'] for r in nop])}, kinds {dict((k, sum(r['how'] == k for r in nop)) for k in set(r['how'] for r in nop))}")


def main():
    rate = ratings("genesis")
    strong, rest = ([], [], 0), ([], [], 0)
    acc = {"strong": [[], [], 0], "rest": [[], [], 0]}
    for f in sorted(PEOPLE.glob("*.summary.json")):
        d = json.loads(f.read_text())
        if d.get("system") != "genesis" or (d.get("seconds") or 0) < 600 or not all(d.get("humans") or [False]):
            continue
        stem = f.name.replace(".summary.json", "")
        rs = rate.get(stem, [None, None])
        m = load(f.with_name(stem + ".js"))
        for team in (0, 1):
            if rs[team] is None:
                continue
            got = side(m, team)
            if got is None:
                continue
            a = acc["strong" if rs[team] >= 80 else "rest"]
            a[0] += got[0]
            a[1] += got[1]
            a[2] += 1
    for k, lab in (("strong", "People rated 80%+"), ("rest", "People rated under 80%")):
        if acc[k][2]:
            report(lab, *acc[k])
    for folder in sys.argv[1:]:
        rows, miss, n = [], [], 0
        for f in sorted(Path(folder).glob("bot_*.js")):
            m = load(f)
            m.setdefault("padTeam", 0)
            got = side(m, 0)
            if got:
                rows += got[0]
                miss += got[1]
                n += 1
        if n:
            report(f"The bot ({Path(folder).parent.name})", rows, miss, n)


if __name__ == "__main__":
    main()
