"""Boot the retail SNES ROM to a live game (pad 1 home, Los Angeles v Montreal, the defaults) and save snes_top.state
(period 1, home shooting at the top net) and snes_bottom.state (period 2, the bottom net). Run once, after copying
the Snes9x core (paths.SNES_CORE_SOURCE -> paths.SNES_CORE)."""
from paths import SNES_STATE_TOP, SNES_STATE_BOTTOM
from snes_emu import SnesEmu

PERIOD, CLOCK, SFLAGS = 0x1630, 0x1632, 0x15D8

e = SnesEmu()
for i in range(12):                          # title, menus, matchups, the "Start Game" menu at the rink
    e.run(200); e.run(4, hold=["START"]); e.run(4)
for f in range(3000):
    e.run(1)
    if e.w(CLOCK) < 599 and e.w(SFLAGS) == 0:
        break
assert e.w(PERIOD) == 0 and e.w(SFLAGS) == 0, (e.w(PERIOD), hex(e.w(SFLAGS)))
open(SNES_STATE_TOP, "wb").write(e.serialize())
e.setw(CLOCK, 3)
for i in range(3000):
    e.run(6, hold=(["START"] if i % 8 == 0 else []))
    if e.w(PERIOD) == 1 and e.w(SFLAGS) == 0 and 0 < e.w(CLOCK) < 599:
        break
assert e.w(PERIOD) == 1 and e.w(SFLAGS) == 0
open(SNES_STATE_BOTTOM, "wb").write(e.serialize())
print("ok", e.w(CLOCK))
