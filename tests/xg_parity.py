"""Checks that the viewer's JavaScript ports agree with the Python they copy (run after changing either):
- XG (viewer.html, "xG model") against tools/xg.py's play_out / Goalie / auto_aim;
- deserveToWin (viewer.html) against tools/deserve.py, on real match files.
Both xG versions are random: each spot and aim is played out N times in each, so differences up to about
3 x sqrt(p(1-p)/N) are noise. Needs node. python tests/xg_parity.py"""
import json
import math
import random
import re

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import deserve  # noqa: E402
import xg  # noqa: E402
from share_game import load_js_object  # noqa: E402

N = 4000
SPOTS = [(0, 150, 1), (40, 200, 1), (-60, 120, 1), (20, 230, 1), (0, -150, 0), (-40, -210, 0), (70, -110, 0)]
GOALIE = {"weight": 6, "agility": 14, "speed": 12, "aidef": 9}
SHOT = {"speed": 20000, "sha": 15}


def block(html, start, end):
    i = html.index(start)
    return html[i:html.index(end, i)]


def node(script):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(script)
    out = subprocess.run(["node", f.name], capture_output=True, text=True)
    Path(f.name).unlink()
    if out.returncode:
        raise SystemExit(out.stderr)
    return json.loads(out.stdout)


def set_spot(px, py, top):
    d3 = 260 if top else -260
    rx, ry = px, max(-259, min(259, py)) - d3
    if rx * rx + ry * ry > 900:
        ln = math.isqrt(int(rx * rx + ry * ry)) + 1
        rx, ry = rx * 26 / ln, ry * 18 / ln
    return rx, ry + d3


def python_spot(px, py, top, one_timer, rng):
    gl = 264 if top else -264
    sx, sy = set_spot(px, py, top)
    g = GOALIE
    goalie = xg.Goalie(sx, sy, 0, 0, g["weight"], g["agility"], g["speed"], g["aidef"])
    reach = 12 if one_timer else xg.REACH[min(19, (g["agility"] + 2) >> 1)]
    pp = max(1, SHOT["speed"] / 68)
    perfect = (SHOT["sha"] + 1) / (SHOT["sha"] + 16)
    out = []
    aims = [None] if one_timer else range(9)
    for d in aims:
        goals = 0
        for _ in range(N):
            dd = xg.auto_aim(px, py, sx, sy, gl) if d is None else d
            tx, tz = xg.AIM[dd]
            if xg.play_out((px, py, 0), (tx, gl, tz), pp, SHOT["sha"], perfect, goalie, reach, 0, rng) == "goal":
                goals += 1
        out.append(goals / N)
    return out


def check_xg(html):
    js = block(html, "const XG = (() => {", "// ---- end of the xG model")
    script = js + f"""
const out = [];
for (const [px, py, top] of {json.dumps(SPOTS)}) {{
  const o = {{speed: {SHOT['speed']}, sha: {SHOT['sha']}, goalie: {json.dumps(GOALIE)}, n: {N}}};
  out.push([XG.spot(px, py, !!top, o).map(r => r.xg), XG.spot(px, py, !!top, {{...o, oneTimer: true}}).map(r => r.xg)]);
}}
console.log(JSON.stringify(out));"""
    js_out = node(script)
    rng = random.Random(1)
    worst = 0
    for (px, py, top), (js_aims, js_ot) in zip(SPOTS, js_out):
        py_aims = python_spot(px, py, top, False, rng)
        py_ot = python_spot(px, py, top, True, rng)
        for a, b in zip(py_aims + py_ot, js_aims + js_ot):
            noise = 3 * math.sqrt(max(a * (1 - a), b * (1 - b), 1 / N) / N) * math.sqrt(2)
            worst = max(worst, abs(a - b) / noise if noise else 0)
            if abs(a - b) > noise:
                print(f"  xG differs at ({px}, {py}): python {a:.3f}, viewer {b:.3f}")
    print(f"xG: worst difference {worst:.2f} of the noise allowance ({'ok' if worst <= 1 else 'CHECK'})")


def check_deserve(html, names):
    fn = block(html, "function deserveToWin(m, upto) {", "\nfunction ")
    consts = block(html, "const DTW_FLURRY_MS", "function deserveToWin(")  # its constants sit just above it
    consts += "const known = () => true, resultAt = sh => sh.result;\n"  # the viewer's live-knowledge helpers, off
    for name in names:
        path = next((d / f"{name}.js" for d in (ROOT / "matches", Path.home() / "Documents" / "NHL94 Viewer" / "matches")
                     if (d / f"{name}.js").exists()), None)
        m = json.loads(load_js_object(path))
        py = deserve.deserve(m)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(m, f)
        js = node(consts + fn + f"""
const m = JSON.parse(require('fs').readFileSync({json.dumps(f.name)}, 'utf8'));
console.log(JSON.stringify(deserveToWin(m, m.t.length - 1)));""")
        Path(f.name).unlink()
        print(f"deserve {name}: python {py}\n{'':{len(name) + 9}}viewer {js}")


SNES_GOALIE = {"weight": 6, "agility": 10, "speed": 10, "aidef": 11}
SNES_SHOT = {"speed": 15000, "sha": 9}


def check_xg_snes(html):
    import xg_snes
    rom_path = ROOT / "roms" / "cd85e387.smc"  # NHL94_Classic, as the helper copies it
    if not rom_path.exists():
        print("SNES xG: no NHL94_Classic copy in roms/, skipped")
        return
    rom = rom_path.read_bytes()
    embedded = json.loads(re.search(r"^const XG_SNES_ROM = (\{.*\});$", html, re.M).group(1))
    fresh = json.loads(json.dumps(xg_snes.map_tables(rom)))
    print(f"SNES xG ROM tables in the viewer: {'same as the ROM gives' if embedded == fresh else 'DIFFERENT from the ROM'}")
    js = block(html, "const XG_SNES = (rom => {", "// ---- end of the SNES xG model")
    js_out = node("const XG_SNES_ROM = " + json.dumps(fresh) + ";\n" + js + f"""
const model = XG_SNES(XG_SNES_ROM), out = [];
for (const [px, py, top] of {json.dumps(SPOTS)}) out.push(model.spot(px, py, !!top, {{speed: {SNES_SHOT['speed']}, sha: {SNES_SHOT['sha']}, goalie: {json.dumps(SNES_GOALIE)}, n: {N}}}).map(r => r.xg));
console.log(JSON.stringify(out));""")
    data, rng, worst = xg_snes.RomData(rom), random.Random(2), 0
    g = SNES_GOALIE
    pp = max(1, SNES_SHOT["speed"] / 136)
    perfect = (SNES_SHOT["sha"] + 1) / (SNES_SHOT["sha"] + 16)
    for (px, py, top), js_aims in zip(SPOTS, js_out):
        gl = 264 if top else -264
        sx, sy = xg_snes.set_spot(px, py, top)
        f = xg_snes.vtoa(px - sx, py - sy)
        facing = (4 if top else 0) if f == 8 else f
        goalie = xg_snes.Goalie(data, sx, sy, 0, 0, facing, data.anim(0xE0FE, facing)[0][0], g["weight"], g["agility"], g["speed"], g["aidef"])
        for d, b in enumerate(js_aims):
            tx, tz = xg_snes.AIM[d]
            a = sum(xg_snes.play_out(px, py, tx, gl, tz, pp, SNES_SHOT["sha"], perfect, goalie, rng) == "goal" for _ in range(N)) / N
            noise = 3 * math.sqrt(max(a * (1 - a), b * (1 - b), 1 / N) / N) * math.sqrt(2)
            worst = max(worst, abs(a - b) / noise)
            if abs(a - b) > noise:
                print(f"  SNES xG differs at ({px}, {py}) aim {d}: python {a:.3f}, viewer {b:.3f}")
    print(f"SNES xG: worst difference {worst:.2f} of the noise allowance ({'ok' if worst <= 1 else 'CHECK'})")


if __name__ == "__main__":
    html = (ROOT / "viewer.html").read_text(encoding="utf-8")
    check_xg(html)
    check_xg_snes(html)
    check_deserve(html, ["2026-10-21_1137_NYI-BOS", "2026-10-14_1540_CGY-BOS", "2026-10-19_2256_TOR-NYI"])
