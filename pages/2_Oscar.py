import os
import runpy
import sys

import streamlit as st

st.set_page_config(page_title="Oscar Explorer - HW1", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
<style>
[data-testid="stSidebarNav"] { display: none; }
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
.block-container { max-width: 90vw !important; padding: 1rem 1.8rem 1.2rem !important; }
.hw1-nav {
    background: linear-gradient(135deg, #425a78 0%, #55759c 55%, #6f8eb4 100%);
    border: 1px solid rgba(255,255,255,0.26);
    border-radius: 14px;
    padding: 0.62rem 1.1rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: 0.22rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.15), 0 2px 10px rgba(26, 45, 70, 0.14);
}
.hw1-nav a {
    color: rgba(255,255,255,0.86) !important;
    text-decoration: none !important;
    font-size: 0.84rem;
    font-weight: 500;
    padding: 0.36rem 0.8rem;
    border-radius: 9px;
    transition: background 0.15s, color 0.15s;
    white-space: nowrap;
}
.hw1-nav a:hover {
    background: rgba(255,255,255,0.14);
    color: #fff !important;
    text-decoration: none !important;
}
.hw1-nav .hw1-active {
    color: #fff !important;
    font-weight: 700;
    font-size: 0.86rem;
    background: rgba(255,255,255,0.18);
    padding: 0.36rem 0.9rem;
    border-radius: 9px;
    white-space: nowrap;
    border: 1px solid rgba(255,255,255,0.24);
}
.hw1-nav .hw1-sep { color: rgba(255,255,255,0.34); margin: 0 0.12rem; font-size: 1.0rem; }
.hw1-nav .hw1-spacer { flex: 1; }
</style>
<nav class="hw1-nav">
  <a href="/" target="_self">&#127968; Home</a>
  <span class="hw1-sep">|</span>
  <span class="hw1-active">&#127916; Task 2 - Oscar Explorer</span>
  <div class="hw1-spacer"></div>
  <a href="/Baby_Names" target="_self">&#128118; Task 1 - Baby Names</a>
  <a href="/Pokemon" target="_self">&#9876;&#65039; Task 3 - Pokemon Arena</a>
  <a href="/NBA_Trivia" target="_self">&#127936; Task 4 - NBA SQL Trivia</a>
  <a href="/Minesweeper" target="_self">&#128163; Task 5 - SQL Minesweeper</a>
</nav>
""",
    unsafe_allow_html=True,
)

_task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "task2_oscar"))
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
