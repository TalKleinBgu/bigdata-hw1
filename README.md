# Big Data Homework 1

**Tal Klein**
Course: *The Art of Analyzing Big Data: The Data Scientist's Toolbox* — Dr. Michael Fire

---

## Overview

This repository contains 4 interactive data applications built with Streamlit, SQLite, and Python — each demonstrating a different aspect of data engineering and analysis.

## Tasks

### Task 1 — Baby Names Explorer
Explore 5.6 million US baby name records stored in SQLite.
- Name popularity over time (raw count vs. percentage)
- Custom SQL query panel with pre-built examples and auto-charting
- Name diversity trends and regional analysis

**Stack:** `sqlite3` · `pandas` · `Streamlit` · `Plotly`

---

### Task 2 — Oscar Actor Explorer
Browse Oscar Award nominations modeled with SQLAlchemy ORM.
- Actor profile cards with Wikipedia photo and bio
- Win statistics, nomination timeline, category percentile
- Discoveries: longest wait for first win, multi-category nominees

**Stack:** `SQLAlchemy` · `requests` (Wikipedia REST API) · `Streamlit` · `Plotly`

---

### Task 3 — Pokémon Battle Arena
Build your team and battle with type-advantage mechanics powered by SQL.
- Speed-based turn order, Attack vs Defense damage formula
- Full battle log with turn-by-turn breakdown
- Cheat codes with real SQL write operations + audit trail

**Stack:** `sqlite3` · `Streamlit` · `Plotly`

---

### Task 4 — NBA SQL Trivia ⭐ Bonus
An interactive SQL learning game with real NBA data and 5 progressive levels.
- Randomized questions from SELECT → WHERE → ORDER BY → GROUP BY → JOIN
- Live timer, hint system, persistent leaderboard with podium visualization
- Practice court (free SQL sandbox) and Quick ID Lookup sidebar widget

**Stack:** `nba_api` · `sqlite3` · `pandas` · `Streamlit` · `Plotly`

---

## Running Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The landing page links to all 4 tasks. Databases are built automatically on first run from the CSV files — no manual setup required.

## Data Sources

| Task | Data | Source |
|------|------|--------|
| 1 | US Baby Names (5.6M rows) | Kaggle / SSA |
| 2 | Oscar Awards | Kaggle dataset |
| 3 | Pokémon stats | Kaggle dataset |
| 4 | NBA player/team/game data | `nba_api` (NBA.com) |
