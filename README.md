# NHL '94 Viewer

Records NHL '94 (Sega Genesis) games played in RetroArch with the Genesis Plus GX core, and replays them from above
in the browser: game sprites, a rotatable and zoomable rink, a follow camera, team and player stats, shot, heat,
turnover and pass maps, a goalie report, clips (video or GIF) and single-file game pages to share.

Windows only: it reads the game's memory out of the running RetroArch process (read only).

## Use it

- **With Python 3**: double-click `NHL94 Helper.bat` and leave its window open while you play. Games are listed at
  http://localhost:9494/helper.html. Run `python tools/embed_rink.py` once first, to make `rink_gens.js`.
- **Without Python**: build `dist\NHL94 Helper.exe` with `tools\build_helper.bat` (needs
  `python -m pip install pyinstaller`). It also writes `dist\NHL94 Helper.zip`, the exe with
  `tools/tester_readme.txt` as "Read me first.txt", which is what to hand to someone else.

## Not in this repository

- Recordings (`captures/`), converted games (`matches/`) and game files (`shared/`): large, and personal to whoever played.
- ROMs, and the sprites extracted from them (`roms/`, `sprites/`): the helper copies the ROM out of the emulator and
  builds the sprites from it on each player's own computer.

## More

`CLAUDE.md` is the detailed record: how the game's memory is laid out, the ROM formats, how each stat is worked out
and how it was checked.
