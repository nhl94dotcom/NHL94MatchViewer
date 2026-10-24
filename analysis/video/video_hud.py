"""Reading the Genesis HUD in a RetroArch video (2026-10-23): the clock box (period, minutes, seconds) and the score box
(each team's letters and score). The font is the game's 8 x 8, stretched to 10 pixels wide by the video (the game
draws 256 wide, the video is 320): the cells sit on a 10-pixel pitch. Characters are read by the nearest of a set of
glyph pictures (`font.npz`), learned from a video lined up with a Helper recording (`learn`: the recording says what
each cell shows).
python analysis/video/video_hud.py learn <video> <capture folder> <align.json> <font.npz>
python analysis/video/video_hud.py test <video> <capture folder> <align.json> <font.npz>"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
import video_pilot as VP  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

TOP, BOTTOM = 192, 208                      # the text rows' first lines (8 rows each)
CELLS = {"period": (TOP, 11), "min": (TOP, 41), "s10": (TOP, 61), "s1": (TOP, 71),
         "top1": (TOP, 241), "top2": (TOP, 251), "top3": (TOP, 261), "top_score10": (TOP, 281), "top_score": (TOP, 291),
         "bot1": (BOTTOM, 241), "bot2": (BOTTOM, 251), "bot3": (BOTTOM, 261), "bot_score10": (BOTTOM, 281), "bot_score": (BOTTOM, 291)}


def cell(a, name):
    y, x = CELLS[name]
    return a[y:y + 8, x - 1:x + 9].min(axis=2).astype(np.float32) / 255     # white text: every channel high


def hud_shown(a):
    """The two boxes' dark backgrounds where no text is drawn."""
    return a[201:206, 238:300].mean() < 70 and a[188:191, 10:80].mean() < 90


def truth(cap, i, abbr):
    """What each cell shows at sample i (from the recording). The score box: the away team on top (2026-10-23 games)."""
    clock, period = cap.word(i, 0xC468), cap.word(i, 0xC466)
    home, away = cap.word(i, 0xC6DA), cap.word(i, 0xCA3E)
    t = {"period": str(period + 1), "min": str(clock // 60), "s10": str(clock % 60 // 10), "s1": str(clock % 10)}
    for row, team, score in (("top", abbr[1], away), ("bot", abbr[0], home)):
        letters = team.ljust(3)
        for n in range(3):
            t[f"{row}{n + 1}"] = letters[n] if letters[n] != " " else "_"
        t[f"{row}_score10"] = str(score // 10) if score >= 10 else "_"
        t[f"{row}_score"] = str(score % 10)
    return t


def samples(video, folder, align, every):
    cap, fc = VP.recording(folder)
    st = json.load(open(align))
    good = {a for a, b, k, s in st if s >= 0.6}
    live = [i for i in range(cap.count) if cap.byte(i, 0xFFF7) == 0 and (i // 600) * 600 in good][::every]
    req = sorted({int(fc[i] + VP.offset_at(st, i)): i for i in live}.items())
    F = VP.Frames(video)
    for j, i in req:
        yield cap, i, F.get(j)
        breathe()


def abbr_of(folder):
    """The two teams' letters (home, away) from the capture folder's name (date_time_HOME-AWAY)."""
    return Path(folder).name.split("_")[-1].split("-")


def learn(video, folder, align, out):
    sums, counts = defaultdict(lambda: np.zeros((8, 10), np.float32)), Counter()
    ab = abbr_of(folder)
    for cap, i, a in samples(video, folder, align, 20):
        if not hud_shown(a):
            continue
        t = truth(cap, i, ab)
        for name in CELLS:
            sums[t[name]] += cell(a, name)
            counts[t[name]] += 1
    keys = sorted(sums)
    np.savez(out, keys=np.array(keys), glyphs=np.stack([sums[k] / counts[k] for k in keys]),
             counts=np.array([counts[k] for k in keys]))
    print({k: counts[k] for k in keys})


class Reader:
    def __init__(self, font):
        d = np.load(font)
        self.keys, self.glyphs = list(d["keys"]), d["glyphs"]

    def char(self, a, name):
        """The nearest glyph of the kind the cell holds (the game draws 0 and O almost alike)."""
        c = cell(a, name)
        e = ((self.glyphs - c) ** 2).sum(axis=(1, 2))
        letters = name[:3] in ("top", "bot") and "score" not in name
        allowed = [k.isalpha() or k == "_" if letters else k.isdigit() or k == "_" for k in self.keys]
        e = np.where(allowed, e, np.inf)
        return self.keys[int(np.argmin(e))]

    def read(self, a):
        """{'period', 'clock' (seconds), 'top', 'bottom' (letters), 'top_score', 'bottom_score'}, or None (no HUD)."""
        if not hud_shown(a):
            return None
        r = {n: self.char(a, n) for n in CELLS}
        num = lambda *cs: int("".join(c for c in cs if c != "_")) if all(c.isdigit() or c == "_" for c in cs) \
            and any(c.isdigit() for c in cs) else None
        clock = num(r["min"]), num(r["s10"]), num(r["s1"])
        return {"period": num(r["period"]),
                "clock": clock[0] * 60 + clock[1] * 10 + clock[2] if None not in clock else None,
                "top": "".join(r[f"top{n}"] for n in (1, 2, 3)).strip("_"),
                "bottom": "".join(r[f"bot{n}"] for n in (1, 2, 3)).strip("_"),
                "top_score": num(r["top_score10"], r["top_score"]), "bottom_score": num(r["bot_score10"], r["bot_score"])}


def test(video, folder, align, font):
    R, ok, n = Reader(font), Counter(), 0
    ab = abbr_of(folder)
    for cap, i, a in samples(video, folder, align, 37):
        got = R.read(a)
        if got is None:
            ok["no HUD"] += 1
            continue
        t = truth(cap, i, ab)
        n += 1
        clock = cap.word(i, 0xC468)
        ok["period"] += got["period"] == cap.word(i, 0xC466) + 1
        ok["clock"] += got["clock"] is not None and abs(got["clock"] - clock) <= 1
        ok["teams"] += got["top"] == ab[1] and got["bottom"] == ab[0]
        ok["score"] += got["top_score"] == cap.word(i, 0xCA3E) and got["bottom_score"] == cap.word(i, 0xC6DA)
    print(Path(folder).name, n, "frames read:", {k: f"{v}/{n}" if k != "no HUD" else v for k, v in ok.items()})


if __name__ == "__main__":
    gentle()
    cmd = sys.argv[1]
    if cmd == "learn":
        learn(*sys.argv[2:6])
    else:
        test(*sys.argv[2:6])
