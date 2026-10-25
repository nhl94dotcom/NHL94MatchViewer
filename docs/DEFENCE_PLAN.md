# Defence studies: the plan (2026-10-25)

The question behind every study here is the user's: **how do you win at NHL '94?** The shooting studies
([SCORING_MAP](SCORING_MAP.md)) answer half of it: which chances score and how to make them. This plan is the other half:
how to stop them. It is a plan, not findings: each study gets its results written into the right doc when it runs
(SCORING_MAP for plays run in the game, a new section of GENESIS_MECHANICS for mechanics, the guides for the practical
advice).

Genesis first, as with the shooting studies; the SNES once the Genesis method works.

## The common yardstick

Every study ends in the same unit: **goals against per possession**, broken down as the chance a possession becomes a
shot, times what that shot is worth (the scoring maps and xG). Put beside the offensive studies (goals for), that gives
one table: for each way of playing, what it gains at one end and costs at the other. That table is the answer the
studies are building toward.

## The two ways of studying

| | Plays run in the game itself (the harness) | The recorded league games |
| --- | --- | --- |
| How | `analysis/scoring_map/`: the real game, headless, every skater placed by hand, one set-up played thousands of times | The match files of the league games (the Genesis games recorded so far, under 30), the same measures as `coach_report.py` |
| Good for | Cause and effect: one thing changed at a time, exact rates | What real people actually do, and what goes with winning |
| Weak at | Only the situations we build; the attackers are bots | Few games; many things change at once; can't prove cause |
| Load | Gentle mode, queued after the current runs | Light: a few minutes of reading files |

The two check each other: the harness says what works, the games say whether people do it and whether it shows in the
results.

## Phase 1: the recorded games (start now; no simulations)

### 1. Where goals and chances against come from

- **Question:** what situations produce the chances that score: rushes, turnovers in your own end, lost faceoffs,
  rebounds, one-timers, the goalie pulled out of position?
- **Method:** every shot against in every Genesis game, traced back to how the possession began and how the attack
  got to the shot (`play_by_play.py` and the event lists already hold the pieces: turnovers, zone entries, faceoffs,
  passes, rebounds).
- **Measures:** count, xG and goals of each kind; how long from the start of the possession to the shot.
- **Output:** a ranked list of the threats. Whatever produces the most goals against is what defence most needs to
  stop, and so which harness studies come first.

### 2. Which defensive habits go with conceding less

- **Question:** of the things a defending person does, which go with fewer and weaker chances against?
- **Method:** per person per game, the defensive measures `coach_report.py` already makes (position goal-side and on
  the puck-net line, switch timing, pokes by purpose, check attempts and the risky ones, transition), against chances
  and xG against. Then `coach_predict.py`'s approach on defence alone.
- **Measures:** each habit's rate, and how chances against change with it.
- **Output:** a short list of habits that matter, with the honest caveat that with under 30 games only big effects will
  show.

### 3. Transition: what a lost puck costs

- **Question:** when a team loses the puck, how often does a chance against follow within 5 seconds, by where it was
  lost (their end, neutral zone, own end) and how (a pass picked off, a poke, a check, a shot held by the goalie)?
- **Method:** every turnover in the match files, followed for 5 s.
- **Output:** the risk price of each kind of play with the puck, which also feeds the offence side (a risky pass that
  sets up a 60% one-timer may still be worth it).

## Phase 2: defending the plays that score (the harness; the biggest payoff)

### 4. One defender against each best play

- **Question:** where should a defender stand to stop the plays the shooting studies found? The plays: the deke (82-96%
  against the computer goalie), the pass across for a one-timer (63% inside 18 feet), the skating far-post slapshot
  (50-62%), the Down slapshot from the middle, the EA Special.
- **Method:** each play exactly as in its study (the same set-ups, timing and bot), with one defending skater added at
  a grid of positions: in front of the carrier at several distances, goal-side, on his stick side, in the passing
  lane, standing or skating back. First the defender stands still (does his body alone block the shot, the pass or the
  swing?); then he acts: a poke at set moments, a check, skating at the carrier.
- **Measures:** the play's goal rate with the defender against without him; how the play failed (blocked, poked away,
  hit, forced wide, pass intercepted).
- **Output:** for each play a map of where the defender takes it away and where he does nothing, plus animations of
  the best positions.
- **Order:** the deke first (it scores most), then the one-timer pass, then the slapshots, then the EA Special.
- **Load:** like a deke grid per play: several hours each in gentle mode.

### 5. Blocking: does a skater in the lane stop a shot?

- **Question:** the game's collisions between a shot puck and a skater's body. Does standing in the shooting lane
  block slapshots and wrist shots, from how far, and where does the deflection go?
- **Method:** the scoring map's shots with one skater placed along the shot line at several distances and offsets.
- **Output:** the blocking zone around a skater; whether "get in the lane" is real advice in this game.
- **Load:** small (a few hours).

## Phase 3: the defensive tools (the harness)

### 6. Poke checks

- **What we know** (GENESIS_MECHANICS 7.5): B released within 17 frames pokes if your skater is the one nearest where
  the puck will be in 16 frames; otherwise control switches.
- **Question:** how often does a poke win the puck, by angle (in front, beside, behind), distance, the carrier's speed
  and both players' ratings? How often does it trip him (a penalty when penalties are on)? When it misses, how far does
  the carrier get past?
- **Method:** a carrier skating a set line; a defender placed at a grid of angles and distances; B at a range of
  frames.
- **Measures:** puck loose, who recovered it, a trip, the carrier's lead after a miss.
- **Output:** a map of where pokes work, and what a missed poke costs.

### 7. Body checks

- **What we know** (GENESIS_MECHANICS 7.1-7.3): only a burst knocks down; impact from closing speed; the knockdown
  number from weight (the weight bug for a person's checker) and Checking; the CB check.
- **Question:** in practice, how often does a check knock the carrier down and free the puck, by angle and closing
  speed, C against CB, light against heavy? Who gets the puck? When it misses, how long is the checker out of the
  play?
- **Method:** as for pokes: a carrier on a set line, a checker bursting in from a grid of angles and speeds.
- **Measures:** knockdown, puck loose, who recovered, the checker's time to get back goal-side after a miss.
- **Output:** when a hit is worth it and when it gives up a chance (the coach report's "risky checks" from the
  game itself).

### 8. Loose pucks and rebounds

- **Question:** after a bobble, a poke or a hit, who gets the puck first, by where everyone stands? On defence: where
  should the defenceman be when the shot goes in, to clear the rebound before the shooter claims it (the defensive
  side of the EA Special)?
- **Method:** the EA study's bobbles (and the pokes and checks of 6-7) with a defender placed at a grid of spots,
  skating at the puck the moment it is loose.
- **Output:** the spots from which a defender wins the race, and the EA Special's rate with a defender there.

## Phase 4: who is on the ice (the harness and the games)

### 9. Whom to control

- **Question:** skaters nobody controls play by the game's own defensive rules (GENESIS_MECHANICS 12.3). How much worse
  do they defend than one a person controls, in the same spot? So which skater should you be, and when is a switch
  worth the moment it costs?
- **Method:** the plays of study 4 with the defender left to the computer against the same defender driven by a
  simple person-like bot; from the games, what happens after switches (study 2's switch timing).
- **Output:** practical rules for switching.

### 10. Ratings on defence

- **Question:** how much do a defender's Agility, Speed, Checking, Defensive Awareness and Weight matter in studies
  4-8? (As with the goalie study: one rating at a time.)
- **Output:** what to look for in defencemen; whether the CDL or other league edits change defence.

## Not in this plan until designed with the user

- **A person in goal.** How a person moving the goalie reacts to dekes, floaters and one-timers is a big part of
  defence, but these tests are deferred until we design them together (NEEDS_FROM_YOU).
- **Full games played by bots.** Possible later (a playing bot was discussed 2026-10-25), and the most complete test of
  all the findings, but not needed to start.

## What comes out at the end

1. **A threat list** (study 1): what to stop, in order of goals against.
2. **For each threat, how to stop it** (studies 4-8): where to stand, when to poke, when to hit, what each costs when
   it fails.
3. **Habits that matter in real games** (studies 2-3, 9): checked against what the harness says works.
4. **The offence-defence table** (the common yardstick): every way of playing, goals for and against per possession.
5. **Guide sections and animations** for each finding, as with the shooting studies.

## Order and timing

| Step | Studies | Load | When |
| --- | --- | --- | --- |
| 1 | 1, 2, 3 (recorded games) | Light | Can start now, beside the current queue |
| 2 | 4 (deke first), 5 | Gentle mode, about a day | After the current queue |
| 3 | 6, 7 | Gentle mode, about a day | Next |
| 4 | 8, 9, 10 | Gentle mode, a few days | Then |
| 5 | The SNES versions | Gentle mode | Once the Genesis method is settled |

Each harness study gets a short pilot first (a few set-ups, checked by eye with animations) before the full run, the
way the deke and EA studies were built.

## Questions for the user

1. Penalties on or off for the poke study (trips count only when they are on)? League settings are assumed.
2. Which defensive habits do good players say matter most? Those go first in study 2 and in the harness grids.
3. Any situations people say are hardest to defend that aren't in the list above?
