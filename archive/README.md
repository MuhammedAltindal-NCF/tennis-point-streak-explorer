# Archive: R Markdown Research Workflow

This folder documents the earlier R/RMarkdown stage of the tennis point streak research project before the final Streamlit application was built.

The main Streamlit app is located in the root project folder. This archive explains the original data preparation, streak detection experiments, and visualization work that led to the final app.

---

## Purpose of This Archive

The goal of this archive is to make the research process reproducible and understandable for someone reviewing the project from the beginning.

Before building the Streamlit app, the project was developed in R using point-by-point Grand Slam tennis data. The work included:

- Cleaning and preparing match-level point sequences
- Identifying point streaks and relaxed/flex streaks
- Adding match context such as game score, set score, and server information
- Creating static visualizations
- Generating CSV files for Tableau/Shiny-style interactive visualization
- Testing different ways to show streak overlays, breaks, and one-point interruptions

---

## Folder Structure

```text
archive/
│
├── README.md
│
├── r_markdown/
│   ├── Tennis_Point_Streaks.Rmd
│   ├── Tennis_Point_Streaks_Part_2.Rmd
│   └── Tennis_Point_Streaks_Part_3.Rmd
│
├── raw_data/
│   ├── 2011-frenchopen-matches.csv
│   └── 2011-frenchopen-points.csv
│
├── figures/
│   ├── Graph-1.png
│   ├── Graph-2.png
│   └── Graph-3.png
│
└── notes/
    └── research_progress_notes.docx
```

---

## Files and Their Roles

### `raw_data/2011-frenchopen-matches.csv`

This file contains match-level metadata for the 2011 French Open dataset.

It includes information such as:

- Match ID
- Player names
- Tournament information
- Match-level identifiers

This file was used to connect player names and match information to the point-by-point data.

---

### `raw_data/2011-frenchopen-points.csv`

This file contains point-by-point data for matches in the 2011 French Open.

It includes information such as:

- Match ID
- Set number
- Game number
- Point number
- Point winner
- Point server
- Point score
- Game score

This was the main source file used to build the point sequence visualizations and streak calculations.

---

## R Markdown Workflow

### 1. `Tennis_Point_Streaks.Rmd`

This was the first stage of the project.

Main purpose:

- Load the raw French Open point-by-point data
- Select individual case-study matches
- Create the first point-sequence visualizations
- Map point winners to player rows
- Add server context with background shading
- Add game and set boundaries
- Begin identifying streak breaks and one-point interruptions

This stage helped establish the basic visual idea: a point-by-point zigzag chart showing which player won each point.

---

### 2. `Tennis_Point_Streaks_Part_2.Rmd`

This was the second stage of the project.

Main purpose:

- Focus on relaxed/flex streaks
- Define streaks as sequences with a minimum number of won points while allowing limited lost points
- Test the Andy Murray vs Viktor Troicki match as a case study
- Add grey overlays to show detected relaxed streaks
- Mark streak breaks and one-point interruptions
- Organize the visualization by set

This stage was important for developing the idea of “momentum periods” instead of only strict consecutive streaks.

---

### 3. `Tennis_Point_Streaks_Part_3.Rmd`

This was the third stage of the R workflow.

Main purpose:

- Create reusable tables for interactive visualization
- Precompute streaks across different parameter settings
- Generate separate output tables for points, games, streak summaries, overlays, and markers

This script can generate the following CSV outputs:

```text
points_tableau.csv
games_tableau.csv
streaks_tableau.csv
streak_overlay_tableau.csv
markers_tableau.csv
```

These generated CSV files are not included in the repository because they can be recreated from the R Markdown code and some of them are large.

---

## Generated CSV Outputs

The R workflow produced several intermediate CSV files.

### `points_tableau.csv`

Point-level table used to draw the main zigzag match flow.

Contains:

- Match ID
- Set number
- Game number
- Point index
- Point score
- Player names
- Point winner
- Point server
- Plotting position

---

### `games_tableau.csv`

Game-level table used for server background shading.

Contains:

- Match ID
- Set number
- Game number
- Game start point
- Game end point
- Server name

---

### `streaks_tableau.csv`

Summary table of detected streaks.

Contains:

- Match ID
- Player name
- Minimum streak length
- Allowed losses
- Streak start and end points
- Points won in streak
- Points lost in streak
- Streak length

---

### `streak_overlay_tableau.csv`

Point-level expansion of the detected streaks.

This file was used to draw the grey streak overlays on top of the point sequence.

This file can become large, so it is not stored in the repository.

---

### `markers_tableau.csv`

Marker table used to show special points on the visualization.

Contains:

- Streak start markers
- Streak end markers
- Streak break markers
- One-point interruption markers

---

## Figures

The `figures/` folder contains selected example visualizations from the R stage.

These figures show the evolution of the project before the final Streamlit app:

- Point sequence visualization
- Server context shading
- Set/game structure
- Relaxed streak overlays
- Streak breaks and one-point interruptions

---

## Why This Archive Exists

This folder is not the final application.

Instead, it documents the research and development process that led to the final Streamlit app.

The final app improves on this archive by adding:

- Interactive match selection
- Player selection
- Adjustable minimum streak length
- Adjustable allowed losses
- Non-overlapping streak logic
- Serve-adjusted Bernoulli simulation
- User-adjustable serve advantage
- Simulated match visualization
- Probability used for each simulated point in hover text

---

## Reproducibility Notes

To reproduce the earlier R workflow:

1. Open the R Markdown files in order.
2. Start with `Tennis_Point_Streaks.Rmd`.
3. Then run `Tennis_Point_Streaks_Part_2.Rmd`.
4. Finally run `Tennis_Point_Streaks_Part_3.Rmd`.
5. The third file can regenerate the intermediate CSV files used for earlier Tableau/Shiny-style visualizations.

The generated CSV files are intentionally excluded from GitHub because they can be recreated and some are large.

---

## Connection to the Final Streamlit App

The current Streamlit app builds on this earlier R workflow.

The archive explains how the original streak logic and visual design were developed. The final Streamlit app then translates these ideas into a Python-based interactive application with simulation features.
