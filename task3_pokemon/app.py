"""
Pokemon Battle Arena - Big Data Homework 1, Task 3
A Streamlit app with SQLite-backed Pokemon battles, cheat codes, and analysis.
"""

import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import html
import os
import random
import time
import copy
from datetime import datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pokemon.db")
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Pokemon.csv")

TYPE_EMOJIS = {
    "Normal": "\u2b50", "Fire": "\U0001f525", "Water": "\U0001f4a7",
    "Grass": "\U0001f33f", "Electric": "\u26a1", "Ice": "\u2744\ufe0f",
    "Fighting": "\U0001f94a", "Poison": "\u2620\ufe0f", "Ground": "\U0001f30d",
    "Flying": "\U0001f54a\ufe0f", "Psychic": "\U0001f52e", "Bug": "\U0001f41b",
    "Rock": "\U0001faa8", "Ghost": "\U0001f47b", "Dragon": "\U0001f409",
    "Dark": "\U0001f311", "Steel": "\U0001f6e1\ufe0f", "Fairy": "\U0001f9da",
}

# Full 18x18 type effectiveness chart  (attacking_type -> defending_type -> multiplier)
# Only non-1.0 entries are listed; everything else defaults to 1.0.
TYPE_CHART = {
    "Normal":   {"Rock": 0.5, "Ghost": 0.0, "Steel": 0.5},
    "Fire":     {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 2.0, "Bug": 2.0, "Rock": 0.5, "Dragon": 0.5, "Steel": 2.0},
    "Water":    {"Fire": 2.0, "Water": 0.5, "Grass": 0.5, "Ground": 2.0, "Rock": 2.0, "Dragon": 0.5},
    "Grass":    {"Fire": 0.5, "Water": 2.0, "Grass": 0.5, "Poison": 0.5, "Ground": 2.0, "Flying": 0.5, "Bug": 0.5, "Rock": 2.0, "Dragon": 0.5, "Steel": 0.5},
    "Electric": {"Water": 2.0, "Grass": 0.5, "Electric": 0.5, "Ground": 0.0, "Flying": 2.0, "Dragon": 0.5},
    "Ice":      {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 0.5, "Ground": 2.0, "Flying": 2.0, "Dragon": 2.0, "Steel": 0.5},
    "Fighting": {"Normal": 2.0, "Ice": 2.0, "Poison": 0.5, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5, "Rock": 2.0, "Ghost": 0.0, "Dark": 2.0, "Steel": 2.0, "Fairy": 0.5},
    "Poison":   {"Grass": 2.0, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5, "Steel": 0.0, "Fairy": 2.0},
    "Ground":   {"Fire": 2.0, "Grass": 0.5, "Electric": 2.0, "Poison": 2.0, "Flying": 0.0, "Bug": 0.5, "Rock": 2.0, "Steel": 2.0},
    "Flying":   {"Grass": 2.0, "Electric": 0.5, "Fighting": 2.0, "Bug": 2.0, "Rock": 0.5, "Steel": 0.5},
    "Psychic":  {"Fighting": 2.0, "Poison": 2.0, "Psychic": 0.5, "Dark": 0.0, "Steel": 0.5},
    "Bug":      {"Fire": 0.5, "Grass": 2.0, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5, "Psychic": 2.0, "Ghost": 0.5, "Dark": 2.0, "Steel": 0.5, "Fairy": 0.5},
    "Rock":     {"Fire": 2.0, "Ice": 2.0, "Fighting": 0.5, "Ground": 0.5, "Flying": 2.0, "Bug": 2.0, "Steel": 0.5},
    "Ghost":    {"Normal": 0.0, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5},
    "Dragon":   {"Dragon": 2.0, "Steel": 0.5, "Fairy": 0.0},
    "Dark":     {"Fighting": 0.5, "Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5, "Fairy": 0.5},
    "Steel":    {"Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Ice": 2.0, "Rock": 2.0, "Steel": 0.5, "Fairy": 2.0},
    "Fairy":    {"Fire": 0.5, "Fighting": 2.0, "Poison": 0.5, "Dragon": 2.0, "Dark": 2.0, "Steel": 0.5},
}

ALL_TYPES = list(TYPE_CHART.keys())

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

@st.cache_resource
def get_conn():
    """Return a SQLite connection (cached per session to avoid re-opening)."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_resource
def _init_db_once():
    """Initialize database once per server session."""
    init_database()
    return True


def load_csv() -> pd.DataFrame:
    """Load the Pokemon CSV from the local file."""
    if not os.path.exists(CSV_PATH):
        st.error(
            f"CSV file not found at `{CSV_PATH}`.\n\n"
            "Please place your **Pokemon.csv** file in the `task3_pokemon/` folder and restart the app."
        )
        st.stop()
    return pd.read_csv(CSV_PATH)


def init_database():
    """Create tables, download data if needed, and populate the DB."""
    conn = get_conn()
    cur = conn.cursor()

    # ---- pokemon table ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pokemon (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            type1 TEXT,
            type2 TEXT,
            hp INTEGER,
            attack INTEGER,
            defense INTEGER,
            sp_atk INTEGER,
            sp_def INTEGER,
            speed INTEGER,
            generation INTEGER,
            legendary INTEGER,
            total INTEGER
        )
    """)

    # ---- type_effectiveness table ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS type_effectiveness (
            attacking_type TEXT,
            defending_type TEXT,
            multiplier REAL,
            PRIMARY KEY (attacking_type, defending_type)
        )
    """)

    # ---- battle_history table ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS battle_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pokemon1_name TEXT,
            pokemon2_name TEXT,
            winner_name TEXT,
            cheats_used TEXT,
            timestamp TEXT
        )
    """)

    # ---- pokemon_original (backup for cheat restoration) ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_original (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            type1 TEXT,
            type2 TEXT,
            hp INTEGER,
            attack INTEGER,
            defense INTEGER,
            sp_atk INTEGER,
            sp_def INTEGER,
            speed INTEGER,
            generation INTEGER,
            legendary INTEGER,
            total INTEGER
        )
    """)

    # ---- indexes ----
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_name ON pokemon(name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pokemon_type1 ON pokemon(type1)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_te_types ON type_effectiveness(attacking_type, defending_type)")

    conn.commit()

    # Check if pokemon table is populated
    count = cur.execute("SELECT COUNT(*) FROM pokemon").fetchone()[0]
    if count == 0:
        load_pokemon_data(conn)

    # Check if type_effectiveness is populated
    te_count = cur.execute("SELECT COUNT(*) FROM type_effectiveness").fetchone()[0]
    if te_count == 0:
        load_type_effectiveness(conn)


def load_pokemon_data(conn: sqlite3.Connection):
    """Load CSV and insert into pokemon + pokemon_original tables."""
    df = load_csv()

    # Normalize column names
    col_map = {
        "#": "id", "Name": "name", "Type 1": "type1", "Type 2": "type2",
        "Total": "total", "HP": "hp", "Attack": "attack", "Defense": "defense",
        "Sp. Atk": "sp_atk", "Sp. Def": "sp_def", "Speed": "speed",
        "Generation": "generation", "Legendary": "legendary",
    }
    df = df.rename(columns=col_map)

    # Keep only expected columns
    expected = ["id", "name", "type1", "type2", "hp", "attack", "defense",
                "sp_atk", "sp_def", "speed", "generation", "legendary", "total"]
    for c in expected:
        if c not in df.columns:
            df[c] = None
    df = df[expected]

    # Convert legendary to int (True/False -> 1/0)
    df["legendary"] = df["legendary"].apply(lambda x: 1 if str(x).strip().lower() in ("true", "1") else 0)

    # Fill NaN type2 with empty string
    df["type2"] = df["type2"].fillna("")

    # Remove duplicate names (Mega forms may share #)
    df = df.drop_duplicates(subset="name", keep="first")

    df.to_sql("pokemon", conn, if_exists="replace", index=False)
    df.to_sql("pokemon_original", conn, if_exists="replace", index=False)
    conn.commit()


def load_type_effectiveness(conn: sqlite3.Connection):
    """Insert the full type chart into type_effectiveness table."""
    rows = []
    for atk in ALL_TYPES:
        for dfn in ALL_TYPES:
            mult = TYPE_CHART.get(atk, {}).get(dfn, 1.0)
            rows.append((atk, dfn, mult))

    conn.executemany(
        "INSERT OR REPLACE INTO type_effectiveness VALUES (?, ?, ?)", rows
    )
    conn.commit()


def restore_pokemon_db():
    """Restore pokemon table from pokemon_original (undo all cheats)."""
    conn = get_conn()
    conn.execute("DELETE FROM pokemon")
    conn.execute("""
        INSERT INTO pokemon
        SELECT * FROM pokemon_original
    """)
    # Remove any stolen pokemon rows
    conn.execute("DELETE FROM pokemon WHERE name LIKE '%_stolen'")
    conn.commit()
    conn.close()


def get_all_pokemon_names() -> list:
    conn = get_conn()
    names = [r[0] for r in conn.execute("SELECT name FROM pokemon ORDER BY name").fetchall()]
    conn.close()
    return names


def get_pokemon_by_name(name: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM pokemon WHERE name = ?", (name,)).fetchone()
    conn.close()
    if row is None:
        return None
    cols = ["id", "name", "type1", "type2", "hp", "attack", "defense",
            "sp_atk", "sp_def", "speed", "generation", "legendary", "total"]
    return dict(zip(cols, row))


@st.cache_data(show_spinner=False)
def get_selection_stat_maxima() -> dict:
    """Global maxima for each stat, used to normalize preview bars."""
    conn = get_conn()
    row = conn.execute(
        """
        SELECT
            MAX(hp),
            MAX(attack),
            MAX(defense),
            MAX(sp_atk),
            MAX(sp_def),
            MAX(speed),
            MAX(total)
        FROM pokemon_original
        """
    ).fetchone()
    conn.close()

    if not row:
        return {
            "hp": 1,
            "attack": 1,
            "defense": 1,
            "sp_atk": 1,
            "sp_def": 1,
            "speed": 1,
            "total": 1,
        }

    return {
        "hp": max(1, int(row[0] or 1)),
        "attack": max(1, int(row[1] or 1)),
        "defense": max(1, int(row[2] or 1)),
        "sp_atk": max(1, int(row[3] or 1)),
        "sp_def": max(1, int(row[4] or 1)),
        "speed": max(1, int(row[5] or 1)),
        "total": max(1, int(row[6] or 1)),
    }


def get_type_multiplier(atk_type: str, def_type1: str, def_type2: str) -> float:
    """Look up combined type multiplier from DB."""
    conn = get_conn()
    mult = 1.0
    if atk_type and def_type1:
        row = conn.execute(
            "SELECT multiplier FROM type_effectiveness WHERE attacking_type=? AND defending_type=?",
            (atk_type, def_type1)
        ).fetchone()
        if row:
            mult *= row[0]
    if atk_type and def_type2:
        row = conn.execute(
            "SELECT multiplier FROM type_effectiveness WHERE attacking_type=? AND defending_type=?",
            (atk_type, def_type2)
        ).fetchone()
        if row:
            mult *= row[0]
    conn.close()
    return mult


def save_battle_result(p1_team, p2_team, winner_side, cheats_used):
    conn = get_conn()
    p1_names = ", ".join([p["name"] for p in p1_team])
    p2_names = ", ".join([p["name"] for p in p2_team])
    winner_names = p1_names if winner_side == "player" else p2_names
    cheats_str = ", ".join(cheats_used) if cheats_used else "None"
    conn.execute(
        "INSERT INTO battle_history (pokemon1_name, pokemon2_name, winner_name, cheats_used, timestamp) VALUES (?,?,?,?,?)",
        (p1_names, p2_names, winner_names, cheats_str, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Battle engine
# ---------------------------------------------------------------------------

def calc_damage(attacker: dict, defender: dict) -> tuple:
    """
    Damage formula (based on Pokemon Gen V simplified):
        damage = ((2*50/5 + 2) * attack_power * (A/D)) / 50 + 2) * type_mult * rand(0.85,1.0)
    Where:
        attack_power = 60 (base move power)
        A = max(attacker Attack, attacker Sp.Atk)
        D = defender Defense if A==Attack, else defender Sp.Def
        type_mult = type_effectiveness(attacker.type1 vs defender.type1 & type2)
    Returns (damage, type_mult, effectiveness_text)
    """
    atk_stat = attacker["attack"]
    spatk_stat = attacker["sp_atk"]
    if spatk_stat > atk_stat:
        a_val = spatk_stat
        d_val = defender["sp_def"]
    else:
        a_val = atk_stat
        d_val = defender["defense"]

    # Avoid division by zero
    if d_val == 0:
        d_val = 1

    attack_power = 60
    base = ((2 * 50 / 5 + 2) * attack_power * (a_val / d_val)) / 50 + 2

    type_mult = get_type_multiplier(attacker["type1"], defender["type1"], defender.get("type2", ""))

    rand_factor = random.uniform(0.85, 1.0)
    damage = int(base * type_mult * rand_factor)
    if damage < 0:
        damage = 0

    if type_mult == 0:
        eff = "No effect!"
    elif type_mult > 1:
        eff = "Super effective!"
    elif type_mult < 1:
        eff = "Not very effective..."
    else:
        eff = ""

    return damage, type_mult, eff


def type_badge(t: str) -> str:
    """Return emoji + type name."""
    if not t:
        return ""
    return f"{TYPE_EMOJIS.get(t, '')} {t}"


# ---------------------------------------------------------------------------
# Cheat system
# ---------------------------------------------------------------------------

CHEAT_DESCRIPTIONS = {
    "UPUPDOWNDOWN": "Doubles HP of your team",
    "GODMODE": "Sets defense and sp_def to 999 for your team",
    "STEAL": "Copies opponent's strongest Pokemon to your team",
    "NERF": "Halves opponent's attack, sp_atk, and speed",
}


def apply_cheat(code: str, player_team: list, ai_team: list) -> str | None:
    """Apply cheat code via SQL. Returns description or None if invalid."""
    code = code.strip().upper()
    conn = get_conn()

    if code == "UPUPDOWNDOWN":
        names = [p["name"] for p in player_team]
        placeholders = ",".join(["?"] * len(names))
        conn.execute(f"UPDATE pokemon SET hp = hp * 2 WHERE name IN ({placeholders})", names)
        conn.commit()
        # Update session state team
        for p in player_team:
            p["hp"] *= 2
            p["max_hp"] = p["hp"]
            p["current_hp"] = p["hp"]
        conn.close()
        return CHEAT_DESCRIPTIONS[code]

    elif code == "GODMODE":
        names = [p["name"] for p in player_team]
        placeholders = ",".join(["?"] * len(names))
        conn.execute(f"UPDATE pokemon SET defense = 999, sp_def = 999 WHERE name IN ({placeholders})", names)
        conn.commit()
        for p in player_team:
            p["defense"] = 999
            p["sp_def"] = 999
        conn.close()
        return CHEAT_DESCRIPTIONS[code]

    elif code == "STEAL":
        # Find opponent's strongest by total
        strongest = max(ai_team, key=lambda x: x.get("total", 0))
        stolen_name = strongest["name"] + "_stolen"
        conn.execute("""
            INSERT INTO pokemon (id, name, type1, type2, hp, attack, defense, sp_atk, sp_def, speed, generation, legendary, total)
            SELECT (SELECT MAX(id) FROM pokemon) + 1, name || '_stolen', type1, type2, hp, attack, defense, sp_atk, sp_def, speed, generation, legendary, total
            FROM pokemon WHERE name = ?
        """, (strongest["name"],))
        conn.commit()
        conn.close()
        # Add to player team
        stolen = copy.deepcopy(strongest)
        stolen["name"] = stolen_name
        stolen["current_hp"] = stolen["hp"]
        stolen["max_hp"] = stolen["hp"]
        player_team.append(stolen)
        return f"Stole {strongest['name']} (added as {stolen_name})"

    elif code == "NERF":
        names = [p["name"] for p in ai_team]
        placeholders = ",".join(["?"] * len(names))
        conn.execute(f"UPDATE pokemon SET attack = attack / 2, sp_atk = sp_atk / 2, speed = speed / 2 WHERE name IN ({placeholders})", names)
        conn.commit()
        for p in ai_team:
            p["attack"] = p["attack"] // 2
            p["sp_atk"] = p["sp_atk"] // 2
            p["speed"] = p["speed"] // 2
        conn.close()
        return CHEAT_DESCRIPTIONS[code]

    conn.close()
    return None


# ---------------------------------------------------------------------------
# Cheat Audit
# ---------------------------------------------------------------------------

def run_cheat_audit() -> dict:
    """Run SQL queries to detect cheating. Returns dict of DataFrames."""
    conn = get_conn()
    results = {}

    # 1. Pokemon with stats exceeding original natural maximums
    df1 = pd.read_sql_query("""
        SELECT p.name, p.hp, p.attack, p.defense, p.sp_atk, p.sp_def, p.speed,
               o.hp AS orig_hp, o.attack AS orig_attack, o.defense AS orig_defense
        FROM pokemon p
        LEFT JOIN pokemon_original o ON p.name = o.name
        WHERE p.hp > COALESCE(o.hp, 0) * 1
           OR p.defense > COALESCE(o.defense, 0) * 1
           OR p.sp_def > COALESCE(o.sp_def, 0) * 1
           OR p.attack < COALESCE(o.attack, 0)
           OR p.sp_atk < COALESCE(o.sp_atk, 0)
    """, conn)
    results["Modified Stats (compared to original)"] = df1

    # 2. Stolen Pokemon
    df2 = pd.read_sql_query("""
        SELECT name, type1, type2, total, hp, attack, defense
        FROM pokemon
        WHERE name LIKE '%_stolen'
    """, conn)
    results["Stolen Pokemon"] = df2

    # 3. Suspiciously high HP
    df3 = pd.read_sql_query("""
        SELECT p.name, p.hp, o.hp AS original_hp
        FROM pokemon p
        JOIN pokemon_original o ON p.name = o.name
        WHERE p.hp > o.hp
    """, conn)
    results["Suspiciously High HP"] = df3

    conn.close()
    return results


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

def render_hp_bar(current_hp: int, max_hp: int, label: str = ""):
    """Render a colored HP bar."""
    pct = max(0, current_hp / max_hp) if max_hp > 0 else 0
    if pct > 0.5:
        color = "#4CAF50"
    elif pct > 0.2:
        color = "#FFC107"
    else:
        color = "#F44336"
    st.markdown(f"""
    <div style="margin-bottom:4px"><b>{label}</b> HP: {max(0,current_hp)}/{max_hp}</div>
    <div style="background:#333;border-radius:8px;height:20px;width:100%;overflow:hidden">
        <div style="background:{color};height:100%;width:{pct*100:.1f}%;border-radius:8px;transition:width 0.3s"></div>
    </div>
    """, unsafe_allow_html=True)


def pokemon_card(p: dict):
    """Display a pokemon info card."""
    t1 = type_badge(p.get("type1", ""))
    t2 = type_badge(p.get("type2", ""))
    types_str = t1 + (f" / {t2}" if t2.strip() else "")
    st.markdown(f"**{p['name']}** &nbsp; {types_str}")
    cols = st.columns(6)
    for i, stat in enumerate(["hp", "attack", "defense", "sp_atk", "sp_def", "speed"]):
        cols[i].metric(stat.upper().replace("_", " "), p.get(stat, 0))


def pokemon_preview_card(p: dict, slot_num: int, stat_maxima: dict):
    """Compact preview card with normalized stat bars for team selection."""
    t1 = type_badge(p.get("type1", ""))
    t2_raw = p.get("type2", "")
    t2 = type_badge(t2_raw) if t2_raw else ""
    types_str = t1 + (f" {t2}" if t2 else "")

    def stat_bar(label: str, key: str, color: str) -> str:
        val = int(p.get(key, 0) or 0)
        max_val = int(stat_maxima.get(key, 1) or 1)
        pct = max(0.0, min(100.0, (val / max_val) * 100.0))
        return f"""
        <div style="margin-bottom:6px;">
            <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:#444;">
                <span style="font-weight:700;">{label}</span>
                <span>{val} / {max_val}</span>
            </div>
            <div style="height:7px;background:#dce2ea;border-radius:999px;overflow:hidden;">
                <div style="height:100%;width:{pct:.1f}%;background:{color};border-radius:999px;"></div>
            </div>
        </div>
        """

    stats_html = (
        stat_bar("HP", "hp", "#43A047")
        + stat_bar("ATK", "attack", "#E53935")
        + stat_bar("DEF", "defense", "#1E88E5")
        + stat_bar("SpA", "sp_atk", "#8E24AA")
        + stat_bar("SpD", "sp_def", "#00ACC1")
        + stat_bar("SPD", "speed", "#FB8C00")
        + stat_bar("TOTAL", "total", "#3949AB")
    )

    st.markdown(
        f"""
        <div style="
            border: 1px solid #d6dde8;
            border-radius: 12px;
            padding: 12px 12px 10px 12px;
            background: linear-gradient(160deg, #f7f9fc 0%, #eef2f7 100%);
            margin-top: 6px;
            transition: box-shadow 0.2s ease, transform 0.15s ease;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        "
        onmouseover="this.style.boxShadow='0 4px 16px rgba(74,144,217,0.18)';this.style.transform='translateY(-2px)';"
        onmouseout="this.style.boxShadow='0 1px 4px rgba(0,0,0,0.06)';this.style.transform='translateY(0)';"
        >
            <div style="font-size:0.64rem;font-weight:800;color:#fff;letter-spacing:0.5px;
                background:linear-gradient(135deg,#4A90D9,#6366F1);border-radius:999px;padding:2px 10px;
                display:inline-block;margin-bottom:7px;text-transform:uppercase;">Slot {slot_num}</div>
            <div style="font-size:0.98rem;font-weight:800;margin-bottom:3px;color:#1a1a2e;">{p['name']}</div>
            <div style="font-size:0.80rem;margin-bottom:9px;color:#555;">{types_str}</div>
            {stats_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def classify_log_entry(entry: str) -> tuple[str, str, str, str]:
    """Return (kind, label, accent_color, bg_color) for a log entry."""
    txt = entry.lower()
    if entry.startswith("**Turn"):
        return ("turn", "TURN", "#6366F1", "#EEF2FF")
    if "cheat activated" in txt:
        return ("cheat", "CHEAT", "#C026D3", "#FDF4FF")
    if "fainted" in txt:
        return ("ko", "K.O.", "#DC2626", "#FEF2F2")
    if "wins" in txt or "draw" in txt:
        return ("result", "RESULT", "#D97706", "#FFFBEB")
    if "super effective" in txt:
        return ("damage", "DAMAGE+", "#16A34A", "#F0FDF4")
    if "not very effective" in txt:
        return ("damage", "DAMAGE-", "#CA8A04", "#FEFCE8")
    if "no effect" in txt:
        return ("damage", "IMMUNE", "#6B7280", "#F3F4F6")
    return ("damage", "DAMAGE", "#0284C7", "#EFF6FF")


def build_battle_summary(log_entries: list[str], winner: str | None = None) -> str:
    """Generate a concise plain-text battle summary."""
    if not log_entries:
        return "No battle events yet."

    turns = len([e for e in log_entries if e.startswith("**Turn")])
    kos = len([e for e in log_entries if "fainted" in e.lower()])
    cheats = len([e for e in log_entries if "CHEAT ACTIVATED" in e])
    last_events = [e.replace("**", "").replace("*", "") for e in log_entries[-6:]]

    winner_line = ""
    if winner:
        winner_line = f"Winner: {winner}\n"

    summary = (
        f"{winner_line}"
        f"Turns: {turns}\n"
        f"Knockouts: {kos}\n"
        f"Cheats used: {cheats}\n"
        "\nRecent events:\n- "
        + "\n- ".join(last_events)
    )
    return summary


def render_battle_log(log_entries: list[str], title: str, key_prefix: str, height: int = 340):
    """Render styled battle log with filters and ordering."""
    st.markdown(f"### {title}")
    filter_col, order_col = st.columns([2, 1])
    with filter_col:
        selected_filter = st.selectbox(
            "Show",
            ["All", "Damage", "Turns", "KOs", "Cheats", "Results"],
            key=f"{key_prefix}_filter",
        )
    with order_col:
        newest_first = st.toggle("Newest first", value=True, key=f"{key_prefix}_newest")

    normalized = []
    for entry in log_entries:
        kind, label, accent, bg = classify_log_entry(entry)
        normalized.append(
            {
                "entry": entry,
                "kind": kind,
                "label": label,
                "accent": accent,
                "bg": bg,
            }
        )

    filter_map = {
        "All": None,
        "Damage": "damage",
        "Turns": "turn",
        "KOs": "ko",
        "Cheats": "cheat",
        "Results": "result",
    }
    target_kind = filter_map[selected_filter]
    if target_kind:
        normalized = [n for n in normalized if n["kind"] == target_kind]

    if newest_first:
        normalized = list(reversed(normalized))

    cards = []
    for item in normalized:
        clean = item["entry"].replace("**", "").replace("*", "")
        clean = html.escape(clean)
        cards.append(
            f"""
            <div style="border-left:4px solid {item['accent']}; background:{item['bg']};
                        border-radius:8px; padding:8px 10px; margin-bottom:7px;">
                <div style="font-size:0.66rem; font-weight:800; color:{item['accent']}; letter-spacing:0.3px;">
                    {item['label']}
                </div>
                <div style="font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                            font-size:0.82rem; color:#111827; white-space:pre-wrap;">
                    {clean}
                </div>
            </div>
            """
        )

    if cards:
        st.markdown(
            f"""
            <div style="height:{height}px; overflow-y:auto; padding:6px 4px 4px 0;">
                {''.join(cards)}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No log entries for this filter yet.")


def render_battle_card(p: dict, is_active: bool = False):
    """Render a battle card; all alive Pokemon are active fighters."""
    fainted = p["current_hp"] <= 0
    pct = max(0, p["current_hp"] / p["max_hp"]) if p["max_hp"] > 0 else 0
    if pct > 0.5:
        bar_color = "#4CAF50"
        bg_tint = "rgba(76,175,80,0.07)" if not fainted else "#f0f0f0"
    elif pct > 0.2:
        bar_color = "#FFC107"
        bg_tint = "rgba(255,193,7,0.08)" if not fainted else "#f0f0f0"
    else:
        bar_color = "#e63946"
        bg_tint = "rgba(230,57,70,0.07)" if not fainted else "#f0f0f0"

    if fainted:
        border_color = "#ccc"
        bg = "#f0f0f0"
        box_shadow = "none"
        glow_css = ""
    else:
        border_color = "#4A90D9"
        bg = f"linear-gradient(135deg, {bg_tint} 0%, #f8fbff 60%, #ffffff 100%)"
        box_shadow = "0 3px 12px rgba(74,144,217,0.18)"
        glow_css = (
            "animation: battleCardPulse 2.2s ease-in-out infinite;"
            if is_active else ""
        )

    opacity = "0.42" if fainted else "1"
    status_text = "Fighting" if not fainted else "Fainted"
    status_color = "#27ae60" if not fainted else "#aaa"
    status_bg = "rgba(39,174,96,0.10)" if not fainted else "rgba(170,170,170,0.12)"

    t1 = type_badge(p.get("type1", ""))
    t2_raw = p.get("type2", "")
    t2 = type_badge(t2_raw) if t2_raw else ""
    types_str = t1 + (f"&nbsp;/&nbsp;{t2}" if t2 else "")
    hp_text = f"{max(0, p['current_hp'])} / {p['max_hp']}"

    # Stat mini-indicators
    atk_val = p.get("attack", 0)
    def_val = p.get("defense", 0)
    spd_val = p.get("speed", 0)
    stat_dots = (
        f'<span style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;color:#888;">'
        f'<span title="ATK {atk_val}" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#EF6C00;"></span>'
        f'<span style="margin-right:5px;">{atk_val}</span>'
        f'<span title="DEF {def_val}" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#1E88E5;"></span>'
        f'<span style="margin-right:5px;">{def_val}</span>'
        f'<span title="SPD {spd_val}" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#43A047;"></span>'
        f'<span>{spd_val}</span>'
        f'</span>'
    )

    st.markdown(f"""
    <style>
        @keyframes battleCardPulse {{
            0%, 100% {{ box-shadow: 0 3px 12px rgba(74,144,217,0.18); }}
            50% {{ box-shadow: 0 3px 18px rgba(74,144,217,0.45), 0 0 6px rgba(74,144,217,0.20); }}
        }}
    </style>
    <div style="
        border: 2px solid {border_color};
        border-radius: 14px;
        padding: 14px 16px 12px 16px;
        background: {bg};
        opacity: {opacity};
        margin-bottom: 10px;
        box-shadow: {box_shadow};
        {glow_css}
        transition: box-shadow 0.3s, transform 0.15s;
    ">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
            <span style="font-weight:800;font-size:1.05rem;letter-spacing:-0.2px;">{p['name']}</span>
            <span style="font-size:0.68rem;font-weight:700;color:{status_color};
                background:{status_bg};border-radius:999px;padding:2px 9px;">{status_text}</span>
        </div>
        <div style="font-size:0.82rem;color:#555;margin-bottom:8px;">{types_str}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-size:0.76rem;color:#555;font-weight:600;">HP&nbsp;&nbsp;<b style="color:#333;">{hp_text}</b></span>
            <span style="font-size:0.72rem;color:#999;">{pct*100:.0f}%</span>
        </div>
        <div style="background:#e0e0e0;border-radius:8px;height:16px;width:100%;overflow:hidden;margin-bottom:8px;">
            <div style="background:linear-gradient(90deg, {bar_color}, {bar_color}dd);height:100%;width:{pct*100:.1f}%;
                border-radius:8px;transition:width 0.4s ease;"></div>
        </div>
        {stat_dots}
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page: Battle Arena
# ---------------------------------------------------------------------------

def page_battle():
    st.markdown('<div class="section-header">Pokemon Battle Arena</div>', unsafe_allow_html=True)

    # Initialize session state
    if "battle_state" not in st.session_state:
        st.session_state.battle_state = "select"  # select -> battle -> done
    if "battle_log" not in st.session_state:
        st.session_state.battle_log = []
    if "cheats_used" not in st.session_state:
        st.session_state.cheats_used = []

    all_names = get_all_pokemon_names()

    # ---- TEAM SELECTION ----
    if st.session_state.battle_state == "select":
        st.markdown('<div class="section-header">Choose Your Team</div>', unsafe_allow_html=True)

        team_size = st.selectbox("Team size", [1, 2, 3], index=0)
        stat_maxima = get_selection_stat_maxima()

        st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Your Team</div>', unsafe_allow_html=True)

        # One column per slot " selectbox + preview card together
        slot_cols = st.columns(team_size)
        selected = []
        for i in range(team_size):
            with slot_cols[i]:
                name = st.selectbox(f"Slot {i+1}", all_names, key=f"sel_{i}")
                selected.append(name)
                p = get_pokemon_by_name(name)
                if p:
                    pokemon_preview_card(p, i + 1, stat_maxima)
        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

        start_l, start_c, start_r = st.columns([1.2, 2.8, 1.2])
        with start_c:
            start_clicked = st.button("Start Battle", key="start_battle_btn", type="primary", use_container_width=True)

        if start_clicked:
            # Restore DB before new battle
            restore_pokemon_db()

            # Build player team
            player_team = []
            for n in selected:
                p = get_pokemon_by_name(n)
                if p:
                    p["current_hp"] = p["hp"]
                    p["max_hp"] = p["hp"]
                    player_team.append(p)

            # AI picks random team of same size
            ai_names = random.sample([n for n in all_names if n not in selected], len(player_team))
            ai_team = []
            for n in ai_names:
                p = get_pokemon_by_name(n)
                if p:
                    p["current_hp"] = p["hp"]
                    p["max_hp"] = p["hp"]
                    ai_team.append(p)

            st.session_state.player_team = player_team
            st.session_state.ai_team = ai_team
            st.session_state.battle_log = []
            st.session_state.cheats_used = []
            st.session_state.battle_state = "battle"
            st.session_state.scroll_to_top = True
            st.rerun()

    # ---- BATTLE ----
    elif st.session_state.battle_state == "battle":
        if st.session_state.get("scroll_to_top", False):
            components.html("""
                <script>
                    (function() {
                        var selectors = [
                            '[data-testid="stAppViewContainer"]',
                            '[data-testid="stMain"]',
                            'section[tabindex="0"]',
                            '.main',
                            'section.main',
                        ];
                        for (var i = 0; i < selectors.length; i++) {
                            var el = window.parent.document.querySelector(selectors[i]);
                            if (el) { el.scrollTop = 0; }
                        }
                        window.parent.scrollTo(0, 0);
                    })();
                </script>
            """, height=1)
            st.session_state.scroll_to_top = False

        player_team = st.session_state.player_team
        ai_team = st.session_state.ai_team

        # Determine fastest alive pokemon on each side for active glow
        _p_alive = [p for p in player_team if p["current_hp"] > 0]
        _a_alive = [p for p in ai_team if p["current_hp"] > 0]
        _p_fastest = max(_p_alive, key=lambda x: x["speed"])["name"] if _p_alive else ""
        _a_fastest = max(_a_alive, key=lambda x: x["speed"])["name"] if _a_alive else ""

        # Layout: player vs AI
        col1, col_mid, col2 = st.columns([5, 1, 5])
        with col1:
            st.markdown("###  Your Team")
            for p in player_team:
                render_battle_card(p, is_active=(p["name"] == _p_fastest))
        with col_mid:
            st.markdown(
"""<style>
@keyframes vsPulse {
    0%, 100% { transform: scale(1); text-shadow: 0 0 12px rgba(239,68,68,0.4), 0 2px 8px rgba(99,102,241,0.3); }
    50% { transform: scale(1.08); text-shadow: 0 0 24px rgba(239,68,68,0.6), 0 4px 16px rgba(99,102,241,0.5); }
}
</style>
<div style="text-align:center;padding-top:36px;">
<span style="font-size:2.6rem;font-weight:900;letter-spacing:4px;color:#EF4444;text-shadow:0 0 12px rgba(239,68,68,0.4),0 2px 8px rgba(99,102,241,0.3);animation:vsPulse 2s ease-in-out infinite;display:inline-block;">VS</span>
</div>""",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown("### AI Team")
            for p in ai_team:
                render_battle_card(p, is_active=(p["name"] == _a_fastest))

        st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)

        turn_count = len([e for e in st.session_state.battle_log if e.startswith("**Turn")])
        bar_l, bar_c, bar_r = st.columns([1.2, 2.8, 1.2])
        with bar_c:
            st.markdown(
                f"""
                <div style="
                    border:2px solid #6366F1;
                    border-radius:14px;
                    padding:12px 16px 8px 16px;
                    background:linear-gradient(135deg,#EEF2FF 0%, #F5F3FF 50%, #f9fbff 100%);
                    margin-bottom:12px;
                    box-shadow:0 2px 10px rgba(99,102,241,0.12);
                ">
                    <div style="font-size:0.68rem;font-weight:800;color:#6366F1;text-align:center;
                        text-transform:uppercase;letter-spacing:1.5px;margin-bottom:2px;">
                        Battle Controls
                    </div>
                    <div style="font-size:1.3rem;font-weight:900;color:#1E1B4B;text-align:center;">
                        Turn {turn_count}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            next_col, spacer_col, auto_col = st.columns([5, 1, 4])
            with next_col:
                next_clicked = st.button("Next Turn", key="next_turn_main", type="primary", use_container_width=True)
            with auto_col:
                auto_clicked = st.button("Auto x3", key="auto_turns_3", use_container_width=True)

        if next_clicked:
            execute_turn(player_team, ai_team)
            st.rerun()
        if auto_clicked:
            for _ in range(3):
                if st.session_state.battle_state != "battle":
                    break
                execute_turn(player_team, ai_team)
            st.rerun()
        # Cheat code input
        with st.expander("\U0001f4dc Enter Cheat Code"):
            st.markdown("Available cheats: `UPUPDOWNDOWN`, `GODMODE`, `STEAL`, `NERF`")
            cheat_input = st.text_input("Cheat Code", key="cheat_input")
            if st.button("Apply Cheat"):
                if cheat_input:
                    result = apply_cheat(cheat_input, player_team, ai_team)
                    if result:
                        st.session_state.cheats_used.append(cheat_input.strip().upper())
                        st.session_state.battle_log.append(
                            f"\U0001f3ae **CHEAT ACTIVATED**: {result}"
                        )
                        st.success(f"Cheat applied: {result}")
                        st.rerun()
                    else:
                        st.error("Invalid cheat code!")
        render_battle_log(
            st.session_state.battle_log,
            title="Battle Log",
            key_prefix="battle_live_log",
            height=320,
        )

        with st.expander("Battle Summary (copy/download)"):
            summary_txt = build_battle_summary(st.session_state.battle_log)
            st.text_area(
                "Summary Text",
                value=summary_txt,
                height=140,
                key="battle_summary_live",
            )
            st.download_button(
                "Download Summary (.txt)",
                data=summary_txt,
                file_name="pokemon_battle_summary.txt",
                mime="text/plain",
                use_container_width=True,
            )
    # ---- BATTLE DONE ----
    elif st.session_state.battle_state == "done":
        winner = st.session_state.get("winner", "player")
        if winner == "player":
            st.balloons()
            st.markdown(
                """<div style="text-align:center;padding:28px 20px;border-radius:16px;
                    background:linear-gradient(135deg,#059669 0%,#10B981 40%,#34D399 100%);
                    box-shadow:0 6px 24px rgba(16,185,129,0.3);margin-bottom:16px;">
                    <div style="font-size:2.2rem;font-weight:900;color:#fff;text-shadow:0 2px 8px rgba(0,0,0,0.2);
                        letter-spacing:1px;">YOU WIN!</div>
                    <div style="font-size:1rem;color:#D1FAE5;margin-top:4px;">Congratulations, Pokemon Master!</div>
                </div>""",
                unsafe_allow_html=True,
            )
        elif winner == "draw":
            st.markdown(
                """<div style="text-align:center;padding:28px 20px;border-radius:16px;
                    background:linear-gradient(135deg,#6366F1 0%,#818CF8 40%,#A5B4FC 100%);
                    box-shadow:0 6px 24px rgba(99,102,241,0.3);margin-bottom:16px;">
                    <div style="font-size:2.2rem;font-weight:900;color:#fff;text-shadow:0 2px 8px rgba(0,0,0,0.2);
                        letter-spacing:1px;">DRAW!</div>
                    <div style="font-size:1rem;color:#E0E7FF;margin-top:4px;">Both teams fainted at the same time!</div>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """<div style="text-align:center;padding:28px 20px;border-radius:16px;
                    background:linear-gradient(135deg,#DC2626 0%,#EF4444 40%,#F87171 100%);
                    box-shadow:0 6px 24px rgba(220,38,38,0.25);margin-bottom:16px;">
                    <div style="font-size:2.2rem;font-weight:900;color:#fff;text-shadow:0 2px 8px rgba(0,0,0,0.2);
                        letter-spacing:1px;">DEFEAT</div>
                    <div style="font-size:1rem;color:#FEE2E2;margin-top:4px;">You lost... Better luck next time!</div>
                </div>""",
                unsafe_allow_html=True,
            )
        pa_l, pa_c, pa_r = st.columns([1.2, 2.6, 1.2])
        with pa_c:
            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
            play_again_top = st.button("Play Again", key="play_again_top", type="primary", use_container_width=True)
        if play_again_top:
            st.session_state.battle_state = "select"
            st.session_state.battle_log = []
            st.session_state.cheats_used = []
            st.rerun()

        render_battle_log(
            st.session_state.battle_log,
            title="Full Battle Log",
            key_prefix="battle_done_log",
            height=420,
        )
        with st.expander("Final Battle Summary (copy/download)"):
            summary_txt = build_battle_summary(st.session_state.battle_log, winner=winner)
            st.text_area(
                "Summary Text",
                value=summary_txt,
                height=160,
                key="battle_summary_done",
            )
            st.download_button(
                "Download Final Summary (.txt)",
                data=summary_txt,
                file_name="pokemon_battle_final_summary.txt",
                mime="text/plain",
                use_container_width=True,
            )
        # Save result
        save_battle_result(
            st.session_state.player_team,
            st.session_state.ai_team,
            winner,
            st.session_state.cheats_used,
        )

        # Cheat audit
        if st.session_state.cheats_used:
            st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-header">Cheat Audit</div>', unsafe_allow_html=True)
            st.markdown(f"**Cheats used this battle:** {', '.join(st.session_state.cheats_used)}")
            audit = run_cheat_audit()
            for title, df in audit.items():
                st.markdown(f"**{title}**")
                if df.empty:
                    st.info("No anomalies detected.")
                else:
                    st.dataframe(df, use_container_width=True)

        # Restore DB
        restore_pokemon_db()

        # Battle history
        st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)
        st.markdown(
            """<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <span style="font-size:1.3rem;font-weight:800;color:#1E1B4B;">Battle History</span>
                <span style="font-size:0.7rem;font-weight:700;color:#6366F1;background:#EEF2FF;
                    border-radius:999px;padding:2px 10px;">Last 20</span>
            </div>""",
            unsafe_allow_html=True,
        )
        conn = get_conn()
        hist = pd.read_sql_query("SELECT * FROM battle_history ORDER BY id DESC LIMIT 20", conn)
        conn.close()
        if hist.empty:
            st.info("No battles yet.")
        else:
            st.dataframe(hist, use_container_width=True, hide_index=True)


def execute_turn(player_team, ai_team):
    """
    All alive Pokemon act simultaneously in Speed order.
    Each attacker targets the enemy with the best type-matchup multiplier;
    ties broken by picking the enemy with the lowest remaining HP (finish off weakest).
    """
    turn_num = len([l for l in st.session_state.battle_log if l.startswith("**Turn")]) + 1
    st.session_state.battle_log.append(f"**Turn {turn_num}**")

    # Build combatant list: (side_label, attacker, enemy_list)
    combatants = []
    for p in player_team:
        if p["current_hp"] > 0:
            combatants.append(("player", p, ai_team))
    for p in ai_team:
        if p["current_hp"] > 0:
            combatants.append(("ai", p, player_team))

    # Sort by Speed descending; shuffle first so equal-speed ties are random
    random.shuffle(combatants)
    combatants.sort(key=lambda x: x[1]["speed"], reverse=True)

    for side, attacker, enemies in combatants:
        if attacker["current_hp"] <= 0:
            continue  # was knocked out earlier this turn
        alive_enemies = [e for e in enemies if e["current_hp"] > 0]
        if not alive_enemies:
            continue

        # Target: best type-multiplier first; tie ' lowest current HP
        best_target = max(
            alive_enemies,
            key=lambda e: (
                get_type_multiplier(attacker["type1"], e["type1"], e.get("type2", "")),
                -e["current_hp"],
            ),
        )

        dmg, mult, eff_text = calc_damage(attacker, best_target)
        best_target["current_hp"] = max(0, best_target["current_hp"] - dmg)

        side_icon = "PLAYER" if side == "player" else "AI"
        mult_str = f"x{mult:.1f}"
        entry = (
            f"{side_icon} **{attacker['name']}** -> **{best_target['name']}** : "
            f"**{dmg}** dmg ({mult_str})"
        )
        if eff_text:
            entry += f" *{eff_text}*"
        st.session_state.battle_log.append(entry)

        if best_target["current_hp"] <= 0:
            st.session_state.battle_log.append(f"**{best_target['name']}** fainted!")

    # Win condition check after all attacks resolve
    player_alive = any(p["current_hp"] > 0 for p in player_team)
    ai_alive = any(p["current_hp"] > 0 for p in ai_team)

    if not player_alive and not ai_alive:
        st.session_state.battle_log.append(" **DRAW! Both teams fainted simultaneously!**")
        st.session_state.winner = "draw"
        st.session_state.battle_state = "done"
    elif not ai_alive:
        st.session_state.battle_log.append(" **PLAYER WINS THE BATTLE!**")
        st.session_state.winner = "player"
        st.session_state.battle_state = "done"
    elif not player_alive:
        st.session_state.battle_log.append(" **AI WINS THE BATTLE!**")
        st.session_state.winner = "ai"
        st.session_state.battle_state = "done"


# ---------------------------------------------------------------------------
# Page: Analysis
# ---------------------------------------------------------------------------

def page_analysis():
    st.markdown('<div class="section-header">Pokemon Analysis</div>', unsafe_allow_html=True)

    conn = get_conn()

    # --- 3.4.1 Most Overpowered Type Combination ---
    st.markdown('<div class="section-header">1. Most Overpowered Type Combinations</div>', unsafe_allow_html=True)
    st.markdown("""
    This query calculates the **average total stats** for each Type 1 + Type 2 combination
    and ranks them to find which type pairings produce the strongest Pokemon on average.
    """)

    df_types = pd.read_sql_query("""
        SELECT type1 || ' / ' || CASE WHEN type2 = '' THEN 'Pure' ELSE type2 END AS type_combo,
               ROUND(AVG(total), 1) AS avg_total,
               COUNT(*) AS count
        FROM pokemon_original
        GROUP BY type1, type2
        HAVING COUNT(*) >= 2
        ORDER BY avg_total DESC
        LIMIT 10
    """, conn)

    if not df_types.empty:
        fig1 = go.Figure()
        colors = px.colors.sequential.Viridis
        n = len(df_types)
        bar_colors = [colors[int(i / (n - 1) * (len(colors) - 1))] if n > 1 else colors[-1] for i in range(n)]

        fig1.add_trace(go.Bar(
            x=df_types["type_combo"],
            y=df_types["avg_total"],
            text=df_types.apply(lambda r: f"<b>{r['avg_total']}</b><br>{int(r['count'])} Pokémon", axis=1),
            textposition="outside",
            marker=dict(
                color=bar_colors,
                line=dict(color="rgba(0,0,0,0.15)", width=1),
                cornerradius=6,
            ),
            hovertemplate="<b>%{x}</b><br>Avg Total: %{y}<extra></extra>",
        ))
        fig1.update_layout(
            title=dict(text="Top 10 Most Overpowered Type Combinations (min 2 Pokémon)", font=dict(size=16)),
            xaxis=dict(title="Type Combination", tickangle=-40),
            yaxis=dict(title="Avg Total Stats", gridcolor="#E5E7EB"),
            height=520,
            plot_bgcolor="rgba(0,0,0,0)",
            bargap=0.25,
        )
        st.plotly_chart(fig1, use_container_width=True)

        st.markdown("""<div class="insight-box"><strong>Interpretation:</strong> Dragon-type combinations consistently dominate the top of the stat rankings. This is because Dragon-type Pokemon are designed as powerful, late-game Pokemon in the franchise. Legendary and pseudo-legendary Pokemon frequently carry Dragon typing, inflating the average. Dual-type combinations with Dragon (e.g., Dragon/Psychic, Dragon/Fire) tend to have even higher averages since these often correspond to specific powerful legendaries.</div>""", unsafe_allow_html=True)
    else:
        st.info("No data available.")

    st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)

    # --- 3.4.2 Power Creep Across Generations ---
    st.markdown('<div class="section-header">2. Power Creep Across Generations</div>', unsafe_allow_html=True)
    st.markdown("""
    This analysis examines whether later generations of Pokemon have higher base stat
    totals on average, a phenomenon known as **power creep** in game design.
    """)

    df_gen = pd.read_sql_query("""
        SELECT generation,
               ROUND(AVG(total), 1) AS avg_total,
               ROUND(AVG(hp), 1) AS avg_hp,
               ROUND(AVG(attack), 1) AS avg_attack,
               ROUND(AVG(speed), 1) AS avg_speed,
               COUNT(*) AS count
        FROM pokemon_original
        WHERE generation IS NOT NULL
        GROUP BY generation
        ORDER BY generation
    """, conn)

    if not df_gen.empty:
        fig2 = go.Figure()
        # Area fill for total stats
        fig2.add_trace(go.Scatter(
            x=df_gen["generation"], y=df_gen["avg_total"],
            mode="lines+markers+text", name="Avg Total",
            line=dict(color="#6366F1", width=3, shape="spline"),
            marker=dict(size=12, symbol="diamond", line=dict(width=2, color="white")),
            fill="tozeroy", fillcolor="rgba(99,102,241,0.08)",
            text=df_gen["avg_total"].apply(lambda x: f"{x:.0f}"),
            textposition="top center",
            textfont=dict(size=10, color="#6366F1"),
        ))
        fig2.add_trace(go.Scatter(
            x=df_gen["generation"], y=df_gen["avg_attack"],
            mode="lines+markers", name="Avg Attack",
            line=dict(color="#EF4444", width=2.5, shape="spline", dash="dot"),
            marker=dict(size=8, symbol="triangle-up"),
        ))
        fig2.add_trace(go.Scatter(
            x=df_gen["generation"], y=df_gen["avg_hp"],
            mode="lines+markers", name="Avg HP",
            line=dict(color="#10B981", width=2.5, shape="spline", dash="dot"),
            marker=dict(size=8, symbol="circle"),
        ))
        fig2.add_trace(go.Scatter(
            x=df_gen["generation"], y=df_gen["avg_speed"],
            mode="lines+markers", name="Avg Speed",
            line=dict(color="#F59E0B", width=2.5, shape="spline", dash="dot"),
            marker=dict(size=8, symbol="square"),
        ))
        # Pokemon count as bar in background
        fig2.add_trace(go.Bar(
            x=df_gen["generation"], y=df_gen["count"],
            name="# Pokémon",
            marker=dict(color="rgba(209,213,219,0.35)"),
            yaxis="y2",
            hovertemplate="Gen %{x}: %{y} Pokémon<extra></extra>",
        ))
        fig2.update_layout(
            title=dict(text="Power Creep: Average Stats Across Generations", font=dict(size=16)),
            xaxis=dict(title="Generation", dtick=1, gridcolor="#F3F4F6"),
            yaxis=dict(title="Average Stat Value", gridcolor="#E5E7EB"),
            yaxis2=dict(title="# Pokémon", overlaying="y", side="right", showgrid=False, range=[0, df_gen["count"].max() * 3]),
            height=540,
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            hovermode="x unified",
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(df_gen, use_container_width=True)

        st.markdown("""<div class="insight-box"><strong>Interpretation:</strong> The data shows a mild upward trend in average total stats across generations, suggesting <strong>moderate power creep</strong>. Generation 4 shows a notable spike, largely due to the introduction of many powerful legendaries and evolved forms of earlier Pokemon. However, the trend is not strictly linear &mdash; Game Freak balances new generations by introducing both strong and weak Pokemon. The increase in average Attack across generations is more pronounced than Speed, suggesting the franchise has leaned toward higher-damage Pokemon over time.</div>""", unsafe_allow_html=True)
    else:
        st.info("No data available.")

    conn.close()


# ---------------------------------------------------------------------------
# Page: Database Schema
# ---------------------------------------------------------------------------

def page_schema():
    st.markdown('<div class="section-header">Database Schema and Info</div>', unsafe_allow_html=True)

    conn = get_conn()

    st.markdown('<div class="section-header">Tables</div>', unsafe_allow_html=True)
    tables = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence' ORDER BY name",
        conn,
    )
    st.dataframe(tables, use_container_width=True)

    for tbl in tables["name"]:
        st.markdown(f"#### Table: `{tbl}`")
        info = pd.read_sql_query(f"PRAGMA table_info({tbl})", conn)
        st.dataframe(info[["name", "type", "pk"]], use_container_width=True)
        count = conn.execute(f"SELECT COUNT(*) FROM [{tbl}]").fetchone()[0]
        st.caption(f"Row count: {count}")

    st.markdown('<div class="section-header">Indexes</div>', unsafe_allow_html=True)
    indexes = pd.read_sql_query("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL", conn)
    st.dataframe(indexes, use_container_width=True)

    st.markdown('<div class="section-header">Sample: pokemon (first 10 rows)</div>', unsafe_allow_html=True)
    sample = pd.read_sql_query("SELECT * FROM pokemon LIMIT 10", conn)
    st.dataframe(sample, use_container_width=True)

    st.markdown('<div class="section-header">Sample: type_effectiveness (Fire matchups)</div>', unsafe_allow_html=True)
    te = pd.read_sql_query("SELECT * FROM type_effectiveness WHERE attacking_type = 'Fire'", conn)
    st.dataframe(te, use_container_width=True)

    conn.close()


def page_battle_mechanics():
    st.markdown('<div class="section-header">Battle Mechanics</div>', unsafe_allow_html=True)

    # --- Damage Formula Card ---
    st.markdown(
        """
        <div style="max-width:720px;margin:0 auto 1.5rem auto;border:2px solid #6366F1;
                    border-radius:16px;padding:1.5rem 2rem;
                    background:linear-gradient(135deg,#EEF2FF 0%,#F5F3FF 50%,#FDF4FF 100%);
                    box-shadow:0 4px 20px rgba(99,102,241,0.15);">
            <div style="text-align:center;margin-bottom:1rem;">
                <span style="font-size:1.4rem;font-weight:800;color:#4338CA;">Damage Formula</span>
                <span style="font-size:0.75rem;color:#6B7280;display:block;margin-top:2px;">Based on Pokemon Gen V simplified</span>
            </div>
            <div style="background:#1E1B4B !important;border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:1rem;text-align:center;color:#A5B4FC !important;font-family:'SF Mono',Consolas,'Courier New',monospace;font-size:0.88rem;line-height:2;">
                <span style="color:#C4B5FD !important;">base</span><span style="color:#A5B4FC !important;"> = ((</span><span style="color:#FDE68A !important;">2</span><span style="color:#A5B4FC !important;">×</span><span style="color:#FDE68A !important;">Level</span><span style="color:#A5B4FC !important;">/</span><span style="color:#FDE68A !important;">5</span><span style="color:#A5B4FC !important;"> + </span><span style="color:#FDE68A !important;">2</span><span style="color:#A5B4FC !important;">) × </span><span style="color:#93C5FD !important;">Power</span><span style="color:#A5B4FC !important;"> × </span><span style="color:#6EE7B7 !important;">A</span><span style="color:#A5B4FC !important;">/</span><span style="color:#FCA5A5 !important;">D</span><span style="color:#A5B4FC !important;">) / </span><span style="color:#FDE68A !important;">50</span><span style="color:#A5B4FC !important;"> + </span><span style="color:#FDE68A !important;">2</span><br>
                <span style="color:#C4B5FD !important;">damage</span><span style="color:#A5B4FC !important;"> = </span><span style="color:#C4B5FD !important;">base</span><span style="color:#A5B4FC !important;"> × </span><span style="color:#F9A8D4 !important;">type_mult</span><span style="color:#A5B4FC !important;"> × </span><span style="color:#D1D5DB !important;">rand</span><span style="color:#A5B4FC !important;">(</span><span style="color:#FDE68A !important;">0.85</span><span style="color:#A5B4FC !important;">, </span><span style="color:#FDE68A !important;">1.0</span><span style="color:#A5B4FC !important;">)</span>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.82rem;color:#374151;">
                <div style="background:rgba(255,255,255,0.85);border-radius:8px;padding:8px 10px;border:1px solid #E5E7EB;">
                    <span style="color:#059669;font-weight:700;">A</span> = max(Attack, Sp.Atk) of attacker
                </div>
                <div style="background:rgba(255,255,255,0.85);border-radius:8px;padding:8px 10px;border:1px solid #E5E7EB;">
                    <span style="color:#DC2626;font-weight:700;">D</span> = Defense or Sp.Def (matching A)
                </div>
                <div style="background:rgba(255,255,255,0.85);border-radius:8px;padding:8px 10px;border:1px solid #E5E7EB;">
                    <span style="color:#B45309;font-weight:700;">Level</span> = 50 &nbsp;|&nbsp; <span style="color:#2563EB;font-weight:700;">Power</span> = 60
                </div>
                <div style="background:rgba(255,255,255,0.85);border-radius:8px;padding:8px 10px;border:1px solid #E5E7EB;">
                    <span style="color:#DB2777;font-weight:700;">type_mult</span> = Type1 vs Type1 &times; Type2
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Turn Order & Effectiveness Cards ---
    col_turn, col_eff = st.columns(2)
    with col_turn:
        st.markdown(
            """
            <div style="border:1px solid #D1D5DB;border-radius:14px;padding:1.2rem;
                        background:linear-gradient(135deg,#F0FDF4 0%,#ECFDF5 100%);height:100%;">
                <div style="font-size:1.1rem;font-weight:700;color:#065F46;margin-bottom:0.8rem;text-align:center;">
                    Turn Order
                </div>
                <div style="font-size:0.85rem;color:#374151;line-height:1.7;">
                    <div style="background:rgba(255,255,255,0.7);border-radius:8px;padding:6px 10px;margin-bottom:6px;">
                        <b>1.</b> All alive Pokemon act each turn
                    </div>
                    <div style="background:rgba(255,255,255,0.7);border-radius:8px;padding:6px 10px;margin-bottom:6px;">
                        <b>2.</b> Sorted by <b>Speed</b> (highest first)
                    </div>
                    <div style="background:rgba(255,255,255,0.7);border-radius:8px;padding:6px 10px;margin-bottom:6px;">
                        <b>3.</b> Equal speed → random order
                    </div>
                    <div style="background:rgba(255,255,255,0.7);border-radius:8px;padding:6px 10px;">
                        <b>4.</b> Target = best type matchup, then lowest HP
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_eff:
        st.markdown(
            """
            <div style="border:1px solid #D1D5DB;border-radius:14px;padding:1.2rem;
                        background:linear-gradient(135deg,#FEF3C7 0%,#FFFBEB 100%);height:100%;">
                <div style="font-size:1.1rem;font-weight:700;color:#92400E;margin-bottom:0.8rem;text-align:center;">
                    Type Effectiveness
                </div>
                <div style="font-size:0.85rem;color:#374151;line-height:1.7;">
                    <div style="background:rgba(16,185,129,0.15);border-radius:8px;padding:6px 10px;margin-bottom:6px;">
                        <b style="color:#059669;">×2.0</b> — Super effective! 💥
                    </div>
                    <div style="background:rgba(255,255,255,0.7);border-radius:8px;padding:6px 10px;margin-bottom:6px;">
                        <b style="color:#6B7280;">×1.0</b> — Normal damage
                    </div>
                    <div style="background:rgba(234,179,8,0.15);border-radius:8px;padding:6px 10px;margin-bottom:6px;">
                        <b style="color:#D97706;">×0.5</b> — Not very effective...
                    </div>
                    <div style="background:rgba(239,68,68,0.12);border-radius:8px;padding:6px 10px;">
                        <b style="color:#DC2626;">×0.0</b> — No effect (immune) 🛡️
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

    # --- Interactive Type Effectiveness Heatmap ---
    st.markdown('<div class="section-header">Full 18x18 Type Effectiveness Chart</div>', unsafe_allow_html=True)

    # Build the matrix from TYPE_CHART
    types = ALL_TYPES
    matrix = []
    for atk in types:
        row = []
        for dfn in types:
            row.append(TYPE_CHART.get(atk, {}).get(dfn, 1.0))
        matrix.append(row)

    type_labels = [f"{TYPE_EMOJIS.get(t, '')} {t}" for t in types]

    # Custom colorscale: red(0) -> orange(0.5) -> white(1.0) -> green(2.0)
    colorscale = [
        [0.0, "#1F2937"],     # 0.0 - immune (dark)
        [0.25, "#EF4444"],    # 0.5 - not very effective (red)
        [0.5, "#FFFFFF"],     # 1.0 - normal (white)
        [1.0, "#10B981"],     # 2.0 - super effective (green)
    ]

    # Annotation text
    annotations_text = []
    for row in matrix:
        text_row = []
        for val in row:
            if val == 0.0:
                text_row.append("0")
            elif val == 0.5:
                text_row.append("½")
            elif val == 1.0:
                text_row.append("")
            elif val == 2.0:
                text_row.append("2")
            else:
                text_row.append(str(val))
        annotations_text.append(text_row)

    fig_heatmap = go.Figure(data=go.Heatmap(
        z=matrix,
        x=type_labels,
        y=type_labels,
        text=annotations_text,
        texttemplate="%{text}",
        textfont={"size": 11, "color": "#111827"},
        colorscale=colorscale,
        zmin=0,
        zmax=2,
        hovertemplate="<b>%{y}</b> → %{x}<br>Multiplier: <b>%{z}×</b><extra></extra>",
        colorbar=dict(
            title="Multiplier",
            tickvals=[0, 0.5, 1.0, 2.0],
            ticktext=["0× Immune", "0.5× Weak", "1× Normal", "2× Super"],
            len=0.6,
        ),
    ))

    fig_heatmap.update_layout(
        title=dict(text="Attacking Type (row) → Defending Type (column)", font=dict(size=14)),
        xaxis=dict(title="Defending Type", tickangle=-45, side="bottom", dtick=1),
        yaxis=dict(title="Attacking Type", autorange="reversed", dtick=1),
        height=700,
        width=900,
        margin=dict(l=120, r=40, t=60, b=120),
    )

    st.plotly_chart(fig_heatmap, use_container_width=True)

    # --- Damage Calculator ---
    st.markdown('<div style="border-top:1px solid #E5E7EB;margin:1.5rem 0;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Damage Calculator</div>', unsafe_allow_html=True)
    st.markdown("Pick two Pokemon and see the calculated damage for one attack.")

    all_names = get_all_pokemon_names()
    calc_col1, calc_col2 = st.columns(2)
    with calc_col1:
        atk_name = st.selectbox("Attacker", all_names, key="calc_atk")
    with calc_col2:
        def_name = st.selectbox("Defender", all_names, index=min(1, len(all_names) - 1), key="calc_def")

    if st.button("Calculate Damage", type="primary"):
        attacker = get_pokemon_by_name(atk_name)
        defender = get_pokemon_by_name(def_name)
        if attacker and defender:
            # Determine A/D
            if attacker["sp_atk"] > attacker["attack"]:
                a_val, a_label = attacker["sp_atk"], "Sp.Atk"
                d_val, d_label = defender["sp_def"], "Sp.Def"
            else:
                a_val, a_label = attacker["attack"], "Attack"
                d_val, d_label = defender["defense"], "Defense"
            if d_val == 0:
                d_val = 1

            type_mult = get_type_multiplier(attacker["type1"], defender["type1"], defender.get("type2", ""))
            base = ((2 * 50 / 5 + 2) * 60 * (a_val / d_val)) / 50 + 2
            dmg_min = int(base * type_mult * 0.85)
            dmg_max = int(base * type_mult * 1.0)

            if type_mult == 0:
                eff_color, eff_text = "#DC2626", "No effect! (Immune)"
            elif type_mult >= 2:
                eff_color, eff_text = "#059669", f"Super effective! (×{type_mult})"
            elif type_mult > 1:
                eff_color, eff_text = "#059669", f"Super effective! (×{type_mult})"
            elif type_mult < 1:
                eff_color, eff_text = "#D97706", f"Not very effective (×{type_mult})"
            else:
                eff_color, eff_text = "#6B7280", "Normal (×1.0)"

            r1, r2, r3 = st.columns(3)
            with r1:
                st.markdown(
                    f"""<div style="border:1px solid #d1d5db;border-radius:12px;padding:1rem;
                    background:#F0FDF4;text-align:center;">
                    <div style="font-size:0.75rem;color:#6B7280;">Attacker</div>
                    <div style="font-size:1.1rem;font-weight:700;">{attacker['name']}</div>
                    <div style="font-size:0.82rem;color:#555;">{type_badge(attacker['type1'])}</div>
                    <div style="font-size:0.82rem;margin-top:4px;">{a_label}: <b>{a_val}</b></div>
                    </div>""", unsafe_allow_html=True)
            with r2:
                st.markdown(
                    f"""<div style="border:2px solid {eff_color};border-radius:12px;padding:1rem;
                    background:#FAFAFA;text-align:center;">
                    <div style="font-size:0.75rem;color:#6B7280;">Damage Range</div>
                    <div style="font-size:1.6rem;font-weight:800;color:{eff_color};">{dmg_min} – {dmg_max}</div>
                    <div style="font-size:0.82rem;color:{eff_color};font-weight:600;">{eff_text}</div>
                    </div>""", unsafe_allow_html=True)
            with r3:
                st.markdown(
                    f"""<div style="border:1px solid #d1d5db;border-radius:12px;padding:1rem;
                    background:#FEF2F2;text-align:center;">
                    <div style="font-size:0.75rem;color:#6B7280;">Defender</div>
                    <div style="font-size:1.1rem;font-weight:700;">{defender['name']}</div>
                    <div style="font-size:0.82rem;color:#555;">{type_badge(defender['type1'])}</div>
                    <div style="font-size:0.82rem;margin-top:4px;">{d_label}: <b>{d_val}</b> | HP: <b>{defender['hp']}</b></div>
                    </div>""", unsafe_allow_html=True)
# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Pokemon Battle Arena",
        page_icon="",
        layout="wide",
    )

    st.markdown(
        """
<div class="sticky-page-header">
  <div class="sticky-page-title">Pokemon Battle Arena</div>
  <div class="sticky-page-subtitle">Battle, analyze, and explore Pokemon data with SQL</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Initialize DB (runs once per server session, cached)
    _init_db_once()

    # Navigation
    tab1, tab2, tab3, tab4 = st.tabs([
        "Battle Arena",
        "Analysis",
        "Schema & Data",
        "Battle Mechanics",
    ])

    with tab1:
        page_battle()
    with tab2:
        page_analysis()
    with tab3:
        page_schema()
    with tab4:
        page_battle_mechanics()

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
            "This app loads the [Pokemon dataset]"
            "(https://www.kaggle.com/datasets/abcsds/pokemon) "
            "into **SQLite** and runs a data-driven battle arena with team selection, "
            "type effectiveness, cheat-code SQL writes, and post-battle analysis."
        )
if __name__ == "__main__":
    main()
