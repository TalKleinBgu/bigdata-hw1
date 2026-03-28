"""
Baby Names Explorer - Big Data Homework 1, Task 1
===================================================
A Streamlit app that explores US baby name trends using SSA data stored in SQLite.
"""

import os
import re
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent
DB_PATH = DATA_DIR / "baby_names.db"
CSV_PATH = DATA_DIR / "StateNames.csv"

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def build_db_from_csv() -> None:
    """Build the SQLite DB from the local StateNames.csv file."""
    df = pd.read_csv(str(CSV_PATH))
    # Keep only the columns we need, rename to match our schema
    df = df[["Name", "Year", "Gender", "State", "Count"]].copy()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS national_names")
    cur.execute("""
        CREATE TABLE national_names (
            Id     INTEGER PRIMARY KEY AUTOINCREMENT,
            Name   TEXT    NOT NULL,
            Year   INTEGER NOT NULL,
            Gender TEXT    NOT NULL,
            State  TEXT    NOT NULL,
            Count  INTEGER NOT NULL
        )
    """)

    # Use pandas to_sql for fast bulk insert (much faster than iterrows)
    df.to_sql("national_names", conn, if_exists="append", index=False)

    # --- Indexes ---
    cur.execute("CREATE INDEX idx_name_year ON national_names (Name, Year)")
    cur.execute("CREATE INDEX idx_year_gender ON national_names (Year, Gender)")
    cur.execute("CREATE INDEX idx_state ON national_names (State)")

    # Persist lightweight stats so schema tab can load instantly without full-table scan.
    cur.execute("CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    metadata_rows = [
        ("row_count", str(int(len(df)))),
        ("year_lo", str(int(df["Year"].min()))),
        ("year_hi", str(int(df["Year"].max()))),
    ]
    cur.executemany("INSERT OR REPLACE INTO app_metadata (key, value) VALUES (?, ?)", metadata_rows)

    conn.commit()
    conn.close()


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    """Return a cached SQLite connection, creating the DB if needed."""
    if not DB_PATH.exists():
        if not CSV_PATH.exists():
            raise FileNotFoundError(
                f"CSV file not found at {CSV_PATH}. "
                "Please place StateNames.csv in the task1_baby_names/ folder."
            )
        build_db_from_csv()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    return conn


def run_query(sql: str, conn: sqlite3.Connection) -> pd.DataFrame:
    """Execute a read-only SQL query and return a DataFrame."""
    return pd.read_sql_query(sql, conn)


@st.cache_data(show_spinner=False)
def cached_static_query(sql: str) -> pd.DataFrame:
    """Cache static analysis queries that do not depend on user input."""
    with sqlite3.connect(str(DB_PATH)) as _conn:
        return pd.read_sql_query(sql, _conn)


@st.cache_data(show_spinner=False)
def get_dataset_stats(_conn) -> dict:
    """Cached dataset-level stats used in multiple sections."""
    rows = _conn.execute("SELECT key, value FROM app_metadata WHERE key IN ('row_count', 'year_lo', 'year_hi')").fetchall()
    if len(rows) == 3:
        meta = {k: v for k, v in rows}
        return {
            "rows": int(meta["row_count"]),
            "year_lo": int(meta["year_lo"]),
            "year_hi": int(meta["year_hi"]),
        }

    # Fallback for old DB versions without metadata table.
    row = _conn.execute(
        "SELECT COUNT(*) AS n, MIN(Year) AS lo, MAX(Year) AS hi FROM national_names"
    ).fetchone()
    return {"rows": int(row[0]), "year_lo": int(row[1]), "year_hi": int(row[2])}


@st.cache_data(show_spinner="Running query...")
def cached_query(sql: str, _conn) -> pd.DataFrame:
    """Cache-backed version for heavy/example queries."""
    return pd.read_sql_query(sql, _conn)


def ensure_extra_indexes(conn: sqlite3.Connection) -> None:
    """Ensure extra read-optimized indexes used by heavy analysis queries."""
    conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON national_names (Name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_year_name ON national_names (Year, Name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_state_name ON national_names (State, Name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_name_state_year ON national_names (Name, State, Year)")
    conn.execute("CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    needed = conn.execute(
        "SELECT COUNT(*) FROM app_metadata WHERE key IN ('row_count', 'year_lo', 'year_hi')"
    ).fetchone()[0]
    if needed < 3:
        row = conn.execute(
            "SELECT COUNT(*) AS n, MIN(Year) AS lo, MAX(Year) AS hi FROM national_names"
        ).fetchone()
        conn.executemany(
            "INSERT OR REPLACE INTO app_metadata (key, value) VALUES (?, ?)",
            [
                ("row_count", str(int(row[0]))),
                ("year_lo", str(int(row[1]))),
                ("year_hi", str(int(row[2]))),
            ],
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Baby Names Explorer",
    page_icon="\U0001F476",
    layout="wide",
)

st.markdown("""
<div class="sticky-page-header">
  <div class="sticky-page-title">Baby Names Explorer</div>
  <div class="sticky-page-subtitle">US baby-name trends from the Social Security Administration, 1910 to present</div>
</div>
""", unsafe_allow_html=True)

# Ensure DB exists and indexes are up to date
conn = get_connection()
ensure_extra_indexes(conn)

# Sidebar - stats only  (Task 1.1)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
.block-container { padding: 1rem 2rem 2.5rem !important; max-width: 1100px !important; margin: 0 auto !important; }
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
.main .block-container { text-align: center; }
h1, h2, h3, h4, h5, h6, p, label, li { text-align: center; }
[data-testid="stHorizontalBlock"] { justify-content: center; }
div[data-testid="stTabs"] [data-baseweb="tab-list"] { justify-content: center; }
div[data-testid="stTabs"] [data-baseweb="tab"] { margin: 0 0.15rem; }
div.stButton > button { display: block; margin-left: auto; margin-right: auto; }
div[data-testid="stTextInput"], div[data-testid="stTextArea"], div[data-testid="stSelectbox"], div[data-testid="stRadio"] { margin-left: auto; margin-right: auto; }
div[data-testid="stTextInput"] label, div[data-testid="stRadio"] label { width: 100%; text-align: center; }
div[data-testid="stTextInput"] input { text-align: center; }
div[data-testid="stRadio"] [role="radiogroup"] { justify-content: center; }
section[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem !important; }
[data-testid="stSidebarContent"] { padding-top: 0.5rem !important; }
/* Uniform section styling */
.section-header { font-size: 1.15rem; font-weight: 600; color: #1F2937; margin: 1.5rem 0 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid #E5E7EB; }
.section-desc { font-size: 0.88rem; color: #6B7280; margin-bottom: 1rem; line-height: 1.5; }
.insight-box { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px; padding: 0.9rem 1.1rem; margin: 0.75rem 0; font-size: 0.85rem; color: #374151; line-height: 1.6; text-align: left; }
.insight-box b, .insight-box strong { color: #111827; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div style="font-size:0.95rem;font-weight:600;color:#1F2937;margin-bottom:0.5rem;">About</div>', unsafe_allow_html=True)
    st.markdown(
        "This app loads the [US Baby Names dataset]"
        "(https://www.kaggle.com/datasets/kaggle/us-baby-names) "
        "into **SQLite** and provides interactive tools for popularity trends, "
        "safe custom SQL queries, and pattern discovery."
    )
# ---------------------------------------------------------------------------
# Main content - organized with tabs
# ---------------------------------------------------------------------------
tab_explore, tab_sql, tab_diversity, tab_patterns, tab_schema = st.tabs(
    ["Name Popularity", "Custom SQL", "Name Diversity", "Pattern Discovery", "Schema"]
)

# ===== TAB A: Name Popularity Over Time ====================================
with tab_explore:
    st.markdown('<div class="section-header">Name Popularity Over Time</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-desc">Enter one or more names (comma-separated) to see how their popularity changed across the years.</div>', unsafe_allow_html=True)

    outer_l, center_col, outer_r = st.columns([1, 4, 1])
    with center_col:
        name_input = st.text_input(
            "Names",
            value="",
            placeholder="e.g. David, Sarah, Michael",
            help="Comma-separated list of names (case-insensitive)",
        )
        show_percentage = st.toggle("Show Percentage", value=False)
        mode = "Percentage" if show_percentage else "Raw Count"

    names = [n.strip().capitalize() for n in name_input.split(",") if n.strip()]

    if names:
        placeholders = ",".join(["?"] * len(names))

        if mode == "Raw Count":
            sql = f"""
                SELECT Name, Year, SUM(Count) AS Value
                FROM national_names
                WHERE Name IN ({placeholders})
                GROUP BY Name, Year
                ORDER BY Year
            """
            y_label = "Births"
        else:
            sql = f"""
                SELECT n.Name, n.Year,
                       ROUND(100.0 * SUM(n.Count) / t.Total, 4) AS Value
                FROM national_names n
                JOIN (
                    SELECT Year, SUM(Count) AS Total
                    FROM national_names
                    GROUP BY Year
                ) t ON n.Year = t.Year
                WHERE n.Name IN ({placeholders})
                GROUP BY n.Name, n.Year
                ORDER BY n.Year
            """
            y_label = "% of All Births"

        df = pd.read_sql_query(sql, conn, params=names)

        if df.empty:
            st.warning("No data found for the entered names.")
        else:
            colors = px.colors.qualitative.Set2
            fig = go.Figure()
            for i, name in enumerate(df["Name"].unique()):
                name_df = df[df["Name"] == name]
                c = colors[i % len(colors)]
                # Build rgba fill color with low opacity
                rgb = px.colors.hex_to_colors_dict.get(c, c) if hasattr(px.colors, 'hex_to_colors_dict') else c
                _rgb_match = re.match(r'#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})', c)
                if _rgb_match:
                    _r, _g, _b = (int(_rgb_match.group(j), 16) for j in (1, 2, 3))
                    fill_c = f"rgba({_r},{_g},{_b},0.08)"
                else:
                    fill_c = "rgba(100,100,100,0.08)"
                fig.add_trace(go.Scatter(
                    x=name_df["Year"], y=name_df["Value"],
                    name=name, mode="lines",
                    line=dict(color=c, width=2.5, shape="spline"),
                    fill="tozeroy", fillcolor=fill_c,
                ))
            fig.update_layout(
                title=dict(text=f"<b>Name Popularity ({mode})</b>", font=dict(size=16)),
                hovermode="x unified",
                dragmode=False,
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showspikes=True, spikemode="across", spikethickness=1, title="Year"),
                yaxis=dict(showspikes=True, spikemode="across", spikethickness=1,
                           gridcolor="#E5E7EB", title=y_label),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Type at least one name above to see the chart.")

# ===== TAB B: Custom SQL Query Panel =======================================
with tab_sql:
    st.markdown('<div class="section-header">Custom SQL Query Panel</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-desc">Run any SELECT query against the national_names table. Non-SELECT statements are blocked for safety.</div>', unsafe_allow_html=True)

    # Pre-built example queries
    example_queries = {
        "Top 10 names in 2010": (
            "SELECT Name, SUM(Count) AS TotalCount\n"
            "FROM national_names\n"
            "WHERE Year = 2010\n"
            "GROUP BY Name\n"
            "ORDER BY TotalCount DESC\n"
            "LIMIT 10;"
        ),
        "Gender-neutral names": (
            "WITH totals AS (\n"
            "    SELECT Name,\n"
            "           SUM(CASE WHEN Gender='M' THEN Count ELSE 0 END) AS Male,\n"
            "           SUM(CASE WHEN Gender='F' THEN Count ELSE 0 END) AS Female\n"
            "    FROM national_names\n"
            "    GROUP BY Name\n"
            "), scored AS (\n"
            "    SELECT Name,\n"
            "           Male,\n"
            "           Female,\n"
            "           (Male + Female) AS Total,\n"
            "           ROUND(100.0 * Male / (Male + Female), 2) AS MalePct,\n"
            "           ROUND(100.0 * Female / (Male + Female), 2) AS FemalePct,\n"
            "           ROUND(ABS(100.0 * Male / (Male + Female) - 50.0), 2) AS GapFrom50\n"
            "    FROM totals\n"
            "    WHERE (Male + Female) >= 1000\n"
            ")\n"
            "SELECT Name, Male, Female, Total, MalePct, FemalePct, GapFrom50\n"
            "FROM scored\n"
            "ORDER BY GapFrom50 ASC, Total DESC\n"
            "LIMIT 20;"
        ),
        "Names that disappeared after 1980": (
            "SELECT Name, SUM(Count) AS PreCount\n"
            "FROM national_names n\n"
            "WHERE Year <= 1980\n"
            "GROUP BY Name\n"
            "HAVING PreCount > 5000\n"
            "   AND NOT EXISTS (\n"
            "       SELECT 1 FROM national_names WHERE Name = n.Name AND Year > 1980\n"
            "   )\n"
            "ORDER BY PreCount DESC\n"
            "LIMIT 15;"
        ),
    }

    # Use session state for the query text
    if "sql_area" not in st.session_state:
        st.session_state.sql_area = "SELECT * FROM national_names LIMIT 10;"
    if "auto_run_sql" not in st.session_state:
        st.session_state.auto_run_sql = False

    btn_cols = st.columns(len(example_queries))
    for idx, (label, query) in enumerate(example_queries.items()):
        with btn_cols[idx]:
            if st.button(label, use_container_width=True):
                st.session_state.sql_area = query
                st.session_state.auto_run_sql = True
                st.rerun()

    user_sql = st.text_area(
        "SQL Query",
        height=300,
        key="sql_area",
    )

    is_example = st.session_state.auto_run_sql
    should_run = st.button("Run Query", type="primary") or is_example
    st.session_state.auto_run_sql = False
    if should_run:
        stripped = user_sql.strip().rstrip(";").strip()
        first_word = stripped.split()[0].upper() if stripped.split() else ""
        if first_word not in ("SELECT", "WITH"):
            st.error(
                "**Only SELECT queries are allowed!** "
                "For safety, this panel blocks INSERT, UPDATE, DELETE, DROP, and other write operations. "
                "Please rewrite your query as a SELECT statement."
            )
        else:
            try:
                # Use cache for the heavy example queries; plain run_query for user queries
                result_df = cached_query(user_sql, conn) if is_example else run_query(user_sql, conn)
                st.success(f"Query returned {len(result_df):,} rows.")
                st.dataframe(result_df, use_container_width=True)

                # Auto-chart
                if len(result_df.columns) >= 2:
                    numeric_cols = result_df.select_dtypes(include="number").columns.tolist()
                    other_cols = [c for c in result_df.columns if c not in numeric_cols]

                    if numeric_cols and other_cols:
                        x_col = other_cols[0]
                        # Use second categorical column as color if present
                        color_col = other_cols[1] if len(other_cols) > 1 else None
                        plot_df = result_df.copy()

                        # For gender queries, calculate % only from Male/Female.
                        pct_cols = numeric_cols.copy()
                        pct_label = "Percentage (%)"
                        if "Male" in plot_df.columns and "Female" in plot_df.columns:
                            pct_cols = ["Male", "Female"]
                            pct_label = "Percentage (%) of Male + Female"

                        # Show percentages when multiple numeric columns are charted.
                        use_pct = len(pct_cols) > 1
                        if use_pct:
                            row_total = plot_df[pct_cols].sum(axis=1).replace(0, 1)
                            for c in pct_cols:
                                plot_df[c] = (plot_df[c] / row_total * 100).round(2)

                        # Decide chart type: line if x looks like years, else bar
                        is_time = (
                            pd.api.types.is_numeric_dtype(plot_df[x_col])
                            and plot_df[x_col].between(1800, 2100).all()
                        )
                        y_label = pct_label if use_pct else "Count"
                        title = "Query Result (line chart)" if is_time else "Query Result (bar chart)"
                        y_col = pct_cols[0] if (color_col and len(pct_cols) == 1) else pct_cols

                        if is_time:
                            chart = px.line(plot_df, x=x_col, y=y_col,
                                            color=color_col, title=title)
                        else:
                            barmode = "stack" if (use_pct and len(pct_cols) > 1) else "group"
                            chart = px.bar(plot_df, x=x_col, y=y_col,
                                           color=color_col, title=title, barmode=barmode)

                        chart.update_layout(
                            template="plotly_white", dragmode=False,
                            hovermode="x unified", yaxis_title=y_label,
                            xaxis=dict(showspikes=True, spikemode="across", spikethickness=1),
                            yaxis=dict(showspikes=True, spikemode="across", spikethickness=1, showgrid=False),
                        )
                        st.plotly_chart(chart, use_container_width=True)
            except Exception as exc:
                st.error(f"Query error: {exc}")

# ===== TAB C: Name Diversity Over Time =====================================
with tab_diversity:
    st.markdown('<div class="section-header">Name Diversity Over Time</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-desc">How many unique names were registered each year, and what is the average count per name? A rising unique-name count signals increasing naming diversity.</div>', unsafe_allow_html=True)

    diversity_sql = """
        SELECT Year,
               COUNT(DISTINCT Name) AS UniqueNames,
               ROUND(AVG(Count), 2)  AS AvgCountPerName
        FROM national_names
        GROUP BY Year
        ORDER BY Year
    """
    div_df = cached_static_query(diversity_sql)

    fig_div = go.Figure()
    fig_div.add_trace(
        go.Scatter(
            x=div_df["Year"], y=div_df["UniqueNames"],
            name="Unique Names", mode="lines",
            line=dict(color="#4A90D9", width=2.5, shape="spline"),
            fill="tozeroy", fillcolor="rgba(74,144,217,0.1)",
        )
    )
    fig_div.add_trace(
        go.Scatter(
            x=div_df["Year"], y=div_df["AvgCountPerName"],
            name="Avg Count per Name", mode="lines",
            yaxis="y2",
            line=dict(color="#E8636E", width=2.5, dash="dot", shape="spline"),
        )
    )
    fig_div.update_layout(
        title=dict(text="<b>Name Diversity Over Time</b>", font=dict(size=16)),
        xaxis_title="Year",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title=dict(text="Unique Names", font=dict(color="#4A90D9")),
                   gridcolor="#E5E7EB", tickfont=dict(color="#4A90D9")),
        yaxis2=dict(
            title=dict(text="Avg Count per Name", font=dict(color="#E8636E")),
            overlaying="y",
            side="right",
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(color="#E8636E"),
        ),
        hovermode="x unified",
        dragmode=False,
        xaxis=dict(showspikes=True, spikemode="across", spikethickness=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig_div, use_container_width=True)

# ===== TAB D: Pattern Discovery (Task 1.3) =================================
with tab_patterns:
    st.markdown('<div class="section-header">Pattern Discovery</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-desc">Three interesting patterns uncovered from the data, each supported by a SQL query, a chart, and an interpretation.</div>', unsafe_allow_html=True)

    # --- Pattern 1: Name Diversity Explosion --------------------------------
    st.markdown('<div class="section-header">1. Name Diversity Explosion Since the 1950s</div>', unsafe_allow_html=True)

    p1_sql = """
        SELECT Year,
               COUNT(DISTINCT Name) AS UniqueNames
        FROM national_names
        GROUP BY Year
        ORDER BY Year;
    """
    p1_df = cached_static_query(p1_sql)

    fig_p1 = go.Figure()
    fig_p1.add_trace(go.Scatter(
        x=p1_df["Year"], y=p1_df["UniqueNames"],
        mode="lines", name="Unique Names",
        line=dict(color="#6366F1", width=2.5, shape="spline"),
        fill="tozeroy", fillcolor="rgba(99,102,241,0.1)",
    ))
    fig_p1.add_vline(
        x=1950, line_dash="dash", line_color="#EF4444", line_width=2,
        annotation=dict(text="<b>1950</b>", font=dict(size=13, color="#EF4444"),
                        showarrow=True, arrowhead=2, arrowcolor="#EF4444"),
    )
    fig_p1.update_layout(
        title=dict(text="<b>Number of Unique Baby Names per Year</b>", font=dict(size=16)),
        plot_bgcolor="rgba(0,0,0,0)",
        dragmode=False, hovermode="x unified",
        xaxis=dict(showspikes=True, spikemode="across", spikethickness=1, title="Year"),
        yaxis=dict(showspikes=True, spikemode="across", spikethickness=1,
                   gridcolor="#E5E7EB", title="Unique Names"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig_p1, use_container_width=True)
    with st.expander("Show SQL query"):
        st.code(p1_sql, language="sql")
    st.markdown("""<div class="insight-box"><strong>Finding:</strong> Name diversity increased sharply after the mid-20th century, with far more unique names used per year than in earlier decades.</div>""", unsafe_allow_html=True)

    st.markdown("""<div class="insight-box"><strong>Interpretation:</strong> The data shows a clear long-term rise in naming diversity. Unique names increase from about <strong>1,693 (1910)</strong> to <strong>3,595 (1950)</strong>, then to <strong>4,689 (1970)</strong>, <strong>8,699 (2000)</strong>, and <strong>9,585 (2014)</strong>. The increase is not a short spike but a sustained expansion over decades, consistent with parents using a broader and more varied set of names over time.</div>""", unsafe_allow_html=True)

    st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)

    # --- Pattern 2: Celebrity / Pop-Culture Influence -----------------------
    st.markdown('<div class="section-header">2. Pop-Culture Influence: The "Arya" Effect</div>', unsafe_allow_html=True)

    p2_sql = """
        SELECT Year, SUM(Count) AS Total
        FROM national_names
        WHERE Name = 'Arya'
        GROUP BY Year
        ORDER BY Year;
    """
    p2_df = cached_static_query(p2_sql)

    fig_p2 = go.Figure()
    fig_p2.add_trace(go.Bar(
        x=p2_df["Year"], y=p2_df["Total"],
        name="Births",
        marker=dict(
            color=p2_df["Total"],
            colorscale="Purples",
            cornerradius=5,
            line=dict(width=0),
        ),
    ))
    fig_p2.add_vline(
        x=2011, line_dash="dash", line_color="#EF4444", line_width=2,
        annotation=dict(text="<b>GoT S1 (2011)</b>", font=dict(size=12, color="#EF4444"),
                        showarrow=True, arrowhead=2, arrowcolor="#EF4444"),
    )
    fig_p2.update_layout(
        title=dict(text='<b>Popularity of the Name "Arya" Over Time</b>', font=dict(size=16)),
        plot_bgcolor="rgba(0,0,0,0)",
        dragmode=False, hovermode="x unified",
        xaxis=dict(showspikes=True, spikemode="across", spikethickness=1, title="Year"),
        yaxis=dict(showspikes=True, spikemode="across", spikethickness=1,
                   gridcolor="#E5E7EB", title="Births"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig_p2, use_container_width=True)
    with st.expander("Show SQL query"):
        st.code(p2_sql, language="sql")
    st.markdown("""<div class="insight-box"><strong>Finding:</strong> The name <em>Arya</em> surged after 2011, indicating a strong pop-culture effect on naming choices.</div>""", unsafe_allow_html=True)

    st.markdown("""<div class="insight-box"><strong>Interpretation:</strong> In this dataset, <em>Arya</em> is nearly absent for many years (first appears at <strong>5 births in 1982</strong>) and then rises sharply around the early 2010s (<strong>249 in 2010</strong>, <strong>422 in 2011</strong>), reaching a peak of <strong>1,574 in 2014</strong>. This timing supports a strong pop-culture effect, where media exposure can rapidly increase adoption of a previously uncommon name.</div>""", unsafe_allow_html=True)

    st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)

    # --- Pattern 3: Regional Naming - The State Divide ----------------------
    st.markdown('<div class="section-header">3. Regional Naming: The State Divide</div>', unsafe_allow_html=True)

    # Show top name per state as a table
    p3_top_sql = """
        WITH ranked AS (
            SELECT State, Name, SUM(Count) AS Total,
                   ROW_NUMBER() OVER (PARTITION BY State ORDER BY SUM(Count) DESC) AS rn
            FROM national_names
            GROUP BY State, Name
        )
        SELECT State, Name AS TopName, Total
        FROM ranked
        WHERE rn = 1
        ORDER BY State;
    """
    p3_top_df = cached_static_query(p3_top_sql)
    if not p3_top_df.empty:
        st.markdown("**Most popular name per state (all available years):**")
        st.dataframe(p3_top_df, use_container_width=True)

        topname_states_df = (
            p3_top_df.groupby("TopName", as_index=False)["State"]
            .count()
            .rename(columns={"State": "NumStates"})
            .sort_values(["NumStates", "TopName"], ascending=[False, True])
        )
        _top20 = topname_states_df.head(20)
        fig_p3_topname_states = go.Figure()
        fig_p3_topname_states.add_trace(go.Bar(
            x=_top20["TopName"], y=_top20["NumStates"],
            text=_top20["NumStates"], textposition="outside",
            textfont=dict(size=12),
            marker=dict(
                color=_top20["NumStates"],
                colorscale="Blues",
                cornerradius=5,
                line=dict(width=0),
            ),
        ))
        fig_p3_topname_states.update_layout(
            title=dict(text="<b>How Many States Each Top Name Dominates</b>", font=dict(size=16)),
            plot_bgcolor="rgba(0,0,0,0)",
            dragmode=False,
            hovermode="x unified",
            xaxis=dict(showspikes=True, spikemode="across", spikethickness=1, title="Top Name"),
            yaxis=dict(showspikes=True, spikemode="across", spikethickness=1,
                       gridcolor="#E5E7EB", title="Number of States"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_p3_topname_states, use_container_width=True)
        with st.expander("Show SQL query"):
            st.code(p3_top_sql, language="sql")

    # Compare a name across selected states
    p3c_sql = """
        SELECT Year, State, SUM(Count) AS Total
        FROM national_names
        WHERE Name = 'Jose'
          AND State IN ('CA', 'TX', 'NY', 'FL', 'MT')
        GROUP BY Year, State
        ORDER BY Year;
    """

    p3c_df = cached_static_query(p3c_sql)
    if not p3c_df.empty:
        _state_colors = {"CA": "#3B82F6", "TX": "#EF4444", "NY": "#10B981", "FL": "#F59E0B", "MT": "#8B5CF6"}
        fig_p3 = go.Figure()
        for state in p3c_df["State"].unique():
            sdf = p3c_df[p3c_df["State"] == state]
            c = _state_colors.get(state, "#6B7280")
            _m = re.match(r'#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})', c)
            fill_c = f"rgba({int(_m.group(1),16)},{int(_m.group(2),16)},{int(_m.group(3),16)},0.07)" if _m else "rgba(100,100,100,0.07)"
            fig_p3.add_trace(go.Scatter(
                x=sdf["Year"], y=sdf["Total"],
                name=state, mode="lines",
                line=dict(color=c, width=2.5, shape="spline"),
                fill="tozeroy", fillcolor=fill_c,
            ))
        fig_p3.update_layout(
            title=dict(text='<b>Regional Popularity of "Jose" Across States</b>', font=dict(size=16)),
            plot_bgcolor="rgba(0,0,0,0)",
            dragmode=False, hovermode="x unified",
            xaxis=dict(showspikes=True, spikemode="across", spikethickness=1, title="Year"),
            yaxis=dict(showspikes=True, spikemode="across", spikethickness=1,
                       gridcolor="#E5E7EB", title="Births"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_p3, use_container_width=True)
        with st.expander("Show SQL query"):
            st.code(p3c_sql, language="sql")
    st.markdown("""<div class="insight-box"><strong>Finding:</strong> Name popularity is strongly regional, and the same name can be dominant in some states while uncommon in others.</div>""", unsafe_allow_html=True)

    st.markdown("""<div class="insight-box"><strong>Interpretation:</strong> Name popularity varies dramatically by state, reflecting regional demographics and cultural influences. In the all-years top-name results, only a few names dominate many states (for example, <strong>Robert: 16 states</strong>, <strong>James: 14</strong>, <strong>John: 10</strong>, <strong>Michael: 10</strong>), while <em>Jose</em> shows strong concentration in specific states rather than uniform popularity (<strong>2014: TX 1,540; CA 1,318; NY 196; FL 300; MT 5 in its latest year, 2004</strong>). This indicates that U.S. naming is a regional mosaic, not a single national pattern.</div>""", unsafe_allow_html=True)

# ===== TAB E: Schema =======================================================
with tab_schema:
    st.markdown('<div class="section-header">Database Schema</div>', unsafe_allow_html=True)
    st.code(
        """CREATE TABLE national_names (
    Id     INTEGER PRIMARY KEY AUTOINCREMENT,
    Name   TEXT    NOT NULL,
    Year   INTEGER NOT NULL,
    Gender TEXT    NOT NULL,
    State  TEXT    NOT NULL,
    Count  INTEGER NOT NULL
);""",
        language="sql",
    )
    st.markdown('<div class="section-header">Indexes</div>', unsafe_allow_html=True)
    st.markdown("- `idx_name_year` on (Name, Year) - speeds up name popularity lookups across years")
    st.markdown("- `idx_year_gender` on (Year, Gender) - speeds up aggregate queries by year and gender")
    st.markdown("- `idx_state` on (State) - speeds up regional filtering and grouping")
    st.markdown("- `idx_year_name` on (Year, Name) - speeds up top names per year and yearly ranking queries")
    st.markdown("- `idx_name_state_year` on (Name, State, Year) - speeds up state-by-state timeline comparisons")
    st.markdown('<div class="section-header">Why These Indexes</div>', unsafe_allow_html=True)
    st.markdown(
        "- `Name + Year` is used by Task 1.2A time-series queries (`WHERE Name IN (...) GROUP BY Name, Year`)."
    )
    st.markdown(
        "- `Year + Gender` supports aggregation queries by year/gender (for diversity and custom SQL examples)."
    )
    st.markdown(
        "- `State` and composite state/name indexes support regional analyses and state filtering in Task 1.3."
    )
    st.markdown('<div class="section-header">SQL Safety</div>', unsafe_allow_html=True)
    st.markdown(
        "The custom SQL panel accepts only `SELECT`/`WITH` queries. "
        "Write operations (`INSERT`, `UPDATE`, `DELETE`, `DROP`, etc.) are blocked with a friendly error."
    )
    st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)
    schema_stats = get_dataset_stats(conn)
    c1, c2 = st.columns(2)
    c1.metric("Total rows", f"{schema_stats['rows']:,}")
    c2.metric("Year range", f"{schema_stats['year_lo']} - {schema_stats['year_hi']}")

