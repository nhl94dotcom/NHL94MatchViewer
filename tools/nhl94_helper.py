"""NHL '94 Helper: records games played in RetroArch on its own, converts them, and lists them on a local page.

Start it by hand (python tools/nhl94_helper.py, or the shortcut) and leave it running while you play. It
- waits for RetroArch with NHL '94 loaded (Genesis Plus GX core);
- starts recording at a game's opening faceoff, records only live play (the game's screen value, $FFF7, is 0: not the
  menus, the pause menu or the instant replay, which animates the players' frames without moving them), and stops at
  the final horn (the period index past the third with the clock at 0), when the game goes back to the menus, or
  when RetroArch closes;
- converts the game (tools/export_match.py), named by date, time and teams, and makes a shareable game file if that
  setting is on;
- serves this folder at http://localhost:9494/ (only to this computer): helper.html lists the games, with the viewer.

Recordings are gzipped (fast.bin.gz, full.bin.gz), with pauses left out of the timeline. The ROM is copied out of the
emulator into roms/ (named by its fingerprint) for the converter, so no ROM folder needs setting up.
See CLAUDE.md, "Game states (for the helper)".
"""
import datetime
import gzip
import http.server
import json
import os
import shutil
import struct
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import webbrowser
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nhl94_memory import Emulator  # noqa: E402

# Where games, replays, sprites and settings live: the project folder, or NHL94_HOME (the packaged helper sets it to
# a folder in Documents, since a single .exe cannot write beside its own files).
ROOT = Path(os.environ["NHL94_HOME"]) if os.environ.get("NHL94_HOME") else Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("NHL94_PORT") or 9494)  # NHL94_PORT: another port, e.g. for testing beside a running helper
SETTINGS_FILE = ROOT / "helper_settings.json"
INDEX_FILE = ROOT / "matches" / "games.json"

BLOCKS = [(0xB000, 0x1000), (0xC400, 0xA00)]  # what each sample keeps, as tools/nhl94_record.ps1 does
SCREEN = 0xFFF7          # 0 = the game itself; 15 menus; 80 pause menu; 100 instant replay
PERIOD, CLOCK = 0xC466, 0xC468
HOME_SCORE, AWAY_SCORE = 0xC6DA, 0xCA3E
HOME_TEAM, AWAY_TEAM = 0xC6F7, 0xCA5B
RECORDS, RECORD_SIZE, ROSTER = 0xB04A, 0x80, 0x66
MENUS = (1, 15)
# full.bin.gz holds all of RAM now and then, for research only: the converter does not need it (converting
# 2026-10-14_1540_CGY-BOS without it gives an identical match), so every 10 s rather than every second.
SAMPLE_S, FULL_EVERY_S = 0.015, 10.0
MIN_GAME_S = 45          # shorter recordings (a few seconds of play, then back to the menus) are not kept
FINAL_WAIT_S = 3.0       # keep recording this long after the final horn

try:  # Windows sleeps in 15.6 ms steps unless asked for 1 ms
    import ctypes
    ctypes.windll.winmm.timeBeginPeriod(1)
except Exception:
    pass


# ---------------------------------------------------------------------------------------------------------- settings
def load_settings():
    settings = {"auto_game_file": False, "open_browser": True}
    try:
        settings.update(json.loads(SETTINGS_FILE.read_text()))
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))


# ------------------------------------------------------------------------------------------------------------ index
index_lock = threading.Lock()


def load_index():
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def save_index(games):
    INDEX_FILE.parent.mkdir(exist_ok=True)
    INDEX_FILE.write_text(json.dumps(sorted(games, key=lambda g: g.get("date", ""), reverse=True), indent=1), encoding="utf-8")


def game_entry(name, date=None):
    """What the game list shows about a converted match, read from matches/<name>.js."""
    path = ROOT / "matches" / f"{name}.js"
    text = path.read_text(encoding="utf-8")
    m = json.loads(text[text.index("{"):text.rindex("}") + 1])
    score = m.get("score", [0, 0])
    shared = sorted((ROOT / "shared").glob(f"*{name}.html")) if (ROOT / "shared").exists() else []
    return {
        "name": name,
        "date": date or datetime.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="minutes"),
        "home": m.get("team1"), "away": m.get("team2"), "abbr": m.get("abbr"),
        "score": [score[-2], score[-1]] if len(score) >= 2 else [0, 0],
        "periods": max(m.get("period", [0])) + 1 if m.get("period") else 0,
        "seconds": round((m["t"][-1] - m["t"][0]) / 1000) if m.get("t") else 0,
        "gameFile": shared[-1].name if shared else None,
    }


def refresh_index():
    """Add any match files the list does not know yet (older recordings, ones converted by hand)."""
    with index_lock:
        games = {g["name"]: g for g in load_index()}
        for path in sorted((ROOT / "matches").glob("*.js")):
            if path.stem not in games:
                try:
                    games[path.stem] = game_entry(path.stem)
                except Exception:
                    continue
        for name in list(games):
            if not (ROOT / "matches" / f"{name}.js").exists():
                del games[name]
        save_index(list(games.values()))


# --------------------------------------------------------------------------------------------------------- the state
class Status:
    def __init__(self):
        self.lock = threading.Lock()
        self.state, self.detail, self.game = "starting", "", None
        self.log = []

    def set(self, state, detail="", game=None, say=True):
        with self.lock:
            changed = (state, detail) != (self.state, self.detail)
            self.state, self.detail, self.game = state, detail, game
            if changed and say:
                line = f"{datetime.datetime.now():%H:%M:%S}  {detail or state}"
                print(line, flush=True)
                self.log = (self.log + [line])[-40:]

    def snapshot(self):
        with self.lock:
            return {"state": self.state, "detail": self.detail, "game": self.game, "log": self.log[-12:]}


status = Status()


# --------------------------------------------------------------------------------------------------------------- ROM
team_cache = {}


def dump_rom(emu):
    """Copy the cartridge out of the emulator into roms/<fingerprint>.bin (once per ROM); its path, or None."""
    fp = emu.rom_fingerprint()
    if not fp:
        return None, None
    path = ROOT / "roms" / f"{fp[0]}_{fp[1]}.bin"
    if not path.exists():
        header = emu._raw(emu.handle, emu.rom + 0x1A0, 8)
        if not header:
            return None, fp
        swapped = bytes(header[i ^ 1] for i in range(8))
        start, end = struct.unpack(">II", swapped)
        size = min(max(end + 1, 0x100000), 0x400000)
        data = emu._raw(emu.handle, emu.rom, size)
        if not data:
            return None, fp
        rom = bytearray(size)
        rom[0::2], rom[1::2] = data[1::2], data[0::2]
        if zlib.crc32(bytes(rom[:0x100000])) != int(fp[0], 16):
            return None, fp
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(bytes(rom))
    return path, fp


def team_abbreviations(rom_path, home, away):
    """('BOS', 'STL') for the team indices, from the ROM; falls back to the numbers."""
    try:
        if rom_path not in team_cache:
            import export_match
            team_cache[rom_path] = export_match.read_teams(rom_path)
        teams = team_cache[rom_path]
        return [teams[i].get("abbr") or teams[i]["name"] for i in (home, away)]
    except Exception:
        return [f"T{home}", f"T{away}"]


# --------------------------------------------------------------------------------------------------------- recording
def word(block, offset):
    return struct.unpack_from("<H", block, offset)[0]


class View:
    """What the game is doing, from one read of the blocks we record plus the screen byte."""

    def __init__(self, emu):
        self.blocks = [emu.read(start, length) for start, length in BLOCKS]
        screen = emu.read(SCREEN ^ 1, 1)
        if any(b is None for b in self.blocks) or screen is None:
            raise ConnectionError("the emulator went away")
        self.screen = screen[0]
        a, c = self.blocks
        self.period, self.clock = word(c, PERIOD - 0xC400), word(c, CLOCK - 0xC400)
        self.score = (word(c, HOME_SCORE - 0xC400), word(c, AWAY_SCORE - 0xC400))
        self.teams = (c[(HOME_TEAM ^ 1) - 0xC400], c[(AWAY_TEAM ^ 1) - 0xC400])
        rosters = [a[((RECORDS + RECORD_SIZE * k + ROSTER) ^ 1) - 0xB000] for k in range(12)]
        self.on_ice = any(r != 0xFF for r in rosters[:6]) and any(r != 0xFF for r in rosters[6:])

    @property
    def live(self):
        return self.screen == 0 and self.on_ice

    def describe(self):
        return f"P{min(self.period, 2) + 1} {self.clock // 60}:{self.clock % 60:02d}, {self.score[0]}-{self.score[1]}"


class Recording:
    def __init__(self, emu, view, rom_path, fingerprint):
        self.emu, self.rom_path = emu, rom_path
        when = datetime.datetime.now()
        abbr = team_abbreviations(rom_path, *view.teams) if rom_path else [f"T{t}" for t in view.teams]
        self.teams = abbr
        self.name = f"{when:%Y-%m-%d_%H%M}_{abbr[0]}-{abbr[1]}".replace(" ", "")
        self.date = when.isoformat(timespec="minutes")
        self.folder = ROOT / "captures" / self.name
        self.folder.mkdir(parents=True, exist_ok=True)
        layout = {"blocks": [list(b) for b in BLOCKS], "recorded_by": "nhl94_helper"}
        if fingerprint:
            layout["rom_crc32"] = fingerprint
        (self.folder / "capture.json").write_text(json.dumps(layout))
        self.fast = gzip.open(self.folder / "fast.bin.gz", "wb", compresslevel=3)
        self.full = gzip.open(self.folder / "full.bin.gz", "wb", compresslevel=3)
        self.live_ms, self.last_wall, self.last_full = 0.0, time.perf_counter(), -1e9
        self.previous, self.samples = None, 0
        self.view, self.final_since, self.menu_since, self.joined_mid_game = view, None, None, not (view.period == 0 and view.clock >= 290)

    def step(self, view):
        """One sample. Returns why it ended ('final', 'menus', 'new game') or None to carry on."""
        now = time.perf_counter()
        elapsed, self.last_wall = (now - self.last_wall) * 1000, now
        old = self.view
        if view.screen in MENUS:
            self.menu_since = self.menu_since or now
            if now - self.menu_since > 3:
                return "menus"
            return None
        self.menu_since = None
        # A new game started without the old one finishing (the clock going back up within a period, other than to
        # start a period).
        if view.live and (view.period < old.period or (view.period == old.period == 0 and view.clock > old.clock + 5 and old.clock != 0)):
            return "new game"
        # The final horn: past the third period with the clock at 0 (and not tied, or later still). Checked whatever
        # the screen shows, in case the game takes the players off at the horn.
        if view.screen == 0:
            over = view.clock == 0 and (view.period >= 4 or (view.period >= 3 and view.score[0] != view.score[1]))
            if over:
                self.view = view
                self.final_since = self.final_since or now
                if now - self.final_since >= FINAL_WAIT_S:
                    return "final"
            else:
                self.final_since = None
        if not view.live:
            return None  # paused, instant replay, or between screens: not recorded, and not counted as game time
        self.live_ms += elapsed
        self.view = view
        data = b"".join(view.blocks)
        if data != self.previous:
            self.fast.write(struct.pack("<q", round(self.live_ms)) + data)
            self.previous, self.samples = data, self.samples + 1
        if now - self.last_full >= FULL_EVERY_S:
            full = self.emu.read(0, 0x10000)
            if full:
                self.full.write(struct.pack("<q", round(self.live_ms)) + full)
            self.last_full = now
        return None

    def close(self):
        self.fast.close()
        self.full.close()


def convert(rec, why):
    """Convert a finished recording (in the background), add it to the list, and make its game file if wanted."""
    try:
        if rec.live_ms / 1000 < MIN_GAME_S and rec.view.score == (0, 0):
            shutil.rmtree(rec.folder, ignore_errors=True)
            status.set("idle", f"Discarded a short recording ({rec.live_ms / 1000:.0f} s of play)")
            return
        status.set("converting", f"Converting {rec.name} ({why})")
        args = [str(rec.folder)] + (["--rom", str(rec.rom_path)] if rec.rom_path else [])
        if getattr(sys, "frozen", False):
            # The packaged helper has no Python to run the converter with: run it here.
            import export_match
            try:
                export_match.main(args)
            except SystemExit as e:
                if e.code:
                    status.set("idle", f"Could not convert {rec.name}: {e.code}")
                    return
        else:
            command = [sys.executable, str(Path(__file__).resolve().parent / "export_match.py")] + args
            result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
            if result.returncode != 0:
                status.set("idle", f"Could not convert {rec.name}: {(result.stderr or result.stdout).strip().splitlines()[-1:]}")
                return
        settings = load_settings()
        if settings.get("auto_game_file"):
            import share_game
            share_game.make_game_file(rec.name)
        with index_lock:
            games = [g for g in load_index() if g["name"] != rec.name]
            games.append(game_entry(rec.name, rec.date))
            save_index(games)
        s = rec.view.score
        status.set("idle", f"Saved {rec.name}: {rec.teams[0]} {s[0]}-{s[1]} {rec.teams[1]}")
    except Exception as e:
        status.set("idle", f"Could not convert {rec.name}: {e}")
        traceback.print_exc()


def watch():
    """The main loop: wait for the emulator and a game, record it, hand it over, and again."""
    emu = None
    while True:
        try:
            if emu is None:
                emu = Emulator.attach()
                if emu is None:
                    status.set("waiting", "Waiting for RetroArch with NHL '94 loaded")
                    time.sleep(2)
                    continue
                rom_path, fingerprint = dump_rom(emu)
            view = View(emu)
            if not view.live:
                status.set("ready", "NHL '94 is running; waiting for a game to start")
                time.sleep(0.25)
                continue
            rec = Recording(emu, view, rom_path, fingerprint)
            status.set("recording", f"Recording {rec.teams[0]} vs {rec.teams[1]}" + (" (joined during the game)" if rec.joined_mid_game else ""),
                       {"name": rec.name, "teams": rec.teams})
            why = None
            try:
                next_sample = time.perf_counter()
                while why is None:
                    view = View(emu)
                    why = rec.step(view)
                    status.set("recording", f"Recording {rec.teams[0]} vs {rec.teams[1]}", {
                        "name": rec.name, "teams": rec.teams, "score": list(rec.view.score), "clock": rec.view.describe(),
                        "seconds": round(rec.live_ms / 1000), "paused": view.screen != 0}, say=False)
                    next_sample += SAMPLE_S
                    time.sleep(max(0.0, next_sample - time.perf_counter()))
            except ConnectionError:
                why = "RetroArch closed"
                emu = None
            finally:
                rec.close()
            threading.Thread(target=convert, args=(rec, why), daemon=True).start()
            if why == "final":
                # Wait for this game to be left behind (the menus, or a new game) before looking for the next one.
                while emu is not None:
                    try:
                        v = View(emu)
                    except ConnectionError:
                        emu = None
                        break
                    if v.screen in MENUS or (v.live and v.period == 0 and v.clock > 0 and v.score == (0, 0)):
                        break
                    time.sleep(0.5)
        except ConnectionError:
            emu = None
        except Exception:
            traceback.print_exc()
            emu = None
            time.sleep(2)


# -------------------------------------------------------------------------------------------------------- web page
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass  # quiet

    def send_json(self, data, code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/helper.html")
            self.end_headers()
        elif url.path == "/api/state":
            self.send_json({**status.snapshot(), "settings": load_settings(), "games": load_index()})
        else:
            super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(url.query)
        name = (query.get("name") or [""])[0]
        if name and not all(ch.isalnum() or ch in "_-" for ch in name):
            return self.send_json({"error": "bad name"}, 400)
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}") if length else {}
        if url.path == "/api/settings":
            settings = load_settings()
            settings.update({k: bool(v) for k, v in body.items() if k in ("auto_game_file", "open_browser")})
            save_settings(settings)
            return self.send_json(settings)
        if url.path == "/api/game-file" and name:
            import share_game
            path = share_game.make_game_file(name)
            with index_lock:
                games = load_index()
                for g in games:
                    if g["name"] == name:
                        g["gameFile"] = path.name
                save_index(games)
            return self.send_json({"file": "shared/" + path.name})
        if url.path == "/api/delete" and name:
            with index_lock:
                save_index([g for g in load_index() if g["name"] != name])
            shutil.rmtree(ROOT / "captures" / name, ignore_errors=True)
            for path in [ROOT / "matches" / f"{name}.js", *((ROOT / "shared").glob(f"*{name}.html") if (ROOT / "shared").exists() else [])]:
                try:
                    path.unlink()
                except OSError:
                    pass
            return self.send_json({"deleted": name})
        self.send_json({"error": "unknown"}, 404)


def convert_folder(folder):
    """Convert a recording folder by hand (--convert <folder>): for re-converting after an update, and for testing the
    packaged helper's built-in converter."""
    import export_match
    folder = Path(folder).resolve()
    export_match.main([str(folder)])
    with index_lock:
        games = [g for g in load_index() if g["name"] != folder.name]
        games.append(game_entry(folder.name))
        save_index(games)
    print(f"Converted {folder.name}")


class Server(http.server.ThreadingHTTPServer):
    """Claims the port for itself: by default Windows lets a second helper listen on the same port, and the page then
    reaches whichever it likes."""
    allow_reuse_address = False

    def server_bind(self):
        import socket
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class Tee:
    """Writes what the window shows to helper_log.txt too, so a tester can send it back."""
    def __init__(self, stream, log):
        self.stream, self.log = stream, log

    def write(self, text):
        self.log.write(text)
        self.log.flush()
        return self.stream.write(text) if self.stream else len(text)

    def flush(self):
        if self.stream:
            self.stream.flush()


def keep_log():
    path = ROOT / "helper_log.txt"
    try:
        if path.exists() and path.stat().st_size > 2_000_000:
            path.unlink()  # start afresh rather than grow forever
        log = open(path, "a", encoding="utf-8")
    except OSError:
        return
    log.write(f"\n==== {datetime.datetime.now():%Y-%m-%d %H:%M:%S}, Windows {sys.getwindowsversion().build}, Python {sys.version.split()[0]}"
              f"{' (packaged)' if getattr(sys, 'frozen', False) else ''}\n")
    sys.stdout, sys.stderr = Tee(sys.stdout, log), Tee(sys.stderr, log)


def main():
    if "--convert" in sys.argv:
        return convert_folder(sys.argv[sys.argv.index("--convert") + 1])
    print("NHL '94 Helper. Leave this window open while you play; close it to stop.", flush=True)
    refresh_index()
    try:
        server = Server(("127.0.0.1", PORT), Handler)
    except OSError:
        print(f"The helper is already running (port {PORT} is taken). Use that window, or close it and start again.", flush=True)
        try:
            input("Press Enter to close.")
        except EOFError:
            pass
        return
    keep_log()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    page = f"http://localhost:{PORT}/helper.html"
    print(f"Your games: {page}", flush=True)
    if load_settings().get("open_browser", True) and "--no-browser" not in sys.argv:
        webbrowser.open(page)
    try:
        watch()
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
