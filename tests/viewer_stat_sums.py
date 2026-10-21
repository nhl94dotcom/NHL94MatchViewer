"""Renders each match's team stats (headless Edge, every group open, at the end of the game) and checks that the
break-down rows add up to their parents: shot attempts against their outcomes, possession by zone, giveaways and
takeaways by kind, faceoffs by zone, zone entries by kind, aimed shots by height, tapestries by length, carrying shares.
python tests/viewer_stat_sums.py [match names ...]   (default: every match in both game folders)"""
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402

EDGE = Path(r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
FOLDERS = [ROOT, Path.home() / "Documents" / "NHL94 Viewer"]


def edge(profile, url):
    return subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", f"--user-data-dir={profile}", "--virtual-time-budget=20000",
                           "--window-size=1600,1200", "--dump-dom", url], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=180).stdout


def rows(dom):
    box = re.search(r'id="teamStats".*?<table>(.*?)</table>', dom, re.S)
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", box.group(1) if box else "", re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) == 3:
            out.append((cells[1], cells[0], cells[2]))  # label, home, away
    return out


def num(v):
    v = v.split(" (")[0].strip()
    if re.fullmatch(r"\d+:\d\d", v):
        a, b = v.split(":")
        return int(a) * 60 + int(b)
    return int(v) if re.fullmatch(r"-?\d+", v) else None


def parts(v, sep="/"):
    return [int(x) for x in re.findall(r"\d+", v.split("%")[0])] if v not in ("–", "-", "") else None


def check(r, from_start=True):
    """Problems in one table: [(row, team, text)]. A recording that began after the opening faceoff (from_start
    False) has the game's own counts (shots on goal, faceoffs won) from before it began, which the event lists can't
    have: those comparisons are skipped."""
    problems = []
    get = {}
    order = []
    parent = None
    for label, h, a in r:
        if label.startswith("· "):
            key = (parent, label)
        else:
            parent, key = label, (label, None)
        get[key] = (h, a)
        order.append(key)
    g = lambda label, sub=None: get.get((label, sub))
    for team in (0, 1):
        def v(label, sub=None):
            x = g(label, sub)
            return x[team] if x else None
        # shot attempts = counted shots on goal + wide + blocked + saved not counted + goals the game did not count
        att, sog = num(v("Shot attempts") or ""), num(v("Shots on goal") or "")
        if att is not None and sog is not None and from_start:
            rest = sum(num(v(k) or "0") or 0 for k in ("Wide", "Blocked", "Saved, not counted"))
            if att < sog + rest:
                problems.append(("Shot attempts", team, f"{att} < shots on goal {sog} + wide / blocked / not counted {rest}"))
        # possession by zone
        poss = v("Possession")
        if poss:
            total = num(poss)
            zones = [num(v("Possession", f"· {z} zone") or "") for z in ("attacking", "neutral", "defensive")]
            if None not in zones and total is not None and abs(sum(zones) - total) > 1:
                problems.append(("Possession", team, f"zones {zones} add to {sum(zones)}, not {total}"))
        for label, sub in (("Giveaways", "· picked off / lost"), ("Takeaways", "· hit / poke / hook / steal"),
                           ("Zone entries", "· carried / passed / dumped"), ("Tapestry goals", "· 2 / 3 / 4+ passes")):
            if v(label) and v(label, sub):
                whole, split = num(v(label)), parts(v(label, sub))
                if whole is not None and split is not None and sum(split) != whole:
                    problems.append((label, team, f"{sub[2:]} {split} add to {sum(split)}, not {whole}"))
        if v("Faceoffs won") and v("Faceoffs won", "· attacking zone") and from_start:
            won = num(v("Faceoffs won"))
            by_zone = [parts(v("Faceoffs won", f"· {z} zone"))[0] for z in ("attacking", "neutral", "defensive")]
            if sum(by_zone) != won:
                problems.append(("Faceoffs won", team, f"by zone {by_zone} add to {sum(by_zone)}, not {won}"))
        if v("Aimed shots (G / att)") and v("Aimed shots (G / att)", "· high"):
            whole = parts(v("Aimed shots (G / att)"))
            split = [parts(v("Aimed shots (G / att)", s)) for s in ("· high", "· middle", "· at the ice")]
            if [sum(p[0] for p in split), sum(p[1] for p in split)] != whole:
                problems.append(("Aimed shots", team, f"high / middle / ice {split} don't add to {whole}"))
        if v("Carried by D / C / W"):
            shares = parts(v("Carried by D / C / W"))
            if shares and not 98 <= sum(shares) <= 102:
                problems.append(("Carried by D / C / W", team, f"{shares} add to {sum(shares)}%"))
            lr = [parts(v("Carried by D / C / W", s)) for s in ("· LD / RD", "· LW / RW")]
            if shares and all(lr) and (abs(sum(lr[0]) - shares[0]) > 2 or abs(sum(lr[1]) - shares[2]) > 2):
                problems.append(("Carried by D / C / W", team, f"sides {lr} don't add to D {shares[0]} / W {shares[2]}"))
        if v("Body checks") and v("Body checks", "· shoulder / hip / cross-check"):
            checks, kinds = num(v("Body checks")), parts(v("Body checks", "· shoulder / hip / cross-check"))
            if checks is not None and kinds and sum(kinds) > checks:
                problems.append(("Body checks", team, f"kinds {kinds} more than {checks}"))
    return problems


def main(names):
    with tempfile.TemporaryDirectory() as profile:
        # open every group: the viewer remembers closed groups in localStorage (shared by all file:// pages)
        opener = Path(profile) / "open.html"
        opener.write_text("<script>localStorage.setItem('nhl94-closed-groups', '[]')</script>", encoding="utf-8")
        edge(profile, opener.as_uri())
        bad = total = 0
        for folder in FOLDERS:
            for path in sorted((folder / "matches").glob("*.js")):
                name = path.stem
                if name == "season" or name.startswith("_") or "_state" in name or (names and name not in names):
                    continue
                m = json.loads(load_js_object(path))
                end = round((m["t"][-1] - m["t"][0]) / 1000) + 1
                r = rows(edge(profile, (folder / "viewer.html").as_uri() + f"?match={name}&t={end}"))
                total += 1
                if not r:
                    print(f"FAIL {name}: no team stats table")
                    bad += 1
                    continue
                first = [m["stats"]["home"][0], m["stats"]["away"][0]] if m.get("stats", {}).get("home") else [[0], [0]]
                problems = check(r, from_start=not any(any(row[:m["stats"]["n"]]) for row in first) if m.get("stats") else True)
                if problems:
                    bad += 1
                    print(f"FAIL {name} ({len(r)} rows)")
                    for row, team, text in problems:
                        print(f"     {row} [{m.get('abbr', ['H', 'A'])[team]}]: {text}")
                else:
                    print(f"ok   {name} ({len(r)} rows)", flush=True)
        print(f"\n{bad} of {total} matches with problems")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
