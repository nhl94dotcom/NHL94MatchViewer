"""Names for ROMs: the file name the player loaded in RetroArch (e.g. "NHL94_Classic", "SDL16"), for the season page,
which otherwise only knows a ROM by its checksum.

A ROM is keyed as the season page keys it: "<system>:<crc32>", the crc32 the converter writes into the match file
(the whole Genesis ROM; the SNES ROM without a copier header). The helper copies only a SNES cartridge's first
megabyte, so a SNES file is keyed both whole and by that first megabyte.

Names come from RetroArch's content history (content_history.lpl, the files loaded, newest first): when the helper
attaches it names the ROM loaded now (`note_loaded`), and `names()` fills in any other ROM by looking through the
folders of the history's files for one with the same checksum. Kept in roms/names.json; the folder scan is cached in
roms/names_scan.json by file size and time.
"""
import json
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from systems.common import ROOT  # noqa: E402

NAMES = ROOT / "roms" / "names.json"
SCAN = ROOT / "roms" / "names_scan.json"
PLACES = ROOT / "roms" / "retroarch.json"  # where RetroArch was last seen
MAX_ROM = 8 * 1024 * 1024  # Genesis and SNES ROMs are 4 MB at most; a .bin this big is another system's disc image
EXTENSIONS = {".bin": "genesis", ".gen": "genesis", ".md": "genesis", ".smc": "snes", ".sfc": "snes"}
CORES = {"genesis": "genesis_plus_gx", "snes": "snes9x"}


def _load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path, data):
    try:
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
        pass


def keys_of(data, system):
    """The season-page keys a ROM file's bytes can have."""
    if system == "snes":
        from systems import snes
        rom = snes.strip_header(data)
        return {f"snes:{zlib.crc32(rom):08x}", f"snes:{zlib.crc32(rom[:0x100000]):08x}"}
    return {f"genesis:{zlib.crc32(data):08x}"}


def retroarch_dirs():
    """RetroArch folders known: where the helper last saw it running, and the one beside the default ROMs."""
    dirs = [Path(p) for p in _load(PLACES, [])]
    try:
        from systems import genesis
        dirs.append(genesis.DEFAULT_ROM.parents[2])
    except Exception:
        pass
    return [d for i, d in enumerate(dirs) if d.exists() and d not in dirs[:i]]


def history(ra_dir):
    """The content history's items (path, core path), newest first."""
    path = ra_dir / "content_history.lpl"
    try:
        for line in (ra_dir / "retroarch.cfg").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("content_history_path"):
                value = line.split("=", 1)[1].strip().strip('"')
                if value and value != "default":
                    path = ra_dir / value[2:] if value.startswith(":\\") or value.startswith(":/") else Path(value)
    except OSError:
        pass
    items = _load(path, {}).get("items", [])
    return [(Path(i.get("path", "")), i.get("core_path", "")) for i in items if i.get("path")]


def note_loaded(pid, system, dump_path):
    """The helper attached to RetroArch (process pid) with a game loaded and copied it to dump_path: name that ROM
    after the newest history entry for this system's core whose file has the same checksum."""
    try:
        from systems import process
        exe = process.process_path(pid)
        if exe:
            places = [str(Path(exe).parent)] + [p for p in _load(PLACES, []) if p != str(Path(exe).parent)]
            _save(PLACES, places[:4])
        if not dump_path or not Path(dump_path).exists():
            return None
        want = keys_of(Path(dump_path).read_bytes(), system)
        for ra in retroarch_dirs():
            for path, core in history(ra):
                if CORES[system] not in core.lower().replace("-", "_") or not path.is_file() or path.stat().st_size > MAX_ROM:
                    continue
                if want & keys_of(path.read_bytes(), system):
                    names = _load(NAMES, {})
                    for key in want:
                        names[key] = path.stem
                    _save(NAMES, names)
                    return path.stem
    except Exception as e:  # a name is a nicety: never let it stop the helper
        print(f"(Could not name the ROM: {e})", file=sys.stderr)
    return None


def names(wanted=()):
    """{key: name} for every ROM named so far, plus any of `wanted` found in the folders of the history's files."""
    out = _load(NAMES, {})
    missing = [k for k in wanted if k not in out]
    if not missing:
        return out
    scan = _load(SCAN, {})
    folders = []
    for ra in retroarch_dirs():
        folders += [path.parent for path, _ in history(ra)]
        folders += [ra / "ROMs" / "Genesis", ra / "ROMs" / "SNES"]
    seen = set()
    for folder in folders:
        if folder in seen or not folder.exists():
            continue
        seen.add(folder)
        for path in sorted(folder.iterdir()):
            system = EXTENSIONS.get(path.suffix.lower())
            if not system or not path.is_file() or path.stat().st_size > MAX_ROM:
                continue
            stat = path.stat()
            entry = scan.get(str(path))
            if not entry or entry["size"] != stat.st_size or entry["time"] != stat.st_mtime:
                try:
                    entry = scan[str(path)] = {"size": stat.st_size, "time": stat.st_mtime, "keys": sorted(keys_of(path.read_bytes(), system))}
                except OSError:
                    continue
            for key in entry["keys"]:
                out.setdefault(key, path.stem)  # names the helper saw loaded stay first
    _save(SCAN, scan)
    return out
