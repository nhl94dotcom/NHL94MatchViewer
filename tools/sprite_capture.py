"""Reads sprites.bin (from nhl94_record_sprites.ps1): work RAM plus the on-screen sprites and their tile graphics."""
import struct

RAM_START, RAM_LEN = 0xB000, 0x1C00
BASE, SIZE = 0xB04A, 0x80


class Sample:
    def __init__(self, ms, ram, sprites, tiles):
        self.ms, self.ram, self.sprites, self.tiles = ms, ram, sprites, tiles

    def byte(self, addr):  # host memory swaps the two bytes of each word
        return self.ram[(addr - RAM_START) ^ 1]

    def word(self, addr):
        return struct.unpack_from("<H", self.ram, addr - RAM_START)[0]

    def sword(self, addr):
        return struct.unpack_from("<h", self.ram, addr - RAM_START)[0]

    def pixels(self, sprite):
        """The sprite's picture as rows of colour indices (0 = transparent), with its flips applied."""
        w, h, first = sprite["w"], sprite["h"], sprite["tile"]
        rows = [[0] * (w * 8) for _ in range(h * 8)]
        for col in range(w):  # sprite tiles run down each column, then across
            for row in range(h):
                data = self.tiles.get((first + col * h + row) & 0x7FF)
                if data is None:
                    return None
                for y in range(8):
                    for b in range(4):
                        v = data[(y * 4 + b) ^ 1]
                        rows[row * 8 + y][col * 8 + b * 2] = v >> 4
                        rows[row * 8 + y][col * 8 + b * 2 + 1] = v & 15
        if sprite["hflip"]:
            rows = [r[::-1] for r in rows]
        if sprite["vflip"]:
            rows = rows[::-1]
        return rows


def read(path):
    data = open(path, "rb").read()
    pos = 0
    while pos + 8 + RAM_LEN <= len(data):
        ms = struct.unpack_from("<q", data, pos)[0]
        ram = data[pos + 8:pos + 8 + RAM_LEN]
        pos += 8 + RAM_LEN
        n = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        sprites = []
        for i in range(n):
            y, w1, attr, x = struct.unpack_from("<4H", data, pos + 8 * i)
            size = (w1 >> 8) & 0xF
            sprites.append({"x": (x & 0x1FF) - 128, "y": (y & 0x3FF) - 128, "w": (size >> 2) + 1, "h": (size & 3) + 1,
                            "tile": attr & 0x7FF, "pal": (attr >> 13) & 3, "hflip": bool(attr & 0x800),
                            "vflip": bool(attr & 0x1000), "pri": attr >> 15})
        pos += 8 * n
        t = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        tiles = {}
        for i in range(t):
            tiles[struct.unpack_from("<H", data, pos)[0]] = data[pos + 2:pos + 34]
            pos += 34
        yield Sample(ms, ram, sprites, tiles)
