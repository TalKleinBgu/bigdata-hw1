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
    background: linear-gradient(135deg, #2f4768 0%, #496b94 60%, #6f91b8 100%);
    border-radius: 14px;
    padding: 0.56rem 1.1rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: 0.2rem;
    box-shadow: 0 2px 10px rgba(29, 51, 80, 0.18);
}
.hw1-nav a {
    color: rgba(255,255,255,0.84) !important;
    text-decoration: none !important;
    font-size: 0.86rem;
    font-weight: 500;
    padding: 0.34rem 0.78rem;
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
    font-size: 0.89rem;
    background: rgba(255,255,255,0.16);
    padding: 0.34rem 0.88rem;
    border-radius: 9px;
    white-space: nowrap;
    border: 1px solid rgba(255,255,255,0.20);
}
.hw1-nav .hw1-sep { color: rgba(255,255,255,0.32); margin: 0 0.12rem; font-size: 1.0rem; }
.hw1-nav .hw1-spacer { flex: 1; }
</style>
<nav class="hw1-nav">
  <a href="/" target="_self">&#127968; Home</a>
  <span class="hw1-sep">|</span>
  <span class="hw1-active">&#127936; Task 4</span>
  <div class="hw1-spacer"></div>
  <a href="/Baby_Names" target="_self">&#128118; Task 1 - Baby Names</a>
  <a href="/Oscar" target="_self">&#127916; Task 2</a>
  <a href="/Pokemon" target="_self">&#9876;&#65039; Task 3</a>
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
