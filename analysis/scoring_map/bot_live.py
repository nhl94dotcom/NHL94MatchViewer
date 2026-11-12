"""The scripted bot (bot.py) playing in RetroArch against a person (2026-11-01, the user: play against the bot).

It reads the game's memory the way the helper does (read-only, tools/systems/genesis.py) and plays controller 2 by
sending key presses to RetroArch: no driver, nothing written to the emulator. Each new game frame (the frame counter
$B03E moves) the bot decides the buttons to hold, and the keys bound to RetroArch's port 2 are pressed or released to
match. Keys go only to RetroArch: whenever another window has the focus, or the game isn't in play (a menu, the pause
menu, a replay), every key is let go and the bot waits. Ctrl+C stops it and lets every key go.

Setup (once, in RetroArch): Settings > Input > Port 2 Controls, bind the keypad (NumLock on or off, either works):
Up keypad 8, Down keypad 5, Left keypad 4, Right keypad 6, and the Genesis buttons A keypad 7, B keypad 9, C keypad 0
(clear of keypad 1-3, which the user plays A, B, C with on port 1, the d-pad on a gamepad; Port 2's rows show the core's names; if yours show the RetroPad's, Genesis Plus GX's default is Y = A, B = B, A = C).
In the game's menus set controller 2 to the bot's team (the team setup screen), the other to yours.

python bot_live.py watch       read only: print what the bot would press, every half second (no keys sent)
python bot_live.py test        press each of the bot's keys for a moment and check that controller 2's buttons in the
                               game's memory ($BEF1) answer (in a game, play running; it moves pad 2's skater a little)
python bot_live.py play [ver]  play (version default bot_run.py's VERSION: 57 since 2026-11-12)

The bot's buttons reach the game a frame late (a key pressed during a frame is read at the next): it was tested with
none. Penalties, line changes off, manual goalies: as in bot_run.py's games."""
import ctypes
import ctypes.wintypes as wt
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from systems import genesis as GEN  # noqa: E402

from bot import Bot  # noqa: E402

FRAME_COUNTER, CONT2TEAM, PAD2 = 0xB03E, 0xC32A, 0xBEF1
BLOCK = (0xB000, 0x900)                                 # the object records, the puck carrier ($B7AA), the counter
# the keypad's scan codes (without the extended flag: the keypad, not the arrow keys)
KEYS = {"UP": 0x48, "DOWN": 0x4C, "LEFT": 0x4B, "RIGHT": 0x4D, "A": 0x47, "B": 0x49, "C": 0x52}
BITS = {"UP": 0x01, "DOWN": 0x02, "LEFT": 0x04, "RIGHT": 0x08, "B": 0x10, "C": 0x20, "A": 0x40}   # $BEF1 (as $BEEF)

user32 = ctypes.WinDLL("user32", use_last_error=True)
winmm = ctypes.WinDLL("winmm")
INPUT_KEYBOARD, KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE = 1, 0x0002, 0x0008


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("u", _U)]


user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.GetForegroundWindow.restype = wt.HWND
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]


def send(scans, up):
    if not scans:
        return
    arr = (INPUT * len(scans))()
    for i, sc in enumerate(scans):
        arr[i].type = INPUT_KEYBOARD
        arr[i].u.ki = KEYBDINPUT(0, sc, KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0), 0, 0)
    user32.SendInput(len(scans), arr, ctypes.sizeof(INPUT))


class Keys:
    """The port-2 keys held now; changes are sent only while RetroArch has the focus."""

    def __init__(self, pid):
        self.pid, self.down = pid, set()

    def focused(self):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(pid))
        return pid.value == self.pid

    def hold(self, buttons):
        want = {b for b in buttons if b in KEYS} if self.focused() else set()
        send([KEYS[b] for b in self.down - want], up=True)
        send([KEYS[b] for b in want - self.down], up=False)
        self.down = want

    def release(self):
        send([KEYS[b] for b in self.down], up=True)
        self.down = set()


class Live:
    """The bot's view of the running game: one read of the object block per frame, served as the harness's b / w /
    sw (Genesis addresses; bytes at A XOR 1, words little-endian in the host copy)."""

    def __init__(self, emu):
        self.emu, self.block = emu, None

    def refresh(self):
        self.block = self.emu.read(*BLOCK)
        if self.block is None:
            raise ConnectionError("RetroArch went away")

    def _off(self, a):
        o = a - BLOCK[0]
        if not 0 <= o < BLOCK[1] - 1:
            raise KeyError(f"${a:04X} is outside the block the runner reads")
        return o

    def b(self, a):
        return self.block[self._off(a) ^ 1]

    def w(self, a):
        return struct.unpack_from("<H", self.block, self._off(a))[0]

    def sw(self, a):
        return struct.unpack_from("<h", self.block, self._off(a))[0]


def word(emu, a):
    v = emu.word(a)
    if v is None:
        raise ConnectionError("RetroArch went away")
    return v


def in_play(emu):
    try:
        return GEN.View(emu).live
    except ConnectionError:
        raise


def attach():
    emu = GEN.attach()
    while emu is None:
        print("waiting for RetroArch with a Genesis game loaded ...", flush=True)
        time.sleep(3)
        emu = GEN.attach()
    return emu


def bot_team(emu):
    """Controller 2's team: 0 Home, 1 Away, None if it has none (cont2team: 1 Home, 2 Away)."""
    t = word(emu, CONT2TEAM)
    return {1: 0, 2: 1}.get(t)


SESSIONS = Path.home() / "NHL94_scoring_map" / "bot_live_sessions.jsonl"


def log_session(event, version):
    """When a play session starts and stops, and the version (2026-11-12): the helper records these games as people's
    (a pad on each side), so analyses of people's games leave out recordings made during a session."""
    import json
    from datetime import datetime
    SESSIONS.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSIONS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"event": event, "time": datetime.now().isoformat(timespec="seconds"), "version": version}) + "\n")


def run(mode, version):
    if mode == "play":
        log_session("start", version)
    try:
        _run(mode, version)
    finally:
        if mode == "play":
            log_session("stop", version)


def _run(mode, version):
    emu = attach()
    live = Live(emu)
    keys = Keys(emu.pid)
    winmm.timeBeginPeriod(1)
    print(f"attached to RetroArch (pid {emu.pid}); mode {mode}" + (f", bot version {version}" if mode == "play" else "")
          + ". Ctrl+C stops.", flush=True)
    bot, team, last_frame, last_print, waiting = None, None, None, 0.0, None
    try:
        while True:
            frame = word(emu, FRAME_COUNTER)
            if frame == last_frame:
                time.sleep(0.001)
                continue
            last_frame = frame
            t = bot_team(emu)
            play = in_play(emu)
            reason = None if play and t is not None else ("controller 2 has no team" if t is None else "not in play")
            if reason:
                keys.release()
                if reason != waiting:
                    print(f"waiting: {reason}", flush=True)
                    waiting = reason
                continue
            if waiting:
                print("playing", flush=True)
                waiting = None
            if bot is None or t != team:
                team, bot = t, Bot(t, version)
                print(f"the bot plays {'Home' if t == 0 else 'Away'} on controller 2", flush=True)
            live.refresh()
            buttons = bot.step(live)
            if mode == "play":
                keys.hold(buttons)
            elif time.time() - last_print > 0.5:
                last_print = time.time()
                print(f"frame {frame:5}: phase {bot.phase:6} would press {' '.join(buttons) or '-'}", flush=True)
    except KeyboardInterrupt:
        print("stopped", flush=True)
    finally:
        keys.release()
        winmm.timeEndPeriod(1)


def test():
    """Each key held about a third of a second while RetroArch has the focus; controller 2's byte must show it."""
    emu = attach()
    keys = Keys(emu.pid)
    print("Click into RetroArch (a game on the ice, play running) within 5 seconds ...", flush=True)
    time.sleep(5)
    ok = True
    try:
        for name in ("UP", "DOWN", "LEFT", "RIGHT", "A", "B", "C"):
            if not keys.focused():
                print("RetroArch doesn't have the focus: test stopped (no keys sent)")
                return
            keys.hold([name])
            seen, end = False, time.time() + 0.35
            while time.time() < end:
                pad = emu.byte(PAD2)
                if pad is not None and pad & BITS[name]:
                    seen = True
                time.sleep(0.005)
            keys.release()
            time.sleep(0.3)
            print(f"  {name:5} keypad scan ${KEYS[name]:02X}: {'seen on controller 2' if seen else 'NOT seen'}", flush=True)
            ok &= seen
    finally:
        keys.release()
    print("all keys work" if ok else "check the Port 2 bindings in RetroArch (bot_live.py's docstring)")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "watch"
    if mode == "test":
        test()
    elif mode in ("watch", "play"):
        from bot_run import VERSION
        run(mode, int(sys.argv[2]) if len(sys.argv) > 2 else VERSION)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
