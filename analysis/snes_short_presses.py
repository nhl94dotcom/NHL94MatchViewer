"""SNES: button presses the game never saw (2026-11-13, NOSE4Web's question after the B trace).

The retail game reads the pads once per Gameloop pass (ReadPads -> GetNewPresses: padnew1 = PadRaw & (PadRaw ^
padlast1)), a pass every d7 frames (2 normally, more when it lags), while Multi5Bios writes PadRaw1-5 in the NMI every
frame. A press that starts and ends between two passes never reaches padnew1; nor does a release that ends between two
passes (the button looks held throughout, so the next press isn't new).

The SNES recordings keep the frame counter Vcount ($83, +1 per NMI), OldVcount ($0D01, the frame of the last pass),
timestep ($0ADB, that pass's d7), PadRaw1 / PadRaw2 ($0776 / $0778) and padnew1 ($0AB8), sampled about 60 times a second
(a sample written only when the RAM changed). So:
- passes: every OldVcount seen, and the d7 of each (timestep);
- each press of a button in PadRaw (a rising edge): its frames by Vcount (first frame seen held to first frame seen
  released; the sampler sees about one frame in each, so lengths are good to about a frame);
- predicted lost: no pass frame inside the press, with the passes around it all seen (gaps of no more than their d7);
- registered: padnew1 had the bit from its start to 70 ms after its end. On the person's own pad this checks the
  prediction; the other pad in a netplay game is the remote player's, predicted and rolled back by RetroArch, so its
  padnew1 can disagree with what was finally played (only the prediction is used there).
By button (B, Y, A, X, L, R) and by press length in frames.

python analysis/snes_short_presses.py [CAPTURE ...]   (default: every SNES recording in <home>/captures)"""
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from export_match import Capture  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
VCOUNT, OLDV, TIMESTEP, PADRAW, PADNEW = 0x0083, 0x0D01, 0x0ADB, 0x0776, 0x0AB8
BUTTONS = {"B": 0x8000, "Y": 0x4000, "A": 0x0080, "X": 0x0040, "L": 0x0020, "R": 0x0010}
AFTER_MS = 70


def study(cap):
    n = cap.count
    ms = [cap.ms(i) for i in range(n)]
    vc = [cap.word(i, VCOUNT) for i in range(n)]
    ov = [cap.word(i, OLDV) for i in range(n)]
    steps = Counter(cap.word(i, TIMESTEP) for i in range(1, n) if ov[i] != ov[i - 1])
    rows = []
    for pad in (0, 1):
        raw = [cap.word(i, PADRAW + 2 * pad) for i in range(n)]
        new = [cap.word(i, PADNEW + 2 * pad) for i in range(n)]
        for name, bit in BUTTONS.items():
            i, last_end = 1, None
            while i < n:
                if raw[i] & bit and not raw[i - 1] & bit:
                    j = i
                    while j < n and raw[j] & bit:
                        j += 1
                    a, b = vc[i], (vc[j] if j < n else vc[-1])          # held from frame a, released by frame b
                    length = (b - a) & 0xFFFF
                    if 0 < length < 600:
                        # the passes seen in the samples around the press (Vcount restarts during a game, so only
                        # the nearby samples' OldVcount values belong to this stretch)
                        local = sorted({ov[k] for k in range(max(0, i - 12), min(n, j + 12))})
                        inside = any(0 <= ((p - a) & 0xFFFF) < length for p in local)
                        near = [p for p in local if -8 <= ((p - a + 0x8000) & 0xFFFF) - 0x8000 <= length + 8]
                        judged = len(near) >= 2 and max(((q - p) & 0xFFFF) for p, q in zip(near, near[1:])) <= 4
                        # the release before it: if no pass fell inside it, the game saw the button held throughout
                        # and this press isn't new to it
                        rel = (a - vc[last_end]) & 0xFFFF if last_end is not None else 9999
                        rel_lost = rel < 8 and not any(0 <= ((p - vc[last_end]) & 0xFFFF) < rel for p in local)
                        end_ms = ms[j] if j < n else ms[-1]
                        seen = any(new[k] & bit for k in range(i, n) if ms[k] <= end_ms + AFTER_MS)
                        rows.append({"pad": pad, "button": name, "frames": length, "judged": judged,
                                     "short": judged and not inside, "release": judged and rel_lost,
                                     "predicted_lost": judged and (not inside or rel_lost), "registered": seen})
                    last_end, i = j if j < n else n - 1, j
                else:
                    i += 1
    return rows, steps


def main():
    caps = sys.argv[1:] or sorted(p.name for p in (HOME / "captures").iterdir()
                                  if (p / "capture.json").exists()
                                  and json.loads((p / "capture.json").read_text()).get("system") == "snes")
    allrows, steps, games = [], Counter(), 0
    for name in caps:
        try:
            rows, st = study(Capture(HOME / "captures" / name))
        except Exception as ex:
            print(name, "unreadable:", ex)
            continue
        games += 1
        allrows += rows
        steps += st
        time.sleep(0.2)
    tot = sum(steps.values())
    print(f"{games} SNES recordings. Game passes by d7 (frames since the last): "
          + ", ".join(f"{k}: {100 * v / tot:.1f}%" for k, v in sorted(steps.items()) if v / tot > 0.001))
    j = [r for r in allrows if r["judged"]]
    print(f"\nPresses judged (the passes around them seen): {len(j)} of {len(allrows)}")
    print("button | presses | 1 frame | 2 frames | 3 frames | lost: press between passes | lost: release between passes"
          " | lost (share)")
    for name in BUTTONS:
        rs = [r for r in j if r["button"] == name]
        if not rs:
            continue
        c = Counter(min(r["frames"], 4) for r in rs)
        lost = sum(r["predicted_lost"] for r in rs)
        print(f"{name:6s} | {len(rs)} | {c[1]} | {c[2]} | {c[3]} | {sum(r['short'] for r in rs)} | "
              f"{sum(r['release'] and not r['short'] for r in rs)} | {lost} ({100 * lost / len(rs):.2f}%)")
    p1 = [r for r in j if r["pad"] == 0]
    agree = Counter((r["predicted_lost"], r["registered"]) for r in p1)
    print("\nPad 1 check (prediction against padnew1): predicted lost & not registered "
          f"{agree[(True, False)]}, predicted lost but registered {agree[(True, True)]}, predicted seen & registered "
          f"{agree[(False, True)]}, predicted seen but not registered {agree[(False, False)]}")


if __name__ == "__main__":
    main()
