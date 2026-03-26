import os, sys, re
import streamlit as st

st.set_page_config(page_title="Pokémon Arena — HW1", page_icon="⚔️", layout="wide")

_NAV = """
<style>
[data-testid="stSidebarNav"] { display: none; }
.hw1-topnav {
    display: flex; align-items: center; gap: 0; margin-bottom: 1.2rem;
    background: #fff5f5; border: 1px solid #f5c0c0;
    border-radius: 12px; padding: 0.5rem 1rem; font-size: 0.88rem;
    flex-wrap: wrap;
}
.hw1-topnav a {
    color: #c0392b; text-decoration: none; font-weight: 600;
    padding: 3px 10px; border-radius: 8px; transition: background 0.15s;
}
.hw1-topnav a:hover { background: #fde0e0; }
.hw1-topnav .sep { color: #ccc; margin: 0 2px; }
.hw1-topnav .current { color: #333; font-weight: 700; padding: 3px 10px; }
</style>
<div class="hw1-topnav">
  <a href="/" target="_self">🏠 Home</a>
  <span class="sep">›</span>
  <span class="current">⚔️ Task 3 — Pokémon Arena</span>
  <span class="sep" style="margin-left:auto"></span>
  <a href="/Baby_Names" target="_self">Task 1 👶</a>
  <span class="sep">·</span>
  <a href="/Oscar" target="_self">Task 2 🎬</a>
  <span class="sep">·</span>
  <a href="/NBA_Trivia" target="_self">Task 4 🏀</a>
</div>
"""
st.markdown(_NAV, unsafe_allow_html=True)

_task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'task3_pokemon'))
_app_file = os.path.join(_task_dir, 'app.py')
os.chdir(_task_dir)
if _task_dir not in sys.path:
    sys.path.insert(0, _task_dir)

_src = open(_app_file, encoding='utf-8').read()
_src = re.sub(r'st\.set_page_config\s*\((?:[^)(]|\([^)(]*\))*\)', 'pass', _src, count=1)
exec(_src, {'__file__': _app_file, '__name__': '__main__'})
