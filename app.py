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
    padding: 1rem 2rem 2.5rem !important;
    max-width: 900px !important;
    margin: 0 auto !important;
}

/* ---- page header (same as task pages) ---- */
.sticky-page-header {
    position: sticky; top: 0; z-index: 1000;
    background: rgba(255,255,255,0.97);
    border-bottom: 2px solid #E5E7EB;
    padding: 1rem 1.5rem;
    margin: 0 -2rem 1.5rem -2rem;
    text-align: center;
}
.sticky-page-title { font-size: 1.5rem; font-weight: 700; color: #111827; line-height: 1.3; }
.sticky-page-subtitle { font-size: 0.9rem; color: #6B7280; margin-top: 0.25rem; font-weight: 400; }

/* ---- badges ---- */
.hw1-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.6rem;
    justify-content: center;
}
.hw1-badge {
    display: inline-block;
    background: #F3F4F6;
    color: #4338CA;
    border: 1px solid #E5E7EB;
    border-radius: 999px;
    padding: 0.2rem 0.7rem;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

/* ---- section title ---- */
.section-header {
    font-size: 1.15rem; font-weight: 600; color: #1F2937;
    margin: 1.5rem 0 0.75rem; padding-bottom: 0.5rem;
    border-bottom: 1px solid #E5E7EB;
    text-align: center;
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
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
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
    height: 3px;
    background: var(--accent, #4a90d9);
    border-radius: 12px 12px 0 0;
    opacity: 0.6;
    transition: opacity 0.2s;
}
.hw1-card:hover::before { opacity: 1; }
.hw1-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(14,35,64,0.1);
    border-color: var(--accent, #4a90d9);
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
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: grid;
    place-items: center;
    font-size: 1.35rem;
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
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
    color: #1F2937;
    line-height: 1.2;
}
.hw1-card-desc {
    font-size: 0.82rem;
    color: #6B7280;
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
    background: #F9FAFB;
    color: var(--accent, #4a90d9);
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 0.66rem;
    font-weight: 600;
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
    .hw1-grid { grid-template-columns: 1fr; }
}
</style>
""",
    unsafe_allow_html=True,
)

# Page header - same pattern as task pages
st.markdown(
    """
<div class="sticky-page-header">
  <div class="sticky-page-title">The Art of Analyzing Big Data</div>
  <div class="sticky-page-subtitle">Homework 1 &mdash; Tal Klein &middot; 209234103 &middot; Dr. Michael Fire</div>
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

st.markdown('<div class="section-header">Choose a Task</div>', unsafe_allow_html=True)

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
