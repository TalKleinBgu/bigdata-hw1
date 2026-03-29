---
title: Big Data HW1
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.37.0"
app_file: app.py
pinned: false
license: mit
---

# Big Data Homework 1

**Tal Klein**  
Course: *The Art of Analyzing Big Data: The Data Scientist's Toolbox* - Dr. Michael Fire

## Overview
This repository contains one unified Streamlit deployment with separate pages for all homework tasks:

- Task 1: Baby Names Explorer
- Task 2: Oscar Actor Explorer
- Task 3: Pokemon Battle Arena
- Task 4: NBA SQL Trivia (Bonus)

Each task also has its own dedicated `README.md` inside its folder with requirement mapping and implementation notes.

## Live Demo
Streamlit deployment link: `https://bigdata-hw1.streamlit.app/`

## Unified Deployment Structure
- Main app entry point: `app.py`
- Streamlit page wrappers: `pages/`
- Task implementations:
  - `task1_baby_names/`
  - `task2_oscar/`
  - `task3_pokemon/`
  - `task4_sql_game/`

## Task Summary

### Task 1 - Baby Names Explorer
- SQLite-backed analysis of US baby names data
- Name popularity trends (raw and relative)
- Custom SQL panel (`SELECT`-only safety)
- Additional visualization and pattern discovery section

Task README: [task1_baby_names/README.md](task1_baby_names/README.md)

### Task 2 - Oscar Actor Explorer
- ORM-based modeling with SQLAlchemy
- Actor/director profile cards with live Wikipedia enrichment
- Insights including wins, nominations, categories, and timeline metrics
- Interesting finds and bonus fun-fact section

Task README: [task2_oscar/README.md](task2_oscar/README.md)

### Task 3 - Pokemon Battle Arena
- SQLite-driven battle mechanics (no hardcoded stats)
- Team selection, turn-by-turn battle log, and win conditions
- Cheat codes implemented via real SQL write operations
- Cheat audit and dataset analysis queries

Task README: [task3_pokemon/README.md](task3_pokemon/README.md)

### Task 4 - NBA SQL Trivia (Bonus)
- Interactive SQL learning game with 5 progressive levels
- Real SQLite backend, query execution, validation, and hints
- Progress tracking, scoring, timing, and leaderboard
- README includes explicit design choices and SQL concepts taught

Task README: [task4_sql_game/README.md](task4_sql_game/README.md)

## Tech Stack
- Python
- Streamlit
- SQLite (`sqlite3`)
- SQLAlchemy (Task 2)
- pandas
- Plotly
- requests / Wikipedia APIs (Task 2)
- nba_api (Task 4)

## Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the landing page and navigate to each task page from the home screen.

## Data Sources
| Task | Data | Source |
|------|------|--------|
| 1 | US Baby Names | NationalNames / StateNames dataset |
| 2 | Oscar Awards | Kaggle Oscar dataset |
| 3 | Pokemon stats | Kaggle Pokemon dataset |
| 4 | NBA players/teams/games | `nba_api` (NBA.com) + local SQLite cache |
