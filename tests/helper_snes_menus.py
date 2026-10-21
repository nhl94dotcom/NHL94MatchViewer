"""Fake-emulator test of the helper (made 2026-10-14 .. 10-19 while building it): plays a recording back as if
RetroArch were running it and prints the helper's state as it waits, records and converts. Needs the recording
and ROM named below. python tests/helper_snes_menus.py"""
import os
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
import os
HOME = os.path.join(tempfile.gettempdir(), 'nhl94_helper_home_snes')
os.environ['NHL94_HOME'] = HOME
for sub in ('matches', 'captures', 'sprites', 'roms', 'shared', 'sounds'):
    os.makedirs(os.path.join(HOME, sub), exist_ok=True)
import sys, time, threading, json, urllib.request, bisect, struct, gzip, zlib
sys.path.insert(0, str(ROOT / 'tools'))
import nhl94_helper as H
from pathlib import Path
from systems import snes

SRC = (Path.home() / 'Documents/NHL94 Viewer/captures/2026-10-16_1528_TOR-CHI')
fast = gzip.decompress((SRC / 'fast.bin.gz').read_bytes())
full = gzip.decompress((SRC / 'full.bin.gz').read_bytes())
print('loaded', flush=True)
S, FS = 8 + 0x4000, 8 + 0x20000
times = [struct.unpack_from('<q', fast, i * S)[0] for i in range(len(fast) // S)]
ftimes = [struct.unpack_from('<q', full, i * FS)[0] for i in range(len(full) // FS)]
SPEED = 25.0
ROM = (Path.home() / 'RetroArch-1.17-Win64/ROMs/SNES/NHL94_Classic.smc')


class FakeSnes:
    """Plays the first SNES recording back as if Snes9x were running it."""
    system = 'snes'; ram = rom = 0; pid = None

    def __init__(self): self.t0 = time.perf_counter()

    def now(self): return (time.perf_counter() - self.t0) * SPEED * 1000

    def read(self, off, size):
        T = self.now()
        if off + size <= 0x4000:
            i = max(0, min(len(times) - 1, bisect.bisect_right(times, T) - 1))
            return fast[i * S + 8 + off:i * S + 8 + off + size]
        j = max(0, min(len(ftimes) - 1, bisect.bisect_right(ftimes, T) - 1))
        return full[j * FS + 8 + off:j * FS + 8 + off + size]

    def rom_fingerprint(self): return f"{zlib.crc32(snes.strip_header(ROM.read_bytes())[:0x100000]):08x}"

    def dump_rom(self): return ROM, self.rom_fingerprint()


emu = FakeSnes()
H.systems.attach = lambda: emu
H.PORT = 9496
sys.argv.append('--no-browser')
threading.Thread(target=H.main, daemon=True).start()
seen = []
for k in range(200):
    time.sleep(1)
    try:
        s = json.loads(urllib.request.urlopen('http://localhost:9496/api/state').read())
        line = (s['state'], s['detail'], s['game'] and {k2: s['game'].get(k2) for k2 in ('clock', 'paused')})
        if not seen or seen[-1][:2] != line[:2]: seen.append(line); print(f"{k:3d}s", line, flush=True)
        if s['state'] == 'idle' and 'Saved' in s['detail']: break
    except Exception as e:
        print('api error', e)
games = json.loads(urllib.request.urlopen('http://localhost:9496/api/state').read())['games']
print('games:', [(g['name'], g['score'], g['seconds']) for g in games][:3])
