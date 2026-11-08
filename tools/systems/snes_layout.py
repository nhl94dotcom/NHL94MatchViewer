"""Where a SNES NHL '94 ROM keeps what the tools read from it, for the retail 1 MB layout and for the 2 MB builds of
github.com/Mhopkinsinc/NHL94SNES-SA1 (2026-11-07; the SA-1 cartridges among them: header map mode $23). The 2 MB
builds move the team list (bank $A1), the uniform colours (bank $A0 in the 32-team build) and the animations (the code
before them in bank $9D grew), and some add sprite frames after the retail 976 (frames 1-976 are the retail ones in
both builds the user has). Found here from the ROM itself, so a later build works too:

- the team list: a run of long pointers (address word, bank byte, 0) to records that read as teams;
- the uniform colours: SetTeamColors' code (the team number times 32, plus the table: asl x5, clc, adc #, sta, lda #bank);
- the animations: walked from SPAlist (a 0 word, then each animation's eight direction pointers, an attribute word and
  its frame lists in order), each matched to its retail twin by its frame lists (snes_spa_retail.json: a hash of each
  direction's list per retail animation word, made from the retail ROM by `python tools/systems/snes_layout.py
  --retail-table <retail rom>`). The match files keep the retail words, so everything that knows an animation by its
  word reads these games unchanged.

layout(rom) (the ROM's bytes without a copier header) -> Layout, cached by the ROM's bytes."""
import hashlib
import json
import struct
from pathlib import Path

RETAIL_TABLE = Path(__file__).with_name("snes_spa_retail.json")
READY_D0 = struct.pack("<10h", 534, 180, 646, 20, 534, 10, 647, 20, 534, -10)  # SPAgready's first frame list
COLOURS_CODE = bytes.fromhex("0a0a0a0a0a1869")  # SetTeamColors: asl a x5, clc, adc.w #table
RETAIL = dict(team_list=0x9CA5E7, home=0x96CD4E, away=0x96C9CE, anim_bank=0x9D)


def file_offset(address):
    """LoROM (and the SA-1 builds, whose banks $80-$BF are the first 2 MB as in LoROM): the ROM file offset."""
    return ((address >> 16) & 0x7F) * 0x8000 + (address & 0x7FFF)


def is_sa1(rom):
    return len(rom) > 0x7FD6 and rom[0x7FD5] == 0x23


def _list_end(rom, at):
    """The end of a frame list at file offset `at` (pairs of frame, time; a negative time ends it), or None (also
    when `at` is an animation, which a direction may point at instead: its first word an address, $8000 or more,
    where a frame number is under 1,000)."""
    if at + 2 > len(rom) or struct.unpack_from("<H", rom, at)[0] >= 0x8000:
        return None
    for _ in range(64):
        if at + 4 > len(rom):
            return None
        t = struct.unpack_from("<h", rom, at + 2)[0]
        at += 4
        if t < 0:
            return at
    return None


def walk_animations(rom, bank, spalist):
    """[(animation word, [eight frame lists as bytes])] from SPAlist (the address of its 0 word) on."""
    base = file_offset(bank << 16)
    out, spa = [], spalist + 2
    while spa + 18 <= 0x10000 and len(out) < 400:
        ptrs = struct.unpack_from("<8H", rom, base + (spa & 0x7FFF))
        if not all(0x8000 <= p < 0x10000 for p in ptrs):
            break
        pos, owned = spa + 18, set(ptrs)
        while pos in owned:
            end = _list_end(rom, base + (pos & 0x7FFF))   # None at the next animation
            if end is None:
                break
            pos = 0x8000 + (end - base)
        if pos == spa + 18:
            break                                   # no frame list of its own after it: past the last animation
        lists = []
        for p in ptrs:
            end = _list_end(rom, base + (p & 0x7FFF))
            lists.append(rom[base + (p & 0x7FFF):end] if end else b"next")   # pointing at another animation
        out.append((spa, lists))
        spa = pos
    return out


def _find_spalist(rom):
    at = rom.find(READY_D0)
    while at >= 0:
        bank = 0x80 | (at // 0x8000)
        target = 0x8000 + at % 0x8000
        base = file_offset(bank << 16)
        # SPAgready's direction 0 points at that list; SPAlist is the 0 word before SPAgready
        for spa in range(target - 18, max(0x8000, target - 0x40), -2):
            if struct.unpack_from("<H", rom, base + (spa & 0x7FFF))[0] == target and \
                    struct.unpack_from("<H", rom, base + ((spa - 2) & 0x7FFF))[0] == 0:
                return bank, spa - 2
        at = rom.find(READY_D0, at + 1)
    return None, None


def _fingerprint(lists):
    return [hashlib.sha1(x).hexdigest()[:10] for x in lists]


def _team_record_ok(rom, address):
    if not (0x80 <= address >> 16 <= 0xFF and address & 0xFFFF >= 0x8000):
        return False
    team = file_offset(address)
    if team + 6 > len(rom):
        return False
    players_off = struct.unpack_from("<H", rom, team)[0]
    off = team + players_off
    if not 0 < players_off < 0x400 or off + 4 > len(rom):
        return False
    length = struct.unpack_from("<H", rom, off)[0]
    return 2 < length <= 40 and all(c >= 32 for c in rom[off + 2:off + length].rstrip(b"\x00"))   # Latin-1 names too


def _team_count(rom, at):
    n = 0
    while at + 4 * n + 4 <= len(rom):
        lo, hi, bank, zero = rom[at + 4 * n:at + 4 * n + 4]
        if zero or not _team_record_ok(rom, bank << 16 | hi << 8 | lo):
            break
        n += 1
    return n


def _find_team_list(rom):
    at = file_offset(RETAIL["team_list"])
    if _team_count(rom, at) >= 26:
        return RETAIL["team_list"], _team_count(rom, at)
    best = (0, None)
    for at in range(0, len(rom) - 4 * 26, 1):
        if rom[at + 3] or rom[at + 7] or rom[at + 11] or not 0x80 <= rom[at + 2] <= 0xBF:
            continue
        n = _team_count(rom, at)
        if n > best[0]:
            best = (n, at)
        if n >= 26:
            break
    if best[1] is None:
        return None, 0
    at = best[1]
    return (0x80 + at // 0x8000) << 16 | (0x8000 + at % 0x8000), best[0]


def _find_colours(rom):
    """SetTeamColors: lda.w HomeTeam (VisTeam for the away colours), asl a x5, clc, adc.w #table, sta.b p0, lda.w #bank.
    HomeTeam is $1C98, VisTeam $1C9A ($7C98 / $7C9A on an SA-1 build: low RAM moved to BW-RAM at $6000)."""
    out = []
    for team in (0x98, 0x9A):
        hit = None
        for high in (0x1C, 0x7C):
            at = rom.find(bytes([0xAD, team, high]) + COLOURS_CODE)
            if at >= 0:
                at += 3
                if rom[at + 9] == 0x85 and rom[at + 11] == 0xA9 and rom[at + 13] == 0:
                    hit = rom[at + 12] << 16 | rom[at + 8] << 8 | rom[at + 7]
                    break
        out.append(hit)
    return out if all(out) else [RETAIL["home"], RETAIL["away"]]


class Layout:
    def __init__(self, rom):
        self.sa1 = is_sa1(rom)
        self.team_list, self.team_count = _find_team_list(rom)
        self.home_palettes, self.away_palettes = _find_colours(rom)
        self.anim_bank, spalist = _find_spalist(rom)
        self.anim_bank = self.anim_bank or RETAIL["anim_bank"]
        self.to_retail, self.from_retail = {}, {}
        if spalist is not None and RETAIL_TABLE.exists():
            retail = {int(k, 16): v for k, v in json.loads(RETAIL_TABLE.read_text()).items()}
            mine = walk_animations(rom, self.anim_bank, spalist)
            for spa, lists in mine:
                fp = _fingerprint(lists)
                score = lambda r: (fp[0] == retail[r][0], sum(a == b for a, b in zip(fp, retail[r])), -abs(r - spa))
                r = max(retail, key=score)
                if score(r)[1] >= 4 and r not in self.from_retail:
                    self.to_retail[spa], self.from_retail[r] = r, spa
        self.retail_animations = all(a == b for a, b in self.to_retail.items())

    def spa(self, word):
        """This ROM's animation word as the retail one (unchanged if unknown or retail)."""
        return self.to_retail.get(word, word)

    def rom_spa(self, retail_word):
        """A retail animation word as this ROM's."""
        return self.from_retail.get(retail_word, retail_word)


_cache = {}


def layout(rom):
    key = hashlib.sha1(rom).hexdigest()
    if key not in _cache:
        _cache[key] = Layout(rom)
    return _cache[key]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "--retail-table":
        from snes import strip_header  # noqa: E402  (run as a script from tools/systems)
        rom = strip_header(Path(sys.argv[2]).read_bytes())
        bank, spalist = _find_spalist(rom)
        table = {f"{spa:04x}": _fingerprint(lists) for spa, lists in walk_animations(rom, bank, spalist)}
        RETAIL_TABLE.write_text(json.dumps(table, indent=0) + "\n")
        print(len(table), "retail animations ->", RETAIL_TABLE)
