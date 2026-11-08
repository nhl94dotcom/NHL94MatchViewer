"""The hacks a SNES NHL '94 ROM carries, read from its code, as the NOSE4Web editor reads them
(github.com/nhl94dotcom/NOSE4Web, src/core/sneshacks.ts): NHL94SNESVault's patches (github.com/Mhopkinsinc/
NHL94SNESVault) and the editor's own fixes, to bugs the Match Viewer project found (each tested in the game,
docs/STUDY_NOTES.md).

Each hack is a set of places, found by the code around them (so the same in the original layout, the 32-team 2 MB
build and the SA-1 build, whose variables sit $6000 higher), each holding the original game's bytes or the hack's. A
hack is on when every place holds the hack's (new code included), off when every place holds the original's, and
unknown otherwise: some other code there, which is never taken for the original game.

`rom_settings(rom)` returns {hack: True / False} for each hack found, and "unknown": [hack ...] for the rest
(the copier header, if any, taken off first)."""
import re

BANK = 0x8000
HACKS = ["hotColdFix", "ppPkFix", "defenceControl", "oneMinutePenalties", "noInterference", "noPenaltyShots",
         "noGoalPosts", "faceoffFix", "penaltyShotFixes", "extraAttackerFix", "yButtonFix", "comebackFix",
         "awarenessFix"]
TITLES = {
    "hotColdFix": "Hot and cold bug fix", "ppPkFix": "Power play and penalty kill fix",
    "defenceControl": "Defence control on", "oneMinutePenalties": "One-minute penalties",
    "noInterference": "No interference penalties", "noPenaltyShots": "No penalty shots", "noGoalPosts": "No goal posts",
    "faceoffFix": "Faceoff spot fix", "penaltyShotFixes": "Penalty shot fixes", "extraAttackerFix": "Extra attacker fix",
    "yButtonFix": "Y button fix", "comebackFix": "Comeback bonus fix", "awarenessFix": "Computer forwards' awareness fix",
}


def h(text):
    return bytes.fromhex(re.sub(r"\s", "", text))


def w(v):
    return bytes([v & 0xFF, (v >> 8) & 0xFF])


def u16(rom, at):
    return rom[at] | rom[at + 1] << 8


def offset(bank, address):
    return (bank & 0x7F) * BANK + (address - 0x8000)


def address(off):
    return 0x8000 + off % BANK


def long(off):
    return w(address(off)) + bytes([0x80 | off // BANK])


def find(rom, pattern):
    """Every place of a hex pattern ('..' any byte)."""
    rx = b"".join(b"." if pattern[i:i + 2] == ".." else re.escape(bytes([int(pattern[i:i + 2], 16)]))
                  for i in range(0, len(pattern), 2))
    return [m.start() for m in re.finditer(b"(?=" + rx + b")", rom, re.S)]


def only(rom, pattern):
    found = find(rom, pattern)
    return found[0] if len(found) == 1 else -1


def same(rom, at, data):
    return data is not None and rom[at:at + len(data)] == data


def shift(rom):
    """How far the game's variables moved: none in a LoROM build, $6000 in the SA-1 build (its map mode $23)."""
    return 0x6000 if len(rom) > 0x7FD6 and rom[0x7FD5] == 0x23 else 0


def in_place(rom):
    """The game's code where the original has it (the original and ROMs patched in place): the comeback test's code
    at the original's place."""
    return only(rom, "a5a538ed....f002....ad....38") == 0xFCFF3


def new_code(rom, site, call, original, code):
    """A call (JSR / JMP in the bank) at `site` to new code: [(place, original, hack)] for the site and the code."""
    if same(rom, site, original):
        return [(site, original, None)]                    # off: the new code's place doesn't matter
    target = offset(0x80 | site // BANK, u16(rom, site + 1))
    return [(site, original, call(address(target))), (target, None, code)]


def hot_cold(rom):
    found = only(rom, "851698186514a8e220..........8900f002090018651610")
    if found < 0:
        return None
    site = found + 9
    code = lambda var: b"\xb9" + var + h("1009 49FF 1A 4A 4A 49FF 1A 60 4A 4A 60")
    if rom[site] == 0xB9 and same(rom, site + 3, h("4A4A")):
        var = w(u16(rom, site + 1))
    elif rom[site] == 0x20 and same(rom, site + 3, h("EAEA")):
        var = w(u16(rom, offset(0x80 | site // BANK, u16(rom, site + 1)) + 1))
    else:
        return None
    return new_code(rom, site, lambda to: b"\x20" + w(to) + h("EAEA"), b"\xb9" + var + h("4A4A"), code(var))


def pp_pk(rom):
    site = only(rom, "f0..a00100b789" + ".." * 27 + "a00200b789290f0049ffff1a85a5")
    if site < 0:
        return None
    hacked = rom[site + 1] == 0x11
    first, second = u16(rom, site + (15 if hacked else 11)), u16(rom, site + 32)
    return [(site, h("F00D A00100 B789 290F00 8D") + w(first) + h("8013 A00100 B789 4A4A4A4A 290F00 49FFFF 1A 8D") + w(second),
             h("F011 A00100 B789 4A4A4A4A 290F00 8D") + w(first) + h("800F A00100 B789 290F00 49FFFF 1A 8D") + w(second))]


def defence(rom):
    found = only(rom, "c90100d006a920000c...." + "........" + "22......22......a97e008d")
    if found < 0:
        return None
    site = found + 11
    hacked = rom[site] == 0x20 and rom[site + 3] == 0xEA
    routine = offset(0x80 | site // BANK, u16(rom, site + 1)) + 1 if hacked else site + 1
    target = rom[routine:routine + 3]
    m = shift(rom)
    code = b"\x22" + target + h("A90100 8D") + w(0x1C94 + m) + b"\x8d" + w(0x1C96 + m) + b"\x60"
    return new_code(rom, site, lambda to: b"\x20" + w(to) + b"\xea", b"\x22" + target, code)


MINORS = [("00000200f6fa", "040a0043"), ("010a010bfffe", "040a0053"), ("01020103fffe", "040a0054"),
          ("01040105fffe", "0a0a0052"), ("010d010efffe", "040a0052"), ("010d010efffe", "04090048"),
          ("01090108fffe", "040d0043"), ("010f0110fffe", "040e0049"), ("0101060cfffe", "04090048")]


def one_minute(rom):
    minors = [only(rom, a + ".." + b) for a, b in MINORS]
    found = only(rom, "a8a9..00858fa9....858d18778d858da78d" + "......" + "f0c9c90100f0c4a90004")
    if found < 0 or min(minors) < 0:
        return None
    site = found + 18
    a = address(site)
    code = h("C90104 F005 C9010A D003 4C") + w(a + 0x0A) + h("29FF00 4C") + w(a + 3)
    return [(m + 6, h("02"), h("01")) for m in minors] + new_code(rom, site, lambda to: b"\x4c" + w(to), h("29FF00"), code)


def one_place(pattern, at, original, hacked):
    def find_it(rom):
        found = only(rom, pattern)
        return None if found < 0 else [(found + at, h(original), h(hacked))]
    return find_it


def goal_posts(rom):
    found = only(rom, "4c....64a9ad....450c30d1a9000038e50c850ca9000038e5a585a5ad....d0bc" + "......" + "c90d00f00ea5adc91200")
    if found < 0:
        return None
    return [(found + 0x21, b"\xad" + w(0x0DF9 + shift(rom)), b"\x4c" + w(address(found)))]


def comeback(rom):
    found = only(rom, "a5a538ed....f002....ad....38")
    if found < 0 or rom[found + 8] not in (0x10, 0x30):
        return None
    return [(found + 8, h("10"), h("30"))]


def awareness(rom):
    sites = [only(rom, p) for p in ("30034c2d85187d", "30034c798b187d")]
    if any(s < 0 or rom[s + 7] not in (0x43, 0x23) for s in sites):
        return None
    return [(s + 7, h("43"), h("23")) for s in sites]


def y_button(rom):
    found = only(rom, "bd....f00dbd....f009bd....c9...." + "...." + "6b")   # Holdplayer: ... cmp #SPAburst; bne; rtl
    if found < 0 or (rom[found + 16:found + 18] not in (h("D001"), h("EAEA"))):
        return None
    return [(found + 16, h("D001"), h("EAEA"))]


FACEOFF_REGION, FOX_AT, PENBUF = 94, 0x7E, 0x15DE


def faceoff_original(fox, foy):
    return h("A5A5 85C5 38 E94600 3005 A94600 85A5 A5A5 38 E9BAFF 1005 A9BAFF 85A5 A5A9 38 E9A600 3013 A9CE00 85A9 "
             "A94600 85A5 A5C5 1005 A9BAFF 85A5 A5A9 38 E95AFF 1013 A932FF 85A9 A94600 85A5 A5C5 1005 A9BAFF 85A5 A5A5 8F") + \
        fox + h("A5A9 8F") + foy


def faceoff_code(penbuf, pfgoal, fox, foy):
    return h("A00000 B9") + w(penbuf) + h("F004 C8 C8 80F7 C00000 F034 88 88 B9") + w(penbuf) + \
        h("29FF00 C90E00 F059 C91400 9022 C92F00 B01D C91600 F018 B9") + w(penbuf) + \
        h("EB 297F00 0A A8 A9CE00 85A9 B9") + w(pfgoal) + \
        h("F005 A932FF 85A9 A5A5 3005 A94600 8003 A9BAFF 85A5 A5A9 300F C95900 9005 A9CE00 8012 A94100 800D C9A8FF B005 "
          "A932FF 8003 A9BFFF 85A9 8004 64A5 64A9 A5A5 8F") + fox + h("A5A9 8F") + foy + h("60")


def faceoff(rom):
    found = only(rom, "a9580285a9b9....f005a9a8fd85a9")
    if found < 0:
        return None
    site = found + 15
    pfgoal = u16(rom, found + 6)
    hacked = rom[site] == 0x20 and rom[site + 3] == 0x80
    src = offset(0x80 | site // BANK, u16(rom, site + 1)) + FOX_AT if hacked else site + 85
    fox_v = rom[src] | rom[src + 1] << 8 | rom[src + 2] << 16
    fox, foy = fox_v.to_bytes(3, "little"), (fox_v + 2).to_bytes(3, "little")
    original = faceoff_original(fox, foy)
    if not hacked and not same(rom, site, original):
        return None
    call = lambda to: b"\x20" + w(to) + bytes([0x80, FACEOFF_REGION - 5]) + b"\xea" * (FACEOFF_REGION - 5)
    return new_code(rom, site, call, original, faceoff_code(PENBUF + shift(rom), pfgoal, fox, foy))


NET_BEFORE, NET_WHISTLE = "0c....ad....d0..68", "a9080085a54c"
STILL_BEFORE = "a9060085a5ce....10.."
END_PENALTY_SHOT = "ad....f0..ad....f0..da9c....a9ffff8d....a90a0085a522"
NET_CODE, STILL_CODE = 12, 13


def penalty_shots(rom):
    ending = only(rom, END_PENALTY_SHOT)
    if ending < 0:
        return None
    end_call = b"\x22" + long(ending)
    if not find(rom, end_call.hex()):
        return None
    net_original = only(rom, NET_BEFORE + NET_WHISTLE + "....")
    net_hooked = only(rom, NET_BEFORE + "4c....eaeaeaeaea") if net_original < 0 else -1
    net_found = net_original if net_original >= 0 else net_hooked
    still_found = only(rom, STILL_BEFORE + "22......80..")
    if net_found < 0 or still_found < 0:
        return None
    net, still = net_found + len(NET_BEFORE) // 2, still_found + len(STILL_BEFORE) // 2
    bank = 0x80 | net // BANK
    if net_original >= 0:
        add_penalty = u16(rom, net + 6)
        return [(net, h(NET_WHISTLE) + w(add_penalty), None), (still, b"\x22" + w(add_penalty) + bytes([bank]), None)]
    room = offset(bank, u16(rom, net + 1))
    add_penalty = u16(rom, room + 10)
    add_long = w(add_penalty) + bytes([bank])
    code = end_call + h(NET_WHISTLE) + w(add_penalty) + end_call + h("a9060085a5") + b"\x5c" + add_long
    return [(net, h(NET_WHISTLE) + w(add_penalty), b"\x4c" + w(address(room)) + b"\xea" * 5),
            (still, b"\x22" + add_long, b"\x22" + long(room + NET_CODE)), (room, None, code)]


def extra_attacker(rom):
    """NHL94SNESVault's ExtraAttackerFix, only in ROMs laid out as the original (it uses the original's work memory)."""
    if not in_place(rom):
        return "n/a"
    return [(offset(0x9B, 0x8C96), h("C90100"), h("2078CE")),
            (offset(0x9B, 0xCE78), b"\xff" * 66, h("48 A5A5 18 6D9F1D 8595 AE9F1D E8 A595 20728D CF8F1D9F F007 C695 CA D0F0 "
                                                    "801E CA A5A5 18 6D9F1D ED8B1D 8595 20728D 48 A5A5 86AF 18 6DAF00 8595 "
                                                    "68 207C8D 68 C90100 60"))]


FIND = {"hotColdFix": hot_cold, "ppPkFix": pp_pk, "defenceControl": defence, "oneMinutePenalties": one_minute,
        "noInterference": one_place("38e91f00" + "...." + "bd....890040d0b5a9140038fd....22", 4, "30BD", "80BD"),
        "noPenaltyShots": one_place("...." + "4c....a9ffff8003a900006b8687a20000b5a548", 0, "D003", "D008"),
        "noGoalPosts": goal_posts, "faceoffFix": faceoff, "penaltyShotFixes": penalty_shots,
        "extraAttackerFix": extra_attacker, "yButtonFix": y_button, "comebackFix": comeback, "awarenessFix": awareness}


def strip(rom):
    return rom[0x200:] if len(rom) % BANK == 0x200 else rom


def rom_settings(rom):
    """{hack: True / False} for each hack recognised, "unknown": [...] for hacks whose places hold other code."""
    rom = strip(rom)
    out, unknown = {}, []
    for name in HACKS:
        places = FIND[name](rom)
        if places == "n/a":
            continue
        if places is None:
            unknown.append(name)
            continue
        if all(same(rom, at, o) for at, o, _ in places if o is not None):
            out[name] = False                              # every place as the original game has it
        elif all(hk is not None and same(rom, at, hk) for at, _, hk in places):
            out[name] = True                               # every place, new code included, as the hack has it
        else:
            unknown.append(name)
    if unknown:
        out["unknown"] = unknown
    return out


def changed(settings):
    return {k: v for k, v in settings.items() if k != "unknown" and v}


if __name__ == "__main__":
    import sys
    from pathlib import Path
    for path in sys.argv[1:]:
        s = rom_settings(Path(path).read_bytes())
        print(Path(path).name, changed(s), ("unknown: " + ", ".join(s["unknown"])) if s.get("unknown") else "")
