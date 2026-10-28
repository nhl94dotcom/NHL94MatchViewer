# NHL '94 league in a Google Sheet (Genesis)

A free league tracker: standings, every box score, season skater and goalie stats, a tab per team and a tab per
owner. After each game, one player uploads a RetroArch save state into the Sheet and it does the rest. Nothing to
install or host. Made for the original `nhl94.bin` on RetroArch's Genesis Plus GX core; league ROMs built on it
should work too (the rosters are read from whatever ROM you load).

## Setting it up (once, about 10 minutes, by one person)

1. **Make a new Google Sheet** (sheets.new) and name it.
2. **Add the script:** in the Sheet, **Extensions > Apps Script**.
   - Replace everything in `Code.gs` with the contents of this folder's `Code.gs`.
   - Click **+** next to Files, choose **HTML**, name it `Upload` (exactly), and replace its contents with this
     folder's `Upload.html`.
   - Click **Save** (the disk icon), then close the Apps Script tab.
3. **Reload the Sheet.** After a few seconds an **NHL '94** menu appears next to Help.
4. **Load the rosters:** **NHL '94 > Load rosters from ROM…**.
   - The first time, Google asks for permission. Choose your account. You'll see "Google hasn't verified this app":
     it's your own script, so click **Advanced**, then **Go to (your project) (unsafe)**, then **Allow**. Then
     choose the menu item again.
   - Pick `nhl94.bin` and press **Submit**. The Sheet reads the teams and players and opens the **Setup** tab.
5. **Fill in Setup:**
   - Columns A and B: each team in the league (its abbreviation from the dropdown, e.g. BOS) and its owner's name.
     Use the same spelling of each owner's name every time.
   - The settings: points for a win (2) and a tie (1), whether the league plays overtime (Yes / No), games per team
     (36).
6. **Share the Sheet** with the other players as **Editors**. Each of them approves the script the first time they
   use the menu (step 4's screens).

## After every game

1. **Stay on the final stats screen** (after the final horn, or after overtime) and **save a state** in RetroArch
   (F2 by default). Once you leave the game, its stats are gone.
2. In the Sheet: **NHL '94 > Upload save state…**, choose the state file and press **Submit**.
   - The files are in RetroArch's `states\Genesis Plus GX` folder, named like `nhl94.state3` (the newest one is the
     one you just saved).
   - The Sheet works out who played from the two teams, adds the game, and rebuilds the standings and every stats
     tab. It takes a few seconds.

Only one of the two players uploads each game (it refuses the same game twice). Uploading needs a computer (the
Sheets phone app doesn't show the menu); the stats can be read on any phone.

## What's in the Sheet

| Tab | What it shows |
| --- | --- |
| Setup | Teams, owners and the points rules (the only tab you edit) |
| Standings | Every team: GP, W, L, T, points, goals for and against, shots, power play, games left |
| Games | One row per game: score, result, shots, power plays, penalty minutes, faceoffs, checks, attack-zone time |
| Skaters / Goalies | Season stats for every player |
| One tab per team | Its record, its games, its skaters and goalies |
| One tab per owner | Their six teams together, their record against each other owner, their teams and top skaters |

The tabs are rebuilt from Games (and the hidden Player games) after every upload, so don't edit them by hand.

## If something goes wrong

- **"This save state is compressed"**: in RetroArch, **Settings > Saving > Save State Compression** off, then save
  the state again.
- **"The game in this save state isn't over"**: the state was saved before the final horn. Load it, let the game
  finish, and save again on the final stats screen.
- **"BOS isn't in the Setup tab"**: add the team and its owner to Setup, then upload again.
- **A game went in by mistake:** **NHL '94 > Delete a game…** and give its number (the first column of Games).
- **The Games tab's Check column** says "ok" when every number added up; anything else is worth a look.
- **The tabs look out of date:** **NHL '94 > Rebuild all tabs**.

## Updating the script

When a new version of `Code.gs` or `Upload.html` comes out, paste it over the old one in **Extensions > Apps
Script** and save. The games already uploaded stay; **Rebuild all tabs** redraws everything with the new version.

## How it reads a save state

A RetroArch save state of Genesis Plus GX holds the console's 64 KB of work RAM after a short header. The game keeps
a stat block for each team there ($364 bytes: Home at $C6CE, Away at $CA32; team ids at $C6F7 / $CA5B; period and
clock at $C466 / $C468): shots, goals, power plays, penalty minutes, faceoffs, checks and attack-zone time, and per
roster slot goals, assists, shots, penalty minutes, checks and ice time (a goalie's goals and shots are against).
The core stores the RAM in byte-swapped pairs. The rosters (names, numbers, which players are goalies) come from the
ROM's team table at $30E.
