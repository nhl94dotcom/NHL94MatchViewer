"""Computer hooks per opportunity by end (Genesis, 2026-11-19; NOSE4Web: normalise the computer defenders' hooks by
the frames check4check could start one).

From the raw captures of the recorded games (people's, regulation, play only), every other sample: an opportunity is
a computer-steered defender (pflags bit 3 clear; not a goalie) within +-30 in x and y of an opponent skater and facing
him exactly (facedir +$55 == vtoa(opponent - him), check4check's test), counted per (defender, opponent) pair; once
against any opponent and once against the carrier only (puckc $B7AA). End: the net the opponent's team attacks.
Hooks and holds: as hook_by_end.py (a flail $0CF4, its catcher the opponent in a hold / hook animation within 40
samples before, computer-steered). Hooks per 1,000 opportunity samples by end, and the bottom net's hooks listed with
the capture sample, period and clock, the hooker's record, position, assignment and his animation before the hook.

python analysis/hook_opportunity.py"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import export_match  # noqa: E402
from hook_by_end import ASS, BASE, FLAIL, HOLD, HOOK, HOME, POS, PUCKC, Rec, s16, vtoa  # noqa: E402

STEP = 2


def main():
    opp, hooks = Counter(), Counter()
    listed = []
    games = 0
    for mp in sorted((HOME / "matches").glob("*.js")):
        if mp.name == "season.js":
            continue
        cf = HOME / "captures" / mp.stem
        if not cf.exists():
            continue
        t = mp.read_text()
        m = json.loads(t[t.index("{"):t.rindex("}") + 1])
        if (m.get("system") or "genesis") != "genesis" or "bot" in str(m.get("name", "")):
            continue
        cap = export_match.Capture(cf)
        games += 1
        cache = {}

        def R(i):
            if i not in cache:
                cache[i] = Rec(cap, i)
                if len(cache) > 200:
                    cache.pop(next(iter(cache)))
            return cache[i]
        prev_flail = [False] * 12
        for i in range(1, cap.count):
            if cap.word(i, 0xFFF7) & 0xFF or cap.word(i, 0xC466) > 2:
                prev_flail = [False] * 12
                continue
            per = cap.word(i, 0xC466)
            r = R(i)
            if i % STEP == 0:
                pc = cap.word(i, PUCKC)
                for k in range(12):
                    pk = r.b(k, 0x35)
                    if pk in (0, 0xFF) or r.b(k, 0x62) & 8:
                        continue
                    kx, ky, face = s16(r.w(k, 0)), s16(r.w(k, 0x14)), r.b(k, 0x55) & 7
                    for v in (range(6, 12) if k < 6 else range(6)):
                        if r.b(v, 0x35) in (0, 0xFF):
                            continue
                        dx, dy = s16(r.w(v, 0)) - kx, s16(r.w(v, 0x14)) - ky
                        if abs(dx) > 30 or abs(dy) > 30 or vtoa(dx, dy) != face:
                            continue
                        end = "Up" if ((v < 6) == (per % 2 == 0)) else "Down"
                        opp[(end, "any")] += 1
                        if pc == v:
                            opp[(end, "carrier")] += 1
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
                        while j0 > max(0, j - 60) and R(j0 - 1).w(k2, 0x58) in HOLD | HOOK:
                            j0 -= 1
                        s = R(max(0, j0 - 1))
                        if not s.b(k2, 0x62) & 8:
                            end = "Up" if (team == 0) == (cap.word(j0, 0xC466) % 2 == 0) else "Down"
                            carrier = cap.word(max(0, j0 - 1), PUCKC) == v
                            hooks[(end, "any")] += 1
                            if carrier:
                                hooks[(end, "carrier")] += 1
                            if end == "Down" and len(listed) < 40:
                                ass = s.b(k2, 0x38 + s.w(k2, 0x36)) if s.w(k2, 0x36) < 8 else 255
                                listed.append(dict(game=mp.stem[:22], sample=j0, period=cap.word(j0, 0xC466) + 1,
                                                   clock=cap.word(j0, 0xC468), hooker=k2, pos=POS.get(s.b(k2, 0x35), "?"),
                                                   assignment=ASS[ass] if ass < len(ASS) else ass, kind=kind,
                                                   before=f"${s.w(k2, 0x58):04X}", hooked_anim=f"${R(j0).w(k2, 0x58):04X}",
                                                   victim=v, victim_carrier=carrier))
                prev_flail[v] = now
        print(mp.stem, dict(hooks), flush=True)
    print(f"\n{games} games; opportunity samples (every {STEP}nd sample) and computer hooks / holds by end")
    for who in ("any", "carrier"):
        for end in ("Up", "Down"):
            o, h = opp[(end, who)], hooks[(end, who)]
            print(f"  against {who:7s} {end:4s}: opportunities {o:7d}  hooks {h:4d}  per 1,000 {1000 * h / max(o, 1):.2f}")
        ou, od, hu, hd = opp[("Up", who)], opp[("Down", who)], hooks[("Up", who)], hooks[("Down", who)]
        if ou and od and hu and hd:
            print(f"     opportunities Down/Up {od / ou:.3f}; hooks per opportunity Down/Up {(hd / od) / (hu / ou):.3f}")
    print("\nBottom-net (Down attacker) computer hooks, first 40:")
    for x in listed:
        print("  ", x)


if __name__ == "__main__":
    main()
