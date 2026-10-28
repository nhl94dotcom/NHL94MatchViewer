"""Entry point of the packaged helper ("NHL94 Helper.exe", built by tools/build_helper.bat).

A single .exe cannot write beside its own files, so games, replays, sprites, ROM copies and settings live in
Documents\\NHL94 Viewer (or wherever NHL94_HOME points). On each start the viewer pages bundled in the .exe are copied
there, so a newer .exe brings a newer viewer. Run from the project folder (python tools/nhl94_helper.py), none of this
applies.
"""
import ctypes
import os
import shutil
import sys
from pathlib import Path

BUNDLED = ("viewer.html", "helper.html", "season.html", "rink_gens.js", "rink_benches.js", "rink_gens.png",
           "rink_snes.js", "rink_benches_snes.js", "rink_snes.png")


def documents():
    """The user's Documents folder (wherever Windows keeps it, OneDrive included)."""
    buf = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:  # CSIDL_PERSONAL
        return Path(buf.value)
    return Path.home() / "Documents"


# The packaged helper also runs itself for work in another process: --export (the live broadcast's converter) and
# --season (a share's season data, in the share's own folder): neither copies the pages or makes the folders.
WORKER = any(flag in sys.argv for flag in ("--export", "--season"))
if getattr(sys, "frozen", False) and not WORKER:
    home = Path(os.environ.get("NHL94_HOME") or documents() / "NHL94 Viewer")
    home.mkdir(parents=True, exist_ok=True)
    os.environ["NHL94_HOME"] = str(home)
    bundle = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    for name in BUNDLED:
        if (bundle / name).exists():
            shutil.copy2(bundle / name, home / name)
    for folder in ("matches", "captures", "sprites", "roms", "shared"):
        (home / folder).mkdir(exist_ok=True)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nhl94_helper  # noqa: E402  (after NHL94_HOME is set)

nhl94_helper.main()
