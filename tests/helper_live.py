"""Fake-emulator test of the helper (made 2026-10-14 .. 10-19 while building it): plays a recording back as if
RetroArch were running it and prints the helper's state as it waits, records and converts. Needs the recording
and ROM named below. python tests/helper_live.py"""
import os
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
import os
HOME = os.path.join(tempfile.gettempdir(), 'nhl94_helper_home_live')
os.environ['NHL94_HOME'] = HOME
for sub in ('matches', 'captures', 'sprites', 'roms', 'shared'):
    os.makedirs(os.path.join(HOME, sub), exist_ok=True)
import sys, struct, time, threading, json, urllib.request, bisect
sys.path.insert(0, str(ROOT / 'tools'))
import nhl94_helper as H
from pathlib import Path
RAM = (ROOT / 'captures/explore1_menus/ram.bin')
S = 8 + 65536; N = RAM.stat().st_size // S
f = open(RAM, 'rb')
times = []
for i in range(N):
    f.seek(i * S); times.append(struct.unpack('<q', f.read(8))[0])
SPEED = 3.0
ROM = (Path.home() / 'RetroArch-1.17-Win64/ROMs/Genesis/nhl94.bin')


class FakeEmu:
    """Plays the explore1_menus recording back as if it were Genesis Plus GX running, with a made-up final horn."""
    handle = None; rom = 0; system = 'genesis'

    def __init__(self): self.t0 = time.perf_counter()

    def frame(self):
        T = (time.perf_counter() - self.t0) * SPEED * 1000
        i = max(0, min(N - 1, bisect.bisect_right(times, T) - 1))
        f.seek(i * S + 8); r = bytearray(f.read(65536))
        if T > 150000:  # a made-up final horn: past the third period, clock 0, 2-1
            struct.pack_into('<H', r, 0xC466, 3); struct.pack_into('<H', r, 0xC468, 0)
            struct.pack_into('<H', r, 0xC6DA, 2); struct.pack_into('<H', r, 0xCA3E, 1)
            r[0xFFF7 ^ 1] = 0
        if T > 160000:
            r[0xFFF7 ^ 1] = 15  # back to the menus
        return r

    def read(self, off, size):
        r = self.frame(); return bytes(r[off:off + size])

    def rom_fingerprint(self): return ['9438f5dd', 'a738ea1c']

    def dump_rom(self): return ROM, self.rom_fingerprint()


emu = FakeEmu()
H.systems.attach = lambda: emu
H.PORT = 9496
import live_broadcast as LB
OUT = os.path.join(tempfile.gettempdir(), 'nhl94_livetest_helper')
LB.S3Target = lambda bucket, prefix: LB.FolderTarget(OUT)
sys.argv += ['--no-browser', '--broadcast', 'test', '--bucket', 'x']
threading.Thread(target=H.main, daemon=True).start()
seen = []
for k in range(75):
    time.sleep(1)
    try:
        s = json.loads(urllib.request.urlopen('http://localhost:9496/api/state').read())
        line = (s['state'], s['detail'], s['game'] and {k2: s['game'].get(k2) for k2 in ('clock', 'seconds', 'paused')})
        if not seen or seen[-1] != line: seen.append(line); print(f"{k:3d}s", line, flush=True)
    except Exception as e:
        print('api error', e)
print('games:', [(g['name'], g['score'], g['seconds']) for g in json.loads(urllib.request.urlopen('http://localhost:9496/api/state').read())['games']][:3])
print('capture.json:', [open(os.path.join(HOME, 'captures', d, 'capture.json')).read() for d in os.listdir(os.path.join(HOME, 'captures'))])

print(open(os.path.join(OUT, 'live.json')).read()); print(sorted(os.listdir(os.path.join(OUT, 'data', os.listdir(os.path.join(OUT, 'data'))[0]))))
