# SNES Classic team guide

Every retail team in the SNES Classic leagues (names starting `Classic_Spring`, `Classic_Summer` or `Classic_Fall`): 15,017 games in 63 leagues, through 2026-11-03. No coach is named. The method is in [COACH_RATING.md](COACH_RATING.md).

**Jump to a team:** [New Jersey](#1-new-jersey-nj) · [Pittsburgh](#2-pittsburgh-pit) · [NY Rangers](#3-ny-rangers-nyr) · [Vancouver](#4-vancouver-van) · [Chicago](#5-chicago-chi) · [Los Angeles](#6-los-angeles-la) · [Calgary](#7-calgary-cgy) · [Washington](#8-washington-wsh) · [Montreal](#9-montreal-mtl) · [Toronto](#10-toronto-tor) · [Boston](#11-boston-bos) · [St. Louis](#12-st-louis-stl) · [Edmonton](#13-edmonton-edm) · [Winnipeg](#14-winnipeg-wpg) · [Detroit](#15-detroit-det) · [Philadelphia](#16-philadelphia-phi) · [Quebec](#17-quebec-que) · [Hartford](#18-hartford-hfd) · [Buffalo](#19-buffalo-buf) · [NY Islanders](#20-ny-islanders-nyi) · [San Jose](#21-san-jose-sj) · [Dallas](#22-dallas-dal)

## How to read this guide

**The basics**

- **Points:** strength values are points of win chance above or below 50, against the average team as used in these leagues, with even coaches and no home edge. +5 means about a 55% chance.

- **± (spread):** about how far a value could be off by chance, from resampling whole leagues or, in the Record table, from the number of games. A value within one spread of zero can't be told from zero.

- **Results show what happened, not why.** Players choose or are given teams, and rarely used teams rest on few coaches.

- **Most differences between levels don't repeat well** when half the leagues are compared with the other half, so treat them as ideas to test. On the SNES, the team order itself depends more on the method than on the Genesis, so read small gaps as ties.

**The "All teams" table**

- **#:** the team's rank by strength now.

- **Team:** the team and its abbreviation. Click a name to go to its entry.

- **Overall:** from strength now. Good is +1.5 or better, Poor is −1.5 or worse, and Average is in between.

- **Best for:** which level of player gets more from this team than from their other teams. High-level or Low-level means one does, Both alike means no gap of over 5 points, and Unclear means the measures disagree or there are too few games. A team can be Poor overall and still best for one level: that level just loses less with it.

- **Confidence:** how sure the Best for call is. Likely: all three measures of level agree on direction, and the gap is at least 1.5 spreads in two. Leaning: the same, at 1 spread. Weak: they agree on direction, the gap is at least 3 points each way, and the team is good for only that level. "Few games" means at least two values rest on under 150 appearances. A dash means no call to rate.

- **Strength now:** how much the team adds, in points, with recent games counting more. A game's weight halves every 3 years, so a game from 3 years ago counts half as much as one played today. It's the better guide to how a team has done lately.

- **Strength, all years:** the same, with every game counting equally. It rests on more games, so it's steadier.

- **Elo adjustment:** points to add to a coach's Elo for using this team, against the average team in use. It's fitted on the league Elo: every game in order, a 1500 start, K 20, +7 for home, and the winner's gain and loser's loss raised by the coasting bonus. A * marks under 300 games, so treat it as rough. Tested on later years, using these inside the running Elo predicts no better than leaving them out, and at full size slightly worse, so they describe past results more than they improve ratings.

- **Record:** all wins and losses with this team, plus ties when there are any.

- **Win %:** wins as a share of wins and losses, without ties or any adjustment for who was coaching.

- **Expected:** the win % that the team's coaches, home ice and the other team predict if this team were the average team in use. A record above expected is what the team itself added.

**The "By level of player" table** (all years; each value says how much better that level does with this team than with its other teams, after taking out who was using it)

- **High level** and **Low level:** the value for each level. A * marks under 150 appearances.

- **High minus low:** the gap between the two. Positive means the team does more for high-level players.

- **By coach (row):** level is each coach's career strength. High and low are the top and bottom groups, with about a third of the appearances each.

- **By league strength (row):** level is the strength of the league's coaches, cut the same way.

- **Top league against others (row):** high is each season's top league, the one with the most As, and low is the same season's other leagues.

**The "Record" table** (one row for each kind of game: all games, regular season, playoffs, home, away, three eras, each coach level, and top league or other leagues)

- **Record**, **Win %** and **Expected:** as in the "All teams" table.

- **Against expected:** win % minus expected, in points, with its spread. Positive means the team did better than its coaches and opponents predict.

**The "Per game" table** (averages over the team's games)

- **Stat** and **Value:** what's measured, explained below, and the team's figure. Percentages are over all its games, not an average of each game's.

- **Rank:** its place among the teams in this guide. 1st is best: the fewest for goals against, shots against and penalty minutes, and the most for checks.

- **Goals for** and **Goals against:** goals scored and allowed.

- **Shots for** and **Shots against:** shots on goal taken and allowed.

- **Shooting %:** goals for as a share of shots for.

- **Save %:** the share of shots against that didn't score.

- **Power play %:** power play goals as a share of power plays.

- **Penalty kill %:** the share of the other team's power plays that didn't score.

- **One-timer goals** and **Breakaway goals:** goals of each kind, as the game counts them.

- **Checks:** checks thrown, as the game counts them.

- **Penalty minutes:** the team's penalty minutes.

- **Faceoffs won %:** the team's share of faceoffs.

- **Attack zone time, seconds:** time spent in the attacking zone.

- **Pass completion %:** completed passes as a share of passes tried, as the game counts them. The game only credits a pass caught by the intended receiver.

**The "Ratings" table** (from the ROM; the number in parentheses is the rank among all 26 NHL teams, with 1st the highest, so the heaviest for Weight)

- **Overall**, **Weight**, **Speed**, **Agility**, **Shot Power**, **Shot Accuracy** and **Checking:** the mean roster rating of the team's top 12 skaters by overall. The SNES hot / cold bug maxes about 46% of ratings each game, but never Weight, so ratings other than Weight count for less than they look.

- **Goalie Agility:** the roster Agility of the team's higher-rated goalie. On the SNES every goalie covers the same net, so it matters less than on the Genesis.

- **Hidden bonus (line under the table):** what the ROM adds to some of the team's ratings at home and takes away on the road.

**The "Leading skaters" table** (the team's top 6 by points; all figures are per team game, whether or not the skater played in it)

- **Player** and **Pos:** the skater, as a forward (F) or defenceman (D).

- **Goals**, **Assists**, **Points** and **Checks:** the skater's figures per team game.

- **Overall**, **Weight**, **Speed**, **Shot Power** and **Shot Acc:** the skater's roster ratings from the ROM.

**The "Goalies" table** (the team's two goalies who faced the most shots)

- **Goalie:** the goalie.

- **Shots faced:** all shots the goalie faced in these games.

- **Save %:** the share of those shots the goalie stopped.

- **Agility** and **Puck Control:** the goalie's roster ratings from the ROM.


## All teams

| # | Team | Overall | Best for | Confidence | Strength now | Strength, all years | Elo adjustment | Record | Win % | Expected |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | [New Jersey (NJ)](#1-new-jersey-nj) | Good | Low-level | Weak | +5.9 | +4.5 | +46 | 444-287-3 | 60.7% | 56.1% |
| 2 | [Pittsburgh (PIT)](#2-pittsburgh-pit) | Good | Both alike | — | +4.0 | +4.3 | +57 | 1,310-1,195-17 | 52.3% | 46.7% |
| 3 | [NY Rangers (NYR)](#3-ny-rangers-nyr) | Good | Both alike | — | +2.7 | +2.5 | +10 | 1,347-1,171-15 | 53.5% | 50.3% |
| 4 | [Vancouver (VAN)](#4-vancouver-van) | Average | Both alike | — | +0.9 | +0.3 | −25 | 1,081-1,013-11 | 51.6% | 51.4% |
| 5 | [Chicago (CHI)](#5-chicago-chi) | Average | Both alike | — | +0.5 | +1.1 | +15 | 1,218-1,195-20 | 50.5% | 49.7% |
| 6 | [Los Angeles (LA)](#6-los-angeles-la) | Average | Both alike | — | +0.4 | +1.4 | −0 | 1,103-1,127-9 | 49.5% | 48.3% |
| 7 | [Calgary (CGY)](#7-calgary-cgy) | Average | Both alike | — | +0.4 | −0.2 | +7 | 967-992-17 | 49.4% | 50.0% |
| 8 | [Washington (WSH)](#8-washington-wsh) | Average | Low-level | Likely | +0.3 | +0.3 | −26 | 593-524-11 | 53.1% | 52.8% |
| 9 | [Montreal (MTL)](#9-montreal-mtl) | Average | Low-level | Leaning | −0.3 | +0.5 | +19 | 775-910-15 | 46.0% | 45.2% |
| 10 | [Toronto (TOR)](#10-toronto-tor) | Average | Unclear | — | −0.6 | −1.4 | −17 | 373-395-3 | 48.6% | 50.4% |
| 11 | [Boston (BOS)](#11-boston-bos) | Average | High-level | Likely | −0.8 | +1.5 | +11 | 1,142-1,348-23 | 45.9% | 43.7% |
| 12 | [St. Louis (STL)](#12-st-louis-stl) | Average | Unclear | — | −0.9 | +0.0 | −5 | 296-252-5 | 54.0% | 53.4% |
| 13 | [Edmonton (EDM)](#13-edmonton-edm) | Average | Low-level | Leaning, few games | −0.9 | −2.0 | −27 | 284-207-6 | 57.8% | 61.2% |
| 14 | [Winnipeg (WPG)](#14-winnipeg-wpg) | Average | Both alike | — | −1.3 | −3.6 | −29 | 624-647-8 | 49.1% | 54.1% |
| 15 | [Detroit (DET)](#15-detroit-det) | Average | Both alike | — | −1.5 | −1.5 | +9 | 972-1,340-15 | 42.0% | 42.3% |
| 16 | [Philadelphia (PHI)](#16-philadelphia-phi) | Poor | Low-level | Leaning | −2.5 | −1.1 | +3 | 309-332-2 | 48.2% | 50.8% |
| 17 | [Quebec (QUE)](#17-quebec-que) | Poor | High-level | Likely | −3.2 | −6.3 | −33 | 458-428-9 | 51.7% | 59.2% |
| 18 | [Hartford (HFD)](#18-hartford-hfd) | Poor | Both alike | Few games | −3.5 | −2.7 | −53* | 129-98-1 | 56.8% | 62.0% |
| 19 | [Buffalo (BUF)](#19-buffalo-buf) | Poor | Both alike | — | −3.6 | −4.1 | −25 | 1,034-1,059-10 | 49.4% | 53.9% |
| 20 | [NY Islanders (NYI)](#20-ny-islanders-nyi) | Poor | Unclear | Few games | −6.0 | −9.6 | −138* | 153-140-2 | 52.2% | 62.7% |
| 21 | [San Jose (SJ)](#21-san-jose-sj) | Poor | Unclear | Few games | −7.7 | −11.8 | −102* | 96-55-2 | 63.6% | 74.5% |
| 22 | [Dallas (DAL)](#22-dallas-dal) | Poor | Unclear | Few games | −9.3 | −5.5 | −116* | 87-94-1 | 48.1% | 54.9% |

Too few games for a full entry: Florida (FLA) 47-26-1; Tampa Bay (TB) 28-35-2; Anaheim (ANH) 24-22; Ottawa (OTW) 19-21.

## 1. New Jersey (NJ)

**Overall: Good. Best for: Low-level (weak).** Strength +5.9 ± 2.9 now (1st of 22), +4.5 ± 2.3 over all years (1st).

**Elo adjustment:** +46 ± 22 points (2nd of 22). Against an even coach on the average team, on neutral ice, that's a 57% win chance. With one fixed strength per coach instead of Elo, it's +47.

Used in 16 of 63 leagues (5 of them a season's top league), by 13 coaches, 734 games, most recently 2026-10-28.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +3.7 ± 3.1 | +9.4 ± 5.5 | −5.7 ± 6.1 |
| By league strength | +3.1 ± 3.7 | +8.8 ± 4.5 | −5.6 ± 5.7 |
| Top league against others | −0.5 ± 3.5 | +8.2 ± 4.3 | −8.7 ± 5.3 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 444-287-3 | 60.7% | 56.1% | +4.7 ± 1.8 |
| Regular season | 371-233-3 | 61.4% | 57.0% | +4.4 ± 2.0 |
| Playoffs | 73-54 | 57.5% | 51.6% | +5.9 ± 4.4 |
| Home | 248-120-1 | 67.4% | 59.1% | +8.3 ± 2.6 |
| Away | 196-167-2 | 54.0% | 53.0% | +1.0 ± 2.6 |
| 2013-2019 | 133-85 | 61.0% | 55.9% | +5.1 ± 3.4 |
| 2020-2022 | 108-74 | 59.3% | 60.3% | −1.0 ± 3.7 |
| 2023-2026 | 203-128-3 | 61.3% | 53.8% | +7.5 ± 2.7 |
| High coach | 172-102-1 | 62.8% | 60.1% | +2.7 ± 3.0 |
| Mid coach | 118-66 | 64.1% | 61.1% | +3.1 ± 3.7 |
| Low coach | 154-119-2 | 56.4% | 48.7% | +7.7 ± 3.0 |
| Top league | 139-98-1 | 58.6% | 58.6% | +0.1 ± 3.2 |
| Other leagues | 242-163-2 | 59.8% | 53.1% | +6.7 ± 2.5 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.55 | 5th | | One-timer goals | 1.36 | 6th |
| Goals against | 3.69 | 3rd | | Breakaway goals | 0.24 | 9th |
| Shots for | 11.7 | 11th | | Checks | 30.2 | 2nd |
| Shots against | 10.8 | 4th | | Penalty minutes | 2.6 | 13th |
| Shooting % | 38.8 | 6th | | Faceoffs won % | 50.6 | 7th |
| Save % | 65.7 | 2nd | | Attack zone time, seconds | 320 | 3rd |
| Power play % | 45.4 | 3rd | | Pass completion % | 54.2 | 20th |
| Penalty kill % | 63.6 | 2nd | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 66.2 (15th) | 8.6 (1st) | 3.3 (15th) | 3.6 (11th) | 3.4 (7th) | 2.6 (20th) | 2.8 (11th) | 4.0 (8th) |

Hidden bonus: +1 at home, −2 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Stephane Richer | F | 1.43 | 0.84 | 2.27 | 1.14 | 72 | 9 | 4 | 5 | 3 |
| Claude Lemieux | F | 0.83 | 0.70 | 1.54 | 0.91 | 68 | 11 | 4 | 4 | 2 |
| Scott Stevens | D | 0.51 | 0.75 | 1.27 | 1.28 | 76 | 11 | 4 | 4 | 2 |
| Vachslav Fetisov | D | 0.28 | 0.70 | 0.98 | 1.34 | 61 | 11 | 2 | 4 | 1 |
| Alexnder Semak | F | 0.47 | 0.49 | 0.95 | 0.52 | 73 | 6 | 3 | 3 | 4 |
| Valeri Zelepukin | F | 0.47 | 0.44 | 0.91 | 0.29 | 68 | 6 | 4 | 3 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Chris Terreri | 7,542 | 66.0 | 4 | 3 |
| Craig Billington | 351 | 63.0 | 3 | 1 |

## 2. Pittsburgh (PIT)

**Overall: Good. Best for: Both alike.** Strength +4.0 ± 1.5 now (2nd of 22), +4.3 ± 1.2 over all years (2nd).

**Elo adjustment:** +57 ± 14 points (1st of 22). Against an even coach on the average team, on neutral ice, that's a 58% win chance. With one fixed strength per coach instead of Elo, it's +41.

Used in 60 of 63 leagues (19 of them a season's top league), by 51 coaches, 2,522 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +4.3 ± 3.4 | +2.2 ± 2.2 | +2.1 ± 3.8 |
| By league strength | +6.3 ± 2.0 | +4.0 ± 2.0 | +2.3 ± 2.7 |
| Top league against others | +5.7 ± 2.1 | +3.1 ± 1.5 | +2.6 ± 2.6 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,310-1,195-17 | 52.3% | 46.7% | +5.6 ± 1.0 |
| Regular season | 1,169-1,021-17 | 53.4% | 47.2% | +6.2 ± 1.1 |
| Playoffs | 141-174 | 44.8% | 43.3% | +1.4 ± 2.8 |
| Home | 691-562-9 | 55.1% | 49.7% | +5.5 ± 1.4 |
| Away | 619-633-8 | 49.4% | 43.8% | +5.7 ± 1.4 |
| 2013-2019 | 326-271-4 | 54.6% | 47.3% | +7.3 ± 2.0 |
| 2020-2022 | 532-480-7 | 52.6% | 47.6% | +4.9 ± 1.6 |
| 2023-2026 | 452-444-6 | 50.4% | 45.3% | +5.2 ± 1.7 |
| High coach | 213-188-5 | 53.1% | 47.9% | +5.2 ± 2.5 |
| Mid coach | 725-574-6 | 55.8% | 48.7% | +7.1 ± 1.4 |
| Low coach | 372-433-6 | 46.2% | 43.0% | +3.2 ± 1.8 |
| Top league | 408-417-6 | 49.5% | 42.2% | +7.2 ± 1.7 |
| Other leagues | 782-684-9 | 53.3% | 49.0% | +4.3 ± 1.3 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.44 | 11th | | One-timer goals | 1.28 | 10th |
| Goals against | 4.25 | 9th | | Breakaway goals | 0.22 | 15th |
| Shots for | 12.5 | 2nd | | Checks | 30.7 | 1st |
| Shots against | 11.2 | 7th | | Penalty minutes | 2.7 | 18th |
| Shooting % | 35.4 | 20th | | Faceoffs won % | 49.7 | 16th |
| Save % | 62.2 | 16th | | Attack zone time, seconds | 321 | 2nd |
| Power play % | 42.2 | 12th | | Pass completion % | 55.7 | 15th |
| Penalty kill % | 58.4 | 12th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 68.8 (7th) | 8.5 (2nd) | 3.2 (19th) | 3.5 (14th) | 3.3 (10th) | 2.8 (14th) | 3.2 (4th) | 4.0 (10th) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mario Lemieux | F | 2.03 | 0.78 | 2.82 | 1.42 | 100 | 10 | 4 | 4 | 6 |
| Jaromir Jagr | F | 0.87 | 0.84 | 1.71 | 0.96 | 80 | 10 | 4 | 3 | 3 |
| Kevin Stevens | F | 0.77 | 0.84 | 1.61 | 0.87 | 77 | 11 | 4 | 3 | 4 |
| Larry Murphy | D | 0.24 | 0.73 | 0.97 | 1.07 | 74 | 10 | 3 | 4 | 2 |
| Ulf Samuelsson | D | 0.22 | 0.69 | 0.92 | 1.22 | 68 | 8 | 4 | 3 | 0 |
| Ron Francis | F | 0.15 | 0.13 | 0.28 | 0.19 | 75 | 9 | 3 | 4 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Tom Barrasso | 27,198 | 62.0 | 4 | 4 |
| Ken Wregget | 957 | 71.8 | 2 | 2 |

## 3. NY Rangers (NYR)

**Overall: Good. Best for: Both alike.** Strength +2.7 ± 1.3 now (3rd of 22), +2.5 ± 1.3 over all years (3rd).

**Elo adjustment:** +10 ± 16 points (6th of 22). Against an even coach on the average team, on neutral ice, that's a 51% win chance. With one fixed strength per coach instead of Elo, it's +27.

Used in 56 of 63 leagues (18 of them a season's top league), by 37 coaches, 2,533 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +1.8 ± 2.1 | +1.2 ± 2.2 | +0.6 ± 3.1 |
| By league strength | +2.7 ± 2.0 | +0.6 ± 2.6 | +2.1 ± 3.3 |
| Top league against others | +2.5 ± 1.9 | +2.4 ± 2.0 | +0.2 ± 2.8 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,347-1,171-15 | 53.5% | 50.3% | +3.2 ± 1.0 |
| Regular season | 1,134-985-15 | 53.5% | 50.5% | +3.0 ± 1.1 |
| Playoffs | 213-186 | 53.4% | 49.1% | +4.3 ± 2.5 |
| Home | 704-558-5 | 55.8% | 53.1% | +2.7 ± 1.4 |
| Away | 643-613-10 | 51.2% | 47.4% | +3.8 ± 1.4 |
| 2013-2019 | 302-271-3 | 52.7% | 52.0% | +0.7 ± 2.1 |
| 2020-2022 | 656-471-7 | 58.2% | 52.4% | +5.8 ± 1.5 |
| 2023-2026 | 389-429-5 | 47.6% | 46.1% | +1.4 ± 1.7 |
| High coach | 543-340-4 | 61.5% | 60.4% | +1.1 ± 1.7 |
| Mid coach | 392-286-4 | 57.8% | 52.4% | +5.4 ± 1.9 |
| Low coach | 412-545-7 | 43.1% | 39.4% | +3.6 ± 1.6 |
| Top league | 448-384-3 | 53.8% | 51.0% | +2.8 ± 1.7 |
| Other leagues | 744-671-10 | 52.6% | 49.1% | +3.5 ± 1.3 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.41 | 13th | | One-timer goals | 1.25 | 12th |
| Goals against | 4.19 | 7th | | Breakaway goals | 0.26 | 4th |
| Shots for | 12.3 | 4th | | Checks | 29.3 | 3rd |
| Shots against | 11.1 | 6th | | Penalty minutes | 2.8 | 21st |
| Shooting % | 35.9 | 19th | | Faceoffs won % | 49.5 | 20th |
| Save % | 62.2 | 14th | | Attack zone time, seconds | 323 | 1st |
| Power play % | 43.1 | 9th | | Pass completion % | 57.7 | 4th |
| Penalty kill % | 58.3 | 13th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 71.6 (2nd) | 7.4 (13th) | 3.8 (7th) | 4.4 (1st) | 3.4 (8th) | 2.6 (21st) | 2.9 (8th) | 3.0 (20th) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mark Messier | F | 1.32 | 0.98 | 2.31 | 1.37 | 85 | 10 | 4 | 3 | 3 |
| Mike Gartner | F | 1.26 | 0.88 | 2.14 | 0.90 | 85 | 7 | 5 | 5 | 3 |
| Esa Tikkanen | F | 1.19 | 0.89 | 2.08 | 1.19 | 80 | 9 | 5 | 4 | 2 |
| James Patrick | D | 0.27 | 0.77 | 1.04 | 1.22 | 71 | 9 | 4 | 4 | 1 |
| Brian Leetch | D | 0.13 | 0.43 | 0.56 | 0.58 | 76 | 6 | 3 | 4 | 1 |
| Kevin Lowe | D | 0.07 | 0.32 | 0.39 | 0.39 | 62 | 8 | 3 | 3 | 1 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Mike Richter | 28,086 | 62.4 | 3 | 3 |

## 4. Vancouver (VAN)

**Overall: Average. Best for: Both alike.** Strength +0.9 ± 1.4 now (4th of 22), +0.3 ± 1.3 over all years (8th).

**Elo adjustment:** −25 ± 19 points (14th of 22). Against an even coach on the average team, on neutral ice, that's a 46% win chance. With one fixed strength per coach instead of Elo, it's −0.

Used in 47 of 63 leagues (16 of them a season's top league), by 29 coaches, 2,105 games, most recently 2026-11-01.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +2.2 ± 2.5 | −0.6 ± 2.4 | +2.8 ± 3.5 |
| By league strength | +1.3 ± 2.6 | +0.3 ± 2.6 | +1.0 ± 3.8 |
| Top league against others | +0.5 ± 2.2 | +0.3 ± 1.6 | +0.2 ± 2.8 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,081-1,013-11 | 51.6% | 51.4% | +0.3 ± 1.1 |
| Regular season | 904-848-11 | 51.6% | 51.7% | −0.1 ± 1.2 |
| Playoffs | 177-165 | 51.8% | 49.4% | +2.4 ± 2.7 |
| Home | 579-473-3 | 55.0% | 54.3% | +0.7 ± 1.5 |
| Away | 502-540-8 | 48.2% | 48.3% | −0.2 ± 1.5 |
| 2013-2019 | 219-229-3 | 48.9% | 51.3% | −2.4 ± 2.4 |
| 2020-2022 | 429-400-4 | 51.7% | 49.8% | +1.9 ± 1.7 |
| 2023-2026 | 433-384-4 | 53.0% | 52.9% | +0.1 ± 1.7 |
| High coach | 454-291-3 | 60.9% | 60.3% | +0.6 ± 1.8 |
| Mid coach | 298-266-4 | 52.8% | 52.6% | +0.3 ± 2.1 |
| Low coach | 329-456-4 | 41.9% | 42.0% | −0.0 ± 1.8 |
| Top league | 380-333-6 | 53.3% | 52.9% | +0.4 ± 1.9 |
| Other leagues | 589-574-4 | 50.6% | 50.3% | +0.3 ± 1.5 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.61 | 3rd | | One-timer goals | 1.31 | 7th |
| Goals against | 4.45 | 16th | | Breakaway goals | 0.27 | 2nd |
| Shots for | 11.9 | 9th | | Checks | 26.6 | 12th |
| Shots against | 11.7 | 12th | | Penalty minutes | 2.7 | 20th |
| Shooting % | 38.7 | 7th | | Faceoffs won % | 50.2 | 10th |
| Save % | 62.0 | 18th | | Attack zone time, seconds | 310 | 15th |
| Power play % | 43.8 | 7th | | Pass completion % | 56.2 | 11th |
| Penalty kill % | 59.1 | 9th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 67.4 (13th) | 7.5 (11th) | 3.6 (10th) | 3.6 (12th) | 3.0 (18th) | 3.3 (2nd) | 2.7 (18th) | 4.0 (14th) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pavel Bure | F | 1.62 | 0.86 | 2.48 | 0.89 | 90 | 5 | 6 | 4 | 4 |
| Trevor Linden | F | 1.28 | 0.83 | 2.11 | 1.12 | 78 | 9 | 4 | 4 | 4 |
| Geoff Courtnall | F | 0.63 | 0.60 | 1.24 | 0.50 | 73 | 7 | 5 | 3 | 3 |
| Cliff Ronning | F | 0.46 | 0.39 | 0.85 | 0.38 | 76 | 5 | 5 | 2 | 3 |
| Jyrki Lumme | D | 0.15 | 0.63 | 0.78 | 1.02 | 64 | 7 | 3 | 2 | 1 |
| Doug Lidster | D | 0.16 | 0.59 | 0.75 | 1.13 | 60 | 9 | 3 | 3 | 1 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Kirk McLean | 24,510 | 62.2 | 4 | 4 |
| Kay Whitmore | 125 | 59.2 | 2 | 2 |

## 5. Chicago (CHI)

**Overall: Average. Best for: Both alike.** Strength +0.5 ± 1.4 now (5th of 22), +1.1 ± 1.2 over all years (6th).

**Elo adjustment:** +15 ± 15 points (4th of 22). Against an even coach on the average team, on neutral ice, that's a 52% win chance. With one fixed strength per coach instead of Elo, it's +4.

Used in 58 of 63 leagues (18 of them a season's top league), by 52 coaches, 2,433 games, most recently 2026-10-28.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +1.6 ± 2.2 | −0.1 ± 3.0 | +1.7 ± 3.8 |
| By league strength | +1.6 ± 2.1 | +0.6 ± 3.2 | +1.1 ± 3.9 |
| Top league against others | +2.0 ± 1.7 | −0.4 ± 1.9 | +2.4 ± 2.7 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,218-1,195-20 | 50.5% | 49.7% | +0.8 ± 1.0 |
| Regular season | 1,056-1,034-20 | 50.5% | 49.7% | +0.8 ± 1.1 |
| Playoffs | 162-161 | 50.2% | 49.4% | +0.7 ± 2.8 |
| Home | 646-563-8 | 53.4% | 52.7% | +0.7 ± 1.4 |
| Away | 572-632-12 | 47.5% | 46.6% | +0.9 ± 1.4 |
| 2013-2019 | 294-294-5 | 50.0% | 48.5% | +1.5 ± 2.1 |
| 2020-2022 | 513-470-6 | 52.2% | 51.2% | +1.0 ± 1.6 |
| 2023-2026 | 411-431-9 | 48.8% | 48.7% | +0.1 ± 1.7 |
| High coach | 423-288-8 | 59.5% | 59.3% | +0.2 ± 1.9 |
| Mid coach | 462-436-8 | 51.4% | 50.6% | +0.9 ± 1.7 |
| Low coach | 333-471-4 | 41.4% | 40.1% | +1.3 ± 1.8 |
| Top league | 365-388-11 | 48.5% | 47.2% | +1.2 ± 1.8 |
| Other leagues | 734-692-7 | 51.5% | 51.5% | −0.1 ± 1.3 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.33 | 15th | | One-timer goals | 1.22 | 14th |
| Goals against | 4.32 | 11th | | Breakaway goals | 0.25 | 8th |
| Shots for | 11.6 | 13th | | Checks | 26.7 | 11th |
| Shots against | 12.0 | 17th | | Penalty minutes | 2.7 | 19th |
| Shooting % | 37.2 | 14th | | Faceoffs won % | 49.9 | 13th |
| Save % | 64.1 | 8th | | Attack zone time, seconds | 312 | 12th |
| Power play % | 40.9 | 16th | | Pass completion % | 55.7 | 16th |
| Penalty kill % | 59.2 | 7th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 70.8 (6th) | 7.3 (15th) | 3.4 (12th) | 3.8 (8th) | 3.4 (6th) | 2.8 (15th) | 3.5 (1st) | 6.0 (1st) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Jeremy Roenick | F | 1.68 | 0.79 | 2.46 | 1.02 | 89 | 4 | 5 | 5 | 5 |
| Steve Larmer | F | 1.04 | 0.84 | 1.87 | 1.03 | 86 | 7 | 4 | 4 | 4 |
| Christan Ruuttu | F | 0.74 | 0.77 | 1.51 | 0.76 | 72 | 8 | 4 | 3 | 2 |
| Steve Smith | D | 0.29 | 0.78 | 1.07 | 1.38 | 72 | 11 | 4 | 4 | 1 |
| Chris Chelios | D | 0.31 | 0.69 | 1.00 | 1.18 | 84 | 7 | 4 | 5 | 1 |
| Joe Murphy | F | 0.11 | 0.09 | 0.19 | 0.11 | 71 | 7 | 4 | 4 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Ed Belfour | 29,034 | 64.2 | 6 | 5 |
| Jim Waite | 200 | 64.5 | 3 | 2 |

## 6. Los Angeles (LA)

**Overall: Average. Best for: Both alike.** Strength +0.4 ± 1.2 now (6th of 22), +1.4 ± 1.2 over all years (5th).

**Elo adjustment:** −0 ± 15 points (10th of 22). Against an even coach on the average team, on neutral ice, that's a 50% win chance. With one fixed strength per coach instead of Elo, it's +8.

Used in 54 of 63 leagues (19 of them a season's top league), by 36 coaches, 2,239 games, most recently 2026-11-01.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +1.8 ± 1.8 | +1.7 ± 2.6 | +0.1 ± 2.8 |
| By league strength | +0.4 ± 1.9 | +1.3 ± 2.3 | −0.9 ± 3.1 |
| Top league against others | +1.4 ± 1.9 | +1.9 ± 1.6 | −0.5 ± 2.4 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,103-1,127-9 | 49.5% | 48.3% | +1.2 ± 1.1 |
| Regular season | 966-977-9 | 49.7% | 48.5% | +1.3 ± 1.1 |
| Playoffs | 137-150 | 47.7% | 47.1% | +0.6 ± 3.0 |
| Home | 568-546-3 | 51.0% | 51.1% | −0.2 ± 1.5 |
| Away | 535-581-6 | 47.9% | 45.4% | +2.5 ± 1.5 |
| 2013-2019 | 197-264-1 | 42.7% | 40.6% | +2.2 ± 2.3 |
| 2020-2022 | 554-429-4 | 56.4% | 51.5% | +4.8 ± 1.6 |
| 2023-2026 | 352-434-4 | 44.8% | 48.7% | −4.0 ± 1.8 |
| High coach | 348-260-3 | 57.2% | 57.2% | +0.0 ± 2.0 |
| Mid coach | 512-463-5 | 52.5% | 51.1% | +1.4 ± 1.6 |
| Low coach | 243-404-1 | 37.6% | 35.7% | +1.9 ± 2.0 |
| Top league | 389-428-3 | 47.6% | 46.5% | +1.1 ± 1.7 |
| Other leagues | 644-605-5 | 51.6% | 50.2% | +1.3 ± 1.4 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.45 | 10th | | One-timer goals | 1.39 | 2nd |
| Goals against | 4.48 | 18th | | Breakaway goals | 0.23 | 12th |
| Shots for | 12.2 | 6th | | Checks | 29.3 | 5th |
| Shots against | 11.7 | 11th | | Penalty minutes | 2.6 | 16th |
| Shooting % | 36.6 | 17th | | Faceoffs won % | 49.6 | 18th |
| Save % | 61.6 | 20th | | Attack zone time, seconds | 315 | 8th |
| Power play % | 43.7 | 8th | | Pass completion % | 55.7 | 14th |
| Penalty kill % | 55.4 | 22nd | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 71.1 (5th) | 7.5 (9th) | 3.8 (2nd) | 3.9 (5th) | 3.2 (12th) | 3.2 (3rd) | 2.5 (20th) | 3.0 (19th) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tomas Sandstrom | F | 1.41 | 0.90 | 2.31 | 1.36 | 80 | 9 | 4 | 5 | 5 |
| Jimmy Carson | F | 1.10 | 0.80 | 1.91 | 0.86 | 76 | 9 | 4 | 4 | 5 |
| Luc Robitaille | F | 0.91 | 0.78 | 1.69 | 0.78 | 85 | 7 | 4 | 4 | 6 |
| Rob Blake | D | 0.30 | 0.81 | 1.11 | 1.41 | 72 | 11 | 4 | 4 | 1 |
| Marty McSorley | D | 0.16 | 0.58 | 0.74 | 1.11 | 61 | 12 | 3 | 3 | 2 |
| Wayne Gretzky | F | 0.36 | 0.31 | 0.67 | 0.24 | 87 | 4 | 4 | 2 | 2 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Kelly Hrudey | 25,228 | 61.8 | 3 | 4 |
| Robb Stauber | 452 | 60.8 | 2 | 3 |

## 7. Calgary (CGY)

**Overall: Average. Best for: Both alike.** Strength +0.4 ± 1.9 now (7th of 22), −0.2 ± 1.5 over all years (11th).

**Elo adjustment:** +7 ± 15 points (8th of 22). Against an even coach on the average team, on neutral ice, that's a 51% win chance. With one fixed strength per coach instead of Elo, it's −8.

Used in 46 of 63 leagues (12 of them a season's top league), by 36 coaches, 1,976 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +0.7 ± 2.4 | +1.7 ± 3.3 | −1.0 ± 4.1 |
| By league strength | −2.6 ± 2.3 | −4.0 ± 2.9 | +1.4 ± 3.6 |
| Top league against others | −1.7 ± 2.5 | −0.7 ± 2.3 | −1.0 ± 3.6 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 967-992-17 | 49.4% | 50.0% | −0.6 ± 1.1 |
| Regular season | 841-832-17 | 50.3% | 50.3% | −0.0 ± 1.2 |
| Playoffs | 126-160 | 44.1% | 48.1% | −4.0 ± 3.0 |
| Home | 505-471-9 | 51.7% | 53.3% | −1.5 ± 1.6 |
| Away | 462-521-8 | 47.0% | 46.7% | +0.3 ± 1.6 |
| 2013-2019 | 204-293-2 | 41.0% | 40.6% | +0.4 ± 2.2 |
| 2020-2022 | 382-377-8 | 50.3% | 52.9% | −2.6 ± 1.8 |
| 2023-2026 | 381-322-7 | 54.2% | 53.4% | +0.8 ± 1.9 |
| High coach | 247-154-2 | 61.6% | 63.9% | −2.3 ± 2.5 |
| Mid coach | 391-442-8 | 46.9% | 48.5% | −1.6 ± 1.7 |
| Low coach | 329-396-7 | 45.4% | 43.9% | +1.5 ± 1.9 |
| Top league | 228-291-2 | 43.9% | 44.1% | −0.2 ± 2.2 |
| Other leagues | 648-583-15 | 52.6% | 53.7% | −1.1 ± 1.4 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.48 | 9th | | One-timer goals | 1.26 | 11th |
| Goals against | 4.42 | 14th | | Breakaway goals | 0.25 | 5th |
| Shots for | 11.6 | 14th | | Checks | 25.8 | 16th |
| Shots against | 11.9 | 15th | | Penalty minutes | 2.7 | 17th |
| Shooting % | 38.6 | 8th | | Faceoffs won % | 50.8 | 6th |
| Save % | 62.9 | 10th | | Attack zone time, seconds | 315 | 9th |
| Power play % | 41.5 | 15th | | Pass completion % | 55.4 | 17th |
| Penalty kill % | 58.6 | 11th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 71.4 (3rd) | 7.5 (8th) | 3.8 (1st) | 4.0 (4th) | 3.5 (4th) | 3.0 (7th) | 3.0 (5th) | 3.0 (17th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gary Roberts | F | 1.29 | 0.86 | 2.15 | 1.42 | 85 | 7 | 4 | 4 | 5 |
| Joe Nieuwendyk | F | 1.02 | 0.70 | 1.72 | 0.92 | 74 | 8 | 4 | 4 | 4 |
| Theoren Fleury | F | 0.95 | 0.73 | 1.68 | 0.80 | 86 | 3 | 5 | 4 | 3 |
| Gary Suter | D | 0.34 | 0.72 | 1.06 | 1.43 | 81 | 7 | 4 | 4 | 2 |
| Al MacInnis | D | 0.34 | 0.70 | 1.04 | 1.41 | 73 | 8 | 4 | 6 | 1 |
| Joel Otto | F | 0.22 | 0.18 | 0.40 | 0.36 | 71 | 11 | 3 | 2 | 4 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Mike Vernon | 22,488 | 63.2 | 3 | 4 |
| Jeff Reese | 857 | 61.4 | 2 | 2 |

## 8. Washington (WSH)

**Overall: Average. Best for: Low-level (likely).** Strength +0.3 ± 1.7 now (8th of 22), +0.3 ± 1.5 over all years (9th).

**Elo adjustment:** −26 ± 19 points (15th of 22). Against an even coach on the average team, on neutral ice, that's a 46% win chance. With one fixed strength per coach instead of Elo, it's +6.

Used in 26 of 63 leagues (12 of them a season's top league), by 22 coaches, 1,128 games, most recently 2026-10-15.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −0.1 ± 1.5 | +2.5 ± 3.6 | −2.6 ± 3.8 |
| By league strength | −2.6 ± 1.2 | +5.6 ± 3.8 | −8.2 ± 4.0 |
| Top league against others | −2.5 ± 1.3 | +5.2 ± 3.8 | −7.8 ± 4.2 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 593-524-11 | 53.1% | 52.8% | +0.2 ± 1.5 |
| Regular season | 490-431-11 | 53.2% | 52.8% | +0.4 ± 1.6 |
| Playoffs | 103-93 | 52.6% | 53.1% | −0.6 ± 3.6 |
| Home | 310-249-8 | 55.5% | 55.9% | −0.4 ± 2.1 |
| Away | 283-275-3 | 50.7% | 49.8% | +0.9 ± 2.1 |
| 2013-2019 | 199-156-4 | 56.1% | 53.2% | +2.9 ± 2.7 |
| 2020-2022 | 223-260-2 | 46.2% | 48.5% | −2.4 ± 2.3 |
| 2023-2026 | 171-108-5 | 61.3% | 59.9% | +1.4 ± 3.0 |
| High coach | 399-266-5 | 60.0% | 60.9% | −0.9 ± 1.9 |
| Mid coach | 66-79-3 | 45.5% | 42.1% | +3.4 ± 4.2 |
| Low coach | 128-179-3 | 41.7% | 40.4% | +1.3 ± 2.9 |
| Top league | 279-271-4 | 50.7% | 53.5% | −2.7 ± 2.1 |
| Other leagues | 170-161-4 | 51.4% | 47.3% | +4.0 ± 2.7 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.60 | 4th | | One-timer goals | 1.19 | 16th |
| Goals against | 4.20 | 8th | | Breakaway goals | 0.22 | 14th |
| Shots for | 12.0 | 7th | | Checks | 29.3 | 4th |
| Shots against | 11.0 | 5th | | Penalty minutes | 2.5 | 3rd |
| Shooting % | 38.3 | 11th | | Faceoffs won % | 50.1 | 11th |
| Save % | 61.7 | 19th | | Attack zone time, seconds | 319 | 4th |
| Power play % | 40.8 | 17th | | Pass completion % | 57.6 | 5th |
| Penalty kill % | 62.7 | 3rd | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 68.7 (8th) | 8.1 (4th) | 3.5 (11th) | 3.4 (20th) | 3.6 (3rd) | 3.2 (4th) | 2.8 (12th) | 3.0 (23rd) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mike Ridley | F | 1.19 | 1.01 | 2.19 | 1.16 | 73 | 9 | 4 | 3 | 4 |
| Peter Bondra | F | 1.15 | 0.88 | 2.03 | 0.86 | 78 | 6 | 6 | 3 | 4 |
| Dimitri Khristich | F | 1.01 | 0.77 | 1.78 | 0.45 | 75 | 7 | 3 | 4 | 6 |
| Al Iafrate | D | 0.50 | 0.75 | 1.26 | 1.40 | 78 | 11 | 4 | 6 | 2 |
| Kevin Hatcher | D | 0.31 | 0.77 | 1.09 | 1.13 | 72 | 12 | 3 | 5 | 2 |
| Kelly Miller | F | 0.28 | 0.21 | 0.49 | 0.38 | 67 | 8 | 4 | 3 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Don Beaupre | 12,141 | 61.7 | 3 | 3 |
| Rick Tabaracci | 144 | 68.1 | 2 | 2 |

## 9. Montreal (MTL)

**Overall: Average. Best for: Low-level (leaning).** Strength −0.3 ± 1.9 now (9th of 22), +0.5 ± 1.4 over all years (7th).

**Elo adjustment:** +19 ± 26 points (3rd of 22). Against an even coach on the average team, on neutral ice, that's a 53% win chance. With one fixed strength per coach instead of Elo, it's +4.

Used in 41 of 63 leagues (14 of them a season's top league), by 36 coaches, 1,700 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −0.7 ± 2.8 | +1.0 ± 2.6 | −1.7 ± 4.1 |
| By league strength | −3.8 ± 1.8 | +3.7 ± 3.2 | −7.6 ± 3.6 |
| Top league against others | −1.3 ± 2.2 | +2.6 ± 2.1 | −3.9 ± 3.1 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 775-910-15 | 46.0% | 45.2% | +0.8 ± 1.2 |
| Regular season | 676-790-15 | 46.1% | 44.6% | +1.5 ± 1.3 |
| Playoffs | 99-120 | 45.2% | 49.2% | −4.0 ± 3.4 |
| Home | 423-418-10 | 50.3% | 48.0% | +2.3 ± 1.7 |
| Away | 352-492-5 | 41.7% | 42.5% | −0.8 ± 1.7 |
| 2013-2019 | 216-312-3 | 40.9% | 41.7% | −0.8 ± 2.2 |
| 2020-2022 | 294-304-6 | 49.2% | 46.7% | +2.5 ± 2.0 |
| 2023-2026 | 265-294-6 | 47.4% | 47.0% | +0.4 ± 2.1 |
| High coach | 238-173-5 | 57.9% | 60.3% | −2.4 ± 2.5 |
| Mid coach | 285-346-4 | 45.2% | 42.9% | +2.3 ± 2.0 |
| Low coach | 252-391-6 | 39.2% | 37.9% | +1.3 ± 2.0 |
| Top league | 256-318-9 | 44.6% | 45.2% | −0.6 ± 2.1 |
| Other leagues | 467-446-6 | 51.2% | 48.6% | +2.5 ± 1.7 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.21 | 19th | | One-timer goals | 1.13 | 20th |
| Goals against | 4.59 | 21st | | Breakaway goals | 0.19 | 21st |
| Shots for | 11.4 | 15th | | Checks | 26.3 | 14th |
| Shots against | 12.1 | 18th | | Penalty minutes | 2.6 | 9th |
| Shooting % | 37.1 | 15th | | Faceoffs won % | 48.8 | 21st |
| Save % | 62.1 | 17th | | Attack zone time, seconds | 308 | 17th |
| Power play % | 39.2 | 19th | | Pass completion % | 57.5 | 6th |
| Penalty kill % | 56.1 | 21st | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 68.2 (9th) | 7.0 (21st) | 3.8 (3rd) | 3.8 (10th) | 3.0 (17th) | 3.0 (8th) | 2.8 (14th) | 6.0 (2nd) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kirk Muller | F | 1.47 | 0.83 | 2.30 | 1.71 | 80 | 9 | 4 | 4 | 4 |
| Brian Bellows | F | 0.82 | 0.66 | 1.49 | 0.96 | 74 | 8 | 4 | 4 | 4 |
| Vincent Damphousse | F | 0.55 | 0.44 | 0.99 | 0.48 | 74 | 6 | 4 | 3 | 3 |
| Eric Desjardins | D | 0.24 | 0.71 | 0.95 | 1.50 | 68 | 9 | 3 | 3 | 2 |
| Matt Schneider | D | 0.20 | 0.68 | 0.88 | 1.18 | 66 | 7 | 4 | 3 | 2 |
| Stephan Lebeau | F | 0.44 | 0.31 | 0.75 | 0.21 | 74 | 5 | 4 | 3 | 5 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Patrick Roy | 20,317 | 62.1 | 6 | 6 |
| Andre Racicot | 215 | 69.3 | 2 | 3 |

## 10. Toronto (TOR)

**Overall: Average. Best for: Unclear.** Strength −0.6 ± 3.6 now (10th of 22), −1.4 ± 2.8 over all years (13th).

**Elo adjustment:** −17 ± 27 points (12th of 22). Against an even coach on the average team, on neutral ice, that's a 48% win chance. With one fixed strength per coach instead of Elo, it's −16.

Used in 19 of 63 leagues (7 of them a season's top league), by 19 coaches, 771 games, most recently 2026-11-02.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −1.4 ± 4.4 | −3.5 ± 5.3 | +2.1 ± 7.3 |
| By league strength | −3.9 ± 5.6 | +4.6 ± 6.4 | −8.6 ± 8.4 |
| Top league against others | −6.7 ± 3.3 | +1.6 ± 4.5 | −8.2 ± 5.8 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 373-395-3 | 48.6% | 50.4% | −1.8 ± 1.8 |
| Regular season | 326-350-3 | 48.2% | 50.1% | −1.9 ± 1.9 |
| Playoffs | 47-45 | 51.1% | 52.2% | −1.1 ± 5.2 |
| Home | 197-188-3 | 51.2% | 53.1% | −2.0 ± 2.5 |
| Away | 176-207 | 46.0% | 47.6% | −1.7 ± 2.6 |
| 2013-2019 | 135-132-2 | 50.6% | 53.1% | −2.6 ± 3.1 |
| 2020-2022 | 160-194-1 | 45.2% | 45.5% | −0.3 ± 2.7 |
| 2023-2026 | 78-69 | 53.1% | 57.2% | −4.1 ± 4.1 |
| High coach | 182-136-1 | 57.2% | 58.8% | −1.5 ± 2.8 |
| Mid coach | 104-61 | 63.0% | 61.3% | +1.7 ± 3.9 |
| Low coach | 87-198-2 | 30.5% | 34.7% | −4.2 ± 3.0 |
| Top league | 124-171-2 | 42.0% | 47.3% | −5.3 ± 2.9 |
| Other leagues | 191-185-1 | 50.8% | 51.5% | −0.7 ± 2.6 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.99 | 22nd | | One-timer goals | 1.17 | 18th |
| Goals against | 4.18 | 6th | | Breakaway goals | 0.21 | 17th |
| Shots for | 10.4 | 22nd | | Checks | 25.4 | 18th |
| Shots against | 11.9 | 14th | | Penalty minutes | 2.5 | 5th |
| Shooting % | 38.3 | 10th | | Faceoffs won % | 50.5 | 8th |
| Save % | 64.8 | 3rd | | Attack zone time, seconds | 307 | 18th |
| Power play % | 38.7 | 21st | | Pass completion % | 53.7 | 21st |
| Penalty kill % | 60.7 | 6th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 67.6 (12th) | 7.7 (7th) | 3.2 (18th) | 3.4 (19th) | 3.3 (11th) | 3.0 (10th) | 3.5 (2nd) | 4.0 (13th) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Doug Gilmour | F | 1.42 | 0.89 | 2.31 | 1.03 | 89 | 4 | 4 | 4 | 4 |
| Dave Andreychuk | F | 0.71 | 0.56 | 1.27 | 0.70 | 72 | 11 | 3 | 4 | 4 |
| Nikolai Borshevsky | F | 0.60 | 0.55 | 1.15 | 0.49 | 71 | 6 | 4 | 3 | 4 |
| Dave Ellett | D | 0.35 | 0.68 | 1.03 | 1.17 | 72 | 9 | 4 | 5 | 1 |
| Wendel Clark | F | 0.39 | 0.37 | 0.76 | 0.24 | 69 | 8 | 3 | 5 | 3 |
| Jamie Macoun | D | 0.18 | 0.48 | 0.66 | 0.44 | 60 | 8 | 3 | 4 | 1 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Felix Potvin | 9,047 | 64.9 | 4 | 4 |
| Daren Puppa | 99 | 66.7 | 3 | 2 |

## 11. Boston (BOS)

**Overall: Average. Best for: High-level (likely).** Strength −0.8 ± 1.8 now (11th of 22), +1.5 ± 1.6 over all years (4th).

**Elo adjustment:** +11 ± 16 points (5th of 22). Against an even coach on the average team, on neutral ice, that's a 52% win chance. With one fixed strength per coach instead of Elo, it's +17.

Used in 61 of 63 leagues (19 of them a season's top league), by 48 coaches, 2,513 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +4.3 ± 1.9 | +1.2 ± 2.3 | +3.1 ± 3.0 |
| By league strength | +4.3 ± 1.9 | −1.9 ± 2.1 | +6.2 ± 2.8 |
| Top league against others | +4.5 ± 2.2 | −1.1 ± 2.4 | +5.7 ± 3.1 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,142-1,348-23 | 45.9% | 43.7% | +2.2 ± 1.0 |
| Regular season | 984-1,193-23 | 45.2% | 43.7% | +1.5 ± 1.1 |
| Playoffs | 158-155 | 50.5% | 43.6% | +6.9 ± 2.8 |
| Home | 610-638-10 | 48.9% | 46.9% | +2.0 ± 1.4 |
| Away | 532-710-13 | 42.8% | 40.4% | +2.4 ± 1.4 |
| 2013-2019 | 400-261-7 | 60.5% | 54.8% | +5.7 ± 1.9 |
| 2020-2022 | 386-581-12 | 39.9% | 40.5% | −0.6 ± 1.6 |
| 2023-2026 | 356-506-4 | 41.3% | 38.7% | +2.6 ± 1.7 |
| High coach | 417-294-9 | 58.6% | 54.3% | +4.4 ± 1.9 |
| Mid coach | 465-484-7 | 49.0% | 47.3% | +1.7 ± 1.6 |
| Low coach | 260-570-7 | 31.3% | 30.5% | +0.8 ± 1.7 |
| Top league | 450-406-8 | 52.6% | 47.4% | +5.2 ± 1.7 |
| Other leagues | 570-850-12 | 40.1% | 39.7% | +0.5 ± 1.3 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.07 | 21st | | One-timer goals | 1.31 | 8th |
| Goals against | 4.38 | 12th | | Breakaway goals | 0.20 | 18th |
| Shots for | 11.9 | 10th | | Checks | 28.5 | 6th |
| Shots against | 11.6 | 10th | | Penalty minutes | 2.6 | 7th |
| Shooting % | 34.3 | 21st | | Faceoffs won % | 49.9 | 14th |
| Save % | 62.2 | 15th | | Attack zone time, seconds | 318 | 5th |
| Power play % | 39.4 | 18th | | Pass completion % | 54.7 | 19th |
| Penalty kill % | 58.0 | 14th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 73.3 (1st) | 6.9 (23rd) | 3.8 (4th) | 4.0 (3rd) | 3.6 (2nd) | 3.0 (6th) | 3.2 (3rd) | 3.0 (16th) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cam Neely | F | 1.36 | 0.75 | 2.11 | 1.19 | 86 | 10 | 4 | 4 | 5 |
| Adam Oates | F | 1.02 | 0.88 | 1.90 | 0.89 | 93 | 7 | 4 | 3 | 4 |
| Vladimir Ruzicka | F | 0.57 | 0.52 | 1.09 | 0.52 | 67 | 10 | 4 | 4 | 3 |
| Ray Bourque | D | 0.45 | 0.62 | 1.06 | 1.24 | 99 | 10 | 4 | 5 | 5 |
| Joe Juneau | F | 0.37 | 0.36 | 0.73 | 0.32 | 72 | 5 | 4 | 4 | 3 |
| Glen Wesley | D | 0.15 | 0.45 | 0.60 | 0.55 | 71 | 8 | 4 | 4 | 1 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Andy Moog | 24,325 | 62.6 | 4 | 4 |
| John Blue | 4,620 | 60.8 | 3 | 3 |

## 12. St. Louis (STL)

**Overall: Average. Best for: Unclear.** Strength −0.9 ± 3.2 now (12th of 22), +0.0 ± 2.6 over all years (10th).

**Elo adjustment:** −5 ± 34 points (11th of 22). Against an even coach on the average team, on neutral ice, that's a 49% win chance. With one fixed strength per coach instead of Elo, it's +5.

Used in 13 of 63 leagues (3 of them a season's top league), by 13 coaches, 553 games, most recently 2026-05-22.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −0.1 ± 3.6 | +0.7 ± 5.0 | −0.8 ± 6.2 |
| By league strength | −1.4 ± 5.1 | +1.8 ± 4.5 | −3.2 ± 6.4 |
| Top league against others | −5.1 ± 4.3* | +2.9 ± 4.0 | −8.1 ± 5.6 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 296-252-5 | 54.0% | 53.4% | +0.6 ± 2.1 |
| Regular season | 256-206-5 | 55.4% | 54.0% | +1.4 ± 2.3 |
| Playoffs | 40-46 | 46.5% | 50.2% | −3.6 ± 5.4 |
| Home | 157-118-2 | 57.1% | 56.6% | +0.5 ± 3.0 |
| Away | 139-134-3 | 50.9% | 50.2% | +0.8 ± 3.0 |
| 2013-2019 | 142-113-3 | 55.7% | 52.9% | +2.8 ± 3.1 |
| 2020-2022 | 22-29 | 43.1% | 41.7% | +1.5 ± 7.0 |
| 2023-2026 | 132-110-2 | 54.5% | 56.4% | −1.9 ± 3.2 |
| High coach | 166-122-5 | 57.6% | 59.2% | −1.6 ± 2.9 |
| Mid coach | 33-12 | 73.3% | 69.1% | +4.2 ± 7.5 |
| Low coach | 97-118 | 45.1% | 42.4% | +2.8 ± 3.4 |
| Top league | 69-73-2 | 48.6% | 56.7% | −8.1 ± 4.2 |
| Other leagues | 125-111 | 53.0% | 48.4% | +4.6 ± 3.3 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.31 | 16th | | One-timer goals | 1.46 | 1st |
| Goals against | 4.02 | 4th | | Breakaway goals | 0.20 | 20th |
| Shots for | 11.2 | 18th | | Checks | 27.6 | 7th |
| Shots against | 11.4 | 9th | | Penalty minutes | 2.5 | 4th |
| Shooting % | 38.6 | 9th | | Faceoffs won % | 49.7 | 15th |
| Save % | 64.7 | 5th | | Attack zone time, seconds | 316 | 6th |
| Power play % | 38.7 | 20th | | Pass completion % | 57.7 | 3rd |
| Penalty kill % | 57.9 | 15th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 63.8 (20th) | 7.1 (17th) | 3.2 (20th) | 3.2 (21st) | 2.8 (22nd) | 2.9 (12th) | 2.7 (17th) | 4.0 (12th) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Brett Hull | F | 1.93 | 0.80 | 2.73 | 2.27 | 81 | 9 | 4 | 6 | 3 |
| Brendan Shanahan | F | 1.00 | 1.05 | 2.05 | 1.34 | 76 | 10 | 3 | 4 | 5 |
| Craig Janney | F | 0.66 | 0.81 | 1.47 | 1.01 | 75 | 7 | 3 | 3 | 4 |
| Jeff Brown | D | 0.24 | 0.75 | 0.99 | 1.96 | 71 | 9 | 3 | 5 | 3 |
| Garth Butcher | D | 0.17 | 0.77 | 0.94 | 2.15 | 55 | 9 | 3 | 2 | 1 |
| Nelson Emerson | F | 0.20 | 0.18 | 0.38 | 0.16 | 70 | 4 | 4 | 3 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Curtis Joseph | 6,292 | 64.9 | 4 | 4 |

## 13. Edmonton (EDM)

**Overall: Average. Best for: Low-level (leaning, few games).** Strength −0.9 ± 3.3 now (13th of 22), −2.0 ± 2.6 over all years (15th).

**Elo adjustment:** −27 ± 34 points (16th of 22). Against an even coach on the average team, on neutral ice, that's a 46% win chance. With one fixed strength per coach instead of Elo, it's −28.

Used in 11 of 63 leagues (9 of them a season's top league), by 7 coaches, 497 games, most recently 2026-11-01.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −1.4 ± 3.3 | +5.5 ± 4.0* | −6.9 ± 5.1 |
| By league strength | −2.5 ± 3.6 | +6.3 ± 6.5* | −8.8 ± 7.6 |
| Top league against others | −2.2 ± 3.2 | +7.0 ± 6.0* | −9.2 ± 6.9 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 284-207-6 | 57.8% | 61.2% | −3.4 ± 2.3 |
| Regular season | 233-169-6 | 58.0% | 61.6% | −3.6 ± 2.5 |
| Playoffs | 51-38 | 57.3% | 59.3% | −2.0 ± 5.3 |
| Home | 157-89-2 | 63.8% | 64.0% | −0.2 ± 3.2 |
| Away | 127-118-4 | 51.8% | 58.4% | −6.5 ± 3.2 |
| 2013-2019 | 139-54-3 | 72.0% | 76.0% | −4.0 ± 3.6 |
| 2020-2022 | 33-24 | 57.9% | 54.0% | +3.9 ± 6.6 |
| 2023-2026 | 112-129-3 | 46.5% | 51.0% | −4.6 ± 3.2 |
| High coach | 245-130-5 | 65.3% | 68.3% | −2.9 ± 2.6 |
| Mid coach | 10-29-1 | 25.6% | 42.6% | −17.0 ± 8.0 |
| Low coach | 29-48 | 37.7% | 36.1% | +1.5 ± 5.7 |
| Top league | 228-166-3 | 57.9% | 61.4% | −3.6 ± 2.5 |
| Other leagues | 26-20 | 56.5% | 51.3% | +5.3 ± 7.4 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.35 | 14th | | One-timer goals | 1.38 | 3rd |
| Goals against | 3.67 | 2nd | | Breakaway goals | 0.19 | 22nd |
| Shots for | 10.9 | 21st | | Checks | 26.5 | 13th |
| Shots against | 10.4 | 1st | | Penalty minutes | 2.6 | 6th |
| Shooting % | 40.0 | 3rd | | Faceoffs won % | 49.6 | 19th |
| Save % | 64.8 | 4th | | Attack zone time, seconds | 316 | 7th |
| Power play % | 42.8 | 11th | | Pass completion % | 58.6 | 2nd |
| Penalty kill % | 61.5 | 5th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 63.8 (19th) | 7.7 (6th) | 3.4 (13th) | 3.5 (13th) | 3.1 (15th) | 2.5 (22nd) | 2.9 (7th) | 4.0 (6th) |

Hidden bonus: +1 at home, −2 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Petr Klima | F | 1.57 | 0.83 | 2.40 | 1.32 | 76 | 7 | 5 | 4 | 5 |
| Craig Simpson | F | 1.19 | 0.94 | 2.12 | 1.27 | 69 | 8 | 3 | 4 | 5 |
| Shayne Corson | F | 0.80 | 1.02 | 1.82 | 1.34 | 71 | 9 | 4 | 3 | 2 |
| Dave Manson | D | 0.37 | 0.82 | 1.19 | 2.06 | 74 | 9 | 4 | 5 | 1 |
| Igor Kravchuk | D | 0.27 | 0.79 | 1.06 | 1.85 | 66 | 9 | 3 | 3 | 2 |
| Doug Weight | F | 0.04 | 0.07 | 0.11 | 0.09 | 65 | 6 | 3 | 3 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Bill Ranford | 5,189 | 64.9 | 4 | 4 |

## 14. Winnipeg (WPG)

**Overall: Average. Best for: Both alike.** Strength −1.3 ± 1.8 now (14th of 22), −3.6 ± 1.6 over all years (17th).

**Elo adjustment:** −29 ± 19 points (17th of 22). Against an even coach on the average team, on neutral ice, that's a 46% win chance. With one fixed strength per coach instead of Elo, it's −35.

Used in 30 of 63 leagues (12 of them a season's top league), by 24 coaches, 1,279 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −3.7 ± 2.5 | −2.5 ± 4.0 | −1.2 ± 5.0 |
| By league strength | −0.6 ± 1.7 | −3.2 ± 4.1 | +2.6 ± 4.6 |
| Top league against others | −3.2 ± 2.6 | −3.8 ± 2.6 | +0.7 ± 3.8 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 624-647-8 | 49.1% | 54.1% | −5.0 ± 1.4 |
| Regular season | 543-551-8 | 49.6% | 54.6% | −5.0 ± 1.5 |
| Playoffs | 81-96 | 45.8% | 50.9% | −5.1 ± 3.8 |
| Home | 331-299-6 | 52.5% | 57.3% | −4.7 ± 2.0 |
| Away | 293-348-2 | 45.7% | 51.0% | −5.3 ± 2.0 |
| 2013-2019 | 161-186-1 | 46.4% | 53.4% | −7.0 ± 2.7 |
| 2020-2022 | 263-293-3 | 47.3% | 54.4% | −7.1 ± 2.1 |
| 2023-2026 | 200-168-4 | 54.3% | 54.4% | −0.1 ± 2.6 |
| High coach | 300-269-2 | 52.7% | 59.0% | −6.3 ± 2.1 |
| Mid coach | 213-184-3 | 53.7% | 57.9% | −4.3 ± 2.5 |
| Low coach | 111-194-3 | 36.4% | 40.1% | −3.7 ± 2.9 |
| Top league | 267-253-3 | 51.3% | 55.4% | −4.0 ± 2.2 |
| Other leagues | 264-284-4 | 48.2% | 52.6% | −4.5 ± 2.1 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.30 | 17th | | One-timer goals | 1.00 | 22nd |
| Goals against | 4.32 | 10th | | Breakaway goals | 0.21 | 16th |
| Shots for | 11.0 | 20th | | Checks | 23.4 | 22nd |
| Shots against | 12.1 | 19th | | Penalty minutes | 2.6 | 11th |
| Shooting % | 39.0 | 4th | | Faceoffs won % | 50.9 | 5th |
| Save % | 64.5 | 6th | | Attack zone time, seconds | 305 | 20th |
| Power play % | 41.6 | 14th | | Pass completion % | 56.8 | 8th |
| Penalty kill % | 57.5 | 18th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 67.9 (11th) | 7.0 (22nd) | 3.3 (16th) | 3.8 (7th) | 3.2 (14th) | 3.1 (5th) | 2.9 (9th) | 4.0 (15th) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Teemu Selanne | F | 1.78 | 0.72 | 2.50 | 1.30 | 90 | 6 | 6 | 4 | 5 |
| Alexei Zhamnov | F | 0.85 | 0.79 | 1.64 | 0.87 | 78 | 7 | 3 | 3 | 4 |
| Thomas Steen | F | 0.64 | 0.69 | 1.33 | 0.75 | 73 | 8 | 3 | 3 | 4 |
| Phil Housley | D | 0.42 | 0.68 | 1.10 | 1.04 | 84 | 6 | 5 | 3 | 2 |
| Teppo Numminen | D | 0.20 | 0.55 | 0.74 | 0.63 | 68 | 7 | 3 | 3 | 2 |
| Evgeny Davydov | F | 0.20 | 0.19 | 0.39 | 0.19 | 64 | 6 | 4 | 4 | 4 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Bob Essensa | 15,416 | 64.6 | 4 | 4 |
| Jim Hrivnak | 79 | 62.0 | 2 | 2 |

## 15. Detroit (DET)

**Overall: Average. Best for: Both alike.** Strength −1.5 ± 1.8 now (15th of 22), −1.5 ± 1.6 over all years (14th).

**Elo adjustment:** +9 ± 15 points (7th of 22). Against an even coach on the average team, on neutral ice, that's a 51% win chance. With one fixed strength per coach instead of Elo, it's −7.

Used in 59 of 63 leagues (18 of them a season's top league), by 45 coaches, 2,327 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −0.8 ± 2.5 | −2.9 ± 3.3 | +2.1 ± 4.0 |
| By league strength | −1.3 ± 1.7 | −1.1 ± 3.4 | −0.1 ± 3.8 |
| Top league against others | −1.6 ± 1.6 | −0.8 ± 2.6 | −0.9 ± 3.0 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 972-1,340-15 | 42.0% | 42.3% | −0.3 ± 1.0 |
| Regular season | 881-1,255-15 | 41.2% | 41.5% | −0.2 ± 1.1 |
| Playoffs | 91-85 | 51.7% | 52.7% | −1.0 ± 3.8 |
| Home | 494-660-10 | 42.8% | 45.1% | −2.3 ± 1.5 |
| Away | 478-680-5 | 41.3% | 39.6% | +1.7 ± 1.5 |
| 2013-2019 | 205-347-3 | 37.1% | 39.8% | −2.7 ± 2.1 |
| 2020-2022 | 434-528-5 | 45.1% | 46.0% | −0.9 ± 1.6 |
| 2023-2026 | 333-465-7 | 41.7% | 39.6% | +2.1 ± 1.8 |
| High coach | 250-184-4 | 57.6% | 58.8% | −1.2 ± 2.4 |
| Mid coach | 373-531-6 | 41.3% | 39.8% | +1.5 ± 1.7 |
| Low coach | 349-625-5 | 35.8% | 37.4% | −1.5 ± 1.6 |
| Top league | 291-447-4 | 39.4% | 39.8% | −0.4 ± 1.8 |
| Other leagues | 618-766-9 | 44.7% | 44.5% | +0.2 ± 1.3 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.13 | 20th | | One-timer goals | 1.21 | 15th |
| Goals against | 4.91 | 22nd | | Breakaway goals | 0.24 | 10th |
| Shots for | 11.2 | 16th | | Checks | 24.1 | 20th |
| Shots against | 13.0 | 22nd | | Penalty minutes | 2.6 | 15th |
| Shooting % | 36.7 | 16th | | Faceoffs won % | 49.7 | 17th |
| Save % | 62.4 | 13th | | Attack zone time, seconds | 306 | 19th |
| Power play % | 38.6 | 22nd | | Pass completion % | 55.9 | 13th |
| Penalty kill % | 56.5 | 20th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 71.3 (4th) | 7.0 (20th) | 3.6 (9th) | 4.2 (2nd) | 3.7 (1st) | 2.9 (11th) | 2.6 (19th) | 4.0 (5th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Steve Yzerman | F | 1.48 | 0.88 | 2.36 | 1.03 | 95 | 6 | 5 | 4 | 5 |
| Sergei Fedorov | F | 1.02 | 0.83 | 1.86 | 0.85 | 84 | 7 | 4 | 4 | 4 |
| Dino Ciccarelli | F | 0.86 | 0.73 | 1.59 | 0.60 | 80 | 5 | 4 | 5 | 5 |
| Paul Coffey | D | 0.37 | 0.70 | 1.06 | 0.99 | 83 | 9 | 5 | 4 | 1 |
| Steve Chiasson | D | 0.13 | 0.54 | 0.67 | 0.64 | 68 | 9 | 3 | 4 | 1 |
| Nicklas Lidstrom | D | 0.05 | 0.14 | 0.18 | 0.25 | 66 | 5 | 3 | 4 | 1 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Tim Cheveldae | 29,583 | 62.4 | 4 | 4 |
| Vincent Riendeau | 682 | 65.7 | 3 | 2 |

## 16. Philadelphia (PHI)

**Overall: Poor. Best for: Low-level (leaning).** Strength −2.5 ± 2.8 now (16th of 22), −1.1 ± 2.5 over all years (12th).

**Elo adjustment:** +3 ± 37 points (9th of 22). Against an even coach on the average team, on neutral ice, that's a 50% win chance. With one fixed strength per coach instead of Elo, it's −25.

Used in 15 of 63 leagues (6 of them a season's top league), by 14 coaches, 643 games, most recently 2025-11-20.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −5.1 ± 3.4 | +3.9 ± 7.8 | −9.1 ± 8.4 |
| By league strength | −4.0 ± 2.8 | +2.6 ± 5.6 | −6.5 ± 6.5 |
| Top league against others | −3.8 ± 2.9 | +2.0 ± 5.1 | −5.7 ± 5.6 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 309-332-2 | 48.2% | 50.8% | −2.6 ± 2.0 |
| Regular season | 265-284-2 | 48.3% | 50.3% | −2.0 ± 2.1 |
| Playoffs | 44-48 | 47.8% | 53.8% | −5.9 ± 5.2 |
| Home | 165-155 | 51.6% | 53.6% | −2.0 ± 2.8 |
| Away | 144-177-2 | 44.9% | 48.0% | −3.1 ± 2.8 |
| 2013-2019 | 49-69-2 | 41.5% | 40.0% | +1.5 ± 4.6 |
| 2020-2022 | 94-92 | 50.5% | 52.5% | −1.9 ± 3.7 |
| 2023-2026 | 166-171 | 49.3% | 53.6% | −4.4 ± 2.7 |
| High coach | 104-110 | 48.6% | 57.9% | −9.3 ± 3.4 |
| Mid coach | 149-101-1 | 59.6% | 58.5% | +1.1 ± 3.2 |
| Low coach | 56-121-1 | 31.6% | 31.4% | +0.3 ± 3.8 |
| Top league | 125-133 | 48.4% | 55.5% | −7.0 ± 3.1 |
| Other leagues | 157-155-1 | 50.3% | 49.8% | +0.6 ± 2.8 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.42 | 12th | | One-timer goals | 1.37 | 4th |
| Goals against | 4.51 | 19th | | Breakaway goals | 0.23 | 13th |
| Shots for | 12.3 | 5th | | Checks | 27.4 | 9th |
| Shots against | 12.0 | 16th | | Penalty minutes | 2.6 | 14th |
| Shooting % | 36.0 | 18th | | Faceoffs won % | 47.8 | 22nd |
| Save % | 62.5 | 12th | | Attack zone time, seconds | 310 | 14th |
| Power play % | 44.7 | 5th | | Pass completion % | 56.1 | 12th |
| Penalty kill % | 57.0 | 19th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 63.9 (18th) | 7.3 (16th) | 3.0 (21st) | 3.4 (18th) | 2.9 (20th) | 3.0 (9th) | 2.8 (15th) | 4.0 (9th) |

Hidden bonus: +2 at home, −2 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Eric Lindros | F | 1.92 | 0.79 | 2.71 | 3.80 | 84 | 12 | 3 | 4 | 6 |
| Mark Recchi | F | 1.04 | 0.89 | 1.93 | 1.69 | 83 | 6 | 4 | 4 | 5 |
| Rod BrindAmour | F | 0.69 | 0.65 | 1.34 | 1.49 | 75 | 9 | 3 | 4 | 4 |
| Dimitri Yushkevich | D | 0.18 | 0.73 | 0.91 | 2.09 | 59 | 7 | 3 | 3 | 1 |
| Pelle Eklund | F | 0.33 | 0.35 | 0.68 | 0.38 | 75 | 5 | 4 | 3 | 3 |
| Greg Hawgood | D | 0.06 | 0.35 | 0.41 | 0.95 | 58 | 7 | 3 | 3 | 2 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Tommy Soderstrom | 7,679 | 62.6 | 4 | 4 |
| Dominic Roussel | 32 | 68.8 | 3 | 3 |

## 17. Quebec (QUE)

**Overall: Poor. Best for: High-level (likely).** Strength −3.2 ± 3.0 now (17th of 22), −6.3 ± 2.4 over all years (20th).

**Elo adjustment:** −33 ± 31 points (18th of 22). Against an even coach on the average team, on neutral ice, that's a 45% win chance. With one fixed strength per coach instead of Elo, it's −55.

Used in 21 of 63 leagues (9 of them a season's top league), by 16 coaches, 895 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −3.3 ± 2.8 | −17.1 ± 13.0* | +13.8 ± 13.3 |
| By league strength | −0.7 ± 3.2 | −22.2 ± 4.9* | +21.5 ± 6.3 |
| Top league against others | +1.1 ± 2.8 | −16.1 ± 3.4 | +17.3 ± 4.7 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 458-428-9 | 51.7% | 59.2% | −7.5 ± 1.7 |
| Regular season | 387-354-9 | 52.2% | 60.0% | −7.8 ± 1.8 |
| Playoffs | 71-74 | 49.0% | 54.6% | −5.7 ± 4.2 |
| Home | 229-216-5 | 51.5% | 61.7% | −10.3 ± 2.4 |
| Away | 229-212-4 | 51.9% | 56.6% | −4.6 ± 2.4 |
| 2013-2019 | 236-213-5 | 52.6% | 60.1% | −7.6 ± 2.4 |
| 2020-2022 | 102-126-3 | 44.7% | 59.5% | −14.8 ± 3.3 |
| 2023-2026 | 120-89-1 | 57.4% | 56.7% | +0.7 ± 3.5 |
| High coach | 364-236-6 | 60.7% | 65.6% | −4.9 ± 2.0 |
| Mid coach | 81-131-2 | 38.2% | 50.3% | −12.1 ± 3.4 |
| Low coach | 13-61-1 | 17.6% | 32.5% | −15.0 ± 5.8 |
| Top league | 226-173-4 | 56.6% | 56.5% | +0.1 ± 2.5 |
| Other leagues | 139-174-2 | 44.4% | 60.2% | −15.8 ± 2.8 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.54 | 6th | | One-timer goals | 1.28 | 9th |
| Goals against | 4.42 | 13th | | Breakaway goals | 0.24 | 11th |
| Shots for | 11.9 | 8th | | Checks | 25.3 | 19th |
| Shots against | 11.9 | 13th | | Penalty minutes | 2.6 | 10th |
| Shooting % | 38.1 | 13th | | Faceoffs won % | 51.1 | 4th |
| Save % | 62.8 | 11th | | Attack zone time, seconds | 311 | 13th |
| Power play % | 46.2 | 2nd | | Pass completion % | 56.2 | 10th |
| Penalty kill % | 57.8 | 16th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 68.1 (10th) | 6.8 (25th) | 3.7 (8th) | 3.5 (15th) | 3.5 (5th) | 3.3 (1st) | 2.3 (24th) | 4.0 (11th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mats Sundin | F | 1.55 | 1.01 | 2.56 | 1.27 | 79 | 7 | 4 | 4 | 5 |
| Joe Sakic | F | 1.13 | 0.89 | 2.02 | 1.06 | 83 | 6 | 4 | 4 | 5 |
| Steve Duchesne | D | 0.32 | 0.80 | 1.12 | 1.46 | 72 | 8 | 4 | 4 | 2 |
| Owen Nolan | F | 0.66 | 0.43 | 1.09 | 0.38 | 71 | 8 | 4 | 4 | 4 |
| Curtis Leschyshyn | D | 0.18 | 0.59 | 0.77 | 1.36 | 62 | 9 | 4 | 2 | 3 |
| Valeri Kamensky | F | 0.36 | 0.29 | 0.65 | 0.47 | 73 | 8 | 4 | 5 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Ron Hextall | 8,502 | 63.7 | 4 | 4 |
| Stephane Fiset | 2,054 | 59.3 | 3 | 2 |

## 18. Hartford (HFD)

**Overall: Poor. Best for: Both alike (few games).** Strength −3.5 ± 3.4 now (18th of 22), −2.7 ± 2.9 over all years (16th).

**Elo adjustment:** −53* ± 14 points (19th of 22). Against an even coach on the average team, on neutral ice, that's a 42% win chance. With one fixed strength per coach instead of Elo, it's −28.

Used in 5 of 63 leagues (3 of them a season's top league), by 5 coaches, 228 games, most recently 2025-06-04.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −1.4 ± 5.1 | −0.2 ± 6.8* | −1.1 ± 8.8 |
| By league strength | −3.9 ± 2.7* | −1.9 ± 3.7* | −2.0 ± 4.6 |
| Top league against others | −0.5 ± 4.9 | −1.7 ± 3.3* | +1.2 ± 6.5 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 129-98-1 | 56.8% | 62.0% | −5.2 ± 3.3 |
| Regular season | 103-77-1 | 57.2% | 61.8% | −4.6 ± 3.7 |
| Playoffs | 26-21 | 55.3% | 62.9% | −7.5 ± 7.3 |
| Home | 70-43-1 | 61.9% | 65.0% | −3.1 ± 4.7 |
| Away | 59-55 | 51.8% | 59.0% | −7.3 ± 4.7 |
| 2013-2019 | 72-54-1 | 57.1% | 61.4% | −4.2 ± 4.5 |
| 2023-2026 | 57-44 | 56.4% | 62.8% | −6.4 ± 5.0 |
| High coach | 97-52-1 | 65.1% | 69.5% | −4.4 ± 4.1 |
| Mid coach | 12-22 | 35.3% | 44.6% | −9.3 ± 8.6 |
| Low coach | 20-24 | 45.5% | 50.0% | −4.6 ± 7.5 |
| Top league | 97-52-1 | 65.1% | 69.5% | −4.4 ± 4.1 |
| Other leagues | 20-24 | 45.5% | 50.0% | −4.6 ± 7.5 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.87 | 1st | | One-timer goals | 1.23 | 13th |
| Goals against | 4.15 | 5th | | Breakaway goals | 0.26 | 3rd |
| Shots for | 11.2 | 17th | | Checks | 27.5 | 8th |
| Shots against | 10.7 | 3rd | | Penalty minutes | 2.6 | 8th |
| Shooting % | 43.4 | 1st | | Faceoffs won % | 52.4 | 2nd |
| Save % | 61.1 | 21st | | Attack zone time, seconds | 313 | 11th |
| Power play % | 44.4 | 6th | | Pass completion % | 56.4 | 9th |
| Penalty kill % | 58.7 | 10th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 62.6 (21st) | 7.4 (12th) | 3.3 (14th) | 3.4 (16th) | 3.1 (16th) | 2.6 (19th) | 2.8 (13th) | 4.0 (7th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pat Verbeek | F | 1.61 | 0.93 | 2.54 | 2.63 | 74 | 7 | 4 | 4 | 4 |
| Geoff Sanderson | F | 1.30 | 1.16 | 2.46 | 1.71 | 73 | 6 | 4 | 4 | 4 |
| Zarley Zalapski | D | 0.52 | 0.86 | 1.38 | 3.71 | 80 | 10 | 4 | 4 | 2 |
| Eric Weinrich | D | 0.36 | 0.85 | 1.21 | 3.54 | 64 | 10 | 4 | 3 | 2 |
| Patrick Poulin | F | 0.37 | 0.36 | 0.72 | 1.42 | 58 | 10 | 3 | 3 | 3 |
| Andrew Cassels | F | 0.31 | 0.26 | 0.57 | 0.23 | 65 | 7 | 3 | 2 | 4 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Sean Burke | 2,330 | 61.7 | 4 | 4 |
| Mario Gosselin | 61 | 52.5 | 2 | 2 |

## 19. Buffalo (BUF)

**Overall: Poor. Best for: Both alike.** Strength −3.6 ± 1.8 now (19th of 22), −4.1 ± 1.5 over all years (18th).

**Elo adjustment:** −25 ± 16 points (13th of 22). Against an even coach on the average team, on neutral ice, that's a 46% win chance. With one fixed strength per coach instead of Elo, it's −30.

Used in 49 of 63 leagues (16 of them a season's top league), by 39 coaches, 2,103 games, most recently 2026-11-01.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −1.4 ± 2.1 | −5.8 ± 2.9 | +4.4 ± 3.4 |
| By league strength | −3.4 ± 2.5 | −5.4 ± 3.3 | +2.0 ± 4.2 |
| Top league against others | −3.4 ± 2.2 | −4.8 ± 2.4 | +1.4 ± 3.0 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,034-1,059-10 | 49.4% | 53.9% | −4.5 ± 1.1 |
| Regular season | 869-917-10 | 48.7% | 53.9% | −5.3 ± 1.2 |
| Playoffs | 165-142 | 53.7% | 53.7% | +0.0 ± 2.9 |
| Home | 552-492-4 | 52.9% | 56.9% | −4.1 ± 1.5 |
| Away | 482-567-6 | 45.9% | 50.9% | −4.9 ± 1.5 |
| 2013-2019 | 290-307-3 | 48.6% | 53.5% | −5.0 ± 2.0 |
| 2020-2022 | 411-468-6 | 46.8% | 51.2% | −4.4 ± 1.7 |
| 2023-2026 | 333-284-1 | 54.0% | 58.2% | −4.2 ± 2.0 |
| High coach | 535-358-1 | 59.9% | 62.4% | −2.5 ± 1.7 |
| Mid coach | 203-262-3 | 43.7% | 51.4% | −7.8 ± 2.3 |
| Low coach | 296-439-6 | 40.3% | 45.1% | −4.9 ± 1.8 |
| Top league | 358-347-1 | 50.8% | 55.0% | −4.2 ± 1.9 |
| Other leagues | 555-601-7 | 48.0% | 52.8% | −4.8 ± 1.5 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.53 | 8th | | One-timer goals | 1.18 | 17th |
| Goals against | 4.55 | 20th | | Breakaway goals | 0.29 | 1st |
| Shots for | 11.6 | 12th | | Checks | 25.7 | 17th |
| Shots against | 12.3 | 20th | | Penalty minutes | 2.6 | 12th |
| Shooting % | 38.9 | 5th | | Faceoffs won % | 50.3 | 9th |
| Save % | 63.0 | 9th | | Attack zone time, seconds | 309 | 16th |
| Power play % | 41.7 | 13th | | Pass completion % | 55.2 | 18th |
| Penalty kill % | 57.7 | 17th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 67.2 (14th) | 6.8 (24th) | 3.8 (5th) | 3.8 (6th) | 2.9 (19th) | 2.7 (17th) | 2.9 (6th) | 5.0 (3rd) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Alexnder Mogilny | F | 2.06 | 0.78 | 2.84 | 1.28 | 96 | 7 | 6 | 4 | 5 |
| Pat LaFontaine | F | 1.01 | 0.89 | 1.89 | 0.80 | 91 | 5 | 4 | 3 | 4 |
| Dale Hawerchuk | F | 0.72 | 0.86 | 1.58 | 0.69 | 74 | 6 | 4 | 3 | 1 |
| Petr Svoboda | D | 0.21 | 0.57 | 0.77 | 0.68 | 65 | 5 | 4 | 3 | 0 |
| Richard Smehlik | D | 0.16 | 0.57 | 0.73 | 0.93 | 60 | 10 | 3 | 3 | 1 |
| Doug Bodger | D | 0.10 | 0.42 | 0.52 | 0.52 | 53 | 10 | 3 | 2 | 1 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Grant Fuhr | 25,107 | 63.3 | 5 | 5 |
| Dominik Hasek | 531 | 58.6 | 3 | 2 |

## 20. NY Islanders (NYI)

**Overall: Poor. Best for: Unclear (few games).** Strength −6.0 ± 2.7 now (20th of 22), −9.6 ± 2.2 over all years (21st).

**Elo adjustment:** −138* ± 34 points (22nd of 22). Against an even coach on the average team, on neutral ice, that's a 31% win chance. With one fixed strength per coach instead of Elo, it's −74.

Used in 8 of 63 leagues (3 of them a season's top league), by 6 coaches, 295 games, most recently 2026-10-31.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −8.7 ± 2.7 | too few | too few |
| By league strength | −9.9 ± 4.4 | −11.2 ± 4.6* | +1.4 ± 6.4 |
| Top league against others | −10.1 ± 2.7* | −6.3 ± 4.7* | −3.9 ± 5.3 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 153-140-2 | 52.2% | 62.7% | −10.5 ± 2.9 |
| Regular season | 124-121-2 | 50.6% | 62.5% | −11.9 ± 3.2 |
| Playoffs | 29-19 | 60.4% | 63.9% | −3.5 ± 7.2 |
| Home | 80-65-1 | 55.2% | 65.3% | −10.2 ± 4.2 |
| Away | 73-75-1 | 49.3% | 60.2% | −10.9 ± 4.1 |
| 2013-2019 | 27-61-1 | 30.7% | 37.4% | −6.7 ± 5.3 |
| 2023-2026 | 126-79-1 | 61.5% | 73.6% | −12.1 ± 3.5 |
| High coach | 118-88-1 | 57.3% | 69.4% | −12.1 ± 3.5 |
| Mid coach | 28-36-1 | 43.8% | 55.5% | −11.8 ± 6.2 |
| Low coach | 7-16 | 30.4% | 23.0% | +7.4 ± 10.4 |
| Top league | 60-48-1 | 55.6% | 69.8% | −14.2 ± 4.8 |
| Other leagues | 73-47 | 60.8% | 67.4% | −6.5 ± 4.6 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.53 | 7th | | One-timer goals | 1.36 | 5th |
| Goals against | 4.44 | 15th | | Breakaway goals | 0.20 | 19th |
| Shots for | 11.1 | 19th | | Checks | 27.0 | 10th |
| Shots against | 11.3 | 8th | | Penalty minutes | 2.2 | 2nd |
| Shooting % | 40.8 | 2nd | | Faceoffs won % | 49.9 | 12th |
| Save % | 60.6 | 22nd | | Attack zone time, seconds | 313 | 10th |
| Power play % | 45.1 | 4th | | Pass completion % | 62.3 | 1st |
| Penalty kill % | 61.6 | 4th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 64.6 (17th) | 7.5 (10th) | 3.2 (17th) | 3.4 (17th) | 3.2 (13th) | 2.8 (13th) | 2.4 (22nd) | 2.0 (25th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pierre Turgeon | F | 1.71 | 1.00 | 2.71 | 3.41 | 82 | 9 | 4 | 4 | 5 |
| Benoit Hogue | F | 1.31 | 0.99 | 2.29 | 2.22 | 78 | 7 | 5 | 3 | 5 |
| Derek King | F | 0.56 | 0.59 | 1.15 | 1.42 | 64 | 9 | 2 | 4 | 5 |
| Vladimir Malakhov | D | 0.23 | 0.85 | 1.08 | 2.72 | 63 | 10 | 3 | 4 | 2 |
| Uwe Krupp | D | 0.12 | 0.35 | 0.46 | 2.02 | 53 | 14 | 2 | 3 | 2 |
| Steve Thomas | F | 0.16 | 0.24 | 0.40 | 0.19 | 72 | 6 | 4 | 3 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Glenn Healy | 3,321 | 60.6 | 2 | 2 |

## 21. San Jose (SJ)

**Overall: Poor. Best for: Unclear (few games).** Strength −7.7 ± 4.5 now (21st of 22), −11.8 ± 6.3 over all years (22nd).

**Elo adjustment:** −102* ± 61 points (20th of 22). Against an even coach on the average team, on neutral ice, that's a 36% win chance. With one fixed strength per coach instead of Elo, it's −82.

Used in 4 of 63 leagues (0 of them a season's top league), by 3 coaches, 153 games, most recently 2026-05-26.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −14.0 ± 6.1* | too few | too few |
| By league strength | too few | −6.9 ± 5.0* | too few |
| Top league against others | too few | −11.3 ± 6.0 | too few |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 96-55-2 | 63.6% | 74.5% | −10.9 ± 4.1 |
| Regular season | 76-40-2 | 65.5% | 77.2% | −11.6 ± 4.6 |
| Playoffs | 20-15 | 57.1% | 65.5% | −8.4 ± 8.5 |
| Home | 54-20-2 | 73.0% | 76.8% | −3.8 ± 5.8 |
| Away | 42-35 | 54.5% | 72.3% | −17.7 ± 5.7 |
| 2013-2019 | 58-44-2 | 56.9% | 69.9% | −13.0 ± 5.0 |
| 2023-2026 | 38-11 | 77.6% | 84.0% | −6.5 ± 7.1 |
| High coach | 47-32-1 | 59.5% | 74.2% | −14.7 ± 5.6 |
| Mid coach | 49-23-1 | 68.1% | 74.8% | −6.7 ± 5.9 |
| Other leagues | 96-55-2 | 63.6% | 74.5% | −10.9 ± 4.1 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.69 | 2nd | | One-timer goals | 1.15 | 19th |
| Goals against | 3.56 | 1st | | Breakaway goals | 0.25 | 6th |
| Shots for | 12.3 | 3rd | | Checks | 23.6 | 21st |
| Shots against | 10.6 | 2nd | | Penalty minutes | 2.2 | 1st |
| Shooting % | 38.1 | 12th | | Faceoffs won % | 53.9 | 1st |
| Save % | 66.4 | 1st | | Attack zone time, seconds | 304 | 21st |
| Power play % | 46.4 | 1st | | Pass completion % | 52.0 | 22nd |
| Penalty kill % | 65.8 | 1st | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 54.1 (23rd) | 6.7 (26th) | 2.8 (23rd) | 2.8 (23rd) | 2.8 (21st) | 2.1 (25th) | 2.3 (25th) | 2.0 (26th) |

Hidden bonus: +1 at home, −2 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pat Falloon | F | 1.73 | 0.91 | 2.63 | 0.39 | 61 | 7 | 4 | 3 | 2 |
| Johan Garpenlov | F | 0.89 | 0.66 | 1.55 | 0.37 | 55 | 6 | 3 | 2 | 3 |
| Doug Wilson | D | 0.42 | 0.78 | 1.20 | 0.44 | 65 | 7 | 3 | 6 | 1 |
| Sandis Ozolinsh | D | 0.28 | 0.67 | 0.95 | 0.33 | 59 | 7 | 3 | 3 | 2 |
| Perry Berezan | F | 0.59 | 0.34 | 0.93 | 0.16 | 53 | 7 | 4 | 2 | 2 |
| Kelly Kisio | F | 0.29 | 0.37 | 0.65 | 0.17 | 63 | 6 | 2 | 3 | 4 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Arturs Irbe | 1,594 | 66.6 | 2 | 3 |
| Jeff Hackett | 9 | 55.6 | 2 | 2 |

## 22. Dallas (DAL)

**Overall: Poor. Best for: Unclear (few games).** Strength −9.3 ± 6.2 now (22nd of 22), −5.5 ± 5.7 over all years (19th).

**Elo adjustment:** −116* ± 67 points (21st of 22). Against an even coach on the average team, on neutral ice, that's a 34% win chance. With one fixed strength per coach instead of Elo, it's −55.

Used in 5 of 63 leagues (1 of them a season's top league), by 6 coaches, 182 games, most recently 2026-11-01.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −7.1 ± 6.8* | −20.5 ± 13.1* | +13.4 ± 14.8 |
| By league strength | −4.5 ± 8.8* | too few | too few |
| Top league against others | −5.7 ± 9.4* | −5.5 ± 6.4 | −0.2 ± 11.5 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 87-94-1 | 48.1% | 54.9% | −6.9 ± 3.7 |
| Regular season | 82-83-1 | 49.7% | 55.5% | −5.8 ± 3.9 |
| Playoffs | 5-11 | 31.2% | 49.1% | −17.9 ± 12.5 |
| Home | 46-42-1 | 52.3% | 58.1% | −5.9 ± 5.3 |
| Away | 41-52 | 44.1% | 51.9% | −7.8 ± 5.2 |
| 2013-2019 | 35-23 | 60.3% | 67.3% | −6.9 ± 6.6 |
| 2020-2022 | 24-20 | 54.5% | 61.5% | −6.9 ± 7.5 |
| 2023-2026 | 28-51-1 | 35.4% | 42.2% | −6.8 ± 5.6 |
| High coach | 20-10 | 66.7% | 75.0% | −8.3 ± 9.1 |
| Mid coach | 63-54-1 | 53.8% | 56.5% | −2.6 ± 4.6 |
| Low coach | 4-30 | 11.8% | 31.8% | −20.0 ± 8.6 |
| Top league | 20-10 | 66.7% | 75.0% | −8.3 ± 9.1 |
| Other leagues | 67-84-1 | 44.4% | 50.9% | −6.6 ± 4.1 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.29 | 18th | | One-timer goals | 1.10 | 21st |
| Goals against | 4.46 | 17th | | Breakaway goals | 0.25 | 7th |
| Shots for | 12.6 | 1st | | Checks | 25.8 | 15th |
| Shots against | 12.5 | 21st | | Penalty minutes | 2.9 | 22nd |
| Shooting % | 34.2 | 22nd | | Faceoffs won % | 51.7 | 3rd |
| Save % | 64.4 | 7th | | Attack zone time, seconds | 302 | 22nd |
| Power play % | 42.9 | 10th | | Pass completion % | 57.0 | 7th |
| Penalty kill % | 59.1 | 8th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 64.7 (16th) | 7.0 (19th) | 3.8 (6th) | 3.8 (9th) | 3.3 (9th) | 2.6 (18th) | 2.7 (16th) | 4.0 (4th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mike Modano | F | 1.98 | 0.80 | 2.77 | 2.75 | 82 | 7 | 5 | 5 | 2 |
| Russ Courtnall | F | 0.82 | 0.37 | 1.19 | 0.85 | 73 | 6 | 6 | 4 | 3 |
| Dave Gagner | F | 0.51 | 0.58 | 1.09 | 1.29 | 75 | 6 | 4 | 3 | 4 |
| Mark Tinordi | D | 0.14 | 0.88 | 1.02 | 2.85 | 65 | 9 | 3 | 4 | 3 |
| Tommy Sjodin | D | 0.16 | 0.52 | 0.68 | 2.27 | 57 | 6 | 3 | 4 | 1 |
| Ulf Dahlen | F | 0.34 | 0.30 | 0.64 | 1.10 | 70 | 8 | 4 | 3 | 4 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Jon Casey | 2,279 | 64.5 | 4 | 3 |
