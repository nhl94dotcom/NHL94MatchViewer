"""How the scoring maps' goals go in: python goal_types.py genesis|snes RUN [phases seeds] [workers]
-> paths.RUNS / RUN / goal_types_<system>.json

A fresh sample over the same spots as the maps (every valid spot, both nets, wrist shot and slapshot, all nine aims,
each equally weighted), natural shots (the game's own draws from a random seed at the release), and every goal sorted
by what happened between the stick and the net, from the puck's and the goalie's state each frame:

- held then in: the goalie had the puck and it still crossed the line (the Genesis top net's shoulder-save bobble);
- off the post / off the goalie: the puck's speed jumped near a post / near the goalie before it went in;
- Genesis: in his pad stack (SPAgstackr / l at the puck's closest pass); through the blind ring (the puck passed
  within his reach, 15, low, untouched: the butterfly's ring around his stick); clean (it never came within his reach);
- SNES: past a save move (named by GoalieSaveList: the sprawl right $E862 is the lane of SNES_MECHANICS 4.8); clean
  (he hadn't started a save).

Each goal keeps its setup (spot, aim, moment, release seed: replays exactly, see goal_frames.py) and, for the first
40 of each type, its path frame by frame."""
import json
import random
import sys
import zlib
from multiprocessing import Pool

from lowload import WORKERS, gentle

from paths import RUNS, STATE_TOP, STATE_BOTTOM, SNES_STATE_TOP, SNES_STATE_BOTTOM

KINDS = {"genesis": {"wrist": 3, "slap": 20}, "snes": {"wrist": 3, "slap": 40}}
GEN_SPA = {0x2: "ready", 0x114: "ready", 0x146: "glove right", 0x178: "glove left", 0x1AA: "glove left",
           0x1EC: "stick right (kick)", 0x21E: "stick left (butterfly)", 0x250: "pad stack right",
           0x2A2: "pad stack left", 0x2F4: "dive", 0x3D8: "skate", 0x50C: "glide", 0xA60: "glide back",
           0x148E: "high shoulder right", 0x14C0: "high shoulder left", 0x14F2: "stick right 2", 0x1544: "stick left 2"}
SNES_SPA = {0xE0FE: "ready", 0xE1E2: "glove right", 0xE214: "glove left", 0xE2AA: "pad stack right",
            0xE2FC: "pad stack left", 0xE246: "stick right", 0xE278: "stick left", 0xE862: "sprawl right",
            0xE7D0: "sprawl left", 0xE73E: "butterfly"}
SNES_SAVES = {0xE1E2, 0xE214, 0xE2AA, 0xE2FC, 0xE246, 0xE278, 0xE862, 0xE7D0, 0xE73E}

S = {}          # this process's harnesses and system


class Gen:
    """The Genesis test ROM (harness.py): object records $80 bytes from $B04A."""
    def __init__(self):
        from harness import Harness, rec, GOALIE, SHOOTER
        from mapper import set_ratings
        self.rec, self.G, self.SH = rec, GOALIE, SHOOTER
        top = Harness(state=STATE_TOP, top=True)
        self.h = {"top": top, "bottom": Harness(state=STATE_BOTTOM, top=False, emu=top.e)}
        for h in self.h.values():
            h.e.unserialize(h.base)
            set_ratings(h, 20, 15)
            h.base = h.e.serialize()
        try:
            self.valid = json.load(open(RUNS / "run1" / "validity.json"))
        except FileNotFoundError:
            self.valid = None
        self.score, self.puckc = 0xC6DA, 0xB7AA

    def ok(self, net, hold, x, y):
        return self.valid is None or self.valid.get(f"{net},{hold},{x},{y}", {"ok": False})["ok"]

    def setup(self, net, x, y, p, rnd):
        clock, settle = 590 - (p * 3) % 8, 80 + (p * 7) % 15
        self.h[net].setup(x, y if net == "top" else -y, settle=settle, clock=clock)
        return dict(clock=clock, settle=settle)

    def shoot(self, net, aim, hold):
        return self.h[net].shoot(aim, hold)[0]

    def fire(self, net, pre, aim, seed):
        h = self.h[net]
        h.e.unserialize(pre)
        h.e.setl(0xD066, seed)
        h.park()
        h.e.run(1)

    def state(self, net):
        e, r = self.h[net].e, self.rec
        p, g = r(14), r(self.G)
        return (e.sw(p), e.sw(p + 0x14), e.sw(p + 0x18), e.sw(p + 0x28), e.sw(p + 0x2A), e.sw(g), e.sw(g + 0x14),
                e.w(g + 0x58), e.w(self.puckc) == self.G)

    def step(self, net):
        h = self.h[net]
        h.park(keep_shooter=False)
        h.e.run(1)

    def scored(self, net, s0):
        return self.h[net].e.w(self.score) != s0

    def score0(self, net):
        return self.h[net].e.w(self.score)


class Snes:
    """The SNES retail ROM (snes_harness.py): word arrays, object k at +2k."""
    def __init__(self):
        import snes_harness as H
        from snes_map_run import _init, _h
        _init(13, 13)
        self.H, self.h = H, _h

    def ok(self, net, hold, x, y):
        return True                                   # judged per moment at the release (as snes_map_run)

    def setup(self, net, x, y, p, rnd):
        seed = rnd.getrandbits(32)
        clock, settle = 590 - p % 8, 80 + (p * 7) % 15
        self.h[net].setup(x, y if net == "top" else -y, settle=settle, clock=clock, seed=seed)
        return dict(clock=clock, settle=settle, seed0=seed)

    def shoot(self, net, aim, hold):
        h, H = self.h[net], self.H
        pre = h.shoot(aim, hold)[0]
        if pre is None:
            return None
        e = h.e
        e.unserialize(pre)
        sg = 1 if net == "top" else -1
        g, s = H.o(H.GOALIE), H.o(H.SHOOTER)
        gx, gy = h.sw(H.XPOS + g), h.sw(H.YPOS + g)
        px, py = h.sw(H.XPOS + H.o(H.PUCK)), h.sw(H.YPOS + H.o(H.PUCK))
        sx, sy = h.sw(H.XPOS + s), h.sw(H.YPOS + s)
        dp = ((px - gx) ** 2 + (py - gy) ** 2) ** 0.5
        ds = ((sx - gx) ** 2 + (sy - gy) ** 2) ** 0.5
        return pre if dp >= 24 and ds >= 16 and sg * py < sg * gy else None

    def fire(self, net, pre, aim, seed):
        self.h[net].fire(pre, aim, seed)

    def state(self, net):
        h, H = self.h[net], self.H
        P, g = H.o(H.PUCK), H.o(H.GOALIE)
        return (h.sw(H.XPOS + P), h.sw(H.YPOS + P), h.sw(H.PUCKZ), h.sw(H.XVEL + P), h.sw(H.YVEL + P),
                h.sw(H.XPOS + g), h.sw(H.YPOS + g), h.e.w(H.SPA + g), h.e.w(H.PUCKC) == g)

    def step(self, net):
        h = self.h[net]
        h.park(keep_shooter=False)
        h.e.run(1)

    def scored(self, net, s0):
        return self.h[net].e.w(self.H.SCORE_HOME) != s0

    def score0(self, net):
        return self.h[net].e.w(self.H.SCORE_HOME)


def play(sysobj, net, maxf=150):
    """Play the shot out frame by frame: (goal?, the path [(px, py, pz, pvx, pvy, gx, gy, gspa, held)])."""
    s0 = sysobj.score0(net)
    sign = 1 if net == "top" else -1
    path = [sysobj.state(net)]
    away = held = 0
    for f in range(maxf):
        sysobj.step(net)
        st = sysobj.state(net)
        path.append(st)
        if sysobj.scored(net, s0):
            return True, path
        held = held + 1 if st[8] else 0
        if held >= 20:
            return False, path
        away = away + 1 if st[4] * sign < 0 else 0
        if away >= 4 or st[1] * sign > 280:
            return False, path
    return False, path


REACH = 13             # the Genesis map's goalie: Agility 13 working (xg.REACH)


def classify(system, path, net):
    """The goal's type, and the goalie's animation where the puck passed closest to him. The last frame is the goal
    itself (the game has already moved the puck), so it is left out."""
    sign = 1 if net == "top" else -1
    path = path[:-1]
    held = any(st[8] for st in path)
    touch = None
    for a, b in zip(path, path[1:]):
        if abs(b[3] - a[3]) + abs(b[4] - a[4]) > 1500 and abs(a[1]) < 268:
            dg = ((a[0] - a[5]) ** 2 + (a[1] - a[6]) ** 2) ** 0.5
            touch = ("goalie" if dg < 32 else "post" if 15 <= abs(a[0]) <= 26 and abs(a[1]) > 245 else "other",
                     (a[1] - a[6]) * sign, a[2])
            break
    near = min(path, key=lambda st: (st[0] - st[5]) ** 2 + (st[1] - st[6]) ** 2)
    dmin = ((near[0] - near[5]) ** 2 + (near[1] - near[6]) ** 2) ** 0.5
    if system == "genesis":
        anim = GEN_SPA.get(near[7], hex(near[7]))
        if held:
            t = "Held, then dragged over the line"
        elif near[7] in (0x250, 0x2A2):
            t = "In his pad stack"
        elif touch and touch[0] == "post":
            t = "Off the post"
        elif touch and touch[0] == "goalie" and touch[1] > 0 and touch[2] <= 5:
            t = "Through the blind ring"          # past his stick untouched, off his body behind his centre, in
        elif touch:
            t = "Off the goalie"
        elif dmin < REACH and near[2] <= 5:
            t = "Through the blind ring"
        else:
            t = "Clean: outside his reach"
    else:
        anim = SNES_SPA.get(near[7], hex(near[7]))
        if held:
            t = "Held, then in"
        elif touch and touch[0] == "post":
            t = "Off the post"
        elif touch:
            t = "Off the goalie"
        elif near[7] in SNES_SAVES:
            t = f"Past his {anim}"
        else:
            t = "Clean: before he moved"
    return t, anim, round(dmin, 1), near[2]


def _init(system):
    gentle()
    S["sys"] = system
    S["o"] = Gen() if system == "genesis" else Snes()


def job(args):
    net, x, y, phases, seeds = args
    system, o = S["sys"], S["o"]
    rnd = random.Random(zlib.crc32(f"{system},{net},{x},{y}".encode()))
    shots, goals = 0, []
    for p in range(phases):
        for kind, hold in KINDS[system].items():
            if not o.ok(net, hold, x, y):
                continue
            moment = o.setup(net, x, y, p, rnd)
            settled = o.h[net].e.serialize()
            for aim in range(9):
                o.h[net].e.unserialize(settled)
                pre = o.shoot(net, aim, hold)
                if pre is None:
                    continue
                for _ in range(seeds):
                    seed = rnd.getrandbits(32)
                    o.fire(net, pre, aim, seed)
                    g, path = play(o, net)
                    shots += 1
                    if g:
                        t, anim, dmin, z = classify(system, path, net)
                        goals.append(dict(net=net, x=x, y=y, kind=kind, aim=aim, p=p, seed=seed, type=t, anim=anim,
                                          dmin=dmin, z=z, frames=len(path), path=path, **moment))
    return shots, goals


def main():
    system, run = sys.argv[1], sys.argv[2]
    phases, seeds = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (8, 8)
    workers = int(sys.argv[5]) if len(sys.argv) > 5 else WORKERS
    ys = range(100, 251, 10) if system == "genesis" else range(90, 251, 10)
    jobs = [(net, x, y, phases, seeds) for net in ("top", "bottom") for y in ys for x in range(-110, 111, 10)]
    shots, goals, kept = 0, [], {}
    with Pool(workers, initializer=_init, initargs=(system,)) as pool:
        for i, (n, gs) in enumerate(pool.imap_unordered(job, jobs)):
            shots += n
            for g in gs:
                k = (g["type"], g["net"], g["kind"])
                kept[k] = kept.get(k, 0) + 1
                if kept[k] > 40:
                    g.pop("path")
                goals.append(g)
            if i % 100 == 0:
                print(i, "of", len(jobs), shots, len(goals), flush=True)
    (RUNS / run).mkdir(parents=True, exist_ok=True)
    json.dump(dict(system=system, phases=phases, seeds=seeds, shots=shots, goals=goals),
              open(RUNS / run / f"goal_types_{system}.json", "w"))
    print("done", shots, len(goals))


if __name__ == "__main__":
    main()
