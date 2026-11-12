"""Per-skater energy over a computer game (2026-11-12, for NOSE4Web's "energy from hits only" decision; used by
gen_injury_baseline.py and snes_injury_baseline.py). Fed once per game second of running clock with each dressed
skater's state (on the ice, on the bench, out) and energy; reports how many skaters went below a third of full (1365
of 4096) and to empty (0), the longest a skater who had played sat on the bench (game seconds), and the longest a
skater stayed on the ice below a third (game seconds: a skater stuck slow)."""
THIRD = 0x1000 // 3


class EnergyTrack:
    def __init__(self):
        self.low, self.played, self.bench, self.tired = {}, set(), {}, {}
        self.bench_max, self.tired_max = (0, None), (0, None)

    def second(self, key, on_ice, on_bench, energy):
        if on_ice:
            self.played.add(key)
            self.low[key] = min(self.low.get(key, 0x10000), energy)
            self.bench[key] = 0
            self.tired[key] = self.tired.get(key, 0) + 1 if energy < THIRD else 0
            if self.tired[key] > self.tired_max[0]:
                self.tired_max = (self.tired[key], key)
        elif on_bench and key in self.played:
            self.bench[key] = self.bench.get(key, 0) + 1
            self.tired[key] = 0
            if self.bench[key] > self.bench_max[0]:
                self.bench_max = (self.bench[key], key)
        else:
            self.bench[key] = self.tired[key] = 0

    def result(self):
        return {"skaters_below_third": sum(v < THIRD for v in self.low.values()),
                "skaters_empty": sum(v == 0 for v in self.low.values()), "skaters_played": len(self.played),
                "longest_bench_s": self.bench_max[0], "longest_bench_who": self.bench_max[1],
                "longest_tired_on_ice_s": self.tired_max[0], "longest_tired_who": self.tired_max[1]}
