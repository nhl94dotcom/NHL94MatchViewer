"""NOSE4Web's repeated-checks fix (b03835c, nhl94_repeat_check_fix.bin), played (2026-11-11). GENESIS_MECHANICS 7.3:
FallDown ignores a call for the same checker and target as its last call (PlayerChked $DEDC / PlayerChking $DEE0,
recorded on every call past the animation tests). The fix (a jsr at $140A8 to $FFAC6) still ignores the pair, but only
while the target's nopuck word ($5E: nopuck, set to 120 by a fall, and nopuckb, 60 by a wobble) is non-zero.

The test, on the scoring-map test ROM and on it with the build laid over it (gen_onetimer_assist_test.overlay): the
pad-1 skater (record 2, a person's checker) bursts (C without the puck) into an away skater standing still (record 8),
everyone else parked and the puck loose far away.
- The first check: the target set 2 Weight points heavier, so a person's check wraps and always knocks him down. The
  fall's length (the target's animation in the fall / stumble set) and his nopuck countdown.
- The same checker again after D frames, the target put back where he was (his animation and nopuck kept): still 2
  heavier (always down if FallDown lets it through), so each D shows whether the pair is blocked.
- Equal weights (the knockdown roll), N seeds: the repeated pair against a fresh pair (PlayerChked cleared) on each ROM.
- Every collision: the team's check count ($C6CE + $10) goes up by one a knockdown, never two.

python gen_repeat_check_fix_test.py RETAIL BUILD [N]"""
import os
import sys
from pathlib import Path

CHECKER, TARGET = 2, 8
CHKED, CHKING = 0xDEDC, 0xDEE0
SEED = 0xD066
TEAM_CHECKS = 0xC6CE + 0x10
FALLS = {0x0DD8, 0x0D26, 0x145C, 0x11E6}        # fall and stumble animations (match_report DOWN)
CHECK_ANIM = 0x0B96                             # the checker's check animation (on contact)


def main():
    retail, build = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 40
    from lowload import gentle, breathe
    gentle()
    import harness
    from harness import Harness, rec, PUCK, PUCKC
    from gen_onetimer_assist_test import overlay
    from paths import ROM, STATE_TOP
    out = Path(os.environ.get("TEMP", ".")) / ("smap94_" + Path(build).name)
    if "--one" not in sys.argv:
        overlay(build, retail, ROM, out)
    if "--one" not in sys.argv:                    # one ROM a process (the core is one DLL per process)
        import subprocess
        for rom, name in ((str(ROM), "original (test ROM)"), (str(out), Path(build).name)):
            subprocess.run([sys.executable, __file__, retail, build, str(n), "--one", rom, name], check=True)
        return
    rom, name = sys.argv[sys.argv.index("--one") + 1], sys.argv[sys.argv.index("--one") + 2]
    if True:
        h = Harness(rom=rom, state=STATE_TOP)
        e = h.e
        rc, rt = rec(CHECKER), rec(TARGET)
        sgn = lambda v: v - 65536 if v > 32767 else v

        def park():
            for k in range(12):
                if k in (CHECKER, TARGET, 11):
                    continue
                e.setw(rec(k), -100 + 18 * k)
                e.setw(rec(k) + 0x14, -230)
                for off in (0x28, 0x2A, 0x2C):
                    e.setw(rec(k) + off, 0)
            e.setw(PUCKC, 0xFFFF)
            e.setw(PUCK, 100)
            e.setw(PUCK + 0x14, -200)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(PUCK + off, 0)

        def place_target():
            e.setw(rt, 0)
            e.setw(rt + 0x14, 60)
            for off in (0x28, 0x2A):
                e.setw(rt + off, 0)

        def run_check(seed=None, maxf=45):
            """The checker 50 below the target at speed, Up held, C pressed: (knocked down?, check-count rise)."""
            e.setw(rt + 0x32, 0)                       # impact: as for a man skating a while (it fades 2 a frame)
            e.setw(rc + 0x32, 0)
            e.setw(rc, 0)
            e.setw(rc + 0x14, 10)
            e.setw(rc + 0x28, 0)
            e.setw(rc + 0x2A, 8000)
            if seed is not None:
                e.setw(SEED, seed & 0xFFFF)
                e.setw(SEED + 2, (seed >> 16) | 1)
            c0 = e.w(TEAM_CHECKS)
            down, prev = False, e.b(rt + 0x5E)
            for f in range(maxf):
                park()
                e.run(1, hold=["UP"] + (["C"] if f < 2 else []))
                cur = e.b(rt + 0x5E)
                down = down or cur > prev                  # a fall sets nopuck to 120: it jumps up
                prev = cur
            return down, e.w(TEAM_CHECKS) - c0

        def wait(frames):
            """The checker taken well away (left on top of the fallen man, every frame of overlap adds to both
            players' impact), the rest parked."""
            for _ in range(frames):
                park()
                e.setw(rc, 80)
                e.setw(rc + 0x14, -120)
                for off in (0x28, 0x2A):
                    e.setw(rc + off, 0)
                e.run(1)

        # the start: the target 2 Weight points heavier than the checker (a person's check then always knocks him down)
        e.unserialize(h.base)
        wc = e.b(rc + 0x67)
        park()
        place_target()
        e.setb(rt + 0x67, wc + 16)
        e.setb(rt + 0x6F, 10)                      # Stickhandling low: no wobble
        e.run(2)
        base = e.serialize()
        down, rise = run_check()
        # the fall's length and the nopuck countdown
        fall_end, frames, f = None, 0, 0
        anims = []
        np0 = None
        while f < 300:
            wait(1)
            f += 1
            a = e.w(rt + 0x58)
            anims.append(a)
            if fall_end is None and a not in FALLS and any(x in FALLS for x in anims):
                fall_end = f
            if np0 is None and e.b(rt + 0x5E) == 0:
                np0 = f
            if fall_end is not None and e.b(rt + 0x5E) == 0:
                break
        print(f"\n{name}: first check knocked him down: {down}, team checks +{rise}; fall animation ends {fall_end} frames "
              f"after the check ended, nopuck reaches 0 after {np0} (the check ran {45} frames, the hit early in it)")
        def hold(x, y, frames, still_target=True):
            """The checker held at (x, y), still, for some frames: the game's y-sorted object list (collisions are
            tested only between neighbours in it) catches up with the move a step a frame."""
            for _ in range(frames):
                park()
                e.setw(rc, x)
                e.setw(rc + 0x14, y)
                for off in (0x28, 0x2A):
                    e.setw(rc + off, 0)
                if still_target:
                    for off in (0x28, 0x2A):
                        e.setw(rt + off, 0)
                e.run(1)

        def recheck(D, seed=None, fresh=False, weight=None, speed=8000):
            """From the state just after the first check: the checker held well away, then 50 below the target (held
            still 8 frames so the sort catches up), contact D frames after the first check ended; burst in as the
            first time. Returns (knocked down?, the check count's rise, nopuck at contact)."""
            e.unserialize(after)
            tx, ty = sgn(e.w(rt)), sgn(e.w(rt + 0x14))
            hold(tx + 80, ty - 150, max(0, D - 18))
            hold(tx, ty - 50, 8)
            if seed is not None:
                e.setw(SEED, seed & 0xFFFF)
                e.setw(SEED + 2, (seed >> 16) | 1)
            if fresh:
                e.setw(CHKED, 0)
                e.setw(CHKED + 2, 0)
            if weight is not None:
                e.setb(rt + 0x67, weight)
            e.setw(rc + 0x2A, speed)
            c0, prev, down, np_at = e.w(TEAM_CHECKS), e.b(rt + 0x5E), False, None
            for f in range(40):
                park()
                for off in (0x28, 0x2A):
                    e.setw(rt + off, 0)
                e.run(1, hold=["UP"] + (["C"] if f < 2 else []))
                if np_at is None and e.w(rc + 0x58) == CHECK_ANIM:
                    np_at = prev
                cur = e.b(rt + 0x5E)
                down = down or cur > prev
                prev = cur
            return down, e.w(TEAM_CHECKS) - c0, np_at

        e.unserialize(base)
        run_check()
        after = e.serialize()
        row = []
        for D in (20, 40, 60, 70, 80, 90, 100, 110, 130, 160):
            down, rise, np = recheck(D)
            row.append(f"{D}: {'DOWN' if down else 'up'} (nopuck {np}, +{rise})")
            breathe()
        print("  the same checker again, about D + 9 frames after the first check ended (the target still 2 heavier: down "
              "whenever FallDown lets it through; the fall animation ends 99 frames after):")
        print("   ", "; ".join(row))
        # equal weights (the knockdown roll): the same pair (recorded by the first, heavy check) against a fresh pair,
        # N seeds, a gentler approach so the roll decides
        for speed in (2000, 4000):
            rep = fresh = 0
            rises = set()
            for k in range(n):
                d1, r1, _ = recheck(160, seed=1000 + 7919 * k, weight=wc, speed=speed)
                d2, r2, _ = recheck(160, seed=1000 + 7919 * k, fresh=True, weight=wc, speed=speed)
                rep += d1
                fresh += d2
                rises |= {r1, r2}
            print(f"  equal weights, approach speed {speed}, after he is up (160 frames on), {n} seeds: the same pair "
                  f"knocked him down {rep} times, a fresh pair {fresh}; check-count rises seen {sorted(rises)}")

if __name__ == "__main__":
    main()
