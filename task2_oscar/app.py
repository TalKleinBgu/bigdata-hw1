"""
Oscar Actor Explorer - Task 2
Big Data Homework 1

A Streamlit application that uses SQLAlchemy ORM to query an Oscar Award
dataset stored in SQLite and enriches actor profiles with live Wikipedia data.
"""

import difflib
import os
import tempfile
import textwrap
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    func,
    case,
    distinct,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship, joinedload
from sqlalchemy.exc import OperationalError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_ROOT = Path(os.getenv("OSCAR_DB_DIR", Path(tempfile.gettempdir()) / "oscar_explorer"))
DB_ROOT.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_ROOT / "oscar.db"
CSV_PATH = BASE_DIR / "full_data.csv"

# ---------------------------------------------------------------------------
# Task 2.1 - SQLAlchemy ORM Model
# ---------------------------------------------------------------------------
Base = declarative_base()


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (UniqueConstraint("name", name="uq_people_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    nominations = relationship("Nomination", back_populates="person", cascade="all, delete-orphan")


class Film(Base):
    __tablename__ = "films"
    __table_args__ = (UniqueConstraint("title", name="uq_films_title"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False, index=True)
    nominations = relationship("Nomination", back_populates="film_ref")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("name", name="uq_categories_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    nominations = relationship("Nomination", back_populates="category_ref")


class Nomination(Base):
    """Normalized nomination fact table linked to Person / Film / Category."""

    __tablename__ = "nominations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year_film = Column(Integer, index=True)
    year_ceremony = Column(Integer, index=True)
    ceremony = Column(Integer)
    winner = Column(Boolean, default=False, index=True)

    person_id = Column(Integer, ForeignKey("people.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    film_id = Column(Integer, ForeignKey("films.id"), nullable=True, index=True)

    person = relationship("Person", back_populates="nominations")
    category_ref = relationship("Category", back_populates="nominations")
    film_ref = relationship("Film", back_populates="nominations")

    @property
    def name(self) -> str:
        return self.person.name if self.person else ""

    @property
    def category(self) -> str:
        return self.category_ref.name if self.category_ref else ""

    @property
    def film(self) -> str:
        return self.film_ref.title if self.film_ref else ""

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
    # year_film might be "1927/28" - take the first 4 chars
    df["year_film"] = df["year_film"].astype(str).str[:4].astype(int)
    # Create year_ceremony from ceremony number + 1927
    df["year_ceremony"] = df["ceremony"].astype(int) + 1928
    # Winner: True/NaN -> bool
    df["winner"] = df["winner"].fillna(False).astype(bool)
    # Keep only the columns we need
    df = df[["year_film", "year_ceremony", "ceremony", "category", "name", "film", "winner"]]
    df = df.dropna(subset=["name"])
    return df


def _init_db(engine):
    """Create tables and populate from CSV if the DB is empty."""
    Base.metadata.create_all(engine)

    def has_normalized_schema() -> bool:
        """Return True when all normalized tables/columns exist."""
        with engine.connect() as conn:
            table_rows = conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            tables = {r[0] for r in table_rows}
            required_tables = {"people", "films", "categories", "nominations"}
            if not required_tables.issubset(tables):
                return False

            cols_nom = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(nominations)").fetchall()}
            cols_people = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(people)").fetchall()}
            cols_films = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(films)").fetchall()}
            cols_categories = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(categories)").fetchall()}

            needed_nom = {"id", "person_id", "category_id", "film_id", "winner", "year_film", "year_ceremony", "ceremony"}
            needed_people = {"id", "name"}
            needed_films = {"id", "title"}
            needed_categories = {"id", "name"}
            return (
                needed_nom.issubset(cols_nom)
                and needed_people.issubset(cols_people)
                and needed_films.issubset(cols_films)
                and needed_categories.issubset(cols_categories)
            )

    # Migration guard: rebuild if an old flat nominations schema exists.
    if not has_normalized_schema():
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    session_cls = sessionmaker(bind=engine)
    session = session_cls()
    count = session.query(func.count(Nomination.id)).scalar()
    if count == 0:
        df = _load_csv()
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        def clean_text(v):
            if pd.isna(v):
                return None
            s = str(v).strip()
            return s if s else None

        unique_people = sorted({clean_text(v) for v in df["name"].tolist() if clean_text(v)})
        unique_categories = sorted({clean_text(v) for v in df["category"].tolist() if clean_text(v)})
        unique_films = sorted({clean_text(v) for v in df["film"].tolist() if clean_text(v)})

        person_objs = {name: Person(name=name) for name in unique_people}
        category_objs = {name: Category(name=name) for name in unique_categories}
        film_objs = {title: Film(title=title) for title in unique_films}

        session.add_all(person_objs.values())
        session.add_all(category_objs.values())
        session.add_all(film_objs.values())
        session.flush()

        person_id_by_name = {name: obj.id for name, obj in person_objs.items()}
        category_id_by_name = {name: obj.id for name, obj in category_objs.items()}
        film_id_by_title = {title: obj.id for title, obj in film_objs.items()}

        batch = []
        for _, row in df.iterrows():
            person_name = clean_text(row.get("name"))
            category_name = clean_text(row.get("category"))
            if not person_name or not category_name:
                continue

            winner_val = row.get("winner", False)
            if isinstance(winner_val, str):
                winner_val = winner_val.strip().lower() in ("true", "1", "yes")

            film_title = clean_text(row.get("film"))
            batch.append(
                {
                    "year_film": int(row["year_film"]) if pd.notna(row.get("year_film")) else None,
                    "year_ceremony": int(row["year_ceremony"]) if pd.notna(row.get("year_ceremony")) else None,
                    "ceremony": int(row["ceremony"]) if pd.notna(row.get("ceremony")) else None,
                    "winner": bool(winner_val),
                    "person_id": person_id_by_name[person_name],
                    "category_id": category_id_by_name[category_name],
                    "film_id": film_id_by_title.get(film_title),
                }
            )

            if len(batch) >= 15000:
                session.bulk_insert_mappings(Nomination, batch)
                session.commit()
                batch.clear()

        if batch:
            session.bulk_insert_mappings(Nomination, batch)
            session.commit()
    session.close()


@st.cache_resource
def get_engine():
    """Return a cached SQLAlchemy engine and ensure DB is populated."""
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    try:
        _init_db(engine)
        # Health-check a normalized join used by the app.
        with engine.connect() as conn:
            conn.exec_driver_sql(
                """
                SELECT COUNT(*)
                FROM nominations n
                JOIN people p ON n.person_id = p.id
                JOIN categories c ON n.category_id = c.id
                """
            ).scalar_one()
    except OperationalError:
        # Self-heal from stale/corrupt schema on cloud deployments.
        engine.dispose()
        if DB_PATH.exists():
            DB_PATH.unlink()
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
    try:
        filters = [Category.name.like(pat) for pat in PERSON_CATEGORIES_PATTERN]
        names = [
            r[0] for r in session.query(distinct(Person.name))
            .join(Nomination, Nomination.person_id == Person.id)
            .join(Category, Nomination.category_id == Category.id)
            .filter(or_(*filters))
            .order_by(Person.name)
            .all()
            if r[0]
        ]
        return names
    except OperationalError:
        # Cached engine may point to a bad DB from a previous run.
        session.close()
        get_engine.clear()
        session = get_session()
        filters = [Category.name.like(pat) for pat in PERSON_CATEGORIES_PATTERN]
        return [
            r[0] for r in session.query(distinct(Person.name))
            .join(Nomination, Nomination.person_id == Person.id)
            .join(Category, Nomination.category_id == Category.id)
            .filter(or_(*filters))
            .order_by(Person.name)
            .all()
            if r[0]
        ]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Wikipedia helper
# ---------------------------------------------------------------------------

def search_wikipedia_titles(name: str, limit: int = 5) -> list[str]:
    """Return candidate Wikipedia page titles for a person name."""
    import requests

    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "opensearch", "search": name, "limit": limit, "format": "json"},
            headers={"User-Agent": "OscarExplorerApp/1.0"},
            timeout=8,
        )
        data = resp.json()
        titles = data[1] if isinstance(data, list) and len(data) > 1 else []
        return [t for t in titles if isinstance(t, str) and t.strip()]
    except Exception:
        return []


def fetch_wikipedia_info_from_title(page_title: str) -> dict:
    """Fetch summary, image, and birth date for a concrete Wikipedia page title."""
    import requests
    import re
    from urllib.parse import quote

    API = "https://en.wikipedia.org/api/rest_v1"
    HEADERS = {"User-Agent": "OscarExplorerApp/1.0"}
    info: dict = {"summary": None, "image": None, "birth_date": None, "page_url": None}

    try:
        api_title = page_title.replace(" ", "_")
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
        .join(Person, Nomination.person_id == Person.id)
        .options(
            joinedload(Nomination.person),
            joinedload(Nomination.category_ref),
            joinedload(Nomination.film_ref),
        )
        .filter(Person.name == name)
        .order_by(Nomination.year_ceremony)
        .all()
    )
    if not noms:
        return {}
    wins = [n for n in noms if n.winner]
    categories = sorted({n.category for n in noms if n.category})
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
            Person.name.label("person_name"),
            func.count(Nomination.id).label("cnt"),
        )
        .join(Person, Nomination.person_id == Person.id)
        .join(Category, Nomination.category_id == Category.id)
        .filter(Category.name == category)
        .group_by(Person.id, Person.name)
        .subquery()
    )
    person_count = (
        session.query(sub.c.cnt).filter(sub.c.person_name == name).scalar()
    )
    if person_count is None:
        return None
    total = session.query(func.count()).select_from(sub).scalar()
    below = session.query(func.count()).select_from(sub).filter(sub.c.cnt < person_count).scalar()
    if total == 0:
        return None
    return below / total * 100


def compute_category_average_comparison(session: Session, name: str, category: str) -> dict | None:
    """Compare the person to average nominees in the same category."""
    sub = (
        session.query(
            Person.name.label("person_name"),
            func.count(Nomination.id).label("noms"),
            (
                func.sum(case((Nomination.winner == True, 1), else_=0)) * 100.0
                / func.count(Nomination.id)
            ).label("win_rate"),
        )
        .join(Nomination, Nomination.person_id == Person.id)
        .join(Category, Nomination.category_id == Category.id)
        .filter(Category.name == category)
        .group_by(Person.id, Person.name)
        .subquery()
    )

    person_row = (
        session.query(sub.c.noms, sub.c.win_rate)
        .filter(sub.c.person_name == name)
        .first()
    )
    if not person_row:
        return None

    avg_noms, avg_win_rate = session.query(
        func.avg(sub.c.noms),
        func.avg(sub.c.win_rate),
    ).one()

    return {
        "person_noms": float(person_row.noms or 0),
        "person_win_rate": float(person_row.win_rate or 0),
        "avg_noms": float(avg_noms or 0),
        "avg_win_rate": float(avg_win_rate or 0),
    }


# ---------------------------------------------------------------------------
# Discovery queries (Task 2.3)
# ---------------------------------------------------------------------------

def _actor_director_filter():
    """Return an OR filter that restricts to acting/directing categories."""
    from sqlalchemy import or_
    return or_(*[Category.name.like(pat) for pat in PERSON_CATEGORIES_PATTERN])


def discovery_most_nominated_no_win(session: Session, top_n: int = 15):
    """Actors/directors with the most nominations but zero wins."""
    sub = (
        session.query(
            Person.name.label("name"),
            func.count(Nomination.id).label("total_noms"),
            func.sum(case((Nomination.winner == True, 1), else_=0)).label("total_wins"),
        )
        .join(Person, Nomination.person_id == Person.id)
        .join(Category, Nomination.category_id == Category.id)
        .filter(_actor_director_filter())
        .group_by(Person.id, Person.name)
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
            Person.name.label("name"),
            func.min(Nomination.year_ceremony).label("first_nom_year"),
        )
        .join(Person, Nomination.person_id == Person.id)
        .join(Category, Nomination.category_id == Category.id)
        .filter(cat_filter)
        .group_by(Person.id, Person.name)
        .subquery()
    )
    first_win = (
        session.query(
            Person.name.label("name"),
            func.min(Nomination.year_ceremony).label("first_win_year"),
        )
        .join(Person, Nomination.person_id == Person.id)
        .join(Category, Nomination.category_id == Category.id)
        .filter(Nomination.winner == True)
        .filter(cat_filter)
        .group_by(Person.id, Person.name)
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
            Person.name.label("name"),
            func.count(distinct(Category.name)).label("num_categories"),
            func.count(Nomination.id).label("total_noms"),
        )
        .join(Person, Nomination.person_id == Person.id)
        .join(Category, Nomination.category_id == Category.id)
        .filter(_actor_director_filter())
        .group_by(Person.id, Person.name)
        .having(func.count(distinct(Category.name)) > 1)
        .order_by(func.count(distinct(Category.name)).desc(), func.count(Nomination.id).desc())
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
    total_nominees = session.query(func.count(distinct(Person.id))).scalar()
    sub_counts = (
        session.query(
            Person.name.label("person_name"),
            func.count(Nomination.id).label("cnt"),
        )
        .join(Nomination, Nomination.person_id == Person.id)
        .group_by(Person.id, Person.name)
        .subquery()
    )
    below = session.query(func.count()).select_from(sub_counts).filter(sub_counts.c.cnt < num_noms).scalar()
    pct = round(below / total_nominees * 100) if total_nominees else 0
    facts.append(f"{name} has more nominations than {pct}% of all Oscar-nominated individuals.")

    # Fact 2: Win % in primary category
    if profile["categories"]:
        cat = profile["categories"][0]
        cat_total = (
            session.query(func.count(distinct(Person.id)))
            .join(Nomination, Nomination.person_id == Person.id)
            .join(Category, Nomination.category_id == Category.id)
            .filter(Category.name == cat)
            .scalar()
        )
        cat_winners = (
            session.query(func.count(distinct(Person.id)))
            .join(Nomination, Nomination.person_id == Person.id)
            .join(Category, Nomination.category_id == Category.id)
            .filter(Category.name == cat, Nomination.winner == True)
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

    st.markdown(
        """
<div class="sticky-page-header">
  <div class="sticky-page-title">Oscar Actor Explorer</div>
  <div class="sticky-page-subtitle">Explore Oscar nomination history, actor profiles, and interesting discoveries</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Ensure DB is ready
    _ = get_engine()
    all_names = get_all_names()

    # ----- Sidebar -----
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
section[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem !important; }
[data-testid="stSidebarContent"] { padding-top: 0.5rem !important; }
.section-header { font-size: 1.15rem; font-weight: 600; color: #1F2937; margin: 1.5rem 0 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid #E5E7EB; }
.section-desc { font-size: 0.88rem; color: #6B7280; margin-bottom: 1rem; line-height: 1.5; }
.insight-box { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px; padding: 0.9rem 1.1rem; margin: 0.75rem 0; font-size: 0.85rem; color: #374151; line-height: 1.6; text-align: left; }
.insight-box b, .insight-box strong { color: #111827; }
</style>
""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<div style="font-size:0.95rem;font-weight:600;color:#1F2937;margin-bottom:0.5rem;">About</div>', unsafe_allow_html=True)
        st.markdown(
            "This app loads the [Oscar Award dataset]"
            "(https://www.kaggle.com/datasets/unanimad/the-oscar-award) "
            "into a SQLite database via **SQLAlchemy ORM** and provides "
            "rich actor/director profiles enriched with live Wikipedia data."
        )

    # ----- Tabs -----
    tab_profile, tab_discoveries, tab_schema = st.tabs(
        ["Actor Profile", "Discoveries", "Schema"]
    )

    # ===================================================================
    # Task 2.2 - Actor Profile
    # ===================================================================
    with tab_profile:
        st.markdown('<div class="section-header">Search for an Actor or Director</div>', unsafe_allow_html=True)

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
                    # --- Fetch Wikipedia info (with disambiguation) ---
                    with st.spinner("Searching Wikipedia..."):
                        wiki_titles = search_wikipedia_titles(target_name, limit=6)

                    wiki_choice = None
                    if wiki_titles:
                        if len(wiki_titles) > 1:
                            st.caption("Multiple Wikipedia matches found. Choose the correct profile:")
                        wiki_choice = st.selectbox(
                            "Wikipedia article",
                            wiki_titles,
                            key=f"wiki_article_{target_name}",
                        )
                        with st.spinner("Fetching Wikipedia data..."):
                            wiki = fetch_wikipedia_info_from_title(wiki_choice)
                    else:
                        wiki = {"summary": None, "image": None, "birth_date": None, "page_url": None}

                    # --- Profile Card ---
                    col_img, col_info = st.columns([1, 3])

                    with col_img:
                        if wiki.get("image"):
                            st.image(wiki["image"], width=250, caption=target_name)
                        else:
                            st.caption("Wikipedia photo unavailable.")

                    with col_info:
                        st.markdown(f'<div style="font-size:1.3rem;font-weight:700;color:#111827;">{target_name}</div>', unsafe_allow_html=True)
                        if wiki.get("birth_date"):
                            st.markdown(f"**Born:** {wiki['birth_date']}")
                        else:
                            st.caption("Birth date unavailable from Wikipedia.")
                        if wiki.get("summary"):
                            st.markdown(wiki["summary"])
                        elif wiki.get("page_url"):
                            st.markdown(f"[Open Wikipedia page]({wiki['page_url']})")
                            st.caption("Biography summary unavailable from Wikipedia API.")
                        else:
                            st.info("No Wikipedia profile found. Showing dataset-only profile.")

                    has_wiki_data = any([wiki.get("summary"), wiki.get("image"), wiki.get("birth_date")])
                    source_label = "Dataset + Wikipedia" if has_wiki_data else "Dataset only"
                    st.caption(f"Profile source: {source_label}")

                    st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)

                    # --- Oscar Stats (styled gradient cards) ---
                    _wins_display = profile["num_wins"] if profile["num_wins"] else "0"
                    _years_display = (
                        f"{profile['first_year']} - {profile['last_year']}"
                        if profile["first_year"]
                        else "N/A"
                    )
                    st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:1rem 0;">
  <div style="background:linear-gradient(135deg,#EEF2FF,#E0E7FF);border-radius:12px;padding:1rem;text-align:center;border:1px solid #C7D2FE;">
    <div style="font-size:0.75rem;color:#6B7280;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">&#127942; Nominations</div>
    <div style="font-size:1.8rem;font-weight:800;color:#4338CA;">{profile["num_nominations"]}</div>
  </div>
  <div style="background:linear-gradient(135deg,#FFFBEB,#FEF3C7);border-radius:12px;padding:1rem;text-align:center;border:1px solid #FDE68A;">
    <div style="font-size:0.75rem;color:#6B7280;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">&#127941; Wins</div>
    <div style="font-size:1.8rem;font-weight:800;color:#B45309;">{_wins_display}</div>
  </div>
  <div style="background:linear-gradient(135deg,#ECFDF5,#D1FAE5);border-radius:12px;padding:1rem;text-align:center;border:1px solid #A7F3D0;">
    <div style="font-size:0.75rem;color:#6B7280;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">&#9989; Win Rate</div>
    <div style="font-size:1.8rem;font-weight:800;color:#065F46;">{profile['win_rate']:.1f}%</div>
  </div>
  <div style="background:linear-gradient(135deg,#F5F3FF,#EDE9FE);border-radius:12px;padding:1rem;text-align:center;border:1px solid #DDD6FE;">
    <div style="font-size:0.75rem;color:#6B7280;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">&#128197; Years Active</div>
    <div style="font-size:1.8rem;font-weight:800;color:#6D28D9;">{_years_display}</div>
  </div>
</div>
""", unsafe_allow_html=True)

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

                        avg_cmp = compute_category_average_comparison(session, target_name, primary_cat)
                        if avg_cmp is not None:
                            delta_noms = avg_cmp["person_noms"] - avg_cmp["avg_noms"]
                            delta_wr = avg_cmp["person_win_rate"] - avg_cmp["avg_win_rate"]
                            st.info(
                                f"Category average comparison (*{primary_cat}*): "
                                f"Avg nominee = **{avg_cmp['avg_noms']:.2f} nominations**, "
                                f"**{avg_cmp['avg_win_rate']:.1f}% win rate**. "
                                f"{target_name} = **{int(avg_cmp['person_noms'])} nominations** "
                                f"({delta_noms:+.2f} vs avg), **{avg_cmp['person_win_rate']:.1f}% win rate** "
                                f"({delta_wr:+.1f} pp vs avg)."
                            )

                    # --- Categories ---
                    st.markdown("**Categories Nominated In:** " + ", ".join(profile["categories"]))

                    # --- Nominations Table ---
                    st.markdown('<div class="section-header">All Nominations</div>', unsafe_allow_html=True)
                    st.caption("Look for the \U0001F3C6 trophy icon in the Result column to spot wins.")
                    rows = []
                    for n in profile["nominations"]:
                        rows.append(
                            {
                                "Year": n.year_ceremony,
                                "Category": n.category if n.category else "N/A",
                                "Film": n.film if n.film else "N/A",
                                "Result": "\U0001F3C6 Won" if n.winner else "Nominated",
                            }
                        )
                    df_noms = pd.DataFrame(rows)
                    st.dataframe(df_noms, use_container_width=True, hide_index=True)

                    # --- Did You Know? (Bonus) ---
                    facts = generate_fun_facts(session, profile, wiki)
                    if facts:
                        st.markdown('<div class="section-header">Did You Know?</div>', unsafe_allow_html=True)
                        for fact in facts:
                            st.markdown(f"- {fact}")

            finally:
                session.close()

    # ===================================================================
    # Task 2.3 - Discoveries
    # ===================================================================
    with tab_discoveries:
        st.markdown('<div class="section-header">Interesting Findings from the Oscar Dataset</div>', unsafe_allow_html=True)

        session = get_session()
        try:
            # ---------------------------------------------------------------
            # Discovery 1: Most Nominated Without a Win
            # ---------------------------------------------------------------
            st.markdown('<div class="section-header">1. Most Nominated Without a Win</div>', unsafe_allow_html=True)
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
                    color_continuous_scale=[[0, "#93C5FD"], [0.5, "#3B82F6"], [1, "#1E3A8A"]],
                    text="Nominations",
                )
                fig1.update_traces(
                    textposition="outside",
                    textfont_size=11,
                    marker_cornerradius=5,
                )
                fig1.update_layout(
                    yaxis={"categoryorder": "total ascending"},
                    height=520,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    title_font_size=16,
                    yaxis_gridcolor="#E5E7EB",
                    xaxis_gridcolor="#E5E7EB",
                    hovermode="x unified",
                    margin=dict(r=60),
                )
                st.plotly_chart(fig1, use_container_width=True)

                top_name = df1.iloc[0]["Name"]
                top_noms = int(df1.iloc[0]["Nominations"])
                st.markdown(
                    f'<div class="insight-box">'
                    f'<strong>Finding:</strong> {top_name} leads this list with {top_noms} nominations and no wins.<br><br>'
                    '<strong>How found:</strong> Filtered to acting/directing categories, grouped by person, '
                    'counted nominations and wins, kept only people with zero wins, then sorted descending.<br><br>'
                    '<strong>Why interesting:</strong> It shows that repeated Oscar recognition does not guarantee a win, '
                    'which highlights how competitive and context-dependent award outcomes can be.'
                    '</div>',
                    unsafe_allow_html=True,
                )

                with st.expander("Show ORM Query Code"):
                    st.code(
                        textwrap.dedent("""\
                        sub = (
                            session.query(
                                Person.name.label("name"),
                                func.count(Nomination.id).label("total_noms"),
                                func.sum(case((Nomination.winner == True, 1), else_=0)).label("total_wins"),
                            )
                            .join(Person, Nomination.person_id == Person.id)
                            .join(Category, Nomination.category_id == Category.id)
                            .filter(
                                Category.name.like("ACTOR%")
                                | Category.name.like("ACTRESS%")
                                | Category.name.like("DIRECTING%")
                            )
                            .group_by(Person.id, Person.name)
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

            st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)

            # ---------------------------------------------------------------
            # Discovery 2: Longest Wait for First Win
            # ---------------------------------------------------------------
            st.markdown('<div class="section-header">2. Longest Wait for First Win</div>', unsafe_allow_html=True)
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
                    # Connecting line
                    fig2.add_trace(
                        go.Scatter(
                            x=[row["First Nomination"], row["First Win"]],
                            y=[row["Name"], row["Name"]],
                            mode="lines",
                            line=dict(width=4, color="#CBD5E1"),
                            showlegend=False,
                            hoverinfo="skip",
                        )
                    )
                    # Nominated marker (red)
                    fig2.add_trace(
                        go.Scatter(
                            x=[row["First Nomination"]],
                            y=[row["Name"]],
                            mode="markers+text",
                            text=[str(int(row["First Nomination"]))],
                            textposition="bottom center",
                            textfont=dict(size=9, color="#DC2626"),
                            marker=dict(size=12, color="#EF4444", symbol="circle",
                                        line=dict(width=1.5, color="#FFFFFF")),
                            showlegend=False,
                            hovertemplate=f"<b>{row['Name']}</b><br>Nominated: {int(row['First Nomination'])}<extra></extra>",
                        )
                    )
                    # Won marker (green)
                    fig2.add_trace(
                        go.Scatter(
                            x=[row["First Win"]],
                            y=[row["Name"]],
                            mode="markers+text",
                            text=[str(int(row["First Win"]))],
                            textposition="bottom center",
                            textfont=dict(size=9, color="#16A34A"),
                            marker=dict(size=12, color="#22C55E", symbol="diamond",
                                        line=dict(width=1.5, color="#FFFFFF")),
                            showlegend=False,
                            hovertemplate=f"<b>{row['Name']}</b><br>Won: {int(row['First Win'])}<extra></extra>",
                        )
                    )
                fig2.update_layout(
                    title=dict(text="Timeline: First Nomination to First Win", font_size=16),
                    xaxis_title="Year",
                    yaxis={"categoryorder": "array", "categoryarray": df2["Name"].tolist()[::-1]},
                    height=600,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    yaxis_gridcolor="#E5E7EB",
                    xaxis_gridcolor="#E5E7EB",
                    hovermode="closest",
                    margin=dict(l=10),
                )
                # Add legend-like annotation
                fig2.add_annotation(
                    text="<span style='color:#EF4444;'>&#9679;</span> Nominated &nbsp;&nbsp; <span style='color:#22C55E;'>&#9670;</span> Won",
                    xref="paper", yref="paper", x=0.5, y=1.06,
                    showarrow=False, font=dict(size=12),
                )
                st.plotly_chart(fig2, use_container_width=True)
                st.dataframe(df2, use_container_width=True, hide_index=True)

                top_wait_name = df2.iloc[0]["Name"]
                top_wait_years = int(df2.iloc[0]["Wait (years)"])
                top_first_nom = int(df2.iloc[0]["First Nomination"])
                top_first_win = int(df2.iloc[0]["First Win"])
                st.markdown(
                    f'<div class="insight-box">'
                    f'<strong>Finding:</strong> {top_wait_name} has the longest wait here: {top_wait_years} years '
                    f'({top_first_nom} to {top_first_win}).<br><br>'
                    '<strong>How found:</strong> For each person, computed first nomination year and first win year, '
                    'joined both results, calculated the year gap, filtered positive gaps, and sorted descending.<br><br>'
                    '<strong>Why interesting:</strong> It shows that Oscar success can take decades, so longevity and persistence '
                    'often matter as much as early-career momentum.'
                    '</div>',
                    unsafe_allow_html=True,
                )

                with st.expander("Show ORM Query Code"):
                    st.code(
                        textwrap.dedent("""\
                        # Filter for actors and directors only
                        cat_filter = Category.name.like("ACTOR%") | Category.name.like("ACTRESS%") | Category.name.like("DIRECTING%")
                        first_nom = (
                            session.query(
                                Person.name.label("name"),
                                func.min(Nomination.year_ceremony).label("first_nom_year"),
                            )
                            .join(Person, Nomination.person_id == Person.id)
                            .join(Category, Nomination.category_id == Category.id)
                            .filter(cat_filter)
                            .group_by(Person.id, Person.name)
                            .subquery()
                        )
                        first_win = (
                            session.query(
                                Person.name.label("name"),
                                func.min(Nomination.year_ceremony).label("first_win_year"),
                            )
                            .join(Person, Nomination.person_id == Person.id)
                            .join(Category, Nomination.category_id == Category.id)
                            .filter(Nomination.winner == True, cat_filter)
                            .group_by(Person.id, Person.name)
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

            st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)

            # ---------------------------------------------------------------
            # Discovery 3: Multi-Category Nominees
            # ---------------------------------------------------------------
            st.markdown('<div class="section-header">3. Multi-Category Nominees</div>', unsafe_allow_html=True)
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
                    color_continuous_scale="Plasma",
                    text="Distinct Categories",
                )
                fig3.update_traces(
                    textposition="outside",
                    textfont_size=11,
                    marker_cornerradius=5,
                )
                fig3.update_layout(
                    xaxis_tickangle=-45,
                    height=520,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    title_font_size=16,
                    yaxis_gridcolor="#E5E7EB",
                    xaxis_gridcolor="#E5E7EB",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                )
                st.plotly_chart(fig3, use_container_width=True)

                st.markdown("**Categories per person (top 5):**")
                for row in multi[:5]:
                    person_cats = (
                        session.query(distinct(Category.name))
                        .join(Nomination, Nomination.category_id == Category.id)
                        .join(Person, Nomination.person_id == Person.id)
                        .filter(Person.name == row[0])
                        .all()
                    )
                    cats = [c[0] for c in person_cats]
                    st.markdown(f"- **{row[0]}**: {', '.join(cats)}")

                top_multi_name = df3.iloc[0]["Name"]
                top_multi_cats = int(df3.iloc[0]["Distinct Categories"])
                st.markdown(
                    f'<div class="insight-box">'
                    f'<strong>Finding:</strong> {top_multi_name} has the broadest category footprint in this result set '
                    f'({top_multi_cats} distinct categories).<br><br>'
                    '<strong>How found:</strong> Filtered to acting/directing categories, grouped by person, counted distinct '
                    'categories and total nominations, kept only people with more than one category, then sorted by breadth.<br><br>'
                    '<strong>Why interesting:</strong> Recognition across multiple categories is a strong signal of versatility, '
                    'showing who succeeded in more than one creative lane.'
                    '</div>',
                    unsafe_allow_html=True,
                )

                with st.expander("Show ORM Query Code"):
                    st.code(
                        textwrap.dedent("""\
                        cat_filter = Category.name.like("ACTOR%") | Category.name.like("ACTRESS%") | Category.name.like("DIRECTING%")
                        results = (
                            session.query(
                                Person.name.label("name"),
                                func.count(distinct(Category.name)).label("num_categories"),
                                func.count(Nomination.id).label("total_noms"),
                            )
                            .join(Person, Nomination.person_id == Person.id)
                            .join(Category, Nomination.category_id == Category.id)
                            .filter(cat_filter)
                            .group_by(Person.id, Person.name)
                            .having(func.count(distinct(Category.name)) > 1)
                            .order_by(
                                func.count(distinct(Category.name)).desc(),
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
        st.markdown('<div class="section-header">Database Schema and ORM Design</div>', unsafe_allow_html=True)
        st.markdown("""\
**Tables (normalized ORM schema):**

| Column | Type | Description |
|---|---|---|
| `people.id` | Integer (PK) | Person identifier |
| `people.name` | String (UNIQUE) | Actor/director name |
| `categories.id` | Integer (PK) | Category identifier |
| `categories.name` | String (UNIQUE) | Oscar category |
| `films.id` | Integer (PK) | Film identifier |
| `films.title` | String (UNIQUE) | Film title |
| `id` | Integer (PK) | Auto-increment primary key |
| `year_film` | Integer | Release year of the film |
| `year_ceremony` | Integer | Year the ceremony took place |
| `ceremony` | Integer | Ceremony number |
| `person_id` | Integer (FK) | Link to `people.id` |
| `category_id` | Integer (FK) | Link to `categories.id` |
| `film_id` | Integer (FK) | Link to `films.id` |
| `winner` | Boolean | Whether the nomination won |

**Design Rationale:** I normalized the flat CSV into `people`, `categories`, `films`,
and `nominations` to remove duplication and make joins/aggregations cleaner.
This is especially useful for profile and discovery queries that repeatedly group
by person/category. I chose **SQLAlchemy ORM** because it has strong ecosystem support,
clear relationship modeling (`relationship`, `joinedload`), and smooth integration
with Streamlit for cached sessions and query composition. All data access is via ORM
queries (no raw SQL for Task 2 logic).
""")
        st.markdown('<div class="section-header">ORM Model Code</div>', unsafe_allow_html=True)
        st.code("""\
class Person(Base):
    __tablename__ = "people"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)

class Film(Base):
    __tablename__ = "films"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False, unique=True, index=True)

class Nomination(Base):
    __tablename__ = "nominations"
    id = Column(Integer, primary_key=True)
    year_film = Column(Integer, index=True)
    year_ceremony = Column(Integer, index=True)
    ceremony = Column(Integer)
    winner = Column(Boolean, default=False, index=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    film_id = Column(Integer, ForeignKey("films.id"), nullable=True, index=True)
""", language="python")


if __name__ == "__main__":
    main()
