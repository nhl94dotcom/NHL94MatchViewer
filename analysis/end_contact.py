"""Contact by end in the recorded games, both systems (2026-11-19; NOSE4Web: in the league database teams attacking
the Down net draw 5.4% more penalties a period on the Genesis, every type about 1.05, tripping and interference about
1.10; the SNES 1.000).

Each regulation period of each recorded game (the bot's left out), each team as attacker of the net it shoots at in
that period (home attacks up in periods 1 and 3, down in period 2). Per attacking team, with the clock running:
- possession: samples it has the puck, of samples anyone has it;
- offensive zone time: samples the puck is past the blue line (|y| > 88) at the net it attacks;
- what it drew from the team defending that net: hits on it (the converter's hits; `team` is the hitter's), knockdowns
  among them (knocked down, upended, into the boards or the bench), hooks and holds that caught one of its skaters
  (a skater going into the flail animation: Genesis $0CF4, SNES $F46A), and penalties called on the defenders;
  each also split by where it happened (the attacker's offensive zone, the neutral zone, its own zone).
Down / Up = the Down attackers' total over the Up attackers' (the same periods and games, so per period).

python analysis/end_contact.py"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import season  # noqa: E402

HOME = Path.home() / "Documents" / "NHL94 Viewer" / "matches"
K = 12
FLAIL = {"genesis": "0cf4", "snes": "f46a"}
DOWN = ("knocked down", "upended", "into the boards", "into the bench")


def zone(y, sg):
    v = y * sg
    return "offensive" if v > 88 else ("own" if v < -88 else "neutral")


def main():
    tot = {s: defaultdict(Counter) for s in ("genesis", "snes")}
    games = Counter()
    for p in sorted(HOME.glob("*.js")):
        if p.name == "season.js":
            continue
        try:
            m = season.load_match(p)
        except Exception:
            continue
        if "bot" in str(m.get("name", "")):
            continue
        sysname = m.get("system") or "genesis"
        games[sysname] += 1
        T = tot[sysname]
        N, P, own, per, clk = len(m["t"]), m["puck"], m["owner"], m["period"], m["clock"]
        end_of = lambda team, q: "Up" if (team == 0) == (per[q] % 2 == 0) else "Down"  # noqa: E731
        sg_of = lambda team, q: 1 if end_of(team, q) == "Up" else -1  # noqa: E731
        running = [i > 0 and per[i] <= 2 and clk[i] != clk[max(0, i - 24)] for i in range(N)]
        for i in range(N):
            if not running[i]:
                continue
            for team in (0, 1):
                e = end_of(team, i)
                T[e]["samples"] += 1
                if own[i] >= 0:
                    T[e]["owned samples"] += 1
                    T[e]["possession"] += (own[i] < 6) == (team == 0)
                T[e]["offensive zone time"] += P[3 * i + 1] * sg_of(team, i) > 88
        for h in m.get("hits", []):
            f = h["f"]
            if per[f] > 2:
                continue
            victim = 1 - h["team"]
            e = end_of(victim, f)
            z = zone(h.get("y", 0), sg_of(victim, f))
            T[e]["hits drawn"] += 1
            T[e][f"hits drawn, {z} zone"] += 1
            if h.get("outcome") in DOWN:
                T[e]["knockdowns drawn"] += 1
        flail = FLAIL[sysname]
        A = m["anim"]
        for k in range(12):
            if k in (5, 11):
                continue
            was = False
            for i in range(N):
                now = A[(i * K + k) * 4:(i * K + k) * 4 + 4] == flail
                if now and not was and per[i] <= 2:
                    team = 0 if k < 6 else 1
                    e = end_of(team, i)
                    y = m["pos"][(i * K + k) * 2 + 1]
                    T[e]["hooks / holds drawn"] += 1
                    T[e][f"hooks / holds drawn, {zone(y, sg_of(team, i))} zone"] += 1
                was = now
        for pen in m.get("penalties", []):
            f = pen["f"]
            if per[f] > 2:
                continue
            drawer = 1 - pen["team"]
            T[end_of(drawer, f)]["penalties drawn"] += 1
    for s in ("genesis", "snes"):
        T = tot[s]
        print(f"== {s}: {games[s]} games (each team attacking each end once a period)")
        rows = ["samples", "possession", "offensive zone time", "hits drawn", "knockdowns drawn", "hooks / holds drawn",
                "penalties drawn"] + sorted(k for k in set(T["Up"]) | set(T["Down"]) if ", " in k)
        for r in rows:
            up, dn = T["Up"][r], T["Down"][r]
            extra = ""
            if r == "possession":
                extra = f"   share Up {up / max(T['Up']['owned samples'], 1):.1%}, Down {dn / max(T['Down']['owned samples'], 1):.1%}"
            elif r == "offensive zone time":
                extra = f"   share Up {up / max(T['Up']['samples'], 1):.1%}, Down {dn / max(T['Down']['samples'], 1):.1%}"
            print(f"  {r:40s} Up {up:8d}  Down {dn:8d}  Down/Up {dn / max(up, 1):.3f}{extra}")


if __name__ == "__main__":
    main()
