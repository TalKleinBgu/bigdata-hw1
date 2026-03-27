"""Landing page - Big Data HW1 - Tal Klein."""
import streamlit as st

st.set_page_config(
    page_title="The Art of Analyzing Big Data HW1 - Tal Klein",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
[data-testid="stSidebarNav"]   { display: none; }
[data-testid="stSidebar"]      { display: none; }
#MainMenu, footer, header      { visibility: hidden; }

.block-container {
    padding: 1rem 1.8rem 1.2rem !important;
    max-width: 90vw;
}

.hw1-hero {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.95rem;
    align-items: center;
    padding: 0.95rem 1rem;
    background: linear-gradient(120deg, #f4f8ff 0%, #edf5ff 55%, #f8fbff 100%);
    border-radius: 16px;
    margin-bottom: 0.95rem;
    border: 1px solid #dbe6f5;
}
.hw1-hero-icon {
    width: 52px;
    height: 52px;
    border-radius: 14px;
    display: grid;
    place-items: center;
    font-size: 1.7rem;
    background: linear-gradient(145deg, #1c6fc2, #4a90d9);
    color: #fff;
    box-shadow: 0 6px 16px rgba(28, 111, 194, 0.28);
}
.hw1-hero h1 {
    font-size: 1.28rem;
    line-height: 1.25;
    font-weight: 800;
    color: #1c2f45;
    margin: 0;
}
.hw1-hero .sub {
    font-size: 0.9rem;
    color: #4f6278;
    margin-top: 0.1rem;
}
.hw1-hero .meta {
    font-size: 0.78rem;
    color: #66768b;
    margin-top: 0.15rem;
}
.hw1-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-top: 0.45rem;
}
.hw1-badge {
    display: inline-block;
    background: #e6f0fb;
    color: #2e5e8f;
    border: 1px solid #cddff1;
    border-radius: 999px;
    padding: 0.12rem 0.52rem;
    font-size: 0.68rem;
    font-weight: 700;
}

.hw1-section-title {
    text-align: center;
    font-size: 1rem;
    font-weight: 700;
    color: #2a3b52;
    margin: 0.1rem 0 0.85rem;
}

.hw1-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.8rem;
    margin-bottom: 0.6rem;
}
.hw1-card {
    display: flex;
    flex-direction: column;
    background: #fff;
    border: 1px solid #e0eaf5;
    border-radius: 14px;
    padding: 0.9rem 0.85rem 0.85rem;
    text-decoration: none;
    color: inherit;
    cursor: pointer;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    position: relative;
    overflow: hidden;
}
.hw1-card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 5px;
    background: var(--accent, #4a90d9);
    border-radius: 14px 14px 0 0;
}
.hw1-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 24px rgba(14, 35, 64, 0.12);
    border-color: var(--accent, #4a90d9);
    text-decoration: none;
    color: inherit;
}
.hw1-card-label {
    font-size: 0.64rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--accent, #4a90d9);
    margin-bottom: 0.2rem;
}
.hw1-card-icon {
    font-size: 1.56rem;
    margin-bottom: 0.24rem;
    line-height: 1;
}
.hw1-card-title {
    font-size: 0.98rem;
    font-weight: 700;
    color: #13253c;
    margin-bottom: 0.28rem;
    line-height: 1.25;
}
.hw1-card-desc {
    font-size: 0.77rem;
    color: #4c5c71;
    line-height: 1.3;
    min-height: 2.05rem;
    margin-bottom: 0.42rem;
}
.hw1-card-tags {
    margin-top: auto;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
}
.hw1-tag {
    background: #f2f7fc;
    color: var(--accent, #4a90d9);
    border: 1px solid #e4edf8;
    border-radius: 9px;
    padding: 2px 7px;
    font-size: 0.66rem;
    font-weight: 700;
    white-space: nowrap;
    flex-shrink: 0;
}
.hw1-card-arrow {
    margin-top: 0.28rem;
    text-align: right;
    font-size: 0.92rem;
    color: var(--accent, #4a90d9);
    opacity: 0.35;
    transition: opacity 0.18s;
}
.hw1-card:hover .hw1-card-arrow { opacity: 1; }

.hw1-footer {
    text-align: center;
    color: #9fb0c2;
    font-size: 0.74rem;
    padding: 0.3rem 0 0;
}

@media (max-width: 980px) {
  .hw1-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .block-container { padding: 0.65rem 0.75rem 1rem !important; }
  .hw1-hero { grid-template-columns: 1fr; text-align: center; gap: 0.55rem; }
  .hw1-hero-icon { margin: 0 auto; }
  .hw1-badges { justify-content: center; }
  .hw1-grid { grid-template-columns: 1fr; }
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hw1-hero">
  <div class="hw1-hero-icon">📊</div>
  <div>
    <h1>Homework 1 · The Art of Analyzing Big Data</h1>
    <div class="sub">Tal Klein · Student ID: 209234103 · Dr. Michael Fire</div>
    <div class="hw1-badges">
      <span class="hw1-badge">SQLite</span>
      <span class="hw1-badge">SQLAlchemy</span>
      <span class="hw1-badge">Streamlit</span>
      <span class="hw1-badge">Plotly</span>
      <span class="hw1-badge">pandas</span>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="hw1-section-title">Choose a Task</div>', unsafe_allow_html=True)

TASKS = [
    {
        "label": "Task 1",
        "icon": "👶",
        "title": "Baby Names Explorer",
        "desc": "5.6M baby-name rows in SQLite with trend charts, SQL panel, and pattern discovery.",
        "tags": ["SQLite", "5.6M rows", "Charts"],
        "accent": "#4A90D9",
        "url": "/Baby_Names",
    },
    {
        "label": "Task 2",
        "icon": "🎬",
        "title": "Oscar Actor Explorer",
        "desc": "SQLAlchemy ORM profiles with live Wikipedia enrichment, wins stats, and discoveries.",
        "tags": ["SQLAlchemy", "Wiki API", "Profiles"],
        "accent": "#E8A838",
        "url": "/Oscar",
    },
    {
        "label": "Task 3",
        "icon": "⚔️",
        "title": "Pokemon Battle Arena",
        "desc": "Data-driven team battle with type advantages, speed turns, cheat codes, and logs.",
        "tags": ["SQLite", "Battle logic", "Cheats"],
        "accent": "#E53935",
        "url": "/Pokemon",
    },
    {
        "label": "Task 4 - Bonus",
        "icon": "🏀",
        "title": "NBA SQL Trivia",
        "desc": "SQL learning game on NBA data with 5 levels, timer, hints, and leaderboard.",
        "tags": ["nba_api", "5 levels", "Leaderboard"],
        "accent": "#F57C00",
        "url": "/NBA_Trivia",
    },
    {
        "label": "Task 5 - Bonus",
        "icon": "💣",
        "title": "SQL Minesweeper",
        "desc": "Classic Minesweeper with a twist — defuse mines by solving NBA SQL queries. Difficulty escalates with every hit.",
        "tags": ["Minesweeper", "SQL", "NBA", "Game"],
        "accent": "#388E3C",
        "url": "/Minesweeper",
    },
]

cards_html = '<div class="hw1-grid">'
for task in TASKS:
    tags_html = "".join(f'<span class="hw1-tag">{tag}</span>' for tag in task["tags"])
    cards_html += f"""
<a class="hw1-card" href="{task['url']}" target="_self" style="--accent:{task['accent']}">
  <div class="hw1-card-label">{task['label']}</div>
  <div class="hw1-card-icon">{task['icon']}</div>
  <div class="hw1-card-title">{task['title']}</div>
  <div class="hw1-card-desc">{task['desc']}</div>
  <div class="hw1-card-tags">{tags_html}</div>
  <div class="hw1-card-arrow">→</div>
</a>"""
cards_html += "</div>"

st.markdown(cards_html, unsafe_allow_html=True)
st.markdown(
    '<div class="hw1-footer">Tal Klein · The Art of Analyzing Big Data HW1 · Built with Streamlit</div>',
    unsafe_allow_html=True,
)
