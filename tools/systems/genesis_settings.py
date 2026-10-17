"""The gameplay settings a Genesis NHL '94 ROM carries: the league editors' hacks (rating scale, hot / cold bonuses,
weight and C-then-B check fixes, base weight, goalie hold time and range, energy, speed burst, turning, clock, three
stars ...), read from the ROM's own code.

Where each setting lives, and the code each hack leaves, come from the NOSE4Web editor
(github.com/nhl94dotcom/NOSE4Web, src/core/hacks.ts), which ports smozoma's smozROM hacks and the findings posted on
the NHL94 forums by wboy, Tony H, clockwise, smozoma, Brodeur30, kingraph and AverageRangersFan. Only ROMs of the
original game and the 30-team ROM built on it (product code GM T-50656) have them at these places.

`rom_settings(rom)` returns {name: value} for every setting it recognises; a setting whose code is not one of the known
versions is left out (its name is in "unknown")."""

ORIGINAL = {
    "ratingScale": "0-6", "bonuses": "original", "weightFix": "off", "checkFix": False, "bodychecks": "off",
    "secondAssist": False, "plusMinus": False, "threeStars": "original", "baseWeight": 140, "goalieHold": 140,
    "goalieWidth": 36, "goalieOut": 231, "goalieLine": 170, "stamina": False, "energyDrain": 33, "energyRecovery": 9,
    "speedBurst": 0, "turnRate": 150, "realTimeClock": False,
}

PRODUCT_CODE_AT = 0x180


def _b(text):
    return bytes.fromhex(text.replace(" ", ""))


def _is(rom, at, wanted):
    return rom[at:at + len(wanted)] == wanted


def _u16(rom, at):
    return (rom[at] << 8) | rom[at + 1]


def _hooked(rom, at, original_len, code):
    """Whether the instructions at `at` were replaced by a call (JSR) to `code`, padded with NOPs."""
    if _u16(rom, at) != 0x4EB9:
        return False
    if any(_u16(rom, at + o) != 0x4E71 for o in range(6, original_len, 2)):
        return False
    target = int.from_bytes(rom[at + 2:at + 6], "big")
    return _is(rom, target, code)


def _site(rom, at, lead, negative=False):
    """A number kept in the game's code, recognised by the instruction just before it."""
    lead = _b(lead)
    if not _is(rom, at - len(lead), lead):
        return None
    value = _u16(rom, at)
    if not negative:
        return value
    signed = value - 0x10000 if value >= 0x8000 else value
    return -signed if signed <= 0 else None


def _same(values):
    return values[0] if values and all(v is not None and v == values[0] for v in values) else None


def _switch(rom, at, original, hacked):
    if _is(rom, at, _b(original)):
        return False
    if _is(rom, at, _b(hacked)):
        return True
    return None


def _stars_code(goal, assist, shot_for, check, goals_against, shots_against, shutout):
    w = lambda v: f"{v & 0xFFFF:04x}"
    return _b(
        f"324A 362A 000C 966B 000C 48C3 7819 4EB9 0000 9F40 4440 D044 2883 4241 122A 00CE C2FC {w(assist)} 4242 142A 00E8 "
        f"B840 6200 0026 D394 C4FC {w(shot_for)} D594 4241 122A 00B4 C2FC {w(goal)} D394 4241 122A 0102 C2FC {w(check)} "
        f"D394 6000 003A BA69 0136 6200 0032 4A42 6700 002C E281 D394 4241 122A 00B4 4A41 6600 0008 0694 0000 {w(shutout)} "
        f"C3FC {w(goals_against)} D394 4A43 6A00 0004 5382 C4FC {w(shots_against)} D594 5449 524A 584C 51CC FF84 4E75 "
        f"FFFF FFFF FFFF")


STARS = {
    "original": _b(
        "324A 362A 000C 966B 000C 48C3 7819 4EB9 0000 9F40 4440 D044 2883 B840 6200 003C 4241 122A 00B4 C2FC 2AF8 D394 "
        "4241 122A 00CE C2FC 2774 D394 4241 122A 00E8 C2FC 000A 4A43 6600 000E C2FC 0064 D394 4281 D269 0136 D394 6000 "
        "003A BA69 0136 6200 0032 4241 122A 00B4 C2FC 0064 4242 142A 00E8 6700 001E 82C2 B27C 0004 6200 0014 0694 0000 "
        "7D00 4A41 6600 0008 0694 0001 24F8 5449 524A 584C 51CC FF7E 4E75"),
    "linesOff": _stars_code(11000, 7000, 500, 500, -11000, 4000, 16000),
    "linesOn": _stars_code(14300, 9100, 650, 650, -11000, 4500, 20800),
}

WEIGHT_CODE = _b("3F01 902A 0067 122B 0067 E201 D001 E201 D001 122B 0075 E301 D001 0400 000E 321F 4E75")
CHECK_CODES = {
    "on": _b("5268 0010 0839 0000 00FF C2EA 6600 002A 4240 102B 0066 D0C0 5228 0102 90C0 90FC 0364 B7CA 6E00 0006 "
             "D0FC 06C8 4240 102A 0066 D0C0 5228 011C 4E75"),
}
for _branch in ("002A", "002E"):
    CHECK_CODES["earlier " + _branch] = _b(
        f"0839 0000 00FF C2EA 6600 {_branch} 5268 0010 4240 102B 0066 D0C0 5228 0102 90C0 90FC 0364 B7CA 6E00 0006 "
        f"D0FC 06C8 4240 102A 0066 D0C0 5228 011C 4E75")
ASSIST_CODE = _b("B068 001A 6700 0008 3168 001A 001C 4E75")
PLUS_MINUS_CODE = _b(
    "0678 001E B8A2 48E7 E0C0 0838 0005 C2F4 6700 0010 0838 0000 C2FA 6600 0006 08C0 0006 B4FC C6CE 6700 0006 08C0 "
    "0007 307C DEF6 3210 D0F8 DEF4 5E78 DEF4 5E78 DEF4 3210 10C0 5248 700B 327C B04A 323C 0080 343C FF10 B451 6600 "
    "000A 10FC 00FF 6000 0006 10E9 0066 D2C1 51C8 FFEA 4CDF 0307 4E75")
PLUS_MINUS_CLEAR = _b(
    "4CDF 0E00 203C 0000 06C7 307C C6CE 4218 51C8 FFFC 307C DEF4 3010 5440 4218 51C8 FFFC 48E7 0070")
ON_ICE_CODE = _b("D3FC 0000 01B2 3F02 3438 BF14 0442 0010 D441 1231 2000 341F 4E75")


def is_supported(rom):
    """Whether a ROM is one the settings can be read from (the original game or the 30-team ROM built on it)."""
    return len(rom) >= 0xFB000 and rom[PRODUCT_CODE_AT:PRODUCT_CODE_AT + 10] == b"GM T-50656"


def rom_settings(rom):
    """The settings recognised in a Genesis NHL '94 ROM (bytes). Returns {} for other ROMs."""
    if not is_supported(rom):
        return {}
    found, unknown = {}, []

    def put(name, value):
        if value is None:
            unknown.append(name)
        else:
            found[name] = value

    # Rating scale and the hot / cold bonuses: how play applies them (the on-ice code) and what Edit Lines shows.
    scale = "0-6" if _is(rom, 0xF711C, _b("3F03 E543 D65F")) else "0-15" if _is(rom, 0xF711C, _b("4E71 E343 4E71")) else None
    put("ratingScale", scale)
    if _is(rom, 0xF710A, _b("D3FC 0000 01A2 1231 1000")):
        on_ice = "one value per player"          # the original code: one bonus for all of a player's ratings
    elif _is(rom, 0xF710A, _b("4201 4E71 4E71 4E71 4E71")):
        on_ice = "none"
    elif _hooked(rom, 0xF710A, 10, ON_ICE_CODE):
        on_ice = "per rating"                    # each rating takes its own bonus, as Edit Lines shows them
    else:
        on_ice = None
    put("bonusesOnIce", on_ice)
    shown_at = {"0-6": (0xFAAB4, 0xFAAD4), "0-15": (0xFAAAC, 0xFAAC8)}.get(scale)
    if shown_at:
        players = {"0-6": ("1E14 4E71", "D634 0000"), "0-15": ("1E2C 0000", "D62C 0000")}[scale]
        if all(_is(rom, at, _b(code)) for at, code in zip(shown_at, ("4207 4E71", "4E71 4A43"))):
            shown = "not shown"
        elif all(_is(rom, at, _b(code)) for at, code in zip(shown_at, players)):
            shown = "as played"
        else:
            shown = "per rating"
        put("bonusesShown", shown)

    weight_original = _is(rom, 0x13D72, _b("902B 0067 D02A 0067"))
    put("weightFix", "off" if weight_original else "simple" if _is(rom, 0x13D72, _b("902A 0067 D02B 0067"))
        else "on" if _hooked(rom, 0x13D72, 8, WEIGHT_CODE) else None)
    # The check's base: moveq #120, then beq over asl #1 (doubled to 240 for a checker a person controls).
    # NOPing the beq (the editor's checkFix) gives everyone 240, and so the weight bug; NOPing the asl gives everyone
    # 120, which fixes both the weight bug and the C-then-B check (a ROM hacker's suggestion): "120".
    put("checkFix", {"6700 0004 E340": False, "4E71 4E71 E340": True, "6700 0004 4E71": "120",
                     "4E71 4E71 4E71": "120"}.get(rom[0x13D6C:0x13D72].hex(" ", 2).upper()))

    if _is(rom, 0x14130, _b("5268 0010 4240 102B 0066 D0C0 5228 011C")) and _is(rom, 0x12302, _b("D532 0000")):
        body = "off"
    elif _is(rom, 0x12302, _b("4E71 4E71")):
        body = next(("on" if name == "on" else "earlier" for name, code in CHECK_CODES.items()
                     if _hooked(rom, 0x14130, 16, code)), None)
    else:
        body = None
    put("bodychecks", body)

    if all(_is(rom, at, _b("3168 001A 001C")) for at in (0x10188, 0xF6CE4)):
        put("secondAssist", False)
    else:
        put("secondAssist", True if all(_hooked(rom, at, 6, ASSIST_CODE) for at in (0x10188, 0xF6CE4)) else None)

    if _is(rom, 0x1494A, _b("0678 001E B8A2")):
        put("plusMinus", False)
    else:
        put("plusMinus", True if _hooked(rom, 0x1494A, 6, PLUS_MINUS_CODE) and _is(rom, 0x17132, PLUS_MINUS_CLEAR) else None)

    put("threeStars", next((name for name, code in STARS.items() if _is(rom, 0x1867E, code)), None))
    base = _u16(rom, 0x8E92)
    put("baseWeight", base if 102 <= base <= 152 and base % 2 == 0 else None)

    frames, never = _site(rom, 0x1530E, "357C"), _switch(rom, 0xD4C6, "9F6B", "6002")
    put("goalieHold", None if frames is None or never is None or frames == 0 else 0 if never else frames)
    put("goalieWidth", _same([_site(rom, 0xB632, "0C53"), _site(rom, 0xB650, "0C53", True)]))
    put("goalieOut", _same([_site(rom, 0xB66A, "0C6B"), _site(rom, 0xB674, "0C6B", True)]))
    put("goalieLine", _same([_site(rom, 0xD3EA, "B27C"), _site(rom, 0xD3F2, "B27C", True)]))
    put("stamina", _switch(rom, 0x15782, "3580", "6002"))
    put("energyDrain", _site(rom, 0x10D42, "0440"))
    put("energyRecovery", _site(rom, 0x7A1A, "0672"))
    if _is(rom, 0xBB88, _b("EE48")):
        put("speedBurst", 0)
    else:
        put("speedBurst", rom[0xBB89] if rom[0xBB88] == 0x70 and 1 <= rom[0xBB89] <= 0x7F else None)
    put("turnRate", _same([_site(rom, 0x10E24, "066B"), _site(rom, 0x10E32, "046B"),
                           _site(rom, 0x10E48, "066B"), _site(rom, 0x10E56, "046B")]))
    clock = [_site(rom, 0x15DEC, "0478"), _site(rom, 0x128CC, "0678"), _site(rom, 0x15E32, "0478")]
    put("realTimeClock", False if clock == [0x0AAA, 0x0018, 0x0AAA] else True if clock == [0x0444, 0x003C, 0x0444] else None)
    if unknown:
        found["unknown"] = unknown
    return found


def changed(settings):
    """The settings that differ from the original game's, as {name: value}."""
    original = dict(ORIGINAL, bonusesOnIce="one value per player", bonusesShown="per rating")
    return {k: v for k, v in settings.items() if k != "unknown" and original.get(k) != v}


if __name__ == "__main__":
    import sys
    from pathlib import Path
    for path in sys.argv[1:]:
        settings = rom_settings(Path(path).read_bytes())
        print(Path(path).name, changed(settings) if settings else "(not a supported ROM)",
              ("unknown: " + ", ".join(settings["unknown"])) if settings.get("unknown") else "")
