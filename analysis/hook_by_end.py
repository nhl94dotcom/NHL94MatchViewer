"""The Genesis computer defenders' hooks and holds by end, from the raw captures (2026-11-19; NOSE4Web: computer
defenders hook Down attackers 222 times against 160 on Up attackers in our games; check4check is even between the
ends, so which assignment puts defenders facing the carrier at close range more often at the bottom net?).

Each recorded Genesis game with its capture (people's games, regulation, play only): a skater going into the flail
animation ($0CF4) is the hook or hold's victim; its catcher the opponent in a hold ($0C90 / $0CC2) or hook ($1122 /
$1154) animation within 40 samples before, computer-controlled (pflags bit 3 clear). On the sample just before the
catcher's hold or hook began (when check4check chose it), from the record ($80 bytes from $B04A): his position (+$35),
his assignment (asslist +$38 at assnum +$36, named from asstab), facedir (+$55) against vtoa(victim - him) (check4check
needs them equal), the gap (|dx|, |dy| within 30), where he stood relative to the victim's travel (his velocity +$28 /
+$2A: in front, beside or behind, by the angle between the travel and the line to the catcher), the victim a carrier
or not (puckc $B7AA), and the zone (the victim's y against the net his team attacks). End: the net the victim's team
attacks (home attacks up in periods 1 and 3).

python analysis/hook_by_end.py"""
import json
import math
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import export_match  # noqa: E402

HOME = Path.home() / "Documents" / "NHL94 Viewer"
BASE, SZ, PUCKC = 0xB04A, 0x80, 0xB7AA
FLAIL, HOLD, HOOK = 0x0CF4, {0x0C90, 0x0CC2}, {0x1122, 0x1154}
ASS = ["null", "assdefo", "assdefd", "asswingd", "asswingo", "asscenterd", "asscentero", "assscore", "assstanley",
       "asseben", "assepen", "assbench", "asspenalty", "assdopen", "assgoalie", "assgoalietopuck", "asspuckc",
       "assnearest", "assshoot", "asspassrec", "assfight", "assfwatch", "assfaceoff", "assfaceoffpl"] + \
      [f"ass{n}" for n in range(24, 36)]
POS = {0: "G", 1: "D", 2: "D", 3: "W", 4: "C", 5: "W"}
DT = [1, 7, 3, 5, 0, 0, 4, 4, 2, 6, 2, 6, 1, 7, 3, 5]


def vtoa(dx, dy):
    if dx == 0 and dy == 0:
        return 8
    i = 0
    if dx < 0:
        dx, i = -dx, i | 1
    if dy < 0:
        dy, i = -dy, i | 2
    if not dx > 2 * dy:
        i |= 4
    if not dy > 2 * dx:
        i |= 8
    return DT[i]


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


class Rec:
    """One sample's 12 player records, from the capture's raw block (words little-endian, bytes swapped)."""
    def __init__(self, cap, i):
        self.raw = cap.raw(i, BASE, SZ * 12)

    def w(self, k, off):
        return struct.unpack_from("<H", self.raw, SZ * k + off)[0]

    def b(self, k, off):
        return self.raw[SZ * k + (off ^ 1)]


def main():
    out = defaultdict(Counter)
    games = 0
    for mp in sorted((HOME / "matches").glob("*.js")):
        if mp.name == "season.js":
            continue
        cf = HOME / "captures" / mp.stem
        if not cf.exists():
            continue
        try:
            m = json.loads(mp.read_text()[mp.read_text().index("{"):mp.read_text().rindex("}") + 1])
        except Exception:
            continue
        if (m.get("system") or "genesis") != "genesis" or "bot" in str(m.get("name", "")):
            continue
        try:
            cap = export_match.Capture(cf)
        except Exception:
            continue
        games += 1
        recs = {}

        def R(i):
            if i not in recs:
                recs[i] = Rec(cap, i)
                if len(recs) > 200:
                    recs.pop(next(iter(recs)))
            return recs[i]
        prev_flail = [False] * 12
        for i in range(1, cap.count):
            if cap.word(i, 0xFFF7) & 0xFF or cap.word(i, 0xC466) > 2:
                prev_flail = [False] * 12
                continue
            r = R(i)
            for v in range(12):
                now = r.w(v, 0x58) == FLAIL and r.b(v, 0x35) not in (0, 0xFF)
                if now and not prev_flail[v]:
                    team = 0 if v < 6 else 1
                    found = None
                    for j in range(i, max(0, i - 40), -1):
                        rj = R(j)
                        for k2 in (range(6, 12) if team == 0 else range(6)):
                            a = rj.w(k2, 0x58)
                            if a in HOLD or a in HOOK:
                                found = (j, k2, "hold" if a in HOLD else "hook")
                                break
                        if found:
                            break
                    if found:
                        j, k2, kind = found
                        j0 = j
                        while j0 > max(0, j - 60) and (R(j0 - 1).w(k2, 0x58) in HOLD | HOOK):
                            j0 -= 1
                        s = R(max(0, j0 - 1))
                        if s.b(k2, 0x62) & 8:
                            out["person"]["n"] += 1
                        else:
                            per = cap.word(j0, 0xC466)
                            end = "Up" if (team == 0) == (per % 2 == 0) else "Down"
                            sg = 1 if end == "Up" else -1
                            cx, cy = s16(s.w(k2, 0)), s16(s.w(k2, 0x14))
                            vx_, vy_ = s16(s.w(v, 0)), s16(s.w(v, 0x14))
                            dx, dy = vx_ - cx, vy_ - cy
                            face = s.b(k2, 0x55) & 7
                            ass = s.b(k2, 0x38 + s.w(k2, 0x36)) if s.w(k2, 0x36) < 8 else 255
                            tvx, tvy = s16(s.w(v, 0x28)), s16(s.w(v, 0x2A))
                            if abs(tvx) + abs(tvy) < 200:
                                rel = "victim still"
                            else:
                                ang = math.degrees(math.acos(max(-1, min(1, ((-dx) * tvx + (-dy) * tvy) /
                                                                         (math.hypot(dx, dy) * math.hypot(tvx, tvy) or 1)))))
                                rel = "in front" if ang < 60 else ("beside" if ang <= 120 else "behind")
                            zy = vy_ * sg
                            zone = "attacking zone" if zy > 88 else ("own zone" if zy < -88 else "neutral zone")
                            carrier = cap.word(j0, PUCKC) == v
                            O = out[end]
                            O["n"] += 1
                            O[f"kind {kind}"] += 1
                            O[f"position {POS.get(s.b(k2, 0x35), '?')}"] += 1
                            O[f"assignment {ASS[ass] if ass < len(ASS) else ass}"] += 1
                            O[f"zone {zone}"] += 1
                            O[f"catcher {rel}"] += 1
                            O[f"facing matches vtoa {face == vtoa(dx, dy)}"] += 1
                            O[f"within 30 {abs(dx) <= 30 and abs(dy) <= 30}"] += 1
                            O[f"victim carrier {carrier}"] += 1
                prev_flail[v] = now
        print(mp.stem, dict(out["Up"])["n"] if "n" in out["Up"] else 0, dict(out["Down"]).get("n", 0), flush=True)
    print(f"\n{games} games; person catchers left out: {out['person']['n']}")
    keys = sorted(set(out["Up"]) | set(out["Down"]))
    for k in keys:
        up, dn = out["Up"][k], out["Down"][k]
        print(f"  {k:42s} Up {up:4d}  Down {dn:4d}  Down/Up {dn / up:.2f}" if up else f"  {k:42s} Up {up:4d}  Down {dn:4d}")


if __name__ == "__main__":
    main()
