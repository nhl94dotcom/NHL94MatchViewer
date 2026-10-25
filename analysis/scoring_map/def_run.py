"""A defender against the plays that score (docs/DEFENCE_PLAN.md study 4; 2026-10-25). The deke runner's plays
(deke_run.py: its "best" set-ups, the best of each deke and floater for each hand, both nets) with one defending
skater added: the away team's left defenceman (record DEF: working Weight 88, Agility 20, Speed 20, Checking 15; the
computer controls him). He is put at a spot in the attacker's view (dx: across from the lane the shooter starts in,
+ his right; dout: out from the goal line) for the whole set-up, and then:
- "static": held there, still, for the whole play (his body alone: does it block the swing, the shot or the skater?);
- "cpu": let go when the shooter starts skating in, so the game's own defensive play takes over (pokes, checks,
  chasing the puck: what a defender left to the computer does from there).
Baseline: the same set-ups with no defender ("none"). The attacker is deke_run's bot: fixed inputs, blind to the
defender, so a defender held in its lane is a wall it skates into; "static" maps where a body breaks the planned move,
not what a person would do about it; "cpu" is the realistic one. The outcomes are deke_run's: goals, no goal, no shot, the puck
lost before the shot (a poke or steal among them), carried in.
Plans: "deke" (the pilot: the best set-ups x the spots x both modes). NHL94_DEKE_MOMENTS as in deke_run (default 12).
python def_run.py PLAN RUN [minutes]   -> paths.RUNS / RUN / def_<PLAN>.jsonl"""
import itertools
import json
import sys
import time
from multiprocessing import Pool

import deke_run as DR
from harness import Harness, rec
from lowload import WORKERS
from paths import RUNS

CREEP = 64                      # 1/64 unit a frame
DEF = 10                        # the away left defenceman (the other away skaters are parked as usual)
GOAL_Y = 264
KEYS = DR.KEYS + ("mode", "dx", "dout")


class DefHarness(Harness):
    """The harness with one defender kept on the ice: pinned to his spot while `pinned`, else left alone."""
    defender, pinned, mode = None, True, "none"

    def park(self, keep_shooter=True):
        e, d = self.e, self.defender
        kept = [e.w(rec(DEF) + off) for off in (0, 0x14, 0x28, 0x2A, 0x2C)] if d else None
        super().park(keep_shooter)
        if not d:
            return
        if self.pinned:
            e.setw(rec(DEF), d[0])
            e.setw(rec(DEF) + 0x14, d[1])
            e.setb(rec(DEF) + 0x55, 4 if self.top else 0)      # facing the shooter coming in
            for off in (0x28, 0x2A, 0x2C):
                e.setw(rec(DEF) + off, 0)
            e.setw(rec(DEF) + 0x2A, CREEP if self.top else -CREEP & 0xFFFF)   # a creep toward the shooter: the game
            # finds player collisions through its y-sorted object list, which it updates only for a player moving
            # under his own speed; a skater put in place with no speed stays where the list last had him and nobody
            # touches him (collide94 checkplcoll)
        else:                                                  # left to the game: undo the parking
            for off, v in zip((0, 0x14, 0x28, 0x2A, 0x2C), kept):
                e.setw(rec(DEF) + off, v)

    def setup(self, x, y, settle=90, clock=None):
        self.pinned = True
        super().setup(x, y, settle, clock)
        self.pinned = self.mode != "cpu"


def plan_jobs(plan):
    base = DR.plan_jobs("best")
    if plan == "deke":
        spots = list(itertools.product(range(-40, 41, 10), range(40, 101, 15)))
        jobs = [j + ("none", 0, 0) for j in base]
        jobs += [j + (mode, dx, dout) for j in base for mode in ("static", "cpu") for dx, dout in spots]
        return jobs
    raise SystemExit(f"unknown plan {plan}")


def _init():
    DR.gentle()
    top = DefHarness(state=DR.STATE_TOP, top=True)
    DR._h["top"], DR._h["bottom"] = top, DefHarness(state=DR.STATE_BOTTOM, top=False, emu=top.e)


def job(args):
    *deke, mode, dx, dout = args
    h = DR._h[deke[1]]
    sg = 1 if h.top else -1
    h.mode = mode
    x0 = deke[3]                                               # the shooter's starting lane (attacker's view)
    h.defender = None if mode == "none" else (sg * (x0 + dx), sg * (GOAL_Y - dout))
    res = DR.job(tuple(deke))
    return dict(res, mode=mode, dx=dx, dout=dout)


def main():
    plan, run = sys.argv[1], sys.argv[2]
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    path = RUNS / run / f"def_{plan}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        for line in open(path):
            d = json.loads(line)
            done.add(tuple(d[k] for k in KEYS))
    todo = [j for j in plan_jobs(plan) if j not in done]
    print(f"{plan}: {len(done)} jobs done before, {len(todo)} to go; this chunk: up to {minutes:g} minutes", flush=True)
    t0, deadline, finished = time.time(), time.time() + 60 * minutes, 0
    with Pool(WORKERS, initializer=_init) as pool, open(path, "a") as f:
        pending, queue = [], list(todo)
        while queue or pending:
            while queue and len(pending) < WORKERS and time.time() < deadline:
                pending.append(pool.apply_async(job, (queue.pop(0),)))
            if not pending:
                break
            time.sleep(1)
            for a in [a for a in pending if a.ready()]:
                pending.remove(a)
                f.write(json.dumps(a.get()) + "\n")
                f.flush()
                finished += 1
    print(f"chunk over: {finished} jobs in {(time.time() - t0) / 60:.1f} minutes; {len(todo) - finished} left", flush=True)


if __name__ == "__main__":
    main()
