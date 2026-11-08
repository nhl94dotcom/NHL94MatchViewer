r"""Re-convert the recordings after a converter change (2026-11-08, the user: re-converting the library took a while).

Every recording that already has a match file (other capture folders are tests or pieces of merged games), in one
process per game folder: export_match with its cached read (read_cache.json.gz beside each recording: only the
analysis runs again unless the recording-reading code changed), the game list updated, and the season rebuilt once at
the end instead of after every game. Gentle: idle priority, resting as long as it works (analysis/scoring_map/
lowload.py; --full-speed: no rests).

python tools/reconvert.py                       both game folders: the project's and Documents\NHL94 Viewer
python tools/reconvert.py --home DIR            one folder
  --no-cache     read every recording again (and don't keep the reads)
  --full-speed   no rests (still idle priority)
  --only NAME    just the matches whose names contain NAME (repeatable)"""
import argparse
import contextlib
import io
import os
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent


def one_home(args):
    sys.path.insert(0, str(TOOLS))
    sys.path.insert(0, str(PROJECT / "analysis" / "scoring_map"))
    if args.full_speed:
        os.environ["NHL94_SMAP_DUTY"] = "1"
    import lowload
    import export_match
    import nhl94_helper as H
    from systems.common import ROOT
    lowload.gentle()
    names = sorted(p.stem for p in (ROOT / "matches").glob("*.js")
                   if p.stem != "season" and not p.name.endswith(".heat.js") and (ROOT / "captures" / p.stem).is_dir())
    if args.only:
        names = [n for n in names if any(o in n for o in args.only)]
    print(f"{ROOT}: {len(names)} recordings", flush=True)
    t0, failed, hits = time.perf_counter(), [], 0
    for i, name in enumerate(names, 1):
        start = time.perf_counter()
        folder = ROOT / "captures" / name
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                export_match.main([str(folder)] + (["--no-cache"] if args.no_cache else []))
            with H.index_lock:
                old = next((g for g in H.load_index() if g["name"] == name), None)
                games = [g for g in H.load_index() if g["name"] != name]
                games.append(H.game_entry(name, old and old.get("date")))
                H.save_index(games)
            hit = getattr(export_match.cached_read, "hit", False)
            hits += hit
            print(f"  {i:3d}/{len(names)} {name:34s} {time.perf_counter() - start:5.1f} s{'  (read cached)' if hit else ''}",
                  flush=True)
        except (Exception, SystemExit) as e:
            failed.append(name)
            print(f"  {i:3d}/{len(names)} {name:34s} FAILED: {e}", flush=True)
        lowload.breathe()
    start = time.perf_counter()
    H.update_season()
    print(f"season rebuilt in {time.perf_counter() - start:.1f} s; {len(names) - len(failed)} converted "
          f"({hits} from cached reads), {len(failed)} failed, {time.perf_counter() - t0:.0f} s in all", flush=True)
    for name in failed:
        print("FAILED", name)
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home", type=Path)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--full-speed", action="store_true")
    ap.add_argument("--only", action="append")
    args = ap.parse_args()
    if args.home:
        os.environ["NHL94_HOME"] = str(args.home.resolve())
        return one_home(args)
    rc = 0
    for home in (PROJECT, Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents" / "NHL94 Viewer"):
        if not (home / "matches").is_dir():
            continue
        extra = [a for a in sys.argv[1:]]
        rc |= subprocess.run([sys.executable, str(Path(__file__).resolve()), "--home", str(home)] + extra).returncode
    return rc


if __name__ == "__main__":
    sys.exit(main())
