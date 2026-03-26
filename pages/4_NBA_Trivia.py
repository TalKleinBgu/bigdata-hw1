import os, sys, re
import streamlit as st

st.set_page_config(page_title="NBA SQL Trivia — HW1", page_icon="🏀", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebarNav"] { display: none; }
div[data-testid="stHorizontalBlock"]:first-of-type {
    background: #fff8f0;
    border: 1px solid #f5d0a0;
    border-radius: 12px;
    padding: 4px 8px;
    margin-bottom: 1rem;
    align-items: center;
}
</style>
""", unsafe_allow_html=True)

c0, c1, csep, c2, c3, c4 = st.columns([0.7, 2.2, 0.1, 0.85, 0.85, 0.85])
with c0:
    st.page_link("app.py", label="🏠 Home")
with c1:
    st.markdown("<span style='font-weight:700; color:#333; font-size:0.9rem;'>🏀 Task 4 — NBA SQL Trivia</span>", unsafe_allow_html=True)
with c2:
    st.page_link("pages/1_Baby_Names.py", label="👶 Task 1")
with c3:
    st.page_link("pages/2_Oscar.py", label="🎬 Task 2")
with c4:
    st.page_link("pages/3_Pokemon.py", label="⚔️ Task 3")

_task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'task4_sql_game'))
_app_file = os.path.join(_task_dir, 'app.py')
os.chdir(_task_dir)
if _task_dir not in sys.path:
    sys.path.insert(0, _task_dir)

_src = open(_app_file, encoding='utf-8').read()
_src = re.sub(r'st\.set_page_config\s*\((?:[^)(]|\([^)(]*\))*\)', 'pass', _src, count=1)
exec(_src, {'__file__': _app_file, '__name__': '__main__'})
