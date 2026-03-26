import os
import runpy
import sys

import streamlit as st

st.set_page_config(page_title="NBA SQL Trivia - HW1", page_icon="🏀", layout="wide")

st.markdown(
    """
<style>
[data-testid="stSidebarNav"] { display: none; }
.hw1-nav {
    background: linear-gradient(135deg, #0d2b5e 0%, #1a5fa8 60%, #4A90D9 100%);
    border-radius: 14px;
    padding: 0.6rem 1.2rem;
    margin-bottom: 1.4rem;
    display: flex;
    align-items: center;
    gap: 0.2rem;
    box-shadow: 0 4px 20px rgba(26,95,168,0.28);
}
.hw1-nav a {
    color: rgba(255,255,255,0.78) !important;
    text-decoration: none !important;
    font-size: 0.87rem;
    font-weight: 500;
    padding: 0.38rem 0.85rem;
    border-radius: 9px;
    transition: background 0.15s, color 0.15s;
    white-space: nowrap;
}
.hw1-nav a:hover {
    background: rgba(255,255,255,0.18);
    color: #fff !important;
    text-decoration: none !important;
}
.hw1-nav .hw1-active {
    color: #fff !important;
    font-weight: 700;
    font-size: 0.9rem;
    background: rgba(255,255,255,0.2);
    padding: 0.38rem 0.95rem;
    border-radius: 9px;
    white-space: nowrap;
    border: 1px solid rgba(255,255,255,0.25);
}
.hw1-nav .hw1-sep { color: rgba(255,255,255,0.22); margin: 0 0.15rem; font-size: 1.1rem; }
.hw1-nav .hw1-spacer { flex: 1; }
</style>
<nav class="hw1-nav">
  <a href="/" target="_self">&#127968; Home</a>
  <span class="hw1-sep">|</span>
  <a href="/Baby_Names" target="_self">&#128118; Task 1 - Baby Names</a>
  <div class="hw1-spacer"></div>
  <a href="/Oscar" target="_self">&#127916; Task 2</a>
  <a href="/Pokemon" target="_self">&#9876;&#65039; Task 3</a>
  <span class="hw1-active">&#127936; Task 4</span>
</nav>
""",
    unsafe_allow_html=True,
)

_task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "task4_sql_game"))
_app_file = os.path.join(_task_dir, "app.py")
os.chdir(_task_dir)
if _task_dir not in sys.path:
    sys.path.insert(0, _task_dir)

_orig_set_page_config = st.set_page_config
st.set_page_config = lambda *args, **kwargs: None
try:
    runpy.run_path(_app_file, run_name="__main__")
finally:
    st.set_page_config = _orig_set_page_config
