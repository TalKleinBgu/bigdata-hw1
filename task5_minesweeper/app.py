"""
SQL Minesweeper — Task 5
Classic Minesweeper + NBA SQL rescue challenges when you hit a mine.
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
import time
import random
import shutil
from collections import deque

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DIR, "minesweeper.db")
_TASK4_DB = os.path.join(_DIR, "..", "task4_sql_game", "nba_trivia.db")

DIFFICULTIES = {
    "Easy":   {"rows": 9,  "cols": 9,  "mines": 10},
    "Medium": {"rows": 16, "cols": 16, "mines": 40},
    "Expert": {"rows": 16, "cols": 30, "mines": 99},
}

LEVEL_NAMES = {
    1: ("SELECT *",               "Basic Retrieval"),
    2: ("WHERE / AND / OR",       "Filtering"),
    3: ("ORDER BY / LIMIT",       "Sorting & Ranking"),
    4: ("GROUP BY / Aggregates",  "Aggregation"),
    5: ("JOIN",                   "Combining Tables"),
}

SCORE_BASE = {"Easy": 500, "Medium": 1_000, "Expert": 2_000}
LEVEL_ACCENT = {1: "#4A90D9", 2: "#43A047", 3: "#F57C00", 4: "#8E24AA", 5: "#E53935"}

# ──────────────────────────────────────────────────────────────────────────────
# Database setup
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_connection():
    _init_db()
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _init_db():
    if os.path.exists(DB_PATH):
        _ensure_leaderboard()
        return
    if os.path.exists(_TASK4_DB):
        shutil.copy2(_TASK4_DB, DB_PATH)
        _ensure_leaderboard()
        return
    # Create from scratch
    conn = sqlite3.connect(DB_PATH)
    _create_schema(conn)
    try:
        _fetch_from_api(conn)
    except Exception:
        conn.close()
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        conn = sqlite3.connect(DB_PATH)
        _create_schema(conn)
        _create_fallback_data(conn)
    conn.close()
    _ensure_leaderboard()


def _ensure_leaderboard():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ms_leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            completion_time_seconds REAL NOT NULL,
            mines_hit INTEGER NOT NULL DEFAULT 0,
            max_sql_level INTEGER NOT NULL DEFAULT 0,
            hints_used INTEGER NOT NULL DEFAULT 0,
            score INTEGER NOT NULL DEFAULT 0,
            played_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def _create_schema(conn):
    conn.executescript("""
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
        CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_id);
        CREATE INDEX IF NOT EXISTS idx_players_position ON players(position);
        CREATE INDEX IF NOT EXISTS idx_games_home ON games(home_team_id);
        CREATE INDEX IF NOT EXISTS idx_games_away ON games(away_team_id);
    """)
    conn.commit()


def _fetch_from_api(conn):
    from nba_api.stats.static import teams as nba_teams
    from nba_api.stats.endpoints import LeagueDashPlayerStats, LeagueStandings, LeagueGameLog
    import time as _t

    all_teams = nba_teams.get_teams()
    standings = LeagueStandings(season="2024-25", season_type="Regular Season")
    _t.sleep(0.7)
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

    player_stats = LeagueDashPlayerStats(season="2024-25", per_mode_detailed="PerGame")
    _t.sleep(0.7)
    ps_df = player_stats.get_data_frames()[0]
    ps_df = ps_df[ps_df["GP"] > 0]

    pos_map = {}
    try:
        from nba_api.stats.endpoints import PlayerIndex
        _t.sleep(0.7)
        pi = PlayerIndex(season="2024-25")
        pi_df = pi.get_data_frames()[0]
        if "PERSON_ID" in pi_df.columns and "POSITION" in pi_df.columns:
            pos_map = {int(r["PERSON_ID"]): str(r["POSITION"]) for _, r in pi_df.iterrows()}
    except Exception:
        pass

    for _, p in ps_df.iterrows():
        pid = int(p["PLAYER_ID"])
        pos_raw = pos_map.get(pid) or str(p.get("PLAYER_POSITION", ""))
        conn.execute(
            "INSERT INTO players VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                pid, p["PLAYER_NAME"], int(p["TEAM_ID"]),
                _normalize_position(pos_raw),
                int(p["AGE"]) if pd.notna(p.get("AGE")) else None,
                round(float(p.get("PTS", 0)), 1), round(float(p.get("REB", 0)), 1),
                round(float(p.get("AST", 0)), 1), round(float(p.get("STL", 0)), 1),
                round(float(p.get("BLK", 0)), 1), round(float(p.get("FG_PCT", 0)) * 100, 1),
                round(float(p.get("FG3_PCT", 0)) * 100, 1), round(float(p.get("FT_PCT", 0)) * 100, 1),
                int(p.get("GP", 0)),
            ),
        )
    conn.commit()

    _t.sleep(0.7)
    game_log = LeagueGameLog(season="2024-25", season_type_all_star="Regular Season")
    gl_df = game_log.get_data_frames()[0]
    inserted = set()
    for _, g in gl_df.iterrows():
        gid = g["GAME_ID"]
        if gid in inserted:
            continue
        inserted.add(gid)
        matchup = str(g["MATCHUP"])
        tid = int(g["TEAM_ID"])
        pts = int(g["PTS"]) if pd.notna(g["PTS"]) else 0
        other = gl_df[(gl_df["GAME_ID"] == gid) & (gl_df["TEAM_ID"] != tid)]
        if len(other) == 0:
            continue
        other = other.iloc[0]
        oid = int(other["TEAM_ID"])
        opts = int(other["PTS"]) if pd.notna(other["PTS"]) else 0
        if "vs." in matchup:
            h, a, hs, as_ = tid, oid, pts, opts
        else:
            h, a, hs, as_ = oid, tid, opts, pts
        conn.execute(
            "INSERT INTO games (home_team_id, away_team_id, home_score, away_score, game_date) VALUES (?,?,?,?,?)",
            (h, a, hs, as_, str(g["GAME_DATE"])),
        )
    conn.commit()


def _normalize_position(pos):
    if not pos or str(pos).strip().upper() in ("N/A", "NONE", "NAN", ""):
        return "N/A"
    pos = str(pos).strip().upper()
    mapping = {
        "GUARD": "G", "POINT GUARD": "G", "SHOOTING GUARD": "G",
        "FORWARD": "F", "SMALL FORWARD": "F", "POWER FORWARD": "F",
        "CENTER": "C", "CENTRE": "C",
        "GUARD-FORWARD": "G-F", "FORWARD-GUARD": "F-G",
        "FORWARD-CENTER": "F-C", "CENTER-FORWARD": "C-F",
        "G": "G", "F": "F", "C": "C",
        "G-F": "G-F", "F-G": "F-G", "F-C": "F-C", "C-F": "C-F",
        "PG": "G", "SG": "G", "SF": "F", "PF": "F",
        "PG-SG": "G", "SG-PG": "G", "SF-PF": "F", "PF-SF": "F",
        "PF-C": "F-C", "C-PF": "C-F", "SG-SF": "G-F", "SF-SG": "F-G",
    }
    if pos in mapping:
        return mapping[pos]
    if pos.startswith("G"):
        return "G"
    if pos.startswith("F"):
        return "F"
    if pos.startswith("C"):
        return "C"
    return "N/A"


def _create_fallback_data(conn):
    teams_data = [
        (1610612737, "Atlanta Hawks",          "ATL", "Atlanta",       "East", "Southeast", 36, 46),
        (1610612738, "Boston Celtics",          "BOS", "Boston",        "East", "Atlantic",  58, 24),
        (1610612739, "Cleveland Cavaliers",     "CLE", "Cleveland",     "East", "Central",   52, 30),
        (1610612740, "New Orleans Pelicans",    "NOP", "New Orleans",   "West", "Southwest", 30, 52),
        (1610612741, "Chicago Bulls",           "CHI", "Chicago",       "East", "Central",   32, 50),
        (1610612742, "Dallas Mavericks",        "DAL", "Dallas",        "West", "Southwest", 48, 34),
        (1610612743, "Denver Nuggets",          "DEN", "Denver",        "West", "Northwest", 50, 32),
        (1610612744, "Golden State Warriors",   "GSW", "Golden State",  "West", "Pacific",   44, 38),
        (1610612745, "Houston Rockets",         "HOU", "Houston",       "West", "Southwest", 41, 41),
        (1610612746, "LA Clippers",             "LAC", "Los Angeles",   "West", "Pacific",   38, 44),
        (1610612747, "Los Angeles Lakers",      "LAL", "Los Angeles",   "West", "Pacific",   46, 36),
        (1610612748, "Miami Heat",              "MIA", "Miami",         "East", "Southeast", 40, 42),
        (1610612749, "Milwaukee Bucks",         "MIL", "Milwaukee",     "East", "Central",   49, 33),
        (1610612750, "Minnesota Timberwolves",  "MIN", "Minnesota",     "West", "Northwest", 52, 30),
        (1610612751, "Brooklyn Nets",           "BKN", "Brooklyn",      "East", "Atlantic",  26, 56),
        (1610612752, "New York Knicks",         "NYK", "New York",      "East", "Atlantic",  50, 32),
        (1610612753, "Orlando Magic",           "ORL", "Orlando",       "East", "Southeast", 47, 35),
        (1610612754, "Indiana Pacers",          "IND", "Indiana",       "East", "Central",   45, 37),
        (1610612755, "Philadelphia 76ers",      "PHI", "Philadelphia",  "East", "Atlantic",  38, 44),
        (1610612756, "Phoenix Suns",            "PHX", "Phoenix",       "West", "Pacific",   42, 40),
        (1610612757, "Portland Trail Blazers",  "POR", "Portland",      "West", "Northwest", 22, 60),
        (1610612758, "Sacramento Kings",        "SAC", "Sacramento",    "West", "Pacific",   40, 42),
        (1610612759, "San Antonio Spurs",       "SAS", "San Antonio",   "West", "Southwest", 34, 48),
        (1610612760, "Oklahoma City Thunder",   "OKC", "Oklahoma City", "West", "Northwest", 57, 25),
        (1610612761, "Toronto Raptors",         "TOR", "Toronto",       "East", "Atlantic",  25, 57),
        (1610612762, "Utah Jazz",               "UTA", "Utah",          "West", "Northwest", 28, 54),
        (1610612763, "Memphis Grizzlies",       "MEM", "Memphis",       "West", "Southwest", 46, 36),
        (1610612764, "Washington Wizards",      "WAS", "Washington",    "East", "Southeast", 20, 62),
        (1610612765, "Detroit Pistons",         "DET", "Detroit",       "East", "Central",   24, 58),
        (1610612766, "Charlotte Hornets",       "CHA", "Charlotte",     "East", "Southeast", 22, 60),
    ]
    conn.executemany("INSERT INTO teams VALUES (?,?,?,?,?,?,?,?)", teams_data)

    players_data = [
        (1,  "Jayson Tatum",             1610612738, "F",   27, 27.1, 8.4,  5.5, 1.1, 0.6, 47.2, 37.6, 85.3, 74),
        (2,  "Jaylen Brown",             1610612738, "G-F", 28, 23.5, 5.5,  3.6, 1.2, 0.5, 49.1, 35.4, 70.5, 70),
        (3,  "Derrick White",            1610612738, "G",   30, 15.8, 4.3,  5.2, 0.9, 1.2, 46.1, 39.5, 89.0, 73),
        (4,  "Kristaps Porzingis",       1610612738, "C",   29, 20.3, 7.2,  2.0, 0.7, 1.9, 51.5, 37.2, 85.7, 55),
        (5,  "Jrue Holiday",             1610612738, "G",   34, 12.5, 5.4,  4.5, 0.9, 0.6, 48.0, 42.1, 82.3, 68),
        (6,  "Shai Gilgeous-Alexander",  1610612760, "G",   26, 30.4, 5.5,  6.2, 2.0, 0.7, 53.5, 35.3, 87.4, 75),
        (7,  "Jalen Williams",           1610612760, "G-F", 24, 20.8, 5.5,  5.1, 1.3, 0.6, 53.2, 35.0, 80.2, 72),
        (8,  "Chet Holmgren",            1610612760, "C",   22, 16.5, 7.9,  2.6, 0.8, 2.5, 53.0, 34.8, 79.5, 68),
        (9,  "Lu Dort",                  1610612760, "G",   25, 10.2, 4.0,  1.8, 1.1, 0.3, 42.5, 36.2, 78.0, 70),
        (10, "Isaiah Hartenstein",       1610612760, "C",   26, 12.0, 12.1, 4.1, 0.8, 1.0, 58.2, 15.0, 68.0, 65),
        (11, "Nikola Jokic",             1610612743, "C",   29, 26.4, 12.4, 9.8, 1.4, 0.9, 58.3, 39.6, 81.7, 74),
        (12, "Jamal Murray",             1610612743, "G",   27, 21.2, 4.0,  6.5, 1.0, 0.3, 48.1, 35.8, 85.0, 62),
        (13, "Michael Porter Jr.",       1610612743, "F",   26, 18.7, 7.1,  1.5, 0.6, 0.8, 50.3, 40.1, 82.0, 65),
        (14, "Aaron Gordon",             1610612743, "F",   29, 14.2, 6.5,  3.5, 0.7, 0.6, 55.1, 33.2, 73.0, 70),
        (15, "Christian Braun",          1610612743, "G-F", 24, 11.8, 5.2,  3.4, 1.2, 0.5, 49.0, 38.0, 80.0, 72),
        (16, "Giannis Antetokounmpo",    1610612749, "F",   30, 31.5, 11.9, 6.5, 1.2, 1.1, 61.1, 27.4, 65.7, 73),
        (17, "Damian Lillard",           1610612749, "G",   34, 25.7, 4.6,  7.4, 1.0, 0.3, 45.0, 35.4, 92.3, 72),
        (18, "Khris Middleton",          1610612749, "F",   33, 14.8, 4.5,  4.8, 0.8, 0.3, 46.0, 38.5, 87.0, 50),
        (19, "Brook Lopez",              1610612749, "C",   36, 12.5, 5.2,  1.5, 0.3, 2.4, 48.0, 36.0, 73.0, 72),
        (20, "Bobby Portis",             1610612749, "F-C", 29, 13.8, 7.8,  1.4, 0.5, 0.4, 47.5, 37.0, 80.0, 68),
        (21, "Luka Doncic",             1610612742, "G-F", 25, 28.8, 8.3,  7.8, 1.4, 0.5, 48.7, 35.4, 78.6, 70),
        (22, "Kyrie Irving",             1610612742, "G",   32, 24.2, 5.0,  5.2, 1.3, 0.4, 49.7, 41.1, 90.5, 72),
        (23, "PJ Washington",            1610612742, "F",   26, 13.5, 7.1,  2.1, 1.0, 0.8, 45.5, 33.0, 71.0, 74),
        (24, "Daniel Gafford",           1610612742, "C",   26, 10.8, 5.8,  1.0, 0.5, 1.8, 68.0,  0.0, 65.5, 68),
        (25, "Klay Thompson",            1610612742, "G",   34, 17.2, 3.5,  2.4, 0.7, 0.5, 44.5, 38.7, 88.0, 72),
        (26, "Anthony Davis",            1610612747, "C",   31, 25.3, 12.6, 3.5, 1.2, 2.3, 56.1, 25.2, 80.5, 76),
        (27, "LeBron James",             1610612747, "F",   40, 24.9,  7.5, 8.3, 1.1, 0.6, 54.0, 40.8, 74.0, 70),
        (28, "Austin Reaves",            1610612747, "G",   26, 15.9,  4.2, 5.5, 1.0, 0.3, 47.2, 39.5, 87.0, 72),
        (29, "Rui Hachimura",            1610612747, "F",   26, 14.2,  4.6, 1.3, 0.7, 0.5, 51.5, 38.0, 81.0, 68),
        (30, "D'Angelo Russell",         1610612747, "G",   28, 16.8,  3.1, 6.3, 1.0, 0.2, 43.8, 37.5, 84.0, 65),
        (31, "Donovan Mitchell",         1610612739, "G",   27, 26.5,  5.1, 6.1, 1.4, 0.3, 46.8, 38.0, 87.5, 72),
        (32, "Darius Garland",           1610612739, "G",   24, 19.8,  2.9, 6.6, 1.0, 0.2, 45.2, 38.5, 84.0, 68),
        (33, "Evan Mobley",              1610612739, "C",   23, 15.7,  9.4, 2.6, 1.3, 1.8, 55.0, 30.0, 73.0, 74),
        (34, "Jarrett Allen",            1610612739, "C",   26, 13.2, 10.6, 2.0, 0.7, 1.3, 64.0,  0.0, 78.0, 70),
        (35, "Max Strus",                1610612739, "G-F", 28, 12.5,  4.2, 2.8, 0.9, 0.3, 43.0, 38.5, 83.0, 72),
        (36, "Karl-Anthony Towns",       1610612752, "C",   29, 24.0, 13.9, 3.0, 1.1, 0.6, 50.5, 41.2, 83.4, 74),
        (37, "Jalen Brunson",            1610612752, "G",   27, 28.7,  3.6, 6.7, 0.9, 0.2, 49.7, 40.4, 84.5, 77),
        (38, "OG Anunoby",               1610612752, "F",   27, 14.7,  4.8, 1.9, 1.4, 0.8, 47.2, 37.1, 83.0, 65),
        (39, "Mikal Bridges",            1610612752, "G-F", 28, 13.8,  4.3, 3.6, 1.0, 0.5, 45.0, 36.0, 81.0, 78),
        (40, "Josh Hart",                1610612752, "G-F", 29, 10.2,  9.1, 4.1, 1.1, 0.3, 46.5, 32.0, 71.0, 80),
        (41, "Tyrese Haliburton",        1610612754, "G",   25, 20.1,  3.9, 9.2, 1.3, 0.3, 46.0, 38.5, 86.0, 60),
        (42, "Pascal Siakam",            1610612754, "F",   30, 22.6,  6.9, 3.8, 1.0, 0.7, 52.0, 35.6, 77.5, 72),
        (43, "Myles Turner",             1610612754, "C",   28, 15.2,  7.0, 1.3, 0.7, 2.6, 52.5, 38.0, 78.0, 68),
        (44, "Andrew Nembhard",          1610612754, "G",   25, 12.0,  3.1, 5.0, 1.5, 0.3, 47.0, 38.0, 83.0, 72),
        (45, "Bennedict Mathurin",       1610612754, "G-F", 22, 14.5,  3.8, 1.6, 0.7, 0.4, 46.0, 36.5, 77.0, 70),
        (46, "Bam Adebayo",              1610612748, "C",   27, 19.3, 10.4, 3.9, 1.2, 0.9, 53.5,  5.0, 77.0, 76),
        (47, "Tyler Herro",              1610612748, "G",   24, 24.1,  5.3, 5.2, 0.9, 0.3, 44.7, 39.0, 87.0, 68),
        (48, "Nikola Jovic",             1610612748, "F",   22, 11.5,  5.8, 2.7, 0.8, 0.5, 48.0, 38.5, 80.0, 72),
        (49, "Terry Rozier",             1610612748, "G",   30, 18.5,  3.9, 5.0, 1.3, 0.3, 45.0, 37.0, 86.0, 58),
        (50, "Haywood Highsmith",        1610612748, "F",   28, 11.0,  4.5, 1.0, 0.8, 0.5, 46.5, 39.0, 81.0, 70),
        (51, "Anthony Edwards",          1610612750, "G",   22, 25.9,  5.4, 5.1, 1.3, 0.5, 46.1, 35.7, 83.0, 76),
        (52, "Rudy Gobert",              1610612750, "C",   32, 14.0, 12.9, 1.3, 0.9, 2.1, 63.5,  5.0, 65.0, 72),
        (53, "Jaden McDaniels",          1610612750, "F",   23, 14.5,  4.5, 1.9, 1.5, 0.8, 48.0, 37.0, 78.0, 70),
        (54, "Mike Conley",              1610612750, "G",   36, 10.8,  3.0, 5.4, 1.0, 0.2, 45.0, 40.0, 88.0, 60),
        (55, "Naz Reid",                 1610612750, "C",   25, 13.5,  5.8, 1.7, 0.6, 1.0, 49.5, 38.5, 81.0, 68),
        (56, "Victor Wembanyama",        1610612759, "C",   20, 21.4, 10.6, 3.9, 1.2, 3.6, 48.5, 32.5, 79.0, 71),
        (57, "Devin Vassell",            1610612759, "G",   24, 19.5,  4.0, 4.1, 1.2, 0.4, 46.0, 39.5, 82.0, 68),
        (58, "Keldon Johnson",           1610612759, "F",   24, 14.8,  5.5, 2.3, 0.9, 0.5, 48.0, 35.0, 73.0, 70),
        (59, "Chris Paul",               1610612759, "G",   39,  9.2,  3.8, 8.2, 1.3, 0.2, 44.5, 33.5, 86.0, 58),
        (60, "Harrison Barnes",          1610612759, "F",   32, 14.2,  5.1, 1.8, 0.8, 0.4, 48.5, 37.0, 83.0, 70),
        (61, "Stephen Curry",            1610612744, "G",   36, 26.4,  4.5, 5.1, 1.3, 0.4, 45.2, 40.8, 92.3, 74),
        (62, "Draymond Green",           1610612744, "F",   34,  9.0,  7.3, 7.0, 1.2, 0.7, 48.0, 30.0, 70.0, 72),
        (63, "Jonathan Kuminga",         1610612744, "F",   22, 16.1,  4.9, 2.6, 0.9, 0.6, 53.0, 30.0, 70.0, 68),
        (64, "Andrew Wiggins",           1610612744, "F",   29, 17.1,  4.8, 2.4, 0.9, 0.8, 47.5, 38.0, 74.0, 71),
        (65, "Brandin Podziemski",       1610612744, "G",   22, 10.8,  6.0, 3.5, 1.2, 0.3, 44.0, 38.0, 82.0, 72),
        (66, "Trae Young",               1610612737, "G",   25, 25.7,  2.9, 10.8,0.9, 0.1, 43.0, 34.5, 87.0, 78),
        (67, "Dejounte Murray",          1610612737, "G",   27, 22.5,  5.3, 6.1, 1.8, 0.4, 46.0, 36.0, 81.0, 72),
        (68, "Clint Capela",             1610612737, "C",   30, 11.5, 11.0, 1.5, 0.6, 1.6, 61.0,  0.0, 72.0, 68),
        (69, "De'Andre Hunter",          1610612737, "F",   26, 14.2,  3.8, 1.8, 1.0, 0.5, 48.5, 37.5, 79.0, 68),
        (70, "Saddiq Bey",               1610612737, "F",   25, 11.0,  4.2, 1.7, 0.8, 0.4, 44.5, 36.0, 80.0, 60),
        (71, "Zion Williamson",          1610612740, "F",   24, 22.9,  5.8, 5.0, 1.0, 0.6, 57.0, 25.0, 71.0, 55),
        (72, "Brandon Ingram",           1610612740, "F",   26, 24.3,  5.1, 5.7, 0.8, 0.6, 47.5, 36.5, 85.0, 68),
        (73, "CJ McCollum",              1610612740, "G",   33, 19.8,  3.5, 4.7, 1.1, 0.3, 46.0, 40.0, 87.0, 72),
        (74, "Herbert Jones",            1610612740, "F",   26, 10.2,  3.9, 2.5, 1.3, 0.8, 48.0, 33.0, 76.0, 70),
        (75, "Jonas Valanciunas",        1610612740, "C",   32, 12.8,  8.8, 2.1, 0.4, 0.5, 57.0, 29.0, 79.0, 68),
        (76, "Zach LaVine",              1610612741, "G",   29, 24.8,  5.2, 4.5, 0.9, 0.5, 46.5, 38.0, 84.0, 65),
        (77, "DeMar DeRozan",            1610612741, "F",   34, 22.5,  4.5, 4.8, 0.9, 0.4, 51.5, 26.0, 88.0, 60),
        (78, "Nikola Vucevic",           1610612741, "C",   33, 18.0, 10.5, 3.4, 0.8, 0.8, 50.0, 31.0, 80.0, 72),
        (79, "Patrick Williams",         1610612741, "F",   22, 12.5,  4.7, 1.8, 0.9, 0.6, 48.5, 37.0, 76.0, 68),
        (80, "Coby White",               1610612741, "G",   24, 18.5,  4.2, 4.5, 1.2, 0.3, 44.5, 39.0, 83.0, 72),
        (81, "Jalen Green",              1610612745, "G",   22, 22.2,  4.4, 4.0, 1.2, 0.4, 44.8, 35.7, 83.0, 75),
        (82, "Alperen Sengun",           1610612745, "C",   22, 21.1, 9.3,  4.5, 1.1, 0.9, 56.0, 30.0, 72.0, 72),
        (83, "Dillon Brooks",            1610612745, "F",   28, 13.5,  3.8, 2.3, 1.2, 0.4, 43.5, 34.0, 77.0, 70),
        (84, "Fred VanVleet",            1610612745, "G",   30, 16.8,  3.5, 7.2, 1.3, 0.2, 43.0, 37.5, 85.0, 68),
        (85, "Jabari Smith Jr.",         1610612745, "F",   22, 14.2,  6.5, 2.0, 1.0, 1.2, 45.5, 38.5, 76.0, 65),
        (86, "Paul George",              1610612746, "F",   33, 22.6,  5.2, 3.8, 1.5, 0.4, 47.0, 39.5, 87.0, 68),
        (87, "Kawhi Leonard",            1610612746, "F",   32, 23.7,  6.1, 3.6, 1.6, 0.5, 52.5, 40.5, 89.0, 45),
        (88, "James Harden",             1610612746, "G",   34, 16.6,  5.3, 8.5, 1.2, 0.5, 44.0, 38.0, 86.0, 72),
        (89, "Ivica Zubac",              1610612746, "C",   27, 14.8, 11.2, 2.0, 0.6, 1.4, 63.0,  0.0, 73.0, 70),
        (90, "Norman Powell",            1610612746, "G-F", 31, 23.5,  3.5, 2.5, 1.0, 0.4, 52.0, 41.5, 85.0, 72),
        (91, "Joel Embiid",              1610612755, "C",   30, 34.7, 11.0, 5.6, 1.0, 1.7, 52.5, 33.5, 87.8, 39),
        (92, "Tyrese Maxey",             1610612755, "G",   23, 25.9,  3.7, 6.2, 1.0, 0.5, 46.6, 38.0, 87.0, 75),
        (93, "Paul Reed",                1610612755, "F-C", 25, 10.2,  7.8, 1.7, 0.8, 1.1, 54.5, 28.0, 70.0, 65),
        (94, "Kelly Oubre Jr.",          1610612755, "F",   29, 15.4,  5.0, 1.8, 1.3, 0.5, 46.5, 36.0, 76.0, 60),
        (95, "Tobias Harris",            1610612755, "F",   32, 16.5,  6.6, 2.8, 0.9, 0.6, 49.5, 37.5, 85.0, 68),
        (96, "Kevin Durant",             1610612756, "F",   35, 27.1,  6.6, 4.0, 0.9, 1.2, 52.5, 41.3, 85.5, 65),
        (97, "Devin Booker",             1610612756, "G",   27, 27.4,  4.5, 6.9, 1.1, 0.3, 49.0, 36.1, 86.5, 68),
        (98, "Bradley Beal",             1610612756, "G",   30, 18.2,  4.5, 5.0, 1.1, 0.3, 47.0, 38.5, 83.0, 50),
        (99, "Jusuf Nurkic",             1610612756, "C",   30, 10.2, 10.2, 3.5, 0.7, 0.9, 51.5,  0.0, 67.0, 60),
        (100,"Grayson Allen",            1610612756, "G",   29, 12.8,  3.5, 2.0, 1.0, 0.4, 46.5, 42.0, 89.0, 70),
        (101,"Damian Lillard",           1610612757, "G",   35,  6.5,  2.0, 4.5, 0.7, 0.1, 40.0, 34.0, 82.0, 20),
        (102,"Anfernee Simons",          1610612757, "G",   25, 21.5,  4.1, 5.2, 1.0, 0.3, 44.5, 38.5, 85.0, 60),
        (103,"Jerami Grant",             1610612757, "F",   30, 20.5,  4.5, 2.8, 1.1, 0.5, 46.0, 37.0, 79.0, 65),
        (104,"Scoot Henderson",          1610612757, "G",   20, 14.5,  3.5, 6.5, 1.3, 0.3, 43.5, 33.0, 75.0, 68),
        (105,"Shaedon Sharpe",           1610612757, "G",   21, 17.5,  4.0, 2.5, 1.1, 0.5, 46.0, 37.5, 77.0, 65),
        (106,"De'Aaron Fox",             1610612758, "G",   26, 26.6,  4.9, 5.8, 1.6, 0.4, 50.5, 34.0, 77.5, 72),
        (107,"Domantas Sabonis",         1610612758, "C",   28, 19.4, 13.7, 8.3, 1.0, 0.5, 59.0, 25.0, 75.0, 74),
        (108,"Kevin Huerter",            1610612758, "G-F", 25, 13.2,  4.2, 3.5, 1.1, 0.3, 45.5, 39.5, 83.0, 68),
        (109,"Harrison Barnes",          1610612758, "F",   32, 12.8,  4.8, 1.5, 0.7, 0.5, 48.5, 37.5, 83.0, 60),
        (110,"Malik Monk",               1610612758, "G",   26, 14.2,  3.2, 4.5, 1.1, 0.2, 46.0, 40.5, 84.0, 68),
        (111,"Jaylen Wells",             1610612763, "G",   22, 12.5,  4.0, 2.0, 1.0, 0.5, 47.5, 38.0, 79.0, 68),
        (112,"Jaren Jackson Jr.",        1610612763, "C",   25, 22.2,  6.9, 2.8, 0.9, 2.9, 46.5, 34.8, 80.0, 65),
        (113,"Desmond Bane",             1610612763, "G-F", 26, 23.8,  4.5, 4.2, 1.2, 0.5, 47.0, 42.0, 87.0, 68),
        (114,"Ja Morant",                1610612763, "G",   24, 22.0,  5.5, 8.1, 1.0, 0.5, 47.2, 30.5, 74.0, 55),
        (115,"GG Jackson",               1610612763, "F",   20, 14.8,  5.5, 1.5, 0.7, 0.8, 47.0, 36.5, 77.0, 65),
        (116,"Kyle Kuzma",               1610612764, "F",   29, 18.5,  6.8, 3.5, 0.9, 0.5, 46.0, 35.5, 80.0, 65),
        (117,"Jordan Poole",             1610612764, "G",   24, 21.3,  3.2, 4.8, 1.0, 0.3, 44.5, 38.0, 83.0, 68),
        (118,"Daniel Gafford",           1610612764, "C",   26,  9.8,  5.2, 1.0, 0.5, 2.0, 68.0,  0.0, 65.0, 55),
        (119,"Marvin Bagley III",        1610612764, "F-C", 25, 12.5,  7.8, 1.2, 0.7, 0.8, 51.0, 25.0, 70.0, 60),
        (120,"Bilal Coulibaly",          1610612764, "G-F", 21, 10.0,  4.0, 2.5, 1.5, 0.6, 46.0, 34.0, 73.0, 65),
        (121,"Paolo Banchero",           1610612753, "F",   22, 22.6,  6.9, 5.4, 1.1, 0.8, 46.5, 32.5, 74.5, 68),
        (122,"Franz Wagner",             1610612753, "F",   23, 19.7,  4.8, 3.6, 0.9, 0.6, 47.5, 35.0, 78.0, 72),
        (123,"Jalen Suggs",              1610612753, "G",   23, 13.2,  3.6, 3.8, 1.4, 0.5, 45.5, 35.5, 78.0, 65),
        (124,"Wendell Carter Jr.",       1610612753, "C",   25, 12.5, 10.2, 2.5, 0.7, 1.3, 55.0, 28.0, 72.0, 60),
        (125,"Moritz Wagner",            1610612753, "C",   27, 13.8,  6.5, 2.0, 0.6, 0.8, 55.0, 34.5, 80.0, 68),
        (126,"Scottie Barnes",           1610612761, "F",   23, 19.9,  8.1, 6.1, 1.3, 0.9, 47.5, 33.5, 71.0, 68),
        (127,"RJ Barrett",               1610612761, "G-F", 24, 21.8,  5.5, 3.5, 0.9, 0.5, 46.5, 36.5, 79.0, 72),
        (128,"Immanuel Quickley",        1610612761, "G",   25, 18.5,  4.2, 6.8, 1.2, 0.4, 45.0, 37.5, 83.0, 68),
        (129,"Jakob Poeltl",             1610612761, "C",   28, 12.0, 10.5, 3.2, 0.6, 1.6, 63.0,  0.0, 72.0, 70),
        (130,"Ochai Agbaji",             1610612761, "G-F", 24, 11.5,  3.8, 1.8, 0.9, 0.5, 46.5, 37.0, 80.0, 62),
        (131,"Lauri Markkanen",          1610612762, "F",   27, 23.2,  8.2, 2.0, 0.9, 0.5, 49.5, 38.0, 86.0, 60),
        (132,"Jordan Clarkson",          1610612762, "G",   32, 17.5,  3.5, 4.2, 0.7, 0.3, 45.0, 37.0, 83.5, 68),
        (133,"John Collins",             1610612762, "F",   26, 14.8,  7.2, 1.8, 0.8, 0.5, 53.0, 34.0, 77.0, 65),
        (134,"Talen Horton-Tucker",      1610612762, "G-F", 23, 12.5,  4.0, 3.5, 1.0, 0.4, 46.5, 34.5, 77.0, 60),
        (135,"Keyonte George",           1610612762, "G",   21, 15.8,  3.5, 5.2, 1.0, 0.2, 41.5, 36.0, 81.0, 65),
        (136,"Cade Cunningham",          1610612765, "G",   23, 22.7,  4.4, 9.0, 1.2, 0.5, 43.0, 33.5, 83.0, 62),
        (137,"Jalen Duren",              1610612765, "C",   20, 14.2, 12.3, 2.8, 0.7, 1.4, 61.0,  0.0, 67.0, 65),
        (138,"Ausar Thompson",           1610612765, "F",   21, 12.5,  5.8, 2.5, 1.5, 0.8, 51.0, 28.0, 68.0, 58),
        (139,"Bojan Bogdanovic",         1610612765, "F",   35, 14.5,  3.2, 1.5, 0.5, 0.3, 46.5, 40.0, 89.0, 62),
        (140,"Marcus Sasser",            1610612765, "G",   23, 11.5,  3.0, 3.5, 1.3, 0.3, 44.0, 37.5, 79.0, 58),
        (141,"LaMelo Ball",              1610612766, "G",   23, 26.2,  5.5, 8.0, 1.6, 0.3, 43.0, 36.0, 81.0, 55),
        (142,"Miles Bridges",            1610612766, "F",   26, 21.0,  7.2, 3.5, 1.0, 0.6, 47.5, 35.5, 78.0, 68),
        (143,"Brandon Miller",           1610612766, "F",   22, 17.3,  4.8, 2.5, 1.1, 0.6, 44.5, 37.5, 77.0, 65),
        (144,"Mark Williams",            1610612766, "C",   23, 12.5, 10.8, 1.5, 0.5, 1.2, 65.0,  0.0, 68.0, 55),
        (145,"Grant Williams",           1610612766, "F",   25, 10.2,  4.5, 2.5, 0.8, 0.6, 46.0, 38.0, 80.0, 60),
        (146,"Jimmy Butler",             1610612748, "F",   34, 20.8,  5.3, 5.0, 1.3, 0.3, 50.0, 30.0, 84.0, 42),
        (147,"Deni Avdija",              1610612764, "F",   23, 15.0,  7.2, 4.5, 1.3, 0.5, 49.5, 34.5, 76.0, 72),
        (148,"Josh Giddey",              1610612741, "G-F", 21, 15.2,  7.5, 6.8, 1.0, 0.4, 46.5, 32.0, 72.0, 68),
        (149,"Cam Thomas",               1610612751, "G",   22, 22.5,  3.0, 4.2, 0.9, 0.3, 45.0, 38.0, 84.0, 65),
        (150,"Ben Simmons",              1610612751, "G-F", 27,  8.0,  6.5, 5.5, 1.5, 0.7, 58.0,  0.0, 58.0, 30),
    ]
    conn.executemany("INSERT INTO players VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", players_data)

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
            home, away = shuffled[i], shuffled[i + 1]
            hs = random.randint(95, 130)
            as_ = random.randint(95, 130)
            while hs == as_:
                as_ = random.randint(95, 130)
            games_to_insert.append((home, away, hs, as_, date))
    conn.executemany(
        "INSERT INTO games (home_team_id, away_team_id, home_score, away_score, game_date) VALUES (?,?,?,?,?)",
        games_to_insert,
    )
    conn.commit()


# ──────────────────────────────────────────────────────────────────────────────
# SQL query runner
# ──────────────────────────────────────────────────────────────────────────────

def run_sql(sql, conn):
    sql_s = sql.strip().rstrip(";").strip()
    if not sql_s:
        return "Please enter a SQL query."
    first = sql_s.split()[0].upper()
    if first not in ("SELECT", "WITH"):
        return "Only SELECT queries are allowed."
    try:
        return pd.read_sql_query(sql_s, conn)
    except Exception as e:
        return f"SQL Error: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# SQL answer validation (adapted from Task 4)
# ──────────────────────────────────────────────────────────────────────────────

def validate_answer(user_answer, question, conn, last_df=None):
    ua = str(user_answer).strip()
    ca = str(question["answer"]).strip()
    vt = question["validator_type"]

    if not ua:
        return False

    if vt == "exact_number":
        try:
            return int(float(ua)) == int(float(ca))
        except (ValueError, TypeError):
            return False

    elif vt == "float_number":
        try:
            return abs(float(ua) - float(ca)) < 0.3
        except (ValueError, TypeError):
            return False

    elif vt == "player_name":
        return _fuzzy_name_match(ua, ca, conn)

    elif vt == "team_name":
        return _fuzzy_team_match(ua, ca, conn)

    elif vt == "name_from_set":
        for name in [n.strip() for n in ca.split("|")]:
            if _fuzzy_name_match(ua, name, conn):
                return True
        return False

    elif vt == "team_from_set":
        for team in [t.strip() for t in ca.split("|")]:
            if _fuzzy_team_match(ua, team, conn):
                return True
        return False

    elif vt in ("position", "conference"):
        return ua.upper() == ca.upper()

    elif vt == "dataframe_match":
        if last_df is None or not isinstance(last_df, pd.DataFrame):
            return False
        try:
            expected = pd.read_json(ca)
            return _dataframes_match(last_df, expected)
        except Exception:
            return False

    return ua.lower() == ca.lower()


def _fuzzy_name_match(user, correct, conn=None):
    u, c = user.lower().strip(), correct.lower().strip()
    if u == c:
        return True
    parts = c.split()
    if len(parts) >= 2 and u == parts[-1]:
        return True
    if c.startswith(u) or c.endswith(u):
        return True
    if len(u) >= 4 and u in c:
        return True
    return False


def _fuzzy_team_match(user, correct, conn=None):
    u, c = user.lower().strip(), correct.lower().strip()
    if u == c:
        return True
    parts = c.split()
    if len(parts) >= 2 and u == parts[-1]:
        return True
    if conn:
        try:
            tdf = pd.read_sql("SELECT full_name, city, abbreviation FROM teams", conn)
            for _, row in tdf.iterrows():
                if row["full_name"].lower() == c:
                    if u in (row["city"].lower(), row["abbreviation"].lower()):
                        return True
                    if u == row["full_name"].lower().split()[-1]:
                        return True
        except Exception:
            pass
    if len(u) >= 4 and u in c:
        return True
    return False


def _dataframes_match(df_user, df_expected):
    try:
        if df_user is None or df_expected is None:
            return False
        u = df_user.copy()
        e = df_expected.copy()
        u.columns = [c.lower().strip() for c in u.columns]
        e.columns = [c.lower().strip() for c in e.columns]
        if set(u.columns) != set(e.columns):
            return False
        e = e[u.columns]
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


def build_hint(question, user_sql, conn):
    """Build a contextual hint: generic hint + feedback about the user's last SQL attempt."""
    parts = [f"**Hint:** {question['hint']}"]
    if user_sql and user_sql.strip():
        result = run_sql(user_sql, conn)
        if isinstance(result, pd.DataFrame):
            parts.append(
                f"Your query ran and returned **{len(result)} row(s)**. "
                "Check that you're selecting the right column and the correct value."
            )
        elif isinstance(result, str) and result.startswith("SQL Error"):
            parts.append(f"**Your SQL has an error:** `{result}`")
    return "\n\n".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
# Question generators (adapted from Task 4)
# ──────────────────────────────────────────────────────────────────────────────

def _random_team(conn):
    return pd.read_sql("SELECT id, full_name, abbreviation, city FROM teams", conn).sample(1).iloc[0]


def _random_player(conn, min_ppg=5):
    df = pd.read_sql(
        f"SELECT id, name, team_id, position, ppg, rpg, apg FROM players WHERE ppg >= {min_ppg}", conn
    )
    if len(df) == 0:
        df = pd.read_sql("SELECT id, name, team_id, position, ppg, rpg, apg FROM players", conn)
    return df.sample(1).iloc[0]


# Level 1
def q1_player_count(conn):
    team = _random_team(conn)
    count = pd.read_sql(f"SELECT COUNT(*) as c FROM players WHERE team_id = {team['id']}", conn).iloc[0]["c"]
    return {"text": f"How many players are on the **{team['full_name']}** roster?",
            "answer": str(int(count)),
            "hint": f"Try: SELECT * FROM players WHERE team_id = {team['id']}",
            "validator_type": "exact_number"}

def q1_player_position(conn):
    p = _random_player(conn, 10)
    return {"text": f"What position does **{p['name']}** play?",
            "answer": str(p["position"]),
            "hint": f"Try: SELECT * FROM players WHERE name = '{p['name']}'",
            "validator_type": "position"}

def q1_player_team(conn):
    p = _random_player(conn, 12)
    team = pd.read_sql(f"SELECT full_name FROM teams WHERE id = {p['team_id']}", conn).iloc[0]["full_name"]
    return {"text": f"What team does **{p['name']}** play for?",
            "answer": team,
            "hint": "Try: SELECT * FROM players — look at team_id, then check the teams table.",
            "validator_type": "team_name"}

def q1_team_city(conn):
    team = _random_team(conn)
    nick = team["full_name"].split()[-1]
    return {"text": f"What city do the **{nick}** play in?",
            "answer": team["city"],
            "hint": "Try: SELECT * FROM teams",
            "validator_type": "team_name"}

def q1_player_ppg(conn):
    p = _random_player(conn, 15)
    return {"text": f"What is **{p['name']}**'s points per game (PPG) average?",
            "answer": str(p["ppg"]),
            "hint": f"Try: SELECT * FROM players WHERE name = '{p['name']}'",
            "validator_type": "float_number"}

def q1_team_conference(conn):
    team = _random_team(conn)
    conf = pd.read_sql(f"SELECT conference FROM teams WHERE id = {team['id']}", conn).iloc[0]["conference"]
    return {"text": f"Which conference are the **{team['full_name']}** in?",
            "answer": conf,
            "hint": "Try: SELECT * FROM teams",
            "validator_type": "conference"}


# Level 2
def q2_ppg_count(conn):
    team = _random_team(conn)
    for thr in random.sample([8, 10, 12, 15, 18], 5):
        cnt = pd.read_sql(f"SELECT COUNT(*) as c FROM players WHERE team_id={team['id']} AND ppg>{thr}", conn).iloc[0]["c"]
        if 1 <= cnt <= 6:
            return {"text": f"How many players on the **{team['full_name']}** average more than **{thr} PPG**?",
                    "answer": str(int(cnt)),
                    "hint": f"Try: SELECT * FROM players WHERE team_id = {team['id']} AND ppg > {thr}",
                    "validator_type": "exact_number"}
    cnt = pd.read_sql(f"SELECT COUNT(*) as c FROM players WHERE team_id={team['id']} AND ppg>10", conn).iloc[0]["c"]
    return {"text": f"How many players on the **{team['full_name']}** average more than **10 PPG**?",
            "answer": str(int(cnt)),
            "hint": f"Try: SELECT * FROM players WHERE team_id = {team['id']} AND ppg > 10",
            "validator_type": "exact_number"}

def q2_guards_assists(conn):
    for thr in random.sample([3, 4, 5, 6, 7], 5):
        cnt = pd.read_sql(f"SELECT COUNT(*) as c FROM players WHERE position LIKE '%G%' AND apg > {thr}", conn).iloc[0]["c"]
        if 3 <= cnt <= 30:
            return {"text": f"How many guards (position contains 'G') average more than **{thr} assists** per game?",
                    "answer": str(int(cnt)),
                    "hint": f"Try: SELECT * FROM players WHERE position LIKE '%G%' AND apg > {thr}",
                    "validator_type": "exact_number"}
    return q2_ppg_count(conn)

def q2_team_rebounds(conn):
    team = _random_team(conn)
    thr = random.choice([5, 6, 7, 8])
    df = pd.read_sql(f"SELECT name FROM players WHERE team_id={team['id']} AND rpg>{thr}", conn)
    if len(df) == 0:
        df = pd.read_sql(f"SELECT name FROM players WHERE team_id={team['id']} AND rpg>4", conn)
        thr = 4
    names = "|".join(df["name"].tolist())
    return {"text": f"Name a player on the **{team['full_name']}** who averages more than **{thr} RPG**.",
            "answer": names,
            "hint": f"Try: SELECT * FROM players WHERE team_id = {team['id']} AND rpg > {thr}",
            "validator_type": "name_from_set"}

def q2_conference_wins(conn):
    conf = random.choice(["East", "West"])
    thr = random.choice([35, 40, 45, 50])
    cnt = pd.read_sql(f"SELECT COUNT(*) as c FROM teams WHERE conference='{conf}' AND wins>{thr}", conn).iloc[0]["c"]
    return {"text": f"How many **{conf}ern Conference** teams have more than **{thr} wins**?",
            "answer": str(int(cnt)),
            "hint": f"Try: SELECT * FROM teams WHERE conference = '{conf}' AND wins > {thr}",
            "validator_type": "exact_number"}

def q2_ppg_and_apg(conn):
    for ppg_t, apg_t in random.sample([(15, 4), (18, 3), (20, 5), (12, 6), (22, 4)], 5):
        df = pd.read_sql(f"SELECT name FROM players WHERE ppg>{ppg_t} AND apg>{apg_t}", conn)
        if 1 <= len(df) <= 15:
            names = "|".join(df["name"].tolist())
            return {"text": f"Name a player who averages more than **{ppg_t} PPG** and more than **{apg_t} APG**.",
                    "answer": names,
                    "hint": f"Try: SELECT * FROM players WHERE ppg > {ppg_t} AND apg > {apg_t}",
                    "validator_type": "name_from_set"}
    return q2_ppg_count(conn)

def q2_age_filter(conn):
    age = random.choice([21, 22, 23, 35, 36])
    op = ">=" if age >= 35 else "<="
    label = "at least" if age >= 35 else "at most"
    cnt = pd.read_sql(f"SELECT COUNT(*) as c FROM players WHERE age {op} {age}", conn).iloc[0]["c"]
    return {"text": f"How many players in the league are **{label} {age} years old**?",
            "answer": str(int(cnt)),
            "hint": f"Try: SELECT * FROM players WHERE age {op} {age}",
            "validator_type": "exact_number"}


# Level 3
def q3_top_scorer(conn):
    top = pd.read_sql("SELECT name FROM players ORDER BY ppg DESC LIMIT 1", conn).iloc[0]["name"]
    return {"text": "Who is the **league's top scorer** (highest PPG)?",
            "answer": top,
            "hint": "Try: SELECT name, ppg FROM players ORDER BY ppg DESC LIMIT 1",
            "validator_type": "player_name"}

def q3_most_assists(conn):
    top = pd.read_sql("SELECT name FROM players ORDER BY apg DESC LIMIT 1", conn).iloc[0]["name"]
    return {"text": "Who has the **most assists per game** in the league?",
            "answer": top,
            "hint": "Try: SELECT name, apg FROM players ORDER BY apg DESC LIMIT 1",
            "validator_type": "player_name"}

def q3_most_wins(conn):
    top = pd.read_sql("SELECT full_name FROM teams ORDER BY wins DESC LIMIT 1", conn).iloc[0]["full_name"]
    return {"text": "Which team has the **most wins** this season?",
            "answer": top,
            "hint": "Try: SELECT full_name, wins FROM teams ORDER BY wins DESC LIMIT 1",
            "validator_type": "team_name"}

def q3_nth_scorer(conn):
    n = random.choice([2, 3, 4, 5])
    ordinal = {2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}[n]
    top = pd.read_sql(f"SELECT name FROM players ORDER BY ppg DESC LIMIT 1 OFFSET {n-1}", conn).iloc[0]["name"]
    return {"text": f"Who is the **{ordinal} highest scorer** in the league (by PPG)?",
            "answer": top,
            "hint": f"Try: SELECT name, ppg FROM players ORDER BY ppg DESC LIMIT 1 OFFSET {n-1}",
            "validator_type": "player_name"}

def q3_most_rebounds(conn):
    top = pd.read_sql("SELECT name FROM players ORDER BY rpg DESC LIMIT 1", conn).iloc[0]["name"]
    return {"text": "Who averages the **most rebounds per game** in the league?",
            "answer": top,
            "hint": "Try: SELECT name, rpg FROM players ORDER BY rpg DESC LIMIT 1",
            "validator_type": "player_name"}

def q3_fewest_losses(conn):
    top = pd.read_sql("SELECT full_name FROM teams ORDER BY losses ASC LIMIT 1", conn).iloc[0]["full_name"]
    return {"text": "Which team has the **fewest losses** this season?",
            "answer": top,
            "hint": "Try: SELECT full_name, losses FROM teams ORDER BY losses ASC LIMIT 1",
            "validator_type": "team_name"}

def q3_top5_scorers_query(conn):
    expected = pd.read_sql(
        "SELECT name, ppg FROM players ORDER BY ppg DESC LIMIT 5", conn
    )
    return {"text": "Write a query that returns the **top 5 scorers** (name and ppg) ordered by PPG descending.",
            "answer": expected.to_json(),
            "hint": "Try: SELECT name, ppg FROM players ORDER BY ppg DESC LIMIT 5",
            "validator_type": "dataframe_match"}


# Level 4
def q4_team_avg_ppg(conn):
    df = pd.read_sql("""SELECT t.full_name, ROUND(AVG(p.ppg),1) as avg_ppg
        FROM players p JOIN teams t ON p.team_id=t.id
        GROUP BY t.id ORDER BY avg_ppg DESC LIMIT 1""", conn)
    return {"text": "Which team has the **highest average PPG** across its roster?",
            "answer": df.iloc[0]["full_name"],
            "hint": "Try: SELECT t.full_name, AVG(p.ppg) FROM players p JOIN teams t ON p.team_id = t.id GROUP BY t.id ORDER BY AVG(p.ppg) DESC",
            "validator_type": "team_name"}

def q4_position_count(conn):
    positions = pd.read_sql("SELECT DISTINCT position FROM players WHERE position IN ('G','F','C')", conn)
    if len(positions) == 0:
        positions = pd.read_sql("SELECT DISTINCT position FROM players LIMIT 3", conn)
    pos = positions.sample(1).iloc[0]["position"]
    cnt = pd.read_sql(f"SELECT COUNT(*) as c FROM players WHERE position='{pos}'", conn).iloc[0]["c"]
    pos_name = {"G": "Guards", "F": "Forwards", "C": "Centers"}.get(pos, pos)
    return {"text": f"How many **{pos_name} (position = '{pos}')** are in the league?",
            "answer": str(int(cnt)),
            "hint": f"Try: SELECT COUNT(*) FROM players WHERE position = '{pos}'",
            "validator_type": "exact_number"}

def q4_conference_wins(conn):
    df = pd.read_sql("SELECT conference, ROUND(AVG(wins),1) as avg_wins FROM teams GROUP BY conference", conn)
    winner = df.sort_values("avg_wins", ascending=False).iloc[0]["conference"]
    return {"text": "Which conference has a **higher average wins** per team: **East** or **West**?",
            "answer": winner,
            "hint": "Try: SELECT conference, AVG(wins) FROM teams GROUP BY conference",
            "validator_type": "conference"}

def q4_position_rpg(conn):
    df = pd.read_sql("""SELECT position, ROUND(AVG(rpg),1) as avg_rpg
        FROM players WHERE position IN ('G','F','C')
        GROUP BY position ORDER BY avg_rpg DESC LIMIT 1""", conn)
    if len(df) == 0:
        df = pd.read_sql("SELECT position, ROUND(AVG(rpg),1) as avg_rpg FROM players GROUP BY position ORDER BY avg_rpg DESC LIMIT 1", conn)
    return {"text": "Which position (G, F, or C) has the **highest average RPG**?",
            "answer": df.iloc[0]["position"],
            "hint": "Try: SELECT position, AVG(rpg) FROM players GROUP BY position ORDER BY AVG(rpg) DESC",
            "validator_type": "position"}

def q4_teams_with_many_players(conn):
    thr = random.choice([4, 5, 6])
    cnt = pd.read_sql(f"""SELECT COUNT(*) as c FROM (
        SELECT team_id FROM players GROUP BY team_id HAVING COUNT(*) >= {thr})""", conn).iloc[0]["c"]
    return {"text": f"How many teams have **at least {thr} players** on their roster?",
            "answer": str(int(cnt)),
            "hint": f"Try: SELECT team_id, COUNT(*) as cnt FROM players GROUP BY team_id HAVING COUNT(*) >= {thr}",
            "validator_type": "exact_number"}

def q4_avg_age_by_team(conn):
    df = pd.read_sql("""SELECT t.full_name, ROUND(AVG(p.age),1) as avg_age
        FROM players p JOIN teams t ON p.team_id=t.id
        GROUP BY t.id ORDER BY avg_age DESC LIMIT 1""", conn)
    return {"text": "Which team has the **oldest roster** (highest average age)?",
            "answer": df.iloc[0]["full_name"],
            "hint": "Try: SELECT t.full_name, AVG(p.age) FROM players p JOIN teams t ON p.team_id = t.id GROUP BY t.id ORDER BY AVG(p.age) DESC",
            "validator_type": "team_name"}

def q4_avg_by_position_query(conn):
    expected = pd.read_sql("""SELECT position, ROUND(AVG(ppg),1) as avg_ppg
        FROM players WHERE position IN ('G','F','C')
        GROUP BY position ORDER BY avg_ppg DESC""", conn)
    return {"text": "Write a query that returns the **average PPG by position** (G, F, C only), ordered by avg_ppg descending. Include columns: position, avg_ppg.",
            "answer": expected.to_json(),
            "hint": "Try: SELECT position, ROUND(AVG(ppg),1) as avg_ppg FROM players WHERE position IN ('G','F','C') GROUP BY position ORDER BY avg_ppg DESC",
            "validator_type": "dataframe_match"}


# Level 5
def q5_home_wins(conn):
    team = _random_team(conn)
    cnt = pd.read_sql(f"""SELECT COUNT(*) as c FROM games g
        JOIN teams t ON g.home_team_id=t.id
        WHERE t.full_name='{team['full_name']}' AND g.home_score>g.away_score""", conn).iloc[0]["c"]
    return {"text": f"How many **home games** did the **{team['full_name']}** win?",
            "answer": str(int(cnt)),
            "hint": f"Try: SELECT COUNT(*) FROM games g JOIN teams t ON g.home_team_id = t.id WHERE t.full_name = '{team['full_name']}' AND g.home_score > g.away_score",
            "validator_type": "exact_number"}

def q5_top_scorer_on_team(conn):
    team = _random_team(conn)
    top = pd.read_sql(f"""SELECT p.name FROM players p
        JOIN teams t ON p.team_id=t.id
        WHERE t.full_name='{team['full_name']}' ORDER BY p.ppg DESC LIMIT 1""", conn).iloc[0]["name"]
    return {"text": f"Who is the **top scorer** on the **{team['full_name']}**?",
            "answer": top,
            "hint": f"Try: SELECT p.name, p.ppg FROM players p JOIN teams t ON p.team_id = t.id WHERE t.full_name = '{team['full_name']}' ORDER BY p.ppg DESC LIMIT 1",
            "validator_type": "player_name"}

def q5_away_losses(conn):
    team = _random_team(conn)
    cnt = pd.read_sql(f"""SELECT COUNT(*) as c FROM games g
        JOIN teams t ON g.away_team_id=t.id
        WHERE t.full_name='{team['full_name']}' AND g.away_score<g.home_score""", conn).iloc[0]["c"]
    return {"text": f"How many games did the **{team['full_name']}** lose **on the road** (as away team)?",
            "answer": str(int(cnt)),
            "hint": f"Try: SELECT COUNT(*) FROM games g JOIN teams t ON g.away_team_id = t.id WHERE t.full_name = '{team['full_name']}' AND g.away_score < g.home_score",
            "validator_type": "exact_number"}

def q5_games_between(conn):
    t1 = _random_team(conn)
    t2 = _random_team(conn)
    while t2["id"] == t1["id"]:
        t2 = _random_team(conn)
    cnt = pd.read_sql(f"""SELECT COUNT(*) as c FROM games
        WHERE (home_team_id={t1['id']} AND away_team_id={t2['id']})
           OR (home_team_id={t2['id']} AND away_team_id={t1['id']})""", conn).iloc[0]["c"]
    return {"text": f"How many games were played between the **{t1['full_name']}** and the **{t2['full_name']}**?",
            "answer": str(int(cnt)),
            "hint": "Try: SELECT * FROM games WHERE (home_team_id = X AND away_team_id = Y) OR (home_team_id = Y AND away_team_id = X) — check the teams table for IDs.",
            "validator_type": "exact_number"}

def q5_team_total_games(conn):
    team = _random_team(conn)
    cnt = pd.read_sql(f"SELECT COUNT(*) as c FROM games WHERE home_team_id={team['id']} OR away_team_id={team['id']}", conn).iloc[0]["c"]
    return {"text": f"How many **total games** (home + away) did the **{team['full_name']}** play?",
            "answer": str(int(cnt)),
            "hint": f"Try: SELECT COUNT(*) FROM games WHERE home_team_id = {team['id']} OR away_team_id = {team['id']}",
            "validator_type": "exact_number"}

def q5_biggest_home_win(conn):
    df = pd.read_sql("""SELECT t.full_name, (g.home_score-g.away_score) as margin
        FROM games g JOIN teams t ON g.home_team_id=t.id
        WHERE g.home_score>g.away_score ORDER BY margin DESC LIMIT 1""", conn)
    return {"text": "Which team had the **biggest home win** (largest margin of victory at home)?",
            "answer": df.iloc[0]["full_name"],
            "hint": "Try: SELECT t.full_name, (g.home_score - g.away_score) as margin FROM games g JOIN teams t ON g.home_team_id = t.id WHERE g.home_score > g.away_score ORDER BY margin DESC LIMIT 1",
            "validator_type": "team_name"}

def q5_team_top_scorer_query(conn):
    expected = pd.read_sql("""SELECT t.full_name as team, p.name, p.ppg
        FROM players p JOIN teams t ON p.team_id=t.id
        ORDER BY p.ppg DESC LIMIT 10""", conn)
    return {"text": "Write a query that returns the **top 10 scorers** with their team name. Include columns: team, name, ppg. Order by ppg descending.",
            "answer": expected.to_json(),
            "hint": "Try: SELECT t.full_name as team, p.name, p.ppg FROM players p JOIN teams t ON p.team_id = t.id ORDER BY p.ppg DESC LIMIT 10",
            "validator_type": "dataframe_match"}


QUESTION_POOLS = {
    1: [q1_player_count, q1_player_position, q1_player_team, q1_team_city, q1_player_ppg, q1_team_conference],
    2: [q2_ppg_count, q2_guards_assists, q2_team_rebounds, q2_conference_wins, q2_ppg_and_apg, q2_age_filter],
    3: [q3_top_scorer, q3_most_assists, q3_most_wins, q3_nth_scorer, q3_most_rebounds, q3_fewest_losses, q3_top5_scorers_query],
    4: [q4_team_avg_ppg, q4_position_count, q4_conference_wins, q4_position_rpg, q4_teams_with_many_players, q4_avg_age_by_team, q4_avg_by_position_query],
    5: [q5_home_wins, q5_top_scorer_on_team, q5_away_losses, q5_games_between, q5_team_total_games, q5_biggest_home_win, q5_team_top_scorer_query],
}


def generate_question(level, conn):
    pool = QUESTION_POOLS[level]
    for fn in random.sample(pool, len(pool)):
        try:
            return fn(conn)
        except Exception:
            continue
    return {"text": "Error generating question.", "answer": "", "hint": "", "validator_type": "exact_number"}


# ──────────────────────────────────────────────────────────────────────────────
# Minesweeper board logic
# ──────────────────────────────────────────────────────────────────────────────

def make_empty_board(rows, cols):
    return [[{"is_mine": False, "revealed": False, "flagged": False, "defused": False, "adjacent": 0}
             for _ in range(cols)] for _ in range(rows)]


def place_mines(board, rows, cols, mine_count, safe_r, safe_c):
    safe = {(safe_r + dr, safe_c + dc)
            for dr in range(-1, 2) for dc in range(-1, 2)
            if 0 <= safe_r + dr < rows and 0 <= safe_c + dc < cols}
    candidates = [(r, c) for r in range(rows) for c in range(cols) if (r, c) not in safe]
    for r, c in random.sample(candidates, min(mine_count, len(candidates))):
        board[r][c]["is_mine"] = True
    for r in range(rows):
        for c in range(cols):
            board[r][c]["adjacent"] = sum(
                1 for dr in range(-1, 2) for dc in range(-1, 2)
                if (dr, dc) != (0, 0)
                and 0 <= r + dr < rows and 0 <= c + dc < cols
                and board[r + dr][c + dc]["is_mine"]
            )


def flood_reveal(board, rows, cols, start_r, start_c):
    queue = deque([(start_r, start_c)])
    visited = {(start_r, start_c)}
    while queue:
        r, c = queue.popleft()
        cell = board[r][c]
        if cell["is_mine"] or cell["defused"]:
            continue
        cell["revealed"] = True
        cell["flagged"] = False
        if cell["adjacent"] == 0:
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    nr, nc = r + dr, c + dc
                    if (0 <= nr < rows and 0 <= nc < cols
                            and (nr, nc) not in visited
                            and not board[nr][nc]["revealed"]
                            and not board[nr][nc]["is_mine"]):
                        visited.add((nr, nc))
                        queue.append((nr, nc))


def check_win(board, rows, cols):
    return all(
        board[r][c]["revealed"] or board[r][c]["is_mine"]
        for r in range(rows) for c in range(cols)
    )


def count_flags(board, rows, cols):
    return sum(board[r][c]["flagged"] for r in range(rows) for c in range(cols))


# ──────────────────────────────────────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────────────────────────────────────

def init_session_state():
    defaults = {
        "ms_started": False,
        "ms_board": [],
        "ms_rows": 9,
        "ms_cols": 9,
        "ms_mines": 10,
        "ms_difficulty": "Easy",
        "ms_first_click": True,
        "ms_start_time": None,
        "ms_game_over": False,
        "ms_won": False,
        "ms_mine_hit_count": 0,
        "ms_sql_rescue": False,
        "ms_sql_question": None,
        "ms_sql_bomb_pos": None,
        "ms_sql_hint_shown": False,
        "ms_sql_wrong_attempts": 0,
        "ms_last_query_result": None,
        "ms_last_query_error": None,
        "ms_hints_used_total": 0,
        "ms_nickname": "",
        "ms_saved": False,
        "ms_sql_input": "",
        "ms_answer_input": "",
        "ms_feedback": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def start_game(difficulty, nickname):
    cfg = DIFFICULTIES[difficulty]
    rows, cols, mines = cfg["rows"], cfg["cols"], cfg["mines"]
    st.session_state.ms_started = True
    st.session_state.ms_board = make_empty_board(rows, cols)
    st.session_state.ms_rows = rows
    st.session_state.ms_cols = cols
    st.session_state.ms_mines = mines
    st.session_state.ms_difficulty = difficulty
    st.session_state.ms_first_click = True
    st.session_state.ms_start_time = None
    st.session_state.ms_game_over = False
    st.session_state.ms_won = False
    st.session_state.ms_mine_hit_count = 0
    st.session_state.ms_sql_rescue = False
    st.session_state.ms_sql_question = None
    st.session_state.ms_sql_bomb_pos = None
    st.session_state.ms_sql_hint_shown = False
    st.session_state.ms_sql_wrong_attempts = 0
    st.session_state.ms_last_query_result = None
    st.session_state.ms_last_query_error = None
    st.session_state.ms_hints_used_total = 0
    st.session_state.ms_nickname = nickname
    st.session_state.ms_saved = False
    st.session_state.ms_sql_input = ""
    st.session_state.ms_answer_input = ""
    st.session_state.ms_feedback = None


def handle_cell_click(r, c, conn):
    ss = st.session_state
    board = ss.ms_board
    rows, cols = ss.ms_rows, ss.ms_cols
    cell = board[r][c]

    if cell["revealed"] or cell["defused"] or cell["flagged"]:
        return

    # First click — generate board
    if ss.ms_first_click:
        place_mines(board, rows, cols, ss.ms_mines, r, c)
        ss.ms_start_time = time.time()
        ss.ms_first_click = False

    if cell["is_mine"]:
        # Trigger SQL rescue
        ss.ms_mine_hit_count += 1
        level = min(ss.ms_mine_hit_count, 5)
        ss.ms_sql_rescue = True
        ss.ms_sql_question = generate_question(level, conn)
        ss.ms_sql_bomb_pos = (r, c)
        ss.ms_sql_hint_shown = False
        ss.ms_sql_wrong_attempts = 0
        ss.ms_last_query_result = None
        ss.ms_last_query_error = None
        ss.ms_sql_input = ""
        ss.ms_answer_input = ""
        ss.ms_feedback = None
    else:
        flood_reveal(board, rows, cols, r, c)
        if check_win(board, rows, cols):
            ss.ms_won = True
            ss.ms_game_over = True


def handle_flag_click(r, c):
    cell = st.session_state.ms_board[r][c]
    if not cell["revealed"] and not cell["defused"]:
        cell["flagged"] = not cell["flagged"]


def defuse_mine(r, c):
    ss = st.session_state
    board = ss.ms_board
    rows, cols = ss.ms_rows, ss.ms_cols
    board[r][c]["defused"] = True
    ss.ms_sql_rescue = False
    ss.ms_sql_question = None
    ss.ms_sql_bomb_pos = None
    ss.ms_feedback = None
    if check_win(board, rows, cols):
        ss.ms_won = True
        ss.ms_game_over = True


# ──────────────────────────────────────────────────────────────────────────────
# Scoring & leaderboard
# ──────────────────────────────────────────────────────────────────────────────

def calculate_score(difficulty, elapsed_seconds, mines_hit, max_sql_level):
    base = SCORE_BASE[difficulty]
    time_penalty = int(elapsed_seconds * 1.5)
    rescue_penalty = mines_hit * 50
    sql_bonus = max_sql_level * 20
    return max(0, base - time_penalty - rescue_penalty + sql_bonus)


def save_to_leaderboard(conn, nickname, difficulty, elapsed, mines_hit, max_sql_level, hints_used, score):
    conn.execute(
        """INSERT INTO ms_leaderboard
           (nickname, difficulty, completion_time_seconds, mines_hit, max_sql_level, hints_used, score)
           VALUES (?,?,?,?,?,?,?)""",
        (nickname, difficulty, elapsed, mines_hit, max_sql_level, hints_used, score),
    )
    conn.commit()


def get_leaderboard(conn, difficulty, limit=20):
    try:
        return pd.read_sql(
            """SELECT nickname, score, completion_time_seconds, mines_hit, max_sql_level,
                      hints_used, played_at
               FROM ms_leaderboard WHERE difficulty = ?
               ORDER BY score DESC, completion_time_seconds ASC LIMIT ?""",
            conn, params=(difficulty, limit),
        )
    except Exception:
        return pd.DataFrame()


def format_time(seconds):
    m, s = int(seconds // 60), int(seconds % 60)
    return f"{m:02d}:{s:02d}"


# ──────────────────────────────────────────────────────────────────────────────
# Board HTML renderer
# ──────────────────────────────────────────────────────────────────────────────

def _cell_style_content(cell, game_over):
    """Return (css_class, display_content) for a cell."""
    if cell["defused"]:
        return "defused", "💣"
    if game_over and cell["is_mine"]:
        return "mine-shown", "💣"
    if cell["revealed"]:
        n = cell["adjacent"]
        if n == 0:
            return "revealed empty", ""
        return f"revealed n{n}", str(n)
    if cell["flagged"]:
        return "flagged", "🚩"
    return "unrevealed", ""


def generate_board_html(board, rows, cols, game_over, locked):
    cell_px = max(28, min(40, 580 // cols))
    grid_w = cols * (cell_px + 2) + 8

    cells_html = ""
    for r in range(rows):
        for c in range(cols):
            cls, content = _cell_style_content(board[r][c], game_over)
            if not locked and "unrevealed" in cls or "flagged" in cls:
                data = f'data-r="{r}" data-c="{c}"'
            else:
                data = ""
            cells_html += f'<div class="ms-cell {cls}" {data}>{content}</div>\n'

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin:0; padding:4px; background:transparent; font-family:Arial,sans-serif; }}
  .ms-grid {{
    display: inline-grid;
    grid-template-columns: repeat({cols}, {cell_px}px);
    gap: 2px;
    background: #9e9e9e;
    padding: 4px;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18);
    user-select: none;
  }}
  .ms-cell {{
    width:{cell_px}px; height:{cell_px}px;
    display:flex; align-items:center; justify-content:center;
    font-size:{max(11, cell_px-12)}px; font-weight:bold;
    border-radius:3px; box-sizing:border-box;
  }}
  .unrevealed {{
    background:#e0e0e0; border:2px outset #fafafa; cursor:pointer;
  }}
  .unrevealed:hover {{ background:#c8c8c8; }}
  .flagged {{
    background:#e0e0e0; border:2px outset #fafafa; cursor:pointer; font-size:{max(10, cell_px-14)}px;
  }}
  .flagged:hover {{ background:#c8c8c8; }}
  .revealed {{ background:#f0f0f0; border:1px solid #bdbdbd; cursor:default; }}
  .empty {{ background:#eeeeee; }}
  .defused {{ background:#c8e6c9; border:1px solid #81c784; cursor:default; font-size:{max(10,cell_px-14)}px; }}
  .mine-shown {{ background:#ffcdd2; border:1px solid #e57373; cursor:default; font-size:{max(10,cell_px-14)}px; }}
  .n1 {{ color:#1565c0; }}
  .n2 {{ color:#2e7d32; }}
  .n3 {{ color:#c62828; }}
  .n4 {{ color:#283593; }}
  .n5 {{ color:#6a1b1b; }}
  .n6 {{ color:#00838f; }}
  .n7 {{ color:#212121; }}
  .n8 {{ color:#757575; }}
  {'* { pointer-events:none !important; cursor:default !important; }' if locked else ''}
</style>
</head>
<body>
<div class="ms-grid" id="grid">{cells_html}</div>
<script>
(function() {{
  var locked = {'true' if locked else 'false'};
  if (locked) return;

  function sendAction(r, c, action) {{
    var inputs = window.parent.document.querySelectorAll('input[placeholder="MS_CLICK_BRIDGE"]');
    if (inputs.length === 0) return;
    var input = inputs[0];
    var setter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
    setter.call(input, r + ',' + c + ',' + action);
    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
  }}

  document.getElementById('grid').addEventListener('click', function(e) {{
    var cell = e.target.closest('[data-r]');
    if (cell) sendAction(cell.dataset.r, cell.dataset.c, 'reveal');
  }});

  document.getElementById('grid').addEventListener('contextmenu', function(e) {{
    e.preventDefault();
    var cell = e.target.closest('[data-r]');
    if (cell) sendAction(cell.dataset.r, cell.dataset.c, 'flag');
  }});

  document.addEventListener('contextmenu', function(e) {{ e.preventDefault(); }});
}})();
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────

def inject_css():
    st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0.8rem 1.5rem 2rem !important; }

/* Hide click bridge input */
[data-testid="stTextInput"]:has(input[placeholder="MS_CLICK_BRIDGE"]) {
    position: absolute; opacity: 0; pointer-events: none;
    height: 0 !important; overflow: hidden; margin: 0; padding: 0;
}

.ms-stat-box {
    background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 10px;
    padding: 0.5rem 1rem; text-align: center;
}
.ms-stat-label { font-size: 0.72rem; color: #6c757d; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.ms-stat-value { font-size: 1.5rem; font-weight: 800; color: #1c2f45; font-family: monospace; }
.ms-rescue-box {
    background: linear-gradient(135deg, #fff3e0 0%, #fce4ec 100%);
    border: 2px solid #ff8f00; border-radius: 14px; padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.ms-level-badge {
    display: inline-block; border-radius: 8px; padding: 3px 10px;
    font-size: 0.75rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem;
}
.ms-win-box {
    background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
    border: 2px solid #43a047; border-radius: 14px; padding: 1.5rem;
    text-align: center; margin-bottom: 1rem;
}
.ms-lose-box {
    background: linear-gradient(135deg, #ffebee 0%, #fce4ec 100%);
    border: 2px solid #e53935; border-radius: 14px; padding: 1.5rem;
    text-align: center; margin-bottom: 1rem;
}
</style>""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Render helpers
# ──────────────────────────────────────────────────────────────────────────────

def render_timer():
    ss = st.session_state
    if not ss.ms_started or ss.ms_start_time is None:
        return
    if ss.ms_game_over:
        elapsed = getattr(ss, "ms_elapsed_final", time.time() - ss.ms_start_time)
        st.components.v1.html(f"""
<div style='text-align:center'>
  <div style='font-size:0.75rem;color:#888;'>⏱ Time</div>
  <div style='font-size:2rem;font-weight:800;color:#E65100;font-family:monospace;'>{format_time(elapsed)}</div>
</div>""", height=60)
        return
    start = ss.ms_start_time
    st.components.v1.html(f"""
<script>
var _s={start};
function _tick(){{
  var el=document.getElementById('ms-timer');
  if(!el)return;
  var e=Date.now()/1000-_s, m=Math.floor(e/60), s=Math.floor(e%60);
  el.innerText=(m<10?'0':'')+m+':'+(s<10?'0':'')+s;
}}
setInterval(_tick,1000); _tick();
</script>
<div style='text-align:center'>
  <div style='font-size:0.75rem;color:#888;'>⏱ Time</div>
  <div id='ms-timer' style='font-size:2rem;font-weight:800;color:#E65100;font-family:monospace;'>00:00</div>
</div>""", height=60)


def render_stats():
    ss = st.session_state
    flags = count_flags(ss.ms_board, ss.ms_rows, ss.ms_cols)
    remaining = ss.ms_mines - flags

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="ms-stat-box">
            <div class="ms-stat-label">💣 Mines Left</div>
            <div class="ms-stat-value">{remaining}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="ms-stat-box">
            <div class="ms-stat-label">🚩 Flags</div>
            <div class="ms-stat-value">{flags}</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="ms-stat-box">
            <div class="ms-stat-label">💥 Rescues</div>
            <div class="ms-stat-value">{ss.ms_mine_hit_count}</div></div>""", unsafe_allow_html=True)
    with c4:
        render_timer()


def render_board_component(conn):
    ss = st.session_state
    locked = ss.ms_game_over or ss.ms_sql_rescue

    # Click bridge — hidden input
    click_val = st.text_input("", key="ms_click_bridge", placeholder="MS_CLICK_BRIDGE",
                               label_visibility="collapsed")

    # Process incoming click
    if click_val:
        parts = click_val.split(",")
        if len(parts) == 3:
            r, c, action = int(parts[0]), int(parts[1]), parts[2]
            if action == "reveal" and not locked:
                handle_cell_click(r, c, conn)
            elif action == "flag" and not locked:
                handle_flag_click(r, c)
        st.session_state["ms_click_bridge"] = ""
        st.rerun()

    board_html = generate_board_html(
        ss.ms_board, ss.ms_rows, ss.ms_cols, ss.ms_game_over, locked
    )
    cell_px = max(28, min(40, 580 // ss.ms_cols))
    height = ss.ms_rows * (cell_px + 2) + 24
    st.components.v1.html(board_html, height=height, scrolling=False)

    st.caption("Left-click to reveal · Right-click to flag/unflag")


def render_sql_rescue(conn):
    ss = st.session_state
    q = ss.ms_sql_question
    level = min(ss.ms_mine_hit_count, 5)
    level_name, level_desc = LEVEL_NAMES[level]
    accent = LEVEL_ACCENT[level]

    st.markdown(f"""<div class="ms-rescue-box">
<h3 style="margin:0 0 0.3rem">💣 Mine #{ss.ms_mine_hit_count} — Defuse it with SQL!</h3>
<span class="ms-level-badge" style="background:{accent}">Level {level}: {level_name}</span>
<p style="margin:0.3rem 0 0; font-size:0.85rem; color:#5d4037;">{level_desc} — answer correctly to continue playing.</p>
</div>""", unsafe_allow_html=True)

    st.markdown(f"**Question:** {q['text']}")
    st.divider()

    # SQL editor
    sql_key = f"ms_sql_editor_{ss.ms_mine_hit_count}"
    sql_input = st.text_area(
        "Write your SQL query here:",
        value=ss.ms_sql_input,
        height=110,
        key=sql_key,
        placeholder="SELECT ...",
    )
    ss.ms_sql_input = sql_input

    col_run, col_hint, col_giveup = st.columns([1, 1, 1])
    with col_run:
        if st.button("▶ Run Query", use_container_width=True):
            if sql_input.strip():
                result = run_sql(sql_input, conn)
                if isinstance(result, pd.DataFrame):
                    ss.ms_last_query_result = result
                    ss.ms_last_query_error = None
                else:
                    ss.ms_last_query_error = result
                    ss.ms_last_query_result = None
            st.rerun()

    with col_hint:
        hint_label = "💡 Hint" + (" (used)" if ss.ms_sql_hint_shown else "")
        if st.button(hint_label, use_container_width=True):
            ss.ms_sql_hint_shown = True
            ss.ms_hints_used_total += 1
            st.rerun()

    with col_giveup:
        if st.button("💀 Give Up", use_container_width=True, type="secondary"):
            ss.ms_game_over = True
            ss.ms_won = False
            ss.ms_sql_rescue = False
            if ss.ms_start_time:
                ss.ms_elapsed_final = time.time() - ss.ms_start_time
            st.rerun()

    # Query result display
    if ss.ms_last_query_error:
        st.error(ss.ms_last_query_error)
    elif ss.ms_last_query_result is not None:
        st.dataframe(ss.ms_last_query_result, use_container_width=True, hide_index=True)

    # Hint display
    if ss.ms_sql_hint_shown:
        hint_text = build_hint(q, sql_input if sql_input.strip() else ss.ms_sql_input, conn)
        st.info(hint_text)

    # Feedback from wrong attempt
    if ss.ms_feedback:
        st.warning(ss.ms_feedback)

    st.divider()
    # Answer submission
    ans_key = f"ms_answer_{ss.ms_mine_hit_count}_{ss.ms_sql_wrong_attempts}"
    if q["validator_type"] == "dataframe_match":
        st.markdown("**Answer:** Run a query that produces the expected output, then click Submit.")
        answer_input = ""
    else:
        answer_input = st.text_input("Your answer:", key=ans_key,
                                      placeholder="Type your answer here...")

    if st.button("✅ Submit Answer", type="primary", use_container_width=True):
        last_df = ss.ms_last_query_result
        correct = validate_answer(answer_input, q, conn, last_df)
        if correct:
            r, c = ss.ms_sql_bomb_pos
            defuse_mine(r, c)
            ss.ms_feedback = None
            st.balloons()
            st.rerun()
        else:
            ss.ms_sql_wrong_attempts += 1
            ss.ms_feedback = (
                f"Not quite! Attempt #{ss.ms_sql_wrong_attempts}. "
                "Try refining your query or check the hint."
            )
            st.rerun()


def render_end_screen(conn):
    ss = st.session_state
    elapsed = getattr(ss, "ms_elapsed_final", None)
    if elapsed is None and ss.ms_start_time:
        elapsed = time.time() - ss.ms_start_time
        ss.ms_elapsed_final = elapsed
    elapsed = elapsed or 0

    max_sql_level = min(ss.ms_mine_hit_count, 5)
    score = calculate_score(ss.ms_difficulty, elapsed, ss.ms_mine_hit_count, max_sql_level)

    if ss.ms_won:
        st.markdown(f"""<div class="ms-win-box">
<h2 style="margin:0;color:#2e7d32;">🎉 Board Cleared!</h2>
<p style="margin:0.3rem 0 0;color:#1b5e20;">You defused all mines and cleared the {ss.ms_difficulty} board!</p>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="ms-lose-box">
<h2 style="margin:0;color:#c62828;">💥 Game Over</h2>
<p style="margin:0.3rem 0 0;color:#b71c1c;">You gave up on mine #{ss.ms_mine_hit_count}.</p>
</div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("⏱ Time", format_time(elapsed))
    with c2:
        st.metric("💣 Rescues", ss.ms_mine_hit_count)
    with c3:
        st.metric("🧠 Max SQL Level", max_sql_level)
    with c4:
        st.metric("⭐ Score", score)

    # Save to leaderboard (wins only)
    if ss.ms_won and not ss.ms_saved and ss.ms_nickname:
        save_to_leaderboard(conn, ss.ms_nickname, ss.ms_difficulty, elapsed,
                            ss.ms_mine_hit_count, max_sql_level, ss.ms_hints_used_total, score)
        ss.ms_saved = True
        st.success("Score saved to leaderboard!")

    if st.button("🔄 Play Again", type="primary"):
        for key in list(st.session_state.keys()):
            if key.startswith("ms_"):
                del st.session_state[key]
        st.rerun()


def render_leaderboard(conn):
    st.subheader("🏆 Leaderboard")
    tabs = st.tabs(["Easy", "Medium", "Expert"])
    for i, diff in enumerate(["Easy", "Medium", "Expert"]):
        with tabs[i]:
            lb = get_leaderboard(conn, diff)
            if lb.empty:
                st.info(f"No {diff} completions yet. Be the first!")
                continue

            # Podium
            top3 = lb.head(3)
            medals = ["🥇", "🥈", "🥉"]
            cols = st.columns(len(top3))
            for j, (_, row) in enumerate(top3.iterrows()):
                with cols[j]:
                    st.markdown(f"""<div style="text-align:center;background:#f8f9fa;
                        border-radius:12px;padding:0.8rem;border:1px solid #dee2e6;">
                        <div style="font-size:1.8rem">{medals[j]}</div>
                        <div style="font-weight:700;font-size:0.95rem">{row['nickname']}</div>
                        <div style="color:#388e3c;font-weight:700">{int(row['score'])} pts</div>
                        <div style="font-size:0.78rem;color:#666">{format_time(row['completion_time_seconds'])}</div>
                        <div style="font-size:0.72rem;color:#888">{row['mines_hit']} rescues · SQL L{int(row['max_sql_level'])}</div>
                    </div>""", unsafe_allow_html=True)

            st.divider()
            # Full table
            display = lb.copy()
            display.insert(0, "Rank", range(1, len(display) + 1))
            display["Time"] = display["completion_time_seconds"].apply(format_time)
            display["SQL Level"] = display["max_sql_level"].astype(int)
            display["Rescues"] = display["mines_hit"].astype(int)
            display["Hints"] = display["hints_used"].astype(int)
            display["Score"] = display["score"].astype(int)
            display["Date"] = pd.to_datetime(display["played_at"]).dt.strftime("%Y-%m-%d")
            st.dataframe(
                display[["Rank", "nickname", "Score", "Time", "Rescues", "SQL Level", "Hints", "Date"]].rename(
                    columns={"nickname": "Player"}),
                use_container_width=True, hide_index=True,
            )


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    inject_css()
    init_session_state()
    conn = get_connection()

    ss = st.session_state
    game_tab, lb_tab = st.tabs(["💣 Play", "🏆 Leaderboard"])

    with lb_tab:
        render_leaderboard(conn)

    with game_tab:
        if not ss.ms_started:
            # Setup screen
            st.markdown("## 💣 SQL Minesweeper")
            st.markdown(
                "Classic Minesweeper — but when you hit a mine, you must solve an **NBA SQL query** to defuse it "
                "and continue playing! Each rescue escalates the SQL difficulty. Left-click to reveal, "
                "right-click to flag."
            )
            st.divider()
            c1, c2 = st.columns([1, 1])
            with c1:
                difficulty = st.radio("Difficulty", ["Easy", "Medium", "Expert"],
                                      captions=["9×9, 10 mines", "16×16, 40 mines", "16×30, 99 mines"],
                                      horizontal=False)
            with c2:
                st.markdown("**SQL Rescue Levels**")
                for lvl, (name, desc) in LEVEL_NAMES.items():
                    accent = LEVEL_ACCENT[lvl]
                    st.markdown(
                        f'<span style="background:{accent};color:#fff;border-radius:6px;'
                        f'padding:2px 8px;font-size:0.75rem;font-weight:700;">L{lvl}</span> '
                        f'**{name}** — {desc}',
                        unsafe_allow_html=True,
                    )
                    if lvl < 5:
                        st.markdown("")

            st.divider()
            nickname = st.text_input("Your nickname (for leaderboard):", max_chars=24,
                                      placeholder="Enter nickname...")
            if st.button("🚀 Start Game", type="primary", disabled=not nickname.strip()):
                start_game(difficulty, nickname.strip())
                st.rerun()
            return

        # Active game
        st.markdown(
            f"**💣 SQL Minesweeper** · {ss.ms_difficulty} "
            f"({ss.ms_rows}×{ss.ms_cols}, {ss.ms_mines} mines) · "
            f"Player: **{ss.ms_nickname}**",
        )

        render_stats()
        st.divider()

        if ss.ms_game_over:
            render_end_screen(conn)
            st.divider()

        render_board_component(conn)

        if ss.ms_sql_rescue and not ss.ms_game_over:
            st.divider()
            render_sql_rescue(conn)


if __name__ == "__main__":
    main()
