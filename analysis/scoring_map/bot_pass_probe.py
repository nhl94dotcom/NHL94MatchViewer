"""The bot's passes against the game's pass target (2026-11-11, chunk 3: the game counts a pass completed only when the
player who takes the puck is passReceiverPlayerNum ($FFBEE0, set when the pass is made: collide94 puckglue), and the
bot's games show 43% by that count against 66% kept by the team). bot_run.play with every frame watched: at each pass
the bot starts (its log's "pass start": the mate it meant), the d-pad it held, the game's target ($BEE0) once set, and
who next took the puck (puckc $B7AA): the meant mate, the game's target, another teammate, an opponent. Per game and
in all: the counts, and for the passes the game aimed elsewhere, the angle from the passer to the meant mate and to
the game's target against the d-pad's direction.

python bot_pass_probe.py GAMES [VERSION]"""
import json
import math
import os
import sys
from collections import Counter

import bot_run
from bot import DIRS
from emu import Emu
from lowload import gentle, breathe
from paths import WORK

TARGET, PUCKC = 0xBEE0, 0xB7AA
R = lambda k: 0xB04A + 0x80 * k
PADDIR = {}
for i, d in enumerate(DIRS):
    PADDIR[tuple(sorted(d if isinstance(d, list) else [d]))] = i * 45


def main():
    games = int(sys.argv[1])
    version = int(sys.argv[2]) if len(sys.argv) > 2 else 45
    gentle()
    e = Emu(bot_run.RETAIL)
    start = (WORK / "bot_start.state").read_bytes()
    total = Counter()
    off = []
    base_run = e.run
    for g in range(games):
        st = {"frame": 0, "open": None, "bot": None, "seen": 0}

        def run(k=1, hold=(), **kw):
            for _ in range(k):
                base_run(1, hold=hold, **kw)
                st["frame"] += 1
                b = st["bot"]
                if b is None:
                    continue
                if st["seen"] < len(b.log):                 # a new event this frame
                    for ev in b.log[st["seen"]:]:
                        if ev["ev"] == "pass start":
                            dirs = tuple(sorted(x for x in hold if x in ("UP", "DOWN", "LEFT", "RIGHT")))
                            me = next((j for j in range(6) if e.b(R(j) + 0x62) & 8), None)
                            st["open"] = {"f": st["frame"], "meant": b.mate, "passer": me, "pad": dirs, "target": None,
                                          "people": ev.get("people", False), "onetimer": ev.get("onetimer", False)}
                    st["seen"] = len(b.log)
                o = st["open"]
                if o is None:
                    continue
                t = e.w(TARGET)
                if o["target"] is None and t < 12:
                    o["target"] = t
                    if o["passer"] is not None:
                        P = lambda j: (e.sw(R(j)), e.sw(R(j) + 0x14))
                        px, py = P(o["passer"])
                        angle = lambda j: math.degrees(math.atan2(-(P(j)[1] - py), P(j)[0] - px))   # screen: up is +y
                        o["a_meant"], o["a_target"] = angle(o["meant"]), angle(t)
                c = e.w(PUCKC)
                if st["frame"] - o["f"] > 4 and c < 12 and c != o["passer"]:
                    who = ("meant" if c == o["meant"] else "") + ("+target" if c == o["target"] else "")
                    who = who or ("other teammate" if c < 6 else "opponent")
                    total[who] += 1
                    kind = "one-timer pass" if o["onetimer"] else "people's pass" if o["people"] else "32's pass"
                    total[f"{kind}: {who}"] += 1
                    if c >= 6 and o["passer"] is not None:   # an opponent: how far the puck went, and was he a goalie
                        total[f"{kind}: opponent was goalie"] += e.b(R(c) + 0x35) == 0
                    total["target is meant" if o["target"] == o["meant"] else "target elsewhere" if o["target"] is not None else "no target"] += 1
                    if o["target"] is not None and o["target"] != o["meant"]:
                        off.append({k: (round(v) if isinstance(v, float) else v) for k, v in o.items()})
                    st["open"] = None
                elif st["frame"] - o["f"] > 120:
                    total["nobody took it in 2 s"] += 1
                    total[("one-timer pass" if o["onetimer"] else "people's pass" if o["people"] else "32's pass") + ": nobody"] += 1
                    st["open"] = None
        e.run = run
        orig_init = bot_run.Bot.__init__

        def init(self, *a, **kw):
            orig_init(self, *a, **kw)
            if st["bot"] is None:
                st["bot"] = self
        bot_run.Bot.__init__ = init
        os.environ["NHL94_BOT_VERSION"] = str(version)
        r = bot_run.play(e, start, 0x9E3779B1 * (g + 1) & 0xFFFFFFFF, home=version)
        bot_run.Bot.__init__ = orig_init
        e.run = base_run
        print(json.dumps({"game": g, "score": r["score"], "so far": dict(total)}), flush=True)
        breathe()
    print(json.dumps({"total": dict(total), "aimed elsewhere (first 25)": off[:25]}, indent=0))


if __name__ == "__main__":
    main()
