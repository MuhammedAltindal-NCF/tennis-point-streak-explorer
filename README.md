# Tennis Point Streak Explorer

## Project Overview

This project is an interactive Streamlit application for exploring point-by-point streaks in Grand Slam tennis matches.

The main research question is:

> Are long point streaks in tennis evidence of psychological momentum, or can similar streaks occur naturally under an independent random process?

To investigate this question, the app combines three components:

1. Point-by-point visualization of real tennis matches
2. Relaxed streak detection with user-controlled parameters
3. Binomial independent-process simulations for comparison against the actual match

The application allows users to select a match, choose one or both players, adjust the definition of a streak, and compare the observed number of streaks with simulated results.

---

## Data

The app uses cleaned point-level and game-level tennis data stored in the `data/` folder.

Expected files:

```text
data/points.csv
data/games.csv
```

The point-level data contains information such as:

- match ID
- set number
- game number
- point number
- point winner
- point server
- player names
- game score
- games won in the set

The game-level data is used to create background shading based on which player was serving during each game.

---

## Main Features

### 1. Match Selection

Users can select a match from a dropdown menu. Each match is displayed using player names and match ID.

Example:

```text
Rafael Nadal vs John Isner — 2011-frenchopen-1101
```

After selecting a match, the app shows:

- total number of points
- number of sets
- number of detected streaks
- point-by-point match visualization

---

## Streak Definition

The app detects relaxed point streaks.

A relaxed streak is defined as a sequence where a player wins at least a selected number of points while allowing a limited number of lost points inside the streak.

For example, if:

```text
Minimum wins = 6
Allowed losses = 1
```

then the following sequence is counted as a valid streak for Player A:

```text
1 1 1 1 1 1 0
```

This means Player A won 6 points and lost 1 point within the streak window.

---

## Sliding-Window Streak Detection

The streak detection algorithm uses a sliding-window approach.

Earlier versions counted only non-overlapping streaks. However, this could miss hidden or overlapping streaks. For example, in the Nadal-Isner match, there is a streak around the point 41–49 region that should be detected when the minimum number of wins is 6 and one lost point is allowed.

To fix this, the current version tests every point as a possible streak start.

This means:

- each set is processed separately
- each player is evaluated separately
- every point can be a potential streak starting point
- overlapping or hidden streaks can be detected
- the same streak definition is used for both actual matches and simulations

This makes the comparison between real and simulated matches more consistent.

---

## Match Visualization

The main graph shows the selected match point by point.

Each set is displayed separately.

The y-axis represents the two players:

- top line: Player 1
- bottom line: Player 2

Each point is plotted according to the point winner.

The visualization includes:

- black point-by-point winner path
- light background shading for serving player
- grey streak shading
- darker shading where streaks overlap
- green markers for streak starts
- red markers for streak ends
- hover tooltips with point details

Hover information includes:

- set number
- game number
- point in set
- game score
- games in set
- point winner
- server

---

## Simulation Module

The app includes a binomial independent-process simulation section.

The purpose of the simulation is to compare the actual number of detected streaks with the number of streaks that could occur under an independent random process.

The app asks:

> If points were generated independently with a selected probability of success, how often would we observe at least as many streaks as in the real match?

---

## Simulation Controls

Users can control the simulation using the sidebar.

### Player A for Simulation

The user selects which player is treated as Player A.

For example:

```text
Player A = Rafael Nadal
```

Then:

```text
1 = Player A wins the point
0 = Player A loses the point
```

---

### Streaks Counted in Simulation

The user can choose between:

```text
Player A only
Both players
```

If `Player A only` is selected, the simulation counts only the streaks won by Player A.

If `Both players` is selected, the simulation counts both:

```text
streaks of 1s + streaks of 0s
```

In other words, it counts both Player A's point-winning streaks and the opponent's point-winning streaks.

---

### Number of Simulations

The number of simulations is user-controlled.

The user can enter any value from:

```text
1 to 10000
```

This allows the user to simulate one match at a time or run many simulations for a distributional comparison.

---

### Optional Random Seed

The random seed is optional.

By default, no seed is used, so each simulation run can produce different random results.

If the user wants reproducibility, they can check:

```text
Use random seed for reproducibility
```

and then enter a seed value.

---

## Simulation Models

The app includes two simulation models.

### 1. Simple Independent Bernoulli Model

In the simple model, each point is simulated independently with the same probability.

For example:

```text
P(Player A wins point) = 0.50
```

or another value selected by the user.

This model treats all points as independent and does not account for who is serving.

---

### 2. Serve-Adjusted Bernoulli Model

The serve-adjusted model accounts for who is serving at each point.

The app estimates the overall serving advantage from all matches in the dataset.

The formula is:

```text
serve advantage = overall server win rate - 0.50
```

For example, if servers won 59.4% of all points in the dataset:

```text
overall server win rate = 0.594
serve advantage = 0.594 - 0.500 = 0.094
```

Then, for Player A:

```text
If Player A is serving:
P(Player A wins point) = base probability + serve advantage

If Player A is returning:
P(Player A wins point) = base probability - serve advantage
```

Example:

```text
base probability = 0.53
serve advantage = 0.094
```

Then:

```text
Player A serving:   0.53 + 0.094 = 0.624
Player A returning: 0.53 - 0.094 = 0.436
```

The app preserves the actual server sequence from the selected match when running this simulation.

---

## Simulation Output

After running the simulation, the app displays:

- mean simulated streaks
- median simulated streaks
- representative simulated streak count
- probability of obtaining at least as many streaks as the actual match
- histogram of simulated streak counts
- representative simulated match visualization

---

## Interpreting `P(Sim ≥ Actual)`

The value:

```text
P(Sim ≥ Actual)
```

means:

> Among the simulated matches, what proportion produced at least as many streaks as the actual match?

For example, if:

```text
Actual streaks = 19
P(Sim ≥ Actual) = 0.421
```

then about 42.1% of simulated matches produced 19 or more streaks.

This suggests that the observed number of streaks is not especially rare under the selected independent simulation model.

A small value, such as:

```text
P(Sim ≥ Actual) < 0.05
```

would suggest that the actual match produced more streaks than expected under the independent model, which could be interpreted as possible evidence of non-random momentum-like behavior.

---

## Histogram Interpretation

The histogram shows the distribution of streak counts across the binomial simulations.

The x-axis represents:

```text
number of streaks in a simulated match
```

The y-axis represents:

```text
frequency
```

The dashed vertical line represents the actual number of streaks in the selected match.

This makes it easier to visually compare the real match against the simulated independent-process distribution.

---

## Example Workflow

A typical analysis workflow is:

1. Select a match.
2. Choose whether to analyze Player 1, Player 2, or both players.
3. Set the minimum number of wins required for a streak.
4. Set the number of allowed losses inside a streak.
5. Inspect the actual match visualization.
6. Choose Player A for the simulation.
7. Select whether to count Player A only or both players.
8. Choose the number of simulations.
9. Select a simple Bernoulli model or serve-adjusted Bernoulli model.
10. Run the simulation.
11. Compare the actual streak count with the simulated distribution.

---

## How to Run the App

From the project folder, run:

```bash
streamlit run app.py
```

or:

```bash
python3 -m streamlit run app.py
```

The app should open in a browser.

If it does not open automatically, copy the local URL from the terminal, usually:

```text
http://localhost:8501
```

---

## Required Packages

The project uses:

```text
streamlit
pandas
numpy
plotly
```

Install them with:

```bash
pip install streamlit pandas numpy plotly
```

or:

```bash
python3 -m pip install streamlit pandas numpy plotly
```

---

## Project Structure

```text
tennis_streaks_streamlit/
├── app.py
├── README.md
├── requirements.txt
├── data/
│   ├── points.csv
│   └── games.csv
└── archive/
```

---

## Research Interpretation

This app does not directly prove whether psychological momentum exists.

Instead, it provides a framework for comparing observed streak patterns against independent-process simulations.

If the actual match has many more streaks than expected under the simulated model, that may suggest the presence of non-random structure.

If the actual match streak count falls near the center of the simulated distribution, then the observed streaks may be explainable by chance, given the selected assumptions.

The serve-adjusted model provides a more realistic baseline than a pure 50-50 model because tennis points are strongly affected by who is serving.

---

## Current Status

The current version includes:

- interactive match selection
- point-by-point visualization
- relaxed streak detection
- sliding-window detection for hidden and overlapping streaks
- user-controlled streak parameters
- binomial independent-process simulation
- custom number of simulations
- optional random seed
- simulation histogram
- Player A only / Both players simulation scope
- serve-adjusted Bernoulli simulation
- overall serve advantage estimated from all matches