# Task 4: SQL Learning Game (Bonus)

## What this task includes
This app implements an interactive SQL learning platform with a real SQLite backend:

1. Real database with preloaded sports data.
2. SQL input where learners execute real queries.
3. Five progressive levels that teach core SQL skills.
4. Validation and hint system for wrong answers.
5. Progress tracking across levels.
6. Gamification features (score, timing, leaderboard, practice mode).

## Assignment checklist mapping
- Task 4.1 Core Platform:
  - SQLite database runs in the background.
  - Interactive SQL input executes learner queries.
  - 5 progressive levels:
    - Level 1: `SELECT`
    - Level 2: `WHERE`
    - Level 3: `ORDER BY` / `LIMIT`
    - Level 4: `GROUP BY` / aggregates
    - Level 5: `JOIN`
  - Feedback system checks correctness and provides hints.
  - Progress tracking shows completed levels.
- Task 4.2 Engagement and Creativity:
  - Trivia/game format with scoring and timer.
  - Leaderboard for competition.
  - Practice SQL sandbox and table exploration UI.
  - Visual analytics components for engagement.

## How to run
From the repository root:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open page: `Task 4 - NBA SQL Trivia` (route `/NBA_Trivia` in the unified deployment).

## Main files
- `task4_sql_game/app.py` - full Task 4 platform logic.
- `task4_sql_game/nba_trivia.db` - SQLite database used by game and practice tabs.

## Design choices
- Beginner-first progression:
  - The game is structured as 5 ordered levels so learners build SQL skills step by step instead of facing all concepts at once.
- Learn by doing on real data:
  - Learners run real SQL against a live SQLite database, which gives authentic query behavior and realistic mistakes.
- Immediate formative feedback:
  - Answers are validated and paired with hints that explain what to try next, reducing frustration and keeping momentum.
- Motivation through gamification:
  - Score, timer, and leaderboard create a clear goal and replay value, encouraging repeated practice.
- Safe exploration space:
  - A practice sandbox allows free `SELECT` experimentation without affecting challenge progress.
- Visibility and orientation:
  - Progress indicators, table previews, and helper examples make the platform usable for complete beginners.

## SQL concepts taught
The platform teaches the following SQL concepts in sequence:

1. `SELECT` (Level 1)
   - Retrieving all columns (`SELECT *`) and selecting specific columns.
2. `WHERE` (Level 2)
   - Filtering rows with conditions, numeric comparisons, and logical combinations.
3. `ORDER BY` and `LIMIT` (Level 3)
   - Sorting results and returning top/bottom-N answers.
4. `GROUP BY` with aggregations (Level 4)
   - Using `COUNT`, `AVG`, and grouped summaries to answer analysis questions.
5. `JOIN` (Level 5)
   - Combining related tables (for example players/teams/games) to answer multi-table queries.

Additional concepts reinforced across levels:
- Aliases for readability (`AS`).
- `HAVING` for post-aggregation filtering (when applicable).
- Interpreting query results as evidence for answering data questions.

## Notes for submission
- Prepare a short 2-3 minute demo video focused on:
  - one full run through the levels,
  - how hints/feedback work,
  - and leaderboard/progress behavior.
- In your written report, explain:
  - why your game flow teaches SQL effectively for beginners,
  - and how your engagement features improve learning.
