# Task 4: SQL Minesweeper

## What this task includes
This app implements a Minesweeper game with SQL rescue challenges:

1. Classic board gameplay (reveal/flag, easy-medium-expert boards).
2. SQL rescue flow when stepping on a mine.
3. Difficulty-scaled SQL questions using NBA data.
4. Leaderboard with score, time, rescues, and SQL level.
5. Restart flow with same nickname and difficulty picker.

## How to run
From the repository root:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open page: `Task 4 - SQL Minesweeper` (route `/Minesweeper`).

## Main files
- `task4_minesweeper/app.py` - full Task 4 app logic.
- `task4_minesweeper/minesweeper.db` - SQLite database used by the game.

## Notes
- Right-click places/removes a flag.
- Hitting a mine opens a centered SQL rescue popup.
- If you give up or lose, mines are exposed on the board.
