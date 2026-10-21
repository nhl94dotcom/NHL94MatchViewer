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
See docs/PROJECT_NOTES.md, "Game states (for the helper)".
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
import systems  # noqa: E402

# Where games, replays, sprites and settings live: the project folder, or NHL94_HOME (the packaged helper sets it to
# a folder in Documents, since a single .exe cannot write beside its own files).
ROOT = Path(os.environ["NHL94_HOME"]) if os.environ.get("NHL94_HOME") else Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("NHL94_PORT") or 9494)  # NHL94_PORT: another port, e.g. for testing beside a running helper
SETTINGS_FILE = ROOT / "helper_settings.json"
INDEX_FILE = ROOT / "matches" / "games.json"

# What to record, and how to read the screen, clock, score and teams, come from the system module of the emulator
# found (tools/systems/: BLOCKS, View).
# full.bin.gz holds all of RAM now and then, for research only: the converter does not need it (converting
# 2026-10-14_1540_CGY-BOS without it gives an identical match), so every 10 s rather than every second.
SAMPLE_S, FULL_EVERY_S = 0.015, 10.0
MIN_GAME_S = 45          # shorter recordings (a few seconds of play, then back to the menus) are not kept
FINAL_WAIT_S = 3.0       # keep recording this long after the final horn
LIVE_FLUSH_S = 2.0       # broadcasting live: make the recording readable this often (tools/live_broadcast.py)
broadcaster = None       # a live_broadcast.Broadcaster with --broadcast

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
            if path.stem not in games and path.name != "season.js":
                try:
                    games[path.stem] = game_entry(path.stem)
                except Exception:
                    continue
        for name in list(games):
            if not (ROOT / "matches" / f"{name}.js").exists():
                del games[name]
        save_index(list(games.values()))


def update_season():
    """Rewrite matches/season.js (every game's summary, for season.html opened from the folder) after a change."""
    try:
        import season
        season.write_season_file()
    except Exception:
        traceback.print_exc()


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


def team_abbreviations(system, rom_path, home, away):
    """('BOS', 'STL') for the team indices, from the ROM; falls back to the numbers."""
    try:
        if rom_path not in team_cache:
            team_cache[rom_path] = system.read_teams(rom_path)
        teams = team_cache[rom_path]
        return [teams[i].get("abbr") or teams[i]["name"] for i in (home, away)]
    except Exception:
        return [f"T{home}", f"T{away}"]


# --------------------------------------------------------------------------------------------------------- recording
class Recording:
    def __init__(self, emu, view, rom_path, fingerprint):
        self.emu, self.rom_path, self.system = emu, rom_path, systems.get(emu.system)
        when = datetime.datetime.now()
        abbr = team_abbreviations(self.system, rom_path, *view.teams) if rom_path else [f"T{t}" for t in view.teams]
        self.teams = self.named = abbr
        self.name = f"{when:%Y-%m-%d_%H%M}_{abbr[0]}-{abbr[1]}".replace(" ", "")
        self.date = when.isoformat(timespec="minutes")
        self.folder = ROOT / "captures" / self.name
        self.folder.mkdir(parents=True, exist_ok=True)
        layout = {"blocks": [list(b) for b in self.system.BLOCKS], "recorded_by": "nhl94_helper", "system": self.system.NAME}
        if fingerprint:
            layout["rom_crc32"] = fingerprint
        (self.folder / "capture.json").write_text(json.dumps(layout))
        self.fast = gzip.open(self.folder / "fast.bin.gz", "wb", compresslevel=3)
        self.full = gzip.open(self.folder / "full.bin.gz", "wb", compresslevel=3)
        self.live_ms, self.last_wall, self.last_full = 0.0, time.perf_counter(), -1e9
        self.last_flush = time.perf_counter()
        self.record_size = 8 + sum(b[1] for b in self.system.BLOCKS)
        self.previous, self.samples = None, 0
        self.view, self.final_since, self.menu_since, self.joined_mid_game = view, None, None, not (view.period == 0 and view.clock >= 290)

    def step(self, view):
        """One sample. Returns why it ended ('final', 'menus', 'new game') or None to carry on."""
        now = time.perf_counter()
        elapsed, self.last_wall = (now - self.last_wall) * 1000, now
        old = self.view
        if view.in_menus:
            self.menu_since = self.menu_since or now
            if now - self.menu_since > 3:
                return "menus"
            return None
        self.menu_since = None
        # Other teams once this game is under way: between periods the Genesis sometimes shows highlights of another game
        # (2026-10-21: a WSH-FLA game at 5-4 in the third period, during a long BOS-NYI intermission, split the recording
        # and named it WSH-FLA). Not recorded and not compared against, however long; only a new game's opening faceoff
        # (first period, 0-0, the clock at the start) with other teams ends this recording.
        if view.live and self.samples and view.teams != old.teams:
            if view.period == 0 and view.score == (0, 0) and view.clock >= 290:
                return "new game"
            return None
        # A new game started without the old one finishing (the clock going back up within a period, other than to
        # start a period).
        if view.live and (view.period < old.period or (view.period == old.period == 0 and view.clock > old.clock + 5 and old.clock != 0)):
            return "new game"
        # The final horn: past the third period with the clock at 0 (and not tied, or later still). Checked whatever
        # the screen shows, in case the game takes the players off at the horn.
        if view.in_game:
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
        if view.teams != old.teams and not self.samples:  # the teams picked after the recording began (it began on a menu screen)
            self.teams = team_abbreviations(self.system, self.rom_path, *view.teams) if self.rom_path else [f"T{t}" for t in view.teams]
        self.view = view
        data = b"".join(view.blocks)
        if data != self.previous:
            self.fast.write(struct.pack("<q", round(self.live_ms)) + data)
            self.previous, self.samples = data, self.samples + 1
        if broadcaster and now - self.last_flush >= LIVE_FLUSH_S:
            self.fast.flush(zlib.Z_SYNC_FLUSH)  # so the live broadcast can read what is recorded so far
            self.last_flush = now
        if now - self.last_full >= FULL_EVERY_S:
            full = self.emu.read(0, self.system.RAM_SIZE)
            if full:
                self.full.write(struct.pack("<q", round(self.live_ms)) + full)
            self.last_full = now
        return None

    def close(self):
        self.fast.close()
        self.full.close()
        # Named after the teams that played: the recording may have begun on a screen still showing others.
        if self.teams != self.named:
            name = f"{self.name[:15]}_{self.teams[0]}-{self.teams[1]}".replace(" ", "")
            if not (ROOT / "captures" / name).exists():
                try:
                    self.folder = self.folder.rename(ROOT / "captures" / name)
                    self.name = name
                except OSError:
                    pass  # keeps the first name


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
        update_season()
        s = rec.view.score
        status.set("idle", f"Saved {rec.name}: {rec.teams[0]} {s[0]}-{s[1]} {rec.teams[1]}")
    except Exception as e:
        status.set("idle", f"Could not convert {rec.name}: {e}")
        traceback.print_exc()
    finally:
        if broadcaster:
            broadcaster.end(ROOT / "matches" / f"{rec.name}.js", rec.live_name)  # the whole game, as converted


def watch():
    """The main loop: wait for the emulator and a game, record it, hand it over, and again."""
    emu = None
    while True:
        try:
            if emu is None:
                emu = systems.attach()
                if emu is None:
                    status.set("waiting", "Waiting for RetroArch with NHL '94 loaded")
                    time.sleep(2)
                    continue
                rom_path, fingerprint = emu.dump_rom()
                import romnames
                romnames.note_loaded(getattr(emu, 'pid', None), emu.system, rom_path)  # the ROM's file name, for the season page
                View = systems.get(emu.system).View
            view = View(emu)
            if not view.live:
                status.set("ready", "NHL '94 is running; waiting for a game to start")
                time.sleep(0.25)
                continue
            rec = Recording(emu, view, rom_path, fingerprint)
            if broadcaster:
                broadcaster.rom_path = rom_path
                broadcaster.begin(rec, rec.record_size)
            rec.live_name = rec.name
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
                        "seconds": round(rec.live_ms / 1000), "paused": not view.in_game}, say=False)
                    next_sample += SAMPLE_S
                    time.sleep(max(0.0, next_sample - time.perf_counter()))
            except ConnectionError:
                why = "RetroArch closed"
                emu = None
            finally:
                if broadcaster and broadcaster.game == rec.live_name:
                    broadcaster.stop.set()  # before close(), which may rename the recording's folder
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
                    if v.in_menus or (v.live and v.period == 0 and v.clock > 0 and v.score == (0, 0)):
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

    def trusted(self, post=False):
        """Only this computer's pages may use the helper. The Host header must name the helper itself (a website that
        points its own name at 127.0.0.1, "DNS rebinding", would otherwise read the games and the ROM copies), and a
        change (POST) must carry the X-NHL94 header, which another website's page cannot send without the helper's
        leave (a cross-site request with a custom header needs a CORS preflight the helper never grants), and come
        from the helper's own origin if the browser says where it came from."""
        hosts = {f"localhost:{PORT}", f"127.0.0.1:{PORT}", f"[::1]:{PORT}"}
        if (self.headers.get("Host") or "").lower() not in hosts:
            return False
        if post:
            origin = self.headers.get("Origin")
            if self.headers.get("X-NHL94") != "1" or (origin and origin.lower() not in {"http://" + h for h in hosts}):
                return False
        return True

    def refuse(self):
        self.send_json({"error": "not allowed"}, 403)

    def do_GET(self):
        if not self.trusted():
            return self.refuse()
        url = urllib.parse.urlparse(self.path)
        if url.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/helper.html")
            self.end_headers()
        elif url.path == "/api/state":
            self.send_json({**status.snapshot(), "settings": load_settings(), "games": load_index()})
        elif url.path == "/api/season":
            import season
            self.send_json(season.season())
        else:
            super().do_GET()

    def do_HEAD(self):
        if not self.trusted():
            return self.refuse()
        super().do_HEAD()

    def do_POST(self):
        if not self.trusted(post=True):
            return self.refuse()
        url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(url.query)
        name = (query.get("name") or [""])[0]
        if name and not all(ch.isalnum() or ch in "_-" for ch in name):
            return self.send_json({"error": "bad name"}, 400)
        length = int(self.headers.get("Content-Length") or 0)
        if length > 5_000_000:
            return self.send_json({"error": "too large"}, 413)
        try:
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
        except ValueError:
            return self.send_json({"error": "bad request"}, 400)
        if not isinstance(body, dict):
            return self.send_json({"error": "bad request"}, 400)
        if url.path == "/api/settings":
            settings = load_settings()
            settings.update({k: bool(v) for k, v in body.items() if k in ("auto_game_file", "open_browser")})
            save_settings(settings)
            return self.send_json(settings)
        if url.path == "/api/seasons":
            import season
            if not isinstance(body.get("seasons"), list):  # never clear the seasons on a malformed request
                return self.send_json({"error": "bad request"}, 400)
            saved = season.save_seasons(body.get("seasons"))
            update_season()
            return self.send_json({"seasons": saved})
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
            for path in [ROOT / "matches" / f"{name}.js", ROOT / "matches" / f"{name}.summary.json",
                         ROOT / "matches" / "heat" / f"{name}.js",
                         *((ROOT / "shared").glob(f"*{name}.html") if (ROOT / "shared").exists() else [])]:
                try:
                    path.unlink()
                except OSError:
                    pass
            update_season()
            return self.send_json({"deleted": name})
        self.send_json({"error": "unknown"}, 404)


def convert_folder(folder):
    """Convert a recording folder by hand (--convert <folder>): for re-converting after an update, and for testing the
    packaged helper's built-in converter."""
    import export_match
    folder = Path(folder).resolve()
    export_match.main([str(folder)])
    with index_lock:
        old = next((g for g in load_index() if g["name"] == folder.name), None)  # keep when it was played
        games = [g for g in load_index() if g["name"] != folder.name]
        games.append(game_entry(folder.name, old and old.get("date")))
        save_index(games)
    update_season()
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


class Server6(Server):
    """The same on IPv6's loopback (::1): Windows resolves "localhost" to ::1 first, and with nothing there each request
    waited about 2 s before the browser tried 127.0.0.1, or gave up and said it could not connect."""
    import socket
    address_family = socket.AF_INET6


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


def exit_with_console():
    """Exit when the helper's window is closed. Closing a Windows Terminal tab (Windows 11 opens console programs
    there) takes the console away without stopping the program: the packaged helper's two processes (PyInstaller's
    launcher and the helper it starts) were left running, holding the port and the exe, so the exe could not be
    rebuilt (the user found them in Task Manager every time). Windows reports no console processes once the console is
    gone, so a thread checks every 2 s and ends the helper; the launcher, waiting for it, ends too."""
    if os.name != "nt":
        return
    import ctypes
    kernel32 = ctypes.windll.kernel32
    attached = lambda: kernel32.GetConsoleProcessList((ctypes.c_uint * 4)(), 4) > 0
    if not attached():  # started without a console: nothing to watch
        return

    def watch_console():
        while attached():
            time.sleep(2)
        os._exit(0)
    threading.Thread(target=watch_console, daemon=True).start()


def start_broadcast():
    """--broadcast [CHANNEL] --bucket NAME: send each game live to s3://<bucket>/live/<channel>/ (live_broadcast.py)."""
    global broadcaster
    import live_broadcast
    i = sys.argv.index("--broadcast")
    channel = sys.argv[i + 1] if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--") else "game"
    if "--bucket" not in sys.argv:
        print("Live broadcast is OFF: say which S3 bucket to use (--bucket NAME).", flush=True)
        return
    bucket = sys.argv[sys.argv.index("--bucket") + 1]
    target = live_broadcast.S3Target(bucket, f"live/{channel}")
    b = live_broadcast.Broadcaster(target)
    try:
        print("Live broadcast: putting the page up\u2026", flush=True)
        b.publish_page()
    except Exception as e:
        print(f"Live broadcast is OFF: could not upload to s3://{bucket} ({e}).", flush=True)
        print("  Sign in to AWS (run 'aws login' in a command window), then start the helper again.", flush=True)
        return
    broadcaster = b
    print(f"Live broadcast ON. Send your viewers this link: {target.url}", flush=True)


def main():
    if "--convert" in sys.argv:
        return convert_folder(sys.argv[sys.argv.index("--convert") + 1])
    if "--export" in sys.argv:  # the packaged helper running the converter as its own process (the live broadcast)
        import export_match
        return export_match.main(sys.argv[sys.argv.index("--export") + 1:])
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
    exit_with_console()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        threading.Thread(target=Server6(("::1", PORT), Handler).serve_forever, daemon=True).start()
    except OSError as e:  # IPv6 turned off, or ::1 taken: 127.0.0.1 still serves
        print(f"(Not listening on ::1: {e})", flush=True)
    if "--broadcast" in sys.argv:
        start_broadcast()
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
