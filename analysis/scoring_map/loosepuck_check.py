"""A dead-still loose puck near each net: does the computer goalie go for it? (2026-11-19; NOSE4Web: assgoalie .24
($DB04) and assgoalietopuck ($DD7E) test "the puck moving away" with eori #8,ccr for the bottom goalie, so a puck with
puckvy = 0 counts as moving away from him but not from the top goalie; their patch nhl94_loosepuck, ef73440c.)

The scoring-map harness (paths.ROM: the test ROM, or NHL94_SMAP_ROM a patched copy), both nets with the period clock
the same: the goalie settled in his net, every skater parked at the far end (so assgoalie's tmnear conditions hold:
his team's nearest 70+ away, the opponents' 50+), the puck put loose and still (no carrier, speeds 0, on the ice) at
each spot (net coordinates: x across, y toward the net; past the circles, |y| > 224, in front of the goal line and
behind it), played 180 frames with the skaters held parked: does the goalie take it (puckc his record) and when, how far he moved,
and whether his assignment became assgoalietopuck (asslist +$38 at assnum +$36 = 15).

python loosepuck_check.py OUT.json   |   python loosepuck_check.py report A.json [B.json]"""
import json
import math
import sys

XS = (-60, -30, 0, 30, 60)
YS = (228, 238, 248, 256, 272, 282, 292)


def run(out):
    import harness as H
    from harness import Harness, rec, GOALIE, PUCK, PUCKC
    from paths import STATE_TOP, STATE_BOTTOM, ROM
    top = Harness(state=STATE_TOP, top=True)
    hs = {"top": top, "bottom": Harness(state=STATE_BOTTOM, top=False, emu=top.e)}
    e = top.e
    res = {"rom": str(ROM), "rows": []}
    for net, h in hs.items():
        sg = 1 if net == "top" else -1
        for y in YS:
            for x in XS:
                e.unserialize(h.base)
                e.setw(0xC468, 300)
                for _ in range(60):                       # the goalie settles; nobody near
                    h.park(keep_shooter=False)
                    e.run(1)
                g0 = (e.sw(rec(GOALIE)), e.sw(rec(GOALIE) + 0x14))
                p = PUCK
                for off, v in ((0, sg * x), (2, 0), (0x14, sg * y), (0x16, 0), (0x18, 0), (0x1A, 0), (0x28, 0), (0x2A, 0), (0x2C, 0)):
                    e.setw(p + off, v & 0xFFFF)
                e.setw(PUCKC, 0xFF00 | (e.w(PUCKC) & 0xFF))
                got, far, topuck = None, 0.0, None
                g = rec(GOALIE)
                for f in range(180):
                    h.park(keep_shooter=False)
                    e.run(1)
                    if topuck is None and e.b(g + 0x38 + e.w(g + 0x36)) == 15 if e.w(g + 0x36) < 8 else False:
                        topuck = f
                    gx, gy = e.sw(rec(GOALIE)), e.sw(rec(GOALIE) + 0x14)
                    far = max(far, math.hypot(gx - g0[0], gy - g0[1]))
                    if e.w(PUCKC) == GOALIE:
                        got = f
                        break
                pv = (e.sw(p + 0x28), e.sw(p + 0x2A))
                res["rows"].append(dict(net=net, x=x, y=y, got=got, moved=round(far, 1), puck_v=pv, topuck=topuck))
        print(net, "done", flush=True)
    json.dump(res, open(out, "w"))


def report(paths):
    for p in paths:
        d = json.load(open(p))
        print("==", p, d["rom"])
        for net in ("top", "bottom"):
            rs = [r for r in d["rows"] if r["net"] == net]
            for front, lab in ((True, "in front of the goal line"), (False, "behind it")):
                ss = [r for r in rs if (r["y"] < 264) == front]
                got = [r for r in ss if r["got"] is not None]
                print(f"  {net:6s} {lab:26s}: goalie took it {len(got)} of {len(ss)}"
                      + (f", median {sorted(r['got'] for r in got)[len(got) // 2]} frames" if got else "")
                      + f"; moved 10+ toward it {sum(r['moved'] >= 10 for r in ss)}; assgoalietopuck {sum(r.get('topuck') is not None for r in ss)}")


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2:])
    else:
        run(sys.argv[1])
