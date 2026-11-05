"""How much the SNES lane's rate moves with who is on the ice (2026-11-04; SNES_SHOOTING 4.8). The game doesn't move the puck every frame, and the lane puck passes at the edge of the
goalie's body box, so the frames it stands still on can decide goal or save. The map parks every skater; a real game has ten on the ice. Three spots (the two lane spots and the mirror spot),
a full slapshot, the same 120 moments as the map, four conditions:
- parked: every skater parked, the shooter too once the shot is away (the map);
- kept: the same with the shooter left where he shot;
- held: the other skaters where they really stood at a person's slapshot in a recorded SNES game (read only; turned to this net, and moved aside if within CLEAR of the shot's path or the
  shooter so none can touch the puck), held still until the shot is decided;
- live: the same, but let go at the release, so the game's computer plays them. A skater may now really get in the way.
Each shot also records the frames the puck stood still on in its first STILL_WINDOW frames, the direct measure of the timing.
python snes_lane_timing.py RUN [minutes]   -> paths.RUNS / RUN / lane_timing.jsonl   (gentle, resumable: a finished job is skipped)
python snes_lane_timing.py RUN report"""
import json
import math
import os
import random
import sys
import time
import zlib
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

from lowload import WORKERS, breathe, gentle
from paths import RUNS, SNES_STATE_BOTTOM, SNES_STATE_TOP
import snes_harness as H

SPOTS = (("lane_top", "top", -10, 180, 6), ("lane_bottom", "bottom", 10, 150, 2), ("mirror_top", "top", 10, 180, 2))
MOMENTS, SEEDS, LAYOUTS, K = 120, 4, 24, 12
SLAP_HOLD = 40
MIN_PUCK = 24
CLEAR = 30
GOAL_Y = 238
RINK_X = 110
STILL_WINDOW = 40
POSITION = 0x0F43                 # the object's position (0 = goalie)
_h = {}


class Ice(H.Harness):
    """The harness with the other skaters placed from a layout (object -> x, y), or parked as the map does."""
    mode, layout, released = "parked", None, False

    def park(self, keep_shooter=True):
        if self.mode == "parked":
            return super().park(keep_shooter)
        if self.mode == "kept":
            return super().park(True)
        if self.released and self.mode == "live":
            return None
        for k, (x, y) in self.layout.items():
            self.put(k, x, y)
        return None

    def play(self):
        """As decide(), and counts the frames the puck stood still on. The goal test and the rest are decide()'s."""
        e, sign, s0 = self.e, 1 if self.top else -1, self.e.w(H.SCORE_HOME)
        away = held = still = seen = 0
        self.released = True
        last = (self.e.w(H.XPOS + H.o(H.PUCK)), self.e.w(H.XFRAC + H.o(H.PUCK)), self.e.w(H.YPOS + H.o(H.PUCK)), self.e.w(H.YFRAC + H.o(H.PUCK)))
        result = 0
        for f in range(150):
            self.park(keep_shooter=False)
            e.run(1)
            now = (e.w(H.XPOS + H.o(H.PUCK)), e.w(H.XFRAC + H.o(H.PUCK)), e.w(H.YPOS + H.o(H.PUCK)), e.w(H.YFRAC + H.o(H.PUCK)))
            if seen < STILL_WINDOW:
                seen += 1
                still += now == last
            last = now
            if e.w(H.SCORE_HOME) != s0:
                result = 1
                break
            held = held + 1 if e.w(H.PUCKC) == H.o(H.GOALIE) else 0
            vy = self.sw(H.YVEL + H.o(H.PUCK)) * sign
            away = away + 1 if vy < 0 else 0
            if held >= 20 or away >= 4 or self.sw(H.YPOS + H.o(H.PUCK)) * sign > 280:
                break
        self.released = False
        return result, still, seen


def seg_distance(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - x0 - t * dx, py - y0 - t * dy)


def clear_of_shot(x, y, sx, sy, sg):
    """Move a skater sideways until he's CLEAR of the shot's path and of the shooter."""
    goal = (0, sg * GOAL_Y)
    side = 1 if x >= (sx + goal[0]) / 2 else -1
    while seg_distance(x, y, sx, sy, *goal) < CLEAR and abs(x) < RINK_X:
        x += side * 4
    if seg_distance(x, y, sx, sy, *goal) < CLEAR:          # at the boards: the other way
        side = -side
        while seg_distance(x, y, sx, sy, *goal) < CLEAR:
            x += side * 4
    return x, y


def real_layouts():
    """Skaters' places at people's slapshots in the recorded SNES games, shooter's end as +y. Only positions leave the match files."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    home = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
    out = []
    for path in sorted((home / "matches").glob("*.js")):
        if path.name == "season.js":
            continue
        text = path.read_text(encoding="utf-8")
        if '"system": "snes"' not in text and '"system":"snes"' not in text:
            continue
        m = json.loads(text[text.find("{"):text.rfind("}") + 1])
        pos, role = m["pos"], m["role"]
        for s in m.get("shotList") or []:
            if s.get("type") != "slapshot" or not s.get("human") or not 100 <= abs(s["y"]) <= 200 or abs(s["x"]) > 60:
                continue
            f = s["f"]
            if (f + 1) * K * 2 > len(pos):
                continue
            at = [(pos[(f * K + k) * 2], pos[(f * K + k) * 2 + 1]) for k in range(K)]
            shooter = min(range(K), key=lambda k: math.hypot(at[k][0] - s["x"], at[k][1] - s["y"]))
            if math.hypot(at[shooter][0] - s["x"], at[shooter][1] - s["y"]) > 30:       # the list's spot and frame are a moment apart
                continue
            group = range(0, 6) if shooter < 6 else range(6, 12)
            sign = 1 if s["y"] > 0 else -1
            goalies = [k for k in range(K) if role[f * K + k] == "0"]                  # "x" is a goalie pulled
            if len(goalies) != 2:
                continue
            mine = next((k for k in goalies if k in group), None)
            theirs = next((k for k in goalies if k not in group), None)
            if mine is None or theirs is None or at[theirs][1] * sign < 150:     # his goalie must be at the net he's shooting at
                continue
            turned = [(sign * x, sign * y) for x, y in at]
            out.append(dict(game=path.stem, f=f,
                            goalie=turned[mine],
                            mates=[turned[k] for k in group if k not in (shooter, mine)],
                            others=[turned[k] for k in range(K) if k not in group and k != theirs]))
    random.Random(94).shuffle(out)
    picked, games = [], defaultdict(int)
    for most in (1, 2, 3, 99):                              # as many different games as there are
        for s in out:
            if len(picked) < LAYOUTS and games[s["game"]] < most and s not in picked:
                picked.append(s)
                games[s["game"]] += 1
    return picked


def init():
    gentle()
    e = None
    for net, st, top in (("top", SNES_STATE_TOP, True), ("bottom", SNES_STATE_BOTTOM, False)):
        h = Ice(state=st, top=top, emu=e)
        e = h.e
        e.unserialize(h.base)
        e.setw(H.SHOTSPD + H.o(H.SHOOTER), 13)
        e.setw(H.SHOTACC + H.o(H.SHOOTER), 13)
        h.base = e.serialize()
        h.goalie = next(k for k in range(6) if e.w(POSITION + H.o(k)) == 0)
        _h[net] = h


def place(h, lay, x, y, sg):
    """A real layout at this spot, for this net: object -> x, y."""
    place_at = {}
    mates = [k for k in range(6) if k not in (H.SHOOTER, h.goalie)]
    others = [k for k in range(6, 12) if k != H.GOALIE]
    place_at[h.goalie] = (sg * lay["goalie"][0], sg * lay["goalie"][1])
    for k, (a, b) in list(zip(mates, lay["mates"])) + list(zip(others, lay["others"])):
        place_at[k] = clear_of_shot(sg * a, sg * b, x, sg * y, sg)
    return place_at


def job(args):
    name, net, x, y, aim, mode, layout, part, lay = args
    h = _h[net]
    sg = 1 if net == "top" else -1
    h.mode = mode
    h.released = False
    h.layout = place(h, lay, x, y, sg) if lay else None
    rnd = random.Random(zlib.crc32(f"{name},{part}".encode()))       # the same moments in every condition
    goals = shots = still = seen = 0
    per = []
    for p in range(MOMENTS):
        h.setup(x, sg * y, settle=80 + (p * 7) % 15, clock=590 - p % 8, seed=rnd.getrandbits(32))
        release = rnd.getrandbits(32)
        pre, _f = h.shoot(aim, SLAP_HOLD)
        if pre is None:
            continue
        e = h.e
        e.unserialize(pre)
        g, s = H.o(H.GOALIE), H.o(H.SHOOTER)
        gx, gy = h.sw(H.XPOS + g), h.sw(H.YPOS + g)
        px, py = h.sw(H.XPOS + H.o(H.PUCK)), h.sw(H.YPOS + H.o(H.PUCK))
        sx, sy = h.sw(H.XPOS + s), h.sw(H.YPOS + s)
        if not (math.hypot(px - gx, py - gy) >= MIN_PUCK and math.hypot(sx - gx, sy - gy) >= 16 and sg * py < sg * gy):
            continue
        h.fire(pre, aim, release)
        r, st, n = h.play()
        goals += r
        shots += 1
        still += st
        seen += n
        per.append(r)
        breathe()
    return dict(spot=name, mode=mode, layout=layout, part=part, shots=shots, goals=goals, still=still, seen=seen, per=per)


def jobs(layouts):
    out = []
    for name, net, x, y, aim in SPOTS:
        for mode in ("parked", "kept"):
            out += [(name, net, x, y, aim, mode, -1, part, None) for part in range(SEEDS)]
        for i, lay in enumerate(layouts):
            out += [(name, net, x, y, aim, mode, i, 0, lay) for mode in ("held", "live")]
    # the controls first, then every spot a layout at a time, so a stopped run is still balanced
    return sorted(out, key=lambda j: (j[6], j[7], j[5], j[0]))


def report(path):
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    for name, *_ in SPOTS:
        print(f"\n{name}")
        for mode in ("parked", "kept", "held", "live"):
            mine = [r for r in rows if r["spot"] == name and r["mode"] == mode]
            if not mine:
                continue
            n, g = sum(r["shots"] for r in mine), sum(r["goals"] for r in mine)
            still = sum(r["still"] for r in mine) / max(1, sum(r["seen"] for r in mine))
            p = g / max(1, n)
            if mode in ("held", "live") and len(mine) > 1:
                rates = sorted(r["goals"] / max(1, r["shots"]) for r in mine)
                mean = sum(rates) / len(rates)
                se = (sum((v - mean) ** 2 for v in rates) / (len(rates) - 1) / len(rates)) ** 0.5
                print(f"  {mode:7} {n:5} shots {100 * p:5.1f}% +-{100 * se:.1f} over {len(mine)} line-ups, from {100 * rates[0]:.1f}% to {100 * rates[-1]:.1f}%; puck still {100 * still:.1f}% of frames")
            else:
                print(f"  {mode:7} {n:5} shots {100 * p:5.1f}%; puck still {100 * still:.1f}% of frames")


def main():
    run = sys.argv[1]
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    path = out / "lane_timing.jsonl"
    if len(sys.argv) > 2 and sys.argv[2] == "report":
        return report(path)
    minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    lay_file = out / "layouts.json"
    if not lay_file.exists():
        lay_file.write_text(json.dumps(real_layouts()), encoding="utf-8")
    layouts = json.loads(lay_file.read_text(encoding="utf-8"))
    print(len(layouts), "line-ups from", len({v["game"] for v in layouts}), "games", flush=True)
    done = set()
    if path.exists():
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            done.add((r["spot"], r["mode"], r["layout"], r["part"]))
    todo = [j for j in jobs(layouts) if (j[0], j[5], j[6], j[7]) not in done]
    t0 = time.time()
    gentle()
    print(len(todo), "jobs to do", flush=True)
    with Pool(WORKERS, initializer=init) as pool, open(path, "a", encoding="utf-8") as fh:
        running = []
        queue = list(todo)
        while queue or running:
            while queue and len(running) < WORKERS and (time.time() - t0) / 60 < minutes:
                running.append(pool.apply_async(job, (queue.pop(0),)))
            if not running:
                break
            time.sleep(1)
            for r in [r for r in running if r.ready()]:
                running.remove(r)
                row = r.get()
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                print(f"{(time.time() - t0) / 60:.1f} min: {row['spot']} {row['mode']} line-up {row['layout']}: {row['goals']} of {row['shots']}, still {row['still']}/{row['seen']}", flush=True)
    print("left to do:", len(queue))


if __name__ == "__main__":
    main()
