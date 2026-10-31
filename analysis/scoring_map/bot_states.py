"""The scripted bot's starting point (2026-10-31): the retail ROM (copy it into the work folder as nhl94_retail.bin;
the Helper keeps one in roms/ as 9438f5dd_a738ea1c.bin) booted to the opening faceoff with the game's default setup
(Regular Season, one player on Home, Montreal v Los Angeles, penalties and line changes off) and 5-minute periods.
Writes bot_start.state. python bot_states.py"""
from emu import Emu
from paths import WORK

RETAIL = WORK / "nhl94_retail.bin"
BOT_STATE = WORK / "bot_start.state"


def main():
    e = Emu(RETAIL)
    for _ in range(3):                      # title screens to the game setup
        e.run(150); e.run(4, hold=["START"]); e.run(4)
    e.run(150)
    for _ in range(4):                      # down to Per. Length, one step left: 10 -> 5 minutes
        e.run(4, hold=["DOWN"]); e.run(20)
    e.run(4, hold=["LEFT"]); e.run(20)
    for _ in range(3):                      # on to the opening faceoff
        e.run(150); e.run(4, hold=["START"]); e.run(4)
    e.run(300)
    assert e.b(0xFFF7) == 0 and e.w(0xC466) == 0, "not in play"
    BOT_STATE.write_bytes(e.serialize())
    print("ok: clock", e.w(0xC468), "teams", e.b(0xC6F7), e.b(0xCA5B))


if __name__ == "__main__":
    main()
