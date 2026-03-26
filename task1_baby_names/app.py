"""
Baby Names Explorer — Big Data Homework 1, Task 1
===================================================
A Streamlit app that explores US baby name trends using SSA data stored in SQLite.
"""

import os
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


@st.cache_data(show_spinner="Running query…")
def cached_query(sql: str, _conn) -> pd.DataFrame:
    """Cache-backed version for heavy/example queries."""
    return pd.read_sql_query(sql, _conn)


def ensure_extra_indexes(conn: sqlite3.Connection) -> None:
    """Add a Name-only index if it doesn't exist (speeds up GROUP BY Name)."""
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_name ON national_names (Name)"
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

st.title("Baby Names Explorer")
st.caption("Exploring US baby-name trends by state from the Social Security Administration (1910 -- present)")

# Ensure DB exists and indexes are up to date
conn = get_connection()
ensure_extra_indexes(conn)

# ---------------------------------------------------------------------------
# Sidebar — Schema & Index Info  (Task 1.1)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Database Schema")
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

    st.subheader("Indexes")

    st.markdown("**1. `idx_name_year` on (Name, Year)**")
    st.markdown(
        "Speeds up the most common query pattern: looking up a specific "
        "name's popularity across years. Used by the Name Popularity chart."
    )

    st.markdown("**2. `idx_year_gender` on (Year, Gender)**")
    st.markdown(
        "Speeds up aggregate queries that group by year and gender, such as "
        "computing total births per year (needed for percentage calculations) "
        "and yearly statistics."
    )

    st.markdown("**3. `idx_state` on (State)**")
    st.markdown(
        "Speeds up queries filtering or grouping by state, enabling "
        "efficient regional analysis of naming trends."
    )

    st.divider()
    row_count = run_query("SELECT COUNT(*) AS n FROM national_names", conn).iloc[0, 0]
    year_range = run_query("SELECT MIN(Year) AS lo, MAX(Year) AS hi FROM national_names", conn)
    st.metric("Total rows", f"{row_count:,}")
    st.metric("Year range", f"{year_range.iloc[0, 0]} -- {year_range.iloc[0, 1]}")

# ---------------------------------------------------------------------------
# Main content — organized with tabs
# ---------------------------------------------------------------------------
tab_explore, tab_sql, tab_diversity, tab_patterns = st.tabs(
    [
        "Name Popularity",
        "Custom SQL",
        "Name Diversity",
        "Pattern Discovery",
    ]
)

# ===== TAB A: Name Popularity Over Time ====================================
with tab_explore:
    st.header("A. Name Popularity Over Time")
    st.markdown("Enter one or more names (comma-separated) to see how their popularity changed across the years.")

    col_input, col_mode = st.columns([3, 1])
    with col_input:
        name_input = st.text_input(
            "Names",
            value="",
            placeholder="e.g. David, Sarah, Michael",
            help="Comma-separated list of names (case-insensitive)",
        )
    with col_mode:
        mode = st.radio("Metric", ["Raw Count", "Percentage"], horizontal=True)

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
            fig = px.line(
                df,
                x="Year",
                y="Value",
                color="Name",
                labels={"Value": y_label, "Year": "Year"},
                title=f"Name Popularity ({mode})",
            )
            fig.update_layout(hovermode="x unified", template="plotly_white",
                                dragmode=False,
                                xaxis=dict(showspikes=True, spikemode="across", spikethickness=1),
                                yaxis=dict(showspikes=True, spikemode="across", spikethickness=1, showgrid=False))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Type at least one name above to see the chart.")

# ===== TAB B: Custom SQL Query Panel =======================================
with tab_sql:
    st.header("B. Custom SQL Query Panel")
    st.markdown(
        "Run any **SELECT** query against the `national_names` table. "
        "Non-SELECT statements are blocked for safety."
    )

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
    st.header("C. Name Diversity Over Time")
    st.markdown(
        "How many **unique names** were registered each year, and what is the "
        "**average count per name**? A rising unique-name count signals increasing "
        "naming diversity."
    )

    diversity_sql = """
        SELECT Year,
               COUNT(DISTINCT Name) AS UniqueNames,
               ROUND(AVG(Count), 2)  AS AvgCountPerName
        FROM national_names
        GROUP BY Year
        ORDER BY Year
    """
    div_df = run_query(diversity_sql, conn)

    fig_div = go.Figure()
    fig_div.add_trace(
        go.Scatter(
            x=div_df["Year"], y=div_df["UniqueNames"],
            name="Unique Names", mode="lines",
            line=dict(color="#4A90D9", width=2),
        )
    )
    fig_div.add_trace(
        go.Scatter(
            x=div_df["Year"], y=div_df["AvgCountPerName"],
            name="Avg Count per Name", mode="lines",
            yaxis="y2",
            line=dict(color="#E8636E", width=2, dash="dot"),
        )
    )
    fig_div.update_layout(
        title="Name Diversity Over Time",
        xaxis_title="Year",
        yaxis=dict(title=dict(text="Unique Names", font=dict(color="#4A90D9"))),
        yaxis2=dict(
            title=dict(text="Avg Count per Name", font=dict(color="#E8636E")),
            overlaying="y",
            side="right",
        ),
        template="plotly_white",
        hovermode="x unified",
        dragmode=False,
        xaxis=dict(showspikes=True, spikemode="across", spikethickness=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig_div, use_container_width=True)

# ===== TAB D: Pattern Discovery (Task 1.3) =================================
with tab_patterns:
    st.header("Pattern Discovery")
    st.markdown("Three interesting patterns uncovered from the data, each supported by a SQL query, a chart, and an interpretation.")

    # --- Pattern 1: Name Diversity Explosion --------------------------------
    st.subheader("1. Name Diversity Explosion Since the 1950s")

    p1_sql = """
        SELECT Year,
               COUNT(DISTINCT Name) AS UniqueNames
        FROM national_names
        GROUP BY Year
        ORDER BY Year;
    """
    p1_df = run_query(p1_sql, conn)

    fig_p1 = px.line(
        p1_df, x="Year", y="UniqueNames",
        title="Number of Unique Baby Names per Year",
        labels={"UniqueNames": "Unique Names"},
    )
    # Add a vertical reference line at 1950
    fig_p1.add_vline(x=1950, line_dash="dash", line_color="red", annotation_text="1950")
    fig_p1.update_layout(template="plotly_white", dragmode=False, hovermode="x unified",
                          xaxis=dict(showspikes=True, spikemode="across", spikethickness=1),
                          yaxis=dict(showspikes=True, spikemode="across", spikethickness=1, showgrid=False))
    st.plotly_chart(fig_p1, use_container_width=True)
    with st.expander("Show SQL query"):
        st.code(p1_sql, language="sql")
    st.markdown("**Finding:** Name diversity increased sharply after the mid-20th century, with far more unique names used per year than in earlier decades.")

    st.markdown(
        """
        **Interpretation:** The data shows a clear long-term rise in naming diversity.
        Unique names increase from about **1,693 (1910)** to **3,595 (1950)**, then to
        **4,689 (1970)**, **8,699 (2000)**, and **9,585 (2014)**. The increase is not a
        short spike but a sustained expansion over decades, consistent with parents
        using a broader and more varied set of names over time.
        """
    )

    st.divider()

    # --- Pattern 2: Celebrity / Pop-Culture Influence -----------------------
    st.subheader("2. Pop-Culture Influence: The \"Arya\" Effect")

    p2_sql = """
        SELECT Year, SUM(Count) AS Total
        FROM national_names
        WHERE Name = 'Arya'
        GROUP BY Year
        ORDER BY Year;
    """
    p2_df = run_query(p2_sql, conn)

    fig_p2 = px.bar(
        p2_df, x="Year", y="Total",
        title='Popularity of the Name "Arya" Over Time',
        labels={"Total": "Births"},
        color_discrete_sequence=["#7B68EE"],
    )
    fig_p2.add_vline(x=2011, line_dash="dash", line_color="red",
                     annotation_text="GoT S1 (2011)")
    fig_p2.update_layout(template="plotly_white", dragmode=False, hovermode="x unified",
                          xaxis=dict(showspikes=True, spikemode="across", spikethickness=1),
                          yaxis=dict(showspikes=True, spikemode="across", spikethickness=1, showgrid=False))
    st.plotly_chart(fig_p2, use_container_width=True)
    with st.expander("Show SQL query"):
        st.code(p2_sql, language="sql")
    st.markdown("**Finding:** The name *Arya* surged after 2011, indicating a strong pop-culture effect on naming choices.")

    st.markdown(
        """
        **Interpretation:** In this dataset, *Arya* is nearly absent for many years
        (first appears at **5 births in 1982**) and then rises sharply around the early
        2010s (**249 in 2010**, **422 in 2011**), reaching a peak of **1,574 in 2014**.
        This timing supports a strong pop-culture effect, where media exposure can
        rapidly increase adoption of a previously uncommon name.
        """
    )

    st.divider()

    # --- Pattern 3: Regional Naming — The State Divide ----------------------
    st.subheader("3. Regional Naming: The State Divide")

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
    p3_top_df = run_query(p3_top_sql, conn)
    if not p3_top_df.empty:
        st.markdown("**Most popular name per state (all available years):**")
        st.dataframe(p3_top_df, use_container_width=True)

        topname_states_df = (
            p3_top_df.groupby("TopName", as_index=False)["State"]
            .count()
            .rename(columns={"State": "NumStates"})
            .sort_values(["NumStates", "TopName"], ascending=[False, True])
        )
        fig_p3_topname_states = px.bar(
            topname_states_df.head(20),
            x="TopName",
            y="NumStates",
            title="How Many States Each Top Name Dominates",
            labels={"TopName": "Top Name", "NumStates": "Number of States"},
            color="NumStates",
            color_continuous_scale="Blues",
        )
        fig_p3_topname_states.update_layout(
            template="plotly_white",
            dragmode=False,
            hovermode="x unified",
            xaxis=dict(showspikes=True, spikemode="across", spikethickness=1),
            yaxis=dict(showspikes=True, spikemode="across", spikethickness=1, showgrid=False),
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

    p3c_df = run_query(p3c_sql, conn)
    if not p3c_df.empty:
        fig_p3 = px.line(
            p3c_df, x="Year", y="Total", color="State",
            title='Regional Popularity of "Jose" Across States',
            labels={"Total": "Births"},
        )
        fig_p3.update_layout(template="plotly_white", dragmode=False, hovermode="x unified",
                              xaxis=dict(showspikes=True, spikemode="across", spikethickness=1),
                              yaxis=dict(showspikes=True, spikemode="across", spikethickness=1, showgrid=False))
        st.plotly_chart(fig_p3, use_container_width=True)
        with st.expander("Show SQL query"):
            st.code(p3c_sql, language="sql")
    st.markdown("**Finding:** Name popularity is strongly regional, and the same name can be dominant in some states while uncommon in others.")

    st.markdown(
        """
        **Interpretation:** Name popularity varies dramatically by state, reflecting
        regional demographics and cultural influences. In the all-years top-name
        results, only a few names dominate many states (for example, **Robert: 16
        states**, **James: 14**, **John: 10**, **Michael: 10**), while *Jose* shows strong
        concentration in specific states rather than uniform popularity
        (**2014: TX 1,540; CA 1,318; NY 196; FL 300; MT 5 in its latest year, 2004**).
        This indicates that U.S. naming is a regional mosaic, not a single national
        pattern.
        """
    )
