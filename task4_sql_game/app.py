"""
NBA SQL Trivia — An Interactive SQL Trivia Game with Real NBA Data
===================================================================
Test your SQL skills with randomized NBA trivia questions!
Each game generates different questions, so you must know SQL — not just the answers.
Race the clock and compete on the leaderboard.
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
import time
import random
import math
import json
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nba_trivia.db")

LEVEL_NAMES = {
    1: ("SELECT *", "Basic Retrieval"),
    2: ("WHERE / AND / OR", "Filtering"),
    3: ("ORDER BY / LIMIT", "Sorting & Ranking"),
    4: ("GROUP BY / AVG / COUNT", "Aggregation"),
    5: ("JOIN", "Combining Tables"),
}

POINTS_PER_LEVEL = 100
HINT_PENALTY = 10

# ---------------------------------------------------------------------------
# Database — connection helper
# ---------------------------------------------------------------------------

def get_connection():
    return sqlite3.connect(DB_PATH)


def run_query(sql):
    """Execute a SELECT query and return a DataFrame or error string."""
    sql_stripped = sql.strip().rstrip(";").strip()
    first_word = sql_stripped.split()[0].upper() if sql_stripped else ""
    if first_word not in ("SELECT", "WITH"):
        return "Only SELECT queries are allowed! Use SELECT or WITH ... SELECT to explore the data."
    try:
        conn = get_connection()
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df
    except Exception as e:
        return f"SQL Error: {e}"


# ---------------------------------------------------------------------------
# Database — create schema
# ---------------------------------------------------------------------------

def create_schema(conn):
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            abbreviation TEXT NOT NULL,
            city TEXT NOT NULL,
            conference TEXT NOT NULL,
            division TEXT NOT NULL,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            position TEXT NOT NULL,
            age INTEGER,
            ppg REAL NOT NULL DEFAULT 0,
            rpg REAL NOT NULL DEFAULT 0,
            apg REAL NOT NULL DEFAULT 0,
            spg REAL NOT NULL DEFAULT 0,
            bpg REAL NOT NULL DEFAULT 0,
            fg_pct REAL DEFAULT 0,
            fg3_pct REAL DEFAULT 0,
            ft_pct REAL DEFAULT 0,
            gp INTEGER DEFAULT 0,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            game_date TEXT NOT NULL,
            FOREIGN KEY (home_team_id) REFERENCES teams(id),
            FOREIGN KEY (away_team_id) REFERENCES teams(id)
        );
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            completion_time_seconds REAL NOT NULL,
            levels_completed INTEGER NOT NULL,
            hints_used INTEGER NOT NULL DEFAULT 0,
            score INTEGER NOT NULL DEFAULT 0,
            played_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_id);
        CREATE INDEX IF NOT EXISTS idx_players_position ON players(position);
        CREATE INDEX IF NOT EXISTS idx_games_home ON games(home_team_id);
        CREATE INDEX IF NOT EXISTS idx_games_away ON games(away_team_id);
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Database — fetch from nba_api and populate
# ---------------------------------------------------------------------------

def fetch_and_cache_data():
    """Fetch NBA data from nba_api and store in SQLite. Falls back to hardcoded data."""
    if os.path.exists(DB_PATH):
        return
    conn = get_connection()
    create_schema(conn)
    try:
        _fetch_from_api(conn)
    except Exception as e:
        st.warning(f"Could not fetch live NBA data ({e}). Using built-in dataset.")
        conn.close()
        os.remove(DB_PATH)
        conn = get_connection()
        create_schema(conn)
        _create_fallback_data(conn)
    conn.close()


def _fetch_from_api(conn):
    """Fetch real data from nba_api."""
    from nba_api.stats.static import teams as nba_teams
    from nba_api.stats.endpoints import LeagueDashPlayerStats, LeagueStandings, LeagueGameLog
    import time as _time

    # --- Teams ---
    all_teams = nba_teams.get_teams()
    standings = LeagueStandings(season="2024-25", season_type="Regular Season")
    _time.sleep(0.7)
    standings_df = standings.get_data_frames()[0]

    team_id_map = {}
    for t in all_teams:
        row = standings_df[standings_df["TeamID"] == t["id"]]
        wins = int(row["WINS"].values[0]) if len(row) > 0 else 0
        losses = int(row["LOSSES"].values[0]) if len(row) > 0 else 0
        conf = row["Conference"].values[0] if len(row) > 0 else "Unknown"
        div = row["Division"].values[0] if len(row) > 0 else "Unknown"
        conn.execute(
            "INSERT INTO teams VALUES (?,?,?,?,?,?,?,?)",
            (t["id"], t["full_name"], t["abbreviation"], t["city"], conf, div, wins, losses),
        )
        team_id_map[t["id"]] = t["full_name"]
    conn.commit()

    # --- Players ---
    player_stats = LeagueDashPlayerStats(season="2024-25", per_mode_detailed="PerGame")
    _time.sleep(0.7)
    ps_df = player_stats.get_data_frames()[0]
    ps_df = ps_df[ps_df["GP"] > 0]

    # Build player_id → position map from PlayerIndex (more reliable source of positions)
    pos_map = {}
    try:
        from nba_api.stats.endpoints import PlayerIndex
        _time.sleep(0.7)
        pi = PlayerIndex(season="2024-25")
        pi_df = pi.get_data_frames()[0]
        # PlayerIndex has PERSON_ID and POSITION columns
        if "PERSON_ID" in pi_df.columns and "POSITION" in pi_df.columns:
            pos_map = {int(row["PERSON_ID"]): str(row["POSITION"]) for _, row in pi_df.iterrows()}
    except Exception:
        pass

    for _, p in ps_df.iterrows():
        pid = int(p["PLAYER_ID"])
        # Prefer PlayerIndex position, fall back to LeagueDash column
        pos_raw = pos_map.get(pid) or str(p.get("PLAYER_POSITION", ""))
        conn.execute(
            "INSERT INTO players VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                pid, p["PLAYER_NAME"], int(p["TEAM_ID"]),
                _normalize_position(pos_raw),
                int(p["AGE"]) if pd.notna(p.get("AGE")) else None,
                round(float(p.get("PTS", 0)), 1),
                round(float(p.get("REB", 0)), 1),
                round(float(p.get("AST", 0)), 1),
                round(float(p.get("STL", 0)), 1),
                round(float(p.get("BLK", 0)), 1),
                round(float(p.get("FG_PCT", 0)) * 100, 1),
                round(float(p.get("FG3_PCT", 0)) * 100, 1),
                round(float(p.get("FT_PCT", 0)) * 100, 1),
                int(p.get("GP", 0)),
            ),
        )
    conn.commit()

    # --- Games ---
    _time.sleep(0.7)
    game_log = LeagueGameLog(season="2024-25", season_type_all_star="Regular Season")
    gl_df = game_log.get_data_frames()[0]

    inserted_games = set()
    for _, g in gl_df.iterrows():
        game_id = g["GAME_ID"]
        if game_id in inserted_games:
            continue
        inserted_games.add(game_id)
        matchup = str(g["MATCHUP"])
        team_id = int(g["TEAM_ID"])
        pts = int(g["PTS"]) if pd.notna(g["PTS"]) else 0
        wl = str(g["WL"])
        game_date = str(g["GAME_DATE"])

        # Find the other row for this game
        other = gl_df[(gl_df["GAME_ID"] == game_id) & (gl_df["TEAM_ID"] != team_id)]
        if len(other) == 0:
            continue
        other = other.iloc[0]
        other_team_id = int(other["TEAM_ID"])
        other_pts = int(other["PTS"]) if pd.notna(other["PTS"]) else 0

        if "vs." in matchup:
            home_id, away_id = team_id, other_team_id
            home_score, away_score = pts, other_pts
        else:
            home_id, away_id = other_team_id, team_id
            home_score, away_score = other_pts, pts

        conn.execute(
            "INSERT INTO games (home_team_id, away_team_id, home_score, away_score, game_date) VALUES (?,?,?,?,?)",
            (home_id, away_id, home_score, away_score, game_date),
        )
    conn.commit()


def _normalize_position(pos):
    if not pos or str(pos).strip().upper() in ("N/A", "NONE", "NAN", ""):
        return "N/A"
    pos = str(pos).strip().upper()
    mapping = {
        # Full names (uppercase)
        "GUARD": "G", "POINT GUARD": "G", "SHOOTING GUARD": "G",
        "FORWARD": "F", "SMALL FORWARD": "F", "POWER FORWARD": "F",
        "CENTER": "C", "CENTRE": "C",
        "GUARD-FORWARD": "G-F", "FORWARD-GUARD": "F-G",
        "FORWARD-CENTER": "F-C", "CENTER-FORWARD": "C-F",
        # Title-case variants from nba_api (after uppercasing)
        "G": "G", "F": "F", "C": "C",
        "G-F": "G-F", "F-G": "F-G", "F-C": "F-C", "C-F": "C-F",
        # Additional API variants
        "PG": "G", "SG": "G", "SF": "F", "PF": "F",
        "PG-SG": "G", "SG-PG": "G", "SF-PF": "F", "PF-SF": "F",
        "PF-C": "F-C", "C-PF": "C-F", "SG-SF": "G-F", "SF-SG": "F-G",
    }
    if pos in mapping:
        return mapping[pos]
    # If it starts with G, F, or C — make a best guess
    if pos.startswith("G"):
        return "G"
    if pos.startswith("F"):
        return "F"
    if pos.startswith("C"):
        return "C"
    return "N/A"


# ---------------------------------------------------------------------------
# Database — fallback hardcoded data
# ---------------------------------------------------------------------------

def _create_fallback_data(conn):
    """Insert realistic hardcoded NBA data when API is unavailable."""
    teams_data = [
        (1610612737, "Atlanta Hawks", "ATL", "Atlanta", "East", "Southeast", 36, 46),
        (1610612738, "Boston Celtics", "BOS", "Boston", "East", "Atlantic", 58, 24),
        (1610612739, "Cleveland Cavaliers", "CLE", "Cleveland", "East", "Central", 52, 30),
        (1610612740, "New Orleans Pelicans", "NOP", "New Orleans", "West", "Southwest", 30, 52),
        (1610612741, "Chicago Bulls", "CHI", "Chicago", "East", "Central", 32, 50),
        (1610612742, "Dallas Mavericks", "DAL", "Dallas", "West", "Southwest", 48, 34),
        (1610612743, "Denver Nuggets", "DEN", "Denver", "West", "Northwest", 50, 32),
        (1610612744, "Golden State Warriors", "GSW", "Golden State", "West", "Pacific", 44, 38),
        (1610612745, "Houston Rockets", "HOU", "Houston", "West", "Southwest", 41, 41),
        (1610612746, "LA Clippers", "LAC", "Los Angeles", "West", "Pacific", 38, 44),
        (1610612747, "Los Angeles Lakers", "LAL", "Los Angeles", "West", "Pacific", 46, 36),
        (1610612748, "Miami Heat", "MIA", "Miami", "East", "Southeast", 40, 42),
        (1610612749, "Milwaukee Bucks", "MIL", "Milwaukee", "East", "Central", 49, 33),
        (1610612750, "Minnesota Timberwolves", "MIN", "Minnesota", "West", "Northwest", 52, 30),
        (1610612751, "Brooklyn Nets", "BKN", "Brooklyn", "East", "Atlantic", 26, 56),
        (1610612752, "New York Knicks", "NYK", "New York", "East", "Atlantic", 50, 32),
        (1610612753, "Orlando Magic", "ORL", "Orlando", "East", "Southeast", 47, 35),
        (1610612754, "Indiana Pacers", "IND", "Indiana", "East", "Central", 45, 37),
        (1610612755, "Philadelphia 76ers", "PHI", "Philadelphia", "East", "Atlantic", 38, 44),
        (1610612756, "Phoenix Suns", "PHX", "Phoenix", "West", "Pacific", 42, 40),
        (1610612757, "Portland Trail Blazers", "POR", "Portland", "West", "Northwest", 22, 60),
        (1610612758, "Sacramento Kings", "SAC", "Sacramento", "West", "Pacific", 40, 42),
        (1610612759, "San Antonio Spurs", "SAS", "San Antonio", "West", "Southwest", 34, 48),
        (1610612760, "Oklahoma City Thunder", "OKC", "Oklahoma City", "West", "Northwest", 57, 25),
        (1610612761, "Toronto Raptors", "TOR", "Toronto", "East", "Atlantic", 25, 57),
        (1610612762, "Utah Jazz", "UTA", "Utah", "West", "Northwest", 28, 54),
        (1610612763, "Memphis Grizzlies", "MEM", "Memphis", "West", "Southwest", 46, 36),
        (1610612764, "Washington Wizards", "WAS", "Washington", "East", "Southeast", 20, 62),
        (1610612765, "Detroit Pistons", "DET", "Detroit", "East", "Central", 24, 58),
        (1610612766, "Charlotte Hornets", "CHA", "Charlotte", "East", "Southeast", 22, 60),
    ]
    conn.executemany("INSERT INTO teams VALUES (?,?,?,?,?,?,?,?)", teams_data)

    players_data = [
        # Boston Celtics
        (1, "Jayson Tatum", 1610612738, "F", 27, 27.1, 8.4, 5.5, 1.1, 0.6, 47.2, 37.6, 85.3, 74),
        (2, "Jaylen Brown", 1610612738, "G-F", 28, 23.5, 5.5, 3.6, 1.2, 0.5, 49.1, 35.4, 70.5, 70),
        (3, "Derrick White", 1610612738, "G", 30, 15.8, 4.3, 5.2, 0.9, 1.2, 46.1, 39.5, 89.0, 73),
        (4, "Kristaps Porzingis", 1610612738, "C", 29, 20.3, 7.2, 2.0, 0.7, 1.9, 51.5, 37.2, 85.7, 55),
        (5, "Jrue Holiday", 1610612738, "G", 34, 12.5, 5.4, 4.5, 0.9, 0.6, 48.0, 42.1, 82.3, 68),
        # Oklahoma City Thunder
        (6, "Shai Gilgeous-Alexander", 1610612760, "G", 26, 30.4, 5.5, 6.2, 2.0, 0.7, 53.5, 35.3, 87.4, 75),
        (7, "Jalen Williams", 1610612760, "G-F", 24, 20.8, 5.5, 5.1, 1.3, 0.6, 53.2, 35.0, 80.2, 72),
        (8, "Chet Holmgren", 1610612760, "C", 22, 16.5, 7.9, 2.6, 0.8, 2.5, 53.0, 34.8, 79.5, 68),
        (9, "Lu Dort", 1610612760, "G", 25, 10.2, 4.0, 1.8, 1.1, 0.3, 42.5, 36.2, 78.0, 70),
        (10, "Isaiah Hartenstein", 1610612760, "C", 26, 12.0, 12.1, 4.1, 0.8, 1.0, 58.2, 15.0, 68.0, 65),
        # Denver Nuggets
        (11, "Nikola Jokic", 1610612743, "C", 29, 26.4, 12.4, 9.8, 1.4, 0.9, 58.3, 39.6, 81.7, 74),
        (12, "Jamal Murray", 1610612743, "G", 27, 21.2, 4.0, 6.5, 1.0, 0.3, 48.1, 35.8, 85.0, 62),
        (13, "Michael Porter Jr.", 1610612743, "F", 26, 18.7, 7.1, 1.5, 0.6, 0.8, 50.3, 40.1, 82.0, 65),
        (14, "Aaron Gordon", 1610612743, "F", 29, 14.2, 6.5, 3.5, 0.7, 0.6, 55.1, 33.2, 73.0, 70),
        (15, "Christian Braun", 1610612743, "G-F", 24, 11.8, 5.2, 3.4, 1.2, 0.5, 49.0, 38.0, 80.0, 72),
        # Milwaukee Bucks
        (16, "Giannis Antetokounmpo", 1610612749, "F", 30, 31.5, 11.9, 6.5, 1.2, 1.1, 61.1, 27.4, 65.7, 73),
        (17, "Damian Lillard", 1610612749, "G", 34, 25.7, 4.6, 7.4, 1.0, 0.3, 45.0, 35.4, 92.3, 72),
        (18, "Khris Middleton", 1610612749, "F", 33, 14.8, 4.5, 4.8, 0.8, 0.3, 46.0, 38.5, 87.0, 50),
        (19, "Brook Lopez", 1610612749, "C", 36, 12.5, 5.2, 1.5, 0.3, 2.4, 48.0, 36.0, 73.0, 72),
        (20, "Bobby Portis", 1610612749, "F-C", 29, 13.8, 7.8, 1.4, 0.5, 0.4, 47.5, 37.0, 80.0, 68),
        # Dallas Mavericks
        (21, "Luka Doncic", 1610612742, "G-F", 25, 28.8, 8.3, 7.8, 1.4, 0.5, 48.7, 35.4, 78.6, 70),
        (22, "Kyrie Irving", 1610612742, "G", 32, 24.2, 5.0, 5.2, 1.3, 0.4, 49.7, 41.1, 90.5, 72),
        (23, "PJ Washington", 1610612742, "F", 26, 13.5, 7.1, 2.1, 1.0, 0.8, 45.5, 33.0, 71.0, 74),
        (24, "Daniel Gafford", 1610612742, "C", 26, 10.8, 5.8, 1.0, 0.5, 1.8, 68.0, 0.0, 65.5, 68),
        (25, "Dereck Lively II", 1610612742, "C", 21, 9.0, 7.4, 2.3, 0.4, 1.3, 63.0, 25.0, 68.0, 70),
        # Minnesota Timberwolves
        (26, "Anthony Edwards", 1610612750, "G", 23, 25.9, 5.4, 5.1, 1.3, 0.5, 46.2, 35.7, 84.0, 75),
        (27, "Karl-Anthony Towns", 1610612752, "C", 29, 24.9, 13.9, 3.3, 0.7, 0.6, 54.8, 41.3, 85.0, 72),
        (28, "Julius Randle", 1610612750, "F", 30, 20.8, 9.3, 4.6, 0.6, 0.3, 47.0, 31.0, 76.0, 68),
        (29, "Rudy Gobert", 1610612750, "C", 32, 10.5, 11.3, 1.3, 0.5, 2.1, 62.0, 0.0, 64.0, 70),
        (30, "Mike Conley", 1610612750, "G", 37, 9.4, 2.8, 5.8, 0.9, 0.2, 44.0, 40.2, 90.0, 65),
        # Cleveland Cavaliers
        (31, "Donovan Mitchell", 1610612739, "G", 28, 26.6, 4.9, 6.1, 1.8, 0.4, 46.1, 36.8, 86.7, 74),
        (32, "Darius Garland", 1610612739, "G", 24, 21.0, 2.7, 6.8, 1.3, 0.1, 44.5, 37.2, 87.0, 68),
        (33, "Evan Mobley", 1610612739, "F-C", 23, 18.3, 9.4, 3.2, 0.6, 1.5, 58.0, 33.0, 70.5, 70),
        (34, "Jarrett Allen", 1610612739, "C", 26, 16.5, 10.5, 2.8, 0.6, 1.3, 63.5, 0.0, 67.0, 72),
        (35, "Max Strus", 1610612739, "G-F", 28, 12.4, 3.8, 3.0, 0.8, 0.3, 43.0, 37.5, 85.0, 66),
        # New York Knicks
        (36, "Jalen Brunson", 1610612752, "G", 28, 28.7, 3.5, 6.7, 0.9, 0.2, 47.9, 38.5, 84.7, 75),
        (37, "OG Anunoby", 1610612752, "F", 27, 14.1, 4.4, 1.5, 1.5, 0.7, 49.3, 38.4, 78.0, 68),
        (38, "Josh Hart", 1610612752, "G-F", 29, 9.4, 8.3, 4.1, 0.8, 0.3, 43.0, 33.0, 76.0, 74),
        (39, "Mikal Bridges", 1610612752, "F", 28, 19.6, 4.5, 3.6, 1.0, 0.4, 44.0, 37.4, 81.5, 72),
        (40, "Mitchell Robinson", 1610612752, "C", 26, 8.5, 8.6, 0.8, 0.4, 1.6, 62.0, 0.0, 55.0, 45),
        # Los Angeles Lakers
        (41, "LeBron James", 1610612747, "F", 40, 25.7, 7.3, 8.3, 1.3, 0.5, 54.0, 41.0, 75.0, 71),
        (42, "Anthony Davis", 1610612747, "F-C", 31, 24.7, 12.6, 3.5, 1.2, 2.3, 55.6, 27.1, 81.6, 72),
        (43, "Austin Reaves", 1610612747, "G", 26, 15.9, 4.3, 5.5, 0.9, 0.3, 48.5, 36.2, 85.0, 73),
        (44, "D'Angelo Russell", 1610612747, "G", 28, 18.0, 3.1, 6.3, 0.9, 0.4, 45.6, 41.5, 77.0, 70),
        (45, "Rui Hachimura", 1610612747, "F", 26, 13.4, 4.3, 1.2, 0.5, 0.3, 49.0, 35.5, 78.0, 68),
        # Phoenix Suns
        (46, "Kevin Durant", 1610612756, "F", 36, 27.1, 6.6, 5.0, 0.9, 1.2, 52.3, 41.3, 85.6, 70),
        (47, "Devin Booker", 1610612756, "G", 27, 27.9, 4.5, 6.9, 1.0, 0.3, 49.2, 36.4, 88.0, 72),
        (48, "Bradley Beal", 1610612756, "G", 31, 18.2, 4.4, 5.0, 1.0, 0.3, 51.1, 43.0, 81.3, 53),
        (49, "Jusuf Nurkic", 1610612756, "C", 30, 10.3, 8.8, 2.5, 0.6, 0.5, 52.0, 20.0, 66.0, 65),
        (50, "Grayson Allen", 1610612756, "G", 29, 13.5, 3.4, 3.0, 0.7, 0.2, 47.2, 46.1, 90.3, 68),
        # Miami Heat
        (51, "Jimmy Butler", 1610612748, "F", 35, 20.8, 5.3, 5.0, 1.3, 0.3, 49.9, 41.4, 86.0, 60),
        (52, "Bam Adebayo", 1610612748, "C", 27, 19.3, 10.4, 3.9, 1.1, 0.8, 52.0, 18.0, 72.0, 74),
        (53, "Tyler Herro", 1610612748, "G", 24, 20.8, 5.3, 4.7, 0.7, 0.2, 44.1, 39.6, 86.0, 72),
        (54, "Terry Rozier", 1610612748, "G", 30, 16.4, 4.2, 4.6, 0.9, 0.3, 43.5, 36.5, 88.0, 58),
        (55, "Caleb Martin", 1610612748, "F", 29, 10.0, 4.5, 2.2, 1.0, 0.3, 44.0, 34.0, 80.0, 66),
        # Philadelphia 76ers
        (56, "Joel Embiid", 1610612755, "C", 30, 34.7, 11.0, 5.6, 1.2, 1.7, 52.9, 38.8, 88.3, 39),
        (57, "Tyrese Maxey", 1610612755, "G", 24, 25.9, 3.7, 6.2, 1.0, 0.5, 45.0, 37.3, 87.0, 72),
        (58, "Paul George", 1610612755, "F", 34, 17.5, 5.5, 4.6, 1.5, 0.4, 44.2, 37.0, 83.0, 62),
        (59, "Tobias Harris", 1610612765, "F", 32, 11.7, 5.0, 2.4, 0.7, 0.4, 46.0, 36.0, 84.0, 70),
        (60, "Kelly Oubre Jr.", 1610612755, "G-F", 28, 15.4, 5.0, 1.3, 1.2, 0.3, 44.3, 31.3, 76.0, 68),
        # Indiana Pacers
        (61, "Tyrese Haliburton", 1610612754, "G", 24, 20.1, 3.7, 10.9, 1.2, 0.4, 47.7, 36.4, 85.5, 69),
        (62, "Pascal Siakam", 1610612754, "F", 30, 21.3, 7.8, 4.1, 0.8, 0.5, 53.0, 31.4, 76.7, 74),
        (63, "Myles Turner", 1610612754, "C", 28, 17.1, 6.9, 1.4, 0.5, 2.3, 52.4, 35.8, 78.0, 72),
        (64, "Bennedict Mathurin", 1610612754, "G", 22, 14.5, 4.0, 1.9, 0.5, 0.3, 44.7, 36.0, 80.0, 70),
        (65, "Andrew Nembhard", 1610612754, "G", 24, 9.2, 3.2, 4.3, 1.0, 0.3, 47.0, 36.5, 80.0, 68),
        # Orlando Magic
        (66, "Paolo Banchero", 1610612753, "F", 22, 22.6, 6.9, 5.4, 1.0, 0.6, 45.5, 34.0, 73.0, 74),
        (67, "Franz Wagner", 1610612753, "F", 23, 19.7, 5.6, 3.7, 1.1, 0.3, 46.5, 33.6, 86.0, 72),
        (68, "Jalen Suggs", 1610612753, "G", 23, 12.6, 3.1, 3.9, 1.5, 0.3, 44.0, 39.0, 76.0, 70),
        (69, "Wendell Carter Jr.", 1610612753, "C", 25, 11.9, 8.1, 2.2, 0.6, 0.6, 52.0, 28.0, 66.0, 54),
        (70, "Cole Anthony", 1610612753, "G", 24, 12.8, 4.0, 3.8, 0.8, 0.3, 43.5, 35.0, 81.0, 58),
        # Sacramento Kings
        (71, "De'Aaron Fox", 1610612758, "G", 26, 26.6, 4.6, 5.6, 2.0, 0.4, 46.5, 32.9, 73.8, 74),
        (72, "Domantas Sabonis", 1610612758, "C", 28, 19.4, 13.7, 8.2, 0.8, 0.5, 56.2, 37.8, 73.3, 74),
        (73, "DeMar DeRozan", 1610612758, "F", 35, 24.0, 4.3, 5.3, 1.1, 0.3, 49.0, 33.3, 85.5, 72),
        (74, "Keegan Murray", 1610612758, "F", 24, 14.8, 5.2, 2.0, 0.6, 0.5, 44.5, 37.4, 85.0, 72),
        (75, "Malik Monk", 1610612758, "G", 26, 15.4, 2.9, 4.9, 0.8, 0.2, 44.0, 35.5, 82.0, 68),
        # Memphis Grizzlies
        (76, "Ja Morant", 1610612763, "G", 25, 21.2, 4.7, 8.1, 0.8, 0.3, 47.3, 30.3, 74.0, 55),
        (77, "Desmond Bane", 1610612763, "G", 26, 23.7, 5.3, 4.8, 0.9, 0.5, 46.5, 39.0, 87.5, 72),
        (78, "Jaren Jackson Jr.", 1610612763, "F-C", 25, 22.3, 5.5, 2.3, 1.0, 1.6, 49.5, 32.2, 81.0, 70),
        (79, "Marcus Smart", 1610612763, "G", 30, 14.5, 4.0, 6.2, 1.0, 0.3, 42.0, 33.0, 76.0, 65),
        (80, "Santi Aldama", 1610612763, "F-C", 24, 10.8, 6.7, 2.1, 0.6, 0.9, 48.0, 38.5, 82.0, 68),
        # Chicago Bulls
        (81, "Zach LaVine", 1610612741, "G", 29, 24.8, 4.2, 4.2, 0.8, 0.4, 49.5, 39.8, 85.0, 60),
        (82, "Coby White", 1610612741, "G", 24, 19.1, 4.5, 5.1, 0.7, 0.3, 44.0, 37.2, 80.0, 72),
        (83, "Nikola Vucevic", 1610612741, "C", 34, 18.0, 10.5, 3.3, 0.7, 0.9, 56.0, 35.0, 77.0, 72),
        (84, "Patrick Williams", 1610612741, "F", 23, 10.0, 3.9, 2.0, 0.7, 0.5, 48.0, 36.0, 72.0, 65),
        (85, "Alex Caruso", 1610612760, "G", 30, 10.3, 4.0, 3.8, 1.7, 0.6, 44.2, 39.0, 83.0, 70),
        # Houston Rockets
        (86, "Jalen Green", 1610612745, "G", 22, 19.6, 5.0, 3.5, 0.8, 0.3, 42.8, 33.4, 78.0, 72),
        (87, "Alperen Sengun", 1610612745, "C", 22, 21.1, 9.3, 5.0, 1.0, 0.7, 53.4, 29.0, 71.0, 72),
        (88, "Fred VanVleet", 1610612745, "G", 30, 14.3, 3.5, 7.2, 1.4, 0.2, 39.8, 36.3, 84.7, 72),
        (89, "Dillon Brooks", 1610612745, "F", 28, 14.0, 3.3, 2.1, 0.8, 0.4, 44.0, 34.5, 80.0, 68),
        (90, "Jabari Smith Jr.", 1610612745, "F", 22, 12.0, 6.5, 1.5, 0.7, 1.0, 41.0, 34.0, 77.0, 70),
        # Toronto Raptors
        (91, "Scottie Barnes", 1610612761, "F", 23, 19.9, 8.2, 6.1, 1.3, 0.9, 47.5, 28.0, 73.5, 68),
        (92, "RJ Barrett", 1610612761, "G-F", 24, 21.8, 6.4, 4.1, 0.6, 0.3, 55.3, 39.2, 75.0, 65),
        (93, "Immanuel Quickley", 1610612761, "G", 25, 18.6, 4.8, 6.8, 0.9, 0.2, 42.0, 35.5, 83.0, 68),
        (94, "Jakob Poeltl", 1610612761, "C", 29, 14.0, 10.0, 2.5, 0.4, 1.3, 60.0, 0.0, 67.0, 70),
        (95, "Gradey Dick", 1610612761, "G", 21, 13.3, 2.8, 2.5, 0.5, 0.2, 44.5, 40.0, 88.0, 72),
        # Golden State Warriors
        (96, "Stephen Curry", 1610612744, "G", 36, 26.4, 4.5, 6.1, 1.0, 0.4, 45.0, 40.8, 92.3, 74),
        (97, "Andrew Wiggins", 1610612744, "F", 29, 13.2, 4.5, 1.7, 0.6, 0.5, 45.3, 35.8, 73.0, 68),
        (98, "Jonathan Kuminga", 1610612744, "F", 22, 16.1, 4.8, 2.2, 0.7, 0.4, 52.5, 32.0, 70.0, 70),
        (99, "Kevon Looney", 1610612744, "C", 28, 6.8, 7.5, 2.5, 0.4, 0.4, 56.5, 0.0, 60.0, 72),
        (100, "Brandin Podziemski", 1610612744, "G", 21, 9.2, 5.8, 3.7, 0.8, 0.3, 41.0, 38.0, 77.0, 70),
        # San Antonio Spurs
        (101, "Victor Wembanyama", 1610612759, "C", 21, 21.4, 10.6, 3.9, 1.2, 3.6, 46.5, 32.5, 79.5, 71),
        (102, "Devin Vassell", 1610612759, "G-F", 24, 19.5, 3.8, 4.0, 1.0, 0.5, 47.0, 38.0, 85.0, 62),
        (103, "Keldon Johnson", 1610612759, "F", 25, 13.2, 4.5, 2.8, 0.6, 0.2, 45.5, 34.0, 75.0, 68),
        (104, "Tre Jones", 1610612759, "G", 24, 10.8, 3.0, 5.7, 1.0, 0.2, 49.0, 28.0, 82.0, 70),
        (105, "Jeremy Sochan", 1610612759, "F", 21, 12.5, 6.2, 3.0, 0.9, 0.4, 48.0, 24.0, 72.0, 68),
        # Atlanta Hawks
        (106, "Trae Young", 1610612737, "G", 26, 25.7, 2.8, 10.8, 1.1, 0.2, 43.0, 37.3, 86.0, 72),
        (107, "Dejounte Murray", 1610612740, "G", 28, 22.3, 5.3, 6.4, 1.6, 0.5, 45.5, 36.0, 80.0, 70),
        (108, "Jalen Johnson", 1610612737, "F", 23, 16.0, 8.7, 3.6, 1.0, 0.6, 51.0, 31.0, 75.0, 68),
        (109, "Clint Capela", 1610612737, "C", 30, 10.5, 9.3, 1.2, 0.5, 1.4, 62.0, 0.0, 50.0, 65),
        (110, "Bogdan Bogdanovic", 1610612737, "G-F", 32, 11.5, 3.0, 3.5, 0.7, 0.2, 42.0, 39.0, 82.0, 60),
        # Portland Trail Blazers
        (111, "Anfernee Simons", 1610612757, "G", 25, 22.6, 2.9, 5.5, 0.6, 0.3, 44.5, 38.0, 87.0, 62),
        (112, "Jerami Grant", 1610612757, "F", 30, 21.0, 3.5, 2.8, 0.8, 1.0, 43.0, 40.2, 81.0, 63),
        (113, "Scoot Henderson", 1610612757, "G", 20, 14.0, 3.5, 5.4, 1.0, 0.3, 38.5, 28.0, 73.0, 68),
        (114, "Deandre Ayton", 1610612757, "C", 26, 16.7, 11.1, 2.0, 0.5, 0.8, 58.5, 22.0, 70.0, 62),
        (115, "Shaedon Sharpe", 1610612757, "G", 21, 16.3, 3.6, 2.2, 0.5, 0.4, 43.0, 35.0, 79.0, 60),
        # Washington Wizards
        (116, "Jordan Poole", 1610612764, "G", 25, 17.4, 2.7, 4.4, 0.8, 0.2, 41.3, 32.5, 86.0, 70),
        (117, "Kyle Kuzma", 1610612764, "F", 29, 22.2, 6.6, 4.2, 0.6, 0.4, 44.0, 33.0, 72.0, 68),
        (118, "Deni Avdija", 1610612757, "F", 23, 14.1, 7.2, 4.4, 1.0, 0.5, 47.0, 35.0, 78.0, 65),
        (119, "Daniel Gafford", 1610612764, "C", 26, 10.1, 5.5, 0.9, 0.5, 1.7, 67.0, 0.0, 63.0, 60),
        (120, "Bilal Coulibaly", 1610612764, "F", 20, 8.4, 4.2, 2.1, 1.1, 0.4, 42.0, 28.0, 70.0, 68),
        # Charlotte Hornets
        (121, "LaMelo Ball", 1610612766, "G", 23, 23.9, 5.1, 8.0, 1.3, 0.3, 43.5, 35.8, 87.0, 55),
        (122, "Brandon Miller", 1610612766, "F", 22, 17.3, 4.3, 2.4, 0.8, 0.6, 44.0, 37.5, 80.0, 68),
        (123, "Miles Bridges", 1610612766, "F", 26, 21.0, 7.3, 3.2, 0.8, 0.6, 46.0, 33.5, 75.0, 70),
        (124, "Mark Williams", 1610612766, "C", 23, 12.0, 8.4, 1.5, 0.5, 1.8, 60.0, 0.0, 66.0, 50),
        (125, "Tre Mann", 1610612766, "G", 23, 11.0, 3.0, 3.5, 0.7, 0.2, 42.0, 36.0, 81.0, 62),
        # Detroit Pistons
        (126, "Cade Cunningham", 1610612765, "G", 23, 22.7, 4.3, 7.5, 1.2, 0.4, 44.9, 35.5, 86.4, 62),
        (127, "Jaden Ivey", 1610612765, "G", 22, 16.2, 3.2, 4.0, 0.7, 0.3, 43.0, 33.5, 75.0, 68),
        (128, "Ausar Thompson", 1610612765, "F", 21, 9.0, 6.4, 2.0, 1.3, 0.5, 48.0, 23.0, 60.0, 52),
        (129, "Jalen Duren", 1610612765, "C", 21, 13.8, 11.0, 2.4, 0.6, 0.8, 59.0, 0.0, 52.0, 70),
        (130, "Bojan Bogdanovic", 1610612765, "F", 35, 14.6, 3.2, 1.8, 0.5, 0.1, 47.0, 39.0, 88.0, 58),
        # Utah Jazz
        (131, "Lauri Markkanen", 1610612762, "F", 27, 23.2, 8.2, 2.0, 0.5, 0.6, 48.0, 39.9, 89.9, 68),
        (132, "Collin Sexton", 1610612762, "G", 25, 18.7, 2.8, 4.0, 0.8, 0.2, 47.5, 37.0, 84.0, 62),
        (133, "Jordan Clarkson", 1610612762, "G", 32, 16.0, 3.5, 4.0, 0.9, 0.2, 43.0, 34.5, 81.0, 68),
        (134, "Walker Kessler", 1610612762, "C", 23, 8.3, 7.5, 0.8, 0.3, 2.3, 60.0, 0.0, 62.0, 70),
        (135, "John Collins", 1610612762, "F", 27, 15.0, 7.0, 2.0, 0.4, 0.6, 54.0, 35.0, 75.0, 68),
        # Brooklyn Nets
        (136, "Mikal Bridges", 1610612751, "F", 28, 19.6, 4.5, 3.6, 1.0, 0.4, 43.6, 37.2, 81.0, 25),
        (137, "Cameron Johnson", 1610612751, "F", 28, 13.4, 4.3, 2.4, 0.6, 0.5, 44.0, 39.5, 83.0, 58),
        (138, "Spencer Dinwiddie", 1610612751, "G", 31, 12.3, 3.2, 5.5, 0.7, 0.2, 40.0, 33.0, 78.0, 62),
        (139, "Nic Claxton", 1610612751, "C", 25, 11.8, 9.2, 2.5, 0.7, 2.1, 60.0, 0.0, 56.0, 65),
        (140, "Cam Thomas", 1610612751, "G", 23, 22.5, 3.0, 3.4, 0.8, 0.3, 42.2, 35.0, 84.5, 72),
        # LA Clippers
        (141, "Kawhi Leonard", 1610612746, "F", 33, 23.7, 6.1, 3.6, 1.6, 0.9, 52.5, 41.7, 88.5, 52),
        (142, "James Harden", 1610612746, "G", 35, 16.6, 5.1, 8.5, 1.1, 0.5, 44.0, 36.0, 87.0, 72),
        (143, "Norman Powell", 1610612746, "G", 31, 14.5, 2.8, 1.5, 0.7, 0.3, 48.0, 42.0, 83.0, 68),
        (144, "Ivica Zubac", 1610612746, "C", 27, 11.7, 9.2, 1.8, 0.3, 1.5, 60.0, 0.0, 67.0, 72),
        (145, "Terance Mann", 1610612746, "G-F", 28, 7.2, 3.5, 2.0, 0.5, 0.3, 48.0, 32.0, 75.0, 62),
        # New Orleans Pelicans
        (146, "Zion Williamson", 1610612740, "F", 24, 22.9, 5.8, 5.0, 1.1, 0.7, 57.0, 33.0, 70.8, 50),
        (147, "Brandon Ingram", 1610612740, "F", 27, 24.7, 5.1, 5.7, 0.7, 0.4, 49.2, 36.5, 82.0, 65),
        (148, "CJ McCollum", 1610612740, "G", 33, 17.5, 3.0, 3.3, 0.7, 0.2, 45.0, 40.0, 83.0, 62),
        (149, "Herb Jones", 1610612740, "F", 26, 11.0, 3.7, 2.4, 1.6, 0.7, 48.0, 37.0, 70.0, 68),
        (150, "Jonas Valanciunas", 1610612740, "C", 32, 12.8, 8.8, 2.1, 0.4, 0.5, 57.0, 29.0, 79.0, 68),
    ]
    conn.executemany("INSERT INTO players VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", players_data)

    # Generate games
    team_ids = [t[0] for t in teams_data]
    random.seed(42)
    game_dates = []
    for month in range(10, 13):
        for day in [5, 10, 15, 20, 25]:
            game_dates.append(f"2024-{month:02d}-{day:02d}")
    for month in range(1, 4):
        for day in [5, 10, 15, 20, 25]:
            game_dates.append(f"2025-{month:02d}-{day:02d}")

    games_to_insert = []
    for date in game_dates:
        shuffled = team_ids[:]
        random.shuffle(shuffled)
        for i in range(0, len(shuffled) - 1, 2):
            home = shuffled[i]
            away = shuffled[i + 1]
            home_score = random.randint(95, 130)
            away_score = random.randint(95, 130)
            while home_score == away_score:
                away_score = random.randint(95, 130)
            games_to_insert.append((home, away, home_score, away_score, date))

    conn.executemany(
        "INSERT INTO games (home_team_id, away_team_id, home_score, away_score, game_date) VALUES (?,?,?,?,?)",
        games_to_insert,
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Question Engine — answer validation
# ---------------------------------------------------------------------------

def validate_answer(user_answer, correct_answer, validator_type, conn=None):
    """Validate user's answer against the correct answer."""
    ua = str(user_answer).strip()
    ca = str(correct_answer).strip()

    if not ua:
        return False

    if validator_type == "exact_number":
        try:
            return int(float(ua)) == int(float(ca))
        except (ValueError, TypeError):
            return False

    elif validator_type == "float_number":
        try:
            return abs(float(ua) - float(ca)) < 0.3
        except (ValueError, TypeError):
            return False

    elif validator_type == "player_name":
        return _fuzzy_name_match(ua, ca, conn)

    elif validator_type == "team_name":
        return _fuzzy_team_match(ua, ca, conn)

    elif validator_type == "name_from_set":
        valid_names = [n.strip() for n in ca.split("|")]
        for name in valid_names:
            if _fuzzy_name_match(ua, name, conn):
                return True
        return False

    elif validator_type == "team_from_set":
        valid_teams = [t.strip() for t in ca.split("|")]
        for team in valid_teams:
            if _fuzzy_team_match(ua, team, conn):
                return True
        return False

    elif validator_type in ("position", "conference"):
        return ua.upper() == ca.upper()

    elif validator_type == "dataframe_match":
        # ca holds the expected DataFrame as JSON; compare against last query result
        last = st.session_state.get("last_query_result", {}).get(
            st.session_state.get("current_level", 1)
        )
        if last is None or not isinstance(last, pd.DataFrame):
            return False
        try:
            expected = pd.read_json(ca)
            return _dataframes_match(last, expected)
        except Exception:
            return False

    else:
        return ua.lower() == ca.lower()


def _dataframes_match(df_user, df_expected):
    """Compare two DataFrames: same shape, same values (order-independent, float-tolerant)."""
    try:
        if df_user is None or df_expected is None:
            return False
        # Normalize column names
        u = df_user.copy()
        e = df_expected.copy()
        u.columns = [c.lower().strip() for c in u.columns]
        e.columns = [c.lower().strip() for c in e.columns]
        if set(u.columns) != set(e.columns):
            return False
        e = e[u.columns]  # match column order
        # Sort both by all columns to make order-independent
        u = u.sort_values(by=list(u.columns)).reset_index(drop=True)
        e = e.sort_values(by=list(e.columns)).reset_index(drop=True)
        if u.shape != e.shape:
            return False
        for col in u.columns:
            if pd.api.types.is_numeric_dtype(u[col]) and pd.api.types.is_numeric_dtype(e[col]):
                if not all(abs(float(a) - float(b)) < 0.5 for a, b in zip(u[col], e[col])):
                    return False
            else:
                if not all(str(a).strip().lower() == str(b).strip().lower() for a, b in zip(u[col], e[col])):
                    return False
        return True
    except Exception:
        return False


def _fuzzy_name_match(user, correct, conn=None):
    u = user.lower().strip()
    c = correct.lower().strip()
    if u == c:
        return True
    # Accept last name match
    parts = c.split()
    if len(parts) >= 2 and u == parts[-1]:
        return True
    # Accept first + last partial
    if c.startswith(u) or c.endswith(u):
        return True
    # Accept if user typed enough of the name
    if len(u) >= 4 and u in c:
        return True
    return False


def _fuzzy_team_match(user, correct, conn=None):
    u = user.lower().strip()
    c = correct.lower().strip()
    if u == c:
        return True
    # Accept nickname (last word)
    parts = c.split()
    if len(parts) >= 2 and u == parts[-1]:
        return True
    # Accept city
    if conn:
        try:
            teams_df = pd.read_sql("SELECT full_name, city, abbreviation FROM teams", conn)
            for _, row in teams_df.iterrows():
                if row["full_name"].lower() == c:
                    if u in (row["city"].lower(), row["abbreviation"].lower()):
                        return True
                    nick = row["full_name"].lower().split()[-1]
                    if u == nick:
                        return True
        except Exception:
            pass
    if len(u) >= 4 and u in c:
        return True
    return False


# ---------------------------------------------------------------------------
# Question Engine — question generators
# ---------------------------------------------------------------------------

def _random_team(conn):
    """Pick a random team from the database."""
    df = pd.read_sql("SELECT id, full_name, abbreviation, city FROM teams", conn)
    return df.sample(1).iloc[0]


def _random_player(conn, min_ppg=5):
    """Pick a random player with at least min_ppg scoring."""
    df = pd.read_sql(f"SELECT id, name, team_id, position, ppg, rpg, apg FROM players WHERE ppg >= {min_ppg}", conn)
    if len(df) == 0:
        df = pd.read_sql("SELECT id, name, team_id, position, ppg, rpg, apg FROM players", conn)
    return df.sample(1).iloc[0]


# ---- LEVEL 1: SELECT * ----

def q1_player_count(conn):
    team = _random_team(conn)
    count = pd.read_sql(f"SELECT COUNT(*) as c FROM players WHERE team_id = {team['id']}", conn).iloc[0]["c"]
    return {
        "text": f"How many players are on the **{team['full_name']}** roster?",
        "answer": str(int(count)),
        "hint": f"Try: SELECT * FROM players WHERE team_id = {team['id']}",
        "validator_type": "exact_number",
    }

def q1_player_position(conn):
    p = _random_player(conn, min_ppg=10)
    return {
        "text": f"What position does **{p['name']}** play?",
        "answer": str(p["position"]),
        "hint": f"Try: SELECT * FROM players WHERE name = '{p['name']}'",
        "validator_type": "position",
        "subject_type": "player",
        "subject_name": p["name"],
    }

def q1_player_team(conn):
    p = _random_player(conn, min_ppg=12)
    team = pd.read_sql(f"SELECT full_name FROM teams WHERE id = {p['team_id']}", conn).iloc[0]["full_name"]
    return {
        "text": f"What team does **{p['name']}** play for?",
        "answer": team,
        "hint": "Try: SELECT * FROM players — look at the team_id, then check the teams table.",
        "validator_type": "team_name",
        "subject_type": "player",
        "subject_name": p["name"],
    }

def q1_team_city(conn):
    team = _random_team(conn)
    nickname = team["full_name"].split()[-1]
    return {
        "text": f"What city do the **{nickname}** play in?",
        "answer": team["city"],
        "hint": "Try: SELECT * FROM teams",
        "validator_type": "team_name",
    }

def q1_player_ppg(conn):
    p = _random_player(conn, min_ppg=15)
    return {
        "text": f"What is **{p['name']}**'s points per game (PPG) average?",
        "answer": str(p["ppg"]),
        "hint": f"Try: SELECT * FROM players WHERE name = '{p['name']}'",
        "validator_type": "float_number",
        "subject_type": "player",
        "subject_name": p["name"],
    }

def q1_team_conference(conn):
    team = _random_team(conn)
    conf = pd.read_sql(f"SELECT conference FROM teams WHERE id = {team['id']}", conn).iloc[0]["conference"]
    return {
        "text": f"Which conference are the **{team['full_name']}** in?",
        "answer": conf,
        "hint": "Try: SELECT * FROM teams",
        "validator_type": "conference",
    }


# ---- LEVEL 2: WHERE / AND / OR ----

def q2_ppg_count(conn):
    team = _random_team(conn)
    for threshold in random.sample([8, 10, 12, 15, 18], 5):
        count = pd.read_sql(
            f"SELECT COUNT(*) as c FROM players WHERE team_id = {team['id']} AND ppg > {threshold}", conn
        ).iloc[0]["c"]
        if 1 <= count <= 6:
            return {
                "text": f"How many players on the **{team['full_name']}** average more than **{threshold} PPG**?",
                "answer": str(int(count)),
                "hint": f"Try: SELECT * FROM players WHERE team_id = {team['id']} AND ppg > {threshold}",
                "validator_type": "exact_number",
            }
    count = pd.read_sql(
        f"SELECT COUNT(*) as c FROM players WHERE team_id = {team['id']} AND ppg > 10", conn
    ).iloc[0]["c"]
    return {
        "text": f"How many players on the **{team['full_name']}** average more than **10 PPG**?",
        "answer": str(int(count)),
        "hint": f"Try: SELECT * FROM players WHERE team_id = {team['id']} AND ppg > 10",
        "validator_type": "exact_number",
    }

def q2_guards_assists(conn):
    for threshold in random.sample([3, 4, 5, 6, 7], 5):
        count = pd.read_sql(
            f"SELECT COUNT(*) as c FROM players WHERE position LIKE '%G%' AND apg > {threshold}", conn
        ).iloc[0]["c"]
        if 3 <= count <= 30:
            return {
                "text": f"How many guards (position contains 'G') average more than **{threshold} assists** per game?",
                "answer": str(int(count)),
                "hint": f"Try: SELECT * FROM players WHERE position LIKE '%G%' AND apg > {threshold}",
                "validator_type": "exact_number",
            }
    return q2_ppg_count(conn)

def q2_team_rebounds(conn):
    team = _random_team(conn)
    threshold = random.choice([5, 6, 7, 8])
    df = pd.read_sql(
        f"SELECT name FROM players WHERE team_id = {team['id']} AND rpg > {threshold}", conn
    )
    if len(df) == 0:
        df = pd.read_sql(f"SELECT name FROM players WHERE team_id = {team['id']} AND rpg > 4", conn)
        threshold = 4
    names = "|".join(df["name"].tolist())
    return {
        "text": f"Name a player on the **{team['full_name']}** who averages more than **{threshold} RPG**.",
        "answer": names,
        "hint": f"Try: SELECT * FROM players WHERE team_id = {team['id']} AND rpg > {threshold}",
        "validator_type": "name_from_set",
        "subject_type": "team",
        "subject_name": team["full_name"],
    }

def q2_conference_wins(conn):
    conf = random.choice(["East", "West"])
    threshold = random.choice([35, 40, 45, 50])
    count = pd.read_sql(
        f"SELECT COUNT(*) as c FROM teams WHERE conference = '{conf}' AND wins > {threshold}", conn
    ).iloc[0]["c"]
    return {
        "text": f"How many **{conf}ern Conference** teams have more than **{threshold} wins**?",
        "answer": str(int(count)),
        "hint": f"Try: SELECT * FROM teams WHERE conference = '{conf}' AND wins > {threshold}",
        "validator_type": "exact_number",
        "subject_type": "conference",
        "subject_name": conf,
    }

def q2_ppg_and_apg(conn):
    for ppg_t, apg_t in random.sample([(15, 4), (18, 3), (20, 5), (12, 6), (22, 4)], 5):
        df = pd.read_sql(
            f"SELECT name FROM players WHERE ppg > {ppg_t} AND apg > {apg_t}", conn
        )
        if 1 <= len(df) <= 15:
            names = "|".join(df["name"].tolist())
            return {
                "text": f"Name a player who averages more than **{ppg_t} PPG** and more than **{apg_t} APG**.",
                "answer": names,
                "hint": f"Try: SELECT * FROM players WHERE ppg > {ppg_t} AND apg > {apg_t}",
                "validator_type": "name_from_set",
            }
    return q2_ppg_count(conn)

def q2_age_filter(conn):
    age = random.choice([21, 22, 23, 35, 36])
    op = ">=" if age >= 35 else "<="
    label = "at least" if age >= 35 else "at most"
    count = pd.read_sql(
        f"SELECT COUNT(*) as c FROM players WHERE age {op} {age}", conn
    ).iloc[0]["c"]
    return {
        "text": f"How many players in the league are **{label} {age} years old**?",
        "answer": str(int(count)),
        "hint": f"Try: SELECT * FROM players WHERE age {op} {age}",
        "validator_type": "exact_number",
    }


# ---- LEVEL 3: ORDER BY / LIMIT ----

def q3_top_scorer(conn):
    top = pd.read_sql("SELECT name FROM players ORDER BY ppg DESC LIMIT 1", conn).iloc[0]["name"]
    return {
        "text": "Who is the **league's top scorer** (highest PPG)?",
        "answer": top,
        "hint": "Try: SELECT name, ppg FROM players ORDER BY ppg DESC LIMIT 1",
        "validator_type": "player_name",
    }

def q3_most_assists(conn):
    top = pd.read_sql("SELECT name FROM players ORDER BY apg DESC LIMIT 1", conn).iloc[0]["name"]
    return {
        "text": "Who has the **most assists per game** in the league?",
        "answer": top,
        "hint": "Try: SELECT name, apg FROM players ORDER BY apg DESC LIMIT 1",
        "validator_type": "player_name",
    }

def q3_most_wins(conn):
    top = pd.read_sql("SELECT full_name FROM teams ORDER BY wins DESC LIMIT 1", conn).iloc[0]["full_name"]
    return {
        "text": "Which team has the **most wins** this season?",
        "answer": top,
        "hint": "Try: SELECT full_name, wins FROM teams ORDER BY wins DESC LIMIT 1",
        "validator_type": "team_name",
    }

def q3_nth_scorer(conn):
    n = random.choice([2, 3, 4, 5])
    ordinal = {2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}[n]
    top = pd.read_sql(f"SELECT name FROM players ORDER BY ppg DESC LIMIT 1 OFFSET {n - 1}", conn).iloc[0]["name"]
    return {
        "text": f"Who is the **{ordinal} highest scorer** in the league (by PPG)?",
        "answer": top,
        "hint": f"Try: SELECT name, ppg FROM players ORDER BY ppg DESC LIMIT 1 OFFSET {n - 1}",
        "validator_type": "player_name",
    }

def q3_most_rebounds(conn):
    top = pd.read_sql("SELECT name FROM players ORDER BY rpg DESC LIMIT 1", conn).iloc[0]["name"]
    return {
        "text": "Who averages the **most rebounds per game** in the league?",
        "answer": top,
        "hint": "Try: SELECT name, rpg FROM players ORDER BY rpg DESC LIMIT 1",
        "validator_type": "player_name",
    }

def q3_fewest_losses(conn):
    top = pd.read_sql("SELECT full_name FROM teams ORDER BY losses ASC LIMIT 1", conn).iloc[0]["full_name"]
    return {
        "text": "Which team has the **fewest losses** this season?",
        "answer": top,
        "hint": "Try: SELECT full_name, losses FROM teams ORDER BY losses ASC LIMIT 1",
        "validator_type": "team_name",
    }


# ---- LEVEL 4: GROUP BY / AVG / COUNT ----

def q4_team_avg_ppg(conn):
    df = pd.read_sql("""
        SELECT t.full_name, ROUND(AVG(p.ppg), 1) as avg_ppg
        FROM players p JOIN teams t ON p.team_id = t.id
        GROUP BY t.id ORDER BY avg_ppg DESC LIMIT 1
    """, conn)
    return {
        "text": "Which team has the **highest average PPG** across its roster?",
        "answer": df.iloc[0]["full_name"],
        "hint": "Try: SELECT t.full_name, AVG(p.ppg) FROM players p JOIN teams t ON p.team_id = t.id GROUP BY t.id ORDER BY AVG(p.ppg) DESC",
        "validator_type": "team_name",
    }

def q4_position_count(conn):
    positions = pd.read_sql("SELECT DISTINCT position FROM players WHERE position IN ('G', 'F', 'C')", conn)
    if len(positions) == 0:
        positions = pd.read_sql("SELECT DISTINCT position FROM players LIMIT 3", conn)
    pos = positions.sample(1).iloc[0]["position"]
    count = pd.read_sql(f"SELECT COUNT(*) as c FROM players WHERE position = '{pos}'", conn).iloc[0]["c"]
    pos_name = {"G": "Guards", "F": "Forwards", "C": "Centers"}.get(pos, pos)
    return {
        "text": f"How many **{pos_name} (position = '{pos}')** are in the league?",
        "answer": str(int(count)),
        "hint": f"Try: SELECT COUNT(*) FROM players WHERE position = '{pos}'",
        "validator_type": "exact_number",
    }

def q4_conference_wins(conn):
    df = pd.read_sql("SELECT conference, ROUND(AVG(wins), 1) as avg_wins FROM teams GROUP BY conference", conn)
    winner = df.sort_values("avg_wins", ascending=False).iloc[0]["conference"]
    return {
        "text": "Which conference has a **higher average wins** per team: **East** or **West**?",
        "answer": winner,
        "hint": "Try: SELECT conference, AVG(wins) FROM teams GROUP BY conference",
        "validator_type": "conference",
    }

def q4_position_rpg(conn):
    df = pd.read_sql("""
        SELECT position, ROUND(AVG(rpg), 1) as avg_rpg
        FROM players WHERE position IN ('G', 'F', 'C')
        GROUP BY position ORDER BY avg_rpg DESC LIMIT 1
    """, conn)
    if len(df) == 0:
        df = pd.read_sql("SELECT position, ROUND(AVG(rpg),1) as avg_rpg FROM players GROUP BY position ORDER BY avg_rpg DESC LIMIT 1", conn)
    return {
        "text": "Which position (G, F, or C) has the **highest average RPG**?",
        "answer": df.iloc[0]["position"],
        "hint": "Try: SELECT position, AVG(rpg) FROM players GROUP BY position ORDER BY AVG(rpg) DESC",
        "validator_type": "position",
    }

def q4_teams_with_many_players(conn):
    threshold = random.choice([4, 5, 6])
    count = pd.read_sql(f"""
        SELECT COUNT(*) as c FROM (
            SELECT team_id FROM players GROUP BY team_id HAVING COUNT(*) >= {threshold}
        )
    """, conn).iloc[0]["c"]
    return {
        "text": f"How many teams have **at least {threshold} players** on their roster?",
        "answer": str(int(count)),
        "hint": f"Try: SELECT team_id, COUNT(*) as cnt FROM players GROUP BY team_id HAVING COUNT(*) >= {threshold}",
        "validator_type": "exact_number",
    }

def q4_avg_age_by_team(conn):
    df = pd.read_sql("""
        SELECT t.full_name, ROUND(AVG(p.age), 1) as avg_age
        FROM players p JOIN teams t ON p.team_id = t.id
        GROUP BY t.id ORDER BY avg_age DESC LIMIT 1
    """, conn)
    return {
        "text": "Which team has the **oldest roster** (highest average age)?",
        "answer": df.iloc[0]["full_name"],
        "hint": "Try: SELECT t.full_name, AVG(p.age) FROM players p JOIN teams t ON p.team_id = t.id GROUP BY t.id ORDER BY AVG(p.age) DESC",
        "validator_type": "team_name",
    }


# ---- LEVEL 5: JOIN ----

def q5_home_wins(conn):
    team = _random_team(conn)
    count = pd.read_sql(f"""
        SELECT COUNT(*) as c FROM games g
        JOIN teams t ON g.home_team_id = t.id
        WHERE t.full_name = '{team['full_name']}' AND g.home_score > g.away_score
    """, conn).iloc[0]["c"]
    return {
        "text": f"How many **home games** did the **{team['full_name']}** win?",
        "answer": str(int(count)),
        "hint": f"Try: SELECT COUNT(*) FROM games g JOIN teams t ON g.home_team_id = t.id WHERE t.full_name = '{team['full_name']}' AND g.home_score > g.away_score",
        "validator_type": "exact_number",
    }

def q5_top_scorer_on_team(conn):
    team = _random_team(conn)
    top = pd.read_sql(f"""
        SELECT p.name FROM players p
        JOIN teams t ON p.team_id = t.id
        WHERE t.full_name = '{team['full_name']}'
        ORDER BY p.ppg DESC LIMIT 1
    """, conn).iloc[0]["name"]
    return {
        "text": f"Who is the **top scorer** on the **{team['full_name']}**?",
        "answer": top,
        "hint": f"Try: SELECT p.name, p.ppg FROM players p JOIN teams t ON p.team_id = t.id WHERE t.full_name = '{team['full_name']}' ORDER BY p.ppg DESC LIMIT 1",
        "validator_type": "player_name",
        "subject_type": "player",
        "subject_name": top,
    }

def q5_away_losses(conn):
    team = _random_team(conn)
    count = pd.read_sql(f"""
        SELECT COUNT(*) as c FROM games g
        JOIN teams t ON g.away_team_id = t.id
        WHERE t.full_name = '{team['full_name']}' AND g.away_score < g.home_score
    """, conn).iloc[0]["c"]
    return {
        "text": f"How many games did the **{team['full_name']}** lose **on the road** (as away team)?",
        "answer": str(int(count)),
        "hint": f"Try: SELECT COUNT(*) FROM games g JOIN teams t ON g.away_team_id = t.id WHERE t.full_name = '{team['full_name']}' AND g.away_score < g.home_score",
        "validator_type": "exact_number",
    }

def q5_games_between(conn):
    t1 = _random_team(conn)
    t2 = _random_team(conn)
    while t2["id"] == t1["id"]:
        t2 = _random_team(conn)
    count = pd.read_sql(f"""
        SELECT COUNT(*) as c FROM games
        WHERE (home_team_id = {t1['id']} AND away_team_id = {t2['id']})
           OR (home_team_id = {t2['id']} AND away_team_id = {t1['id']})
    """, conn).iloc[0]["c"]
    return {
        "text": f"How many games were played between the **{t1['full_name']}** and the **{t2['full_name']}**?",
        "answer": str(int(count)),
        "hint": "Try: SELECT * FROM games WHERE (home_team_id = X AND away_team_id = Y) OR (home_team_id = Y AND away_team_id = X) — check the teams table for IDs.",
        "validator_type": "exact_number",
    }

def q5_team_total_games(conn):
    team = _random_team(conn)
    count = pd.read_sql(f"""
        SELECT COUNT(*) as c FROM games
        WHERE home_team_id = {team['id']} OR away_team_id = {team['id']}
    """, conn).iloc[0]["c"]
    return {
        "text": f"How many **total games** (home + away) did the **{team['full_name']}** play?",
        "answer": str(int(count)),
        "hint": f"Try: SELECT COUNT(*) FROM games WHERE home_team_id = {team['id']} OR away_team_id = {team['id']}",
        "validator_type": "exact_number",
    }

def q5_biggest_home_win(conn):
    df = pd.read_sql("""
        SELECT t.full_name, (g.home_score - g.away_score) as margin
        FROM games g JOIN teams t ON g.home_team_id = t.id
        WHERE g.home_score > g.away_score
        ORDER BY margin DESC LIMIT 1
    """, conn)
    return {
        "text": "Which team had the **biggest home win** (largest margin of victory at home)?",
        "answer": df.iloc[0]["full_name"],
        "hint": "Try: SELECT t.full_name, (g.home_score - g.away_score) as margin FROM games g JOIN teams t ON g.home_team_id = t.id WHERE g.home_score > g.away_score ORDER BY margin DESC LIMIT 1",
        "validator_type": "team_name",
    }


# ---- WRITE-THE-QUERY questions (dataframe_match) ----

def q3_top5_scorers_query(conn):
    """Level 3 write-the-query: return top 5 scorers by PPG."""
    expected = pd.read_sql(
        "SELECT name, ppg FROM players ORDER BY ppg DESC LIMIT 5", conn
    )
    return {
        "text": (
            "**Write-the-Query Challenge!** 🖊️\n\n"
            "Write a SQL query that returns the **top 5 scorers** in the league, "
            "showing their **name** and **ppg**, sorted by PPG from highest to lowest.\n\n"
            "Your query must return exactly this result:"
        ),
        "answer": expected.to_json(),
        "hint": "Try: SELECT name, ppg FROM players ORDER BY ppg DESC LIMIT 5",
        "validator_type": "dataframe_match",
        "expected_df_json": expected.to_json(),
    }

def q4_avg_by_position_query(conn):
    """Level 4 write-the-query: average PPG grouped by position."""
    expected = pd.read_sql(
        "SELECT position, ROUND(AVG(ppg), 1) as avg_ppg FROM players "
        "WHERE position IN ('G','F','C') GROUP BY position ORDER BY avg_ppg DESC",
        conn
    )
    return {
        "text": (
            "**Write-the-Query Challenge!** 🖊️\n\n"
            "Write a SQL query that shows the **average PPG per position** (G, F, C only), "
            "with columns **position** and **avg_ppg** (rounded to 1 decimal), "
            "sorted from highest to lowest avg_ppg.\n\n"
            "Your query must return exactly this result:"
        ),
        "answer": expected.to_json(),
        "hint": "Try: SELECT position, ROUND(AVG(ppg), 1) as avg_ppg FROM players WHERE position IN ('G','F','C') GROUP BY position ORDER BY avg_ppg DESC",
        "validator_type": "dataframe_match",
        "expected_df_json": expected.to_json(),
    }

def q5_team_top_scorer_query(conn):
    """Level 5 write-the-query: top scorer per team using JOIN."""
    expected = pd.read_sql(
        """SELECT t.full_name, p.name, p.ppg
           FROM players p
           JOIN teams t ON p.team_id = t.id
           WHERE p.ppg = (
               SELECT MAX(p2.ppg) FROM players p2 WHERE p2.team_id = t.id
           )
           ORDER BY t.full_name""",
        conn
    )
    return {
        "text": (
            "**Write-the-Query Challenge!** 🖊️\n\n"
            "Write a SQL query showing the **top scorer on each team**, "
            "with columns **full_name** (team), **name** (player), and **ppg**, "
            "one row per team, sorted alphabetically by team name.\n\n"
            "Your query must return exactly this result:"
        ),
        "answer": expected.to_json(),
        "hint": "Hint: JOIN players and teams, then use a subquery or window function to find the max PPG player per team.",
        "validator_type": "dataframe_match",
        "expected_df_json": expected.to_json(),
    }


# ---------------------------------------------------------------------------
# Question pools
# ---------------------------------------------------------------------------

QUESTION_POOLS = {
    1: [q1_player_count, q1_player_position, q1_player_team, q1_team_city, q1_player_ppg, q1_team_conference],
    2: [q2_ppg_count, q2_guards_assists, q2_team_rebounds, q2_conference_wins, q2_ppg_and_apg, q2_age_filter],
    3: [q3_top_scorer, q3_most_assists, q3_most_wins, q3_nth_scorer, q3_most_rebounds, q3_fewest_losses, q3_top5_scorers_query],
    4: [q4_team_avg_ppg, q4_position_count, q4_conference_wins, q4_position_rpg, q4_teams_with_many_players, q4_avg_age_by_team, q4_avg_by_position_query],
    5: [q5_home_wins, q5_top_scorer_on_team, q5_away_losses, q5_games_between, q5_team_total_games, q5_biggest_home_win, q5_team_top_scorer_query],
}


def generate_question(level, conn):
    """Pick a random question from the level's pool and generate it."""
    pool = QUESTION_POOLS[level]
    func = random.choice(pool)
    try:
        return func(conn)
    except Exception:
        # Retry with a different question if one fails
        for f in random.sample(pool, len(pool)):
            try:
                return f(conn)
            except Exception:
                continue
        return {
            "text": "Error generating question. Click 'New Game' to try again.",
            "answer": "",
            "hint": "",
            "validator_type": "exact_number",
        }


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_session_state():
    defaults = {
        "game_started": False,
        "start_time": None,
        "current_level": 1,
        "questions": {},
        "completed_levels": set(),
        "score": 0,
        "hints_used": {1: False, 2: False, 3: False, 4: False, 5: False},
        "nickname": "",
        "game_finished": False,
        "saved_to_leaderboard": False,
        "last_query_result": {1: None, 2: None, 3: None, 4: None, 5: None},
        "last_query_error": {1: None, 2: None, 3: None, 4: None, 5: None},
        "level_start_times": {},
        "level_scores": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def new_game(conn):
    """Generate 5 random questions and reset state."""
    questions = {}
    for level in range(1, 6):
        questions[level] = generate_question(level, conn)
    st.session_state.questions = questions
    st.session_state.current_level = 1
    st.session_state.completed_levels = set()
    st.session_state.score = 0
    st.session_state.hints_used = {1: False, 2: False, 3: False, 4: False, 5: False}
    st.session_state.start_time = time.time()
    st.session_state.game_started = True
    st.session_state.game_finished = False
    st.session_state.saved_to_leaderboard = False
    st.session_state.last_query_result = {1: None, 2: None, 3: None, 4: None, 5: None}
    st.session_state.last_query_error = {1: None, 2: None, 3: None, 4: None, 5: None}
    st.session_state.level_start_times = {1: time.time()}
    st.session_state.level_scores = {}


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

def save_to_leaderboard(conn, nickname, completion_time, levels, hints, score):
    conn.execute(
        "INSERT INTO leaderboard (nickname, completion_time_seconds, levels_completed, hints_used, score) VALUES (?,?,?,?,?)",
        (nickname, completion_time, levels, hints, score),
    )
    conn.commit()


def get_leaderboard(conn, limit=20):
    try:
        return pd.read_sql(f"""
            SELECT nickname, completion_time_seconds, levels_completed, hints_used, score, played_at
            FROM leaderboard
            WHERE levels_completed = 5
            ORDER BY completion_time_seconds ASC
            LIMIT {limit}
        """, conn)
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Timer formatting
# ---------------------------------------------------------------------------

def format_time(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# Visualization helpers
# ---------------------------------------------------------------------------

def auto_chart(df, key_suffix=""):
    """Auto-detect column types and render the best Plotly chart for a query result."""
    if df is None or len(df) == 0 or len(df.columns) < 2:
        return

    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    text_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    date_like = [c for c in text_cols if any(k in c.lower() for k in ("date", "year", "month"))]

    fig = None

    if date_like and num_cols:
        # Line chart: date/year on x, first numeric on y
        x_col = date_like[0]
        y_col = num_cols[0]
        fig = px.line(df.sort_values(x_col), x=x_col, y=y_col,
                      title=f"{y_col} over {x_col}",
                      color_discrete_sequence=["#E65100"])

    elif text_cols and len(num_cols) == 1:
        # Horizontal bar chart
        x_col = num_cols[0]
        y_col = text_cols[0]
        plot_df = df.copy()
        if len(plot_df) > 20:
            plot_df = plot_df.head(20)
        fig = px.bar(plot_df, x=x_col, y=y_col, orientation="h",
                     title=f"{x_col} by {y_col}",
                     color=x_col, color_continuous_scale="Oranges")
        fig.update_layout(yaxis={"autorange": "reversed"})

    elif text_cols and len(num_cols) >= 2:
        # Grouped bar: first text col as y, all numeric cols as bars
        y_col = text_cols[0]
        plot_df = df.copy()
        if len(plot_df) > 15:
            plot_df = plot_df.head(15)
        melted = plot_df[[y_col] + num_cols].melt(id_vars=y_col, var_name="Stat", value_name="Value")
        fig = px.bar(melted, x="Value", y=y_col, color="Stat", orientation="h",
                     title=f"Stats by {y_col}", barmode="group")
        fig.update_layout(yaxis={"autorange": "reversed"})

    elif len(num_cols) >= 2:
        # Scatter of first two numeric columns
        fig = px.scatter(df, x=num_cols[0], y=num_cols[1],
                         title=f"{num_cols[1]} vs {num_cols[0]}",
                         color_discrete_sequence=["#E65100"])

    if fig:
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        )
        with st.expander("📊 Auto Chart", expanded=True):
            st.plotly_chart(fig, use_container_width=True, key=f"autochart_{key_suffix}")


def render_player_radar(player_name, conn):
    """Render a spider/radar chart of a player's stats relative to the league."""
    try:
        p = pd.read_sql(
            "SELECT ppg, rpg, apg, spg, bpg FROM players WHERE name = ?",
            conn, params=(player_name,)
        )
        if len(p) == 0:
            return
        p = p.iloc[0]
        maxes = pd.read_sql(
            "SELECT MAX(ppg) as ppg, MAX(rpg) as rpg, MAX(apg) as apg, MAX(spg) as spg, MAX(bpg) as bpg FROM players",
            conn
        ).iloc[0]
        # Normalize to 0-10
        stats = {k: round(float(p[k]) / max(float(maxes[k]), 0.01) * 10, 1) for k in ["ppg", "rpg", "apg", "spg", "bpg"]}
        labels = ["PPG", "RPG", "APG", "SPG", "BPG"]
        values = [stats[k] for k in ["ppg", "rpg", "apg", "spg", "bpg"]]
        values_closed = values + [values[0]]
        labels_closed = labels + [labels[0]]

        fig = go.Figure(go.Scatterpolar(
            r=values_closed, theta=labels_closed,
            fill="toself",
            fillcolor="rgba(230,101,0,0.25)",
            line=dict(color="#E65100", width=2),
            name=player_name,
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
            showlegend=False,
            title=dict(text=f"📊 {player_name} — Stats Radar", font=dict(size=13)),
            height=300,
            margin=dict(l=20, r=20, t=50, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        with st.expander("📊 Player Stats Radar", expanded=False):
            st.caption(f"Stats normalized relative to league leaders. Raw: PPG {p['ppg']}, RPG {p['rpg']}, APG {p['apg']}, SPG {p['spg']}, BPG {p['bpg']}")
            st.plotly_chart(fig, use_container_width=True, key=f"radar_player_{player_name}")
    except Exception:
        pass


def render_team_radar(team_name, conn):
    """Render a radar chart of a team's offensive profile (avg stats of roster)."""
    try:
        row = pd.read_sql(
            """SELECT ROUND(AVG(p.ppg),1) as ppg, ROUND(AVG(p.rpg),1) as rpg,
                      ROUND(AVG(p.apg),1) as apg, ROUND(AVG(p.spg),1) as spg,
                      ROUND(AVG(p.bpg),1) as bpg
               FROM players p JOIN teams t ON p.team_id = t.id
               WHERE t.full_name = ?""",
            conn, params=(team_name,)
        )
        if len(row) == 0:
            return
        row = row.iloc[0]
        maxes = pd.read_sql(
            """SELECT MAX(avg_ppg) as ppg, MAX(avg_rpg) as rpg, MAX(avg_apg) as apg,
                      MAX(avg_spg) as spg, MAX(avg_bpg) as bpg FROM (
                SELECT AVG(p.ppg) as avg_ppg, AVG(p.rpg) as avg_rpg, AVG(p.apg) as avg_apg,
                       AVG(p.spg) as avg_spg, AVG(p.bpg) as avg_bpg
                FROM players p GROUP BY p.team_id
            )""",
            conn
        ).iloc[0]
        stats = {k: round(float(row[k]) / max(float(maxes[k]), 0.01) * 10, 1) for k in ["ppg", "rpg", "apg", "spg", "bpg"]}
        labels = ["PPG", "RPG", "APG", "SPG", "BPG"]
        values = [stats[k] for k in ["ppg", "rpg", "apg", "spg", "bpg"]]
        values_closed = values + [values[0]]
        labels_closed = labels + [labels[0]]

        fig = go.Figure(go.Scatterpolar(
            r=values_closed, theta=labels_closed,
            fill="toself",
            fillcolor="rgba(230,101,0,0.25)",
            line=dict(color="#E65100", width=2),
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
            showlegend=False,
            title=dict(text=f"📊 {team_name} — Roster Profile", font=dict(size=13)),
            height=300,
            margin=dict(l=20, r=20, t=50, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        with st.expander("📊 Team Roster Radar", expanded=False):
            st.caption("Average stats per player on roster, normalized relative to league-best team averages.")
            st.plotly_chart(fig, use_container_width=True, key=f"radar_team_{team_name}")
    except Exception:
        pass


def render_er_diagram():
    """Render a clean ER diagram. All shapes and annotations use data coordinates (xref='x', yref='y')."""
    fig = go.Figure()

    # Box layout in data coordinates [0..10, 0..10]
    # Each box: (cx, cy, w, h) — center x, center y, full width, full height
    boxes = {
        "teams":   (5.0, 8.0, 3.6, 2.4),
        "players": (1.8, 3.0, 3.6, 2.8),
        "games":   (8.2, 3.0, 3.6, 2.8),
    }
    colors = {"teams": "#F57C00", "players": "#1565C0", "games": "#2E7D32"}
    fields = {
        "teams":   ["id  (PK)", "full_name", "city", "conference", "wins / losses"],
        "players": ["id  (PK)", "name", "team_id  (FK)", "position", "ppg / rpg / apg"],
        "games":   ["id  (PK)", "home_team_id  (FK)", "away_team_id  (FK)", "home_score", "game_date"],
    }

    MAX_LEN = 20
    shapes = []
    annotations = []

    for tbl, (cx, cy, w, h) in boxes.items():
        x0, x1 = cx - w / 2, cx + w / 2
        y0, y1 = cy - h / 2, cy + h / 2
        header_h = h * 0.28          # top 28% = header
        body_y0 = y0
        body_y1 = y1 - header_h
        header_y0 = body_y1
        header_y1 = y1

        # Header rectangle
        shapes.append(dict(type="rect", x0=x0, x1=x1, y0=header_y0, y1=header_y1,
                           fillcolor=colors[tbl], line=dict(color="white", width=1.5), layer="below"))
        # Body rectangle
        shapes.append(dict(type="rect", x0=x0, x1=x1, y0=body_y0, y1=body_y1,
                           fillcolor="#F7F7F7", line=dict(color="#CCCCCC", width=1), layer="below"))

        # Table name in header (data coords)
        annotations.append(dict(
            x=cx, y=(header_y0 + header_y1) / 2,
            text=f"<b>{tbl}</b>",
            showarrow=False, font=dict(color="white", size=12),
            xref="x", yref="y",
        ))

        # Field rows evenly spaced inside body
        fld_list = fields[tbl]
        n = len(fld_list)
        body_height = body_y1 - body_y0
        for i, fld in enumerate(fld_list):
            # Space evenly from top of body downward
            fy = body_y1 - (i + 0.5) * (body_height / n)
            display = fld if len(fld) <= MAX_LEN else fld[:MAX_LEN - 1] + "…"
            annotations.append(dict(
                x=cx, y=fy,
                text=display,
                showarrow=False, font=dict(color="#333", size=8.5),
                xref="x", yref="y",
            ))

    # Connector: teams → players
    t_cx, t_cy, t_w, _ = boxes["teams"]
    p_cx, p_cy, p_w, _ = boxes["players"]
    shapes.append(dict(type="line",
                       x0=t_cx - t_w / 2, y0=t_cy,
                       x1=p_cx + p_w / 2, y1=p_cy,
                       line=dict(color="#AAAAAA", width=1.5, dash="dot")))
    annotations.append(dict(
        x=(t_cx - t_w/2 + p_cx + p_w/2) / 2,
        y=(t_cy + p_cy) / 2 + 0.25,
        text="team_id",
        showarrow=False, font=dict(color="#777", size=8, style="italic"),
        xref="x", yref="y",
    ))

    # Connector: teams → games
    g_cx, g_cy, g_w, _ = boxes["games"]
    shapes.append(dict(type="line",
                       x0=t_cx + t_w / 2, y0=t_cy,
                       x1=g_cx - g_w / 2, y1=g_cy,
                       line=dict(color="#AAAAAA", width=1.5, dash="dot")))
    annotations.append(dict(
        x=(t_cx + t_w/2 + g_cx - g_w/2) / 2,
        y=(t_cy + g_cy) / 2 + 0.25,
        text="home/away_team_id",
        showarrow=False, font=dict(color="#777", size=8, style="italic"),
        xref="x", yref="y",
    ))

    fig.update_layout(
        shapes=shapes, annotations=annotations,
        xaxis=dict(visible=False, range=[0, 10]),
        yaxis=dict(visible=False, range=[0, 10]),
        height=300,
        margin=dict(l=5, r=5, t=5, b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig



def render_postgame_analytics():
    """Render a radar chart showing SQL skill performance per level after game completion."""
    level_scores = st.session_state.get("level_scores", {})
    hints_used = st.session_state.get("hints_used", {})

    categories = [f"L{l}: {LEVEL_NAMES[l][0]}" for l in range(1, 6)]
    values = [level_scores.get(l, 0) for l in range(1, 6)]
    values_closed = values + [values[0]]
    cats_closed = categories + [categories[0]]

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(go.Scatterpolar(
            r=values_closed,
            theta=cats_closed,
            fill="toself",
            fillcolor="rgba(230,101,0,0.25)",
            line=dict(color="#E65100", width=2.5),
            name="Your Score",
        ))
        # Perfect score reference
        fig.add_trace(go.Scatterpolar(
            r=[100, 100, 100, 100, 100, 100],
            theta=cats_closed,
            fill="toself",
            fillcolor="rgba(0,150,0,0.05)",
            line=dict(color="rgba(0,150,0,0.4)", width=1, dash="dot"),
            name="Perfect Score",
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            title=dict(text="Your SQL Skill Radar", font=dict(size=14)),
            height=320,
            margin=dict(l=20, r=20, t=50, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=-0.15),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Per-Level Breakdown")
        for lv in range(1, 6):
            skill, _ = LEVEL_NAMES[lv]
            score = level_scores.get(lv, 0)
            used_hint = hints_used.get(lv, False)
            icon = "✅" if score == 100 else ("💡" if used_hint else "⚡")
            st.markdown(f"{icon} **Level {lv} — {skill}**: {score}/100 pts"
                        + (" *(hint used)*" if used_hint else ""))
        total = sum(values)
        pct = round(total / 500 * 100)
        st.markdown("---")
        st.markdown(f"**Total: {total}/500 pts ({pct}%)**")
        if pct == 100:
            st.success("Perfect SQL master! 🏆")
        elif pct >= 80:
            st.info("Excellent SQL skills! Keep it up.")
        elif pct >= 60:
            st.warning("Good effort! Review the levels where you used hints.")
        else:
            st.error("Keep practicing — SQL takes time to master!")


# ---------------------------------------------------------------------------
# UI — Header
# ---------------------------------------------------------------------------

def render_header():
    st.markdown("""
    <h1 style='text-align: center; color: #E65100;'>
        🏀 NBA SQL Trivia
    </h1>
    <p style='text-align: center; color: #666; font-size: 1.1em;'>
        Test your SQL skills with real NBA data — every game is different!
    </p>
    """, unsafe_allow_html=True)

    if st.session_state.game_started and not st.session_state.game_finished:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            start_epoch = st.session_state.start_time
            st.components.v1.html(f"""
<script>
var _startEpoch = {start_epoch};
function _updateTimer() {{
    var elapsed = Date.now()/1000 - _startEpoch;
    var m = Math.floor(elapsed/60);
    var s = Math.floor(elapsed%60);
    var el = document.getElementById('live-timer');
    if (el) el.innerText = (m<10?'0':'')+m+':'+(s<10?'0':'')+s;
}}
setInterval(_updateTimer, 1000);
_updateTimer();
</script>
<div style='text-align:center; padding-top:4px;'>
  <div style='font-size:0.8em; color:#888; margin-bottom:2px;'>⏱ Time</div>
  <div style='font-size:2.4em; font-weight:700; color:#E65100; font-family:monospace;' id='live-timer'>00:00</div>
</div>
""", height=75)
        with c2:
            st.metric("📊 Score", st.session_state.score)
        with c3:
            done = len(st.session_state.completed_levels)
            st.metric("✅ Progress", f"{done}/5")
        with c4:
            hints = sum(1 for v in st.session_state.hints_used.values() if v)
            st.metric("💡 Hints", hints)

        st.progress(len(st.session_state.completed_levels) / 5)


# ---------------------------------------------------------------------------
# UI — Sidebar
# ---------------------------------------------------------------------------

def render_sidebar(conn):
    with st.sidebar:
        st.markdown("### 🔍 Quick ID Lookup")
        st.caption("Find IDs without writing SQL")
        lookup_type = st.radio("Look up:", ["Player", "Team"], horizontal=True, key="lookup_type")
        try:
            if lookup_type == "Player":
                players_df = pd.read_sql(
                    "SELECT id, name, team_id FROM players ORDER BY name", conn
                )
                selected = st.selectbox(
                    "Player:", [""] + list(players_df["name"]), key="lookup_player",
                    label_visibility="collapsed"
                )
                if selected:
                    row = players_df[players_df["name"] == selected].iloc[0]
                    team_name = pd.read_sql(
                        f"SELECT full_name FROM teams WHERE id = {row['team_id']}", conn
                    ).iloc[0]["full_name"]
                    st.code(f"player id  = {int(row['id'])}\nteam_id    = {int(row['team_id'])}")
                    st.caption(f"Team: {team_name}")
            else:
                teams_df = pd.read_sql(
                    "SELECT id, full_name, abbreviation FROM teams ORDER BY full_name", conn
                )
                selected = st.selectbox(
                    "Team:", [""] + list(teams_df["full_name"]), key="lookup_team",
                    label_visibility="collapsed"
                )
                if selected:
                    row = teams_df[teams_df["full_name"] == selected].iloc[0]
                    st.code(f"team id    = {int(row['id'])}\nabbrev.    = {row['abbreviation']}")
        except Exception:
            st.caption("Lookup unavailable.")

        st.markdown("---")
        st.markdown("### 📋 Database Schema")

        tables = {
            "teams": "NBA teams with win/loss records",
            "players": "Player stats (PPG, RPG, APG, etc.)",
            "games": "Game results with scores",
        }
        for table, desc in tables.items():
            with st.expander(f"📁 {table}"):
                st.caption(desc)
                try:
                    schema = pd.read_sql(f"PRAGMA table_info({table})", conn)
                    st.dataframe(schema[["name", "type"]], use_container_width=True, hide_index=True)
                    sample = pd.read_sql(f"SELECT * FROM {table} LIMIT 3", conn)
                    st.caption("Sample data:")
                    st.dataframe(sample, use_container_width=True, hide_index=True)
                except Exception:
                    pass

        st.markdown("---")
        st.markdown("### 🗺 Relationships")
        er_fig = render_er_diagram()
        st.plotly_chart(er_fig, use_container_width=True, key="er_diagram")

        st.markdown("---")
        st.markdown("### 📖 SQL Cheat Sheet")
        with st.expander("SELECT"):
            st.code("SELECT * FROM table_name\nSELECT col1, col2 FROM table_name")
        with st.expander("WHERE"):
            st.code("SELECT * FROM players\nWHERE ppg > 20 AND position = 'G'")
        with st.expander("ORDER BY / LIMIT"):
            st.code("SELECT * FROM players\nORDER BY ppg DESC\nLIMIT 5")
        with st.expander("GROUP BY / HAVING"):
            st.code("SELECT position, AVG(ppg)\nFROM players\nGROUP BY position\nHAVING AVG(ppg) > 10")
        with st.expander("JOIN"):
            st.code("SELECT p.name, t.full_name\nFROM players p\nJOIN teams t ON p.team_id = t.id")



# ---------------------------------------------------------------------------
# UI — Game Tab
# ---------------------------------------------------------------------------

def render_game_tab(conn):
    if not st.session_state.game_started:
        render_welcome(conn)
        return

    if st.session_state.game_finished:
        render_victory(conn)
        return

    level = st.session_state.current_level
    skill, desc = LEVEL_NAMES[level]
    q = st.session_state.questions.get(level)

    if not q:
        st.error("Error loading question. Try starting a new game.")
        return

    # Level header
    st.markdown(f"""
    <p style='margin: 0 0 14px; font-size: 1.2em;'>
        <span style='color: #E65100; font-weight: 600;'>Level {level}/5</span>
        <span style='color: #999; margin: 0 8px;'>·</span>
        <span style='color: #555;'>{skill}</span>
        <span style='color: #999; margin: 0 8px;'>·</span>
        <span style='color: #888; font-style: italic;'>{desc}</span>
    </p>
    """, unsafe_allow_html=True)

    # Question
    st.markdown(f"### ❓ {q['text']}")

    # Show radar chart if question is about a specific player or team
    subj_type = q.get("subject_type")
    subj_name = q.get("subject_name")
    if subj_type == "player" and subj_name:
        render_player_radar(subj_name, conn)
    elif subj_type == "team" and subj_name:
        render_team_radar(subj_name, conn)

    # Answer guidance + submission — placed ABOVE the SQL editor so it's always visible
    vtype = q.get("validator_type", "")
    is_df_match = vtype == "dataframe_match"

    if vtype == "name_from_set":
        st.info("💬 **How to answer:** Use SQL below to find eligible players, then type **any one** valid player name here. First name, last name, or full name all work.")
    elif vtype in ("player_name", "team_name"):
        st.caption("Tip: You can type just the last name or team nickname.")

    # For dataframe_match: show expected output above the answer section
    if is_df_match and q.get("expected_df_json"):
        st.markdown("**Expected output — your query must return exactly this:**")
        try:
            expected_preview = pd.read_json(q["expected_df_json"])
            st.dataframe(expected_preview, use_container_width=True, hide_index=True)
        except Exception:
            pass

    # Answer input + submit buttons in a tight row
    if is_df_match:
        col_ans, col_sub, col_new = st.columns([3, 1.5, 1.2])
        with col_ans:
            st.markdown("When your query matches the table above:")
        answer = "df_match_submit"
        submit_label = "✅ Submit Query"
    else:
        col_ans, col_sub, col_new = st.columns([3, 1.5, 1.2])
        with col_ans:
            ans_key = f"answer_{level}"
            answer = st.text_input("Answer", key=ans_key, label_visibility="collapsed",
                                   placeholder="Your answer here...")
        submit_label = "✅ Submit"

    with col_sub:
        submit_clicked = st.button(submit_label, type="primary", use_container_width=True)
    with col_new:
        if st.button("🔄 New Game", use_container_width=True, help="Start over"):
            new_game(conn)
            st.rerun()

    if submit_clicked:
        check_val = answer if not is_df_match else "df_match_submit"
        if not is_df_match and not answer.strip():
            st.warning("Please type an answer first!")
        elif validate_answer(check_val, q["answer"], q["validator_type"], conn):
            points = POINTS_PER_LEVEL - (HINT_PENALTY if st.session_state.hints_used.get(level, False) else 0)
            st.session_state.score += points
            st.session_state.completed_levels.add(level)
            st.session_state.level_scores[level] = points
            if level < 5:
                st.session_state.level_start_times[level + 1] = time.time()

            if level < 5:
                st.session_state.current_level = level + 1
                st.balloons()
                st.success(f"🎉 Correct! +{points} points. Moving to Level {level + 1}!")
                time.sleep(1.5)
                st.rerun()
            else:
                st.session_state.game_finished = True
                st.balloons()
                st.rerun()
        else:
            st.error("❌ Not quite! Check your SQL results and try again.")

    st.markdown("---")

    # Hint button
    col_hint_btn, col_hint_spacer = st.columns([1, 3])
    with col_hint_btn:
        hint_used = st.session_state.hints_used.get(level, False)
        hint_clicked = st.button(
            "💡 Hint (-10 pts)" if not hint_used else "💡 Hint (used)",
            disabled=hint_used,
            use_container_width=True,
        )
    if hint_clicked and not hint_used:
        st.session_state.hints_used[level] = True
        st.rerun()
    if st.session_state.hints_used.get(level, False) and q["hint"]:
        st.info(f"💡 **Hint:** {q['hint']}")

    # SQL Editor — below the answer section
    st.markdown("**Write SQL to explore the data:**")
    sql_key = f"sql_editor_{level}"
    sql = st.text_area(
        "SQL Query",
        value="",
        height=120,
        key=sql_key,
        placeholder="SELECT * FROM players WHERE ...",
        label_visibility="collapsed",
    )
    run_clicked = st.button("▶ Run Query", type="primary", use_container_width=True)

    # Run query — store result in session state
    if run_clicked and sql.strip():
        result = run_query(sql)
        if isinstance(result, pd.DataFrame):
            st.session_state.last_query_result[level] = result
            st.session_state.last_query_error[level] = None
        else:
            st.session_state.last_query_error[level] = result
            st.session_state.last_query_result[level] = None

    # Always show last result (persists across reruns)
    last_result = st.session_state.get("last_query_result", {}).get(level)
    last_error = st.session_state.get("last_query_error", {}).get(level)
    if last_result is not None and isinstance(last_result, pd.DataFrame):
        st.markdown(f"**Results** ({len(last_result)} rows):")
        st.dataframe(last_result, use_container_width=True, hide_index=True)
    elif last_error:
        st.error(last_error)


def render_welcome(conn):
    st.markdown("""
    <div style='text-align: center; padding: 30px; background: linear-gradient(135deg, #FFF3E0, #FFE0B2);
                border-radius: 15px; margin: 20px 0;'>
        <h2 style='color: #E65100;'>Welcome to NBA SQL Trivia!</h2>
        <p style='color: #795548; font-size: 1.1em;'>
            Answer 5 NBA trivia questions using SQL queries.<br>
            Every game has different questions — you need SQL skills, not memorization!<br>
            Race the clock and compete for the best time.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### How it works:")
    st.markdown("""
    1. Each level asks a trivia question about real NBA data
    2. Write SQL queries to explore the database and find the answer
    3. Type your answer and submit — correct answers advance you to the next level
    4. Use hints if you're stuck (costs 10 points each)
    5. Complete all 5 levels as fast as you can!
    """)

    st.markdown("#### SQL Skills by Level:")
    for lv, (skill, desc) in LEVEL_NAMES.items():
        st.markdown(f"**Level {lv}:** {skill} — {desc}")

    st.markdown("---")
    nickname = st.text_input("Enter your nickname:", placeholder="Your name for the leaderboard...")
    if st.button("🚀 Start Game!", type="primary", disabled=not nickname.strip()):
        st.session_state.nickname = nickname.strip()
        new_game(conn)
        st.rerun()


def render_victory(conn):
    elapsed = time.time() - st.session_state.start_time
    total_hints = sum(1 for v in st.session_state.hints_used.values() if v)

    st.markdown(f"""
    <div style='text-align: center; padding: 40px; background: linear-gradient(135deg, #E8F5E9, #C8E6C9);
                border-radius: 15px; margin: 20px 0; border: 2px solid #4CAF50;'>
        <h1 style='color: #2E7D32;'>🏆 Champion!</h1>
        <p style='font-size: 1.3em; color: #1B5E20;'>
            You completed all 5 levels!
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("⏱ Total Time", format_time(elapsed))
    with c2:
        st.metric("📊 Final Score", st.session_state.score)
    with c3:
        st.metric("💡 Hints Used", total_hints)

    # Save to leaderboard
    if not st.session_state.saved_to_leaderboard:
        try:
            save_to_leaderboard(conn, st.session_state.nickname, elapsed, 5, total_hints, st.session_state.score)
            st.session_state.saved_to_leaderboard = True
            st.success("Score saved to leaderboard!")
        except Exception as e:
            st.warning(f"Could not save to leaderboard: {e}")

    # Post-game analytics
    st.markdown("---")
    st.markdown("### 📊 Your SQL Performance")
    render_postgame_analytics()

    st.markdown("---")
    if st.button("🔄 Play Again", type="primary"):
        new_game(conn)
        st.rerun()


# ---------------------------------------------------------------------------
# UI — Leaderboard Tab
# ---------------------------------------------------------------------------

def render_podium(lb):
    """Render an Olympic-style podium for the top 3 players."""
    fig = go.Figure()

    # Podium order: silver (2nd) left, gold (1st) center, bronze (3rd) right
    configs = [
        (2.0, 2.2, "#A8A9AD", "🥈 2nd", 1),   # silver
        (5.0, 3.2, "#FFD700", "🥇 1st", 0),   # gold
        (8.0, 1.5, "#CD7F32", "🥉 3rd", 2),   # bronze
    ]

    for cx, h, color, label, idx in configs:
        if idx >= len(lb):
            continue
        row = lb.iloc[idx]

        # Platform
        fig.add_shape(type="rect", x0=cx - 1.1, x1=cx + 1.1, y0=0, y1=h,
                      fillcolor=color, line=dict(color="white", width=2), layer="below")

        # Rank label inside platform
        fig.add_annotation(x=cx, y=h / 2, text=f"<b>{label}</b>",
                           showarrow=False, font=dict(size=13, color="white"),
                           xref="x", yref="y")

        # Nickname above platform
        nick = str(row["Nickname"])[:14] + ("…" if len(str(row["Nickname"])) > 14 else "")
        fig.add_annotation(x=cx, y=h + 0.35, text=f"<b>{nick}</b>",
                           showarrow=False, font=dict(size=11, color="#222"),
                           xref="x", yref="y")

        # Score + time
        fig.add_annotation(x=cx, y=h + 0.80,
                           text=f"⭐ {int(row['Score'])} pts  ⏱ {row['Time']}",
                           showarrow=False, font=dict(size=9.5, color="#555"),
                           xref="x", yref="y")

    # Floor line
    fig.add_shape(type="line", x0=0.5, x1=9.5, y0=0, y1=0,
                  line=dict(color="#CCCCCC", width=2))

    fig.update_layout(
        xaxis=dict(visible=False, range=[0, 10]),
        yaxis=dict(visible=False, range=[-0.2, 4.8]),
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_leaderboard_tab(conn):
    st.markdown("### 🏆 Leaderboard — Top SQL Players")
    lb = get_leaderboard(conn)
    if len(lb) == 0:
        st.info("No completed games yet. Be the first to finish all 5 levels!")
        return

    lb = lb.reset_index(drop=True)
    lb.columns = ["Nickname", "Time (s)", "Levels", "Hints", "Score", "Date"]
    lb["Time"] = lb["Time (s)"].apply(format_time)
    lb["Rank"] = range(1, len(lb) + 1)

    # Podium for top 3
    st.plotly_chart(render_podium(lb), use_container_width=True)

    # Full rankings table
    st.markdown("#### Full Rankings")
    display_df = lb[["Rank", "Nickname", "Time", "Score", "Hints", "Date"]].copy()
    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# UI — Practice Tab
# ---------------------------------------------------------------------------

def render_practice_tab(conn):
    st.markdown("### 🏃 Practice Court")
    st.markdown("Free SQL sandbox — explore the NBA database without any scoring.")

    sql = st.text_area(
        "SQL Query",
        value="-- Try any SELECT query!\nSELECT * FROM teams ORDER BY wins DESC",
        height=120,
        key="practice_sql",
        label_visibility="collapsed",
    )

    if st.button("▶ Run Query", key="practice_run", type="primary"):
        result = run_query(sql)
        if isinstance(result, pd.DataFrame):
            st.markdown(f"**Results** ({len(result)} rows):")
            st.dataframe(result, use_container_width=True, hide_index=True)
            auto_chart(result, key_suffix="practice")
        else:
            st.error(result)

    with st.expander("📝 Example Queries"):
        examples = {
            "All teams sorted by wins": "SELECT * FROM teams ORDER BY wins DESC",
            "Top 10 scorers": "SELECT name, ppg, position FROM players ORDER BY ppg DESC LIMIT 10",
            "Players per team": "SELECT t.full_name, COUNT(*) as player_count FROM players p JOIN teams t ON p.team_id = t.id GROUP BY t.id ORDER BY player_count DESC",
            "Guards averaging 20+ PPG": "SELECT name, ppg, apg FROM players WHERE position LIKE '%G%' AND ppg >= 20 ORDER BY ppg DESC",
            "Home wins per team": "SELECT t.full_name, COUNT(*) as home_wins FROM games g JOIN teams t ON g.home_team_id = t.id WHERE g.home_score > g.away_score GROUP BY t.id ORDER BY home_wins DESC",
            "Average stats by position": "SELECT position, ROUND(AVG(ppg),1) as avg_ppg, ROUND(AVG(rpg),1) as avg_rpg, ROUND(AVG(apg),1) as avg_apg FROM players GROUP BY position",
        }
        for label, query in examples.items():
            st.markdown(f"**{label}:**")
            st.code(query, language="sql")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="NBA SQL Trivia",
        page_icon="🏀",
        layout="wide",
    )

    fetch_and_cache_data()
    conn = get_connection()

    init_session_state()
    render_header()
    render_sidebar(conn)

    tab_game, tab_leaderboard, tab_practice = st.tabs(["🏀 Game", "🏆 Leaderboard", "🏃 Practice"])

    with tab_game:
        render_game_tab(conn)
    with tab_leaderboard:
        render_leaderboard_tab(conn)
    with tab_practice:
        render_practice_tab(conn)

    conn.close()


if __name__ == "__main__":
    main()
