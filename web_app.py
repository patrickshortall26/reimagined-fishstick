import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

st.set_page_config(page_title="Snooker Game Visualizer", layout="wide")
st.title("Snooker Game Data Visualization")

# Session state for file upload
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None

if st.session_state.uploaded_file:
    uploaded_file = st.session_state.uploaded_file
else:
    uploaded_file = st.file_uploader("Upload the Excel file", type=["xlsx"])
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file

if uploaded_file:
    excel = pd.ExcelFile(uploaded_file)
    game_df = pd.read_excel(excel, sheet_name="Game view")
    player_keys_df = pd.read_excel(excel, sheet_name="PlayerKeys")

    # Merge player names
    id_to_name = player_keys_df.set_index("ID")["Name"].to_dict()
    game_df["Player 1 Name"] = game_df["Player 1"].map(id_to_name)
    game_df["Player 2 Name"] = game_df["Player 2"].map(id_to_name)

    # Convert date
    game_df["Date"] = pd.to_datetime(game_df["Date"], format="%Y%m%d")

    # Sidebar filters
    st.sidebar.header("Filter Data")

    # Move minimum threshold sliders above tournament selector
    st.sidebar.markdown("### Minimum Value Thresholds")
    color_list = ["Yellow", "Green", "Brown", "Blue", "Pink", "Black", "Baulk"]
    min_thresholds = {}
    for color in color_list:
        min_thresholds[color] = st.sidebar.slider(f"{color}", min_value=0.0, max_value=1.0, value=0.0, step=0.01)

    tournaments = st.sidebar.multiselect("Select Tournaments", options=game_df["Tournament"].unique(), default=game_df["Tournament"].unique())

    # Player and time selection in main layout
    player_list = sorted(set(game_df["Player 1 Name"].dropna()).union(game_df["Player 2 Name"].dropna()))
    col1, col_date, col_toggle, col2 = st.columns([1.5, 2, 1, 1.5])

    with col1:
        player_a = st.selectbox("Player A", options=player_list, key="player_a")
    with col2:
        player_b = st.selectbox("Player B", options=player_list, index=1 if player_list[0] == player_a else 0, key="player_b")
    with col_toggle:
        use_presets = st.toggle("Use Preset Range", value=True)
    with col_date:
        if use_presets:
            preset = st.selectbox("Preset Range", ["Last 3 Months", "Last 6 Months", "Last Year", "Last 2 Years", "All Time"])
            today = datetime.today()
            if preset == "Last 3 Months":
                start_date = today - timedelta(days=90)
            elif preset == "Last 6 Months":
                start_date = today - timedelta(days=180)
            elif preset == "Last Year":
                start_date = today - timedelta(days=365)
            elif preset == "Last 2 Years":
                start_date = today - timedelta(days=730)
            else:
                start_date = game_df["Date"].min()
            end_date = today
        else:
            date_range = st.date_input("Select Date Range", [game_df["Date"].min(), game_df["Date"].max()], key="date_range")
            start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])

    # Filter logic
    filtered_df = game_df[
        (game_df["Tournament"].isin(tournaments)) &
        (game_df["Date"] >= start_date) &
        (game_df["Date"] <= end_date)
    ]

    def get_player_stats(df, player_name):
        player_games = df[(df["Player 1 Name"] == player_name) | (df["Player 2 Name"] == player_name)].copy()
        color_cols = color_list

        player_games["Total Frames"] = pd.to_numeric(player_games["Total Frames"], errors='coerce').fillna(0)
        for col in color_cols:
            player_games[col] = pd.to_numeric(player_games[col], errors='coerce').fillna(0)

        for col in color_cols:
            player_games[col] = player_games[col] * player_games["Total Frames"]

        weighted_sums = player_games[color_cols].sum()
        total_frames = player_games["Total Frames"].sum()

        if total_frames > 0:
            weighted_avgs = weighted_sums / total_frames
        else:
            weighted_avgs = pd.Series([0]*len(color_cols), index=color_cols)

        avg_colors = weighted_avgs.reset_index()
        avg_colors.columns = ["Ball", "Average Proportion"]
        num_games = len(player_games)
        return avg_colors, num_games

    stats_a, games_a = get_player_stats(filtered_df, player_a)
    stats_b, games_b = get_player_stats(filtered_df, player_b)

    color_mapping = {
        "Yellow": "#FFFF00",
        "Green": "#008000",
        "Brown": "#8B4513",
        "Blue": "#0000FF",
        "Pink": "#FFC0CB",
        "Black": "#000000",
        "Baulk": "#A9A9A9"
    }

    st.markdown("### Player Comparison")
    col_plot1, col_plot2 = st.columns(2)

    def create_chart(data, player_name, game_count):
        base = alt.Chart(data).encode(x=alt.X("Ball", sort=None))
        bars = base.mark_bar().encode(
            y="Average Proportion",
            color=alt.Color("Ball", scale=alt.Scale(domain=list(color_mapping.keys()), range=list(color_mapping.values())), legend=None),
            tooltip=["Ball", "Average Proportion"]
        )

        # Draw threshold lines
        rules = alt.Chart(pd.DataFrame({
            "Ball": list(min_thresholds.keys()),
            "Threshold": list(min_thresholds.values())
        })).mark_rule(color="red", strokeDash=[4, 2]).encode(
            x="Ball",
            y="Threshold"
        )

        return (bars + rules).properties(title=f"{player_name} ({game_count} games)", width=300, height=400)

    with col_plot1:
        st.altair_chart(create_chart(stats_a, player_a, games_a), use_container_width=True)

    with col_plot2:
        st.altair_chart(create_chart(stats_b, player_b, games_b), use_container_width=True)

    st.divider()
    st.file_uploader("Upload a new Excel file", type=["xlsx"], key="new_upload")

else:
    uploaded_file = st.file_uploader("Upload the Excel file", type=["xlsx"], key="initial_upload")
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
