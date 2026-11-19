# The greatest coaches: how the year-end and peak tables work

A quick reference for the private tables `analysis/coach_peaks.py` writes to `%USERPROFILE%\NHL94_League_Data\coach_peaks`
(`PEAKS_GENESIS.md`, `PEAKS_SNES.md`, `PEAKS_COMBINED.md`). The tables name real people, so they stay in that folder;
this page has the methods only. "Coach" means a league player. Every number comes from the league result databases
(every league game since 2013, both systems).

## The two ratings underneath everything

**The Rating** (the one the coach guides use; the full method is in [COACH_RATING.md](COACH_RATING.md)):
- Every game is one equation: the result = home coach's strength - away coach's strength + home team - away team
  (team terms only in the Classic leagues, where an abbreviation always means the same roster) + a home edge. All
  games are solved together, so **beating a strong coach counts for more** than beating a weak one, and a coach is
  told apart from the team he used by how the same people do with other teams.
- The result isn't only win or loss: a win also counts for how long the winner was cruising (the league's coasting
  idea). Ties count as half.
- **Recent games count more**: a game's weight halves every 1.5 years.
- **Coaches with few games are pulled toward average**, so ten lucky wins don't make a champion.
- It's shown as a **win chance against an average coach** (the average of coaches with 100+ games), with neutral
  teams and no home edge. 75% means: against an average regular, on even teams, this coach wins about 3 of 4.
- **"As of" a date** means the fit uses only the games played before that date, as the Rating would have read then.

**The league's Elo** (as on the league site): every game in date order from 1500, K 20, +7 for the home side, the
Classic team adjustments in the leagues that use them, and the winner's gain and loser's loss multiplied by the
coasting bonus (x1.5 from the second-period buzzer for a cruising win). Elo doesn't solve all games together: it only
moves after each game, so it says less about whom a coach beat and jumps around more.

Both systems are rated separately: a Genesis Rating and an SNES Rating are each against that system's own average
coach. Names are matched trimmed and in lower case on both, so "SomeCoach" and "somecoach" are one coach.

## The tables, in the order they appear

### 1. The top ten at each year's end (2013 to 2026)

The Rating **as of 31 December** of each year (2026: to the last game in the data), from the games played by then.
To be listed a coach needs **100+ career games by then and 20+ games in that calendar year**, so retired coaches
don't sit in the table on old results. Each row: rank, Rating, career games, and that year's record.
- 2013 is thin (about 10 qualifiers): the data starts that year and nobody had 100 games yet.
- Talking point: the ranking says how strong a coach *was considered at that moment*, with the most recent year and
  a half counting most. A coach who had a monster spring and a quiet autumn still shows his spring in December.

### 2. Years finishing first, and years in the top ten

Counted from table 1: how many year-ends a coach was **#1**, which years, and how many year-ends he was **in the top
ten**. The simplest "greatness" count: staying power at the top.

### 3. Peak Rating

The **highest Rating a coach ever reached**, checked on the 1st of every month since 2013, using only the games played
by then. A month counts only if he had 100+ career games and 20+ games in the year before that day. Shown with the
month it happened.
- Talking point: "the best he ever was, by the standard rating". It favours a coach at the top of a long run, since
  the Rating keeps a year and a half of memory.

### 4. Best single year, and the prime (best three years in a row)

A strength **from one calendar year's games alone**, given whom he played, the teams and home ice. A year needs 20+
decided games, and each year is pulled a little toward the coach's career level (a 25-game year moves less than a
300-game year). Two lists:
- **Best year:** the single best calendar year.
- **Prime:** the best **three calendar years in a row**, averaged with each year weighted by its games. A coach
  without three qualifying years back to back has no prime (see table 7).
- Talking point: like a peak-years argument in baseball; this rewards sustained excellence, not one great month.

### 5. Against the field

How far above **the competition of the day** a coach stood at his best. On the 1st of each month the active coaches
are gathered (100+ career games, 20+ in the year before); a coach's height above their average is measured **in the
group's own spread** (standard deviations). +2.0 means two spreads above the typical active regular. The table shows
his highest, when, and how many coaches were active then.
- Talking point: it puts eras on equal terms. Beating a deep 2024 field and a thin 2014 field are each judged against
  who was actually playing.

### 6. Peak Elo

The league's Elo at its best, **held**: the best stretch of 30 games in a row, taking the middle (median) rating after
each of those 30 games, counted from the coach's 50th game on (so a hot start before the rating settles doesn't
count). It needs 80+ games. The table also shows the single highest Elo and when.
- Talking point: the familiar number. Held over 30 games so one lucky night isn't a peak.

### 7. All four together

Each coach's **rank on tables 3, 4 (prime), 5 and 6**, among the coaches who can be ranked on all four, and the
**mean of the four ranks** (1.0 = first on everything). The table also shows years first and years in the top ten.
- Only coaches with a prime (three qualifying years in a row) and 80+ games for the held Elo can be ranked here, so
  it's the long-career list.
- Where the ranks split, the split is the story: a Prime rank far below the others means a high peak that didn't last
  three years; a Peak Elo rank far below the others usually means the Rating credits his opponents' strength more
  than Elo does.

### 8. Strong coaches not ranked on all four, and why

The best coaches by Peak Rating who are missing from table 7, with their values on the measures they do have and
**what they lack** (no three qualifying years in a row, listing the years that qualified; or too few games for the held
Elo). Check here before saying someone "isn't on the list".

### 9. Genesis and SNES together (`PEAKS_COMBINED.md`)

At each year's end, coaches with **50+ games on each system that year** and 100+ career games on each; those with
**150+ on each are in bold**. The combined value is the average of the two year-end Ratings (each a win chance against
that system's own average coach), taken in log odds so one very high value isn't squashed. Each system's Rating,
games and record that year are shown beside it.
- Before 2020 almost nobody played both systems this much (0 to 8 a year at 50 games; 150 on both happened once);
  from 2020 there are 11 to 19 a year at 50 and 3 to 11 at 150.
- Each system counts equally, and fairly so: active regulars' Ratings spread about as widely on both (year-ends
  2021-2025: Genesis 0.80-0.95, SNES 0.75-1.09 in log odds). It's the Classic *teams* that sit closer together on the
  SNES, not the coaches.

## What none of these can tell you

- **Who would win now.** They describe results; a coach's level today is best read from the current Rating.
- **League level.** A coach in a lower league plays weaker opponents; the Rating adjusts for whom he played, but a
  coach who rarely meets the top regulars is rated through a few links.
- **Names.** Two handles for one person are two coaches; one handle shared by two people is one.
- **Small differences.** A point or two of Rating, or a couple of places in a rank, is within the noise.
