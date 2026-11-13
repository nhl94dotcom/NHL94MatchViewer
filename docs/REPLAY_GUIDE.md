NHL '94 replay overlay - live stats over a video of games already played
========================================================================

This pack shows the NHL '94 Helper's stats panel over a video of games that were played and recorded earlier, in step
with the video: the score, the numbers and the events (goals, big saves ...) appear at the moment they happen in the
video. It is made for one video file: "About this pack.txt" names it and lists where each game starts. The video must
be that file, uncut (pausing and skipping while you stream are fine with the WebSocket set-up below).

You need OBS Studio 28 or later (obsproject.com). Nothing else: no helper, no RetroArch, no internet.

The pack has: replay.html (the panel), replay_data.js (the games' numbers), replay_settings.js (your choices), this
guide and "About this pack.txt".


PART A - SETTING UP (once)
--------------------------

A1. Unzip the pack into a folder of its own, for example "NHL94 Replay" on your Desktop. Keep the files together.
    You can put the video in the same folder (or anywhere).

A2. Add the video to OBS.
    1. In OBS, make a scene for the replay (Scenes "+", name it "Replay").
    2. Under "Sources", click "+" and choose "Media Source".
    3. Name it exactly:   NHL94 video   (the panel finds the video by this name) and click OK.
    4. Tick "Local File", click "Browse" and pick the video.
    5. Untick "Loop". Untick "Restart playback when source becomes active". Click OK.
    6. The video is small (the game's own size: 320 x 224 on the Genesis, 256 x 224 on the SNES). Make it fill the
       screen: right-click the source >
       Transform > Fit to screen. For sharp pixels: right-click the source > Scale Filtering > Point.

A3. Turn on OBS's WebSocket (this lets the panel follow the video, even when you pause or skip).
    1. OBS menu Tools > WebSocket Server Settings.
    2. Tick "Enable WebSocket server". Leave "Server Port" at 4455.
    3. Leave "Enable Authentication" ticked. Click "Show Connect Info" and copy the "Server Password".
    4. Click OK.
    5. Open replay_settings.js with Notepad (right-click it > Open with > Notepad). On the line
          obspw: "",
       paste the password between the quotes, for example   obspw: "aBcD1234efGH",
       Save (File > Save) and close Notepad.

A4. Add the panel to OBS.
    1. In the "Replay" scene, under "Sources", click "+" and choose "Browser".
    2. Name it "NHL94 stats" and click OK.
    3. Tick "Local file", click "Browse" and pick replay.html in the pack's folder.
    4. Set "Width" to 1920 and "Height" to 1080 (your canvas size: Settings > Video > Base Resolution).
    5. Click OK. Make sure "NHL94 stats" is above "NHL94 video" in the Sources list (drag it up if not), so the
       panel is drawn over the video.

A5. Check it.
    1. Play the video: hover over "NHL94 video" in the preview and use the play button that appears, or right-click
       the source and use the media controls (OBS also shows them below the preview when the source is selected).
    2. Until the first game's opening faceoff the panel says "Waiting for a game...". From the faceoff it shows
       the score and the numbers, and they change with the game.
    3. Pause the video: the panel stops too. Skip ahead: the panel jumps with it.
    If the panel says "OBS WebSocket not connected" or "no Media Source called ...", see "If something isn't right".

A6. Choose what the panel shows: in replay_settings.js (Notepad, as in A3). After saving, select "NHL94 stats" in
    OBS and click "Refresh" under the preview.
    - stats: the numbers, in your order, separated by commas, no spaces. Choose from:
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
          corsi_pct      share of all shot attempts in the game (Corsi %)
          fenwick_pct    the same without blocked attempts (Fenwick %)
          pdo            shooting % + save % (x 100): around 100 is normal, far above means luck running hot
          possession     time with the puck (game clock)
          possession_pct share of the game's time with the puck (the rest is loose-puck "transition")
          attack_zone_per_goal   attacking-zone time with the puck for each goal scored (lower = more dangerous)
          zone_entries   times the puck was taken over the attacking blue line
          zone_entries_kinds     those entries carried / passed / dumped
          bobbled        passes that bounced off a teammate who could have taken them
          checks_person  the person's check attempts (C bursts at a man), CB checks included
          checks_person_hfw      those as hit / failed / whiff
          checks_all     every check attempt, the computer's skaters' too
          checks_all_hfw         those as hit / failed / whiff
          cb_right       the person's checks where C or CB was the better choice for the two players' weights
                         (C into a man 2+ weight points heavier, CB otherwise), as right / judged
          cb_right_pct   the same as a percentage
    - events: which events appear, separated by commas:
          goal       goals, with scorer, assists, type (one-timer, power play ...) and "tying goal" / "go-ahead goal"
          big_save   a save on a chance worth 0.30 expected goals or more
          big_miss   a chance worth 0.30 expected goals or more that missed the net untouched
          post       a shot off the post
          injury     an injured player
          penalty    a penalty, with the player and its length
          giveaway   a giveaway that led straight to a goal
          streak     a team's third (fourth ...) goal in a row
          big_hit    a player upended, or sent into the boards or the bench (about 7 a game)
          hit        every knockdown (about 40 a game: a lot)
    - layout: "panel" (numbers and events), "bar" (numbers in one row) or "ticker" (events only).
    - recent: how many event lines. side: "right" or "left". scale: bigger or smaller (1.3, 0.8).
      score: "0" hides the score.
    - delay: "0" shows each goal, save or penalty the moment it happens in the video. "3" holds everything back 3
      seconds, which is how the live overlay feels during a real game (it needs a moment to work things out).
    You can add the panel more than once with different choices: copy the pack's folder, change that copy's
    replay_settings.js, and add its replay.html as another Browser Source.


PART B - THE STREAM
-------------------

B1. Switch to the "Replay" scene and start the video (as in A5). That's all: the panel follows the video to the end.
B2. Pausing, skipping back or ahead: fine, the panel follows.
B3. Between games the panel keeps the last game's final numbers until the next game's opening faceoff.


WITHOUT THE WEBSOCKET (if you'd rather not turn it on)
-------------------------------------------------------
In replay_settings.js set   obs: "",   (empty). The panel then counts from the moment it loads, so the video and the
panel have to start together and the video must not be paused:
1. "NHL94 video" Properties: tick "Restart playback when source becomes active".
2. "NHL94 stats" Properties: tick "Refresh browser when scene becomes active".
3. To start, switch to the "Replay" scene from another scene: both start at that moment.
If the panel then runs a little early or late, set offset (seconds; + if the panel is late, - if it is early) and
start again.


IF SOMETHING ISN'T RIGHT
------------------------
- "OBS WebSocket not connected": Tools > WebSocket Server Settings: "Enable WebSocket server" ticked, port 4455.
  "OBS refused the WebSocket password": the password in replay_settings.js must be exactly as "Show Connect Info"
  shows it. Then click "Refresh" on "NHL94 stats".
- "Waiting for the video to start...": connected to OBS; press play on the video.
- "OBS: no Media Source called ...": the video source's name in OBS must be exactly "NHL94 video" (or change obs: in
  replay_settings.js to your source's name).
- "replay_data.js not found": keep replay.html, replay_data.js and replay_settings.js in the same folder.
- The panel doesn't change after editing replay_settings.js: select "NHL94 stats" and click "Refresh".
- Nothing shows during the video's first minute: the panel waits for the first game's opening faceoff.
