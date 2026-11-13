NHL '94 Helper - streaming live stats with OBS
=============================================

This guide is for showing live stats from an NHL '94 game on a stream (Twitch or similar) with OBS. The helper
watches the game in your own RetroArch, works out the stats a few seconds behind play, and gives OBS two things to
show: a ready-made stats panel, and plain text files you can lay out yourself. It also records every game in full,
as it always does.

It works whether you play or watch: as a netplay spectator, your RetroArch runs the same game as the players', and
that is what the helper reads. Everything stays on your computer; nothing is uploaded.

Do part A once, well before the first game. Part B is what you do for every stream. Part C is after the series.


WHAT YOU NEED
- Windows 10 or 11 (64-bit).
- RetroArch 1.17 (64-bit) with the Genesis Plus GX core (Genesis) or the Snes9x core (SNES).
- OBS Studio (obsproject.com).
- The helper zip, which has four files: "NHL94 Helper.exe", "NHL94 Helper - Stream.bat", "Read me first.txt" and
  this guide.


PART A - SETTING UP (once)
--------------------------

A1. Unzip the helper zip into a folder of its own, for example "NHL94 Helper" on your Desktop.
    Keep "NHL94 Helper.exe" and "NHL94 Helper - Stream.bat" in the same folder.

A2. Double-click "NHL94 Helper - Stream.bat".
    - If Windows says "Windows protected your PC": click "More info", then "Run anyway". If it shows "Open File -
      Security Warning" instead: click "Run". (The program is new and not signed; this only happens the first time.)
    - If your antivirus objects: the helper reads RetroArch's memory to see the game. It only reads, never changes
      anything. Allow it, or tell whoever gave you the helper what the antivirus said.
    - A black window opens. Its first lines should include:
          Local live mode ON. In OBS add a Browser Source: http://localhost:9494/overlay.html
    - Your browser also opens the games page. You can close the browser; leave the black window open.

A3. Check the panel. In your web browser, open this address:
          http://localhost:9494/overlay.html?demo=1
    You should see a dark stats panel with two teams (PHI and CHI) and four event lines. That is a made-up game for
    setting up. (Without "?demo=1" it says "Waiting for a game..." until a game is being played.)

A4. Add the stats panel to OBS.
    1. In OBS, pick the scene that shows the game.
    2. Under "Sources", click "+" and choose "Browser".
    3. Choose "Create new", name it "NHL94 stats", click OK.
    4. In "URL", paste:
          http://localhost:9494/overlay.html?demo=1
    5. Set "Width" to 1920 and "Height" to 1080 (the same as your canvas, see Settings > Video > Base Resolution).
    6. Leave everything else as it is and click OK.
    7. The panel appears at the top right, over the game. It has no background of its own outside the dark box.
    You'll replace "?demo=1" with your own choices in step A5.

A5. Choose what the panel shows. Everything is set in its address. Open the source's Properties (double-click it
    in "Sources") and change the URL. The address has this shape:

          http://localhost:9494/overlay.html?layout=panel&stats=shots,xg,hits,faceoffs,power_play,save_pct&events=goal,big_save,big_miss,post,penalty&recent=4

    Parts you can change (separate them with "&"; no spaces anywhere):
    - layout=panel    numbers in a table with recent events under it (the default)
      layout=bar      the numbers in one row, no events
      layout=ticker   only the latest event line(s)
    - stats=...       the numbers, in your order, separated by commas. Choose from:
          shots          shots on goal
          attempts       all shot attempts (on goal, wide, blocked)
          xg             expected goals (how many goals the chances were worth)
          shooting_pct   goals per shot on goal
          save_pct       the goalie's save percentage
          hits           body checks
          knockdowns     checks that knocked a player down
          faceoffs       faceoffs won / taken
          faceoff_pct    faceoff percentage
          passes         passes completed / tried
          pass_pct       pass percentage
          power_play     power-play goals / chances
          penalties      penalties taken
          pim            penalty minutes
          attack_zone    time in the attacking zone
          one_timers     one-timer goals / tries
          breakaways     breakaway goals / tries
          posts          shots off the post
          takeaways      pucks taken from the other team
          giveaways      pucks given away
          goals          goals
    - events=...      which events appear, separated by commas. Without it, all of these but big_hit and hit
                      appear. Choose from:
          goal       goals, with scorer, assists, type (one-timer, power play ...) and "tying goal" / "go-ahead goal"
          big_save   a save on a chance worth 0.30 expected goals or more
          big_miss   a chance worth 0.30 expected goals or more that missed the net untouched (about 1-2 a game)
          big_hit    a player upended, or sent into the boards or the bench (about 7 a game)
          hit        every knockdown (there are about 40 a game: a lot for a stream)
          post       a shot off the post
          injury     an injured player, out for the period or the game
          penalty    a penalty, with the player and its length
          giveaway   a giveaway that led straight to a goal
          streak     a team's third (fourth ...) goal in a row
          fight      a fight (only on ROMs with fighting)
    - recent=4        how many event lines to show (newest at the top)
    - scale=1.2       bigger (or smaller, e.g. 0.8)
    - side=left       the panel at the top left instead of the top right
    - score=0         hide the score (shown by default: at the top of the panel, at the start of the bar)
    New events are highlighted for 8 seconds. To move the panel anywhere else, drag the source in OBS.

    You can add the panel more than once with different addresses, for example a "bar" along the top and a
    "ticker" at the bottom.

A6. (Optional) Build your own layout from text files instead. While a game is on, the helper keeps a folder of small
    text files, one number in each:
          Documents\NHL94 Viewer\live\obs
    For example score.txt (like "PHI 3 - 2 CHI"), home_shots.txt, away_shots.txt, home_xg.txt, away_xg.txt,
    home_abbr.txt (the team's short name),
    last_goal.txt, last_big_save.txt, last_big_miss.txt, last_big_hit.txt, last_penalty.txt, event_last.txt (the latest event of any
    kind but hits) and events_recent.txt (the last five events, hits left out). The numbers are the ones listed in A5, with "home_" or
    "away_" in front.
    To show one:
    1. Under "Sources", click "+" and choose "Text (GDI+)".
    2. Name it (for example "home shots") and click OK.
    3. Tick "Read from file", click "Browse" and pick the file in the folder above.
    4. Choose the font, size and colour, click OK, and drag it where you want it.
    The files appear once the first game starts (do the test game in A7 first, then set these up).

A7. A test game, before the series. This checks that recording works where you sit.
    1. Start the helper with "NHL94 Helper - Stream.bat" (if it isn't already open).
    2. Start RetroArch and join a netplay game as you will for the series (as a spectator if that's how you'll watch).
       Or just play a game against the computer.
    3. Watch the black window: at the opening faceoff it shows a line like "Recording PHI vs CHI" (with your game's
       teams; "joined during the game" is added if you joined late). The OBS panel switches from
       "Waiting for a game..." to the stats within a few seconds.
    4. At the end of the game, open http://localhost:9494/helper.html in your browser. The game should be in the
       list. Click "Watch": the score and the shots should match the game's own end-of-game stats.
    5. If anything looked wrong, send Documents\NHL94 Viewer\helper_log.txt to whoever gave you the helper.


PART B - EACH STREAM
--------------------

B1. Double-click "NHL94 Helper - Stream.bat". Leave the black window open the whole time.
B2. Start OBS. The panel shows "Waiting for a game..." (you can hide it until the game starts if you like).
B3. Start RetroArch and join the game.
B4. Nothing else to do. The panel fills in at the opening faceoff and updates every few seconds. Between games it
    keeps the last game's final numbers until the next game starts.
B5. When you're done, close the black window.

How far behind play the panel is (measured on a recorded game played back at real speed): the numbers are about 1 to
3 seconds behind play. Events take a little longer: a goal shows about 3 seconds after it goes in (6 at most), a big
hit about 2, a big save about 4 (once the shot is over), and a penalty about 8 (it waits for the whistle).

If something isn't right:
- The panel says "Waiting for a game..." during play: check that the black window is open and says "Local live mode
  ON" near the top (if it doesn't, it was started with the plain "NHL94 Helper.exe": close it and use the .bat).
- The panel doesn't change at all: in OBS, select the source and click "Refresh" under the preview (or open its
  Properties and click "Refresh cache of current page").
- Only one program can use the helper's address at a time: if the black window says "The helper is already
  running", close the other copy first.


PART C - AFTER THE SERIES
-------------------------

Every game was recorded in full. To send them for analysis:
C1. Open your Documents folder, then "NHL94 Viewer", then "captures".
C2. Each game is a folder named by date, time and teams, for example 2026-11-20_2015_PHI-CHI. Select the folders
    of the series' games (or the whole "captures" folder).
C3. Right-click the selection and choose "Compress to ZIP file" (Windows 11), or "Send to" > "Compressed (zipped)
    folder" (Windows 10, or under "Show more options" on Windows 11). A game is about 15 MB, so a seven-game series is
    about 100 MB.
C4. Send the zip with Google Drive, Dropbox, WeTransfer or similar, and say which ROM the series used.
    Please don't send the "roms" folder: it holds copies of the game ROM, which can't be shared.


OTHER ROMS AND THE SNES
-----------------------
The same steps work for any NHL '94 ROM on either system, league ROMs included. On ROMs with fighting, the "fight"
event appears too. A number the helper can't work out for a game shows as "-".
