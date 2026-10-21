"""Loads every match in the viewer (headless Edge) in several ways and reports script errors: uncaught exceptions in
the console, and the viewer's own "could not run the viewer" report. Every match: the end of the game with the
highlights open and live knowledge on, and a map. A few matches also: every map, the stats tab layout, a turned and
zoomed following camera, the rink picture instead of the overhead rink, and phone width.
python tests/viewer_smoke.py [match names ...]   (default: every match in both game folders)"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402

EDGE = Path(r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
FOLDERS = [ROOT, Path.home() / "Documents" / "NHL94 Viewer"]
MAPS = ["shots", "heat", "turnovers", "passes", "entries", "goalie", "xg"]
FULL = {"capture6_netplay_bos_stl", "2026-10-14_1540_CGY-BOS", "snes_2026-10-15_1755", "capture5_league30",
        "2026-10-16_2018_PHI-VAN", "2026-10-19_0818_ANA-ATL", "capture1"}
NOISE = ("chrome-extension://", "ProtocolLaunch", "DevTools", "Third-party cookie")


def run(folder, query, size="1366,900"):
    with tempfile.TemporaryDirectory() as profile:
        url = (folder / "viewer.html").as_uri() + "?" + query
        p = subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", f"--user-data-dir={profile}", "--enable-logging=stderr",
                            "--v=0", "--virtual-time-budget=15000", f"--window-size={size}", "--dump-dom", url],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    errors = [line for line in p.stderr.splitlines() if "CONSOLE" in line and not any(n in line for n in NOISE)
              and ("Uncaught" in line or "Error" in line or "error" in line)]
    if "This browser could not run the viewer: " in p.stdout.replace("'This browser could not run the viewer: '", ""):
        errors.append("the viewer reported it could not run")
    if "id=\"stage\"" not in p.stdout:
        errors.append("no page")
    return errors


def main(names):
    jobs = []
    for folder in FOLDERS:
        for path in sorted((folder / "matches").glob("*.js")):
            name = path.stem
            if name in ("season",) or name.startswith("_") or (names and name not in names):
                continue
            try:
                m = json.loads(load_js_object(path))
            except Exception as e:
                print(f"{name}: unreadable ({e})")
                continue
            end = round((m["t"][-1] - m["t"][0]) / 1000)
            jobs.append((folder, name, f"match={name}&t={end}&highlights&live&map=shots"))
            jobs.append((folder, name, f"match={name}&t={end // 2}&map=goalie"))
            if name in FULL:
                jobs += [(folder, name, f"match={name}&t={end // 2}&map={mp}") for mp in MAPS]
                jobs += [(folder, name, f"match={name}&t={end // 3}&layout=stats"),
                         (folder, name, f"match={name}&t={end // 3}&rot=135&zoom=2.5&follow"),
                         (folder, name, f"match={name}&t={end // 3}&overhead=0&rot=180"),
                         (folder, name, f"match={name}&t={end // 3}&pane=stats&size=phone")]
    bad = 0
    for folder, name, query in jobs:
        size = "504,900" if "size=phone" in query else "1366,900"
        errors = run(folder, query.replace("&size=phone", ""), size)
        if errors:
            bad += 1
            print(f"FAIL {name} [{query}]")
            for e in errors[:6]:
                print("     " + e[:400])
        else:
            print(f"ok   {name} [{query}]", flush=True)
    print(f"\n{bad} of {len(jobs)} loads had errors")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
