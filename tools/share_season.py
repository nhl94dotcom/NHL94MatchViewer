"""Make a folder (and a zip of it) that lets someone without the helper see the season stats and watch the games: the
season page and the viewer with only the games chosen, their sprites and sounds, and the rink of their system. No recordings
and no ROMs go in. They unzip it anywhere and open season.html (the pages work from a folder: season.html reads
matches/season.js, the viewer loads matches/<name>.js).

    python tools/share_season.py "<output folder>" <game name pattern> [<pattern> ...]

Patterns match the games' names (2026-10-17_2219_BOS-DAL), with * as a wildcard: "*BOS-DAL" "*DAL-BOS" picks every
Boston-Dallas game. The games come from NHL94_HOME when it is set (the packaged helper's Documents\\NHL94 Viewer), else
the project folder. Run it again after more games to remake the folder and zip. The helper's games list makes the
same from the games ticked there (make_share, behind its "Export to ZIP" button)."""
import fnmatch
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path(os.environ["NHL94_HOME"]) if os.environ.get("NHL94_HOME") else HERE.parent
PAGES = ["season.html", "viewer.html", "helper.html"]
# The rink of each system the games were played on: the picture as the viewer's script (tools/embed_rink.py; the season
# page reads it too, so the PNG stays home) and the bench masks.
RINK_FILES = {"genesis": ["rink_gens.js", "rink_benches.js"], "snes": ["rink_snes.js", "rink_benches_snes.js"]}


def load_match_head(path):
    """The match file's ROM checksum (for its sprites and sounds) and system, read without parsing the whole file."""
    text = path.read_text(encoding="utf-8")
    field = lambda key: (lambda at: json.loads(text[at + len(key) + 3:text.index(",", at)].strip()) if at >= 0 else None)(text.find(f'"{key}":'))
    return field("rom"), field("system") or "genesis"


def season_command():
    """How to run season.py in another process: the packaged helper has no Python, so it runs itself with --season."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--season"]
    return [sys.executable, str(HERE / "season.py")]


def make_share(out, names, source=SOURCE):
    """Make the share folder `out` and its zip (out + ".zip") from the games `names` in `source`. Returns the zip's
    path. Raises ValueError when `out` is a folder that must not be replaced."""
    out = Path(out).resolve()
    if out.exists():
        # Only ever replace an earlier share (or an empty folder): never a folder given by mistake (Documents, the games)
        earlier = (out / "season.html").exists() and (out / "matches" / "season.js").exists() and not (out / "captures").exists()
        if any(out.iterdir()) and not earlier:
            raise ValueError(f"{out} is not empty and is not an earlier share: give a new folder.")
        if out in (source.resolve(), HERE.parent) or source.resolve().is_relative_to(out):
            raise ValueError(f"{out} holds the games themselves: give a new folder.")
        shutil.rmtree(out)
    (out / "matches" / "heat").mkdir(parents=True)
    for page in PAGES:
        if (source / page).exists():
            shutil.copy2(source / page, out / page)
    roms, keys = set(), set()
    for name in names:
        shutil.copy2(source / "matches" / f"{name}.js", out / "matches" / f"{name}.js")
        rom, system = load_match_head(source / "matches" / f"{name}.js")
        roms.add(rom)
        keys.add(f"{system}:{rom}")
    for system in {key.split(":")[0] for key in keys}:
        for page in RINK_FILES.get(system, RINK_FILES["genesis"]):
            if (source / page).exists():
                shutil.copy2(source / page, out / page)
    for folder in ("sprites", "sounds"):
        for rom in roms - {None}:
            src = source / folder / f"{rom}.js"
            if src.exists():
                (out / folder).mkdir(exist_ok=True)
                shutil.copy2(src, out / folder / src.name)
    # The names of these games' ROMs for the season page (NHL94_Classic, SDL16 ...), and nothing else: the helper's
    # names_scan.json lists every ROM file on this computer with its full path (user name included), so it never goes.
    known = json.loads((source / "roms" / "names.json").read_text(encoding="utf-8")) if (source / "roms" / "names.json").exists() else {}
    (out / "roms").mkdir(exist_ok=True)
    (out / "roms" / "names.json").write_text(json.dumps({k: v for k, v in known.items() if k in keys}, indent=1), encoding="utf-8")
    # The season data for just these games: summaries, heat maps and matches/season.js, made in the new folder
    env = dict(os.environ, NHL94_HOME=str(out))
    subprocess.run(season_command(), env=env, check=True, stdout=subprocess.DEVNULL,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for f in ("names_scan.json", "retroarch.json"):  # a ROM it could not name sends romnames scanning this computer
        (out / "roms" / f).unlink(missing_ok=True)
    return Path(shutil.make_archive(str(out), "zip", root_dir=out.parent, base_dir=out.name))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out, patterns = Path(sys.argv[1]).resolve(), sys.argv[2:]
    names = sorted(p.stem for p in (SOURCE / "matches").glob("*.js")
                   if p.name != "season.js" and any(fnmatch.fnmatch(p.stem, pat) for pat in patterns))
    print(f"Games from: {SOURCE}" + ("" if os.environ.get("NHL94_HOME") else "  (the project folder: set NHL94_HOME to use the helper's games)"))
    if not names:
        sys.exit(f"No games in {SOURCE / 'matches'} match {patterns}.")
    try:
        archive = make_share(out, names)
    except ValueError as e:
        sys.exit(str(e))
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"{len(names)} games: {', '.join(names)}")
    print(f"Folder: {out} ({size / 1e6:.0f} MB)\nZip: {archive} ({archive.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
