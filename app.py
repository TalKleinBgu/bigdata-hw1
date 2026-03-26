"""Landing page — Big Data HW1 · Tal Klein"""
import streamlit as st

st.set_page_config(
    page_title="Big Data HW1 — Tal Klein",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stSidebarNav"]   { display: none; }
[data-testid="stSidebar"]      { display: none; }
#MainMenu, footer, header      { visibility: hidden; }

/* ── reset streamlit padding ── */
.block-container { padding: 2rem 3rem 3rem !important; max-width: 1200px; }

/* ── hero ── */
.hw1-hero {
    text-align: center;
    padding: 2.8rem 1rem 1.8rem;
    background: linear-gradient(135deg, #f8faff 0%, #eef3fb 100%);
    border-radius: 20px;
    margin-bottom: 2.2rem;
    border: 1px solid #dde8f5;
}
.hw1-hero h1 {
    font-size: 2.8rem; font-weight: 800;
    background: linear-gradient(90deg, #1a5fa8, #4A90D9);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}
.hw1-hero .sub { font-size: 1.1rem; color: #444; margin-bottom: 0.25rem; }
.hw1-hero .meta { font-size: 0.9rem; color: #888; }
.hw1-badge {
    display: inline-block; background: #4A90D9; color: white;
    border-radius: 20px; padding: 3px 13px; font-size: 0.8rem;
    font-weight: 600; margin: 3px 2px;
}

/* ── section title ── */
.hw1-section-title {
    text-align: center; font-size: 1.4rem; font-weight: 700;
    color: #222; margin: 0 0 1.4rem;
    display: flex; align-items: center; justify-content: center; gap: 8px;
}

/* ── cards grid ── */
.hw1-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.4rem;
    margin-bottom: 2.5rem;
}

/* ── single card as full <a> ── */
.hw1-card {
    display: flex; flex-direction: column;
    background: #fff;
    border: 2px solid #e8edf5;
    border-radius: 18px;
    padding: 1.7rem 1.4rem 1.4rem;
    text-decoration: none;
    color: inherit;
    cursor: pointer;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    position: relative;
    overflow: hidden;
}
.hw1-card::before {               /* coloured top bar */
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 5px;
    background: var(--accent, #4A90D9);
    border-radius: 18px 18px 0 0;
}
.hw1-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 14px 36px rgba(0,0,0,0.13);
    border-color: var(--accent, #4A90D9);
    text-decoration: none;
    color: inherit;
}
.hw1-card-label {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 1.2px;
    text-transform: uppercase; color: var(--accent, #4A90D9);
    margin-bottom: 0.6rem;
}
.hw1-card-icon  { font-size: 2.6rem; margin-bottom: 0.5rem; }
.hw1-card-title { font-size: 1.15rem; font-weight: 700; color: #1a1a1a; margin-bottom: 0.6rem; }
.hw1-card-desc  { font-size: 0.87rem; color: #555; line-height: 1.6; flex: 1; }
.hw1-card-tags  { margin-top: 1rem; }
.hw1-tag {
    display: inline-block; background: #f2f5fb;
    color: var(--accent, #4A90D9);
    border-radius: 10px; padding: 4px 14px;
    font-size: 0.76rem; font-weight: 600; margin: 3px 3px 0 0;
}
.hw1-card-arrow {
    margin-top: 1.1rem; text-align: right;
    font-size: 1.1rem; color: var(--accent, #4A90D9);
    opacity: 0; transition: opacity 0.18s;
}
.hw1-card:hover .hw1-card-arrow { opacity: 1; }

/* ── about expander ── */
.hw1-divider { border: none; border-top: 1.5px solid #e8edf5; margin: 0.5rem 0 1.8rem; }
.hw1-footer  { text-align: center; color: #bbb; font-size: 0.8rem; padding: 1.2rem 0 0; }
</style>
""", unsafe_allow_html=True)

# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hw1-hero">
  <div style="font-size:3.2rem; margin-bottom:0.5rem;">📊</div>
  <h1>Big Data Homework 1</h1>
  <div class="sub"><b>Tal Klein</b> &nbsp;·&nbsp; Student ID: <i>209234103</i></div>
  <div class="meta">
    The Art of Analyzing Big Data: The Data Scientist's Toolbox &nbsp;·&nbsp; Dr. Michael Fire
  </div>
  <div style="margin-top:1rem;">
    <span class="hw1-badge">SQLite</span>
    <span class="hw1-badge">SQLAlchemy</span>
    <span class="hw1-badge">Streamlit</span>
    <span class="hw1-badge">Plotly</span>
    <span class="hw1-badge">pandas</span>
    <span class="hw1-badge">nba_api</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Task grid (single HTML block → CSS Grid → equal heights) ─────────────────
st.markdown('<div class="hw1-section-title">🚀 Choose a Task</div>', unsafe_allow_html=True)

TASKS = [
    {
        "label": "Task 1",
        "icon": "👶",
        "title": "Baby Names Explorer",
        "desc": "Explore 5.6 million US baby name records in SQLite. Track popularity over time, run custom SQL, and uncover data-driven insights about naming trends across decades and states.",
        "tags": ["SQLite", "5.6M rows", "Charts"],
        "accent": "#4A90D9",
        "url": "/Baby_Names",
    },
    {
        "label": "Task 2",
        "icon": "🎬",
        "title": "Oscar Actor Explorer",
        "desc": "Browse Oscar nominations modeled with SQLAlchemy ORM. Get actor profiles with Wikipedia photos, win statistics, and discover who waited longest for their first Academy Award.",
        "tags": ["SQLAlchemy ORM", "Wikipedia API", "Profiles"],
        "accent": "#E8A838",
        "url": "/Oscar",
    },
    {
        "label": "Task 3",
        "icon": "⚔️",
        "title": "Pokémon Battle Arena",
        "desc": "Build your team and battle! Type advantages, speed-based turn order, and attack damage are all powered by SQLite queries. Includes cheat codes and post-game Pokémon analysis.",
        "tags": ["SQLite", "Battle logic", "Cheats"],
        "accent": "#E53935",
        "url": "/Pokemon",
    },
    {
        "label": "Task 4 ⭐ Bonus",
        "icon": "🏀",
        "title": "NBA SQL Trivia",
        "desc": "Test your SQL skills with real NBA data across 5 progressive levels — SELECT to JOINs. Randomized questions, live timer, hint system, and a leaderboard podium for top players.",
        "tags": ["nba_api", "5 levels", "Leaderboard"],
        "accent": "#F57C00",
        "url": "/NBA_Trivia",
    },
]

cards_html = '<div class="hw1-grid">'
for t in TASKS:
    tags_html = "".join(f'<span class="hw1-tag">{tag}</span>' for tag in t["tags"])
    cards_html += f"""
<a class="hw1-card" href="{t['url']}" target="_self" style="--accent:{t['accent']}">
  <div class="hw1-card-label">{t['label']}</div>
  <div class="hw1-card-icon">{t['icon']}</div>
  <div class="hw1-card-title">{t['title']}</div>
  <div class="hw1-card-desc">{t['desc']}</div>
  <div class="hw1-card-tags">{tags_html}</div>
  <div class="hw1-card-arrow">→</div>
</a>"""
cards_html += '</div>'

st.markdown(cards_html, unsafe_allow_html=True)

st.markdown(
    '<div class="hw1-footer">Tal Klein · Big Data HW1 · Built with Streamlit</div>',
    unsafe_allow_html=True,
)
