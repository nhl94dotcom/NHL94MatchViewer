"""3-on-3 overtime short draws traced (2026-11-12, for NOSE4Web a91a6f8 / 0c544c0): gen_3on3_ot_check's cases
with TryAddPlayerToList's two calls traced: a scratch copy of the ROM, bsr.w TryAdd at $158D0 / $158EA ->
jsr ($F400).w, a stub in work RAM logging (candidate d0, result d1, slot d4, team a2, flags) to a ring at
$FFF480 (index $FFF47E; the boot ROM check NOPed on a retail copy). At any faceoff drop where a team has fewer
skaters than its tmap: PlList / plpos, tmlines, tmpdst, tmboxlist, tmap, tmgoalie, the team's objects and the
traced calls, every draw with three or more of a team's players sitting in the box
with their objects (crowded_*.json), and every change to the team's objects' position, newpos, newpnum and pnum in the 1,500 frames before. python gen_3on3_ot_trace.py ROM [CASE] [SEEDS] [FIRST]   (to %USERPROFILE%/NHL94_scoring_map/runs/ot3_trace)"""
import sys, json, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pathlib import Path
import emu as EMU
import gen_3on3_ot_check as M
ROM = Path(sys.argv[1])
OUT = Path.home() / "NHL94_scoring_map/runs/ot3_trace"
OUT.mkdir(parents=True, exist_ok=True)
data = bytearray(ROM.read_bytes())
for at in (0x158D0, 0x158EA):
    assert data[at:at + 2] == b"\x61\x00" and int.from_bytes(data[at + 2:at + 4], "big", signed=True) + at + 2 == 0x158F2
    data[at:at + 4] = bytes.fromhex("4eb8f400")
if data[0x300:0x306].hex() == "4eb9000ffac0":
    data[0x300:0x306] = bytes.fromhex("4e714e714e71")     # the boot's ROM check, as NOSE4Web's builds
scratch = OUT / (ROM.stem + "_trace.bin")
scratch.write_bytes(data)
STUB = bytes.fromhex(
    "3f00" "4eb9000158f2" "40e7" "48e72080" "307cf480" "3438f47e" "d0c2"
    "30ef000a" "30c1" "30c4" "30ca" "30ef0008" "0642000a" "024203ff" "31c2f47e"
    "4cdf0104" "44df" "548f" "4e75")
ring_seen = {"idx": 0}
calls = []
frame = {"n": 0}
objlog = {"last": None, "changes": []}
class TEmu(EMU.Emu):
    def run(self, n=1, hold=(), *a, **k):
        for _ in range(n):
            for i, byte in enumerate(STUB):
                self.setb(0xF400 + i, byte)
            super().run(1, hold, *a, **k)
            frame["n"] += 1
            # every object's position word (+$34), newpos (+$60), newpnum (+$61) and pnum (+$66): changes kept
            st = tuple((self.w(M.BASE + M.SZ * k + 0x34), self.b(M.BASE + M.SZ * k + 0x60), self.b(M.BASE + M.SZ * k + 0x61),
                        self.b(M.BASE + M.SZ * k + 0x66)) for k in range(12))
            if st != objlog["last"]:
                objlog["changes"].append({"fr": frame["n"], "objects": {k: {"position": hex(st[k][0]), "newpos": st[k][1],
                                          "newpnum": st[k][2], "pnum": st[k][3]} for k in range(12)
                                          if objlog["last"] is None or st[k] != objlog["last"][k]}})
                objlog["last"] = st
                if len(objlog["changes"]) > 4000:
                    del objlog["changes"][:2000]
            idx = self.w(0xF47E) & 0x3FF
            guard = 0
            while ring_seen["idx"] != idx and guard < 120:       # the stub's own wrap: (idx + 10) & $3FF
                guard += 1
                o = 0xF480 + ring_seen["idx"]
                cand, res, slot, a2, sr = (self.w(o + 2 * j) for j in range(5))
                calls.append({"fr": frame["n"], "team": 0 if a2 == 0xC6CE else 1 if a2 == 0xCA32 else hex(a2),
                              "slot": slot, "cand": cand, "result": res, "Z": bool(sr & 4)})
                ring_seen["idx"] = (ring_seen["idx"] + 10) & 0x3FF
            if guard >= 120:
                ring_seen["idx"] = idx                         # lost track: resynchronise, never loop on
            if len(calls) > 20000:
                del calls[:10000]
M.Emu = TEmu
orig = M.on_ice
dumps = []
short = {0: 0, 1: 0}
prev_stop = {0: False, 1: False}
crowded = []
def on_ice(e, t):
    r = orig(e, t)
    b = M.TEAMS[t]
    tm = e.w(b + M.TMAP)
    gl = any(e.b(M.BASE + M.SZ * k + 0x35) == 0 for k in range(6 * t, 6 * t + 6))
    want = tm - 1 if gl else tm
    stopped = bool(e.b(M.GMODE) & 1)
    drop = prev_stop[t] and not stopped                    # a faceoff drop
    prev_stop[t] = stopped
    if drop:                                               # every draw with 3+ of this team's players in the box
        boxed = [i + 1 for i in range(26) if 0 < e.w(b + 0x66 + 2 * i) < 0x8000]
        held = [e.b(M.BASE + M.SZ * k + 0x66) + 1 for k in range(6 * t, 6 * t + 6)
                if e.b(M.BASE + M.SZ * k + 0x35) == 0xFF and e.b(M.BASE + M.SZ * k + 0x66) + 1 in boxed]
        if len(held) >= 3:
            crowded.append({"team": t, "clock": e.w(M.CLOCK), "tmap": tm, "skaters": len(r), "goalie_on": gl,
                            "boxed": boxed, "boxed_with_objects": held})
    if drop and len(r) < want and tm <= 6 and len(dumps) < 6:   # a team short of its tmap at the drop
        dumps.append({
            "team": t, "clock": e.w(M.CLOCK), "frame": frame["n"], "on_ice": r, "goalie_on": gl,
            "stopped": bool(e.b(M.GMODE) & 1),
            "PlList_last": [e.b(0xCF14 + i) for i in range(6)], "plpos_last": [e.b(0xCF1A + i) for i in range(6)],
            "tmline": e.w(b + 0x16), "tmlines": [e.b(b + 0x16A + i) for i in range(64)],
            "tmpdst": [hex(e.w(b + 0x66 + 2 * s)) for s in range(26)],
            "tmboxlist": [e.b(b + 0x9A + i) for i in range(26)],
            "tmap": tm, "tmgoalie": hex(e.w(b + 0x26)),
            "objects": [{"k": k, "position": e.b(M.BASE + M.SZ * k + 0x35), "pnum+1": e.b(M.BASE + M.SZ * k + 0x66) + 1}
                        for k in range(6 * t, 6 * t + 6)],
            "calls_last_3000": [c for c in calls if c["fr"] > frame["n"] - 3000 and c["team"] == t],
            "object_changes_last_1500": [{"fr": c["fr"], "objects": {k: v for k, v in c["objects"].items()
                                                                     if 6 * t <= k < 6 * t + 6}}
                                         for c in objlog["changes"] if c["fr"] > frame["n"] - 1500]})
    return r
M.on_ice = on_ice
case = sys.argv[2] if len(sys.argv) > 2 else "off"
first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
for seed in range(first, first + (int(sys.argv[3]) if len(sys.argv) > 3 else 1)):
    calls.clear(); ring_seen["idx"] = 0; frame["n"] = 0; short[0] = short[1] = 0
    objlog["last"] = None; objlog["changes"].clear()
    n0 = len(dumps)
    r = M.run_case(str(scratch), case, seed, OUT)
    for d in dumps[n0:]:
        d["seed"] = seed
    print(seed, r.get("score"), r.get("error"), r.get("gsp"), "short-handed beyond tmap:", len(dumps) - n0, flush=True)
    (OUT / f"dumps_{ROM.stem}_{case}.json").write_text(json.dumps(dumps, indent=1))
    (OUT / f"crowded_{ROM.stem}_{case}.json").write_text(json.dumps(crowded, indent=1))
