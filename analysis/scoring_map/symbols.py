"""Symbols from the test ROM's build listing (paths.LISTING): equates and rs variables
("ADDR =VALUE  name equ/rs ...") and code / data labels (a name at the start of the source column). sym['puckc'] etc."""
import json
import re
from pathlib import Path

from paths import LISTING as LST, WORK

CACHE = WORK / "symbols.json"
SRC_COL = 36


def load():
    if CACHE.exists() and CACHE.stat().st_mtime > LST.stat().st_mtime:
        return json.loads(CACHE.read_text())
    sym = {}
    for line in LST.read_text(encoding="latin-1").splitlines():
        if len(line) < 10 or not re.match(r"[0-9A-F]{8}", line):
            continue
        m = re.match(r"([0-9A-F]{8}) =([0-9A-F]{8})\s+([A-Za-z_.][\w.]*)\s+(equ|rs\.[bwl]|=|set|rs)\b", line, re.I)
        if m:
            sym.setdefault(m.group(3), int(m.group(2), 16))
            continue
        src = line[SRC_COL:] if len(line) > SRC_COL else ""
        m = re.match(r"([A-Za-z_][\w]*):?(\s|$)", src)
        if m and not src[:1].isspace() and m.group(1).lower() not in ("include", "even", "if", "else", "endif", "endm"):
            sym.setdefault(m.group(1), int(line[:8], 16))
    CACHE.write_text(json.dumps(sym))
    return sym


if __name__ == "__main__":
    import sys
    s = load()
    print(len(s))
    for n in sys.argv[1:]:
        print(n, hex(s[n]) if n in s else None)
