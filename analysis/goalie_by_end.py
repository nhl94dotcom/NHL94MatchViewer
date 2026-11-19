"""The goalie at the Up and the Down net in the recorded Genesis games (2026-11-19; the Down-goal question: NOSE4Web's
HotList hot spots differ between the facing-up and facing-down art, and people's goalie placement by end).

Every shot on goal (shotList kinds shot, one-timer, pass shot; result goal or save), regulation only, people's games
(not the bot's). End: Up when it was shot at the top net (home attacks up in periods 1 and 3). Net coordinates: x and
y multiplied by +1 at the top net, -1 at the bottom (the bottom net seen from the same side as the top, so both are
"the net at +264"). The goalie is the defending side's record in position 0 (role "0"; shots with none in the net, |y| < 200, are left out), read at two moments: the
release (the shot's sample) and the reach (the first sample the puck is level with him or past him in y, before the
shot is resolved). At the reach: his sprite frame, facing (0-7), drawn mirrored or not, and his stick blade (the ROM's
HotList point of that frame, ROM $A44C8, x negated when mirrored, y negated: the converter's rule), given as the blade's
offset from him in net coordinates ("out" toward the shooter's end, "side" to the right looking out from the net);
the puck's height there (low: z <= 5, the stick's reach). The shooter's screen side is the release x on the screen
(right: x > 0), not mirrored. gctl: whether a person controlled the goalie at the release ("human").

Tables: (1) goals / shots on goal by end and screen side, all and low; (2) the goalie's frame at the reach for goals and
low saves by end (the commonest frames), with the blade's median offset; (3) where the goalie stood at the release by
end, for person-controlled and computer goalies (depth from the goal line, 264 - y; side), and the goal rate by depth
and side bins.

python analysis/goalie_by_end.py"""
import statistics as st
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import season  # noqa: E402

HOME = Path.home() / "Documents" / "NHL94 Viewer" / "matches"
RETAIL = Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin"
K = 12


def hot_table():
    rom = RETAIL.read_bytes()
    return [struct.unpack_from(">bb", rom, 0xA44C8 + 2 * fr) for fr in range(846)]


def rows():
    hot = hot_table()
    games = skipped = 0
    out = []
    for p in sorted(HOME.glob("*.js")):
        if p.name == "season.js":
            continue
        try:
            m = season.load_match(p)
        except Exception:
            continue
        if (m.get("system") or "genesis") != "genesis" or "bot" in str(m.get("name", "")):
            continue
        games += 1
        P, N = m["puck"], len(m["t"])
        pos = lambda i, k: (m["pos"][(i * K + k) * 2], m["pos"][(i * K + k) * 2 + 1])
        for s in m.get("shotList", []):
            f = s["f"]
            if s.get("kind") not in ("shot", "one-timer", "pass shot") or s.get("result") not in ("goal", "save"):
                continue
            per = m["period"][f]
            if per > 2:
                continue
            up = (s["team"] == 0) == (per % 2 == 0)
            sg = 1 if up else -1
            others = range(6, 12) if s["team"] == 0 else range(6)
            g = next((k for k in others if m["role"][f * K + k] == "0"), None)
            if g is None or abs(pos(f, g)[1]) < 200:
                skipped += 1
                continue                        # no goalie in the net (pulled, or parked off the ice)
            gx, gy = pos(f, g)
            end = s.get("resolved") or s.get("known") or f + 60
            reach = None
            for q in range(f + 1, min(N, end + 1)):
                if sg * P[3 * q + 1] >= sg * pos(q, g)[1] - 2:
                    reach = q
                    break
            if reach is None:
                reach = min(N - 1, end)
            fr = int(m["frame"][(reach * K + g) * 3:(reach * K + g) * 3 + 3], 16)
            facing = int(m["facing"][reach * K + g]) if m["facing"][reach * K + g].isdigit() else -1
            mir = m["mirror"][reach * K + g] == "1"
            hx, hy = hot[fr] if 0 < fr < len(hot) else (0, 0)
            if mir:
                hx = -hx
            bx, by = hx, -hy                       # blade offset from him, screen coordinates
            out.append(dict(
                end="Up" if up else "Down", side="right" if s["x"] > 0 else "left", goal=s["result"] == "goal",
                human=s.get("gctl") == "human", depth=264 - sg * gy, gside=sg * gx,
                low=P[3 * reach + 2] <= 5, frame=fr, facing=facing, mirror=mir,
                blade_out=-sg * by, blade_side=-sg * bx, gname=p.stem))
    print(f"shots with no goalie in the net: {skipped}")
    return games, out


def rate(rs):
    g = sum(r["goal"] for r in rs)
    return f"{g:4d}/{len(rs):5d} {g / max(len(rs), 1):6.1%}"


def main():
    games, R = rows()
    print(f"{games} games, {len(R)} shots on goal in regulation\n")
    print("(1) goals / shots on goal by end and the shooter's screen side")
    for low in (None, True):
        for end in ("Up", "Down"):
            line = [f"{end:4s} {'low ' if low else 'all '}"]
            for side in ("left", "right"):
                rs = [r for r in R if r["end"] == end and r["side"] == side and (low is None or r["low"])]
                line.append(f"{side}: {rate(rs)}")
            rs = [r for r in R if r["end"] == end and (low is None or r["low"])]
            line.append(f"both: {rate(rs)}")
            print("   ".join(line))
    print("\n(2) the goalie's frame at the reach, goals and low saves (the 8 commonest frames each end)")
    for end in ("Up", "Down"):
        rs = [r for r in R if r["end"] == end and (r["goal"] or r["low"])]
        for fr, n in Counter(r["frame"] for r in rs).most_common(8):
            sub = [r for r in rs if r["frame"] == fr]
            g = sum(r["goal"] for r in sub)
            print(f"  {end:4s} frame {fr:3d}: {n:4d} (goals {g:3d}; low saves {sum(not r['goal'] for r in sub):3d})  facing "
                  f"{Counter(r['facing'] for r in sub).most_common(2)}  blade out {st.median(r['blade_out'] for r in sub):+.0f} "
                  f"side {st.median(r['blade_side'] for r in sub):+.0f}  shooters right {sum(r['side'] == 'right' for r in sub)}")
    print("\n(3) where the goalie stood at the release (net coordinates; depth from the goal line, side + to his right "
          "looking out)")
    for who in (True, False):
        for end in ("Up", "Down"):
            rs = [r for r in R if r["end"] == end and r["human"] == who]
            if not rs:
                continue
            d = [r["depth"] for r in rs]
            x = [r["gside"] for r in rs]
            print(f"  {'person' if who else 'computer':8s} {end:4s} {len(rs):5d} shots: depth median {st.median(d):5.1f} "
                  f"(quartiles {st.quantiles(d, n=4)[0]:.0f} / {st.quantiles(d, n=4)[2]:.0f}), side median {st.median(x):+5.1f} "
                  f"(quartiles {st.quantiles(x, n=4)[0]:+.0f} / {st.quantiles(x, n=4)[2]:+.0f}), goals {rate(rs)}")
    print("\n   goal rate by depth (person-controlled goalies)")
    bins = ((-99, 10), (10, 16), (16, 20), (20, 24), (24, 30), (30, 999))
    for end in ("Up", "Down"):
        line = [f"  {end:4s}"]
        for lo, hi in bins:
            rs = [r for r in R if r["end"] == end and r["human"] and lo <= r["depth"] < hi]
            line.append(f"[{lo},{hi}) {rate(rs)}")
        print("  ".join(line))
    print("\n   goal rate by side (person-controlled goalies)")
    sbins = ((-999, -12), (-12, -4), (-4, 4), (4, 12), (12, 999))
    for end in ("Up", "Down"):
        line = [f"  {end:4s}"]
        for lo, hi in sbins:
            rs = [r for r in R if r["end"] == end and r["human"] and lo <= r["gside"] < hi]
            line.append(f"[{lo},{hi}) {rate(rs)}")
        print("  ".join(line))


if __name__ == "__main__":
    main()
