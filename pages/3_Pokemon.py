import os
import runpy
import sys

import streamlit as st

st.set_page_config(page_title="Pokemon Arena - HW1", page_icon="⚔️", layout="wide")

st.markdown(
    """
<style>
[data-testid="stSidebarNav"] { display: none; }
</style>
""",
    unsafe_allow_html=True,
)

c0, c1, csep, c2, c3, c4 = st.columns([0.7, 2.2, 0.1, 0.85, 0.85, 0.85])
with c0:
    st.page_link("app.py", label="🏠 Home")
with c1:
    st.markdown(
        "<span style='font-weight:700; color:#333; font-size:0.9rem;'>⚔️ Task 3 - Pokemon Arena</span>",
        unsafe_allow_html=True,
    )
with c2:
    st.page_link("pages/1_Baby_Names.py", label="👶 Task 1")
with c3:
    st.page_link("pages/2_Oscar.py", label="🎬 Task 2")
with c4:
    st.page_link("pages/4_NBA_Trivia.py", label="🏀 Task 4")

_task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "task3_pokemon"))
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
