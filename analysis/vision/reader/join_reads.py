"""join_reads.py A.json B.json ... OUT.json: reads of consecutive stretches (run_reader, one per worker) joined into one;
each later read's track ids (tracks, carrier, stars) moved past every earlier one's, since each reader numbers its
tracks from 0 and the pseudo match keeps a track id's player for good (2026-11-19: joined plainly, game 4's second half
read the right team 35% of the time)."""
import json
import sys
*ins, out = sys.argv[1:]
rows, off = [], 0
for p in ins:
    r_ = json.load(open(p))
    top = 0
    for r in r_:
        if r.get("tracks"):
            r["tracks"] = [[t[0] + off] + list(t[1:]) for t in r["tracks"]]
            top = max([top] + [t[0] for t in r["tracks"]])
        if r.get("carrier") is not None:
            r["carrier"] += off
        if r.get("stars"):
            r["stars"] = {str(int(k) + off): v for k, v in r["stars"].items()}
    rows += r_
    off = top + 1
json.dump(rows, open(out, "w"))
print(out, len(rows), "rows")
