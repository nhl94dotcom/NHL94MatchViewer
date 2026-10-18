"""Make a folder (and a zip of it) that lets someone without the helper see the season stats and watch the games: the
season page and the viewer with only the games chosen, their sprites and sounds, and the rink pictures. No recordings
and no ROMs go in. They unzip it anywhere and open season.html (the pages work from a folder: season.html reads
matches/season.js, the viewer loads matches/<name>.js).

    python tools/share_season.py "<output folder>" <game name pattern> [<pattern> ...]

Patterns match the games' names (2026-10-17_2219_BOS-DAL), with * as a wildcard: "*BOS-DAL" "*DAL-BOS" picks every
Boston-Dallas game. The games come from NHL94_HOME when it is set (the packaged helper's Documents\\NHL94 Viewer), else
the project folder. Run it again after more games to remake the folder and zip."""
import fnmatch
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path(os.environ["NHL94_HOME"]) if os.environ.get("NHL94_HOME") else HERE.parent
PAGES = ["season.html", "viewer.html", "helper.html", "rink_gens.png", "rink_snes.png", "rink_gens.js", "rink_snes.js",
         "rink_benches.js", "rink_benches_snes.js"]


def load_match_head(path):
    """The match file's ROM checksum (for its sprites and sounds), read without parsing the whole file."""
    text = path.read_text(encoding="utf-8")
    at = text.find('"rom":')
    return json.loads(text[at + 6:text.index(",", at)].strip()) if at >= 0 else None


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out, patterns = Path(sys.argv[1]).resolve(), sys.argv[2:]
    names = sorted(p.stem for p in (SOURCE / "matches").glob("*.js")
                   if p.name != "season.js" and any(fnmatch.fnmatch(p.stem, pat) for pat in patterns))
    if not names:
        sys.exit(f"No games in {SOURCE / 'matches'} match {patterns}.")
    if out.exists():
        shutil.rmtree(out)
    (out / "matches" / "heat").mkdir(parents=True)
    for page in PAGES:
        if (SOURCE / page).exists():
            shutil.copy2(SOURCE / page, out / page)
    roms = set()
    for name in names:
        shutil.copy2(SOURCE / "matches" / f"{name}.js", out / "matches" / f"{name}.js")
        roms.add(load_match_head(SOURCE / "matches" / f"{name}.js"))
    for folder in ("sprites", "sounds"):
        for rom in roms - {None}:
            src = SOURCE / folder / f"{rom}.js"
            if src.exists():
                (out / folder).mkdir(exist_ok=True)
                shutil.copy2(src, out / folder / src.name)
    # ROM names for the season page (no ROMs themselves)
    for f in ("names.json", "names_scan.json"):
        if (SOURCE / "roms" / f).exists():
            (out / "roms").mkdir(exist_ok=True)
            shutil.copy2(SOURCE / "roms" / f, out / "roms" / f)
    # The season data for just these games: summaries, heat maps and matches/season.js, made in the new folder
    env = dict(os.environ, NHL94_HOME=str(out))
    subprocess.run([sys.executable, str(HERE / "season.py")], env=env, check=True, stdout=subprocess.DEVNULL)
    archive = shutil.make_archive(str(out), "zip", root_dir=out.parent, base_dir=out.name)
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"{len(names)} games: {', '.join(names)}")
    print(f"Folder: {out} ({size / 1e6:.0f} MB)\nZip: {archive} ({Path(archive).stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
