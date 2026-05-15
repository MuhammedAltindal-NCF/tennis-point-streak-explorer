import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ------------------------------------------------------------
# Page setup
# ------------------------------------------------------------
st.set_page_config(
    page_title="Tennis Point Streak Explorer",
    layout="wide"
)


# ------------------------------------------------------------
# Load data
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
# ------------------------------------------------------------
def prepare_match_points(points, match_id):
    match_df = points[points["match_id"] == match_id].copy()
    match_df = match_df.sort_values(["SetNo", "PointNumber"]).reset_index(drop=True)

    match_df["point_in_set"] = match_df.groupby("SetNo").cumcount() + 1

    p1 = match_df["P1_name"].dropna().iloc[0]
    p2 = match_df["P2_name"].dropna().iloc[0]

    match_df["winner_y"] = np.where(match_df["PointWinner"] == 1, 1.0, 0.0)

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

    match_df["P1Score_clean"] = match_df["P1Score"].apply(clean_score_value)
    match_df["P2Score_clean"] = match_df["P2Score"].apply(clean_score_value)
    match_df["P1GamesWon_clean"] = match_df["P1GamesWon"].apply(clean_score_value)
    match_df["P2GamesWon_clean"] = match_df["P2GamesWon"].apply(clean_score_value)

    match_df["game_score"] = match_df["P1Score_clean"] + "-" + match_df["P2Score_clean"]
    match_df["games_in_set"] = match_df["P1GamesWon_clean"] + "-" + match_df["P2GamesWon_clean"]

    match_df["hover_text"] = (
        "Game: " + match_df["GameNo"].astype(str)
        + "<br>Point in set: " + match_df["point_in_set"].astype(str)
        + "<br>Game score: " + match_df["game_score"].astype(str)
        + "<br>Games in set: " + match_df["games_in_set"].astype(str)
    )

    return match_df, p1, p2


# ------------------------------------------------------------
# Non-overlapping relaxed streak detection
# ------------------------------------------------------------
def detect_relaxed_streaks_in_sequence(seq, point_nums=None, min_wins=8, allowed_losses=1):
    """
    Detect relaxed streaks using sequential non-overlapping logic.

    Rules:
    - A streak must start with a point won by the streaking player.
    - The streak is extended as far as possible while losses <= allowed_losses.
    - After a valid streak is saved:
        * If the streak contains no loss, the next search starts after the streak ends.
        * If the streak contains a loss, the next search starts after the first lost point
          inside that streak.

    This prevents a pure 8-point consecutive run from being counted as multiple
    overlapping 6-point streaks, while still allowing limited relaxed-streak overlap
    only after an interruption point.
    """

    seq = np.asarray(seq).astype(int)
    n = len(seq)

    if point_nums is None:
        point_nums = np.arange(1, n + 1)
    else:
        point_nums = np.asarray(point_nums)

    streaks = []
    start = 0

    while start < n:
        if seq[start] != 1:
            start += 1
            continue

        wins = 0
        losses = 0
        best_end = None
        best_wins = None
        best_losses = None

        for end in range(start, n):
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

        if best_end is None:
            start += 1
            continue

        streaks.append({
            "start_index": int(start),
            "end_index": int(best_end),
            "start_point": int(point_nums[start]),
            "end_point": int(point_nums[best_end]),
            "points_won_in_streak": int(best_wins),
            "points_lost_in_streak": int(best_losses),
            "duration_points": int(best_end - start + 1),
        })

        segment = seq[start:best_end + 1]
        loss_positions = np.where(segment == 0)[0]

        if len(loss_positions) == 0:
            start = best_end + 1
        else:
            start = start + int(loss_positions[0]) + 1

    return streaks


# ------------------------------------------------------------
# Count relaxed streaks from a binary sequence
# ------------------------------------------------------------
def count_relaxed_streaks_from_sequence(seq, min_wins=8, allowed_losses=1):
    streaks = detect_relaxed_streaks_in_sequence(
        seq=seq,
        point_nums=None,
        min_wins=min_wins,
        allowed_losses=allowed_losses
    )

    return len(streaks)


# ------------------------------------------------------------
# Count streaks for Player A only or both players
# ------------------------------------------------------------
def count_streaks_for_scope(seq, min_wins=8, allowed_losses=1, scope="Player A only"):
    seq = np.asarray(seq).astype(int)

    count_a = count_relaxed_streaks_from_sequence(
        seq=seq,
        min_wins=min_wins,
        allowed_losses=allowed_losses
    )

    if scope == "Player A only":
        return count_a

    opponent_seq = 1 - seq

    count_b = count_relaxed_streaks_from_sequence(
        seq=opponent_seq,
        min_wins=min_wins,
        allowed_losses=allowed_losses
    )

    return count_a + count_b


# ------------------------------------------------------------
# Detect relaxed streak intervals for one selected player
# ------------------------------------------------------------
def find_relaxed_streaks(match_df, player_number, player_name, min_wins=8, allowed_losses=1):
    streaks = []
    streak_id = 1

    for set_no, set_df in match_df.groupby("SetNo"):
        set_df = set_df.sort_values("point_in_set").reset_index(drop=True)

        seq = (set_df["PointWinner"] == player_number).astype(int).values
        point_nums = set_df["point_in_set"].values

        detected = detect_relaxed_streaks_in_sequence(
            seq=seq,
            point_nums=point_nums,
            min_wins=min_wins,
            allowed_losses=allowed_losses
        )

        for s in detected:
            streaks.append({
                "streak_id": streak_id,
                "player_number": player_number,
                "player_name": player_name,
                "SetNo": int(set_no),
                "start_point": int(s["start_point"]),
                "end_point": int(s["end_point"]),
                "points_won_in_streak": int(s["points_won_in_streak"]),
                "points_lost_in_streak": int(s["points_lost_in_streak"]),
                "duration_points": int(s["duration_points"]),
            })

            streak_id += 1

    return pd.DataFrame(streaks)


# ------------------------------------------------------------
# Calculate streaks for the selected visualization option
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
# Actual streak count for simulation comparison
# ------------------------------------------------------------
def actual_streak_count_for_scope(match_df, player_number, min_wins, allowed_losses, scope):
    total = 0

    for _, set_df in match_df.groupby("SetNo"):
        set_df = set_df.sort_values("point_in_set")
        seq = (set_df["PointWinner"] == player_number).astype(int).values

        total += count_streaks_for_scope(
            seq=seq,
            min_wins=min_wins,
            allowed_losses=allowed_losses,
            scope=scope
        )

    return total


# ------------------------------------------------------------
# Estimate server win rate across all matches
# ------------------------------------------------------------
def estimate_server_win_rate(df):
    valid = df[
        df["PointServer"].isin([1, 2]) &
        df["PointWinner"].isin([1, 2])
    ].copy()

    if valid.empty:
        return 0.50

    server_won = valid["PointServer"] == valid["PointWinner"]
    return float(server_won.mean())


# ------------------------------------------------------------
# Prepare server sequences by set for the selected match
# ------------------------------------------------------------
def get_server_sequences_by_set(match_df):
    server_sequences = []

    for _, set_df in match_df.groupby("SetNo"):
        set_df = set_df.sort_values("point_in_set")
        server_sequences.append(tuple(set_df["PointServer"].fillna(0).astype(int).values))

    return tuple(server_sequences)


# ------------------------------------------------------------
# Run binomial simulations
# ------------------------------------------------------------
def run_binomial_simulations_with_paths(
    set_lengths,
    server_sequences,
    player_a_number,
    n_sim,
    p,
    min_wins,
    allowed_losses,
    seed,
    scope,
    simulation_model,
    serve_advantage
):
    rng = np.random.default_rng(seed)

    sim_counts = []
    sim_paths = []
    sim_prob_paths = []

    for _ in range(n_sim):
        total_count = 0
        by_set = []
        probs_by_set = []

        for set_idx, set_len in enumerate(set_lengths):
            set_len = int(set_len)

            if simulation_model == "Serve-adjusted Bernoulli":
                servers = np.asarray(server_sequences[set_idx]).astype(int)

                # Player A receives a probability increase when Player A serves.
                # Player A receives a probability decrease when the opponent serves.
                probs = np.where(
                    servers == player_a_number,
                    p + serve_advantage,
                    p - serve_advantage
                )

                # Unknown server values fall back to the base probability.
                probs = np.where(np.isin(servers, [1, 2]), probs, p)

                # Keep probabilities valid.
                probs = np.clip(probs, 0.0, 1.0)

                seq = rng.binomial(1, probs)
            else:
                probs = np.repeat(p, set_len)
                seq = rng.binomial(1, probs)

            by_set.append(seq.tolist())
            probs_by_set.append(probs.tolist())

            total_count += count_streaks_for_scope(
                seq=seq,
                min_wins=min_wins,
                allowed_losses=allowed_losses,
                scope=scope
            )

        sim_counts.append(total_count)
        sim_paths.append(by_set)
        sim_prob_paths.append(probs_by_set)

    return np.array(sim_counts), sim_paths, sim_prob_paths

# ------------------------------------------------------------
# Build simulated match dataframe
# ------------------------------------------------------------
def build_simulated_match_df(sim_paths, sim_prob_paths, server_sequences, p1, p2, player_a_name):
    player_a_number = 1 if player_a_name == p1 else 2

    rows = []
    global_point = 0

    for set_no, seq in enumerate(sim_paths, start=1):
        servers = server_sequences[set_no - 1]
        probs = sim_prob_paths[set_no - 1]

        for point_in_set, a_win in enumerate(seq, start=1):
            global_point += 1

            if a_win == 1:
                point_winner = player_a_number
            else:
                point_winner = 2 if player_a_number == 1 else 1

            server_number = int(servers[point_in_set - 1])
            prob_player_a_wins = float(probs[point_in_set - 1])

            winner_name = p1 if point_winner == 1 else p2
            server_name = p1 if server_number == 1 else p2 if server_number == 2 else "Unknown"
            winner_y = 1.0 if point_winner == 1 else 0.0

            rows.append({
                "SetNo": set_no,
                "PointNumber": global_point,
                "point_in_set": point_in_set,
                "PointWinner": point_winner,
                "PointServer": server_number,
                "winner_y": winner_y,
                "winner_name_clean": winner_name,
                "server_name_clean": server_name,
                "prob_player_a_wins": prob_player_a_wins,
            })

    sim_df = pd.DataFrame(rows)

    sim_df["hover_text"] = (
        "Point in set: " + sim_df["point_in_set"].astype(str)
        + "<br>Winner: " + sim_df["winner_name_clean"].astype(str)
        + "<br>Server: " + sim_df["server_name_clean"].astype(str)
        + "<br>Player A: " + str(player_a_name)
        + "<br>P(Player A wins): " + sim_df["prob_player_a_wins"].round(3).astype(str)
    )

    return sim_df

# ------------------------------------------------------------
# Calculate simulated streaks for plotting
# ------------------------------------------------------------
def calculate_simulated_streaks_for_scope(
    sim_df,
    p1,
    p2,
    sim_player,
    min_wins,
    allowed_losses,
    scope
):
    sim_player_number = 1 if sim_player == p1 else 2

    if scope == "Player A only":
        return find_relaxed_streaks(
            match_df=sim_df,
            player_number=sim_player_number,
            player_name=sim_player,
            min_wins=min_wins,
            allowed_losses=allowed_losses
        )

    streaks_p1 = find_relaxed_streaks(
        match_df=sim_df,
        player_number=1,
        player_name=p1,
        min_wins=min_wins,
        allowed_losses=allowed_losses
    )

    streaks_p2 = find_relaxed_streaks(
        match_df=sim_df,
        player_number=2,
        player_name=p2,
        min_wins=min_wins,
        allowed_losses=allowed_losses
    )

    return pd.concat([streaks_p1, streaks_p2], ignore_index=True)


# ------------------------------------------------------------
# Add server shading
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
# Add service legend annotations
# ------------------------------------------------------------
def add_service_legend(fig, p1, p2):
    fig.add_annotation(
        x=0.99,
        y=1.105,
        xref="paper",
        yref="paper",
        text=f"{p1} served",
        showarrow=False,
        xanchor="right",
        yanchor="top",
        font=dict(size=11, color="black"),
        bgcolor="rgba(255, 220, 220, 0.95)",
        bordercolor="rgba(180, 180, 180, 0.8)",
        borderwidth=1
    )

    fig.add_annotation(
        x=0.99,
        y=1.07,
        xref="paper",
        yref="paper",
        text=f"{p2} served",
        showarrow=False,
        xanchor="right",
        yanchor="top",
        font=dict(size=11, color="black"),
        bgcolor="rgba(220, 235, 255, 0.95)",
        bordercolor="rgba(180, 180, 180, 0.8)",
        borderwidth=1
    )


# ------------------------------------------------------------
# Add path segment
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
# ------------------------------------------------------------
def add_streak_tubes(fig, set_df, set_streaks, row):
    if set_streaks.empty:
        return

    for _, s in set_streaks.iterrows():
        path_df = set_df[
            (set_df["point_in_set"] >= s["start_point"]) &
            (set_df["point_in_set"] <= s["end_point"])
        ].copy()

        add_path_segment(
            fig=fig,
            path_df=path_df,
            row=row,
            color="rgba(90, 90, 90, 0.13)",
            width=12
        )

    overlap_df = set_df[["point_in_set", "winner_y"]].copy()
    overlap_df["overlap_n"] = 0

    for _, s in set_streaks.iterrows():
        mask = (
            (overlap_df["point_in_set"] >= s["start_point"]) &
            (overlap_df["point_in_set"] <= s["end_point"])
        )
        overlap_df.loc[mask, "overlap_n"] += 1

    overlap_2 = overlap_df[overlap_df["overlap_n"] >= 2].copy()
    add_path_segment(
        fig=fig,
        path_df=overlap_2,
        row=row,
        color="rgba(70, 70, 70, 0.22)",
        width=12
    )

    overlap_3 = overlap_df[overlap_df["overlap_n"] >= 3].copy()
    add_path_segment(
        fig=fig,
        path_df=overlap_3,
        row=row,
        color="rgba(45, 45, 45, 0.34)",
        width=12
    )


# ------------------------------------------------------------
# Add streak start/end markers
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

        fig.add_trace(
            go.Scatter(
                x=[x_start, x_start],
                y=[y_start - 0.13, y_start + 0.13],
                mode="lines",
                line=dict(color="green", width=2),
                hovertemplate=(
                    "Streak Start"
                    + "<br>Player: " + str(s["player_name"])
                    + "<br>Point in set: " + str(x_start)
                    + "<br>Wins in streak: " + str(s["points_won_in_streak"])
                    + "<br>Losses used: " + str(s["points_lost_in_streak"])
                    + "<extra></extra>"
                ),
                showlegend=False
            ),
            row=row,
            col=1
        )

        fig.add_trace(
            go.Scatter(
                x=[x_end - 0.32, x_end + 0.32],
                y=[y_end, y_end],
                mode="lines",
                line=dict(color="red", width=2),
                hovertemplate=(
                    "Streak End"
                    + "<br>Player: " + str(s["player_name"])
                    + "<br>Point in set: " + str(x_end)
                    + "<br>Duration: " + str(s["duration_points"]) + " points"
                    + "<extra></extra>"
                ),
                showlegend=False
            ),
            row=row,
            col=1
        )


# ------------------------------------------------------------
# Create actual match plot
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

        add_server_shading(fig, set_games, row, p1, p2)
        add_streak_tubes(fig, set_df, set_streaks, row)

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
            text=f"{p1} vs {p2} — {match_id}",
            x=0.5,
            xanchor="center",
            font=dict(size=24, color="black")
        ),
        height=max(650, 175 * n_sets),
        margin=dict(l=130, r=40, t=115, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="black"),
    )

    fig.update_annotations(font=dict(size=15, color="black"))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")

    add_service_legend(fig, p1, p2)

    return fig


# ------------------------------------------------------------
# Create simulated match plot
# ------------------------------------------------------------
def make_simulated_point_plot(
    sim_df,
    sim_streaks_df,
    match_games,
    p1,
    p2,
    player_a_name,
    p,
    rep_count,
    simulation_model,
    scope
):
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
        set_games = match_games[match_games["SetNo"] == set_no].copy()

        if not sim_streaks_df.empty:
            set_streaks = sim_streaks_df[sim_streaks_df["SetNo"] == int(set_no)].copy()
        else:
            set_streaks = pd.DataFrame()

        # Keep the same actual server shading in the simulated match.
        add_server_shading(fig, set_games, row, p1, p2)
        add_streak_tubes(fig, set_df, set_streaks, row)

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
                f"model = {simulation_model}, scope = {scope}, "
                f"simulated streaks = {rep_count}"
            ),
            x=0.5,
            xanchor="center",
            font=dict(size=18, color="black")
        ),
        height=max(650, 175 * n_sets),
        margin=dict(l=130, r=40, t=115, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="black"),
    )

    fig.update_annotations(font=dict(size=15, color="black"))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")

    add_service_legend(fig, p1, p2)

    return fig


# ------------------------------------------------------------
# Create simulation histogram
# ------------------------------------------------------------
def make_simulation_histogram(sim_counts, actual_count):
    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=sim_counts,
            nbinsx=max(5, min(30, len(np.unique(sim_counts)))),
            name="Simulated streak counts"
        )
    )

    fig.add_vline(
        x=actual_count,
        line_dash="dash",
        line_width=3,
        annotation_text="Actual",
        annotation_position="top right"
    )

    fig.update_layout(
        title="Distribution of Simulated Streak Counts",
        xaxis_title="Number of streaks in simulated match",
        yaxis_title="Frequency",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="black"),
        height=420,
        margin=dict(l=60, r=40, t=70, b=60)
    )

    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")

    return fig


# ------------------------------------------------------------
# Main app: data loading
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

st.sidebar.caption(
    "Streak detection uses the sequential non-overlapping rule: pure consecutive runs "
    "do not restart until the previous run is broken; relaxed streaks may restart only "
    "after the first allowed loss inside the previous streak."
)


# ------------------------------------------------------------
# Sidebar: simulation controls
# ------------------------------------------------------------
st.sidebar.divider()

st.sidebar.header("Binomial Simulation Controls")

sim_player = st.sidebar.selectbox(
    "Player A for Simulation:",
    [p1, p2]
)

sim_scope = st.sidebar.selectbox(
    "Streaks Counted in Simulation:",
    ["Player A only", "Both players"]
)

n_sim = st.sidebar.number_input(
    "Number of Simulations (1 = simulate one match):",
    min_value=1,
    max_value=10000,
    value=1000,
    step=1
)

p_sim = st.sidebar.number_input(
    "Base Probability of Success for Player A:",
    min_value=0.00,
    max_value=1.00,
    value=0.50,
    step=0.01
)

simulation_model = st.sidebar.selectbox(
    "Simulation Model:",
    ["Simple independent Bernoulli", "Serve-adjusted Bernoulli"]
)

overall_server_win_rate = estimate_server_win_rate(points)
estimated_serve_advantage = overall_server_win_rate - 0.50
estimated_serve_advantage = max(float(estimated_serve_advantage), 0.0)

serve_advantage = 0.0

if simulation_model == "Serve-adjusted Bernoulli":
    st.sidebar.caption(
        f"Overall server win rate across all matches: {overall_server_win_rate:.3f}. "
        f"Estimated serve advantage: {estimated_serve_advantage:.3f}."
    )

    serve_advantage = st.sidebar.number_input(
        "Serve Advantage Used (+/-):",
        min_value=0.000,
        max_value=0.250,
        value=float(round(estimated_serve_advantage, 3)),
        step=0.005,
        format="%.3f"
    )

    st.sidebar.caption(
        "This value is added to Player A's point-win probability when Player A served "
        "that point, and subtracted when Player A returned."
    )

use_seed = st.sidebar.checkbox(
    "Use random seed for reproducibility",
    value=False
)

if use_seed:
    seed = st.sidebar.number_input(
        "Random Seed:",
        min_value=1,
        max_value=999999,
        value=123,
        step=1
    )
    seed_value = int(seed)
else:
    seed_value = None

run_sim = st.sidebar.button("Run Binomial Simulation")


# ------------------------------------------------------------
# Actual match streak calculation
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
# ------------------------------------------------------------
st.divider()
st.subheader("Binomial Independent Process Simulation")

sim_player_number = 1 if sim_player == p1 else 2

actual_sim_count = actual_streak_count_for_scope(
    match_df=match_df,
    player_number=sim_player_number,
    min_wins=min_length,
    allowed_losses=allowed_losses,
    scope=sim_scope
)

set_lengths = tuple(
    int(len(set_df))
    for _, set_df in match_df.groupby("SetNo")
)

server_sequences = get_server_sequences_by_set(match_df)

sim_col1, sim_col2, sim_col3, sim_col4 = st.columns(4)

with sim_col1:
    st.metric("Simulation Player A", sim_player)

with sim_col2:
    st.metric("Counting Scope", sim_scope)

with sim_col3:
    st.metric("Actual Streaks for Scope", actual_sim_count)

with sim_col4:
    st.metric("Base Win Probability", f"{p_sim:.2f}")

if simulation_model == "Serve-adjusted Bernoulli":
    st.markdown(
        f"""
        **Simulation model:** Serve-adjusted Bernoulli  
        **Overall server win rate across all matches:** {overall_server_win_rate:.3f}  
        **Estimated serve advantage:** {estimated_serve_advantage:.3f}  
        **Serve advantage used:** {serve_advantage:.3f}  
        **Player A serving probability:** {min(max(p_sim + serve_advantage, 0), 1):.3f}  
        **Player A returning probability:** {min(max(p_sim - serve_advantage, 0), 1):.3f}  
        """
    )

    st.caption(
        "The simulation preserves the selected match's actual set lengths and point-by-point "
        "server sequence. The red/blue serve regions in the simulated plot are therefore the same "
        "as the actual match. Only the point winners are randomly generated."
    )
else:
    st.markdown(
        """
        **Simulation model:** Simple independent Bernoulli  
        Each point is simulated independently with the same base probability.
        """
    )


# ------------------------------------------------------------
# Run simulation after button click
# ------------------------------------------------------------
if run_sim:
    sim_counts, sim_paths_all, sim_prob_paths_all = run_binomial_simulations_with_paths(
        set_lengths=set_lengths,
        server_sequences=server_sequences,
        player_a_number=sim_player_number,
        n_sim=int(n_sim),
        p=float(p_sim),
        min_wins=int(min_length),
        allowed_losses=int(allowed_losses),
        seed=seed_value,
        scope=sim_scope,
        simulation_model=simulation_model,
        serve_advantage=float(serve_advantage)
    )

    prob_at_least_actual = float(np.mean(sim_counts >= actual_sim_count))

    sim_median = np.median(sim_counts)
    rep_idx = int(np.argmin(np.abs(sim_counts - sim_median)))

    rep_paths = sim_paths_all[rep_idx]
    rep_prob_paths = sim_prob_paths_all[rep_idx]
    rep_count = int(sim_counts[rep_idx])

    sim_match_df = build_simulated_match_df(
        sim_paths=rep_paths,
        sim_prob_paths=rep_prob_paths,
        server_sequences=server_sequences,
        p1=p1,
        p2=p2,
        player_a_name=sim_player
    )

    sim_streaks_df = calculate_simulated_streaks_for_scope(
        sim_df=sim_match_df,
        p1=p1,
        p2=p2,
        sim_player=sim_player,
        min_wins=min_length,
        allowed_losses=allowed_losses,
        scope=sim_scope
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

    if int(n_sim) > 1:
        hist_fig = make_simulation_histogram(
            sim_counts=sim_counts,
            actual_count=actual_sim_count
        )

        st.plotly_chart(hist_fig, use_container_width=True)
    else:
        st.info(
            "Only one simulation was run, so the histogram is not very informative. "
            "Increase the number of simulations to see the simulated streak-count distribution."
        )

    sim_fig = make_simulated_point_plot(
        sim_df=sim_match_df,
        sim_streaks_df=sim_streaks_df,
        match_games=match_games,
        p1=p1,
        p2=p2,
        player_a_name=sim_player,
        p=float(p_sim),
        rep_count=rep_count,
        simulation_model=simulation_model,
        scope=sim_scope
    )

    st.plotly_chart(sim_fig, use_container_width=True)

    if simulation_model == "Serve-adjusted Bernoulli":
        st.caption(
            f"Simulation note: Each simulated point is an independent Bernoulli trial for Player A. "
            f"The base probability is p = {p_sim:.2f}. The selected match's actual server sequence "
            f"is preserved point-by-point. When Player A served in that sequence, the simulation used "
            f"p + serve advantage = {min(max(p_sim + serve_advantage, 0), 1):.3f}. "
            f"When Player A returned, it used p - serve advantage = "
            f"{min(max(p_sim - serve_advantage, 0), 1):.3f}. "
            f"Streaks are counted using minimum wins = {min_length}, allowed losses = "
            f"{allowed_losses}, and scope = {sim_scope}."
        )
    else:
        st.caption(
            f"Simulation note: Each simulated point is an independent Bernoulli trial for Player A "
            f"with p = {p_sim:.2f}. The simulated match uses the same set lengths as the selected match, "
            f"and streaks are counted using minimum wins = {min_length}, allowed losses = "
            f"{allowed_losses}, and scope = {sim_scope}."
        )

else:
    st.info("Click **Run Binomial Simulation** to generate simulation results.")


# ------------------------------------------------------------
# Optional data tables
# ------------------------------------------------------------
with st.expander("View detected streaks table"):
    if streaks_df.empty:
        st.write("No streaks detected with the selected parameters.")
    else:
        st.dataframe(streaks_df, use_container_width=True)

with st.expander("Preview selected match data"):
    st.dataframe(match_df.head(30), use_container_width=True)