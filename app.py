import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ------------------------------------------------------------
# Page setup
# This block configures the Streamlit page title and layout.
# ------------------------------------------------------------
st.set_page_config(
    page_title="Tennis Point Streak Explorer",
    layout="wide"
)


# ------------------------------------------------------------
# Load data
# This block reads the point-level and game-level CSV files.
# It also converts important columns into numeric format.
# ------------------------------------------------------------
@st.cache_data
def load_data():
    points = pd.read_csv("data/points.csv")
    games = pd.read_csv("data/games.csv")

    point_numeric_cols = [
        "SetNo",
        "GameNo",
        "PointNumber",
        "PointWinner",
        "PointServer",
        "P1GamesWon",
        "P2GamesWon",
    ]

    for col in point_numeric_cols:
        if col in points.columns:
            points[col] = pd.to_numeric(points[col], errors="coerce")

    game_numeric_cols = [
        "SetNo",
        "GameNo",
        "game_start",
        "game_end",
    ]

    for col in game_numeric_cols:
        if col in games.columns:
            games[col] = pd.to_numeric(games[col], errors="coerce")

    return points, games


# ------------------------------------------------------------
# Score cleaning helper
# This function removes unnecessary decimals from scores.
# Example: 40.0 becomes 40, while AD stays AD.
# ------------------------------------------------------------
def clean_score_value(x):
    if pd.isna(x):
        return ""

    s = str(x).strip()

    if s.endswith(".0"):
        return s[:-2]

    return s


# ------------------------------------------------------------
# Match label helper
# This function creates readable dropdown labels for matches.
# Example: Player 1 vs Player 2 — match_id
# ------------------------------------------------------------
def get_match_label(points, match_id):
    match_df = points[points["match_id"] == match_id]

    if match_df.empty:
        return str(match_id)

    p1 = match_df["P1_name"].dropna().iloc[0]
    p2 = match_df["P2_name"].dropna().iloc[0]

    return f"{p1} vs {p2} — {match_id}"


# ------------------------------------------------------------
# Prepare actual match data
# This function filters the selected match and creates variables
# needed for plotting, hover labels, and point ordering.
# ------------------------------------------------------------
def prepare_match_points(points, match_id):
    match_df = points[points["match_id"] == match_id].copy()
    match_df = match_df.sort_values(["SetNo", "PointNumber"]).reset_index(drop=True)

    # Create point order within each set.
    match_df["point_in_set"] = match_df.groupby("SetNo").cumcount() + 1

    # Extract player names from the selected match.
    p1 = match_df["P1_name"].dropna().iloc[0]
    p2 = match_df["P2_name"].dropna().iloc[0]

    # Create y-position: Player 1 is shown on top, Player 2 on bottom.
    match_df["winner_y"] = np.where(match_df["PointWinner"] == 1, 1.0, 0.0)

    # Create clean point winner and server names.
    match_df["winner_name_clean"] = np.where(
        match_df["PointWinner"] == 1,
        p1,
        p2
    )

    match_df["server_name_clean"] = np.where(
        match_df["PointServer"] == 1,
        p1,
        np.where(match_df["PointServer"] == 2, p2, "Unknown")
    )

    # Clean tennis score labels for hover text.
    match_df["P1Score_clean"] = match_df["P1Score"].apply(clean_score_value)
    match_df["P2Score_clean"] = match_df["P2Score"].apply(clean_score_value)
    match_df["P1GamesWon_clean"] = match_df["P1GamesWon"].apply(clean_score_value)
    match_df["P2GamesWon_clean"] = match_df["P2GamesWon"].apply(clean_score_value)

    # Create score strings for hover text.
    match_df["game_score"] = match_df["P1Score_clean"] + "-" + match_df["P2Score_clean"]
    match_df["games_in_set"] = match_df["P1GamesWon_clean"] + "-" + match_df["P2GamesWon_clean"]

    # Create hover text for each point.
    match_df["hover_text"] = (
        "<b>Point details</b>"
        + "<br>Set: " + match_df["SetNo"].astype(str)
        + "<br>Game: " + match_df["GameNo"].astype(str)
        + "<br>Point in set: " + match_df["point_in_set"].astype(str)
        + "<br>Game score: " + match_df["game_score"].astype(str)
        + "<br>Games in set: " + match_df["games_in_set"].astype(str)
        + "<br>Point winner: " + match_df["winner_name_clean"].astype(str)
        + "<br>Server: " + match_df["server_name_clean"].astype(str)
    )

    return match_df, p1, p2


# ------------------------------------------------------------
# Count relaxed streaks from a binary sequence
# This function counts non-overlapping streaks in a 0/1 sequence.
# 1 means Player A won the point; 0 means Player A lost the point.
# ------------------------------------------------------------
def count_relaxed_streaks_from_sequence(seq, min_wins=8, allowed_losses=1):
    seq = np.asarray(seq).astype(int)
    n = len(seq)

    count = 0
    start = 0

    while start < n:
        # A streak must start with a point won by Player A.
        while start < n and seq[start] == 0:
            start += 1

        if start >= n:
            break

        wins = 0
        losses = 0
        end = start
        best_end = None

        # Extend the streak while losses stay within the allowed limit.
        while end < n:
            if seq[end] == 1:
                wins += 1
            else:
                losses += 1

            if losses > allowed_losses:
                break

            if wins >= min_wins:
                best_end = end

            end += 1

        # Count the streak and move past it to avoid double-counting.
        if best_end is not None:
            count += 1
            start = best_end + 1
        else:
            start += 1

    return count


# ------------------------------------------------------------
# Detect relaxed streak intervals
# This function returns the start/end points of detected streaks
# for one selected player.
# ------------------------------------------------------------
def find_relaxed_streaks(match_df, player_number, player_name, min_wins=8, allowed_losses=1):
    streaks = []
    streak_id = 1

    for set_no, set_df in match_df.groupby("SetNo"):
        set_df = set_df.sort_values("point_in_set").reset_index(drop=True)

        # Convert actual point winners into a binary sequence for the selected player.
        seq = (set_df["PointWinner"] == player_number).astype(int).values
        point_nums = set_df["point_in_set"].values

        n = len(seq)
        start = 0

        while start < n:
            while start < n and seq[start] == 0:
                start += 1

            if start >= n:
                break

            wins = 0
            losses = 0
            end = start

            best_end = None
            best_wins = 0
            best_losses = 0

            while end < n:
                if seq[end] == 1:
                    wins += 1
                else:
                    losses += 1

                if losses > allowed_losses:
                    break

                if wins >= min_wins:
                    best_end = end
                    best_wins = wins
                    best_losses = losses

                end += 1

            if best_end is not None:
                streaks.append({
                    "streak_id": streak_id,
                    "player_number": player_number,
                    "player_name": player_name,
                    "SetNo": int(set_no),
                    "start_point": int(point_nums[start]),
                    "end_point": int(point_nums[best_end]),
                    "points_won_in_streak": int(best_wins),
                    "points_lost_in_streak": int(best_losses),
                    "duration_points": int(point_nums[best_end] - point_nums[start] + 1),
                })

                streak_id += 1
                start = best_end + 1
            else:
                start += 1

    return pd.DataFrame(streaks)


# ------------------------------------------------------------
# Calculate streaks for the selected visualization option
# This function supports Both / Player 1 / Player 2 selections.
# ------------------------------------------------------------
def calculate_streaks_for_selection(match_df, player_choice, p1, p2, min_wins, allowed_losses):
    if player_choice == "Both":
        streaks_p1 = find_relaxed_streaks(
            match_df=match_df,
            player_number=1,
            player_name=p1,
            min_wins=min_wins,
            allowed_losses=allowed_losses
        )

        streaks_p2 = find_relaxed_streaks(
            match_df=match_df,
            player_number=2,
            player_name=p2,
            min_wins=min_wins,
            allowed_losses=allowed_losses
        )

        return pd.concat([streaks_p1, streaks_p2], ignore_index=True)

    if player_choice == p1:
        return find_relaxed_streaks(
            match_df=match_df,
            player_number=1,
            player_name=p1,
            min_wins=min_wins,
            allowed_losses=allowed_losses
        )

    return find_relaxed_streaks(
        match_df=match_df,
        player_number=2,
        player_name=p2,
        min_wins=min_wins,
        allowed_losses=allowed_losses
    )


# ------------------------------------------------------------
# Count actual streaks for simulation comparison
# This function counts actual streaks for one Player A only.
# It resets streak detection within each set.
# ------------------------------------------------------------
def actual_streak_count_by_player(match_df, player_number, min_wins, allowed_losses):
    total = 0

    for _, set_df in match_df.groupby("SetNo"):
        set_df = set_df.sort_values("point_in_set")
        seq = (set_df["PointWinner"] == player_number).astype(int).values

        total += count_relaxed_streaks_from_sequence(
            seq,
            min_wins=min_wins,
            allowed_losses=allowed_losses
        )

    return total


# ------------------------------------------------------------
# Run binomial simulations
# This function simulates many independent Bernoulli match sequences.
# It also keeps each simulated path so one representative graph can be drawn.
# ------------------------------------------------------------
@st.cache_data
def run_binomial_simulations_with_paths(set_lengths, n_sim, p, min_wins, allowed_losses, seed):
    rng = np.random.default_rng(seed)

    sim_counts = []
    sim_paths = []

    for _ in range(n_sim):
        total_count = 0
        by_set = []

        # Preserve the same number of points in each actual set.
        for set_len in set_lengths:
            seq = rng.binomial(1, p, size=int(set_len))
            by_set.append(seq.tolist())

            total_count += count_relaxed_streaks_from_sequence(
                seq,
                min_wins=min_wins,
                allowed_losses=allowed_losses
            )

        sim_counts.append(total_count)
        sim_paths.append(by_set)

    return np.array(sim_counts), sim_paths


# ------------------------------------------------------------
# Build simulated match dataframe
# This function converts one simulated 0/1 path into a match-like dataframe
# so it can be plotted using the same style as the actual match.
# ------------------------------------------------------------
def build_simulated_match_df(sim_paths, p1, p2, player_a_name):
    player_a_number = 1 if player_a_name == p1 else 2

    rows = []
    global_point = 0

    for set_no, seq in enumerate(sim_paths, start=1):
        for point_in_set, a_win in enumerate(seq, start=1):
            global_point += 1

            if a_win == 1:
                point_winner = player_a_number
            else:
                point_winner = 2 if player_a_number == 1 else 1

            winner_name = p1 if point_winner == 1 else p2
            winner_y = 1.0 if point_winner == 1 else 0.0

            rows.append({
                "SetNo": set_no,
                "PointNumber": global_point,
                "point_in_set": point_in_set,
                "PointWinner": point_winner,
                "winner_y": winner_y,
                "winner_name_clean": winner_name,
            })

    sim_df = pd.DataFrame(rows)

    sim_df["hover_text"] = (
        "<b>Simulated point details</b>"
        + "<br>Set: " + sim_df["SetNo"].astype(str)
        + "<br>Point in set: " + sim_df["point_in_set"].astype(str)
        + "<br>Simulated winner: " + sim_df["winner_name_clean"].astype(str)
        + "<br>Player A: " + str(player_a_name)
    )

    return sim_df


# ------------------------------------------------------------
# Add server shading
# This function uses game-level data to add light background shading
# according to the server in each game.
# ------------------------------------------------------------
def add_server_shading(fig, set_games, row, p1, p2):
    for _, g in set_games.iterrows():
        server = g["server_name"]

        if server == p1:
            color = "rgba(255, 220, 220, 0.18)"
        elif server == p2:
            color = "rgba(220, 235, 255, 0.18)"
        else:
            color = "rgba(230, 230, 230, 0.12)"

        fig.add_shape(
            type="rect",
            x0=g["game_start"] - 0.5,
            x1=g["game_end"] + 0.5,
            y0=-0.25,
            y1=1.25,
            fillcolor=color,
            line=dict(width=0),
            layer="below",
            row=row,
            col=1
        )


# ------------------------------------------------------------
# Add path segment
# This function draws a thick transparent line following the point path.
# It avoids connecting non-consecutive point segments.
# ------------------------------------------------------------
def add_path_segment(fig, path_df, row, color, width):
    if path_df.empty:
        return

    grp = (path_df["point_in_set"].diff().fillna(1) != 1).cumsum()

    for _, seg in path_df.groupby(grp):
        if len(seg) < 2:
            continue

        fig.add_trace(
            go.Scatter(
                x=seg["point_in_set"],
                y=seg["winner_y"],
                mode="lines",
                line=dict(color=color, width=width),
                hoverinfo="skip",
                showlegend=False
            ),
            row=row,
            col=1
        )


# ------------------------------------------------------------
# Add streak shading tubes
# This function adds grey transparent streak shading that follows
# the actual point path. Overlapping streaks become darker.
# ------------------------------------------------------------
def add_streak_tubes(fig, set_df, set_streaks, row):
    if set_streaks.empty:
        return

    # Draw a base light tube for each streak.
    for _, s in set_streaks.iterrows():
        path_df = set_df[
            (set_df["point_in_set"] >= s["start_point"]) &
            (set_df["point_in_set"] <= s["end_point"])
        ].copy()

        add_path_segment(
            fig=fig,
            path_df=path_df,
            row=row,
            color="rgba(90, 90, 90, 0.16)",
            width=14
        )

    # Count how many streaks overlap at each point.
    overlap_df = set_df[["point_in_set", "winner_y"]].copy()
    overlap_df["overlap_n"] = 0

    for _, s in set_streaks.iterrows():
        mask = (
            (overlap_df["point_in_set"] >= s["start_point"]) &
            (overlap_df["point_in_set"] <= s["end_point"])
        )
        overlap_df.loc[mask, "overlap_n"] += 1

    # Darken areas with 2 or more overlapping streaks.
    overlap_2 = overlap_df[overlap_df["overlap_n"] >= 2].copy()
    add_path_segment(
        fig=fig,
        path_df=overlap_2,
        row=row,
        color="rgba(70, 70, 70, 0.26)",
        width=14
    )

    # Darken areas with 3 or more overlapping streaks even more.
    overlap_3 = overlap_df[overlap_df["overlap_n"] >= 3].copy()
    add_path_segment(
        fig=fig,
        path_df=overlap_3,
        row=row,
        color="rgba(45, 45, 45, 0.38)",
        width=14
    )


# ------------------------------------------------------------
# Add streak start/end markers
# Start marker = green vertical line.
# End marker = red horizontal line.
# Markers are placed at the actual point location.
# ------------------------------------------------------------
def add_streak_markers(fig, set_streaks, set_df, row):
    if set_streaks.empty:
        return

    for _, s in set_streaks.iterrows():
        x_start = int(s["start_point"])
        x_end = int(s["end_point"])

        start_rows = set_df[set_df["point_in_set"] == x_start]
        end_rows = set_df[set_df["point_in_set"] == x_end]

        if not start_rows.empty:
            y_start = float(start_rows["winner_y"].iloc[0])
        else:
            y_start = 1.0 if int(s["player_number"]) == 1 else 0.0

        if not end_rows.empty:
            y_end = float(end_rows["winner_y"].iloc[0])
        else:
            y_end = 1.0 if int(s["player_number"]) == 1 else 0.0

        # Draw green vertical start marker.
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_start],
                y=[y_start - 0.14, y_start + 0.14],
                mode="lines",
                line=dict(color="green", width=2),
                hovertemplate=(
                    "Streak Start"
                    + "<br>Player: " + str(s["player_name"])
                    + "<br>Point in set: " + str(x_start)
                    + "<extra></extra>"
                ),
                showlegend=False
            ),
            row=row,
            col=1
        )

        # Draw red horizontal end marker.
        fig.add_trace(
            go.Scatter(
                x=[x_end - 0.38, x_end + 0.38],
                y=[y_end, y_end],
                mode="lines",
                line=dict(color="red", width=2),
                hovertemplate=(
                    "Streak End"
                    + "<br>Player: " + str(s["player_name"])
                    + "<br>Point in set: " + str(x_end)
                    + "<extra></extra>"
                ),
                showlegend=False
            ),
            row=row,
            col=1
        )


# ------------------------------------------------------------
# Create actual match plot
# This function creates the main point-by-point visualization
# for the selected real match.
# ------------------------------------------------------------
def make_point_plot(match_df, match_games, streaks_df, p1, p2, match_id):
    sets = sorted(match_df["SetNo"].dropna().unique())
    n_sets = len(sets)

    fig = make_subplots(
        rows=n_sets,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.055,
        subplot_titles=[f"Set {int(s)}" for s in sets]
    )

    for row, set_no in enumerate(sets, start=1):
        set_df = match_df[match_df["SetNo"] == set_no].copy()
        set_games = match_games[match_games["SetNo"] == set_no].copy()

        if not streaks_df.empty:
            set_streaks = streaks_df[streaks_df["SetNo"] == int(set_no)].copy()
        else:
            set_streaks = pd.DataFrame()

        # Add server background shading.
        add_server_shading(fig, set_games, row, p1, p2)

        # Add streak shading before the black point line.
        add_streak_tubes(fig, set_df, set_streaks, row)

        # Add main point-by-point line and markers.
        fig.add_trace(
            go.Scatter(
                x=set_df["point_in_set"],
                y=set_df["winner_y"],
                mode="lines+markers",
                line=dict(color="black", width=1.4),
                marker=dict(color="black", size=5),
                text=set_df["hover_text"],
                hovertemplate="%{text}<extra></extra>",
                showlegend=False
            ),
            row=row,
            col=1
        )

        # Add start/end markers after the main line.
        add_streak_markers(fig, set_streaks, set_df, row)

        # Format y-axis with actual player names.
        fig.update_yaxes(
            tickvals=[0, 1],
            ticktext=[p2, p1],
            range=[-0.25, 1.25],
            tickfont=dict(size=13, color="black"),
            row=row,
            col=1
        )

        # Hide x-axis tick labels to keep the plot clean.
        fig.update_xaxes(
            showticklabels=False,
            ticks="",
            title_text="",
            showgrid=False,
            zeroline=False,
            row=row,
            col=1
        )

    fig.update_layout(
        title=dict(
            text=f"{p1} vs {p2} — {match_id}",
            x=0.5,
            xanchor="center",
            font=dict(size=24, color="black")
        ),
        height=max(650, 175 * n_sets),
        margin=dict(l=130, r=40, t=90, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="black"),
    )

    fig.update_annotations(font=dict(size=15, color="black"))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")

    return fig


# ------------------------------------------------------------
# Create simulated match plot
# This function creates a point-by-point visualization for one
# representative simulated Bernoulli match.
# ------------------------------------------------------------
def make_simulated_point_plot(sim_df, sim_streaks_df, p1, p2, player_a_name, p, rep_count):
    sets = sorted(sim_df["SetNo"].dropna().unique())
    n_sets = len(sets)

    fig = make_subplots(
        rows=n_sets,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.055,
        subplot_titles=[f"Set {int(s)}" for s in sets]
    )

    for row, set_no in enumerate(sets, start=1):
        set_df = sim_df[sim_df["SetNo"] == set_no].copy()

        if not sim_streaks_df.empty:
            set_streaks = sim_streaks_df[sim_streaks_df["SetNo"] == int(set_no)].copy()
        else:
            set_streaks = pd.DataFrame()

        # Add simulated streak shading.
        add_streak_tubes(fig, set_df, set_streaks, row)

        # Add simulated point-by-point line.
        fig.add_trace(
            go.Scatter(
                x=set_df["point_in_set"],
                y=set_df["winner_y"],
                mode="lines+markers",
                line=dict(color="black", width=1.4),
                marker=dict(color="black", size=5),
                text=set_df["hover_text"],
                hovertemplate="%{text}<extra></extra>",
                showlegend=False
            ),
            row=row,
            col=1
        )

        # Add simulated streak start/end markers.
        add_streak_markers(fig, set_streaks, set_df, row)

        fig.update_yaxes(
            tickvals=[0, 1],
            ticktext=[p2, p1],
            range=[-0.25, 1.25],
            tickfont=dict(size=13, color="black"),
            row=row,
            col=1
        )

        fig.update_xaxes(
            showticklabels=False,
            ticks="",
            title_text="",
            showgrid=False,
            zeroline=False,
            row=row,
            col=1
        )

    fig.update_layout(
        title=dict(
            text=(
                f"Representative Simulated Match — Player A: {player_a_name}, "
                f"p = {p:.2f}, simulated streaks = {rep_count}"
            ),
            x=0.5,
            xanchor="center",
            font=dict(size=22, color="black")
        ),
        height=max(650, 175 * n_sets),
        margin=dict(l=130, r=40, t=90, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="black"),
    )

    fig.update_annotations(font=dict(size=15, color="black"))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")

    return fig


# ------------------------------------------------------------
# Main app: data loading
# This block loads data and prepares the sidebar controls.
# ------------------------------------------------------------
points, games = load_data()

st.sidebar.title("Tennis Point Streak Explorer")

st.sidebar.header("Match Visualization Controls")

match_ids = sorted(points["match_id"].dropna().unique())

match_label_map = {
    get_match_label(points, match_id): match_id
    for match_id in match_ids
}

selected_match_label = st.sidebar.selectbox(
    "Choose Match:",
    list(match_label_map.keys())
)

selected_match_id = match_label_map[selected_match_label]

match_df, p1, p2 = prepare_match_points(points, selected_match_id)
match_games = games[games["match_id"] == selected_match_id].copy()


# ------------------------------------------------------------
# Sidebar: actual match controls
# This block controls the actual match visualization.
# ------------------------------------------------------------
player_choice = st.sidebar.selectbox(
    "Choose Player(s):",
    ["Both", p1, p2]
)

min_length = st.sidebar.selectbox(
    "Minimum Wins in Streak:",
    list(range(3, 16)),
    index=5
)

allowed_losses = st.sidebar.selectbox(
    "Allowed Losses:",
    [0, 1, 2, 3],
    index=1
)


# ------------------------------------------------------------
# Sidebar: simulation controls
# This block controls the binomial independent-process simulation.
# ------------------------------------------------------------
st.sidebar.divider()

st.sidebar.header("Binomial Simulation Controls")

sim_player = st.sidebar.selectbox(
    "Player A for Simulation:",
    [p1, p2]
)

n_sim = st.sidebar.selectbox(
    "Number of Simulations:",
    [500, 1000, 5000, 10000],
    index=1
)

p_sim = st.sidebar.number_input(
    "Probability of Success for Player A:",
    min_value=0.00,
    max_value=1.00,
    value=0.50,
    step=0.01
)

seed = st.sidebar.number_input(
    "Random Seed:",
    min_value=1,
    max_value=999999,
    value=123,
    step=1
)

run_sim = st.sidebar.button("Run Binomial Simulation")


# ------------------------------------------------------------
# Actual match streak calculation
# This block calculates streaks for the selected actual match.
# ------------------------------------------------------------
streaks_df = calculate_streaks_for_selection(
    match_df=match_df,
    player_choice=player_choice,
    p1=p1,
    p2=p2,
    min_wins=min_length,
    allowed_losses=allowed_losses
)


# ------------------------------------------------------------
# Main page: actual match section
# This block displays the selected match metrics and graph.
# ------------------------------------------------------------
st.title("Tennis Point Streak Explorer")

st.markdown(
    f"""
    **Selected match:** `{selected_match_id}`  
    **Players:** {p1} vs {p2}  
    **Player selection:** {player_choice}  
    **Minimum wins:** {min_length}  
    **Allowed losses:** {allowed_losses}
    """
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Match Points", len(match_df))

with col2:
    st.metric("Sets", match_df["SetNo"].nunique())

with col3:
    st.metric("Actual Streaks", len(streaks_df))

actual_fig = make_point_plot(
    match_df=match_df,
    match_games=match_games,
    streaks_df=streaks_df,
    p1=p1,
    p2=p2,
    match_id=selected_match_id
)

st.plotly_chart(actual_fig, use_container_width=True)


# ------------------------------------------------------------
# Main page: simulation section
# This block calculates and displays simulation metrics and graph.
# ------------------------------------------------------------
st.divider()
st.subheader("Binomial Independent Process Simulation")

sim_player_number = 1 if sim_player == p1 else 2

actual_sim_count = actual_streak_count_by_player(
    match_df=match_df,
    player_number=sim_player_number,
    min_wins=min_length,
    allowed_losses=allowed_losses
)

set_lengths = tuple(
    int(len(set_df))
    for _, set_df in match_df.groupby("SetNo")
)

sim_col1, sim_col2, sim_col3 = st.columns(3)

with sim_col1:
    st.metric("Simulation Player", sim_player)

with sim_col2:
    st.metric("Actual Player Streaks", actual_sim_count)

with sim_col3:
    st.metric("Point Win Probability", f"{p_sim:.2f}")


# ------------------------------------------------------------
# Run simulation after button click
# This block runs all simulations, selects one representative path,
# and draws the simulated match graph.
# ------------------------------------------------------------
if run_sim:
    sim_counts, sim_paths_all = run_binomial_simulations_with_paths(
        set_lengths=set_lengths,
        n_sim=int(n_sim),
        p=float(p_sim),
        min_wins=int(min_length),
        allowed_losses=int(allowed_losses),
        seed=int(seed)
    )

    prob_at_least_actual = float(np.mean(sim_counts >= actual_sim_count))

    # Select the representative simulation closest to the median simulated streak count.
    sim_median = np.median(sim_counts)
    rep_idx = int(np.argmin(np.abs(sim_counts - sim_median)))

    rep_paths = sim_paths_all[rep_idx]
    rep_count = int(sim_counts[rep_idx])

    sim_match_df = build_simulated_match_df(
        sim_paths=rep_paths,
        p1=p1,
        p2=p2,
        player_a_name=sim_player
    )

    sim_streaks_df = find_relaxed_streaks(
        match_df=sim_match_df,
        player_number=sim_player_number,
        player_name=sim_player,
        min_wins=min_length,
        allowed_losses=allowed_losses
    )

    result_col1, result_col2, result_col3, result_col4 = st.columns(4)

    with result_col1:
        st.metric("Mean Simulated Streaks", f"{np.mean(sim_counts):.2f}")

    with result_col2:
        st.metric("Median Simulated Streaks", f"{np.median(sim_counts):.0f}")

    with result_col3:
        st.metric("Representative Simulation Streaks", rep_count)

    with result_col4:
        st.metric("P(Sim ≥ Actual)", f"{prob_at_least_actual:.3f}")

    sim_fig = make_simulated_point_plot(
        sim_df=sim_match_df,
        sim_streaks_df=sim_streaks_df,
        p1=p1,
        p2=p2,
        player_a_name=sim_player,
        p=float(p_sim),
        rep_count=rep_count
    )

    st.plotly_chart(sim_fig, use_container_width=True)

    st.caption(
        f"Simulation note: Each simulated point is an independent Bernoulli trial for Player A "
        f"with p = {p_sim:.2f}. The simulated match uses the same set lengths as the selected match, "
        f"and streaks are counted using the same minimum wins ({min_length}) and allowed losses ({allowed_losses}) settings."
    )

else:
    st.info("Click **Run Binomial Simulation** to generate simulation results.")


# ------------------------------------------------------------
# Optional data tables
# This block keeps the raw tables available for checking/debugging.
# ------------------------------------------------------------
with st.expander("View detected streaks table"):
    if streaks_df.empty:
        st.write("No streaks detected with the selected parameters.")
    else:
        st.dataframe(streaks_df, use_container_width=True)

with st.expander("Preview selected match data"):
    st.dataframe(match_df.head(30), use_container_width=True)