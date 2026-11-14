# What wins: the recorded people's games

The user's aim for the analyses (2026-11-14): the stats that show how people play and why someone won or lost. This
page collects the measures that separate winners from losers in the recorded games where a person played each side.
Each is an association, not a cause: a team ahead may sit back and a team behind may press, so some stats move with
the score rather than make it.

**How:** `analysis/what_wins.py [genesis|snes]` takes every finished game recorded from its start with a person on
both sides (the season summaries; the bot's games left out), each team stat as this team minus the other (the score
itself, goals inside lists and the mirrored "against" halves left out), and reports how often the winner's value was
higher, the mean winner-minus-loser difference, and the rank correlation with the goal difference. Then a small
logistic model on the strongest stats shows which carry weight with the others known.

## Genesis (31 games, 2026-11-14)

| team minus opponent | winner higher | winner - loser (mean +- SE) | rank corr. with goal diff |
|---|---|---|---|
| expected goals (xG for) | 90% | +2.39 +- 0.42 | +0.76 |
| one-timers tried | 82% | +2.77 +- 0.56 | +0.73 |
| shot attempts | 81% | +4.03 +- 1.05 | +0.52 |
| shots on goal | 81% | +3.81 +- 0.96 | +0.64 |
| shot attempts off the rush | 79% | +3.61 +- 0.89 | +0.60 |
| zone entries that led to an attempt | 77% | +2.97 +- 0.77 | +0.55 |
| passes completed by the person | 74% | +7.16 +- 2.67 | +0.58 |
| turnovers that led to a shot against | 26% | -2.16 +- 0.77 | -0.35 |
| checks that led to a shot | 69% | +1.06 +- 0.50 | +0.40 |
| giveaways | 31% | -1.61 +- 0.72 | -0.16 |
| odd-man rushes | 68% | +1.39 +- 0.76 | +0.39 |
| attacking-zone possession (time) | 56% | +21.6 +- 10.4 s | +0.35 |
| attacking-zone time | 58% | +17.5 +- 17.5 s | +0.10 |
| checks thrown | 42% | -1.29 +- 1.58 | -0.12 |
| big hits | 42% | -0.23 +- 0.55 | -0.21 |
| penalties | 47% | +0.00 +- 0.36 | -0.09 |

Logistic model (one-timers tried, xG, shots on goal, rush attempts): one-timers tried carries the most weight (+1.5 per
standard deviation), then xG (+1.3), with the others known.

**Read:** on the Genesis the winner makes more chances and better ones (xG), above all one-timers, and completes more
passes; he gives the puck away less, and above all less often in ways that lead straight to a shot against. Time in
the attacking zone and possession there barely separate winners from losers, and hitting doesn't win games: winners
threw slightly fewer checks.

## SNES (25 games, 2026-11-14)

| team minus opponent | winner higher | winner - loser (mean +- SE) | rank corr. with goal diff |
|---|---|---|---|
| zone entries | 80% | +2.24 +- 0.79 | +0.50 |
| shot attempts off the rush | 72% | +1.92 +- 0.81 | +0.56 |
| expected goals (xG for) | 72% | +1.37 +- 0.34 | +0.70 |
| shots on goal | 68% | +1.32 +- 0.85 | +0.44 |
| zone entries that led to an attempt | 70% | +1.76 +- 0.80 | +0.62 |
| passes tried | 68% | +4.60 +- 2.84 | +0.41 |
| breakaways tried | 66% | +0.64 +- 0.37 | +0.33 |
| high-danger attempts | 62% | +1.36 +- 0.68 | +0.48 |
| one-timers tried | 62% | +1.04 +- 0.71 | +0.31 |
| big hits | 36% | -0.72 +- 0.54 | -0.27 |
| checks thrown | 38% | -1.56 +- 2.42 | -0.39 |

**Read:** on the SNES the winner gets into the zone more and shoots off the rush; one-timers matter less than on the
Genesis. Hitting again goes with losing more than winning.

## Decisions: shoot or wait, check or hang back

Ratios from the same summaries (what_wins.py's "ratio" rows), winner against loser:

| | Genesis: winner higher | SNES: winner higher |
|---|---|---|
| xG per attempt (shot quality) | 81% (+0.10 a shot) | 72% (+0.06) |
| one-timers per attempt | 73% | - |
| passes completed by the person | 76% | 38% |
| zone entries that led to an attempt | 69% | 60% |
| checks that paid off (the puck, a shot or a goal) | 61% | 72% |
| giveaways per attempt | 18% (the winner lower in 82%) | 40% |

**Shoot or wait:** on the Genesis the winner takes better shots, not only more: more of them one-timers off a pass,
and more of his passes reach their man; and he gives the puck away far less for each attempt he makes. Waiting for the
better shot, usually through a pass, goes with winning. **Check or hang back:** winners don't throw more checks, but
more of theirs win the puck or lead to a shot: picking the moment beats hitting a lot.

## Caveats

- Small samples: 31 and 25 games, many of them the user's own, so the results lean toward how the user's games go.
- Score effects: the team ahead tends to sit back, so possession and attack time can understate the better team;
  the team behind takes more risks.
- The stats themselves come from the converter, checked against the game's own counts where the game keeps them
  (goals, shots, checks, faceoffs) and, since 2026-11-14, giveaways and takeaways against NOSE4Web's in-game count.
