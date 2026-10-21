"""The crowd meter's hidden effects, measured in the recordings (2026-10-21).
- SNES: the code meant to raise four of every player's hot / cold bytes by 2 at 110 dB (HotColdRaised $19CE nonzero) is
  never called; checks it stays 0 (CurCrowdMeter $19C2).
- Genesis: while the meter (CurCrowdMeter $C30E) is at or above the arena's record (CrowdRecord $C310) the game sets
  sflags7 bit 6 ($C2FC; bset on the word's address: its high byte, $4000), and every computer player's reaction timer runs a frame shorter (GENESIS_MECHANICS 14.3).
  Recorded only since 2026-10-17 (the helper's $C2E0 block).
python analysis/crowd_study.py"""
import sys
from pathlib import Path

sys.path.insert(0, "tools")
import systems  # noqa: E402
from export_match import Capture  # noqa: E402

FOLDERS = [Path("captures"), Path.home() / "Documents" / "NHL94 Viewer" / "captures"]
SNES_METER, SNES_RAISED = 0x19C2, 0x19CE
GEN_FLAGS7, GEN_METER, GEN_RECORD = 0xC2FC, 0xC30E, 0xC310


def recordings():
    seen = set()
    for folder in FOLDERS:
        for cap in sorted(folder.glob("*")):
            if cap.name in seen or cap.name.startswith("_") or not (cap / "capture.json").exists():
                continue
            if not (cap.parent.parent / "matches" / f"{cap.name}.js").exists():
                continue
            seen.add(cap.name)
            yield cap


def main():
    rows = []
    for cap_dir in recordings():
        system = systems.of_capture(cap_dir)
        try:
            cap = Capture(cap_dir, system)
        except Exception as e:  # noqa: BLE001
            print("skip", cap_dir.name, e)
            continue
        if system.NAME == "snes":
            if cap.offset(SNES_METER) is None:
                continue
            meter = [cap.word(i, SNES_METER) for i in range(cap.count)]
            on = [cap.word(i, SNES_RAISED) != 0 for i in range(cap.count)]
        else:
            if cap.offset(GEN_METER) is None:
                continue  # recorded before the flags block was kept
            meter = [cap.word(i, GEN_METER) for i in range(cap.count)]
            record = [cap.word(i, GEN_RECORD) for i in range(cap.count)]
            on = [bool(cap.word(i, GEN_FLAGS7) & 0x4000) for i in range(cap.count)]  # bset #6 on the word: its high byte
        ms = [cap.ms(i) for i in range(cap.count)]
        total = ms[-1] - ms[0]
        spells, start = [], None
        for i, v in enumerate(on):
            if v and start is None:
                start = i
            elif not v and start is not None:
                spells.append((start, i))
                start = None
        if start is not None:
            spells.append((start, len(on) - 1))
        time_on = sum(ms[b] - ms[a] for a, b in spells)
        rows.append({"system": system.NAME, "game": cap_dir.name, "minutes": total / 60000, "on": time_on / 60000,
                     "spells": len(spells), "max_meter": max(meter), "median_meter": sorted(meter)[len(meter) // 2],
                     "record": (record[-1] if system.NAME == "genesis" else None)})
    for s in ("genesis", "snes"):
        sel = [r for r in rows if r["system"] == s]
        if not sel:
            continue
        mins = sum(r["minutes"] for r in sel)
        on = sum(r["on"] for r in sel)
        print(f"\n== {s}: {len(sel)} recordings, {mins:.0f} minutes; the effect on {on:.1f} min ({100 * on / mins:.1f}%), "
              f"{sum(r['spells'] for r in sel)} spells")
        for r in sel:
            print(f"   {r['game']:28} {r['minutes']:5.1f} min, on {r['on'] * 60:5.0f} s in {r['spells']:2} spells, meter median {r['median_meter']} max {r['max_meter']}"
                  + (f", arena record {r['record']}" if r["record"] is not None else ""))


if __name__ == "__main__":
    main()
