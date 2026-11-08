"""One check for a NOSE4Web build (2026-11-08): which of the tested fixes a ROM has, any changed bytes outside them,
and each fix's in-game test on the ROM and on the original, with a pass / fail.

The fixes are found by their bytes (the call sites and changed instructions; the code they call out to may sit
anywhere in the free space, so combined ROMs are found too). The original is the retail ROM of the same layout in the
ROM's folder (nhl94.bin, NHL94.smc, nhl94_2026.sfc for the SA-1 build, nhl94snes_2026.sfc for the 2 MB one) unless
--orig names it. Each test is the study script already written for that fix, at a smaller size (--full: the sizes of
the write-ups in docs/STUDY_NOTES.md), the ROM and the original two at a time in gentle mode. The pass rule for each
is the result the write-up found: the fix's behaviour on the ROM, the bug on the original (a test whose original
doesn't show the bug says so: the test, not the fix, is then in doubt).

python fix_check.py ROM [--orig ORIGINAL] [--full] [--only ID,ID] [--list]"""
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
from paths import RUNS  # noqa: E402

PY = sys.executable

# Each fix: its id, system, and per layout the bytes that mark it ({offset: bytes or None (any)}) and the ranges it
# may change (left out of the "other changes" list). Offsets are file offsets of the original layouts.
G = "genesis"
S = "snes"


def jsr_hi(off):
    """A Genesis call into the free space at the end of the ROM: jsr $000Fxxxx."""
    return {off: bytes.fromhex("4eb9000f")}


FIXES = [
    dict(id="rocket_pass", system=G, name="Rocket pass", sig={"genesis": jsr_hi(0xBF40)},
         spans={"genesis": [(0xBF40, 0xBFAB)]}),
    dict(id="runaway", system=G, name="Runaway speed", sig={"genesis": {**jsr_hi(0xAF76), 0xEBA0: bytes.fromhex("00c8")}},
         spans={"genesis": [(0xAF76, 0xAF7D), (0xEBA0, 0xEBA3), (0xFEFF4, 0xFEFFB)]}),
    dict(id="faceoff_g", system=G, name="Faceoff spots", sig={"genesis": jsr_hi(0x12504)},
         spans={"genesis": [(0x12504, 0x1255B)]}),
    dict(id="ps_table", system=G, name="Penalty-shot table", sig={"genesis": {0x1914E: bytes.fromhex("ffff0038003c0036003a002e00300034")}},
         spans={"genesis": [(0x1914E, 0x19160)]}),
    dict(id="ps_fixes_g", system=G, name="Penalty-shot fixes (retake, ghost puck)",
         sig={"genesis": {0xED0E: bytes.fromhex("02380083c2f2"), **jsr_hi(0x15930)}},
         spans={"genesis": [(0xED0E, 0xED27), (0x15930, 0x15937)]}),
    dict(id="goalie_pull", system=G, name="Computer goalie pull", sig={"genesis": {0xF758: b"\x6f", 0xF760: b"\x6e"}},
         spans={"genesis": [(0xF758, 0xF759), (0xF760, 0xF761)]}),
    dict(id="blind_ring", system=G, name="Blind ring", sig={"genesis": jsr_hi(0x14EC8)},
         spans={"genesis": [(0x14EC8, 0x14ED1)]}),
    dict(id="sniping", system=G, name="Delayed-penalty sniping", sig={"genesis": {0xC422: bytes.fromhex("4e714e71")}},
         spans={"genesis": [(0xC422, 0xC426)]}),
    dict(id="awareness_g", system=G, name="Awareness slip", sig={"genesis": {0xD0E1: b"\x6a", 0xD2D9: b"\x6a"}},
         spans={"genesis": [(0xD0E1, 0xD0E2), (0xD2D9, 0xD2DA)]}),
    dict(id="crowd", system=G, name="Crowd bonus", sig={"genesis": {0xFEF66: bytes.fromhex("4e714e71")}},
         spans={"genesis": [(0xFEF66, 0xFEF6A)]}),
    dict(id="count_deflections", system=G, name="Count stick deflections", sig={"genesis": jsr_hi(0x151D6)},
         spans={"genesis": [(0x151D6, 0x151DE)]}),
    dict(id="faceoff_s", system=S, name="Faceoff spots",
         sig={"retail": {0xF3326: b"\x20", 0xF3328: b"\xff"}, "sa1": {0xF3355: b"\x20", 0xF3357: b"\xff"}},
         spans={"retail": [(0xF3326, 0xF3385)], "sa1": [(0xF3355, 0xF33B4)]}),
    dict(id="ps_fixes_s", system=S, name="Penalty-shot fixes (knocked net, still puck)",
         sig={"retail": {0xF147C: b"\x4c", 0xF147E: b"\xff"}, "sa1": {0xF1480: b"\x4c", 0xF1482: b"\xff"}},
         spans={"retail": [(0xF147C, 0xF1485), (0xF5DA9, 0xF5DAE)], "sa1": [(0xF1480, 0xF1489), (0xF5E2C, 0xF5E31)]}),
    dict(id="extra_attacker", system=S, name="Extra attacker (Edit Lines)", sig={"retail": {0xD8C96: bytes.fromhex("2078ce")}},
         spans={"retail": [(0xD8C96, 0xD8C9A), (0xDCE78, 0xDCEC0)]}),
    dict(id="y_button", system=S, name="Y button while down",
         sig={"retail": {0xF225C: bytes.fromhex("eaea6b")}, "sa1": {0xF227F: bytes.fromhex("eaea6b")}},
         spans={"retail": [(0xF225C, 0xF225E)], "sa1": [(0xF227F, 0xF2281)]}),
    dict(id="comeback", system=S, name="Comeback bonus timing",
         sig={"retail": {0xFCFFB: b"\x30"}, "sa1": {0xFD10B: b"\x30"}, "2mb": {0xFD039: b"\x30"}},
         spans={"retail": [(0xFCFFB, 0xFCFFC)], "sa1": [(0xFD10B, 0xFD10C)], "2mb": [(0xFD039, 0xFD03A)]}),
    dict(id="awareness_s", system=S, name="Awareness slip",
         sig={k: {0xF04A0: b"\x23", 0xF0ACE: b"\x23"} for k in ("retail", "sa1", "2mb")},
         spans={k: [(0xF04A0, 0xF04A1), (0xF0ACE, 0xF0ACF)] for k in ("retail", "sa1", "2mb")}),
]
# never "other changes": the header checksum, the checksum check's call and routine (Genesis), the free space the
# hooks' code goes in
IGNORE = {"genesis": [(0x18E, 0x191), (0x300, 0x307), (0xFE000, 0x100000)],
          "retail": [(0x7FDC, 0x7FE0), (0xF7E00, 0xF8000), (0xDCE00, 0xDD000)],
          "sa1": [(0x7FDC, 0x7FE0), (0xF7E00, 0xF8000)],
          "2mb": [(0x7FDC, 0x7FE0), (0xF7E00, 0xF8000)]}
ORIGINAL = {"genesis": "nhl94.bin", "retail": "NHL94.smc", "sa1": "nhl94_2026.sfc", "2mb": "nhl94snes_2026.sfc"}


def strip(data):
    """An SNES file with a 512-byte copier header in front: without it."""
    return data[0x200:] if len(data) % 0x8000 == 0x200 else data


def layout(data):
    if data[0x100:0x104] == b"SEGA":
        return "genesis"
    if len(data) > 0x100000:
        return "sa1" if data[0x7FD5] == 0x23 else "2mb"
    return "retail"


def found(data, lay):
    out = []
    for fx in FIXES:
        sig = fx["sig"].get(lay)
        if sig and all(data[o:o + len(b)] == b for o, b in sig.items()):
            out.append(fx)
    return out


def other_changes(data, orig, lay, fixes):
    skip = IGNORE[lay] + [s for fx in fixes for s in fx["spans"][lay]]
    runs, i, n = [], 0, min(len(data), len(orig))
    while i < n:
        if data[i] != orig[i] and not any(a <= i < b for a, b in skip):
            j = i
            while j < n and data[j] != orig[j] and not any(a <= j < b for a, b in skip):
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


# --- the tests: each runs the study script on both ROMs and returns (original's result, the ROM's, pass?)

def run(args, env=None):
    e = dict(os.environ, **(env or {}))
    p = subprocess.run([PY, *args], cwd=HERE, capture_output=True, text=True, env=e)
    if p.returncode:
        raise RuntimeError(f"{args[0]} failed: {p.stderr.strip()[-400:]}")
    return p.stdout


def both(make, orig, rom, env=None):
    """make(rom, tag) -> args; runs the original and the ROM side by side."""
    e = dict(os.environ, **(env or {}))
    procs = [subprocess.Popen([PY, *make(r, t)], cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=e)
             for r, t in ((orig, "o"), (rom, "r"))]
    outs = []
    for p in procs:
        out, err = p.communicate()
        if p.returncode:
            raise RuntimeError(err.strip()[-400:])
        outs.append(out)
    return outs


def rows(run_name):
    return [json.loads(l) for l in open(RUNS / run_name / "trials.jsonl")]


def t_rocket(orig, rom, full, lay):
    cases = Path(rom).parent / "rocket_pass_cases.json"
    if not cases.exists():
        return None, None, None, "no rocket_pass_cases.json beside the ROM"
    both(lambda r, t: ["rocket_pass_test.py", f"fc_rocket_{t}", r, str(cases), "40" if full else "10", "60" if full else "8"], orig, rom)
    res = []
    for t in "or":
        sel = [x for x in rows(f"fc_rocket_{t}") if "ratio" in x and x.get("over_1_3") and not x.get("wrong_root")]
        rs = sorted(x["ratio"] for x in sel)
        res.append(rs[len(rs) // 2] if rs else None)
    o, r = res
    return f"rocket cases' speed / intended, median {o}", f"{r}", (r is not None and r <= 1.12 and (o or 0) > 1.15), None


def t_runaway(orig, rom, full, lay):
    both(lambda r, t: ["runaway_fix_test.py", f"fc_runaway_{t}", r, "100" if full else "30"], orig, rom,
         env={"NHL94_RFT_CASES": "takeover,boards,takeover_whiff"})
    c = [sum(1 for x in rows(f"fc_runaway_{t}") if x.get("late", 0) > 10000 and x["res"] == "ok") for t in "or"]
    return f"still fast after the bursts: {c[0]}", f"{c[1]}", c[1] == 0 and c[0] > 0, None


def t_faceoff(system):
    def t(orig, rom, full, lay):
        o, r = both(lambda x, tag: ["faceoff_fix_test.py", system, x, "original" if tag == "o" else "fixed"], orig, rom)
        jo, jr = (json.loads(s.splitlines()[0]) for s in (o, r))
        ok = jr["differ"] <= 0.005 * (jr["agree"] + jr["differ"]) and jo["differ"] <= 0.03 * (jo["agree"] + jo["differ"])
        return (f"spots by its own rule: agree {jo['agree']} / differ {jo['differ']}", f"agree {jr['agree']} / differ {jr['differ']}",
                ok, None)
    return t


def t_ps_table(orig, rom, full, lay):
    both(lambda r, t: ["ps_table_test.py", f"fc_pst_{t}", r, "2000" if full else "500"], orig, rom)
    right = {0x16: 0x38, 0x18: 0x3C, 0x1A: 0x36, 0x1C: 0x3A, 0x1E: 0x2E, 0x20: 0x30}
    res = []
    for t in "or":
        ps = [x for x in rows(f"fc_pst_{t}") if x["res"] == "foul" and x["code"] >= 0x2E and x["plain"] in right]
        res.append((sum(right[x["plain"]] == x["code"] for x in ps), len(ps)))
    (oa, on), (ra, rn) = res
    return f"penalty shots with their own foul's name: {oa} of {on}", f"{ra} of {rn}", rn >= 3 and ra == rn and oa < on, None


def t_ps_fixes_g(orig, rom, full, lay):
    both(lambda r, t: ["ps_fixes_test.py", f"fc_psf_{t}", r, "50" if full else "10"], orig, rom)
    res = []
    for t in "or":
        rs = rows(f"fc_psf_{t}")
        w = Counter(x["res"] for x in rs if x["case"] == "whistle")
        g = [x for x in rs if x["case"] == "ghost" and x["res"] == "ok"]
        res.append((w["retake"], w["faceoff"], sum(x["nc_start"] for x in g), len(g)))
    o, r = res
    return (f"whistle mid-attempt: retakes {o[0]}, faceoffs {o[1]}; ghost puck as the attempt starts {o[2]} of {o[3]}",
            f"retakes {r[0]}, faceoffs {r[1]}; ghost {r[2]} of {r[3]}", r[0] == 0 and r[1] > 0 and r[2] == 0 and o[0] > 0, None)


def t_goalie_pull(orig, rom, full, lay):
    both(lambda r, t: ["goalie_pull_test.py", f"fc_gp_{t}", r, "10" if full else "3"], orig, rom)
    res = []
    for t in "or":
        by = {d: [x["pulled"] for x in rows(f"fc_gp_{t}") if x["deficit"] == d] for d in range(4)}
        res.append({d: f"{sum(v)}/{len(v)}" for d, v in by.items()})
    o, r = res
    ok = int(r[1].split("/")[0]) > 0 and int(r[2].split("/")[0]) > 0 and r[0].startswith("0/") and r[3].startswith("0/") \
        and o[1].startswith("0/")
    return f"pulled when 0/1/2/3 down: {', '.join(o.values())}", ", ".join(r.values()), ok, None


def t_blind_ring(orig, rom, full, lay):
    both(lambda r, t: ["blind_ring_test.py", f"fc_br_{t}", r, "20" if full else "5"], orig, rom, env={"NHL94_BRT_FLAT": "1"})
    c = []
    for t in "or":
        g = [x for x in rows(f"fc_br_{t}") if x["res"] == "goal"]
        c.append(sum(1 for x in g if x["through"] and abs(x["through"]["dx"]) <= 8))
    return f"flat pucks in through his middle: {c[0]}", f"{c[1]}", c[1] == 0 and c[0] > 0, None


def t_sniping(orig, rom, full, lay):
    o, r = both(lambda x, t: ["sniping_test.py", x, "30" if full else "12"], orig, rom)
    pct = lambda s: [int(m) for m in re.search(r"pulled: exact (\d+) of (\d+)", s).groups()]
    (oe, on), (re_, rn) = pct(o), pct(r)
    return f"own goalie pulled, shots exact: {oe} of {on}", f"{re_} of {rn}", oe == on and re_ < 0.85 * rn, None


def t_awareness(system):
    def t(orig, rom, full, lay):
        o, r = both(lambda x, tag: ["awareness_test.py", system, x, "3000" if full else "1500"], orig, rom)
        parse = lambda s: eval(s[s.index("{"):s.rindex("}") + 1])
        po, pr = parse(o), parse(r)
        f = lambda d: f"aidef {d.get('aidef', 0)} / aioff {d.get('aioff', 0)}"
        return (f"forwards' timer reloads with the puck: {f(po)}", f(pr),
                pr.get("aioff", 0) > 3 * pr.get("aidef", 0) and po.get("aidef", 0) > po.get("aioff", 0) * 0.5, None)
    return t


def t_crowd(orig, rom, full, lay):
    o, r = both(lambda x, t: ["crowd_test.py", x], orig, rom)
    speeds = lambda s: [int(m) for m in re.findall(r"top speed (\d+)", s)]   # loud, quiet
    (ol, oq), (rl, rq) = speeds(o), speeds(r)
    return f"top speed loud / quiet: {ol} / {oq}", f"{rl} / {rq}", oq == ol and rq < rl, None


def t_count_deflections(orig, rom, full, lay):
    out = run(["count_deflections_test.py", rom, orig, "300" if full else "80"])
    tot = re.findall(r"shots on goal original (\d+), test (\d+); goals (\d+) / (\d+)", out)
    extra = re.findall(r"shots \+(\d+)", out)
    o = sum(int(a) for a, _, _, _ in tot)
    r = sum(int(b) for _, b, _, _ in tot)
    goals_same = all(c == d for _, _, c, d in tot)
    return f"shots on goal: {o}", f"{r} (never more than +1 a shot: {all(int(x) <= 1 for x in extra)})", \
        r > o and goals_same and all(int(x) <= 1 for x in extra), None


def t_ps_fixes_s(orig, rom, full, lay):
    both(lambda r, t: ["snes_ps_fixes_test.py", f"fc_sps_{t}", r, "40" if full else "12"], orig, rom)
    res = [Counter(x["res"] for x in rows(f"fc_sps_{t}")) for t in "or"]
    o, r = res
    return f"retakes {o['retake']}", f"retakes {r['retake']}, faceoffs {sum(v for k, v in r.items() if k.startswith('faceoff'))}", \
        r["retake"] == 0 and o["retake"] > 0, None


def t_y_button(orig, rom, full, lay):
    if lay != "retail":
        return None, None, None, "the test plays the retail layout's recorded moments only"
    both(lambda r, t: ["snes_y_button_test.py", f"fc_yb_{t}", r, "818" if full else "250"], orig, rom)
    res = []
    for t in "or":
        lk = [x for x in rows(f"fc_yb_{t}") if x["kind"] != "unlocked"]
        res.append((sum(x.get("own_changed", False) for x in lk), len(lk)))
    (oc, on), (rc, rn) = res
    return f"locked frames where Y made the downed skater act: {oc} of {on}", f"{rc} of {rn}", rc == 0 and oc > 0, None


def t_extra_attacker(orig, rom, full, lay):
    o, r = both(lambda x, t: ["snes_extra_attacker_test.py", x], orig, rom)
    twice = lambda s: s.count("the same player twice")
    return f"picks leaving a player twice on the line: {twice(o)}", f"{twice(r)}", twice(r) == 0 and twice(o) > 0, None


def t_comeback(orig, rom, full, lay):
    o, r = both(lambda x, t: ["snes_comeback_test.py", x], orig, rom)
    def halves(s):
        out = {}
        for half in ("first half", "second half"):
            m = re.search(half + r": Home's Checking trailing minus leading \[([^\]]*)\]", s)
            out[half] = max([int(v) for v in m.group(1).split(",") if v.strip()] or [0])
        return out
    ho, hr = halves(o), halves(r)
    return (f"bonus (Checking) in the 3rd period's first / second half: +{ho['first half']} / +{ho['second half']}",
            f"+{hr['first half']} / +{hr['second half']}",
            hr["first half"] == 0 and hr["second half"] > 0 and ho["first half"] > 0, None)


TESTS = dict(rocket_pass=t_rocket, runaway=t_runaway, faceoff_g=t_faceoff("genesis"), ps_table=t_ps_table,
             ps_fixes_g=t_ps_fixes_g, goalie_pull=t_goalie_pull, blind_ring=t_blind_ring, sniping=t_sniping,
             awareness_g=t_awareness("genesis"), crowd=t_crowd, count_deflections=t_count_deflections,
             faceoff_s=t_faceoff("snes"), ps_fixes_s=t_ps_fixes_s, y_button=t_y_button,
             extra_attacker=t_extra_attacker, comeback=t_comeback, awareness_s=t_awareness("snes"))


def main():
    args = sys.argv[1:]
    if "--list" in args:
        for fx in FIXES:
            print(f"{fx['id']:18} {fx['system']:8} {fx['name']} ({', '.join(fx['sig'])})")
        return
    rom = Path(args[0])
    full = "--full" in args
    only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
    data = strip(rom.read_bytes())
    lay = layout(data)
    orig = Path(args[args.index("--orig") + 1]) if "--orig" in args else rom.parent / ORIGINAL[lay]
    od = strip(orig.read_bytes())
    if len(data) != rom.stat().st_size:
        print("(a 512-byte copier header: offsets are without it; the tests need a ROM without one)")
    fixes = found(data, lay)
    print(f"{rom.name}: {lay} layout, against {orig.name}")
    print("Fixes found: " + (", ".join(fx["name"] for fx in fixes) or "none"))
    other = other_changes(data, od, lay, fixes)
    if other:
        print(f"Other changed bytes ({len(other)} runs, not from these fixes): " +
              ", ".join(f"${a:X}-${b - 1:X}" for a, b in other[:12]) + (" ..." if len(other) > 12 else ""))
    else:
        print("No other changed bytes.")
    print()
    results = []
    for fx in fixes:
        if only and fx["id"] not in only:
            continue
        print(f"{fx['name']}: testing ...", flush=True)
        try:
            o, r, ok, note = TESTS[fx["id"]](str(orig), str(rom), full, lay)
        except Exception as ex:                     # noqa: BLE001  (a test that can't run is reported, not fatal)
            o, r, ok, note = None, None, None, f"the test failed to run: {ex}"
        verdict = "PASS" if ok else "not run" if ok is None else "FAIL"
        results.append((fx["name"], verdict))
        print(f"  {verdict}: original {o}; this ROM {r}" if o is not None else f"  {verdict}: {note}", flush=True)
    print("\nSummary: " + "; ".join(f"{n} {v}" for n, v in results))


if __name__ == "__main__":
    main()
