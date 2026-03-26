"""
Landing page — Big Data HW1
Tal Klein
"""
import streamlit as st

st.set_page_config(
    page_title="Big Data HW1 — Tal Klein",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── styles ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* hide default sidebar nav labels on landing */
[data-testid="stSidebarNav"] { display: none; }

.hero {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
}
.hero h1 {
    font-size: 3rem;
    font-weight: 800;
    color: #1E1E1E;
    margin-bottom: 0.2rem;
}
.hero .subtitle {
    font-size: 1.15rem;
    color: #555;
    margin-bottom: 0.4rem;
}
.hero .meta {
    font-size: 0.95rem;
    color: #888;
}
.badge {
    display: inline-block;
    background: #4A90D9;
    color: white;
    border-radius: 20px;
    padding: 3px 14px;
    font-size: 0.85rem;
    font-weight: 600;
    margin: 2px;
}

.task-card {
    background: #FFFFFF;
    border: 1.5px solid #E0E7EF;
    border-radius: 16px;
    padding: 1.6rem 1.4rem 1.2rem;
    height: 100%;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
    position: relative;
}
.task-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.12); }
.task-num {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #999;
    margin-bottom: 0.3rem;
}
.task-icon { font-size: 2.4rem; margin-bottom: 0.5rem; }
.task-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1E1E1E;
    margin-bottom: 0.6rem;
}
.task-desc {
    font-size: 0.9rem;
    color: #555;
    line-height: 1.55;
    margin-bottom: 1rem;
}
.pill {
    display: inline-block;
    background: #F0F4F8;
    color: #4A90D9;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 600;
    margin: 2px 2px 0 0;
}
.divider { border: none; border-top: 1.5px solid #E0E7EF; margin: 2rem 0; }
.footer {
    text-align: center;
    color: #aaa;
    font-size: 0.82rem;
    padding: 1.5rem 0 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div style="font-size:3.5rem; margin-bottom:0.4rem;">📊</div>
  <h1>Big Data Homework 1</h1>
  <div class="subtitle">
    <b>Tal Klein</b> &nbsp;·&nbsp; Student ID: <i>[YOUR_ID]</i>
  </div>
  <div class="meta">
    The Art of Analyzing Big Data: The Data Scientist's Toolbox
    &nbsp;·&nbsp; Dr. Michael Fire
  </div>
  <br/>
  <span class="badge">SQLite</span>
  <span class="badge">SQLAlchemy</span>
  <span class="badge">Streamlit</span>
  <span class="badge">Plotly</span>
  <span class="badge">pandas</span>
  <span class="badge">nba_api</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

st.markdown(
    "<h3 style='text-align:center; color:#333; margin-bottom:1.5rem;'>🚀 Choose a Task</h3>",
    unsafe_allow_html=True
)

# ── Task cards ───────────────────────────────────────────────────────────────
TASKS = [
    {
        "num": "Task 1",
        "icon": "👶",
        "title": "Baby Names Explorer",
        "desc": (
            "Explore 5.6 million US baby name records stored in SQLite. "
            "Track name popularity over time, run custom SQL queries, "
            "and discover data-driven insights about naming trends."
        ),
        "pills": ["SQLite", "5.6M rows", "Interactive charts"],
        "color": "#4A90D9",
        "page": "pages/1_Baby_Names.py",
    },
    {
        "num": "Task 2",
        "icon": "🎬",
        "title": "Oscar Actor Explorer",
        "desc": (
            "Browse Oscar Award nominations modeled with SQLAlchemy ORM. "
            "Look up any actor's career profile, Wikipedia bio, win stats, "
            "and discover who waited longest for their first Oscar."
        ),
        "pills": ["SQLAlchemy ORM", "Wikipedia API", "Actor profiles"],
        "color": "#E8A838",
        "page": "pages/2_Oscar.py",
    },
    {
        "num": "Task 3",
        "icon": "⚔️",
        "title": "Pokémon Battle Arena",
        "desc": (
            "Build your team and battle! Type advantages, speed-based turn "
            "order, and a full battle log are all powered by SQLite queries. "
            "Includes cheat codes and post-game Pokémon analysis."
        ),
        "pills": ["SQLite", "Battle mechanics", "Cheat codes"],
        "color": "#E53935",
        "page": "pages/3_Pokemon.py",
    },
    {
        "num": "Task 4 ⭐ Bonus",
        "icon": "🏀",
        "title": "NBA SQL Trivia",
        "desc": (
            "Test your SQL skills with real NBA data across 5 progressive "
            "levels — from basic SELECT to complex JOINs. Randomized "
            "questions, live timer, leaderboard podium, and a practice court."
        ),
        "pills": ["nba_api", "5 levels", "Leaderboard", "Real-time timer"],
        "color": "#F57C00",
        "page": "pages/4_NBA_Trivia.py",
    },
]

cols = st.columns(4, gap="medium")
for col, task in zip(cols, TASKS):
    with col:
        pills_html = "".join(f'<span class="pill">{p}</span>' for p in task["pills"])
        st.markdown(f"""
<div class="task-card">
  <div class="task-num">{task["num"]}</div>
  <div class="task-icon">{task["icon"]}</div>
  <div class="task-title">{task["title"]}</div>
  <div class="task-desc">{task["desc"]}</div>
  <div>{pills_html}</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.page_link(task["page"], label=f"Open {task['icon']} {task['title']}", use_container_width=True)

# ── About section ─────────────────────────────────────────────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)

with st.expander("📖 About this assignment"):
    st.markdown("""
This is **Homework Assignment 1** for the course
*"The Art of Analyzing Big Data: The Data Scientist's Toolbox"* — Dr. Michael Fire.

The assignment covers 4 tasks (25 pts each, 100 pts total + 5 pts bonus):

| Task | Topic | Key Technologies |
|------|-------|-----------------|
| 1 | Baby Names Explorer | SQLite, pandas, Plotly |
| 2 | Oscar Actor Explorer | SQLAlchemy ORM, Wikipedia REST API |
| 3 | Pokémon Battle Arena | SQLite, battle mechanics |
| 4 ⭐ | NBA SQL Trivia *(Bonus)* | nba_api, SQLite, interactive game |

All databases are built automatically on first run from local CSV files or APIs — no manual setup required.
""")

st.markdown(
    '<div class="footer">Tal Klein · Big Data HW1 · Built with Streamlit</div>',
    unsafe_allow_html=True
)
