# CLAUDE.md — HW1: The Art of Analyzing Big Data

## Project Overview

This is Homework Assignment 1 for the course **"The Art of Analyzing Big Data: The Data Scientist's Toolbox"** (Dr. Michael Fire).

The assignment consists of **4 tasks** (25pt each, total 100pt + 5pt bonus):
1. Baby Names Explorer (SQLite + interactive app)
2. Oscar Actor Explorer (ORM + Wikipedia API)
3. Pokémon Battle Arena (SQLite + game mechanics)
4. SQL Learning Game (interactive teaching platform)

---

## Implementation Details

### Data Loading — All Tasks Use Local CSV Files

All tasks load data from **local CSV files** placed in each task folder. No downloads or URL connections are used.

- **Task 1**: Place `StateNames.csv` in `task1_baby_names/`. The app uses `pandas.to_sql()` for fast bulk loading (~5.6M rows). The DB is built on first run and cached as `baby_names.db`.
- **Task 2**: Place `full_data.csv` (tab-separated) in `task2_oscar/`. The DB is built via SQLAlchemy ORM on first run and cached as `oscar.db`.
- **Task 3**: `Pokemon.csv` is already in `task3_pokemon/`.
- **Task 4**: No external data needed — the basketball database is generated from hardcoded data in the app.

### Streamlit Theme

All tasks use a consistent light theme:
```toml
primaryColor = "#4A90D9"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F4F8"
textColor = "#1E1E1E"
```
Exception: Task 4 uses an orange basketball theme (`primaryColor = "#F57C00"`, dark background).

---

## Task 1: Baby Names Explorer (25pt)

**Dataset**: `StateNames.csv` (US Baby Names with State column)
**Backend**: SQLite via Python's built-in `sqlite3`
**App**: `task1_baby_names/app.py`

### Task 1.1 — Data Loading & Schema Design (5pt)

- Table `national_names` with columns: `Id`, `Name`, `Year`, `Gender`, `State`, `Count`
- **3 indexes**:
  1. `idx_name_year` on (Name, Year) — speeds up name popularity lookups
  2. `idx_year_gender` on (Year, Gender) — speeds up yearly aggregate queries
  3. `idx_state` on (State) — speeds up regional filtering/grouping

### Task 1.2 — Interactive Name Explorer App (15pt)

**A. Name Popularity Over Time**
- User types names (comma-separated) → line chart
- Toggle: raw count vs. percentage of all births
- Plots use crosshair/spike mode (no zoom-on-drag)

**B. Custom SQL Query Panel**
- Free-text box for any SELECT/WITH query
- 3 pre-built example queries as clickable buttons (auto-run on click):
  - "Top 10 names in 2010"
  - "Gender-neutral names"
  - "Names that disappeared after 1980"
- Safety: blocks non-SELECT queries with a friendly error message
- Auto-chart: detects numeric + categorical columns and renders bar/line chart

**C. Name Diversity Over Time**
- Dual-axis chart: unique names per year + average count per name

### Task 1.3 — Pattern Discovery (10pt)

1. **Name Diversity Explosion Since the 1950s** — unique names per year chart with 1950 reference line
2. **Pop-Culture Influence: The "Arya" Effect** — bar chart showing Game of Thrones name spike
3. **Regional Naming: The State Divide** — state-level name comparison (e.g., "Jose" in CA vs MT), top name per state table

---

## Task 2: Oscar Actor Explorer (25pt)

**Dataset**: `full_data.csv` (Oscar Award dataset, tab-separated)
**ORM**: SQLAlchemy
**App**: `task2_oscar/app.py`

### Task 2.1 — Data Modeling with ORM (5pt)

- Single `Nomination` model with columns: id, year_film, year_ceremony, ceremony, category, name, film, winner
- Indexes on name, category, year_ceremony, year_film
- Schema explanation in sidebar expander

### Task 2.2 — Actor Profile App (10pt)

- **Name search**: Selectbox with autocomplete + fuzzy matching fallback
- **Filtered to actors/directors only** (categories: ACTOR%, ACTRESS%, DIRECTING%)
- **Profile card**: Wikipedia photo, bio summary, birth date (via REST API)
- **Oscar stats**: nominations, wins, win rate, years active, category percentile comparison, years to first win
- **Nominations table**: all nominations with year, category, film, result
- **Edge cases**: not found → fuzzy suggestions, no wins handled, no Wikipedia → graceful fallback

### Task 2.3 — Interesting Finds (10pt)

1. **Most Nominated Without a Win** — horizontal bar chart (blue gradient)
2. **Longest Wait for First Win** — timeline visualization (nomination → win)
3. **Multi-Category Nominees** — bar chart + category breakdown for top 5

All discoveries filtered to actors/directors only. ORM query code shown in expanders.

**Bonus**: "Did You Know?" fun facts auto-generated per actor (percentile, win %, age at first nomination, wait time).

### Wikipedia Integration

Uses the Wikipedia REST API (`/api/rest_v1`):
- `/page/summary/{title}` for bio + thumbnail image
- `/page/media-list/{title}` as image fallback
- `/page/html/{title}` for birth date extraction from infobox

---

## Task 3: Pokémon Battle Arena (25pt)

**Dataset**: `Pokemon.csv`
**Backend**: SQLite via `sqlite3`
**App**: `task3_pokemon/app.py`

### Task 3.1 — Data Loading & Schema (5pt)

- Load Pokémon dataset into SQLite
- Additional tables: type-effectiveness table, battle history log

### Task 3.2 — Battle Game (10pt)

- Team selection (1–3 Pokémon per player)
- Battle mechanics: Speed → turn order, Attack vs Defense → damage, type advantages from DB
- Battle log with turn-by-turn details
- Player vs AI mode

### Task 3.3 — Cheat Codes (5pt)

- At least 3 cheats with real SQL write operations (UPDATE/INSERT)
- Cheat audit query to detect cheats post-game

### Task 3.4 — Pokémon Analysis (5pt)

- 2 interesting insights via SQL queries

---

## Task 4: NBA SQL Trivia (25pt + bonus)

**Theme**: NBA Trivia Game — test your SQL skills with real NBA data
**App**: `task4_sql_game/app.py`
**Database**: Auto-generated `nba_trivia.db` (fetched from `nba_api` or fallback hardcoded data)

### Data Source

- **Primary**: `nba_api` Python package — fetches real NBA data (players, teams, games) from NBA.com
- **Fallback**: Hardcoded realistic dataset (30 teams, 150 players, 450 games) if API unavailable
- Fetch-once-cache pattern: data stored in SQLite on first run, fully offline after that

### Database Schema

- `teams` (30 NBA teams — full_name, city, abbreviation, conference, division, wins, losses)
- `players` (150+ players — name, position, age, ppg, rpg, apg, spg, bpg, fg_pct, fg3_pct, ft_pct, gp)
- `games` (450+ games — home/away teams, scores, dates)
- `leaderboard` (persistent — nickname, completion time, score, hints used, date)

### 5 Progressive Levels (Randomized Questions)

1. **SELECT \*** — basic retrieval (player info, team info, counts)
2. **WHERE / AND / OR** — filtering (stats thresholds, conference filtering)
3. **ORDER BY / LIMIT** — ranking (top scorers, best teams, nth highest)
4. **GROUP BY / AVG / COUNT** — aggregation (team averages, position stats)
5. **JOIN** — combining tables (home wins, top scorer per team, games between teams)

Each level has a pool of 6+ question templates. Questions are parameterized with random teams/players/thresholds, so **every game session is different**.

### Features

- **Randomized questions**: 30+ question generators ensure no two games are alike
- **Timer**: Clock runs from game start, tracks total completion time
- **Leaderboard**: Persistent SQLite table — compete for fastest completion
- **Practice Court**: Free SQL sandbox with example queries
- **Hints**: 1 hint per level, costs -10 points
- **Scoring**: 100 pts/level (−10 per hint), max 500
- **Answer validation**: Fuzzy matching for names/teams (accepts nicknames, last names, etc.)
- **Safety**: Only SELECT queries allowed

---

## Tech Stack (Actual)

| Task | Stack |
|---|---|
| Task 1 | `sqlite3`, `pandas`, `Streamlit`, `plotly` |
| Task 2 | `SQLAlchemy`, `requests` (Wikipedia REST API), `Streamlit`, `plotly` |
| Task 3 | `sqlite3`, `Streamlit` |
| Task 4 | `sqlite3`, `pandas`, `nba_api`, `Streamlit` |

---

## Running the Apps

Each task is a standalone Streamlit app:
```bash
cd task1_baby_names && streamlit run app.py
cd task2_oscar && streamlit run app.py
cd task3_pokemon && streamlit run app.py
cd task4_sql_game && streamlit run app.py
```

---

## Notes

- All written explanations must be **your own words** — no LLM output.
- You may be asked to explain your solution **in person**.
- Prioritize deployed apps (Streamlit Cloud, HuggingFace Spaces) for best presentation.
- To rebuild a database: stop Streamlit, delete the `.db` file, restart the app.
