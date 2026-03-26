# Task 3: Pokemon Battle Arena

## What this task includes
This app implements Task 3 with SQLite-backed game logic and Streamlit:

1. Pokemon stats loaded from dataset into SQLite.
2. Battle system where turn order, damage, and effectiveness are data-driven.
3. Team selection (1-3 Pokemon per side).
4. Type effectiveness table stored in database and used in battle calculations.
5. Cheat code system that performs real SQL write operations.
6. Cheat audit queries to detect modified data.
7. Analysis section with SQL insights from the Pokemon dataset.

## Assignment checklist mapping
- Task 3.1 Data Loading and Schema:
  - `pokemon` table for stats.
  - `type_effectiveness` table for multipliers.
  - `battle_history` table for logs.
  - Backup/original table used for cheat restoration/audit.
- Task 3.2 Battle Game:
  - Team picking from database values only.
  - Speed-based turn order.
  - Damage derived from attack/defense stats.
  - Type multiplier applied from DB table.
  - Turn-by-turn battle log and win condition.
- Task 3.3 Cheat Codes:
  - Cheat codes execute SQL writes (`UPDATE`/`INSERT`) on DB.
  - Includes multiple cheats and a post-battle audit query section.
- Task 3.4 Pokemon Analysis:
  - In-app SQL analyses (for example, type combo strength and generation power trends).

## How to run
From the repository root:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open page: `Task 3 - Pokemon Arena` (route `/Pokemon` in the unified deployment).

## Main files
- `task3_pokemon/app.py` - full Task 3 app logic.
- `task3_pokemon/pokemon.db` - SQLite database used by battle and analytics.
- `task3_pokemon/Pokemon.csv` - source dataset.

## Notes for submission
- A single deployment with separate task pages is fine if navigation is clear.
- In your written report, document:
  - the exact damage formula,
  - how type effectiveness is applied,
  - and proof that cheats are implemented through real database writes.
