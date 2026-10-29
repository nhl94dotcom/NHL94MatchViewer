"""The xG models against the game itself, every kind of shot the studies play (2026-10-29, the user: update the xG
models with the scoring findings). One-timers were checked before (ot_xg_check.py, ot_xg_check_snes.py); this does the
rest, both systems: standing wrist shots and slapshots from anywhere in the zone, shots on the move (mv_run), dekes
and floaters (deke_run, snes_deke_run), EA Specials' first shots and follow-ups (ea_run, snes_ea_run), and the SNES
walk-in (snes_ea_run with NHL94_EA_WALKIN).

A watcher wraps the emulator's run and unserialize, so the study modules' own job functions play as they always do:
every frame it looks for a shot leaving the stick (Genesis: the test ROM's doshot counter going up while a home
skater has the puck; SNES: the puck coming loose from a home skater, moving at 2,000 or more toward the goal the
goalie guards, heading for his goal line within 100 of the middle) and reads what the converter would
record for it: the puck's spot (and height), its fastest speed over the next 10 frames, the stick's aim the frame
after (Genesis AIM_DIR, SNES passdir), the shooter's Shot Accuracy, the goalie's spot, velocity, working ratings and
sprite frame (pad stack included), and his lock, no-touch timer (nopuck) and no-collision flag. Then it follows the puck to the shot's own end: a goal (the score goes up before
anyone has the puck), else not (anyone has it, it is 12 beyond the goal line, it has moved away from the goal 4 frames
running (it can't go in without touching something: the harness's decide), or 150 frames pass). A rewind (unserialize)
drops a shot not yet decided. The model is asked as add_expected_goals asks it (xg.play_out / xg_snes.play_out,
SAMPLES draws): "prod" with the recordings' goalie blur, "exact" without it (the state here is exact).

python xg_calib.py genesis|snes RUN [minutes] [categories]   -> paths.RUNS / RUN / xg_calib_<system>.jsonl
One line per shot: category, job, the shot's order since the last rewind (0 the first: an EA follow-up is 1), the
inputs, goal (0/1) and the model's two values. Gentle mode, a pool per category (one emulator per process)."""
import itertools
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

from lowload import WORKERS, breathe, gentle
from paths import RUNS

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

SYSTEM = sys.argv[1] if len(sys.argv) > 1 else "genesis"
SAMPLES = 200
CATS = {"genesis": ("standing", "moving", "deke", "ea"), "snes": ("standing", "deke", "ea", "walkin")}
ENV = {"ea": {"NHL94_EA_MOMENTS": "3", "NHL94_SEA_MOMENTS": "4", "NHL94_EA_FOLLOW": "near"},
       "walkin": {"NHL94_SEA_MOMENTS": "4", "NHL94_EA_WALKIN": "1", "NHL94_EA_FOLLOW": "near"},
       "deke": {"NHL94_DEKE_MOMENTS": "4", "NHL94_SDEKE_MOMENTS": "6"}, "moving": {}, "standing": {}}
_w = {}


class Watcher:
    """Finds shots in whatever the study module plays, and scores each by the game and by the model."""

    def __init__(self, e, system, out):
        import xg
        import xg_snes
        self.e, self.system, self.out = e, system, out
        self.xg, self.xs = xg, xg_snes
        if system == "genesis":
            import harness as G
            self.G = G
            self.puckc, self.score, self.goalie, self.puck = G.PUCKC, G.SCORE_HOME, G.GOALIE, 14
        else:
            import snes_harness as S
            from paths import SNES_ROM
            self.S = S
            self.data = xg_snes.RomData(SNES_ROM.read_bytes())
            self.puckc, self.score, self.goalie, self.puck = S.PUCKC, S.SCORE_HOME, S.GOALIE, S.PUCK
        self.tag, self.pending, self.ord = None, None, 0
        self._run, self._unser = e.run, e.unserialize
        e.run, e.unserialize = self.run, self.unserialize
        self.prev = None
        self.nshots = e.w(G.E["n"]) if system == "genesis" else None

    # --- the game's state
    def sw(self, a):
        v = self.e.w(a)
        return v - 0x10000 if v & 0x8000 else v

    def carrier(self):
        c = self.e.w(self.puckc)
        if self.system == "genesis":
            return None if c >> 8 == 0xFF else c
        return None if c & 0x8000 else c // 2

    def xy(self, k):
        if self.system == "genesis":
            r = self.G.rec(k)
            return self.sw(r), self.sw(r + 0x14)
        S = self.S
        return self.sw(S.XPOS + S.o(k)), self.sw(S.YPOS + S.o(k))

    def v(self, k):
        if self.system == "genesis":
            r = self.G.rec(k)
            return self.sw(r + 0x28), self.sw(r + 0x2A)
        S = self.S
        return self.sw(S.XVEL + S.o(k)), self.sw(S.YVEL + S.o(k))

    # --- the emulator, wrapped
    def run(self, n=1, hold=()):
        for _ in range(n):
            self._run(1, hold)
            self.tick()

    def unserialize(self, raw):
        self._unser(raw)
        self.pending, self.ord = None, 0
        self.prev = self.carrier()
        if self.system == "genesis":
            self.nshots = self.e.w(self.G.E["n"])

    def tick(self):
        c = self.carrier()
        p = self.pending
        if p is not None:
            p["n"] += 1
            if p["n"] <= 10:
                p["speed"] = max(p["speed"], math.hypot(*self.v(self.puck)))
            if p["n"] == 1:
                p["aim"] = self.e.w(0xBEDC) if self.system == "genesis" else self.e.w(0x0D03) & 0xFF
            goal = self.e.w(self.score) != p["s0"]
            beyond = abs(self.xy(self.puck)[1]) > 276
            p["away"] = p["away"] + 1 if self.v(self.puck)[1] * p["gl"] < 0 else 0
            if goal or (p["n"] > 10 and (c is not None or beyond or p["n"] >= 150)) or p["away"] >= 4:
                p["goal"] = int(goal)
                self.finish(p)
                self.pending = None
        elif self.system == "genesis":
            n = self.e.w(self.G.E["n"])
            if n != self.nshots and self.prev is not None and self.prev < 6:
                self.start(self.prev)              # the test ROM counts every doshot: a shot, whatever its line
            self.nshots = n
        elif self.prev is not None and self.prev < 6 and c is None:
            self.start(self.prev)
        self.prev = c

    def start(self, shooter):
        px, py = self.xy(self.puck)
        vx, vy = self.v(self.puck)
        gx, gy = self.xy(self.goalie)
        gl = 264 if gy > 0 else -264
        if self.system == "snes":                  # no doshot counter: a puck fired at the goal line
            if math.hypot(vx, vy) < 2000 or vy * gl <= 0 or abs(py) >= 264 or abs(px + (gl - py) * vx / vy) > 100:
                return
        self.ord += 1
        st = dict(tag=self.tag, ord=self.ord - 1, px=px, py=py, gl=gl, speed=math.hypot(vx, vy),
                  s0=self.e.w(self.score), n=0, aim=None, away=0)
        e = self.e
        gvx, gvy = self.v(self.goalie)
        if self.system == "genesis":
            g, sr = self.G.rec(self.goalie), self.G.rec(shooter)
            st.update(pz=max(0, self.sw(self.G.rec(self.puck) + 0x18)), sha=e.b(sr + 0x6D),
                      goalie=[gx, gy, gvx, gvy] + [e.b(g + o) for o in (0x67, 0x68, 0x69, 0x6B, 0x6C)],
                      ganim=e.w(g + 0x58), gframe=e.w(g + 6), gfacing=e.b(g + 0x55), gmirror=not e.b(g + 0x76) & 1,
                      glock=e.b(g + 0x62) >> 5 & 1, gspanum=e.w(g + 0x5A), gspacnt=self.sw(g + 0x5C),
                      gnopuck=e.w(g + 0x5E), gnc=e.b(g + 0x62) >> 2 & 1)
        else:
            S, g = self.S, self.S.o(self.goalie)
            st.update(pz=0, sha=e.w(S.SHOTACC + S.o(shooter)),
                      goalie=[gx, gy, gvx, gvy] + [e.w(a + g) for a in (0x12C3, 0x12E3, 0x1303, 0x1343)],
                      facing=e.w(0x1163 + g) & 7, frame=e.w(0x0D97 + g), gspa=e.w(S.SPA + g),
                      glock=e.w(0x14E3 + g), gnopuck=e.w(0x1203 + g), gnc=e.w(0x1563 + g))   # pfalock, nopuck, pfnc
        self.pending = st

    # --- the model, as add_expected_goals asks it
    def model(self, p, spread):
        rng = random.Random(f"{p['tag']}:{p['px']}:{p['py']}:{p['ord']}:{spread}")
        if self.system == "genesis":
            xg = self.xg
            xg.GOALIE_SPREAD = spread
            gx, gy, gvx, gvy, w, agl, spd, aid, pkc = p["goalie"]
            reach, shift = xg.REACH[min(19, (agl + 2) >> 1)], 0
            anim = "%04x" % p["ganim"]
            if anim in xg.PAD_STACK:
                reach, shift = 18, xg.PAD_STACK[anim]
            d = p["aim"] if p["aim"] is not None and 0 <= p["aim"] <= 8 else 8
            tx, tz = xg.AIM[d]
            pp = max(1.0, p["speed"] / 68)
            G = xg.Goalie(gx, gy, gvx, gvy, w, agl, spd, aid, rom=None, frame=None, facing=4, mirror=False,
                          puck_control=pkc)
            goals = sum(xg.play_out((p["px"], p["py"], p["pz"]), (tx, p["gl"], tz), pp, p["sha"],
                                    (p["sha"] + 1) / (p["sha"] + 16), G, reach, shift, rng) == "goal"
                        for _ in range(SAMPLES))
            xg.GOALIE_SPREAD = 4.0
        else:
            xs = self.xs
            xs.GOALIE_SPREAD = spread
            gx, gy, gvx, gvy, w, agl, spd, aid = p["goalie"]
            d = p["aim"] if p["aim"] is not None and 0 <= p["aim"] <= 8 else 8
            tx, tz = xs.AIM[d]
            G = xs.Goalie(self.data, gx, gy, gvx, gvy, p["facing"], p["frame"], w, agl, spd, aid)
            goals = sum(xs.play_out(p["px"], p["py"], tx, p["gl"], tz, max(1.0, p["speed"] / 136), p["sha"],
                                    (p["sha"] + 1) / (p["sha"] + 16), G, rng) == "goal" for _ in range(SAMPLES))
            xs.GOALIE_SPREAD = 2.0
        return goals / SAMPLES

    def finish(self, p):
        p["prod"] = self.model(p, 4.0 if self.system == "genesis" else 2.0)
        p["exact"] = self.model(p, 0.0)
        p.pop("s0")
        p.pop("away")
        self.out.append(p)


# --- the categories: each a module with its own harness, and a sample of its jobs
def standing_init(system):
    if system == "genesis":
        from harness import Harness
        from paths import STATE_TOP, STATE_BOTTOM
        top = Harness(state=STATE_TOP, top=True)
        return {"top": top, "bottom": Harness(state=STATE_BOTTOM, top=False, emu=top.e)}
    import snes_harness as S
    from paths import SNES_STATE_TOP, SNES_STATE_BOTTOM
    top = S.Harness(state=SNES_STATE_TOP, top=True)
    return {"top": top, "bottom": S.Harness(state=SNES_STATE_BOTTOM, top=False, emu=top.e)}


def standing_jobs(system, rnd, n):
    """(net, x, y out from centre, wind-up, aim, Shot Power, Shot Accuracy, moment seed)."""
    hold = (3, 20) if system == "genesis" else (3, 40)
    rat = ((10, 15, 20, 25), (5, 10, 15, 20, 25)) if system == "genesis" else ((5, 8, 11, 14), (3, 6, 9, 12, 15))
    return [(rnd.choice(("top", "bottom")), rnd.randrange(-110, 111, 10), rnd.randrange(100, 251, 10),
             rnd.choice(hold), rnd.randrange(9), rnd.choice(rat[0]), rnd.choice(rat[1]), rnd.getrandbits(32))
            for _ in range(n)]


def standing_job(system, hs, args):
    net, x, y, hold, aim, shp, sha, seed = args
    h = hs[net]
    sg = 1 if net == "top" else -1
    rnd = random.Random(seed)
    if system == "genesis":
        from mapper import set_ratings
        h.setup(x, sg * y, settle=rnd.randrange(80, 95), clock=590 - rnd.randrange(8))
        set_ratings(h, shp, sha)
        h.e.setl(0xD066, rnd.getrandbits(32))
        pre, _ = h.shoot(aim, hold)
        if pre is not None:
            from harness import decide
            decide(h)
    else:
        import snes_harness as S
        h.setup(x, sg * y, settle=rnd.randrange(80, 95), clock=590 - rnd.randrange(8), seed=rnd.getrandbits(32))
        h.e.setw(S.SHOTSPD + S.o(S.SHOOTER), shp)
        h.e.setw(S.SHOTACC + S.o(S.SHOOTER), sha)
        pre, _ = h.shoot(aim, hold)
        if pre is not None:
            h.decide()


MODULES = {("genesis", "moving"): "mv_run", ("genesis", "deke"): "deke_run", ("genesis", "ea"): "ea_run",
           ("snes", "deke"): "snes_deke_run", ("snes", "ea"): "snes_ea_run", ("snes", "walkin"): "snes_ea_run"}
PLANS = {("genesis", "moving"): ("cross", "diag", "slapx"), ("genesis", "deke"): ("best", "retime"),
         ("genesis", "ea"): ("fine", "wide"), ("snes", "deke"): ("near",), ("snes", "ea"): ("fine", "explore"),
         ("snes", "walkin"): ("walkin",)}


def _init(system, cat, out_path):
    gentle()
    for k, v in ENV[cat].items():
        os.environ[k] = v
    _w["system"], _w["cat"], _w["out"] = system, cat, out_path
    if cat == "standing":
        _w["hs"] = standing_init(system)
        e = _w["hs"]["top"].e
    else:
        mod = __import__(MODULES[(system, cat)])
        _w["mod"] = mod
        mod._init()
        e = next(iter(mod._h.values())).e
    _w["watch"] = Watcher(e, system, [])


def work(args):
    w = _w["watch"]
    w.out.clear()
    w.tag = json.dumps(args)
    if _w["cat"] == "standing":
        standing_job(_w["system"], _w["hs"], args)
    else:
        try:
            _w["mod"].job(tuple(args))
        except Exception as ex:                     # a job the module refuses (a plan's corner): skip it
            return [dict(error=repr(ex), tag=w.tag)]
    breathe()
    return [dict(p, cat=_w["cat"]) for p in w.out]


def jobs_for(system, cat, rnd):
    if cat == "standing":
        return standing_jobs(system, rnd, 1200)
    mod = __import__(MODULES[(system, cat)])
    js = []
    for plan in PLANS[(system, cat)]:
        try:
            js += [list(j) for j in mod.plan_jobs(plan)]
        except SystemExit:
            pass
    rnd.shuffle(js)
    return js[:{"moving": 60, "deke": 40, "ea": 60, "walkin": 40}[cat]]


def main():
    run = sys.argv[2]
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    cats = sys.argv[4].split(",") if len(sys.argv) > 4 else CATS[SYSTEM]
    path = RUNS / run / f"xg_calib_{SYSTEM}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        for line in open(path):
            r = json.loads(line)
            done.add((r.get("cat"), r["tag"]))
    deadline = time.time() + 60 * minutes
    for cat in cats:
        rnd = random.Random(zlib.crc32(f"{SYSTEM},{cat}".encode()))
        todo = [j for j in jobs_for(SYSTEM, cat, rnd) if (cat, json.dumps(j)) not in done]
        print(f"{SYSTEM} {cat}: {len(todo)} jobs to go", flush=True)
        if time.time() > deadline:
            break
        with Pool(WORKERS, initializer=_init, initargs=(SYSTEM, cat, str(path))) as pool, open(path, "a") as f:
            pending, queue, n = [], list(todo), 0
            while queue or pending:
                while queue and len(pending) < WORKERS and time.time() < deadline:
                    a = queue.pop(0)
                    pending.append((a, pool.apply_async(work, (a,))))
                if not pending:
                    break
                time.sleep(1)
                for item in [x for x in pending if x[1].ready()]:
                    pending.remove(item)
                    a, r = item
                    rows = r.get()
                    if not rows:                    # no shot in the job: mark it done
                        rows = [dict(cat=cat, tag=json.dumps(a), none=True)]
                    for row in rows:
                        row.setdefault("cat", cat)
                        row["tag"] = json.dumps(a)
                        f.write(json.dumps(row) + "\n")
                    f.flush()
                    n += 1
            print(f"  {cat}: {n} jobs this chunk", flush=True)


if __name__ == "__main__":
    main()
