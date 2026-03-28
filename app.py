"""Landing page - Big Data HW1 - Tal Klein."""
import streamlit as st

st.set_page_config(
    page_title="The Art of Analyzing Big Data HW1 - Tal Klein",
    page_icon="",
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
    max-width: 860px !important;
    margin: 0 auto !important;
    padding: 2rem 1.8rem 2.5rem !important;
}

/* ---- animated background ---- */
.hw1-page-bg {
    position: fixed;
    inset: 0;
    z-index: -1;
    background: linear-gradient(135deg, #f0f4ff 0%, #e8eeff 25%, #f5f0ff 50%, #eef6ff 75%, #f0f4ff 100%);
    background-size: 400% 400%;
    animation: bgShift 12s ease infinite;
}
@keyframes bgShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* ---- hero ---- */
.hw1-hero {
    text-align: center;
    padding: 2.4rem 2rem 2rem;
    background: rgba(255,255,255,0.82);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(200,210,230,0.5);
    border-radius: 20px;
    margin-bottom: 1.6rem;
    box-shadow: 0 8px 32px rgba(30,60,120,0.08);
}
.hw1-hero-icon {
    width: 64px;
    height: 64px;
    border-radius: 18px;
    display: inline-grid;
    place-items: center;
    font-size: 2rem;
    background: linear-gradient(145deg, #1c6fc2, #6366F1);
    color: #fff;
    box-shadow: 0 8px 24px rgba(99,102,241,0.3);
    margin-bottom: 0.8rem;
}
.hw1-hero h1 {
    font-size: 1.65rem;
    line-height: 1.3;
    font-weight: 800;
    color: #1a1a2e;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.02em;
}
.hw1-hero .sub {
    font-size: 0.95rem;
    color: #4f5d75;
    margin-top: 0.15rem;
    font-weight: 500;
}
.hw1-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.75rem;
    justify-content: center;
}
.hw1-badge {
    display: inline-block;
    background: linear-gradient(135deg, #EEF2FF, #E0E7FF);
    color: #4338CA;
    border: 1px solid #C7D2FE;
    border-radius: 999px;
    padding: 0.2rem 0.7rem;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}

/* ---- section title ---- */
.hw1-section-title {
    text-align: center;
    font-size: 1.1rem;
    font-weight: 700;
    color: #374151;
    margin: 0 0 1.2rem;
    letter-spacing: 0.01em;
}

/* ---- card grid ---- */
.hw1-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    margin-bottom: 1.2rem;
}
.hw1-card {
    display: flex;
    flex-direction: column;
    background: rgba(255,255,255,0.88);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(200,210,230,0.45);
    border-radius: 16px;
    padding: 1.2rem 1.1rem 1rem;
    text-decoration: none;
    color: inherit;
    cursor: pointer;
    transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
    position: relative;
    overflow: hidden;
}
.hw1-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: var(--accent, #4a90d9);
    border-radius: 16px 16px 0 0;
    opacity: 0.7;
    transition: opacity 0.2s;
}
.hw1-card:hover::before { opacity: 1; }
.hw1-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(14,35,64,0.13), 0 0 0 1px var(--accent, #4a90d9);
    border-color: transparent;
    text-decoration: none;
    color: inherit;
}
.hw1-card-header {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin-bottom: 0.6rem;
}
.hw1-card-icon-wrap {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    font-size: 1.5rem;
    background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 12%, white), color-mix(in srgb, var(--accent) 6%, white));
    border: 1px solid color-mix(in srgb, var(--accent) 20%, white);
    flex-shrink: 0;
}
.hw1-card-label {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: var(--accent, #4a90d9);
    margin-bottom: 0.1rem;
}
.hw1-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1a1a2e;
    line-height: 1.2;
}
.hw1-card-desc {
    font-size: 0.82rem;
    color: #5a6577;
    line-height: 1.45;
    margin-bottom: 0.6rem;
    flex: 1;
}
.hw1-card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: auto;
}
.hw1-card-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
}
.hw1-tag {
    background: color-mix(in srgb, var(--accent) 8%, white);
    color: var(--accent, #4a90d9);
    border: 1px solid color-mix(in srgb, var(--accent) 18%, white);
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 0.66rem;
    font-weight: 700;
    white-space: nowrap;
}
.hw1-card-arrow {
    font-size: 1.1rem;
    color: var(--accent, #4a90d9);
    opacity: 0;
    transform: translateX(-4px);
    transition: opacity 0.2s, transform 0.2s;
    font-weight: 700;
}
.hw1-card:hover .hw1-card-arrow {
    opacity: 1;
    transform: translateX(0);
}

/* ---- footer ---- */
.hw1-footer {
    text-align: center;
    color: #9CA3AF;
    font-size: 0.76rem;
    padding: 0.8rem 0 0;
    border-top: 1px solid #E5E7EB;
    margin-top: 0.4rem;
}

@media (max-width: 700px) {
    .block-container { padding: 1rem 0.75rem 1.5rem !important; }
    .hw1-hero { padding: 1.5rem 1rem; }
    .hw1-hero h1 { font-size: 1.3rem; }
    .hw1-grid { grid-template-columns: 1fr; }
}
</style>
""",
    unsafe_allow_html=True,
)

# Animated background
st.markdown('<div class="hw1-page-bg"></div>', unsafe_allow_html=True)

st.markdown(
    """
<div class="hw1-hero">
  <div class="hw1-hero-icon">&#128202;</div>
  <h1>The Art of Analyzing Big Data</h1>
  <div class="sub">Homework 1 &mdash; Tal Klein &middot; 209234103 &middot; Dr. Michael Fire</div>
  <div class="hw1-badges">
    <span class="hw1-badge">SQLite</span>
    <span class="hw1-badge">SQLAlchemy</span>
    <span class="hw1-badge">Streamlit</span>
    <span class="hw1-badge">Plotly</span>
    <span class="hw1-badge">pandas</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="hw1-section-title">Choose a Task</div>', unsafe_allow_html=True)

TASKS = [
    {
        "label": "Task 1",
        "icon": "&#128118;",
        "title": "Baby Names Explorer",
        "desc": "5.6 M baby-name rows in SQLite with trend charts, a safe custom SQL panel, and pattern discovery.",
        "tags": ["SQLite", "5.6M rows", "Plotly Charts"],
        "accent": "#4A90D9",
        "url": "/Baby_Names",
    },
    {
        "label": "Task 2",
        "icon": "&#127916;",
        "title": "Oscar Actor Explorer",
        "desc": "SQLAlchemy ORM actor profiles enriched with live Wikipedia data, win stats, and discoveries.",
        "tags": ["SQLAlchemy ORM", "Wiki API", "Profiles"],
        "accent": "#E8A838",
        "url": "/Oscar",
    },
    {
        "label": "Task 3",
        "icon": "&#9876;&#65039;",
        "title": "Pokemon Battle Arena",
        "desc": "Data-driven team battles with type effectiveness, speed turns, cheat-code SQL writes, and audit logs.",
        "tags": ["SQLite", "Battle Engine", "Cheat Audit"],
        "accent": "#E53935",
        "url": "/Pokemon",
    },
    {
        "label": "Task 4 &mdash; Bonus",
        "icon": "&#128163;",
        "title": "SQL Minesweeper",
        "desc": "Classic Minesweeper where hitting a mine triggers an NBA SQL rescue challenge. Difficulty escalates each hit.",
        "tags": ["Minesweeper", "SQL Challenges", "NBA Data"],
        "accent": "#388E3C",
        "url": "/Minesweeper",
    },
]

cards_html = '<div class="hw1-grid">'
for task in TASKS:
    tags_html = "".join(f'<span class="hw1-tag">{tag}</span>' for tag in task["tags"])
    cards_html += f"""
<a class="hw1-card" href="{task['url']}" target="_self" style="--accent:{task['accent']}">
  <div class="hw1-card-header">
    <div class="hw1-card-icon-wrap">{task['icon']}</div>
    <div>
      <div class="hw1-card-label">{task['label']}</div>
      <div class="hw1-card-title">{task['title']}</div>
    </div>
  </div>
  <div class="hw1-card-desc">{task['desc']}</div>
  <div class="hw1-card-footer">
    <div class="hw1-card-tags">{tags_html}</div>
    <div class="hw1-card-arrow">&rarr;</div>
  </div>
</a>"""
cards_html += "</div>"

st.markdown(cards_html, unsafe_allow_html=True)
st.markdown(
    '<div class="hw1-footer">Tal Klein &middot; The Art of Analyzing Big Data &middot; Homework 1 &middot; Built with Streamlit</div>',
    unsafe_allow_html=True,
)
