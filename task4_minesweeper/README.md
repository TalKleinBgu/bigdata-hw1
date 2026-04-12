# Task 4: SQL Minesweeper

## Overview

Classic Minesweeper fused with a progressive SQL quiz engine. Every mine you step on pauses the game and forces you to answer an NBA-data SQL question before you can continue. The SQL difficulty escalates automatically with each rescue — so early mistakes are forgiving, but later ones demand real query skills.

---

## Design Choices

### Why Minesweeper as the host game?

Minesweeper naturally produces high-stakes moments (hitting a mine) that map cleanly onto a "rescue" mechanic. The tension of being one click away from triggering a challenge keeps SQL practice from feeling like dry homework. The game also has well-understood difficulty tiers (Easy / Medium / Expert), which gives the SQL escalation a natural pacing curve.

### Board rendering: `@st.fragment` + JavaScript/iframe bridge

Streamlit re-renders the entire page on every interaction by default. A 16×30 Expert board has 480 cells — re-rendering all of them on each click would be too slow and would flicker visibly. To solve this:

- The board is rendered inside a `@st.fragment`, which isolates re-renders to just the board component.
- The board HTML is injected into a hidden `st.components.v1.html` iframe. JavaScript inside the iframe captures left-clicks and right-clicks and writes `row,col,action` into a hidden `st.text_input` (the "click bridge").
- Streamlit detects the `text_input` change, the fragment re-runs, processes the click, and re-renders only the board — not the rest of the page.

This pattern works around Streamlit's lack of native grid interaction support without requiring a custom component or a backend websocket.

### SQL rescue flow

When a mine is hit, a rescue dialog replaces the board. The player must answer the SQL question correctly (or accept a hint penalty) to resume. Giving up or timing out ends the game and reveals all mines. This design:

- Makes SQL practice a gate, not an optional extra.
- Keeps the feedback loop tight: wrong answers show the correct query immediately so the player learns before retrying.

### Difficulty escalation

The SQL level the player is currently on is tracked in session state and increments with each mine hit (capped at level 5). This means:

- First mine → easiest SQL level
- Each subsequent mine → harder SQL level
- A player who never hits a mine never faces SQL — staying safe is its own reward.

### Score formula

```
score = base_score
      - (elapsed_seconds * 2)   # time penalty
      - (mines_hit * 50)         # rescue penalty
      + (max_sql_level * 100)    # SQL skill bonus
```

The SQL bonus means that answering hard questions — even after hitting mines — partially offsets the penalty. This rewards engagement with the harder SQL material.

### NBA data: live API with hardcoded fallback

The app fetches real NBA player/team/game data from `nba_api` on first run and stores it in SQLite. If the API is unavailable (rate-limited, offline), a hardcoded fallback dataset of 30 teams and 400+ players is used instead. This ensures the app always works regardless of network conditions.

---

## SQL Concepts Taught

The five SQL levels map to a deliberate learning progression, from the most basic retrieval to multi-table analysis:

### Level 1 — Basic Retrieval (`SELECT *`)

The player must identify a specific row in a table (e.g., "Which team plays in Cleveland?"). This introduces:
- `SELECT *` or `SELECT column` syntax
- Reading and interpreting tabular results

### Level 2 — Filtering (`WHERE / AND / OR`)

Questions require filtering rows by one or more conditions (e.g., "Find all players on the Lakers who score more than 15 PPG"). This teaches:
- `WHERE` clause with equality and comparison operators (`=`, `>`, `<`)
- Combining conditions with `AND` / `OR`
- `LIKE` for partial string matching

### Level 3 — Sorting & Ranking (`ORDER BY / LIMIT`)

Questions ask for top-N results or ranked records (e.g., "Who is the 3rd highest scorer in the league?"). This teaches:
- `ORDER BY column ASC/DESC`
- `LIMIT` and `OFFSET` for pagination and nth-row access
- Combining sort + filter

### Level 4 — Aggregation (`GROUP BY / Aggregates`)

Questions require computing summaries across groups (e.g., "Which position has the highest average rebounds?", "How many teams have at least 5 players with 10+ PPG?"). This teaches:
- Aggregate functions: `COUNT`, `AVG`, `SUM`, `MIN`, `MAX`
- `GROUP BY` to partition rows into groups
- `HAVING` to filter aggregated groups (subquery form)
- `ROUND()` for formatted output

### Level 5 — Combining Tables (`JOIN`)

Questions span two tables — players and teams, or games and teams (e.g., "Who is the top scorer on the team with the most home wins?", "What was the biggest home-court margin of victory?"). This teaches:
- `INNER JOIN` with an explicit `ON` condition
- Multi-table filtering and aggregation
- Aliases (`p`, `t`, `g`) for readable multi-table queries
- Chaining `JOIN` with `ORDER BY`, `GROUP BY`, and `LIMIT`

---

## How to Run

From the repository root:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open page: **Task 4 - SQL Minesweeper** (route `/Minesweeper`).

---

## Main Files

- `task4_minesweeper/app.py` — full game and SQL engine
- `task4_minesweeper/minesweeper.db` — SQLite database (auto-generated on first run)

## Controls

- **Left-click** — reveal a cell
- **Right-click** — place or remove a flag
- Hitting a mine opens the SQL rescue dialog
- Give up ends the game and reveals the board
