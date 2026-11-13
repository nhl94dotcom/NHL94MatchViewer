"""The puck out of play in the recorded Genesis games (2026-11-13, NOSE4Web: a delay-of-game option for a puck sent out
of play from the defending zone, as today's NHL calls it).

wallcollb's out-of-play path (collide94.asm): a puck at the boards above height $1D (or above $12 off the sides and the
bottom end) sets sfslock (sflags bit 6) and the puck's pfnc, and while the clock runs adds penalty 6 (PenOOP: the
whistle) for ltplayer. The recordings keep sflags ($C2EC), gmode ($C2EA, bit 0 the clock stopped: bset / btst on
memory work on the byte at the address, the word's high byte), the puck's record
(14: X +$00, Y +$14, Z +$18, the speeds +$28 / +$2A / +$2C) and a2touchpuck's last touch: ltplayer ($BF7A, the toucher's
record), ltx / lty ($BF7C / $BF7E, where). Each exit: the first sample with sfslock set while the clock was running in
live play (screen $FFF7 0), the puck high (Z > $12) and at the boards (|X| > 112 or |Y| > 255) in the sample before.
For each: the last toucher's team and role (goalie or skater), his zone at the touch (his own defending zone, neutral,
attacking: blue lines at 64 from the middle, by the way his team attacked then), and the path since the touch (the
samples since ltplayer / ltx / lty last changed): straight out, or off the boards / glass / net first (a speed
component reversing along the way, the ice bounce left out).

python analysis/out_of_play_study.py [--snes] [CAPTURE ...]   (default: every recording of the system with a match file)"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from export_match import Capture  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
GMODE, SFLAGS, SCREEN = 0xC2EA, 0xC2EC, 0xFFF7
LTPLAYER, LTX, LTY = 0xBF7A, 0xBF7C, 0xBF7E
BASE, SZ, PUCK = 0xB04A, 0x80, 14
BLUE = 64                                   # blue lines at +-64 (GENESIS_MECHANICS: zones)
AFTER_WHISTLE = {}                          # pucks over the glass with the clock already stopped: left out


def s16(v):
    return v - 65536 if v & 0x8000 else v


def puck(c, i):
    a = BASE + SZ * PUCK
    return (s16(c.word(i, a)), s16(c.word(i, a + 0x14)), s16(c.word(i, a + 0x18)),
            s16(c.word(i, a + 0x28)), s16(c.word(i, a + 0x2A)))


def exits(c, name):
    out = []
    n = c.count
    prev_lock = True
    for i in range(1, n):
        sf, scr = c.byte(i, SFLAGS), c.byte(i, SCREEN)        # bset / btst on memory: the byte at the address
        lock = bool(sf & 0x40)
        if lock and not prev_lock and scr == 0 and c.byte(i - 1, GMODE) & 1:
            x, y, z, _, _ = puck(c, i - 1)
            if z > 0x12 and (abs(x) > 112 or abs(y) > 255):
                AFTER_WHISTLE[name] = AFTER_WHISTLE.get(name, 0) + 1
        if lock and not prev_lock and scr == 0 and not (c.byte(i - 1, GMODE) & 1):
            x, y, z, vx, vy = puck(c, i - 1)
            if z > 0x12 and (abs(x) > 112 or abs(y) > 255):
                lt = c.word(i, LTPLAYER)
                ltx, lty = s16(c.word(i, LTX)), s16(c.word(i, LTY))
                rec = BASE + SZ * lt
                team = 0 if lt < 6 else 1
                role = c.byte(i, rec + 0x35) if lt < 12 else 0xFF          # 0 goalie
                period = c.word(i, 0xC466)
                home_up = period % 2 == 0                                   # home attacks up in periods 1 and 3
                up = home_up if team == 0 else not home_up
                own = -lty if up else lty                                   # positive: toward his own net
                zone = "own" if own > BLUE else "attacking" if own < -BLUE else "neutral"
                # the path since the touch: back while ltplayer / ltx / lty stay the same
                j = i - 1
                while j > 0 and (c.word(j, LTPLAYER), c.word(j, LTX), c.word(j, LTY)) == (lt, c.word(i, LTX), c.word(i, LTY)):
                    j -= 1
                vel = [puck(c, k)[3:5] for k in range(j + 1, i)]
                bounced = any((a[0] * b[0] < 0 and abs(a[0]) > 200) or (a[1] * b[1] < 0 and abs(a[1]) > 200)
                              for a, b in zip(vel, vel[1:]))
                out.append({"capture": name, "i": i, "period": period, "clock": c.word(i, 0xC468), "team": team,
                            "goalie": role == 0, "zone": zone, "touch": [ltx, lty], "exit": [x, y, z],
                            "flight_s": round((c.ms(i) - c.ms(j + 1)) / 1000, 2), "bounced": bounced})
        prev_lock = lock
    return out


# The SNES (wallcollb.asm: over the glass at height $21+, or $16+ off the sides and the bottom end; wallcollb_out sets
# sfslock in sflags $15D8 and, with the clock running (gmclock $15D6 zero), the whistle for ltplayer): ltplayer
# $30F6 (the toucher's object number), ltx / lty $30F8 / $30FA; the puck $0D71 / $0DD3 / $0DF9, speeds $0EDF / $0EFF;
# each object's position $0F43 (0 goalie) and pfgoal $14C3 (nonzero: attacks the top).
SN = {"sflags": 0x15D8, "clockstop": 0x15D6, "lt": 0x30F6, "ltx": 0x30F8, "lty": 0x30FA, "x": 0x0D71, "y": 0x0DD3,
      "z": 0x0DF9, "vx": 0x0EDF, "vy": 0x0EFF, "pos": 0x0F43, "goal": 0x14C3, "period": 0x1630, "clock": 0x1632,
      "paused": 0x15D8}


def exits_snes(c, name):
    out = []
    w = lambda i, a: s16(c.word(i, a))
    prev_lock = True
    for i in range(1, c.count):
        sf = c.word(i, SN["sflags"])
        lock = bool(sf & 0x40)
        if lock and not prev_lock and not (sf & 0x0801) and c.word(i - 1, SN["clockstop"]) != 0:
            x, y, z = w(i - 1, SN["x"]), w(i - 1, SN["y"]), w(i - 1, SN["z"])
            if z >= 0x16 and (abs(x) > 100 or abs(y) > 250):
                AFTER_WHISTLE[name] = AFTER_WHISTLE.get(name, 0) + 1
        if lock and not prev_lock and not (sf & 0x0801) and c.word(i - 1, SN["clockstop"]) == 0:
            x, y, z = w(i - 1, SN["x"]), w(i - 1, SN["y"]), w(i - 1, SN["z"])
            if z >= 0x16 and (abs(x) > 100 or abs(y) > 250):
                lt = c.word(i, SN["lt"])
                ltx, lty = w(i, SN["ltx"]), w(i, SN["lty"])
                team = 0 if lt < 6 else 1
                goalie = lt < 12 and c.word(i, SN["pos"] + 2 * lt) == 0
                up = lt < 12 and c.word(i, SN["goal"] + 2 * lt) != 0
                own = -lty if up else lty
                zone = "own" if own > BLUE else "attacking" if own < -BLUE else "neutral"
                j = i - 1
                key = (c.word(i, SN["lt"]), c.word(i, SN["ltx"]), c.word(i, SN["lty"]))
                while j > 0 and (c.word(j, SN["lt"]), c.word(j, SN["ltx"]), c.word(j, SN["lty"])) == key:
                    j -= 1
                vel = [(w(k, SN["vx"]), w(k, SN["vy"])) for k in range(j + 1, i)]
                bounced = any((a[0] * b[0] < 0 and abs(a[0]) > 200) or (a[1] * b[1] < 0 and abs(a[1]) > 200)
                              for a, b in zip(vel, vel[1:]))
                out.append({"capture": name, "i": i, "period": c.word(i, SN["period"]), "clock": c.word(i, SN["clock"]),
                            "team": team, "goalie": goalie, "zone": zone, "touch": [ltx, lty], "exit": [x, y, z],
                            "flight_s": round((c.ms(i) - c.ms(j + 1)) / 1000, 2), "bounced": bounced})
        prev_lock = lock
    return out


def main():
    system = "snes" if "--snes" in sys.argv else "genesis"
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or sorted(
        p.name for p in (HOME / "captures").iterdir()
        if (HOME / "matches" / f"{p.name}.js").exists() and (p / "capture.json").exists()
        and json.loads((p / "capture.json").read_text()).get("system", "genesis") == system)
    rows, games = [], 0
    for name in names:
        try:
            c = Capture(HOME / "captures" / name)
        except Exception as ex:
            print(name, "unreadable:", ex)
            continue
        games += 1
        rows += exits_snes(c, name) if system == "snes" else exits(c, name)
    print(f"{games} {system} recordings: {len(rows)} pucks out of play in play ({len(rows) / max(games, 1):.2f} a game)")
    print(f"  left out: {sum(AFTER_WHISTLE.values())} over the glass after the whistle (the clock already stopped)")
    for key in ("zone", "goalie", "bounced"):
        print(f"  by {key}: " + ", ".join(f"{k} {v}" for k, v in Counter(r[key] for r in rows).most_common()))
    own = [r for r in rows if r["zone"] == "own"]
    print(f"  from the toucher's own zone: {len(own)} ({len(own) / max(games, 1):.2f} a game); straight out "
          f"{sum(not r['bounced'] for r in own)}, off something first {sum(r['bounced'] for r in own)}; by a goalie "
          f"{sum(r['goalie'] for r in own)}")
    (Path(__file__).resolve().parents[1] / "reports").mkdir(exist_ok=True)
    (Path(__file__).resolve().parents[1] / "reports" / f"out_of_play_{system}.json").write_text(json.dumps(rows, indent=1))
    for r in rows[:12]:
        print("   ", r)


if __name__ == "__main__":
    main()
