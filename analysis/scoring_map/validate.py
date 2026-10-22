"""Natural shots (the game's own random draws, from a random seed at the release) against mapper.cell's figure:
python validate.py top|bottom X Y AIM HOLD N SEED (N = 0: mapper.cell's estimate; else N natural shots)."""
import sys, random, json
from harness import Harness, decide, rec
from mapper import cell, prepare
from paths import STATE_TOP, STATE_BOTTOM
top, (x, y, aim, hold, n, seedbase) = sys.argv[1] == "top", map(int, sys.argv[2:8])
h = Harness(state=STATE_TOP if top else STATE_BOTTOM, top=top)
rng = random.Random(seedbase)
if n == 0:
    r = cell(h, x, y, aim, hold, 20, 15, budget=4000, rng=rng)
    print(json.dumps(r))
else:
    pres, inp = prepare(h, x, y, aim, hold, 20, 15)
    g = 0
    for i in range(n):
        pre, _, _ = pres[rng.randrange(len(pres))]
        h.e.unserialize(pre)
        h.e.setl(0xD066, rng.getrandbits(32))
        h.park()
        h.e.run(1)
        g += decide(h)[0]
    print(json.dumps(dict(goals=g, n=n)))
