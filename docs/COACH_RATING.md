# How the coach ratings are calculated

This document explains how the league coach ratings are made, how they were tested and what they can't tell you. The code is
`analysis/coach_rating.py`. The tables with players' names stay in the private league data folder, so this document has
aggregates only. Results are as of the league data update of 2026-11-04, with games through 2026-11-03.

## The short version

A rating is a coach's estimated chance of beating an average coach, with neutral teams and no home edge. To get it:

1. Every game gets a score: the win or loss, plus a bonus for how early the win was safe.
2. Every game becomes one equation that links the two coaches, their teams and the home edge.
3. All the equations are solved together, so a result counts for more or less depending on who it came against.
4. Recent games count more, and small samples are pulled toward the middle.
5. The answer is converted to a win chance using how well ratings predicted later games, with 50 set to the mean coach who has 100+
   games in that table.

## 1. The games

The source is the league result databases: every league game since 2013 on both systems.

A game is used if it has a home and away score, two different named players and a valid date. Games marked as simulated are
skipped. Regular-season and playoff games count the same.

- **Names.** Names are compared in lower case. People confirmed to have changed names are merged through a private list
  (`coach_aliases.csv` in the league data folder). Someone who changed names and isn't on that list still counts as two coaches.
- **Repeated results.** About 0.3% of rows repeat another row's league, players, score, shots and goal list. These stay in. They're
  usually a real second game, played when no save state was taken after the first, so an earlier save state with the right winner was used again.
- **Period lengths.** Nearly all leagues play 5-minute periods. A league's length is read from its longest regulation goal, and goal times in the
  few others are converted to a share of the period: two Genesis leagues with 7-minute periods and three with 3-minute periods, 890 games in all. No
  SNES league or league group is affected. Short overtimes need nothing, because overtime wins get no coasting bonus.

There are six tables, each fitted entirely on its own games:

| Table | Which leagues | Games | Coaches | With 100+ games |
| --- | --- | --- | --- | --- |
| Genesis, all leagues | all | 86,985 | 326 | 173 |
| SNES, all leagues | all | 36,243 | 224 | 96 |
| Genesis Classic | name starts with "Classic" | 23,092 | 281 | 121 |
| SNES Classic | name starts with "Classic" | 15,151 | 182 | 75 |
| Genesis Chaos | name starts with "Chaos" | 11,711 | 106 | 62 |
| SNES Draft | name starts with "SNES_Draft" | 7,918 | 65 | 37 |

## 2. The score for each game

The winner gets a positive score and the loser the same score as a negative. A tie is 0.

`score = 1 + coasting bonus`, where the bonus can't go above 1.

**The coasting bonus** is the final unbroken stretch of regulation in which the eventual winner was safe, as a share of a third
period's length. "Safe" means a lead of 2 or more goals and a 90%+ chance of winning given only that lead and the time left. That
chance is taken from how such positions turned out in the same table's games. The check runs every 10 seconds of game time.

| Result | Score |
| --- | --- |
| Tie | 0 |
| Overtime win, or any 1-goal win | 1 |
| Win by 2+ goals, never safe for long | at least 1.1 |
| Safe for the last half of a third period's length | 1.5 |
| Safe for a third period's length or longer | 2 (the maximum) |

A very few games have no usable goal times. They get a bonus of 0.1 if the margin was 2 or more, otherwise none.

Shots, xG and other game stats aren't used. Goals matter only through the win and the coasting bonus.

All scores are then divided by their spread (standard deviation, about 1.5), so that the settings in section 5 mean the same thing
across the tables. The examples below use round numbers before that step, for simplicity.

## 3. One equation per game

`game score = home coach − away coach + home team − away team + home edge`

The score is from the home side's view. The coaches and teams are unknown numbers (their strengths), and the home edge is one more
unknown shared by the whole table. Genesis Classic has 23,092 equations and 304 unknowns: 281 coaches, 22 teams and the home edge.

**Team terms apply only to Classic leagues with retail rosters.** That means a league name starting with "Classic" and only retail team labels,
so one Genesis league with other labels (`Classic_Dynasty_S1`) counts as Classic for the group but has no team terms. A name with
"Classic" later in it, such as a Modern Classic league, isn't treated as Classic. In those leagues the same abbreviation is taken to mean the same roster. Elsewhere
rosters differ, so no team term is fitted and a coach's drafting and roster become part of their rating. A team needs 100+
appearances to get a term. A game involving a team below that, or two sides on the same team, has no team terms at all.

## 4. Solving them together

No set of strengths can fit every game, because upsets happen. For any candidate set of strengths, each game has a **miss**:
the actual score minus the expected one. The method is weighted ridge regression: choose the strengths that make this total as
small as possible.

`total = sum of (game weight × miss²) + pull setting × sum of (strength²)`

Three small examples show what this does.

**Same record, different opponents.** P goes 5-5 against Strong, Q goes 5-5 against Weak, and Strong beats Weak in all 10 of their
games with a score of 1 each. Without the pull, P comes out equal to Strong and Q equal to Weak, so P rates 1 above Q. They have
identical records and never played each other.

**A circle of results.** A beats B, B beats C and C beats A, each with a score of 1. All three come out equal.

**A narrow win can lower a rating.** If a coach is expected to score 1.5 against a much weaker player and scores 1, the miss is
negative and pulls them down slightly. A narrow loss to someone much stronger can raise them. Only the difference from what was
expected moves a rating.

## 5. The pull toward the middle

The second part of the total charges a cost for every strength away from zero. A rating has to reduce the misses by more than it
costs, so large ratings need evidence.

**The easiest way to picture it is as imaginary tied games.** A pull setting of 2 is roughly like giving every coach 2 extra tied
games against a player at the middle. A setting of 10 is like giving them 10. For a coach whose opponents' strengths are already
known, what's left after the pull is:

`share kept = weighted games ÷ (weighted games + pull setting)`

| Weighted games | Kept at setting 2 | Kept at setting 10 |
| --- | --- | --- |
| 1 | 33% | 9% |
| 5 | 71% | 33% |
| 20 | 91% | 67% |
| 100 | 98% | 91% |

**Where the middle is.** Zero is the plain mean of all coaches in the table, including low-game ones, who are mostly weaker than
regulars. So the middle isn't 50. Its place on the final scale is:

| Genesis, all | SNES, all | Genesis Classic | SNES Classic | Genesis Chaos | SNES Draft |
| --- | --- | --- | --- | --- | --- |
| about 45 | about 36 | about 41 | about 39 | about 39 | about 46 |

A brand-new coach therefore starts well below 50. Coaches with 1-9 games bear this out: their median rating is about 40 in Genesis Classic and
36 in SNES Classic.

**How far it reaches.**
- **Against a hot start:** the pull is fairly light. In Genesis Classic (setting 2), a coach who goes 8-1 against average opponents keeps
  about 80% of their result and would rate about 65. That's short of the top, but it isn't proof either, so use the 100+ game filter when
  ranking.
- **For retired coaches:** age reduces weighted games, so the pull grows after someone stops playing. With a half-life of 1.5 years
  and setting 2, 200 games from 8 years ago count as about 5 weighted games and keep 71%. From 12 years ago they count as less than 1 and
  keep 28%. So retired players drift toward the middle in the main column but not in `career`. This is slow in SNES Classic, where the
  half-life is 3 years: a coach who stopped in 2016 still ranks 4th among coaches with 100+ games.

The home edge has no pull. Team terms have the same pull as coaches.

## 6. Recent games count more

Each game's weight halves with every half-life of age: at a half-life of 1.5 years, a game counts 1/2 after 1.5 years, 1/4 after 3
and 1/16 after 6. Age is measured from the last game in that table, so Chaos, which last played in April 2026, is measured from then.

The half-life and pull setting were chosen by testing (section 10), not by judgment:

| Table | Half-life | Pull setting |
| --- | --- | --- |
| Genesis, all leagues | 1.5 years | 10 |
| SNES, all leagues | 1.5 years | 2 |
| Genesis Classic | 1.5 years | 2 |
| SNES Classic | 3 years | 2 |
| Genesis Chaos | 1.5 years | 2 |
| SNES Draft | 1.5 years | 2 |

## 7. From strength to a win chance

Strengths are on an arbitrary scale, so one factor converts them to a chance:

`win chance = 1 / (1 + exp(−factor × strength gap))`

**The factor comes from later games.** Every half year in the last 3 years of the table, the fit uses only earlier games to
predict the next half year's decided games between coaches with 30+ earlier games. The factor is whatever best matches how those games
really came out. A factor fitted on the same games as the strengths came out too large and overstated chances: in SNES Classic, predictions of about 84% won about 75%
of later games. With the factor from later games, those same games look like this:

| Predicted, about | Genesis, all | SNES, all | Genesis Classic | SNES Classic | Genesis Chaos | SNES Draft |
| --- | --- | --- | --- | --- | --- | --- |
| 55% | 55% | 55% | 57% | 54% | 55% | 58% |
| 65% | 64% | 63% | 63% | 63% | 66% | 63% |
| 75% | 74% | 74% | 74% | 79% | 74% | 72% |
| 85% | 87% | 87% | 84% | 82% | 79% | 88% |

The factor was set on these games, so the overall level is bound to match. The agreement across the bands is the real check. The top band is small in
the league groups (110-276 games), so those are rough. The factors in use are:

| Genesis, all | SNES, all | Genesis Classic | SNES Classic | Genesis Chaos | SNES Draft |
| --- | --- | --- | --- | --- | --- |
| 2.058 | 1.981 | 1.746 | 1.610 | 1.678 | 1.626 |

The factor affects percentages only. It can't change the order of coaches in a table.

**Setting the average.** Only differences between coaches appear in the equation. Adding 10 to everyone changes nothing, so the zero
point has to be chosen. Everyone is shifted so that the mean coach with 100+ games in that table is at exactly 50. Low-game
coaches still count in the fit and are listed in the table, but they don't set this average. This is one reason numbers can't be compared across tables.

**Comparing two coaches in a table.** Turn each rating into `ln(rating ÷ (100 − rating))`, subtract, and put the gap back through
`1 / (1 + exp(−gap))`. For example, an 80 against a 60 is `1.386 − 0.405 = 0.981`, or about 73%. Teams and home edge would shift this further.

## 8. The columns in the private tables

| Column | Meaning |
| --- | --- |
| `win_chance_vs_average` | The main rating, which fades old games, so it's closest to current strength |
| `low`, `high` | One standard error of the coach's gap from the average, either side of the rating, from the fit alone. For retired coaches it's wide, because little weight is left on their games |
| `career` | The same fit with every game weighted equally, on the same factor and shifted so the mean 100+ coach is 50. It's a career average, not a peak. Sharing the factor makes the two columns comparable, but `career` isn't a measured historical win rate |
| `games`, `games_last_2_years`, `last_played` | Simple counts and dates, which don't affect the rating. "Last 2 years" runs back from the table's last game |
| `group` | Which connected group of opponents the coach is in. All six tables have a single group |

The top-player lists use these filters: 100+ games to be listed, and 30+ games in the last 2 years to count as active.

## 9. Classic team strengths

Team strengths don't come from ROM ratings or roster data. They're fitted from the results in the same equations.
The calculation separates coach from team because the same people play on different teams. If many coaches do better with a team than
they do elsewhere, that goes to the team. If one coach does well on everything, that goes to the coach.

The values below are points of win chance above or below 50 for a team against a neutral team, with even coaches and no home edge. The
zero is the plain mean of the fitted teams. "Sides" counts each time a team appeared in a game. The values fade with age like everything else, so they reflect
recent play more than old play.

| Genesis Classic | Value | Sides | | SNES Classic | Value | Sides |
| --- | --- | --- | --- | --- | --- | --- |
| CHI | +10.9 | 3,955 | | NJ | +6.7 | 760 |
| DET | +9.4 | 4,124 | | PIT | +5.1 | 2,522 |
| BUF | +7.2 | 3,962 | | NYR | +3.8 | 2,533 |
| MTL | +5.5 | 3,859 | | VAN | +2.1 | 2,105 |
| BOS | +4.5 | 3,812 | | CHI | +1.7 | 2,433 |
| VAN | +2.6 | 3,879 | | LA | +1.6 | 2,239 |
| DAL | +2.2 | 2,675 | | CGY | +1.6 | 1,976 |
| WPG | +2.1 | 3,541 | | WSH | +1.2 | 1,148 |
| HFD | +1.2 | 477 | | MTL | +0.9 | 1,700 |
| CGY | +0.8 | 3,025 | | TOR | +0.6 | 771 |
| TOR | +0.4 | 1,574 | | BOS | +0.4 | 2,513 |
| LA | −0.9 | 2,379 | | STL | +0.3 | 573 |
| PHI | −1.9 | 1,067 | | EDM | +0.3 | 521 |
| QUE | −2.3 | 2,050 | | WPG | −0.2 | 1,279 |
| NJ | −2.8 | 334 | | DET | −0.3 | 2,327 |
| EDM | −2.8 | 669 | | PHI | −0.9 | 663 |
| NYI | −3.0 | 225 | | QUE | −2.0 | 895 |
| WSH | −4.2 | 380 | | HFD | −2.1 | 254 |
| PIT | −5.5 | 1,153 | | BUF | −2.5 | 2,103 |
| TB | −6.9 | 225 | | NYI | −4.2 | 319 |
| STL | −7.6 | 1,004 | | SJ | −6.6 | 175 |
| NYR | −9.1 | 1,307 | | DAL | −7.4 | 204 |

**How far to trust them.**
- **SNES values depend on the settings, especially for rarely played teams.** Changing the SNES Classic pull setting from 10 to 2, with the
  small data fixes, moved San Jose from +5.8 to −6.5, and Detroit from −5.0 to −0.3. Read that column for broad groups only.
- **Some labels get no term.** Genesis Classic has 4 retail labels under 100 sides (ANH, FLA, OTW, SJ; 20-28 each), and SNES Classic has 4 (OTW,
  ANH, TB, FLA; 40-96 each).
- **New Jersey on the SNES** holds up better than most of that column. It stays between +5.6 and +7.1 across settings and is the heaviest roster, and
  SNES Weight is the one playing rating the hot / cold bug doesn't touch (`LEAGUE_RESULTS`).
- **The assumption is one roster per abbreviation.** If a Classic league used a changed roster, its team value would blur the two.

## 10. How it was tested

Settings and versions were judged by predicting the future:

- **The test.** Starting in 2020, fit on all games before a date, then predict later decided games between coaches who
  each had 30+ earlier games in that table. The chance comes from a factor set on earlier test games, so nothing from a test game goes into its own
  prediction.
- **The measure.** Log loss, where lower is better and a coin flip is 0.6931.
- **Choosing settings.** Half-lives of none, 3 and 1.5 years and pull settings of 2, 10 and 40 were tried on half-yearly refits. In SNES Classic the
  difference between pull settings 2 and 10 was very small, so that choice is close to a coin flip.
- **The versions compared.** Win or loss only; goal difference capped at ±5; win plus coasting capped at 100% or 200%; and a blend of
  capped goal difference with coasting at 100%.
- **Elo for comparison.** Everyone starts at 1500, K is 16 on the Genesis and 20 on the SNES, with no home or team terms. It was run both ways: updated
  after every game, and frozen monthly to match how often the rating was refitted. The best other value of K improved Elo's scores by
  about 0.001 at most, which changes none of the conclusions.

Results with monthly refits, in each league group alone, with all versions on the same settings as that table:

| Table | Test games | Elo, every game | Elo, frozen monthly | Win only | Capped goal diff | Win + coasting (used) | Blend |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Genesis Classic | 13,030 | 0.6500 | 0.6642 | 0.6477 | 0.6465 | 0.6462 | 0.6461 |
| SNES Classic | 8,850 | 0.6409 | 0.6576 | 0.6490 | 0.6448 | 0.6468 | 0.6455 |
| Genesis Chaos | 9,258 | 0.6458 | 0.6647 | 0.6457 | 0.6440 | 0.6445 | 0.6441 |
| SNES Draft | 6,325 | 0.6342 | 0.6534 | 0.6434 | 0.6387 | 0.6411 | 0.6398 |

And in the all-leagues tables:

| Table | Test games | Elo, every game | Elo, frozen monthly | Win only | Capped goal diff | Win + coasting (used) | Blend |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Genesis, all | 63,636 | 0.6029 | 0.6145 | 0.6062 | 0.6056 | 0.6056 | 0.6055 |
| SNES, all | 26,767 | 0.5915 | 0.6045 | 0.5962 | 0.5921 | 0.5939 | 0.5928 |

What this shows:

- **Against Elo updated every game:** the rating is better in Genesis Classic (by 0.0038 ± 0.0018), level in Genesis Chaos, and
  behind in SNES Classic (0.0059 ± 0.0025), SNES Draft (0.0069 ± 0.0028) and both all-leagues tables (0.0027 and 0.0025).
- **Against Elo frozen monthly,** the like-for-like comparison, the rating is better in every table.
- **Coasting against win-only:** coasting is better in every table, by small amounts that clear the test's noise.
- **Coasting against capped goal difference:** tied on the Genesis, in all three tables. Goal difference is ahead on the SNES (0.0019 ± 0.0005 in SNES
  Classic, 0.0024 ± 0.0005 in SNES Draft, 0.0018 ± 0.0003 in all leagues). The tables use coasting because it's the rule
  that was asked for, not because it won. The blend is about as good as either.

**Other checks**

| Check | Genesis, all | SNES, all | Genesis Classic | SNES Classic | Genesis Chaos | SNES Draft |
| --- | --- | --- | --- | --- | --- | --- |
| Two random halves of the games, fitted apart: correlation over coaches with 100+ games | 0.98 | 0.98 | 0.94 | 0.95 | 0.96 | 0.97 |
| A coach one standard deviation above another (among 100+ coaches) wins | 69% | 70% | 65% | 65% | 67% | 68% |
| Home wins between even coaches on neutral teams | 50.5% | 52.4% | 50.8% | 52.5% | 48.8% | 51.8% |

Dropping low-game coaches' games was also tested. Removing coaches under 100 games made predictions worse
(Genesis 0.6210 to 0.6251, SNES 0.6244 to 0.6269) and left the top 20 unchanged, so every game stays in the fit.

**The width of `low` and `high`.** Each table was split at 18 months ago, for coaches with 50+ games on both sides (21-56 coaches a table). The
ranges fit luck but not change:

| Check: how far ratings differ, against what the ranges expect | Genesis, all | SNES, all | Genesis Classic | SNES Classic | Genesis Chaos | SNES Draft |
| --- | --- | --- | --- | --- | --- | --- |
| Random halves of the later games | 0.92 | 0.66 | 0.92 | 0.69 | 0.81 | 0.83 |
| Earlier games against later games | 1.77 | 1.21 | 1.14 | 2.01 | 1.25 | 1.36 |

So a range describes how sure the rating is about a coach's recent level, slightly generously. It's about one and a half times too narrow, sometimes
twice, as a guide to where a coach will be later, because people really do change. These small groups make the figures rough.

**How much one day moves the ratings.** Twelve real days from the past year in each table, fitted with and without the day's games, for active regulars:

| | Genesis, all | SNES, all | Genesis Classic | SNES Classic | Genesis Chaos | SNES Draft |
| --- | --- | --- | --- | --- | --- | --- |
| Games on a typical playing day | 32 | 11 | 20 | 10 | 15 | 8 |
| Typical move for someone who played, in rating points | 0.10 | 0.11 | 0.41 | 0.26 | 0.23 | 0.36 |
| Largest move seen | 0.99 | 0.88 | 1.74 | 1.55 | 1.19 | 1.00 |
| Typical move for someone who didn't play | 0.01 | 0.01 | 0.03 | 0.03 | 0.01 | 0.04 |
| Days the top 10 stayed in the same order | 12 | 12 | 8 | 12 | 12 | 10 |

## 11. What the ratings can't tell you

- **The main column isn't an all-time ranking.** It leans toward recent form. Use `career` for all-time, and note that it's an average, not a peak.
- **Eras are hard to compare.** Players from different years are linked only through shared opponents. If the whole league improved,
  the model can't see it, so old players with few games can rate high against an old, possibly weaker field. In SNES Classic the two highest
  `career` ratings belong to coaches with 142-160 games who stopped by 2016.
- **Numbers can't be compared across tables.** Each has its own games and average. Compare ranks instead.
- **Chaos and SNES Draft ratings include the roster.** They measure drafting plus playing, and one rating can't separate the two.
- **The ranges leave out change.** `low` and `high` fit game-to-game luck but not changes in form (section 10). Don't treat gaps of 1-2 points as real.
- **Small samples can run hot.** Among many coaches with about 100 games, those who reach a top list are more likely to have been lucky, so
  low-game ratings at the top are a little inflated.
- **The test isn't completely independent.** Settings were chosen on the same years used for the test, Elo's K was also tuned earlier on
  these games, and the coasting bonus's chance-by-lead table is built from all years. That flatters both sides slightly, so small gaps between versions shouldn't be overread.
- **One strength per coach.** The model can't see someone who matches up unusually well against a particular opponent or style. Those results count as misses.
- **The 50 is not a typical active player.** It's the mean of 100+ game coaches, including retired ones, and active regulars mostly play each
  other. So a record near .500 among active regulars can earn a rating well above 50.

## 12. Running it

```
python analysis/coach_rating.py            the all-leagues test and tables
python analysis/coach_rating.py groups     each league group fitted alone
```

Results go to `%USERPROFILE%\NHL94_League_Data`: `coach_ratings_<system>.csv`, `coach_ratings_<system>_<group>.csv`,
`coach_rating_test.md` and `coach_rating_groups.md`. Findings in aggregate are in `docs/LEAGUE_RESULTS.md`.
