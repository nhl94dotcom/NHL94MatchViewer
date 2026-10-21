"""Skaters stuck on a net (2026-10-21, the user: on the SNES a skater who skates diagonally into the front or back of the
net stays there, and every speed burst he makes can knock the net off; not on the Genesis). Every recorded game, both
systems, each once: stretches of live play where a skater stays inside the net's collision oval (both games test about
32 across and 11 up / down the ice from the net's middle: checkgoalp) for at least MIN_MS, with how long, how much he
moved, how many speed bursts he made there, whether the net came off, and whether a person controlled him.
python analysis/net_stuck_study.py"""
import json
import math
import sys
from collections import Counter

sys.path.insert(0, "tools")
sys.path.insert(0, "analysis")
import systems  # noqa: E402
from share_game import load_js_object  # noqa: E402
from tangle_study import games  # noqa: E402

K = 12
MIN_MS = 1000
RX, RY = 32, 11


def main():
    out, minutes = [], Counter()
    for name, path in games():
        m = json.loads(load_js_object(path))
        system = m.get("system", "genesis")
        burst = systems.of_match(m).ACTIONS.get("lunge", set())
        t, N, P = m["t"], len(m["t"]), m["puck"]
        minutes[system] += (t[-1] - t[0]) / 60000
        nets = m.get("nets") or []
        net_at = lambda i: next(((r[1], r[2], r[3], r[4]) for r in reversed(nets) if r[0] <= i), (0, 268, 0, -268))
        for k in range(K):
            i = 0
            while i < N:
                if m["role"][i * K + k] not in "12345" or P[3 * i + 2] < -100:
                    i += 1
                    continue
                x, y = m["pos"][(i * K + k) * 2], m["pos"][(i * K + k) * 2 + 1]
                n = net_at(i)
                which = next((j for j in (0, 1) if abs(x - n[2 * j]) < RX and abs(y - n[2 * j + 1]) < RY
                              and ((x - n[2 * j]) / RX) ** 2 + ((y - n[2 * j + 1]) / RY) ** 2 <= 1), None)
                if which is None:
                    i += 1
                    continue
                s = i
                while i < N and P[3 * i + 2] > -100 and m["role"][i * K + k] in "12345":
                    x, y = m["pos"][(i * K + k) * 2], m["pos"][(i * K + k) * 2 + 1]
                    n = net_at(i)
                    if ((x - n[2 * which]) / (RX + 4)) ** 2 + ((y - n[2 * which + 1]) / (RY + 4)) ** 2 > 1:
                        break
                    i += 1
                e = i - 1
                if t[e] - t[s] < MIN_MS:
                    continue
                bursts = sum(1 for q in range(s + 1, e + 1) if m["anim"][(q * K + k) * 4:(q * K + k) * 4 + 4] in burst
                             and m["anim"][((q - 1) * K + k) * 4:((q - 1) * K + k) * 4 + 4] not in burst)
                moved = math.hypot(m["pos"][(e * K + k) * 2] - m["pos"][(s * K + k) * 2], m["pos"][(e * K + k) * 2 + 1] - m["pos"][(s * K + k) * 2 + 1])
                off = any(s <= ev["f"] <= e + 30 for ev in m.get("netsOff", []))
                out.append({"system": system, "game": name, "f": s, "ms": t[e] - t[s], "bursts": bursts, "moved": moved, "off": off,
                            "person": bool(m["ctrl"][s] >> k & 1), "side": "front" if abs(m["pos"][(s * K + k) * 2 + 1]) < abs(net_at(s)[2 * which + 1]) else "back"})
    for system in ("genesis", "snes"):
        ev = [e for e in out if e["system"] == system]
        print(f"\n== {system}: {len(ev)} skaters held at a net for {MIN_MS / 1000:.0f} s+ in {minutes[system]:.0f} min ({60 * len(ev) / max(1, minutes[system]):.1f} an hour)")
        if not ev:
            continue
        print(f"   a person's {sum(e['person'] for e in ev)}; front {sum(e['side'] == 'front' for e in ev)}, back {sum(e['side'] == 'back' for e in ev)}; "
              f"with bursts {sum(1 for e in ev if e['bursts'])} ({sum(e['bursts'] for e in ev)} bursts); net knocked off {sum(e['off'] for e in ev)}")
        for e in sorted(ev, key=lambda e: -e["ms"])[:10]:
            print(f"   {e['game']} f{e['f']}: {e['ms'] / 1000:.1f} s, moved {e['moved']:.0f}, {e['side']}, bursts {e['bursts']}, net off {e['off']}, {'person' if e['person'] else 'cpu'}")


if __name__ == "__main__":
    main()
