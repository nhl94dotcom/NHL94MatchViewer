# Genesis Classic team guide

Every retail team in the Genesis Classic leagues (names starting `Classic_Spring`, `Classic_Summer` or `Classic_Fall`): 22,757 games in 97 leagues, through 2026-11-03. No coach is named. The method is in [COACH_RATING.md](COACH_RATING.md).

**Jump to a team:** [Chicago](#1-chicago-chi) · [Detroit](#2-detroit-det) · [Buffalo](#3-buffalo-buf) · [Montreal](#4-montreal-mtl) · [Boston](#5-boston-bos) · [Vancouver](#6-vancouver-van) · [Dallas](#7-dallas-dal) · [Winnipeg](#8-winnipeg-wpg) · [Hartford](#9-hartford-hfd) · [Calgary](#10-calgary-cgy) · [Toronto](#11-toronto-tor) · [Los Angeles](#12-los-angeles-la) · [Philadelphia](#13-philadelphia-phi) · [Quebec](#14-quebec-que) · [New Jersey](#15-new-jersey-nj) · [NY Islanders](#16-ny-islanders-nyi) · [Edmonton](#17-edmonton-edm) · [Pittsburgh](#18-pittsburgh-pit) · [Washington](#19-washington-wsh) · [Tampa Bay](#20-tampa-bay-tb) · [St. Louis](#21-st-louis-stl) · [NY Rangers](#22-ny-rangers-nyr)

## How to read this guide

**The basics**

- **Points:** strength values are points of win chance above or below 50, against the average team as used in these leagues, with even coaches and no home edge. +5 means about a 55% chance.

- **± (spread):** about how far a value could be off by chance, from resampling whole leagues or, in the Record table, from the number of games. A value within one spread of zero can't be told from zero.

- **Results show what happened, not why.** Players choose or are given teams, and rarely used teams rest on few coaches.

- **± understates the uncertainty for rarely used teams.** Their values are pulled toward average, and ± is measured around the pulled value. A team with few games or few coaches is less certain than its ± suggests.

**Why the numbers for a team can disagree**

Two teams can have similar strengths but different Elo adjustments, or a team can have a good record and a poor strength. Usually that's not an error. Where the numbers agree, the method doesn't matter. Where they differ, the team is less certain. Use strength to judge how good a team is, and the Elo adjustment inside an Elo rating.

- **Each number uses a different yardstick for the coach.** Every team value is what's left after taking out who was coaching. Strength uses one fitted strength for each coach. The Elo adjustment uses each coach's Elo at the start of that league. A different yardstick leaves a different remainder, even with the same record.

- **Elo can run high or low for a while.** If a coach's Elo is well above how they then play, the team they're using looks worse than it is. If it's well below, the team looks better. A fitted strength reflects the coach's whole Classic career, so it's less affected by this.

- **Favorites tend to fall short of what Elo predicts.** A rating gap in Classic games is only worth about 0.6 of its face value. A team usually used by Elo favorites can therefore look worse on the Elo adjustment than on strength, and a team usually used by underdogs can look better.

- **Rarely used teams rest on a few seasons.** One or two unusual seasons, or one coach, can move their numbers a lot, and more on the Elo adjustment than on strength.

- **Each number counts different results.** Strength counts how early wins were safe as well as who won. The Elo adjustment's fit counts only who won, and it leaves out games where a coach has under 30 earlier games.

- **Strength now and strength over all years cover different games.** A team can look better or worse lately because of who has used it recently, or because the leagues have changed, so a gap between the two doesn't prove the team itself changed. Rosters in these leagues stay the same.

- **A record alone doesn't say how good a team is.** Better coaches may have used it, or worse ones. A strong team can have a modest record if weaker coaches tend to use it, and a weak team can have a good record if stronger coaches do. That's what the Expected column is for.

- **Most differences between levels don't repeat well** when half the leagues are compared with the other half, so treat them as ideas to test. The overall team order is sturdier.

**The "All teams" table**

- **#:** the team's rank by strength now.

- **Team:** the team and its abbreviation. Click a name to go to its entry.

- **Overall:** from strength now. Good is +1.5 or better, Poor is −1.5 or worse, and Average is in between.

- **Best for:** which level of player gets more from this team than from their other teams. High-level or Low-level means one does, Both alike means no gap of over 5 points, and Unclear means the measures disagree or there are too few games. A team can be Poor overall and still best for one level: that level just loses less with it.

- **Confidence:** how sure the Best for call is. Likely: all three measures of level agree on direction, and the gap is at least 1.5 spreads in two. Leaning: the same, at 1 spread. Weak: they agree on direction, the gap is at least 3 points each way, and the team is good for only that level. "Few games" means at least two values rest on under 150 appearances. A dash means no call to rate.

- **Strength now:** how much the team adds, in points, with recent games counting more. A game's weight halves every 1.5 years, so a game from 3 years ago counts a quarter as much as one played today. It's the better guide to how a team has done lately.

- **Strength, all years:** the same, with every game counting equally. It rests on more games, so it's steadier.

- **Elo adjustment:** points to add to a coach's Elo for using this team, against the average team in use. It's fitted on the league Elo: every game in order, a 1500 start, K 20, +7 for home and each team's own adjustment in the expected score, and the winner's gain and loser's loss raised by the coasting bonus. Rarely used teams are pulled toward zero, by the amount that best predicted later years. A * marks under 300 games, so treat it as rough. Tested on later years, using these inside the running Elo predicts clearly better than leaving them out.

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

- **Overall**, **Weight**, **Speed**, **Agility**, **Shot Power**, **Shot Accuracy** and **Checking:** the mean roster rating of the team's top 12 skaters by overall. Hot and cold values change them a little in play.

- **Goalie Agility:** the roster Agility of the team's higher-rated goalie. On the Genesis it sets the goalie's reach.

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
| 1 | [Chicago (CHI)](#1-chicago-chi) | Good | Both alike | — | +8.1 | +8.8 | +83 | 2,119-1,831-5 | 53.6% | 43.8% |
| 2 | [Detroit (DET)](#2-detroit-det) | Good | Both alike | — | +6.4 | +6.7 | +39 | 2,244-1,873-7 | 54.5% | 47.2% |
| 3 | [Buffalo (BUF)](#3-buffalo-buf) | Good | Both alike | — | +4.2 | +4.1 | +38 | 2,033-1,927-2 | 51.3% | 47.0% |
| 4 | [Montreal (MTL)](#4-montreal-mtl) | Good | Both alike | — | +2.5 | +2.9 | +32 | 2,016-1,837-6 | 52.3% | 48.3% |
| 5 | [Boston (BOS)](#5-boston-bos) | Average | High-level | Likely | +1.4 | +1.0 | +6 | 1,969-1,841-2 | 51.7% | 50.8% |
| 6 | [Vancouver (VAN)](#6-vancouver-van) | Average | High-level | Leaning | −0.5 | −0.7 | +6 | 1,832-2,043-4 | 47.3% | 47.7% |
| 7 | [Dallas (DAL)](#7-dallas-dal) | Average | Both alike | — | −0.8 | −1.2 | −34 | 1,397-1,274-4 | 52.3% | 53.7% |
| 8 | [Winnipeg (WPG)](#8-winnipeg-wpg) | Average | Both alike | — | −1.0 | +0.1 | −8 | 1,806-1,734-1 | 51.0% | 50.9% |
| 9 | [Hartford (HFD)](#9-hartford-hfd) | Poor | Unclear | — | −1.8 | −6.5 | −50 | 262-190 | 58.0% | 66.3% |
| 10 | [Calgary (CGY)](#10-calgary-cgy) | Poor | Both alike | — | −1.9 | −4.8 | −32 | 1,396-1,628-1 | 46.2% | 51.4% |
| 11 | [Toronto (TOR)](#11-toronto-tor) | Poor | Both alike | — | −2.7 | −2.6 | −40 | 693-879-2 | 44.1% | 46.6% |
| 12 | [Los Angeles (LA)](#12-los-angeles-la) | Poor | Unclear | — | −4.0 | −2.2 | −20 | 1,138-1,241 | 47.8% | 50.6% |
| 13 | [Philadelphia (PHI)](#13-philadelphia-phi) | Poor | Both alike | — | −5.0 | −4.9 | −22 | 507-533-5 | 48.8% | 54.5% |
| 14 | [Quebec (QUE)](#14-quebec-que) | Poor | High-level | Leaning | −5.1 | −4.6 | −43 | 1,034-1,014-2 | 50.5% | 55.4% |
| 15 | [New Jersey (NJ)](#15-new-jersey-nj) | Poor | Both alike | — | −5.5 | −5.6 | −89 | 144-165-1 | 46.6% | 53.1% |
| 16 | [NY Islanders (NYI)](#16-ny-islanders-nyi) | Poor | Unclear | Few games | −5.9 | −10.7 | −59* | 95-115 | 45.2% | 56.6% |
| 17 | [Edmonton (EDM)](#17-edmonton-edm) | Poor | Low-level | Leaning | −6.1 | −6.8 | −64 | 314-337 | 48.2% | 56.1% |
| 18 | [Pittsburgh (PIT)](#18-pittsburgh-pit) | Poor | Unclear | — | −7.9 | −10.0 | −70 | 458-674-5 | 40.5% | 51.2% |
| 19 | [Washington (WSH)](#19-washington-wsh) | Poor | Unclear | Few games | −8.6 | −7.4 | −17 | 160-197 | 44.8% | 54.2% |
| 20 | [Tampa Bay (TB)](#20-tampa-bay-tb) | Poor | Low-level | Leaning, few games | −9.4 | −13.1 | −102* | 98-108 | 47.6% | 62.2% |
| 21 | [St. Louis (STL)](#21-st-louis-stl) | Poor | Unclear | — | −10.1 | −7.5 | −59 | 471-512-1 | 47.9% | 55.3% |
| 22 | [NY Rangers (NYR)](#22-ny-rangers-nyr) | Poor | Both alike | — | −12.0 | −10.9 | −74 | 546-761 | 41.8% | 53.7% |

Too few games for a full entry: Anaheim (ANH) 1-19.

## 1. Chicago (CHI)

**Overall: Good. Best for: Both alike.** Strength +8.1 ± 1.2 now (1st of 22), +8.8 ± 1.0 over all years (1st).

**Elo adjustment:** +83 ± 11 points (1st of 22). Against an even coach on the average team, on neutral ice, that's a 62% win chance. With one fixed strength per coach instead of Elo, it's +67.

Used in 91 of 97 leagues (24 of them a season's top league), by 71 coaches, 3,955 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +9.7 ± 1.7 | +9.2 ± 2.1 | +0.6 ± 2.6 |
| By league strength | +8.4 ± 1.7 | +9.8 ± 2.1 | −1.4 ± 2.6 |
| Top league against others | +9.0 ± 1.9 | +8.8 ± 1.3 | +0.2 ± 2.3 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 2,119-1,831-5 | 53.6% | 43.8% | +9.9 ± 0.8 |
| Regular season | 1,832-1,589-5 | 53.6% | 43.8% | +9.8 ± 0.9 |
| Playoffs | 287-242 | 54.3% | 43.6% | +10.6 ± 2.2 |
| Home | 1,108-868-3 | 56.1% | 45.1% | +11.0 ± 1.1 |
| Away | 1,011-963-2 | 51.2% | 42.5% | +8.7 ± 1.1 |
| 2013-2019 | 560-490-1 | 53.3% | 43.5% | +9.8 ± 1.5 |
| 2020-2022 | 599-542-2 | 52.5% | 44.6% | +7.9 ± 1.5 |
| 2023-2026 | 960-799-2 | 54.6% | 43.4% | +11.2 ± 1.2 |
| High coach | 464-306 | 60.3% | 50.8% | +9.4 ± 1.8 |
| Mid coach | 773-660-1 | 53.9% | 44.1% | +9.9 ± 1.3 |
| Low coach | 882-865-4 | 50.5% | 40.4% | +10.1 ± 1.2 |
| Top league | 507-516 | 49.6% | 40.2% | +9.3 ± 1.6 |
| Other leagues | 1,612-1,315-5 | 55.1% | 45.0% | +10.1 ± 0.9 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.72 | 15th | | One-timer goals | 1.26 | 14th |
| Goals against | 3.42 | 2nd | | Breakaway goals | 0.29 | 11th |
| Shots for | 11.9 | 10th | | Checks | 27.9 | 5th |
| Shots against | 12.1 | 15th | | Penalty minutes | 3.2 | 14th |
| Shooting % | 31.2 | 13th | | Faceoffs won % | 49.3 | 20th |
| Save % | 71.9 | 2nd | | Attack zone time, seconds | 319 | 12th |
| Power play % | 38.1 | 14th | | Pass completion % | 61.3 | 17th |
| Penalty kill % | 64.2 | 3rd | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 70.8 (6th) | 7.3 (14th) | 3.4 (12th) | 3.8 (8th) | 3.4 (7th) | 2.8 (15th) | 3.5 (1st) | 6.0 (1st) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Jeremy Roenick | F | 2.04 | 0.57 | 2.61 | 7.05 | 89 | 4 | 5 | 5 | 5 |
| Steve Larmer | F | 0.70 | 0.77 | 1.48 | 3.49 | 86 | 7 | 4 | 4 | 4 |
| Joe Murphy | F | 0.35 | 0.49 | 0.85 | 1.91 | 71 | 7 | 4 | 4 | 3 |
| Chris Chelios | D | 0.17 | 0.64 | 0.81 | 5.96 | 84 | 7 | 4 | 5 | 1 |
| Steve Smith | D | 0.07 | 0.55 | 0.62 | 6.17 | 72 | 11 | 4 | 4 | 1 |
| Christan Ruuttu | F | 0.23 | 0.31 | 0.53 | 1.32 | 72 | 8 | 4 | 3 | 2 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Ed Belfour | 47,534 | 72.0 | 6 | 5 |
| Jim Waite | 349 | 75.1 | 3 | 2 |

## 2. Detroit (DET)

**Overall: Good. Best for: Both alike.** Strength +6.4 ± 1.5 now (2nd of 22), +6.7 ± 1.1 over all years (2nd).

**Elo adjustment:** +39 ± 10 points (2nd of 22). Against an even coach on the average team, on neutral ice, that's a 56% win chance. With one fixed strength per coach instead of Elo, it's +50.

Used in 93 of 97 leagues (25 of them a season's top league), by 75 coaches, 4,124 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +7.4 ± 1.8 | +7.2 ± 2.3 | +0.2 ± 2.8 |
| By league strength | +6.5 ± 1.8 | +8.8 ± 2.5 | −2.4 ± 3.1 |
| Top league against others | +7.8 ± 1.9 | +6.2 ± 1.2 | +1.5 ± 2.2 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 2,244-1,873-7 | 54.5% | 47.2% | +7.3 ± 0.8 |
| Regular season | 1,861-1,559-7 | 54.4% | 47.1% | +7.3 ± 0.9 |
| Playoffs | 383-314 | 54.9% | 47.5% | +7.4 ± 1.9 |
| Home | 1,143-919-5 | 55.4% | 48.7% | +6.8 ± 1.1 |
| Away | 1,101-954-2 | 53.6% | 45.7% | +7.8 ± 1.1 |
| 2013-2019 | 666-452-2 | 59.6% | 54.5% | +5.1 ± 1.5 |
| 2020-2022 | 699-532-1 | 56.8% | 47.3% | +9.5 ± 1.4 |
| 2023-2026 | 879-889-4 | 49.7% | 42.5% | +7.2 ± 1.2 |
| High coach | 829-496-2 | 62.6% | 55.8% | +6.7 ± 1.4 |
| Mid coach | 609-550 | 52.5% | 45.4% | +7.1 ± 1.5 |
| Low coach | 806-827-5 | 49.4% | 41.5% | +7.9 ± 1.2 |
| Top league | 513-525-2 | 49.4% | 41.2% | +8.2 ± 1.6 |
| Other leagues | 1,731-1,348-5 | 56.2% | 49.2% | +7.0 ± 0.9 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.24 | 2nd | | One-timer goals | 1.40 | 5th |
| Goals against | 3.84 | 10th | | Breakaway goals | 0.33 | 3rd |
| Shots for | 12.8 | 1st | | Checks | 23.6 | 19th |
| Shots against | 12.1 | 13th | | Penalty minutes | 3.1 | 9th |
| Shooting % | 33.1 | 7th | | Faceoffs won % | 49.6 | 17th |
| Save % | 68.2 | 10th | | Attack zone time, seconds | 328 | 2nd |
| Power play % | 42.0 | 2nd | | Pass completion % | 61.1 | 19th |
| Penalty kill % | 60.8 | 12th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 71.3 (4th) | 7.0 (21st) | 3.6 (9th) | 4.2 (3rd) | 3.7 (2nd) | 2.9 (11th) | 2.6 (18th) | 4.0 (5th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Steve Yzerman | F | 1.65 | 0.92 | 2.57 | 3.95 | 95 | 6 | 5 | 4 | 5 |
| Dino Ciccarelli | F | 1.37 | 0.76 | 2.13 | 4.60 | 80 | 5 | 4 | 5 | 5 |
| Sergei Fedorov | F | 0.76 | 0.78 | 1.54 | 3.09 | 84 | 7 | 4 | 4 | 4 |
| Nicklas Lidstrom | D | 0.10 | 0.68 | 0.78 | 4.74 | 66 | 5 | 3 | 4 | 1 |
| Paul Coffey | D | 0.16 | 0.58 | 0.74 | 4.05 | 83 | 9 | 5 | 4 | 1 |
| Dallas Drake | F | 0.11 | 0.14 | 0.26 | 0.76 | 66 | 4 | 4 | 3 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Tim Cheveldae | 49,421 | 68.3 | 4 | 4 |
| Vincent Riendeau | 199 | 60.8 | 3 | 2 |

## 3. Buffalo (BUF)

**Overall: Good. Best for: Both alike.** Strength +4.2 ± 1.1 now (3rd of 22), +4.1 ± 0.9 over all years (3rd).

**Elo adjustment:** +38 ± 10 points (3rd of 22). Against an even coach on the average team, on neutral ice, that's a 55% win chance. With one fixed strength per coach instead of Elo, it's +26.

Used in 92 of 97 leagues (25 of them a season's top league), by 69 coaches, 3,962 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +3.8 ± 1.8 | +4.0 ± 1.9 | −0.3 ± 2.8 |
| By league strength | +3.2 ± 1.7 | +6.4 ± 2.0 | −3.2 ± 2.6 |
| Top league against others | +4.3 ± 1.8 | +4.0 ± 1.1 | +0.3 ± 2.1 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 2,033-1,927-2 | 51.3% | 47.0% | +4.4 ± 0.8 |
| Regular season | 1,791-1,664-2 | 51.8% | 47.0% | +4.8 ± 0.9 |
| Playoffs | 242-263 | 47.9% | 46.8% | +1.2 ± 2.2 |
| Home | 1,060-920-2 | 53.5% | 48.3% | +5.2 ± 1.1 |
| Away | 973-1,007 | 49.1% | 45.6% | +3.5 ± 1.1 |
| 2013-2019 | 604-521 | 53.7% | 49.4% | +4.3 ± 1.5 |
| 2020-2022 | 568-568-1 | 50.0% | 45.4% | +4.6 ± 1.5 |
| 2023-2026 | 861-838-1 | 50.7% | 46.4% | +4.2 ± 1.2 |
| High coach | 660-517 | 56.1% | 53.5% | +2.6 ± 1.5 |
| Mid coach | 661-590-1 | 52.8% | 47.6% | +5.2 ± 1.4 |
| Low coach | 712-820-1 | 46.5% | 41.4% | +5.0 ± 1.3 |
| Top league | 481-544 | 46.9% | 42.8% | +4.1 ± 1.6 |
| Other leagues | 1,552-1,383-2 | 52.9% | 48.4% | +4.5 ± 0.9 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.79 | 10th | | One-timer goals | 1.21 | 18th |
| Goals against | 3.65 | 3rd | | Breakaway goals | 0.33 | 5th |
| Shots for | 12.1 | 8th | | Checks | 25.0 | 14th |
| Shots against | 11.9 | 7th | | Penalty minutes | 3.3 | 16th |
| Shooting % | 31.4 | 12th | | Faceoffs won % | 49.8 | 15th |
| Save % | 69.5 | 4th | | Attack zone time, seconds | 326 | 4th |
| Power play % | 37.6 | 17th | | Pass completion % | 60.4 | 22nd |
| Penalty kill % | 61.1 | 9th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 67.2 (14th) | 6.8 (24th) | 3.8 (4th) | 3.8 (6th) | 2.9 (19th) | 2.7 (18th) | 2.9 (6th) | 5.0 (3rd) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Alexnder Mogilny | F | 1.96 | 0.56 | 2.52 | 4.40 | 96 | 7 | 6 | 4 | 5 |
| Pat LaFontaine | F | 1.00 | 0.87 | 1.87 | 4.70 | 91 | 5 | 4 | 3 | 4 |
| Dale Hawerchuk | F | 0.54 | 0.79 | 1.33 | 2.95 | 74 | 6 | 4 | 3 | 1 |
| Petr Svoboda | D | 0.10 | 0.67 | 0.77 | 5.32 | 65 | 5 | 4 | 3 | 0 |
| Richard Smehlik | D | 0.03 | 0.41 | 0.43 | 3.97 | 60 | 10 | 3 | 3 | 1 |
| Grant Ledyard | D | 0.01 | 0.15 | 0.16 | 1.41 | 46 | 9 | 3 | 1 | 0 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Grant Fuhr | 46,910 | 69.6 | 5 | 5 |
| Dominik Hasek | 252 | 67.9 | 3 | 2 |

## 4. Montreal (MTL)

**Overall: Good. Best for: Both alike.** Strength +2.5 ± 1.2 now (4th of 22), +2.9 ± 0.9 over all years (4th).

**Elo adjustment:** +32 ± 11 points (4th of 22). Against an even coach on the average team, on neutral ice, that's a 55% win chance. With one fixed strength per coach instead of Elo, it's +26.

Used in 87 of 97 leagues (22 of them a season's top league), by 69 coaches, 3,859 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +4.7 ± 1.8 | +1.5 ± 1.4 | +3.1 ± 2.3 |
| By league strength | +2.9 ± 1.7 | +2.9 ± 1.7 | +0.0 ± 2.6 |
| Top league against others | +3.1 ± 2.0 | +2.9 ± 1.1 | +0.3 ± 2.4 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 2,016-1,837-6 | 52.3% | 48.3% | +4.0 ± 0.8 |
| Regular season | 1,724-1,551-6 | 52.6% | 48.9% | +3.7 ± 0.9 |
| Playoffs | 292-286 | 50.5% | 44.6% | +5.9 ± 2.1 |
| Home | 1,033-896-1 | 53.6% | 49.6% | +4.0 ± 1.1 |
| Away | 983-941-5 | 51.1% | 47.0% | +4.1 ± 1.1 |
| 2013-2019 | 547-457-3 | 54.5% | 49.2% | +5.3 ± 1.6 |
| 2020-2022 | 600-506-1 | 54.2% | 48.9% | +5.3 ± 1.5 |
| 2023-2026 | 869-874-2 | 49.9% | 47.4% | +2.5 ± 1.2 |
| High coach | 643-416-1 | 60.7% | 56.4% | +4.4 ± 1.5 |
| Mid coach | 637-608-2 | 51.2% | 46.3% | +4.8 ± 1.4 |
| Low coach | 736-813-3 | 47.5% | 44.3% | +3.2 ± 1.3 |
| Top league | 502-473-1 | 51.5% | 47.7% | +3.8 ± 1.6 |
| Other leagues | 1,514-1,364-5 | 52.6% | 48.5% | +4.1 ± 0.9 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.41 | 21st | | One-timer goals | 1.23 | 16th |
| Goals against | 3.33 | 1st | | Breakaway goals | 0.21 | 20th |
| Shots for | 11.6 | 15th | | Checks | 24.9 | 15th |
| Shots against | 12.0 | 8th | | Penalty minutes | 3.3 | 15th |
| Shooting % | 29.4 | 21st | | Faceoffs won % | 50.3 | 9th |
| Save % | 72.2 | 1st | | Attack zone time, seconds | 325 | 5th |
| Power play % | 36.9 | 19th | | Pass completion % | 61.4 | 15th |
| Penalty kill % | 65.8 | 1st | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 68.2 (9th) | 7.0 (22nd) | 3.8 (3rd) | 3.8 (10th) | 3.0 (17th) | 3.0 (7th) | 2.8 (14th) | 6.0 (2nd) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Denis Savard | F | 0.89 | 0.75 | 1.64 | 4.27 | 75 | 5 | 4 | 3 | 3 |
| Stephan Lebeau | F | 0.94 | 0.56 | 1.49 | 3.90 | 74 | 5 | 4 | 3 | 5 |
| Vincent Damphousse | F | 0.53 | 0.51 | 1.04 | 2.18 | 74 | 6 | 4 | 3 | 3 |
| Kirk Muller | F | 0.61 | 0.32 | 0.93 | 2.14 | 80 | 9 | 4 | 4 | 4 |
| Matt Schneider | D | 0.08 | 0.37 | 0.45 | 3.25 | 66 | 7 | 4 | 3 | 2 |
| Eric Desjardins | D | 0.06 | 0.32 | 0.37 | 3.71 | 68 | 9 | 3 | 3 | 2 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Patrick Roy | 45,906 | 72.3 | 6 | 6 |
| Andre Racicot | 110 | 60.9 | 2 | 3 |

## 5. Boston (BOS)

**Overall: Average. Best for: High-level (likely).** Strength +1.4 ± 1.9 now (5th of 22), +1.0 ± 1.2 over all years (5th).

**Elo adjustment:** +6 ± 13 points (6th of 22). Against an even coach on the average team, on neutral ice, that's a 51% win chance. With one fixed strength per coach instead of Elo, it's +5.

Used in 88 of 97 leagues (23 of them a season's top league), by 66 coaches, 3,812 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +4.6 ± 2.2 | −3.0 ± 2.8 | +7.7 ± 3.5 |
| By league strength | +2.4 ± 2.0 | −3.0 ± 2.2 | +5.4 ± 2.7 |
| Top league against others | +3.4 ± 2.3 | +0.1 ± 1.3 | +3.3 ± 2.5 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,969-1,841-2 | 51.7% | 50.8% | +0.9 ± 0.8 |
| Regular season | 1,669-1,553-2 | 51.8% | 51.2% | +0.6 ± 0.9 |
| Playoffs | 300-288 | 51.0% | 48.5% | +2.5 ± 2.1 |
| Home | 1,036-876-2 | 54.2% | 52.1% | +2.1 ± 1.1 |
| Away | 933-965 | 49.2% | 49.5% | −0.4 ± 1.1 |
| 2013-2019 | 591-491 | 54.6% | 51.8% | +2.9 ± 1.5 |
| 2020-2022 | 487-543-1 | 47.3% | 48.3% | −1.0 ± 1.6 |
| 2023-2026 | 891-807-1 | 52.5% | 51.7% | +0.8 ± 1.2 |
| High coach | 688-433 | 61.4% | 58.6% | +2.8 ± 1.5 |
| Mid coach | 850-846-1 | 50.1% | 49.5% | +0.6 ± 1.2 |
| Low coach | 431-562-1 | 43.4% | 44.1% | −0.7 ± 1.6 |
| Top league | 457-482 | 48.7% | 46.0% | +2.6 ± 1.6 |
| Other leagues | 1,512-1,359-2 | 52.7% | 52.4% | +0.3 ± 0.9 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.78 | 11th | | One-timer goals | 1.31 | 11th |
| Goals against | 3.65 | 5th | | Breakaway goals | 0.26 | 15th |
| Shots for | 12.2 | 7th | | Checks | 29.1 | 2nd |
| Shots against | 11.6 | 4th | | Penalty minutes | 3.2 | 13th |
| Shooting % | 31.1 | 15th | | Faceoffs won % | 49.2 | 21st |
| Save % | 68.5 | 7th | | Attack zone time, seconds | 324 | 7th |
| Power play % | 40.1 | 7th | | Pass completion % | 62.1 | 10th |
| Penalty kill % | 61.7 | 7th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 73.7 (1st) | 7.1 (16th) | 3.8 (1st) | 4.2 (2nd) | 3.7 (1st) | 2.9 (10th) | 3.3 (3rd) | 3.0 (16th) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Adam Oates | F | 1.03 | 0.89 | 1.93 | 3.89 | 93 | 7 | 4 | 3 | 4 |
| Joe Juneau | F | 0.97 | 0.74 | 1.71 | 3.91 | 72 | 5 | 4 | 4 | 3 |
| Cam Neely | F | 0.80 | 0.47 | 1.27 | 2.83 | 86 | 10 | 4 | 4 | 5 |
| Ray Bourque | D | 0.34 | 0.52 | 0.86 | 8.58 | 99 | 10 | 4 | 5 | 5 |
| Don Sweeney | D | 0.19 | 0.61 | 0.80 | 6.27 | 71 | 4 | 4 | 4 | 1 |
| Ted Donato | F | 0.26 | 0.28 | 0.54 | 1.65 | 65 | 4 | 4 | 3 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Andy Moog | 40,674 | 68.8 | 4 | 4 |
| John Blue | 3,262 | 68.4 | 3 | 3 |

## 6. Vancouver (VAN)

**Overall: Average. Best for: High-level (leaning).** Strength −0.5 ± 1.3 now (6th of 22), −0.7 ± 1.2 over all years (7th).

**Elo adjustment:** +6 ± 10 points (5th of 22). Against an even coach on the average team, on neutral ice, that's a 51% win chance. With one fixed strength per coach instead of Elo, it's −6.

Used in 89 of 97 leagues (23 of them a season's top league), by 69 coaches, 3,879 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +1.2 ± 1.8 | −2.2 ± 2.2 | +3.4 ± 2.7 |
| By league strength | +0.9 ± 1.9 | −2.2 ± 1.9 | +3.1 ± 2.6 |
| Top league against others | −0.3 ± 2.0 | −0.9 ± 1.4 | +0.6 ± 2.4 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,832-2,043-4 | 47.3% | 47.7% | −0.4 ± 0.8 |
| Regular season | 1,563-1,783-4 | 46.7% | 47.8% | −1.0 ± 0.9 |
| Playoffs | 269-260 | 50.9% | 47.1% | +3.7 ± 2.2 |
| Home | 942-995-2 | 48.6% | 49.1% | −0.5 ± 1.1 |
| Away | 890-1,048-2 | 45.9% | 46.2% | −0.3 ± 1.1 |
| 2013-2019 | 419-552-2 | 43.2% | 45.3% | −2.1 ± 1.6 |
| 2020-2022 | 514-638-1 | 44.6% | 45.0% | −0.4 ± 1.5 |
| 2023-2026 | 899-853-1 | 51.3% | 50.7% | +0.6 ± 1.2 |
| High coach | 615-464-1 | 57.0% | 56.5% | +0.5 ± 1.5 |
| Mid coach | 589-643-1 | 47.8% | 48.2% | −0.4 ± 1.4 |
| Low coach | 628-936-2 | 40.2% | 41.1% | −1.0 ± 1.3 |
| Top league | 463-501-1 | 48.0% | 48.3% | −0.2 ± 1.6 |
| Other leagues | 1,369-1,542-3 | 47.0% | 47.5% | −0.4 ± 0.9 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.73 | 13th | | One-timer goals | 1.09 | 21st |
| Goals against | 3.90 | 14th | | Breakaway goals | 0.36 | 2nd |
| Shots for | 12.3 | 5th | | Checks | 24.9 | 16th |
| Shots against | 12.1 | 14th | | Penalty minutes | 3.1 | 5th |
| Shooting % | 30.4 | 20th | | Faceoffs won % | 50.5 | 5th |
| Save % | 67.8 | 12th | | Attack zone time, seconds | 322 | 10th |
| Power play % | 37.7 | 16th | | Pass completion % | 61.1 | 20th |
| Penalty kill % | 59.2 | 16th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 67.8 (12th) | 7.2 (15th) | 3.6 (10th) | 3.6 (13th) | 2.9 (20th) | 3.5 (1st) | 2.5 (20th) | 4.0 (14th) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pavel Bure | F | 1.82 | 0.62 | 2.43 | 5.46 | 90 | 5 | 6 | 4 | 4 |
| Cliff Ronning | F | 0.76 | 0.79 | 1.55 | 3.85 | 76 | 5 | 5 | 2 | 3 |
| Geoff Courtnall | F | 0.62 | 0.57 | 1.19 | 2.15 | 73 | 7 | 5 | 3 | 3 |
| Doug Lidster | D | 0.06 | 0.63 | 0.69 | 5.63 | 60 | 9 | 3 | 3 | 1 |
| Jyrki Lumme | D | 0.07 | 0.60 | 0.67 | 4.72 | 64 | 7 | 3 | 2 | 1 |
| Trevor Linden | F | 0.32 | 0.25 | 0.56 | 1.03 | 78 | 9 | 4 | 4 | 4 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Kirk McLean | 46,639 | 67.9 | 4 | 4 |
| Kay Whitmore | 139 | 61.9 | 2 | 2 |

## 7. Dallas (DAL)

**Overall: Average. Best for: Both alike.** Strength −0.8 ± 1.6 now (7th of 22), −1.2 ± 1.3 over all years (8th).

**Elo adjustment:** −34 ± 11 points (12th of 22). Against an even coach on the average team, on neutral ice, that's a 45% win chance. With one fixed strength per coach instead of Elo, it's −10.

Used in 61 of 97 leagues (19 of them a season's top league), by 46 coaches, 2,675 games, most recently 2026-11-01.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +0.9 ± 2.0 | −1.5 ± 3.7 | +2.4 ± 4.3 |
| By league strength | +0.2 ± 1.8 | −2.7 ± 3.4 | +2.9 ± 4.0 |
| Top league against others | +0.7 ± 2.0 | −2.2 ± 1.6 | +3.0 ± 2.5 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,397-1,274-4 | 52.3% | 53.7% | −1.4 ± 1.0 |
| Regular season | 1,194-1,091-4 | 52.3% | 53.8% | −1.6 ± 1.0 |
| Playoffs | 203-183 | 52.6% | 52.8% | −0.3 ± 2.5 |
| Home | 701-642-2 | 52.2% | 55.0% | −2.8 ± 1.4 |
| Away | 696-632-2 | 52.4% | 52.4% | +0.0 ± 1.4 |
| 2013-2019 | 446-388-1 | 53.5% | 52.7% | +0.8 ± 1.7 |
| 2020-2022 | 387-390-1 | 49.8% | 53.5% | −3.7 ± 1.8 |
| 2023-2026 | 564-496-2 | 53.2% | 54.6% | −1.4 ± 1.5 |
| High coach | 717-456-2 | 61.1% | 61.0% | +0.1 ± 1.5 |
| Mid coach | 408-399-1 | 50.6% | 54.5% | −3.9 ± 1.8 |
| Low coach | 272-419-1 | 39.4% | 40.3% | −0.9 ± 1.9 |
| Top league | 487-394-2 | 55.3% | 55.5% | −0.2 ± 1.7 |
| Other leagues | 910-880-2 | 50.8% | 52.8% | −2.0 ± 1.2 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.90 | 6th | | One-timer goals | 1.05 | 22nd |
| Goals against | 3.76 | 7th | | Breakaway goals | 0.38 | 1st |
| Shots for | 11.8 | 11th | | Checks | 24.5 | 18th |
| Shots against | 12.0 | 10th | | Penalty minutes | 3.1 | 3rd |
| Shooting % | 33.0 | 8th | | Faceoffs won % | 50.1 | 12th |
| Save % | 68.7 | 6th | | Attack zone time, seconds | 319 | 13th |
| Power play % | 39.6 | 9th | | Pass completion % | 60.8 | 21st |
| Penalty kill % | 61.9 | 6th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 64.7 (16th) | 7.0 (20th) | 3.8 (5th) | 3.8 (9th) | 3.3 (9th) | 2.6 (19th) | 2.7 (15th) | 4.0 (4th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mike Modano | F | 1.67 | 0.66 | 2.33 | 4.50 | 82 | 7 | 5 | 5 | 2 |
| Russ Courtnall | F | 1.24 | 0.69 | 1.93 | 3.65 | 73 | 6 | 6 | 4 | 3 |
| Neal Broten | F | 0.55 | 0.75 | 1.30 | 4.26 | 69 | 4 | 4 | 3 | 2 |
| Tommy Sjodin | D | 0.08 | 0.68 | 0.75 | 4.04 | 57 | 6 | 3 | 4 | 1 |
| Mark Tinordi | D | 0.05 | 0.40 | 0.45 | 3.68 | 65 | 9 | 3 | 4 | 3 |
| Dave Gagner | F | 0.23 | 0.19 | 0.42 | 0.95 | 75 | 6 | 4 | 3 | 4 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Jon Casey | 31,908 | 69.0 | 4 | 3 |
| Darcy Wakaluk | 97 | 44.3 | 2 | 3 |

## 8. Winnipeg (WPG)

**Overall: Average. Best for: Both alike.** Strength −1.0 ± 1.4 now (8th of 22), +0.1 ± 0.9 over all years (6th).

**Elo adjustment:** −8 ± 11 points (7th of 22). Against an even coach on the average team, on neutral ice, that's a 49% win chance. With one fixed strength per coach instead of Elo, it's −0.

Used in 83 of 97 leagues (25 of them a season's top league), by 60 coaches, 3,541 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +1.3 ± 1.5 | +1.5 ± 2.4 | −0.3 ± 2.8 |
| By league strength | +0.4 ± 1.5 | +2.5 ± 2.1 | −2.1 ± 2.5 |
| Top league against others | +0.7 ± 1.6 | −0.1 ± 1.1 | +0.8 ± 1.9 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,806-1,734-1 | 51.0% | 50.9% | +0.1 ± 0.8 |
| Regular season | 1,591-1,477-1 | 51.9% | 51.1% | +0.8 ± 0.9 |
| Playoffs | 215-257 | 45.6% | 50.0% | −4.4 ± 2.3 |
| Home | 919-844 | 52.1% | 52.2% | −0.1 ± 1.2 |
| Away | 887-890-1 | 49.9% | 49.6% | +0.3 ± 1.2 |
| 2013-2019 | 560-441-1 | 55.9% | 54.4% | +1.5 ± 1.6 |
| 2020-2022 | 538-502 | 51.7% | 51.8% | −0.1 ± 1.6 |
| 2023-2026 | 708-791 | 47.2% | 47.9% | −0.7 ± 1.3 |
| High coach | 720-555-1 | 56.5% | 56.2% | +0.2 ± 1.4 |
| Mid coach | 651-678 | 49.0% | 50.2% | −1.2 ± 1.4 |
| Low coach | 435-501 | 46.5% | 44.6% | +1.8 ± 1.6 |
| Top league | 518-525-1 | 49.7% | 49.5% | +0.1 ± 1.5 |
| Other leagues | 1,288-1,209 | 51.6% | 51.5% | +0.1 ± 1.0 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.01 | 4th | | One-timer goals | 1.33 | 9th |
| Goals against | 3.92 | 15th | | Breakaway goals | 0.31 | 6th |
| Shots for | 12.4 | 4th | | Checks | 22.9 | 22nd |
| Shots against | 12.1 | 12th | | Penalty minutes | 3.1 | 7th |
| Shooting % | 32.4 | 10th | | Faceoffs won % | 50.9 | 2nd |
| Save % | 67.5 | 13th | | Attack zone time, seconds | 325 | 6th |
| Power play % | 41.8 | 3rd | | Pass completion % | 61.3 | 18th |
| Penalty kill % | 59.8 | 14th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 67.9 (11th) | 7.0 (23rd) | 3.3 (16th) | 3.8 (7th) | 3.2 (15th) | 3.1 (5th) | 2.9 (10th) | 4.0 (15th) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Teemu Selanne | F | 1.86 | 0.66 | 2.52 | 4.91 | 90 | 6 | 6 | 4 | 5 |
| Evgeny Davydov | F | 0.79 | 0.72 | 1.50 | 2.88 | 64 | 6 | 4 | 4 | 4 |
| Alexei Zhamnov | F | 0.54 | 0.67 | 1.21 | 2.60 | 78 | 7 | 3 | 3 | 4 |
| Phil Housley | D | 0.41 | 0.69 | 1.09 | 4.74 | 84 | 6 | 5 | 3 | 2 |
| Teppo Numminen | D | 0.08 | 0.61 | 0.70 | 4.37 | 68 | 7 | 3 | 3 | 2 |
| Luciano Borsato | F | 0.17 | 0.22 | 0.39 | 1.30 | 61 | 4 | 3 | 2 | 4 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Bob Essensa | 42,378 | 67.7 | 4 | 4 |
| Jim Hrivnak | 181 | 60.2 | 2 | 2 |

## 9. Hartford (HFD)

**Overall: Poor. Best for: Unclear.** Strength −1.8 ± 6.2 now (9th of 22), −6.5 ± 4.8 over all years (15th).

**Elo adjustment:** −50 ± 16 points (15th of 22). Against an even coach on the average team, on neutral ice, that's a 43% win chance. With one fixed strength per coach instead of Elo, it's −41.

Used in 10 of 97 leagues (4 of them a season's top league), by 9 coaches, 452 games, most recently 2026-05-22.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −12.5 ± 5.4 | too few | too few |
| By league strength | −13.3 ± 7.6 | −3.4 ± 3.7* | −10.0 ± 8.3 |
| Top league against others | −13.0 ± 7.4 | −1.7 ± 5.2 | −11.3 ± 8.6 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 262-190 | 58.0% | 66.3% | −8.3 ± 2.4 |
| Regular season | 210-160 | 56.8% | 67.2% | −10.4 ± 2.6 |
| Playoffs | 52-30 | 63.4% | 62.3% | +1.1 ± 5.5 |
| Home | 129-94 | 57.8% | 68.0% | −10.2 ± 3.3 |
| Away | 133-96 | 58.1% | 64.6% | −6.5 ± 3.3 |
| 2013-2019 | 90-69 | 56.6% | 69.2% | −12.6 ± 4.0 |
| 2020-2022 | 64-40 | 61.5% | 71.6% | −10.1 ± 4.9 |
| 2023-2026 | 108-81 | 57.1% | 60.9% | −3.7 ± 3.6 |
| High coach | 137-104 | 56.8% | 71.6% | −14.7 ± 3.2 |
| Mid coach | 125-86 | 59.2% | 60.3% | −1.0 ± 3.4 |
| Top league | 98-82 | 54.4% | 69.2% | −14.7 ± 3.7 |
| Other leagues | 164-108 | 60.3% | 64.4% | −4.1 ± 3.0 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.28 | 1st | | One-timer goals | 1.51 | 3rd |
| Goals against | 3.70 | 6th | | Breakaway goals | 0.29 | 10th |
| Shots for | 12.2 | 6th | | Checks | 26.4 | 9th |
| Shots against | 11.1 | 1st | | Penalty minutes | 3.3 | 18th |
| Shooting % | 35.1 | 1st | | Faceoffs won % | 50.3 | 8th |
| Save % | 66.6 | 18th | | Attack zone time, seconds | 329 | 1st |
| Power play % | 41.6 | 4th | | Pass completion % | 64.9 | 1st |
| Penalty kill % | 64.6 | 2nd | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 64.0 (19th) | 7.4 (11th) | 3.3 (14th) | 3.5 (15th) | 3.2 (13th) | 2.8 (16th) | 2.8 (13th) | 4.0 (7th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Geoff Sanderson | F | 1.43 | 1.04 | 2.48 | 4.31 | 73 | 6 | 4 | 4 | 4 |
| Pat Verbeek | F | 1.59 | 0.81 | 2.39 | 4.20 | 74 | 7 | 4 | 4 | 4 |
| Terry Yake | F | 0.59 | 0.65 | 1.24 | 2.36 | 66 | 6 | 3 | 3 | 4 |
| Zarley Zalapski | D | 0.18 | 0.71 | 0.89 | 7.27 | 80 | 10 | 4 | 4 | 2 |
| Eric Weinrich | D | 0.05 | 0.44 | 0.49 | 3.60 | 64 | 10 | 4 | 3 | 2 |
| Andrew Cassels | F | 0.16 | 0.30 | 0.46 | 0.65 | 65 | 7 | 3 | 2 | 4 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Sean Burke | 4,954 | 66.8 | 4 | 4 |
| Mario Gosselin | 30 | 53.3 | 2 | 2 |

## 10. Calgary (CGY)

**Overall: Poor. Best for: Both alike.** Strength −1.9 ± 1.6 now (10th of 22), −4.8 ± 1.3 over all years (12th).

**Elo adjustment:** −32 ± 12 points (11th of 22). Against an even coach on the average team, on neutral ice, that's a 45% win chance. With one fixed strength per coach instead of Elo, it's −40.

Used in 76 of 97 leagues (22 of them a season's top league), by 65 coaches, 3,025 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −6.7 ± 1.6 | −5.3 ± 3.0 | −1.4 ± 3.5 |
| By league strength | −4.5 ± 1.7 | −4.0 ± 2.5 | −0.5 ± 3.1 |
| Top league against others | −5.3 ± 1.9 | −4.5 ± 1.8 | −0.8 ± 2.6 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,396-1,628-1 | 46.2% | 51.4% | −5.3 ± 0.9 |
| Regular season | 1,244-1,443-1 | 46.3% | 51.2% | −4.9 ± 1.0 |
| Playoffs | 152-185 | 45.1% | 53.1% | −8.0 ± 2.7 |
| Home | 694-814 | 46.0% | 52.6% | −6.6 ± 1.3 |
| Away | 702-814-1 | 46.3% | 50.2% | −3.9 ± 1.3 |
| 2013-2019 | 356-530 | 40.2% | 48.7% | −8.5 ± 1.7 |
| 2020-2022 | 395-447 | 46.9% | 49.7% | −2.8 ± 1.7 |
| 2023-2026 | 645-651-1 | 49.8% | 54.4% | −4.6 ± 1.4 |
| High coach | 559-512 | 52.2% | 60.3% | −8.1 ± 1.5 |
| Mid coach | 414-458 | 47.5% | 48.7% | −1.2 ± 1.7 |
| Low coach | 423-658-1 | 39.1% | 44.8% | −5.7 ± 1.5 |
| Top league | 383-465 | 45.2% | 51.2% | −6.1 ± 1.7 |
| Other leagues | 1,013-1,163-1 | 46.6% | 51.5% | −4.9 ± 1.1 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.84 | 8th | | One-timer goals | 1.23 | 15th |
| Goals against | 4.11 | 18th | | Breakaway goals | 0.28 | 12th |
| Shots for | 12.5 | 3rd | | Checks | 27.7 | 6th |
| Shots against | 11.6 | 3rd | | Penalty minutes | 3.4 | 21st |
| Shooting % | 30.7 | 18th | | Faceoffs won % | 50.2 | 11th |
| Save % | 64.5 | 20th | | Attack zone time, seconds | 328 | 3rd |
| Power play % | 38.9 | 11th | | Pass completion % | 61.4 | 16th |
| Penalty kill % | 57.9 | 20th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 71.8 (2nd) | 7.6 (9th) | 3.7 (7th) | 4.1 (4th) | 3.5 (4th) | 3.0 (6th) | 3.2 (5th) | 3.0 (17th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Theoren Fleury | F | 1.33 | 0.76 | 2.09 | 7.50 | 86 | 3 | 5 | 4 | 3 |
| Gary Roberts | F | 1.02 | 0.62 | 1.64 | 3.72 | 85 | 7 | 4 | 4 | 5 |
| Robert Reichel | F | 0.55 | 0.43 | 0.98 | 2.11 | 73 | 6 | 4 | 4 | 4 |
| Gary Suter | D | 0.20 | 0.63 | 0.82 | 5.81 | 81 | 7 | 4 | 4 | 2 |
| Sergei Makarov | F | 0.35 | 0.45 | 0.79 | 1.51 | 73 | 6 | 4 | 2 | 4 |
| Al MacInnis | D | 0.17 | 0.57 | 0.74 | 4.83 | 73 | 8 | 4 | 6 | 1 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Mike Vernon | 34,587 | 64.7 | 3 | 4 |
| Jeff Reese | 273 | 63.4 | 2 | 2 |

## 11. Toronto (TOR)

**Overall: Poor. Best for: Both alike.** Strength −2.7 ± 2.4 now (11th of 22), −2.6 ± 1.5 over all years (10th).

**Elo adjustment:** −40 ± 19 points (13th of 22). Against an even coach on the average team, on neutral ice, that's a 44% win chance. With one fixed strength per coach instead of Elo, it's −23.

Used in 38 of 97 leagues (12 of them a season's top league), by 35 coaches, 1,574 games, most recently 2026-11-01.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −3.3 ± 2.4 | −7.7 ± 2.9 | +4.4 ± 3.8 |
| By league strength | −4.4 ± 2.5 | +0.3 ± 4.1 | −4.7 ± 4.7 |
| Top league against others | −3.6 ± 2.6 | −2.0 ± 1.9 | −1.6 ± 3.2 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 693-879-2 | 44.1% | 46.6% | −2.6 ± 1.3 |
| Regular season | 624-781-2 | 44.4% | 46.5% | −2.1 ± 1.3 |
| Playoffs | 69-98 | 41.3% | 48.0% | −6.6 ± 3.9 |
| Home | 372-416 | 47.2% | 48.1% | −0.9 ± 1.8 |
| Away | 321-463-2 | 40.9% | 45.2% | −4.3 ± 1.8 |
| 2013-2019 | 293-456-1 | 39.1% | 42.7% | −3.6 ± 1.8 |
| 2020-2022 | 202-235-1 | 46.2% | 47.3% | −1.1 ± 2.4 |
| 2023-2026 | 198-188 | 51.3% | 53.5% | −2.2 ± 2.5 |
| High coach | 281-248-1 | 53.1% | 57.9% | −4.8 ± 2.2 |
| Mid coach | 290-236-1 | 55.1% | 51.9% | +3.2 ± 2.2 |
| Low coach | 122-395 | 23.6% | 29.8% | −6.2 ± 2.2 |
| Top league | 229-262-1 | 46.6% | 50.1% | −3.4 ± 2.3 |
| Other leagues | 464-617-1 | 42.9% | 45.1% | −2.2 ± 1.5 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.48 | 20th | | One-timer goals | 1.23 | 17th |
| Goals against | 4.01 | 17th | | Breakaway goals | 0.24 | 16th |
| Shots for | 11.3 | 19th | | Checks | 28.1 | 4th |
| Shots against | 12.3 | 19th | | Penalty minutes | 3.5 | 22nd |
| Shooting % | 30.8 | 17th | | Faceoffs won % | 49.8 | 16th |
| Save % | 67.4 | 14th | | Attack zone time, seconds | 317 | 16th |
| Power play % | 34.8 | 22nd | | Pass completion % | 62.4 | 8th |
| Penalty kill % | 58.5 | 17th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 67.6 (13th) | 7.7 (8th) | 3.2 (18th) | 3.4 (19th) | 3.3 (11th) | 3.0 (9th) | 3.5 (2nd) | 4.0 (13th) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Doug Gilmour | F | 1.66 | 0.67 | 2.32 | 7.89 | 89 | 4 | 4 | 4 | 4 |
| Nikolai Borshevsky | F | 0.73 | 0.85 | 1.58 | 3.22 | 71 | 6 | 4 | 3 | 4 |
| Dave Ellett | D | 0.14 | 0.56 | 0.69 | 6.38 | 72 | 9 | 4 | 5 | 1 |
| Wendel Clark | F | 0.35 | 0.24 | 0.59 | 1.30 | 69 | 8 | 3 | 5 | 3 |
| Jamie Macoun | D | 0.05 | 0.40 | 0.45 | 3.52 | 60 | 8 | 3 | 4 | 1 |
| Glenn Anderson | F | 0.19 | 0.24 | 0.43 | 0.90 | 71 | 7 | 4 | 3 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Felix Potvin | 19,131 | 67.7 | 4 | 4 |
| Daren Puppa | 103 | 62.1 | 3 | 2 |

## 12. Los Angeles (LA)

**Overall: Poor. Best for: Unclear.** Strength −4.0 ± 1.5 now (12th of 22), −2.2 ± 1.4 over all years (9th).

**Elo adjustment:** −20 ± 16 points (9th of 22). Against an even coach on the average team, on neutral ice, that's a 47% win chance. With one fixed strength per coach instead of Elo, it's −21.

Used in 57 of 97 leagues (22 of them a season's top league), by 51 coaches, 2,379 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | +0.3 ± 1.5 | −2.8 ± 4.7 | +3.1 ± 5.0 |
| By league strength | −1.0 ± 1.9 | −6.8 ± 2.7 | +5.8 ± 3.2 |
| Top league against others | −1.2 ± 1.8 | −2.6 ± 2.2 | +1.4 ± 2.8 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,138-1,241 | 47.8% | 50.6% | −2.8 ± 1.0 |
| Regular season | 978-1,072 | 47.7% | 51.0% | −3.3 ± 1.1 |
| Playoffs | 160-169 | 48.6% | 47.9% | +0.7 ± 2.8 |
| Home | 582-604 | 49.1% | 52.1% | −3.0 ± 1.5 |
| Away | 556-637 | 46.6% | 49.1% | −2.5 ± 1.4 |
| 2013-2019 | 405-360 | 52.9% | 54.2% | −1.3 ± 1.8 |
| 2020-2022 | 294-370 | 44.3% | 49.0% | −4.7 ± 1.9 |
| 2023-2026 | 439-511 | 46.2% | 48.8% | −2.6 ± 1.6 |
| High coach | 558-412 | 57.5% | 59.0% | −1.5 ± 1.6 |
| Mid coach | 432-534 | 44.7% | 48.3% | −3.6 ± 1.6 |
| Low coach | 148-295 | 33.4% | 37.2% | −3.8 ± 2.4 |
| Top league | 463-517 | 47.2% | 48.9% | −1.7 ± 1.6 |
| Other leagues | 675-724 | 48.2% | 51.8% | −3.5 ± 1.3 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 4.04 | 3rd | | One-timer goals | 1.59 | 2nd |
| Goals against | 4.20 | 20th | | Breakaway goals | 0.29 | 9th |
| Shots for | 11.8 | 12th | | Checks | 26.8 | 8th |
| Shots against | 11.7 | 5th | | Penalty minutes | 3.1 | 4th |
| Shooting % | 34.2 | 3rd | | Faceoffs won % | 50.3 | 6th |
| Save % | 64.1 | 21st | | Attack zone time, seconds | 324 | 8th |
| Power play % | 41.0 | 5th | | Pass completion % | 62.1 | 9th |
| Penalty kill % | 58.3 | 18th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 71.1 (5th) | 7.7 (7th) | 3.8 (2nd) | 3.9 (5th) | 3.2 (12th) | 3.2 (3rd) | 2.5 (19th) | 3.0 (19th) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wayne Gretzky | F | 0.87 | 1.20 | 2.08 | 5.83 | 87 | 4 | 4 | 2 | 2 |
| Tomas Sandstrom | F | 1.40 | 0.52 | 1.91 | 3.28 | 80 | 9 | 4 | 5 | 5 |
| Luc Robitaille | F | 0.99 | 0.63 | 1.61 | 3.00 | 85 | 7 | 4 | 4 | 6 |
| Alexei Zhitnik | D | 0.15 | 0.65 | 0.80 | 5.23 | 66 | 5 | 4 | 3 | 2 |
| Rob Blake | D | 0.10 | 0.68 | 0.78 | 6.10 | 72 | 11 | 4 | 4 | 1 |
| Tony Granato | F | 0.40 | 0.34 | 0.74 | 1.49 | 75 | 6 | 5 | 3 | 4 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Kelly Hrudey | 26,480 | 64.3 | 3 | 4 |
| Robb Stauber | 623 | 62.8 | 2 | 3 |

## 13. Philadelphia (PHI)

**Overall: Poor. Best for: Both alike.** Strength −5.0 ± 1.9 now (13th of 22), −4.9 ± 1.8 over all years (13th).

**Elo adjustment:** −22 ± 18 points (10th of 22). Against an even coach on the average team, on neutral ice, that's a 47% win chance. With one fixed strength per coach instead of Elo, it's −33.

Used in 25 of 97 leagues (9 of them a season's top league), by 25 coaches, 1,045 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −4.1 ± 1.9 | −6.6 ± 3.2 | +2.5 ± 3.8 |
| By league strength | −3.7 ± 2.3 | −7.1 ± 4.1 | +3.4 ± 4.8 |
| Top league against others | −3.5 ± 2.2 | −6.1 ± 2.5 | +2.6 ± 3.2 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 507-533-5 | 48.8% | 54.5% | −5.7 ± 1.6 |
| Regular season | 444-456-5 | 49.3% | 54.0% | −4.6 ± 1.7 |
| Playoffs | 63-77 | 45.0% | 57.9% | −12.9 ± 4.2 |
| Home | 280-240-2 | 53.8% | 55.8% | −2.0 ± 2.2 |
| Away | 227-293-3 | 43.7% | 53.1% | −9.5 ± 2.2 |
| 2013-2019 | 126-199 | 38.8% | 42.2% | −3.5 ± 2.8 |
| 2020-2022 | 152-131-1 | 53.7% | 62.0% | −8.3 ± 3.0 |
| 2023-2026 | 229-203-4 | 53.0% | 58.7% | −5.7 ± 2.4 |
| High coach | 336-212 | 61.3% | 67.5% | −6.2 ± 2.1 |
| Mid coach | 76-98 | 43.7% | 51.8% | −8.1 ± 3.8 |
| Low coach | 95-223-5 | 29.9% | 33.5% | −3.6 ± 2.8 |
| Top league | 227-169 | 57.3% | 63.3% | −5.9 ± 2.5 |
| Other leagues | 280-364-5 | 43.5% | 49.1% | −5.6 ± 2.0 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.66 | 18th | | One-timer goals | 1.30 | 12th |
| Goals against | 3.85 | 11th | | Breakaway goals | 0.26 | 14th |
| Shots for | 11.8 | 13th | | Checks | 24.8 | 17th |
| Shots against | 12.5 | 20th | | Penalty minutes | 3.2 | 12th |
| Shooting % | 31.1 | 16th | | Faceoffs won % | 49.5 | 19th |
| Save % | 69.3 | 5th | | Attack zone time, seconds | 324 | 9th |
| Power play % | 38.2 | 13th | | Pass completion % | 61.7 | 14th |
| Penalty kill % | 60.8 | 11th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 64.6 (18th) | 7.1 (17th) | 3.1 (21st) | 3.6 (12th) | 3.0 (18th) | 3.0 (8th) | 2.7 (16th) | 4.0 (9th) |

Hidden bonus: +2 at home, −2 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mark Recchi | F | 1.60 | 0.65 | 2.25 | 4.87 | 83 | 6 | 4 | 4 | 5 |
| Pelle Eklund | F | 0.85 | 0.83 | 1.68 | 4.29 | 75 | 5 | 4 | 3 | 3 |
| Kevin Dineen | F | 0.41 | 0.47 | 0.88 | 1.92 | 68 | 7 | 5 | 2 | 3 |
| Eric Lindros | F | 0.40 | 0.28 | 0.68 | 1.86 | 84 | 12 | 3 | 4 | 6 |
| Dimitri Yushkevich | D | 0.06 | 0.61 | 0.67 | 4.24 | 59 | 7 | 3 | 3 | 1 |
| Greg Hawgood | D | 0.05 | 0.42 | 0.47 | 2.99 | 58 | 7 | 3 | 3 | 2 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Tommy Soderstrom | 12,639 | 69.7 | 4 | 4 |
| Dominic Roussel | 316 | 63.0 | 3 | 3 |

## 14. Quebec (QUE)

**Overall: Poor. Best for: High-level (leaning).** Strength −5.1 ± 2.4 now (14th of 22), −4.6 ± 1.5 over all years (11th).

**Elo adjustment:** −43 ± 13 points (14th of 22). Against an even coach on the average team, on neutral ice, that's a 44% win chance. With one fixed strength per coach instead of Elo, it's −33.

Used in 48 of 97 leagues (10 of them a season's top league), by 41 coaches, 2,050 games, most recently 2026-11-01.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −4.3 ± 2.2 | −9.0 ± 4.4 | +4.8 ± 4.7 |
| By league strength | −2.3 ± 3.1 | −8.2 ± 2.9 | +5.9 ± 4.2 |
| Top league against others | −3.1 ± 3.1 | −5.2 ± 1.9 | +2.1 ± 3.7 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 1,034-1,014-2 | 50.5% | 55.4% | −4.9 ± 1.1 |
| Regular season | 901-862-2 | 51.1% | 55.4% | −4.3 ± 1.2 |
| Playoffs | 133-152 | 46.7% | 55.4% | −8.7 ± 3.0 |
| Home | 535-490-1 | 52.2% | 56.8% | −4.6 ± 1.6 |
| Away | 499-524-1 | 48.8% | 54.0% | −5.2 ± 1.6 |
| 2013-2019 | 334-359-1 | 48.2% | 51.6% | −3.4 ± 1.9 |
| 2020-2022 | 339-274-1 | 55.3% | 60.1% | −4.8 ± 2.0 |
| 2023-2026 | 361-381 | 48.7% | 55.0% | −6.4 ± 1.8 |
| High coach | 470-296-1 | 61.4% | 67.1% | −5.7 ± 1.8 |
| Mid coach | 352-337-1 | 51.1% | 53.6% | −2.5 ± 1.9 |
| Low coach | 212-381 | 35.8% | 42.3% | −6.6 ± 2.1 |
| Top league | 270-196-1 | 57.9% | 61.5% | −3.6 ± 2.3 |
| Other leagues | 764-818-1 | 48.3% | 53.6% | −5.3 ± 1.3 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.84 | 9th | | One-timer goals | 1.39 | 6th |
| Goals against | 3.88 | 13th | | Breakaway goals | 0.27 | 13th |
| Shots for | 11.6 | 14th | | Checks | 23.0 | 21st |
| Shots against | 12.1 | 16th | | Penalty minutes | 3.1 | 2nd |
| Shooting % | 33.0 | 9th | | Faceoffs won % | 49.9 | 13th |
| Save % | 68.1 | 11th | | Attack zone time, seconds | 314 | 18th |
| Power play % | 40.6 | 6th | | Pass completion % | 62.0 | 11th |
| Penalty kill % | 59.9 | 13th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 68.1 (10th) | 6.8 (25th) | 3.7 (8th) | 3.5 (17th) | 3.5 (6th) | 3.3 (2nd) | 2.3 (24th) | 4.0 (11th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Joe Sakic | F | 1.43 | 0.81 | 2.23 | 3.96 | 83 | 6 | 4 | 4 | 5 |
| Mats Sundin | F | 1.18 | 0.80 | 1.98 | 3.19 | 79 | 7 | 4 | 4 | 5 |
| Andrei Kovalenko | F | 0.59 | 0.67 | 1.26 | 4.08 | 69 | 3 | 4 | 3 | 4 |
| Steve Duchesne | D | 0.12 | 0.51 | 0.62 | 3.69 | 72 | 8 | 4 | 4 | 2 |
| Alexei Gusarov | D | 0.06 | 0.36 | 0.42 | 2.51 | 61 | 6 | 3 | 3 | 3 |
| Valeri Kamensky | F | 0.20 | 0.16 | 0.36 | 0.62 | 73 | 8 | 4 | 5 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Ron Hextall | 24,695 | 68.2 | 4 | 4 |
| Stephane Fiset | 123 | 65.0 | 3 | 2 |

## 15. New Jersey (NJ)

**Overall: Poor. Best for: Both alike.** Strength −5.5 ± 4.7 now (15th of 22), −5.6 ± 2.5 over all years (14th).

**Elo adjustment:** −89 ± 33 points (21st of 22). Against an even coach on the average team, on neutral ice, that's a 37% win chance. With one fixed strength per coach instead of Elo, it's −30.

Used in 7 of 97 leagues (3 of them a season's top league), by 6 coaches, 310 games, most recently 2026-11-01.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −6.1 ± 2.8 | −3.6 ± 9.4* | −2.5 ± 9.9 |
| By league strength | −6.8 ± 2.3 | −3.9 ± 11.2* | −2.9 ± 11.6 |
| Top league against others | −6.7 ± 2.4 | −5.6 ± 6.7 | −1.1 ± 7.2 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 144-165-1 | 46.6% | 53.1% | −6.5 ± 2.8 |
| Regular season | 122-157-1 | 43.7% | 50.7% | −7.0 ± 3.0 |
| Playoffs | 22-8 | 73.3% | 75.6% | −2.2 ± 9.1 |
| Home | 77-78-1 | 49.7% | 54.5% | −4.8 ± 4.0 |
| Away | 67-87 | 43.5% | 51.8% | −8.3 ± 4.0 |
| 2013-2019 | 68-30 | 69.4% | 75.5% | −6.2 ± 5.1 |
| 2020-2022 | 18-61-1 | 22.8% | 28.0% | −5.2 ± 5.6 |
| 2023-2026 | 58-74 | 43.9% | 51.6% | −7.6 ± 4.4 |
| High coach | 111-39 | 74.0% | 79.6% | −5.6 ± 4.1 |
| Mid coach | 14-26 | 35.0% | 43.9% | −8.9 ± 7.9 |
| Low coach | 19-100-1 | 16.0% | 22.9% | −6.9 ± 4.6 |
| Top league | 111-39 | 74.0% | 79.6% | −5.6 ± 4.1 |
| Other leagues | 33-126-1 | 20.8% | 28.2% | −7.4 ± 4.0 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.75 | 12th | | One-timer goals | 1.38 | 7th |
| Goals against | 3.65 | 4th | | Breakaway goals | 0.24 | 18th |
| Shots for | 11.2 | 20th | | Checks | 30.2 | 1st |
| Shots against | 12.0 | 9th | | Penalty minutes | 3.3 | 17th |
| Shooting % | 33.5 | 5th | | Faceoffs won % | 50.7 | 4th |
| Save % | 69.6 | 3rd | | Attack zone time, seconds | 314 | 17th |
| Power play % | 39.0 | 10th | | Pass completion % | 64.7 | 2nd |
| Penalty kill % | 63.6 | 4th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 66.5 (15th) | 8.8 (1st) | 3.3 (15th) | 3.7 (11th) | 3.5 (5th) | 2.5 (22nd) | 2.9 (8th) | 4.0 (8th) |

Hidden bonus: +1 at home, −2 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Stephane Richer | F | 1.39 | 0.68 | 2.07 | 4.12 | 72 | 9 | 4 | 5 | 3 |
| Alexnder Semak | F | 1.06 | 0.95 | 2.01 | 4.72 | 73 | 6 | 3 | 3 | 4 |
| Valeri Zelepukin | F | 0.73 | 0.79 | 1.52 | 2.54 | 68 | 6 | 4 | 3 | 3 |
| Scott Stevens | D | 0.13 | 0.59 | 0.72 | 8.85 | 76 | 11 | 4 | 4 | 2 |
| Claude Lemieux | F | 0.25 | 0.27 | 0.51 | 1.38 | 68 | 11 | 4 | 4 | 2 |
| Alexei Kasatonov | D | 0.04 | 0.38 | 0.42 | 3.95 | 62 | 11 | 3 | 4 | 1 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Chris Terreri | 3,657 | 69.7 | 4 | 3 |
| Craig Billington | 38 | 63.2 | 3 | 1 |

## 16. NY Islanders (NYI)

**Overall: Poor. Best for: Unclear (few games).** Strength −5.9 ± 3.0 now (16th of 22), −10.7 ± 5.7 over all years (20th).

**Elo adjustment:** −59* ± 14 points (16th of 22). Against an even coach on the average team, on neutral ice, that's a 42% win chance. With one fixed strength per coach instead of Elo, it's −50.

Used in 5 of 97 leagues (2 of them a season's top league), by 6 coaches, 210 games, most recently 2026-05-09.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −15.4 ± 9.1* | −5.6 ± 9.8* | −9.8 ± 13.8 |
| By league strength | −4.6 ± 5.5* | −4.6 ± 4.6* | −0.1 ± 7.4 |
| Top league against others | −4.5 ± 5.3* | −15.1 ± 7.5* | +10.7 ± 9.4 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 95-115 | 45.2% | 56.6% | −11.3 ± 3.5 |
| Regular season | 84-98 | 46.2% | 56.4% | −10.2 ± 3.7 |
| Playoffs | 11-17 | 39.3% | 57.8% | −18.5 ± 9.4 |
| Home | 47-56 | 45.6% | 56.8% | −11.1 ± 4.9 |
| Away | 48-59 | 44.9% | 56.3% | −11.5 ± 4.8 |
| 2013-2019 | 43-41 | 51.2% | 70.1% | −18.9 ± 5.5 |
| 2023-2026 | 52-74 | 41.3% | 47.5% | −6.3 ± 4.5 |
| High coach | 53-46 | 53.5% | 72.2% | −18.7 ± 5.0 |
| Mid coach | 36-35 | 50.7% | 54.6% | −3.9 ± 5.9 |
| Low coach | 6-34 | 15.0% | 21.1% | −6.1 ± 7.9 |
| Top league | 41-39 | 51.2% | 57.3% | −6.1 ± 5.6 |
| Other leagues | 54-76 | 41.5% | 56.1% | −14.5 ± 4.4 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.96 | 5th | | One-timer goals | 1.29 | 13th |
| Goals against | 4.39 | 21st | | Breakaway goals | 0.24 | 17th |
| Shots for | 11.4 | 18th | | Checks | 23.1 | 20th |
| Shots against | 13.3 | 22nd | | Penalty minutes | 2.7 | 1st |
| Shooting % | 34.7 | 2nd | | Faceoffs won % | 53.3 | 1st |
| Save % | 66.9 | 16th | | Attack zone time, seconds | 318 | 14th |
| Power play % | 43.9 | 1st | | Pass completion % | 61.7 | 13th |
| Penalty kill % | 55.4 | 21st | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 64.6 (17th) | 7.5 (10th) | 3.2 (17th) | 3.4 (18th) | 3.2 (14th) | 2.8 (13th) | 2.4 (22nd) | 2.0 (25th) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Benoit Hogue | F | 1.31 | 0.86 | 2.17 | 3.45 | 78 | 7 | 5 | 3 | 5 |
| Pierre Turgeon | F | 1.34 | 0.65 | 1.99 | 3.31 | 82 | 9 | 4 | 4 | 5 |
| Steve Thomas | F | 0.48 | 0.55 | 1.03 | 2.46 | 72 | 6 | 4 | 3 | 3 |
| Darius Kasparitis | D | 0.14 | 0.64 | 0.78 | 5.48 | 57 | 7 | 3 | 3 | 1 |
| Marty McInnis | F | 0.26 | 0.37 | 0.63 | 1.83 | 54 | 4 | 3 | 2 | 3 |
| Tom Kurvers | D | 0.04 | 0.33 | 0.37 | 2.03 | 59 | 8 | 3 | 4 | 1 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Glenn Healy | 2,706 | 67.5 | 2 | 2 |
| Mark Fitzpatrik | 61 | 54.1 | 2 | 3 |

## 17. Edmonton (EDM)

**Overall: Poor. Best for: Low-level (leaning).** Strength −6.1 ± 4.4 now (17th of 22), −6.8 ± 2.8 over all years (16th).

**Elo adjustment:** −64 ± 23 points (18th of 22). Against an even coach on the average team, on neutral ice, that's a 41% win chance. With one fixed strength per coach instead of Elo, it's −49.

Used in 16 of 97 leagues (6 of them a season's top league), by 18 coaches, 651 games, most recently 2026-05-16.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −8.6 ± 2.4 | −0.2 ± 7.2 | −8.4 ± 7.7 |
| By league strength | −10.3 ± 3.2 | −6.8 ± 5.4 | −3.5 ± 5.8 |
| Top league against others | −10.3 ± 2.9 | −4.1 ± 4.2 | −6.2 ± 4.9 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 314-337 | 48.2% | 56.1% | −7.9 ± 2.0 |
| Regular season | 288-297 | 49.2% | 56.3% | −7.0 ± 2.1 |
| Playoffs | 26-40 | 39.4% | 55.0% | −15.6 ± 6.2 |
| Home | 156-171 | 47.7% | 57.5% | −9.8 ± 2.8 |
| Away | 158-166 | 48.8% | 54.8% | −6.1 ± 2.8 |
| 2013-2019 | 136-167 | 44.9% | 53.2% | −8.3 ± 2.9 |
| 2020-2022 | 66-61 | 52.0% | 56.2% | −4.2 ± 4.4 |
| 2023-2026 | 112-109 | 50.7% | 60.2% | −9.5 ± 3.4 |
| High coach | 194-182 | 51.6% | 61.9% | −10.3 ± 2.6 |
| Mid coach | 40-49 | 44.9% | 59.1% | −14.1 ± 5.3 |
| Low coach | 80-106 | 43.0% | 43.1% | −0.1 ± 3.7 |
| Top league | 123-141 | 46.6% | 58.3% | −11.7 ± 3.1 |
| Other leagues | 191-196 | 49.4% | 54.7% | −5.3 ± 2.5 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.70 | 17th | | One-timer goals | 1.16 | 19th |
| Goals against | 3.86 | 12th | | Breakaway goals | 0.33 | 4th |
| Shots for | 11.5 | 17th | | Checks | 26.2 | 10th |
| Shots against | 12.2 | 17th | | Penalty minutes | 3.2 | 11th |
| Shooting % | 32.1 | 11th | | Faceoffs won % | 49.8 | 14th |
| Save % | 68.2 | 9th | | Attack zone time, seconds | 313 | 19th |
| Power play % | 38.0 | 15th | | Pass completion % | 63.0 | 5th |
| Penalty kill % | 60.9 | 10th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 63.8 (20th) | 7.7 (6th) | 3.4 (13th) | 3.5 (14th) | 3.1 (16th) | 2.5 (21st) | 2.9 (7th) | 4.0 (6th) |

Hidden bonus: +1 at home, −2 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Petr Klima | F | 1.89 | 0.64 | 2.52 | 4.38 | 76 | 7 | 5 | 4 | 5 |
| Craig Simpson | F | 0.66 | 0.53 | 1.19 | 2.49 | 69 | 8 | 3 | 4 | 5 |
| Kevin Todd | F | 0.47 | 0.66 | 1.13 | 3.45 | 61 | 5 | 4 | 3 | 2 |
| Dave Manson | D | 0.18 | 0.59 | 0.76 | 6.38 | 74 | 9 | 4 | 5 | 1 |
| Igor Kravchuk | D | 0.09 | 0.56 | 0.65 | 5.03 | 66 | 9 | 3 | 3 | 2 |
| Shayne Corson | F | 0.17 | 0.21 | 0.38 | 1.02 | 71 | 9 | 4 | 3 | 2 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Bill Ranford | 7,836 | 68.5 | 4 | 4 |
| Ron Tugnutt | 43 | 51.2 | 2 | 1 |

## 18. Pittsburgh (PIT)

**Overall: Poor. Best for: Unclear.** Strength −7.9 ± 4.0 now (18th of 22), −10.0 ± 2.6 over all years (19th).

**Elo adjustment:** −70 ± 14 points (19th of 22). Against an even coach on the average team, on neutral ice, that's a 40% win chance. With one fixed strength per coach instead of Elo, it's −73.

Used in 28 of 97 leagues (4 of them a season's top league), by 31 coaches, 1,137 games, most recently 2026-10-31.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −6.0 ± 5.0 | −11.9 ± 5.2 | +6.0 ± 7.0 |
| By league strength | −11.9 ± 6.1 | −12.9 ± 4.2 | +1.0 ± 7.2 |
| Top league against others | −11.9 ± 6.3 | −9.6 ± 3.0 | −2.4 ± 6.9 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 458-674-5 | 40.5% | 51.2% | −10.7 ± 1.5 |
| Regular season | 397-619-5 | 39.1% | 50.3% | −11.2 ± 1.6 |
| Playoffs | 61-55 | 52.6% | 59.0% | −6.4 ± 4.6 |
| Home | 232-331-2 | 41.2% | 52.6% | −11.3 ± 2.1 |
| Away | 226-343-3 | 39.7% | 49.8% | −10.1 ± 2.1 |
| 2013-2019 | 202-331-1 | 37.9% | 49.0% | −11.1 ± 2.2 |
| 2020-2022 | 82-99 | 45.3% | 55.1% | −9.8 ± 3.7 |
| 2023-2026 | 174-244-4 | 41.6% | 52.2% | −10.6 ± 2.4 |
| High coach | 167-127 | 56.8% | 65.1% | −8.3 ± 2.9 |
| Mid coach | 211-263-1 | 44.5% | 57.1% | −12.6 ± 2.3 |
| Low coach | 80-284-4 | 22.0% | 32.2% | −10.3 ± 2.6 |
| Top league | 89-93-1 | 48.9% | 61.3% | −12.4 ± 3.7 |
| Other leagues | 369-581-4 | 38.8% | 49.3% | −10.4 ± 1.6 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.36 | 22nd | | One-timer goals | 1.32 | 10th |
| Goals against | 4.14 | 19th | | Breakaway goals | 0.22 | 19th |
| Shots for | 11.0 | 21st | | Checks | 25.1 | 13th |
| Shots against | 12.6 | 21st | | Penalty minutes | 3.1 | 6th |
| Shooting % | 30.6 | 19th | | Faceoffs won % | 49.5 | 18th |
| Save % | 67.2 | 15th | | Attack zone time, seconds | 310 | 21st |
| Power play % | 36.5 | 20th | | Pass completion % | 63.4 | 4th |
| Penalty kill % | 59.7 | 15th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 68.8 (7th) | 8.5 (2nd) | 3.2 (19th) | 3.5 (16th) | 3.3 (10th) | 2.8 (14th) | 3.2 (4th) | 4.0 (10th) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mario Lemieux | F | 1.66 | 0.59 | 2.25 | 4.31 | 100 | 10 | 4 | 4 | 6 |
| Jaromir Jagr | F | 0.60 | 0.71 | 1.31 | 3.29 | 80 | 10 | 4 | 3 | 3 |
| Joe Mullen | F | 0.43 | 0.53 | 0.96 | 1.76 | 73 | 6 | 3 | 3 | 5 |
| Ulf Samuelsson | D | 0.12 | 0.55 | 0.67 | 7.06 | 68 | 8 | 4 | 3 | 0 |
| Larry Murphy | D | 0.12 | 0.52 | 0.65 | 5.19 | 74 | 10 | 3 | 4 | 2 |
| Kevin Stevens | F | 0.14 | 0.20 | 0.35 | 0.94 | 77 | 11 | 4 | 3 | 4 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Tom Barrasso | 14,135 | 67.5 | 4 | 4 |
| Ken Wregget | 133 | 54.9 | 2 | 2 |

## 19. Washington (WSH)

**Overall: Poor. Best for: Unclear (few games).** Strength −8.6 ± 5.0 now (19th of 22), −7.4 ± 3.4 over all years (17th).

**Elo adjustment:** −17 ± 25 points (8th of 22). Against an even coach on the average team, on neutral ice, that's a 48% win chance. With one fixed strength per coach instead of Elo, it's −48.

Used in 8 of 97 leagues (2 of them a season's top league), by 9 coaches, 357 games, most recently 2025-05-23.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −9.5 ± 4.6* | −4.5 ± 7.8* | −5.1 ± 9.5 |
| By league strength | −11.2 ± 4.9* | −8.4 ± 9.8* | −2.8 ± 11.0 |
| Top league against others | −11.3 ± 4.9* | −5.1 ± 4.7 | −6.1 ± 7.2 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 160-197 | 44.8% | 54.2% | −9.4 ± 2.6 |
| Regular season | 134-170 | 44.1% | 52.5% | −8.4 ± 2.9 |
| Playoffs | 26-27 | 49.1% | 63.7% | −14.7 ± 6.9 |
| Home | 76-101 | 42.9% | 55.5% | −12.5 ± 3.8 |
| Away | 84-96 | 46.7% | 52.9% | −6.3 ± 3.7 |
| 2013-2019 | 79-91 | 46.5% | 54.8% | −8.4 ± 3.8 |
| 2020-2022 | 32-20 | 61.5% | 82.5% | −20.9 ± 6.9 |
| 2023-2026 | 49-86 | 36.3% | 42.5% | −6.2 ± 4.3 |
| High coach | 97-50 | 66.0% | 78.9% | −12.9 ± 4.1 |
| Mid coach | 48-49 | 49.5% | 54.9% | −5.4 ± 5.1 |
| Low coach | 15-98 | 13.3% | 21.4% | −8.2 ± 4.7 |
| Top league | 61-34 | 64.2% | 79.5% | −15.3 ± 5.1 |
| Other leagues | 99-163 | 37.8% | 45.0% | −7.2 ± 3.1 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.71 | 16th | | One-timer goals | 1.09 | 20th |
| Goals against | 4.00 | 16th | | Breakaway goals | 0.30 | 7th |
| Shots for | 12.7 | 2nd | | Checks | 28.2 | 3rd |
| Shots against | 11.9 | 6th | | Penalty minutes | 3.2 | 10th |
| Shooting % | 29.2 | 22nd | | Faceoffs won % | 50.3 | 7th |
| Save % | 66.5 | 19th | | Attack zone time, seconds | 313 | 20th |
| Power play % | 36.5 | 21st | | Pass completion % | 63.7 | 3rd |
| Penalty kill % | 61.3 | 8th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 68.7 (8th) | 8.1 (4th) | 3.5 (11th) | 3.4 (20th) | 3.6 (3rd) | 3.2 (4th) | 2.8 (12th) | 3.0 (23rd) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Peter Bondra | F | 1.29 | 0.81 | 2.10 | 4.64 | 78 | 6 | 6 | 3 | 4 |
| Dimitri Khristich | F | 1.15 | 0.66 | 1.81 | 4.43 | 75 | 7 | 3 | 4 | 6 |
| Mike Ridley | F | 0.45 | 0.43 | 0.88 | 2.22 | 73 | 9 | 4 | 3 | 4 |
| Al Iafrate | D | 0.16 | 0.46 | 0.62 | 6.11 | 78 | 11 | 4 | 6 | 2 |
| Bob Carpenter | F | 0.24 | 0.24 | 0.48 | 1.11 | 62 | 7 | 4 | 3 | 2 |
| Sylvain Cote | D | 0.07 | 0.38 | 0.46 | 2.92 | 61 | 6 | 3 | 3 | 2 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Don Beaupre | 3,925 | 66.0 | 3 | 3 |
| Rick Tabaracci | 232 | 76.3 | 2 | 2 |

## 20. Tampa Bay (TB)

**Overall: Poor. Best for: Low-level (leaning, few games).** Strength −9.4 ± 4.7 now (20th of 22), −13.1 ± 4.3 over all years (22nd).

**Elo adjustment:** −102* ± 37 points (22nd of 22). Against an even coach on the average team, on neutral ice, that's a 36% win chance. With one fixed strength per coach instead of Elo, it's −58.

Used in 5 of 97 leagues (1 of them a season's top league), by 5 coaches, 206 games, most recently 2025-05-18.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −18.5 ± 4.0* | −0.9 ± 7.2* | −17.6 ± 7.8 |
| By league strength | −20.9 ± 9.4* | −7.2 ± 8.5* | −13.8 ± 13.2 |
| Top league against others | −20.7 ± 9.4* | −10.5 ± 4.5 | −10.2 ± 10.5 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 98-108 | 47.6% | 62.2% | −14.6 ± 3.5 |
| Regular season | 86-92 | 48.3% | 62.8% | −14.5 ± 3.7 |
| Playoffs | 12-16 | 42.9% | 58.3% | −15.4 ± 9.4 |
| Home | 48-54 | 47.1% | 63.2% | −16.1 ± 5.0 |
| Away | 50-54 | 48.1% | 61.2% | −13.2 ± 4.9 |
| 2013-2019 | 7-13 | 35.0% | 54.9% | −19.9 ± 11.2 |
| 2020-2022 | 30-29 | 50.8% | 62.9% | −12.1 ± 6.5 |
| 2023-2026 | 61-66 | 48.0% | 63.0% | −15.0 ± 4.4 |
| High coach | 44-56 | 44.0% | 65.1% | −21.1 ± 5.0 |
| Mid coach | 30-32 | 48.4% | 62.3% | −13.9 ± 6.4 |
| Low coach | 24-20 | 54.5% | 55.4% | −0.9 ± 7.5 |
| Top league | 22-21 | 51.2% | 78.5% | −27.4 ± 7.6 |
| Other leagues | 76-87 | 46.6% | 57.9% | −11.3 ± 3.9 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.73 | 14th | | One-timer goals | 1.42 | 4th |
| Goals against | 3.82 | 9th | | Breakaway goals | 0.15 | 22nd |
| Shots for | 11.9 | 9th | | Checks | 25.8 | 11th |
| Shots against | 11.5 | 2nd | | Penalty minutes | 3.3 | 19th |
| Shooting % | 31.2 | 14th | | Faceoffs won % | 48.5 | 22nd |
| Save % | 66.8 | 17th | | Attack zone time, seconds | 310 | 22nd |
| Power play % | 37.1 | 18th | | Pass completion % | 61.9 | 12th |
| Penalty kill % | 58.1 | 19th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 54.5 (22nd) | 7.1 (19th) | 2.9 (22nd) | 2.7 (25th) | 2.3 (25th) | 2.8 (17th) | 2.3 (26th) | 3.0 (22nd) |

Hidden bonus: +0 at home, −0 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Brian Bradley | F | 1.98 | 0.68 | 2.66 | 7.85 | 71 | 4 | 3 | 4 | 5 |
| Mikael Andersson | F | 0.58 | 1.00 | 1.58 | 3.02 | 52 | 6 | 4 | 2 | 2 |
| Chris Kontos | F | 0.79 | 0.53 | 1.32 | 2.61 | 68 | 8 | 3 | 3 | 5 |
| Roman Hamrlik | D | 0.06 | 0.63 | 0.69 | 4.70 | 48 | 7 | 2 | 3 | 1 |
| Bob Beers | D | 0.03 | 0.54 | 0.58 | 4.12 | 51 | 9 | 3 | 2 | 2 |
| Steve Kasper | F | 0.17 | 0.28 | 0.46 | 1.52 | 55 | 5 | 3 | 2 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Wendell Young | 2,363 | 66.8 | 3 | 3 |

## 21. St. Louis (STL)

**Overall: Poor. Best for: Unclear.** Strength −10.1 ± 4.1 now (21st of 22), −7.5 ± 2.0 over all years (18th).

**Elo adjustment:** −59 ± 21 points (17th of 22). Against an even coach on the average team, on neutral ice, that's a 42% win chance. With one fixed strength per coach instead of Elo, it's −47.

Used in 23 of 97 leagues (7 of them a season's top league), by 19 coaches, 984 games, most recently 2026-11-03.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −2.6 ± 3.2 | −10.3 ± 4.7 | +7.7 ± 5.5 |
| By league strength | −6.2 ± 2.6 | −8.6 ± 4.0 | +2.4 ± 4.5 |
| Top league against others | −5.5 ± 3.6 | −8.7 ± 3.2 | +3.2 ± 4.9 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 471-512-1 | 47.9% | 55.3% | −7.4 ± 1.6 |
| Regular season | 399-447-1 | 47.2% | 55.1% | −8.0 ± 1.7 |
| Playoffs | 72-65 | 52.6% | 56.3% | −3.8 ± 4.3 |
| Home | 241-249-1 | 49.2% | 57.1% | −8.0 ± 2.3 |
| Away | 230-263 | 46.7% | 53.5% | −6.8 ± 2.3 |
| 2013-2019 | 129-107-1 | 54.7% | 59.1% | −4.5 ± 3.3 |
| 2020-2022 | 187-192 | 49.3% | 54.4% | −5.0 ± 2.6 |
| 2023-2026 | 155-213 | 42.1% | 53.8% | −11.7 ± 2.6 |
| High coach | 247-151 | 62.1% | 66.5% | −4.4 ± 2.5 |
| Mid coach | 85-162 | 34.4% | 44.5% | −10.1 ± 3.2 |
| Low coach | 139-199-1 | 41.1% | 50.0% | −8.9 ± 2.7 |
| Top league | 193-148 | 56.6% | 62.7% | −6.1 ± 2.7 |
| Other leagues | 278-364-1 | 43.3% | 51.4% | −8.1 ± 2.0 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.64 | 19th | | One-timer goals | 1.59 | 1st |
| Goals against | 3.80 | 8th | | Breakaway goals | 0.18 | 21st |
| Shots for | 11.0 | 22nd | | Checks | 25.4 | 12th |
| Shots against | 12.1 | 11th | | Penalty minutes | 3.1 | 8th |
| Shooting % | 33.2 | 6th | | Faceoffs won % | 50.8 | 3rd |
| Save % | 68.5 | 8th | | Attack zone time, seconds | 317 | 15th |
| Power play % | 38.4 | 12th | | Pass completion % | 62.6 | 6th |
| Penalty kill % | 62.2 | 5th | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 63.8 (21st) | 7.1 (18th) | 3.2 (20th) | 3.2 (21st) | 2.8 (22nd) | 2.9 (12th) | 2.7 (17th) | 4.0 (12th) |

Hidden bonus: +2 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Brett Hull | F | 1.77 | 0.62 | 2.39 | 4.60 | 81 | 9 | 4 | 6 | 3 |
| Nelson Emerson | F | 0.67 | 0.92 | 1.59 | 4.46 | 70 | 4 | 4 | 3 | 3 |
| Brendan Shanahan | F | 0.40 | 0.38 | 0.78 | 1.37 | 76 | 10 | 3 | 4 | 5 |
| Jeff Brown | D | 0.14 | 0.53 | 0.67 | 4.77 | 71 | 9 | 3 | 5 | 3 |
| Craig Janney | F | 0.29 | 0.38 | 0.66 | 1.31 | 75 | 7 | 3 | 3 | 4 |
| Bob Bassen | F | 0.25 | 0.27 | 0.52 | 1.83 | 57 | 4 | 4 | 2 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| Curtis Joseph | 11,820 | 68.6 | 4 | 4 |
| Guy Hebert | 33 | 60.6 | 2 | 2 |

## 22. NY Rangers (NYR)

**Overall: Poor. Best for: Both alike.** Strength −12.0 ± 3.3 now (22nd of 22), −10.9 ± 2.5 over all years (21st).

**Elo adjustment:** −74 ± 17 points (20th of 22). Against an even coach on the average team, on neutral ice, that's a 40% win chance. With one fixed strength per coach instead of Elo, it's −80.

Used in 32 of 97 leagues (14 of them a season's top league), by 32 coaches, 1,307 games, most recently 2026-11-02.

**By level of player**

| | High level | Low level | High minus low |
| --- | --- | --- | --- |
| By coach | −11.6 ± 3.9 | −9.3 ± 5.9 | −2.4 ± 6.6 |
| By league strength | −11.0 ± 3.8 | −6.1 ± 5.2 | −4.9 ± 6.0 |
| Top league against others | −10.7 ± 3.8 | −11.1 ± 3.1 | +0.4 ± 4.8 |

**Record**

| | Record | Win % | Expected | Against expected |
| --- | --- | --- | --- | --- |
| All games | 546-761 | 41.8% | 53.7% | −11.9 ± 1.4 |
| Regular season | 497-694 | 41.7% | 53.7% | −11.9 ± 1.4 |
| Playoffs | 49-67 | 42.2% | 53.9% | −11.7 ± 4.6 |
| Home | 281-373 | 43.0% | 54.7% | −11.8 ± 2.0 |
| Away | 265-388 | 40.6% | 52.6% | −12.1 ± 2.0 |
| 2013-2019 | 211-309 | 40.6% | 53.3% | −12.8 ± 2.2 |
| 2020-2022 | 86-159 | 35.1% | 47.0% | −11.9 ± 3.2 |
| 2023-2026 | 249-293 | 45.9% | 57.1% | −11.1 ± 2.1 |
| High coach | 256-324 | 44.1% | 57.6% | −13.5 ± 2.1 |
| Mid coach | 189-247 | 43.3% | 55.0% | −11.6 ± 2.4 |
| Low coach | 101-190 | 34.7% | 44.0% | −9.2 ± 2.9 |
| Top league | 258-330 | 43.9% | 56.2% | −12.4 ± 2.1 |
| Other leagues | 288-431 | 40.1% | 51.6% | −11.6 ± 1.9 |

**Per game**

| Stat | Value | Rank | | Stat | Value | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| Goals for | 3.88 | 7th | | One-timer goals | 1.34 | 8th |
| Goals against | 4.48 | 22nd | | Breakaway goals | 0.30 | 8th |
| Shots for | 11.6 | 16th | | Checks | 27.5 | 7th |
| Shots against | 12.2 | 18th | | Penalty minutes | 3.4 | 20th |
| Shooting % | 33.6 | 4th | | Faceoffs won % | 50.2 | 10th |
| Save % | 63.4 | 22nd | | Attack zone time, seconds | 319 | 11th |
| Power play % | 39.8 | 8th | | Pass completion % | 62.4 | 7th |
| Penalty kill % | 55.4 | 22nd | |  | |  |

**Ratings**

| Overall | Weight | Speed | Agility | Shot Power | Shot Accuracy | Checking | Goalie Agility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 71.6 (3rd) | 7.4 (12th) | 3.8 (6th) | 4.4 (1st) | 3.4 (8th) | 2.6 (20th) | 2.9 (9th) | 3.0 (20th) |

Hidden bonus: +1 at home, −1 away.

**Leading skaters** (per team game)

| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mike Gartner | F | 1.83 | 0.63 | 2.46 | 4.86 | 85 | 7 | 5 | 5 | 3 |
| Esa Tikkanen | F | 0.79 | 0.83 | 1.62 | 4.61 | 80 | 9 | 5 | 4 | 2 |
| Mark Messier | F | 0.45 | 0.51 | 0.95 | 2.57 | 85 | 10 | 4 | 3 | 3 |
| Brian Leetch | D | 0.16 | 0.65 | 0.81 | 4.63 | 76 | 6 | 3 | 4 | 1 |
| James Patrick | D | 0.12 | 0.64 | 0.77 | 6.25 | 71 | 9 | 4 | 4 | 1 |
| Darren Turcotte | F | 0.15 | 0.17 | 0.31 | 0.81 | 70 | 6 | 4 | 3 | 3 |

**Goalies**

| Goalie | Shots faced | Save % | Agility | Puck Control |
| --- | --- | --- | --- | --- |
| John Vanbiesbrk | 13,187 | 63.3 | 3 | 3 |
| Mike Richter | 2,459 | 65.7 | 3 | 3 |
