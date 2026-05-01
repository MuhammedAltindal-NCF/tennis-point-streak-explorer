# Tennis Point Streak Explorer

This project is an interactive Streamlit application for exploring point-by-point tennis streaks and comparing observed streak patterns against a simple independent binomial simulation model.

## Project Overview

The app allows users to select a tennis match, choose one or both players, adjust streak parameters, and visualize point-by-point streak patterns across sets.

The visualization highlights detected streaks using transparent path-based shading. Darker areas indicate overlapping streak intervals. Start and end points of streaks are marked directly on the point path.

The project also includes a binomial independent-process simulation. For a selected Player A, each simulated point is treated as an independent Bernoulli trial with probability `p = 0.50` by default. The number of simulated points is based on the number of points in the selected match. The app then compares the actual number of streaks to simulated streak outcomes.

## Main Features

- Interactive match selection
- Dynamic player selection
- Adjustable streak parameters:
  - Minimum wins in streak
  - Allowed losses inside a streak
- Point-by-point match visualization
- Hover tooltips showing:
  - Set number
  - Game number
  - Point in set
  - Game score
  - Games in set
  - Point winner
  - Server
- Serve-based background shading
- Streak shading that follows the point path
- Darker shading for overlapping streak intervals
- Start and end markers for streaks
- Binomial independent-process simulation
- Representative simulated match graph
- Summary metrics including:
  - Actual streak count
  - Mean simulated streak count
  - Median simulated streak count
  - Probability of obtaining at least as many streaks as the actual match

## Data

The app uses two main CSV files:

data/points.csv  
data/games.csv

### points.csv

This file contains point-level match data. Key columns include:

- match_id
- SetNo
- GameNo
- PointNumber
- PointWinner
- PointWinnerName
- PointServer
- PointServerName
- P1Score
- P2Score
- P1GamesWon
- P2GamesWon
- P1_name
- P2_name

### games.csv

This file contains game-level information used for serve shading. Key columns include:

- match_id
- SetNo
- GameNo
- game_start
- game_end
- server_name

## Streak Definition

For a selected player, each point is converted into a binary sequence:

1 = selected player won the point  
0 = selected player lost the point

A relaxed streak is detected when a segment contains at least the selected number of wins while allowing up to the selected number of losses inside the segment.

For example, with:

Minimum wins = 5  
Allowed losses = 1

a sequence such as:

1, 1, 1, 0, 1, 1

can be counted as a streak because it contains five wins with one allowed loss.

## Binomial Simulation

The simulation creates independent Bernoulli sequences for a selected Player A:

X_i ~ Bernoulli(p)

The default value is:

p = 0.50

The number of simulated points is based on the selected match. The app preserves the same set lengths as the actual match and applies the same streak detection rule to the simulated sequence.

The key probability reported by the app is:

P(Simulated streak count >= Actual streak count)

This value estimates how often an independent binomial process produces at least as many streaks as the actual match.

## How to Run Locally

Install the required packages:

pip install -r requirements.txt

Run the Streamlit app:

streamlit run app.py

## Project Structure

tennis_streaks_streamlit/
├── app.py
├── requirements.txt
├── README.md
└── data/
    ├── points.csv
    └── games.csv

## Notes

This simulation is a simple baseline model. It assumes independent points and a fixed point-winning probability. It does not account for serve advantage, player skill differences, fatigue, pressure situations, or other match-context factors.

Therefore, the simulation should be interpreted as a comparison against a simplified independent model, not as direct proof of psychological momentum.