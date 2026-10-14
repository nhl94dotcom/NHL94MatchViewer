"""Writes a match as one self-contained page to send to someone: shared/<teams, score, name>.html.

The same file the viewer's "Save game file" button makes: viewer.html with the rink picture (rink_gens.js), the
bench masks (rink_benches.js), and the match and its ROM's sprite library gzipped and base64'd inside
(window.NHL94_PACKED), which the page unpacks when it opens. Used by the helper; also from the command line:

    python tools/share_game.py <match name>
"""
import base64
import gzip
import json
import os
import re
import sys
from pathlib import Path

# Where games, replays, sprites and settings live: the project folder, or NHL94_HOME (the packaged helper sets it to
# a folder in Documents, since a single .exe cannot write beside its own files).
ROOT = Path(os.environ["NHL94_HOME"]) if os.environ.get("NHL94_HOME") else Path(__file__).resolve().parent.parent


def load_js_object(path):
    """The object in a `window.NAME = {...};` file."""
    text = path.read_text(encoding="utf-8")
    return text[text.index("{"):text.rindex("}") + 1]


def pack(text):
    return base64.b64encode(gzip.compress(text.encode("utf-8"), 9)).decode("ascii")


def make_game_file(name, out_dir=None):
    match_text = load_js_object(ROOT / "matches" / f"{name}.js")
    match = json.loads(match_text)
    packed = {"match": pack(match_text)}
    rom = match.get("rom")
    if rom and (ROOT / "sprites" / f"{rom}.js").exists():
        packed["sprites"] = pack(load_js_object(ROOT / "sprites" / f"{rom}.js"))
    data = ["<script>", '// The game, packed by tools/share_game.py.']
    rink = ROOT / "rink_gens.js"
    if rink.exists():
        data.append(rink.read_text(encoding="ascii").strip())
    benches = ROOT / "rink_benches.js"
    if benches.exists():
        data.append(benches.read_text(encoding="utf-8").strip())
    data.append("window.NHL94_PACKED = " + json.dumps(packed) + ";")
    data.append("</script>")
    page = (ROOT / "viewer.html").read_text(encoding="utf-8")
    tag = '<script src="rink_gens.js"></script>'
    assert page.count(tag) == 1, "viewer.html no longer loads rink_gens.js the expected way"
    page = page.replace(tag, "\n".join(data))
    score = f"{match['score'][-2]}-{match['score'][-1]}" if len(match.get("score", [])) >= 2 else ""
    title = f"{match.get('team1', 'Home')} {score} {match.get('team2', 'Away')}"
    page = re.sub(r"<title>[^<]*</title>", lambda _: f"<title>{title.replace('<', '').replace('&', '')} · NHL '94</title>", page, count=1)
    out_dir = Path(out_dir or ROOT / "shared")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / (re.sub(r"[^\w.-]+", "_", f"{title} {name}") + ".html")
    target.write_text(page, encoding="utf-8")
    return target


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python tools/share_game.py <match name>")
    path = make_game_file(sys.argv[1])
    print(f"{path} ({path.stat().st_size / 1048576:.1f} MB)")
