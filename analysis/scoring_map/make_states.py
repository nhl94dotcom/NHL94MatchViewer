"""Boot the test ROM to a live game (pad 1 home, Montreal v Los Angeles, the defaults) and save live.state (period 1,
home shooting at the top net) and live_p2.state (period 2, the bottom net)."""
from emu import Emu
from paths import STATE_TOP, STATE_BOTTOM

e = Emu()
for i in range(6):
    e.run(150); e.run(4, hold=["START"]); e.run(4)
e.run(440)
assert e.b(0xFFF7) == 0 and e.w(0xC466) == 0
open(STATE_TOP, "wb").write(e.serialize())
e.setw(0xC468, 3)
for i in range(1500):
    e.run(6, hold=(["START"] if i % 8 == 0 else []))
    if e.w(0xC466) == 1 and e.b(0xFFF7) == 0 and 0 < e.w(0xC468) < 598:
        break
assert e.w(0xC466) == 1
open(STATE_BOTTOM, "wb").write(e.serialize())
print("ok", e.w(0xC468))
