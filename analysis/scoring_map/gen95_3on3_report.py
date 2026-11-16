"""Summary of gen95_3on3_check.py's runs (2026-11-16): per run the skater counts seen in play (home v away, with tmap,
the goalies pulled and the boxed counts) and how long; the even-strength units; the largest lead in skaters; the
faceoffs (short teams, the centres' spots from the puck); what followed the overtime (a shootout's attempts and
skaters).

python gen95_3on3_report.py JSONL ..."""
import json
import sys
from collections import Counter, defaultdict


def main():
    for path in sys.argv[1:]:
        for line in open(path):
            r = json.loads(line)
            print(f"== {path.split(chr(92))[-1].split('/')[-1]} seed {r['seed']}: frames {r.get('frames')}, OT mark {r.get('ot_flag')},"
                  f" carried {r.get('carried')}, score {r.get('score')}, opts {r.get('opts')}, error {r.get('error')}")
            if r.get("error"):
                continue
            states = Counter()
            units = Counter()
            lead = 0
            for s in r["segments"]:
                if s["stopped"]:
                    continue
                h, a, tm, gl, bx = s["key"]
                n = s["to"] - s["from"] + 4
                states[f"{len(h)}v{len(a)} tmap {tm[0]}/{tm[1]} pulled {int(gl[0])}{int(gl[1])} boxed {bx[0]}/{bx[1]}"] += n
                lead = max(lead, abs(len(h) - len(a)))
                if bx == [0, 0] and gl == [False, False]:
                    units[f"{'-'.join(h)} | {'-'.join(a)}"] += n
            print("  in play (frames):", dict(states.most_common()))
            print("  even strength, no one boxed, goalies in:", dict(units))
            print("  largest lead in skaters in play:", lead)
            fos = r["faceoffs"]
            shorts = [fo for fo in fos if any(fo["short"])]
            cspots = [(fo["spots"].get("HC"), fo["spots"].get("AC")) for fo in fos]
            print(f"  faceoffs {len(fos)}; a team short of its tmap: {[(fo['clock'], fo['home'], fo['away'], fo['tmap'], fo['pulled']) for fo in shorts]}")
            print(f"  centres from the puck at the drops: {cspots[:10]}")
            sh = r["shootout"]
            print(f"  after: {r.get('after')}; shootout {sh['seen']}, attempts {sh['attempts']}, skaters {sh['skaters']}")


if __name__ == "__main__":
    main()
