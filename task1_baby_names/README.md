# Task 1: Baby Names Explorer

## What this task includes
This app implements Task 1 using SQLite (`sqlite3`) and Streamlit:

1. Data loading from CSV into SQLite.
2. Indexed schema for fast analytical queries.
3. Interactive name popularity explorer (single or multiple names).
4. SQL panel that allows only `SELECT`/`WITH` queries.
5. Extra visualization: name diversity over time.
6. Pattern discovery section with 3 findings and interpretations.

## Assignment checklist mapping
- Task 1.1 Data Loading and Schema:
  - Table includes `Id`, `Name`, `Year`, `Gender`, `Count`, `State`.
  - Indexes include `(Name, Year)`, `(Year, Gender)`, and additional helper indexes.
- Task 1.2A Name Popularity Over Time:
  - Comma-separated names input.
  - Toggle for raw count vs relative popularity (percent of births that year).
- Task 1.2B Custom SQL Query Panel:
  - Free SQL textbox with safety block for non-`SELECT` queries.
  - Built-in example queries with one-click auto-fill.
  - Result table plus automatic chart where relevant.
- Task 1.2C Additional Visualization:
  - Name diversity trend (unique names per year).
- Task 1.3 Pattern Discovery:
  - Three documented patterns in the app with query/visual support and interpretation.

## How to run
From the repository root:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open page: `Task 1 - Baby Names` (route `/Baby_Names` in the unified deployment).

## Main files
- `task1_baby_names/app.py` - full Task 1 app logic.
- `task1_baby_names/baby_names.db` - SQLite database used by the app.
- `task1_baby_names/StateNames.csv` - source dataset.

## Notes for submission
- You can submit one deployment link that contains all tasks as separate pages.
- In your written report, explain in your own words:
  - schema and index choices,
  - how the SQL safety guard works,
  - and the meaning of your 3 discovered patterns.
