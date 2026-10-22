"""The chance a shot scores, from the real game. For one spot, aim and wind-up:

- phases: the moment of the shot matters (the goalie's look-ahead uses the game clock's low bits, the wind-up save
  rule bit 1 of its seconds, findpc runs every 5 frames and his rethink countdown every few), so the shot is set up at
  8 clock values x 15 settle lengths (every combination of the 5- and 3-frame cycles) and every launch is played at
  one of those 120 moments, equally weighted;
- perfect: with chance (ShA + 1) / (ShA + 16) from within 200 of the aim point, the launch is exact: played at all;
- scatter: every (sx, sy, sz) the scatter can draw is equally likely; when there are few enough, all of them are played
  at every phase (exact); otherwise a random sample of (phase, sx, sy, sz), with its standard error.
"""
import random
from fractions import Fraction

from harness import Harness, fire, decide, rec, SHOOTER
from shotport import scatter_ranges, launch, perfect_chance

CLOCKS = [590 - i for i in range(8)]
SETTLES = list(range(80, 95))


def set_ratings(h, shp, sha):
    e = h.e
    e.setb(rec(SHOOTER) + 0x6C, shp)
    e.setb(rec(SHOOTER) + 0x6D, sha)


def prepare(h, x, y, aim, hold, shp, sha):
    """The 16 release states (pre-doshot) and the shot's inputs. None if no shot came."""
    pres, inp = [], None
    h.e.unserialize(h.base)
    set_ratings(h, shp, sha)
    rated, saved = h.e.serialize(), h.base
    for c in CLOCKS:
        for s in SETTLES:
            h.base = rated
            h.setup(x, y, settle=s, clock=c)
            h.base = saved
            pre, f = h.shoot(aim, hold)
            if pre is None:
                return None, None
            en = h.entry()
            i = dict(px=en["px"], py=en["py"], dir=en["dir"], pout=en["pout"], sha=en["sha"], top=en["top"],
                     vz0=0, gspa=en["gspa"])
            if inp is None:
                inp = i
            elif (i["px"], i["py"], i["pout"]) != (inp["px"], inp["py"], inp["pout"]):
                inp.setdefault("varies", 0)
                inp["varies"] += 1
            pres.append((pre, i, en["v"]))
    return pres, inp


def cell(h, x, y, aim, hold, shp, sha, budget=1500, rng=None):
    """Monte Carlo over the exact distribution: the perfect branch and the scatter branch sampled separately (each
    sample a random moment, a random post-release seed, and for the scatter a random (sx, sy, sz)), combined with the
    exact perfect chance."""
    rng = rng or random.Random(hash((x, y, aim, hold, shp, sha)) & 0xFFFFFFFF)
    pres, inp = prepare(h, x, y, aim, hold, shp, sha)
    if pres is None:
        return None
    p = float(perfect_chance(inp))
    n_p = int(budget * p) if p else 0
    n_p = max(n_p, 120) if p else 0
    n_s = budget - n_p if p < 1 else 0
    gp = gs = 0
    for k in range(n_p):
        pre, i, _ = pres[k % len(pres)] if k < len(pres) else pres[rng.randrange(len(pres))]
        fire(h, pre, launch(i, True), post_seed=rng.getrandbits(32))
        gp += decide(h)[0]
    for _ in range(n_s):
        pre, i, _ = pres[rng.randrange(len(pres))]
        adj, yadj, zr, d3 = scatter_ranges(i)
        sx = rng.randrange(-adj, adj) if adj else 0
        sy = rng.randrange(-yadj, yadj) if yadj else 0
        sz = rng.randrange(zr) if zr else 0
        fire(h, pre, launch(i, False, sx, sy, sz), post_seed=rng.getrandbits(32))
        gs += decide(h)[0]
    perf = gp / n_p if n_p else 0.0
    sc = gs / n_s if n_s else 0.0
    chance = p * perf + (1 - p) * sc
    var = (p * p * perf * (1 - perf) / n_p if n_p else 0) + ((1 - p) ** 2 * sc * (1 - sc) / n_s if n_s else 0)
    adj, yadj, zr, d3 = scatter_ranges(inp)
    return dict(x=x, y=y, aim=aim, hold=hold, shp=shp, sha=sha, chance=chance, se=var ** 0.5, p=p, perfect=perf,
                scatter=sc, n=n_p + n_s, adj=adj, d3=d3, pout=inp["pout"], varies=inp.get("varies", 0))
