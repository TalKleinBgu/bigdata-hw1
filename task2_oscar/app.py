"""
Oscar Actor Explorer ג€” Task 2
Big Data Homework 1

A Streamlit application that uses SQLAlchemy ORM to query an Oscar Award
dataset stored in SQLite and enriches actor profiles with live Wikipedia data.
"""

import difflib
import textwrap
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    create_engine,
    func,
    case,
    distinct,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "oscar.db"
CSV_PATH = BASE_DIR / "full_data.csv"

# ---------------------------------------------------------------------------
# Task 2.1 ג€” SQLAlchemy ORM Model
# ---------------------------------------------------------------------------
Base = declarative_base()


class Nomination(Base):
    """ORM model representing a single Oscar nomination row."""

    __tablename__ = "nominations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year_film = Column(Integer, index=True)
    year_ceremony = Column(Integer, index=True)
    ceremony = Column(Integer)
    category = Column(String, index=True)
    name = Column(String, index=True)
    film = Column(String)
    winner = Column(Boolean, default=False)

    def __repr__(self):
        tag = "W" if self.winner else "N"
        return f"<Nomination({self.year_ceremony} {self.category} | {self.name} - {self.film} [{tag}])>"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _load_csv() -> pd.DataFrame:
    """Load the Oscar CSV from the local full_data.csv file."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"CSV file not found at {CSV_PATH}. "
            "Please place full_data.csv in the task2_oscar/ folder and restart the app."
        )
    # full_data.csv is tab-separated
    df = pd.read_csv(CSV_PATH, sep="\t")
    # Normalise column names to what the app expects
    rename = {
        "Ceremony": "ceremony",
        "Year": "year_film",
        "Category": "category",
        "Film": "film",
        "Name": "name",
        "Winner": "winner",
    }
    df = df.rename(columns=rename)
    # year_film might be "1927/28" ג€” take the first 4 chars
    df["year_film"] = df["year_film"].astype(str).str[:4].astype(int)
    # Create year_ceremony from ceremony number + 1927
    df["year_ceremony"] = df["ceremony"].astype(int) + 1928
    # Winner: True/NaN ג†’ bool
    df["winner"] = df["winner"].fillna(False).astype(bool)
    # Keep only the columns we need
    df = df[["year_film", "year_ceremony", "ceremony", "category", "name", "film", "winner"]]
    df = df.dropna(subset=["name"])
    return df


def _init_db(engine):
    """Create tables and populate from CSV if the DB is empty."""
    Base.metadata.create_all(engine)
    session_cls = sessionmaker(bind=engine)
    session = session_cls()
    count = session.query(func.count(Nomination.id)).scalar()
    if count == 0:
        df = _load_csv()
        # Normalise column names to lower-case snake_case (in case of Kaggle format)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        records = []
        for _, row in df.iterrows():
            winner_val = row.get("winner", False)
            if isinstance(winner_val, str):
                winner_val = winner_val.strip().lower() in ("true", "1", "yes")
            records.append(
                Nomination(
                    year_film=int(row["year_film"]) if pd.notna(row.get("year_film")) else None,
                    year_ceremony=int(row["year_ceremony"]) if pd.notna(row.get("year_ceremony")) else None,
                    ceremony=int(row["ceremony"]) if pd.notna(row.get("ceremony")) else None,
                    category=str(row["category"]).strip() if pd.notna(row.get("category")) else None,
                    name=str(row["name"]).strip() if pd.notna(row.get("name")) else None,
                    film=str(row["film"]).strip() if pd.notna(row.get("film")) else None,
                    winner=bool(winner_val),
                )
            )
        session.bulk_save_objects(records)
        session.commit()
    session.close()


@st.cache_resource
def get_engine():
    """Return a cached SQLAlchemy engine and ensure DB is populated."""
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    _init_db(engine)
    return engine


def get_session() -> Session:
    """Return a new ORM session."""
    engine = get_engine()
    return sessionmaker(bind=engine)()


# ---------------------------------------------------------------------------
# All distinct names (cached for autocomplete)
# ---------------------------------------------------------------------------

# Categories for actors and directors only
PERSON_CATEGORIES_PATTERN = (
    "ACTOR%", "ACTRESS%", "DIRECTING%",
)


@st.cache_data(ttl=600)
def get_all_names() -> list[str]:
    """Return a sorted list of all distinct nominee names (people only, not studios/countries)."""
    session = get_session()
    from sqlalchemy import or_
    filters = [Nomination.category.like(pat) for pat in PERSON_CATEGORIES_PATTERN]
    names = [
        r[0] for r in session.query(distinct(Nomination.name))
        .filter(or_(*filters))
        .order_by(Nomination.name)
        .all()
        if r[0]
    ]
    session.close()
    return names


# ---------------------------------------------------------------------------
# Wikipedia helper
# ---------------------------------------------------------------------------

def fetch_wikipedia_info(name: str) -> dict:
    """Fetch summary, image, and birth date using the Wikipedia REST API."""
    import requests
    import re
    from urllib.parse import quote

    API = "https://en.wikipedia.org/api/rest_v1"
    HEADERS = {"User-Agent": "OscarExplorerApp/1.0"}
    info: dict = {"summary": None, "image": None, "birth_date": None, "page_url": None}

    try:
        # Step 1: Search for the page title via the Action API (search endpoint)
        search_resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "opensearch", "search": name, "limit": 3, "format": "json"},
            headers=HEADERS,
            timeout=8,
        )
        search_data = search_resp.json()
        titles = search_data[1] if len(search_data) > 1 else []
        if not titles:
            return info

        api_title = titles[0].replace(" ", "_")
        info["page_url"] = f"https://en.wikipedia.org/wiki/{quote(api_title)}"

        # Step 2: Get summary via REST API /page/summary/{title}
        try:
            resp = requests.get(
                f"{API}/page/summary/{quote(api_title)}",
                headers=HEADERS,
                timeout=8,
            )
            if resp.status_code == 200:
                data = resp.json()
                info["summary"] = data.get("extract")
                # The summary endpoint also provides a thumbnail
                thumb = data.get("thumbnail", {})
                if thumb.get("source"):
                    info["image"] = thumb["source"]
        except Exception:
            pass

        # Step 3: If no image from summary, try /page/media-list/{title}
        if not info["image"]:
            try:
                resp = requests.get(
                    f"{API}/page/media-list/{quote(api_title)}",
                    headers=HEADERS,
                    timeout=8,
                )
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    for item in items:
                        if item.get("type") == "image":
                            src = item.get("original", {}).get("source", "")
                            lower = src.lower()
                            if any(lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
                                if not any(skip in lower for skip in ("logo", "icon", "symbol", "flag", "replace")):
                                    info["image"] = src
                                    break
            except Exception:
                pass

        # Step 4: Get birth date from page HTML
        try:
            resp = requests.get(
                f"{API}/page/html/{quote(api_title)}",
                headers=HEADERS,
                timeout=8,
            )
            if resp.status_code == 200:
                birth_match = re.search(r'class="bday">(\d{4}-\d{2}-\d{2})<', resp.text)
                if birth_match:
                    info["birth_date"] = birth_match.group(1)
        except Exception:
            pass

    except Exception:
        pass
    return info


# ---------------------------------------------------------------------------
# ORM query helpers
# ---------------------------------------------------------------------------

def query_person_profile(session: Session, name: str) -> dict:
    """Query the DB for a person's complete Oscar profile."""
    noms = (
        session.query(Nomination)
        .filter(Nomination.name == name)
        .order_by(Nomination.year_ceremony)
        .all()
    )
    if not noms:
        return {}
    wins = [n for n in noms if n.winner]
    categories = sorted({n.category for n in noms})
    years = [n.year_ceremony for n in noms if n.year_ceremony]
    first_year = min(years) if years else None
    last_year = max(years) if years else None

    win_years = [n.year_ceremony for n in wins if n.year_ceremony]
    first_win_year = min(win_years) if win_years else None
    nom_years = [n.year_ceremony for n in noms if n.year_ceremony]
    first_nom_year = min(nom_years) if nom_years else None

    years_to_first_win = None
    if first_win_year and first_nom_year:
        years_to_first_win = first_win_year - first_nom_year

    return {
        "name": name,
        "nominations": noms,
        "num_nominations": len(noms),
        "num_wins": len(wins),
        "categories": categories,
        "first_year": first_year,
        "last_year": last_year,
        "win_rate": len(wins) / len(noms) * 100 if noms else 0,
        "years_to_first_win": years_to_first_win,
    }


def compute_category_percentile(session: Session, name: str, category: str) -> float | None:
    """Compute what percentage of nominees in *category* have fewer nominations than *name*."""
    # Count of nominations per person in this category
    sub = (
        session.query(
            Nomination.name,
            func.count(Nomination.id).label("cnt"),
        )
        .filter(Nomination.category == category)
        .group_by(Nomination.name)
        .subquery()
    )
    person_count = (
        session.query(sub.c.cnt).filter(sub.c.name == name).scalar()
    )
    if person_count is None:
        return None
    total = session.query(func.count()).select_from(sub).scalar()
    below = session.query(func.count()).select_from(sub).filter(sub.c.cnt < person_count).scalar()
    if total == 0:
        return None
    return below / total * 100


# ---------------------------------------------------------------------------
# Discovery queries (Task 2.3)
# ---------------------------------------------------------------------------

def _actor_director_filter():
    """Return an OR filter that restricts to acting/directing categories."""
    from sqlalchemy import or_
    return or_(*[Nomination.category.like(pat) for pat in PERSON_CATEGORIES_PATTERN])


def discovery_most_nominated_no_win(session: Session, top_n: int = 15):
    """Actors/directors with the most nominations but zero wins."""
    sub = (
        session.query(
            Nomination.name,
            func.count(Nomination.id).label("total_noms"),
            func.sum(case((Nomination.winner == True, 1), else_=0)).label("total_wins"),
        )
        .filter(_actor_director_filter())
        .group_by(Nomination.name)
        .subquery()
    )
    results = (
        session.query(sub.c.name, sub.c.total_noms)
        .filter(sub.c.total_wins == 0)
        .order_by(sub.c.total_noms.desc())
        .limit(top_n)
        .all()
    )
    return results


def discovery_longest_wait_for_win(session: Session, top_n: int = 15):
    """Actors/directors with the longest gap between first nomination and first win."""
    cat_filter = _actor_director_filter()
    first_nom = (
        session.query(
            Nomination.name,
            func.min(Nomination.year_ceremony).label("first_nom_year"),
        )
        .filter(cat_filter)
        .group_by(Nomination.name)
        .subquery()
    )
    first_win = (
        session.query(
            Nomination.name,
            func.min(Nomination.year_ceremony).label("first_win_year"),
        )
        .filter(Nomination.winner == True)
        .filter(_actor_director_filter())
        .group_by(Nomination.name)
        .subquery()
    )
    results = (
        session.query(
            first_nom.c.name,
            first_nom.c.first_nom_year,
            first_win.c.first_win_year,
            (first_win.c.first_win_year - first_nom.c.first_nom_year).label("wait_years"),
        )
        .join(first_win, first_nom.c.name == first_win.c.name)
        .filter((first_win.c.first_win_year - first_nom.c.first_nom_year) > 0)
        .order_by((first_win.c.first_win_year - first_nom.c.first_nom_year).desc())
        .limit(top_n)
        .all()
    )
    return results


def discovery_multi_category(session: Session, top_n: int = 15):
    """Actors/directors nominated in the most different acting/directing categories."""
    results = (
        session.query(
            Nomination.name,
            func.count(distinct(Nomination.category)).label("num_categories"),
            func.count(Nomination.id).label("total_noms"),
        )
        .filter(_actor_director_filter())
        .group_by(Nomination.name)
        .having(func.count(distinct(Nomination.category)) > 1)
        .order_by(func.count(distinct(Nomination.category)).desc(), func.count(Nomination.id).desc())
        .limit(top_n)
        .all()
    )
    return results


# ---------------------------------------------------------------------------
# Did-You-Know fun-fact generator
# ---------------------------------------------------------------------------

def generate_fun_facts(session: Session, profile: dict, wiki_info: dict) -> list[str]:
    """Generate fun facts for the 'Did You Know?' section."""
    facts = []
    name = profile["name"]
    num_noms = profile["num_nominations"]

    # Fact 1: Percentile among all nominees
    total_nominees = session.query(func.count(distinct(Nomination.name))).scalar()
    sub_counts = (
        session.query(
            Nomination.name,
            func.count(Nomination.id).label("cnt"),
        )
        .group_by(Nomination.name)
        .subquery()
    )
    below = session.query(func.count()).select_from(sub_counts).filter(sub_counts.c.cnt < num_noms).scalar()
    pct = round(below / total_nominees * 100) if total_nominees else 0
    facts.append(f"{name} has more nominations than {pct}% of all Oscar-nominated individuals.")

    # Fact 2: Win % in primary category
    if profile["categories"]:
        cat = profile["categories"][0]
        cat_total = (
            session.query(func.count(distinct(Nomination.name)))
            .filter(Nomination.category == cat)
            .scalar()
        )
        cat_winners = (
            session.query(func.count(distinct(Nomination.name)))
            .filter(Nomination.category == cat, Nomination.winner == True)
            .scalar()
        )
        if cat_total:
            win_pct = round(cat_winners / cat_total * 100)
            facts.append(f"Only {win_pct}% of nominees in '{cat}' have ever won.")

    # Fact 3: Birth-date-based age at first nomination
    if wiki_info.get("birth_date") and profile.get("first_year"):
        try:
            birth_year = int(wiki_info["birth_date"][:4])
            age_at_first = profile["first_year"] - birth_year
            if 5 < age_at_first < 120:
                facts.append(
                    f"{name}'s first Oscar nomination came at approximately age {age_at_first}."
                )
        except (ValueError, TypeError):
            pass

    # Fact 4: Years to first win
    if profile["years_to_first_win"] is not None:
        if profile["years_to_first_win"] == 0:
            facts.append(f"{name} won on their very first nomination!")
        else:
            facts.append(
                f"{name} waited {profile['years_to_first_win']} years between "
                "first nomination and first win."
            )
    elif profile["num_wins"] == 0 and profile["first_year"] and profile["last_year"]:
        span = profile["last_year"] - profile["first_year"]
        if span > 0:
            facts.append(
                f"{name} has been nominated over a span of {span} years "
                "and is still awaiting a win."
            )

    return facts


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def fuzzy_suggestions(query: str, names: list[str], n: int = 8) -> list[str]:
    """Return close matches using difflib."""
    return difflib.get_close_matches(query, names, n=n, cutoff=0.4)


# ===========================================================================
# Streamlit UI
# ===========================================================================

def main():
    st.set_page_config(
        page_title="Oscar Actor Explorer",
        page_icon="\U0001F3AC",
        layout="wide",
    )

    st.title("\U0001F3AC Oscar Actor Explorer")
    st.caption("Explore Oscar nomination history, actor profiles, and interesting discoveries.")

    # Ensure DB is ready
    _ = get_engine()
    all_names = get_all_names()

    # ----- Sidebar -----
    st.markdown(“””
<style>
section[data-testid=”stSidebar”] > div:first-child { padding-top: 0.5rem !important; }
[data-testid=”stSidebarContent”] { padding-top: 0.5rem !important; }
</style>
“””, unsafe_allow_html=True)

    with st.sidebar:
        st.header(“About This App”)
        st.markdown(
            “This app loads the [Oscar Award dataset]”
            “(https://www.kaggle.com/datasets/unanimad/the-oscar-award) “
            “into a SQLite database via **SQLAlchemy ORM** and provides “
            “rich actor/director profiles enriched with live Wikipedia data.”
        )

    # ----- Tabs -----
    tab_profile, tab_discoveries, tab_schema = st.tabs(
        ["\U0001F464 Actor Profile (Task 2.2)", "\U0001F50D Discoveries (Task 2.3)", "\U0001F4CB Schema (Task 2.1)"]
    )

    # ===================================================================
    # Task 2.2 ג€” Actor Profile
    # ===================================================================
    with tab_profile:
        st.subheader("Search for an Actor or Director")

        # Autocomplete via selectbox with search
        selected_name = st.selectbox(
            "Type a name to search",
            options=[""] + all_names,
            index=0,
            placeholder="Start typing a name...",
        )

        # Alternative free-text search for fuzzy matching
        free_text = st.text_input(
            "Or type a partial / approximate name for fuzzy matching",
            value="",
            key="free_text_search",
        )

        target_name = selected_name
        if free_text and not selected_name:
            matches = fuzzy_suggestions(free_text, all_names)
            if matches:
                target_name = st.selectbox("Did you mean:", matches, key="fuzzy_select")
            else:
                st.warning(f"No close matches found for **{free_text}**. Try a different spelling.")
                target_name = ""

        if target_name:
            session = get_session()
            try:
                profile = query_person_profile(session, target_name)
                if not profile:
                    st.error(f"No Oscar data found for **{target_name}**.")
                    suggestions = fuzzy_suggestions(target_name, all_names, n=5)
                    if suggestions:
                        st.info("Suggestions: " + ", ".join(suggestions))
                else:
                    # --- Fetch Wikipedia info ---
                    with st.spinner("Fetching Wikipedia data..."):
                        wiki = fetch_wikipedia_info(target_name)

                    # --- Profile Card ---
                    col_img, col_info = st.columns([1, 3])

                    with col_img:
                        if wiki.get("image"):
                            st.image(wiki["image"], width=250, caption=target_name)
                        else:
                            st.markdown("*No photo available*")

                    with col_info:
                        st.markdown(f"## {target_name}")
                        if wiki.get("birth_date"):
                            st.markdown(f"**Born:** {wiki['birth_date']}")
                        if wiki.get("summary"):
                            st.markdown(wiki["summary"])
                        elif wiki.get("page_url"):
                            st.markdown(f"[Wikipedia page]({wiki['page_url']})")
                        else:
                            st.info("No Wikipedia info found for this person.")

                    st.divider()

                    # --- Oscar Stats ---
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Nominations", profile["num_nominations"])
                    m2.metric("Wins", profile["num_wins"] if profile["num_wins"] else "No wins yet")
                    m3.metric("Win Rate", f"{profile['win_rate']:.1f}%")
                    m4.metric(
                        "Years Active",
                        f"{profile['first_year']} - {profile['last_year']}"
                        if profile["first_year"]
                        else "N/A",
                    )

                    if profile["years_to_first_win"] is not None:
                        st.info(
                            f"Years between first nomination and first win: "
                            f"**{profile['years_to_first_win']}**"
                        )

                    # --- Category percentile comparison ---
                    if profile["categories"]:
                        primary_cat = profile["categories"][0]
                        pct = compute_category_percentile(session, target_name, primary_cat)
                        if pct is not None:
                            st.success(
                                f"{target_name} has more nominations than **{pct:.0f}%** "
                                f"of nominees in *{primary_cat}*."
                            )

                    # --- Categories ---
                    st.markdown("**Categories Nominated In:** " + ", ".join(profile["categories"]))

                    # --- Nominations Table ---
                    st.subheader("All Nominations")
                    rows = []
                    for n in profile["nominations"]:
                        rows.append(
                            {
                                "Year": n.year_ceremony,
                                "Category": n.category,
                                "Film": n.film,
                                "Result": "\U0001F3C6 Won" if n.winner else "Nominated",
                            }
                        )
                    df_noms = pd.DataFrame(rows)
                    st.dataframe(df_noms, use_container_width=True, hide_index=True)

                    # --- Did You Know? (Bonus) ---
                    facts = generate_fun_facts(session, profile, wiki)
                    if facts:
                        st.subheader("\U0001F4A1 Did You Know?")
                        for fact in facts:
                            st.markdown(f"- {fact}")

            finally:
                session.close()

    # ===================================================================
    # Task 2.3 ג€” Discoveries
    # ===================================================================
    with tab_discoveries:
        st.subheader("Interesting Findings from the Oscar Dataset")

        session = get_session()
        try:
            # ---------------------------------------------------------------
            # Discovery 1: Most Nominated Without a Win
            # ---------------------------------------------------------------
            st.markdown("### 1. Most Nominated Without a Win")
            st.markdown(
                "Which people have received the most Oscar nominations but have **never won**?"
            )

            no_win = discovery_most_nominated_no_win(session, top_n=15)
            if no_win:
                df1 = pd.DataFrame(no_win, columns=["Name", "Nominations"])
                fig1 = px.bar(
                    df1,
                    x="Nominations",
                    y="Name",
                    orientation="h",
                    title="Most Oscar Nominations Without a Win",
                    color="Nominations",
                    color_continuous_scale=[[0, "#6BAED6"], [1, "#08306B"]],
                )
                fig1.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
                st.plotly_chart(fig1, use_container_width=True)

                top_name = df1.iloc[0]["Name"]
                top_noms = int(df1.iloc[0]["Nominations"])
                st.markdown(
                    f"**Finding:** {top_name} leads this list with {top_noms} nominations and no wins.\n\n"
                    "**How found:** Filtered to acting/directing categories, grouped by person, "
                    "counted nominations and wins, kept only people with zero wins, then sorted descending.\n\n"
                    "**Why interesting:** It shows that repeated Oscar recognition does not guarantee a win, "
                    "which highlights how competitive and context-dependent award outcomes can be."
                )

                with st.expander("Show ORM Query Code"):
                    st.code(
                        textwrap.dedent("""\
                        sub = (
                            session.query(
                                Nomination.name,
                                func.count(Nomination.id).label("total_noms"),
                                func.sum(case((Nomination.winner == True, 1), else_=0)).label("total_wins"),
                            )
                            .filter(Nomination.category.like("ACTOR%") | Nomination.category.like("ACTRESS%") | Nomination.category.like("DIRECTING%"))
                            .group_by(Nomination.name)
                            .subquery()
                        )
                        results = (
                            session.query(sub.c.name, sub.c.total_noms)
                            .filter(sub.c.total_wins == 0)
                            .order_by(sub.c.total_noms.desc())
                            .limit(15)
                            .all()
                        )
                        """),
                        language="python",
                    )

            st.divider()

            # ---------------------------------------------------------------
            # Discovery 2: Longest Wait for First Win
            # ---------------------------------------------------------------
            st.markdown("### 2. Longest Wait for First Win")
            st.markdown(
                "Who waited the longest between their **first nomination** and "
                "their **first win**?"
            )

            wait = discovery_longest_wait_for_win(session, top_n=15)
            if wait:
                df2 = pd.DataFrame(
                    wait, columns=["Name", "First Nomination", "First Win", "Wait (years)"]
                )

                fig2 = go.Figure()
                for _, row in df2.iterrows():
                    fig2.add_trace(
                        go.Scatter(
                            x=[row["First Nomination"], row["First Win"]],
                            y=[row["Name"], row["Name"]],
                            mode="lines+markers+text",
                            text=["Nominated", "Won"],
                            textposition="top center",
                            marker=dict(size=10),
                            line=dict(width=3),
                            name=row["Name"],
                            showlegend=False,
                        )
                    )
                fig2.update_layout(
                    title="Timeline: First Nomination to First Win",
                    xaxis_title="Year",
                    yaxis={"categoryorder": "array", "categoryarray": df2["Name"].tolist()[::-1]},
                    height=550,
                )
                st.plotly_chart(fig2, use_container_width=True)
                st.dataframe(df2, use_container_width=True, hide_index=True)

                top_wait_name = df2.iloc[0]["Name"]
                top_wait_years = int(df2.iloc[0]["Wait (years)"])
                top_first_nom = int(df2.iloc[0]["First Nomination"])
                top_first_win = int(df2.iloc[0]["First Win"])
                st.markdown(
                    f"**Finding:** {top_wait_name} has the longest wait here: {top_wait_years} years "
                    f"({top_first_nom} to {top_first_win}).\n\n"
                    "**How found:** For each person, computed first nomination year and first win year, "
                    "joined both results, calculated the year gap, filtered positive gaps, and sorted descending.\n\n"
                    "**Why interesting:** It shows that Oscar success can take decades, so longevity and persistence "
                    "often matter as much as early-career momentum."
                )

                with st.expander("Show ORM Query Code"):
                    st.code(
                        textwrap.dedent("""\
                        # Filter for actors and directors only
                        cat_filter = Nomination.category.like("ACTOR%") | Nomination.category.like("ACTRESS%") | Nomination.category.like("DIRECTING%")
                        first_nom = (
                            session.query(
                                Nomination.name,
                                func.min(Nomination.year_ceremony).label("first_nom_year"),
                            )
                            .filter(cat_filter)
                            .group_by(Nomination.name)
                            .subquery()
                        )
                        first_win = (
                            session.query(
                                Nomination.name,
                                func.min(Nomination.year_ceremony).label("first_win_year"),
                            )
                            .filter(Nomination.winner == True, cat_filter)
                            .group_by(Nomination.name)
                            .subquery()
                        )
                        results = (
                            session.query(
                                first_nom.c.name,
                                first_nom.c.first_nom_year,
                                first_win.c.first_win_year,
                                (first_win.c.first_win_year - first_nom.c.first_nom_year).label("wait_years"),
                            )
                            .join(first_win, first_nom.c.name == first_win.c.name)
                            .filter((first_win.c.first_win_year - first_nom.c.first_nom_year) > 0)
                            .order_by((first_win.c.first_win_year - first_nom.c.first_nom_year).desc())
                            .limit(15)
                            .all()
                        )
                        """),
                        language="python",
                    )

            st.divider()

            # ---------------------------------------------------------------
            # Discovery 3: Multi-Category Nominees
            # ---------------------------------------------------------------
            st.markdown("### 3. Multi-Category Nominees")
            st.markdown(
                "Who has been nominated in the **most different categories**? "
                "These versatile artists have been recognized across multiple disciplines."
            )

            multi = discovery_multi_category(session, top_n=15)
            if multi:
                df3 = pd.DataFrame(
                    multi, columns=["Name", "Distinct Categories", "Total Nominations"]
                )
                st.dataframe(df3, use_container_width=True, hide_index=True)

                fig3 = px.bar(
                    df3,
                    x="Name",
                    y="Distinct Categories",
                    color="Total Nominations",
                    title="Nominees in the Most Different Oscar Categories",
                    color_continuous_scale="Viridis",
                )
                fig3.update_layout(xaxis_tickangle=-45, height=500)
                st.plotly_chart(fig3, use_container_width=True)

                st.markdown("**Categories per person (top 5):**")
                for row in multi[:5]:
                    person_cats = (
                        session.query(distinct(Nomination.category))
                        .filter(Nomination.name == row[0])
                        .all()
                    )
                    cats = [c[0] for c in person_cats]
                    st.markdown(f"- **{row[0]}**: {', '.join(cats)}")

                top_multi_name = df3.iloc[0]["Name"]
                top_multi_cats = int(df3.iloc[0]["Distinct Categories"])
                st.markdown(
                    f"**Finding:** {top_multi_name} has the broadest category footprint in this result set "
                    f"({top_multi_cats} distinct categories).\n\n"
                    "**How found:** Filtered to acting/directing categories, grouped by person, counted distinct "
                    "categories and total nominations, kept only people with more than one category, then sorted by breadth.\n\n"
                    "**Why interesting:** Recognition across multiple categories is a strong signal of versatility, "
                    "showing who succeeded in more than one creative lane."
                )

                with st.expander("Show ORM Query Code"):
                    st.code(
                        textwrap.dedent("""\
                        cat_filter = Nomination.category.like("ACTOR%") | Nomination.category.like("ACTRESS%") | Nomination.category.like("DIRECTING%")
                        results = (
                            session.query(
                                Nomination.name,
                                func.count(distinct(Nomination.category)).label("num_categories"),
                                func.count(Nomination.id).label("total_noms"),
                            )
                            .filter(cat_filter)
                            .group_by(Nomination.name)
                            .having(func.count(distinct(Nomination.category)) > 1)
                            .order_by(
                                func.count(distinct(Nomination.category)).desc(),
                                func.count(Nomination.id).desc(),
                            )
                            .limit(15)
                            .all()
                        )
                        """),
                        language="python",
                    )

        finally:
            session.close()

    with tab_schema:
        st.header("Database Schema & ORM Design (Task 2.1)")
        st.markdown("""\
**Table: `nominations`**

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `year_film` | Integer | Release year of the film |
| `year_ceremony` | Integer | Year the ceremony took place |
| `ceremony` | Integer | Ceremony number |
| `category` | String | Award category |
| `name` | String | Nominee name |
| `film` | String | Film title |
| `winner` | Boolean | Whether the nomination won |

**Design Rationale:** A single *Nomination* table faithfully mirrors the flat CSV
structure. Further normalization (separate Person / Film / Category tables) was considered
but adds complexity without clear benefit for this read-heavy analytical workload.
Indexes on `name`, `category`, `year_ceremony`, and `year_film` speed up the profile
and discovery queries. All queries use the **SQLAlchemy ORM** — no raw SQL.
""")
        st.subheader("ORM Model Code")
        st.code("""\
class Nomination(Base):
    __tablename__ = "nominations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    year_film = Column(Integer, index=True)
    year_ceremony = Column(Integer, index=True)
    ceremony = Column(Integer)
    category = Column(String, index=True)
    name = Column(String, index=True)
    film = Column(String)
    winner = Column(Boolean, default=False)
""", language="python")


if __name__ == "__main__":
    main()


