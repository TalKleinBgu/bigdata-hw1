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

def get_conn():
    """Return a SQLite connection (cached per session to avoid re-opening)."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


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

    conn.close()


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
        stat_bar("HP", "hp", "#2E7D32")
        + stat_bar("ATK", "attack", "#EF6C00")
        + stat_bar("DEF", "defense", "#F9A825")
        + stat_bar("SpA", "sp_atk", "#8E24AA")
        + stat_bar("SpD", "sp_def", "#1E88E5")
        + stat_bar("SPD", "speed", "#43A047")
        + stat_bar("TOTAL", "total", "#1565C0")
    )

    st.markdown(
        f"""
        <div style="
            border: 1px solid #d6dde8;
            border-radius: 10px;
            padding: 10px 10px 8px 10px;
            background: var(--secondary-background-color, #f2f4f8);
            margin-top: 6px;
        ">
            <div style="font-size:0.68rem;font-weight:700;color:#1f3a56;
                background:#dbe4f0;border-radius:999px;padding:1px 8px;
                display:inline-block;margin-bottom:6px;">Slot {slot_num}</div>
            <div style="font-size:0.95rem;font-weight:800;margin-bottom:3px;">{p['name']}</div>
            <div style="font-size:0.80rem;margin-bottom:8px;color:#444;">{types_str}</div>
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


def render_battle_card(p: dict):
    """Render a battle card; all alive Pokémon are active fighters."""
    fainted = p["current_hp"] <= 0
    pct = max(0, p["current_hp"] / p["max_hp"]) if p["max_hp"] > 0 else 0
    if pct > 0.5:
        bar_color = "#4CAF50"
    elif pct > 0.2:
        bar_color = "#FFC107"
    else:
        bar_color = "#e67e22"

    border_color = "#4A90D9" if not fainted else "#ccc"
    bg = "linear-gradient(135deg,#e8f4fd 0%,#f8fbff 100%)" if not fainted else "#f0f0f0"
    opacity = "0.42" if fainted else "1"
    status_text = "⚔️ Fighting" if not fainted else "💀 Fainted"
    status_color = "#27ae60" if not fainted else "#aaa"

    t1 = type_badge(p.get("type1", ""))
    t2_raw = p.get("type2", "")
    t2 = type_badge(t2_raw) if t2_raw else ""
    types_str = t1 + (f"&nbsp;/&nbsp;{t2}" if t2 else "")
    hp_text = f"{max(0, p['current_hp'])} / {p['max_hp']}"

    st.markdown(f"""
    <div style="
        border: 2px solid {border_color};
        border-radius: 12px;
        padding: 12px 14px;
        background: {bg};
        opacity: {opacity};
        margin-bottom: 8px;
        box-shadow: {'0 3px 10px rgba(74,144,217,0.20)' if not fainted else 'none'};
    ">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-weight:800;font-size:1rem;">{p['name']}</span>
            <span style="font-size:0.72rem;font-weight:700;color:{status_color};">{status_text}</span>
        </div>
        <div style="font-size:0.82rem;color:#555;margin-bottom:8px;">{types_str}</div>
        <div style="font-size:0.78rem;color:#666;margin-bottom:4px;">HP:&nbsp;<b>{hp_text}</b></div>
        <div style="background:#ddd;border-radius:6px;height:14px;width:100%;overflow:hidden;">
            <div style="background:{bar_color};height:100%;width:{pct*100:.1f}%;border-radius:6px;transition:width 0.3s;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page: Battle Arena
# ---------------------------------------------------------------------------

def page_battle():
    st.header("\U0001f3df\ufe0f Pokemon Battle Arena")

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
        st.subheader("Choose Your Team")

        team_size = st.selectbox("Team size", [1, 2, 3], index=0)
        stat_maxima = get_selection_stat_maxima()

        st.markdown("---")
        st.subheader("Your Team")

        # One column per slot — selectbox + preview card together
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

        # Layout: player vs AI
        col1, col_mid, col2 = st.columns([5, 1, 5])
        with col1:
            st.markdown("### 🟢 Your Team")
            for p in player_team:
                render_battle_card(p)
        with col_mid:
            st.markdown(
                "<div style='text-align:center;font-size:1.8rem;font-weight:900;"
                "padding-top:40px;color:#555;'>VS</div>",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown("### 🔵 AI Team")
            for p in ai_team:
                render_battle_card(p)

        st.markdown("---")

        turn_count = len([e for e in st.session_state.battle_log if e.startswith("**Turn")])
        bar_l, bar_c, bar_r = st.columns([1.2, 2.8, 1.2])
        with bar_c:
            st.markdown(
                f"""
                <div style="
                    border:1px solid #d8e0ec;
                    border-radius:12px;
                    padding:10px 12px;
                    background:linear-gradient(180deg,#f9fbff 0%, #f1f5fb 100%);
                    margin-bottom:10px;
                ">
                    <div style="font-size:0.75rem;font-weight:800;color:#334155;text-align:center;margin-bottom:6px;">
                        Battle Controls · Turn {turn_count}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            next_col, auto_col = st.columns(2)
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
            st.success("🏆 YOU WIN! Congratulations, Pokemon Master!")
        elif winner == "draw":
            st.info("🤝 DRAW! Both teams fainted at the same time!")
        else:
            st.markdown(
                '<div style="padding:12px 16px;border-radius:8px;background:#f0f0f0;'
                'border:1px solid #ccc;font-size:1.05rem;">😞 You lost... Better luck next time!</div>',
                unsafe_allow_html=True,
            )
        pa_l, pa_c, pa_r = st.columns([1.4, 2.2, 1.4])
        with pa_c:
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
            st.markdown("---")
            st.subheader("\U0001f50d Cheat Audit")
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
        st.markdown("---")
        st.subheader("\U0001f4ca Battle History")
        conn = get_conn()
        hist = pd.read_sql_query("SELECT * FROM battle_history ORDER BY id DESC LIMIT 20", conn)
        conn.close()
        if hist.empty:
            st.info("No battles yet.")
        else:
            st.dataframe(hist, use_container_width=True)


def execute_turn(player_team, ai_team):
    """
    All alive Pokémon act simultaneously in Speed order.
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

        # Target: best type-multiplier first; tie → lowest current HP
        best_target = max(
            alive_enemies,
            key=lambda e: (
                get_type_multiplier(attacker["type1"], e["type1"], e.get("type2", "")),
                -e["current_hp"],
            ),
        )

        dmg, mult, eff_text = calc_damage(attacker, best_target)
        best_target["current_hp"] = max(0, best_target["current_hp"] - dmg)

        side_icon = "🟢" if side == "player" else "🔵"
        mult_str = f"×{mult:.1f}"
        entry = (
            f"{side_icon} **{attacker['name']}** → **{best_target['name']}** : "
            f"**{dmg}** dmg ({mult_str})"
        )
        if eff_text:
            entry += f" *{eff_text}*"
        st.session_state.battle_log.append(entry)

        if best_target["current_hp"] <= 0:
            st.session_state.battle_log.append(f"💥 **{best_target['name']}** fainted!")

    # Win condition check after all attacks resolve
    player_alive = any(p["current_hp"] > 0 for p in player_team)
    ai_alive = any(p["current_hp"] > 0 for p in ai_team)

    if not player_alive and not ai_alive:
        st.session_state.battle_log.append("🤝 **DRAW! Both teams fainted simultaneously!**")
        st.session_state.winner = "draw"
        st.session_state.battle_state = "done"
    elif not ai_alive:
        st.session_state.battle_log.append("🏆 **PLAYER WINS THE BATTLE!**")
        st.session_state.winner = "player"
        st.session_state.battle_state = "done"
    elif not player_alive:
        st.session_state.battle_log.append("🏆 **AI WINS THE BATTLE!**")
        st.session_state.winner = "ai"
        st.session_state.battle_state = "done"


# ---------------------------------------------------------------------------
# Page: Analysis
# ---------------------------------------------------------------------------

def page_analysis():
    st.header("\U0001f4ca Pokemon Analysis")

    conn = get_conn()

    # --- 3.4.1 Most Overpowered Type Combination ---
    st.subheader("1. Most Overpowered Type Combinations")
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
        fig1 = px.bar(
            df_types, x="type_combo", y="avg_total",
            color="avg_total",
            color_continuous_scale="Viridis",
            text="avg_total",
            labels={"type_combo": "Type Combination", "avg_total": "Avg Total Stats"},
            title="Top 10 Most Overpowered Type Combinations (min 2 Pokemon)",
        )
        fig1.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig1, use_container_width=True)

        st.markdown("""
        **Interpretation:** Dragon-type combinations consistently dominate the top of the
        stat rankings. This is because Dragon-type Pokemon are designed as powerful,
        late-game Pokemon in the franchise. Legendary and pseudo-legendary Pokemon
        frequently carry Dragon typing, inflating the average. Dual-type combinations
        with Dragon (e.g., Dragon/Psychic, Dragon/Fire) tend to have even higher
        averages since these often correspond to specific powerful legendaries.
        """)
    else:
        st.info("No data available.")

    st.markdown("---")

    # --- 3.4.2 Power Creep Across Generations ---
    st.subheader("2. Power Creep Across Generations")
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
        fig2.add_trace(go.Scatter(
            x=df_gen["generation"], y=df_gen["avg_total"],
            mode="lines+markers", name="Avg Total",
            line=dict(color="#FF6347", width=3), marker=dict(size=10)
        ))
        fig2.add_trace(go.Scatter(
            x=df_gen["generation"], y=df_gen["avg_attack"],
            mode="lines+markers", name="Avg Attack",
            line=dict(color="#4FC3F7", width=2), marker=dict(size=7)
        ))
        fig2.add_trace(go.Scatter(
            x=df_gen["generation"], y=df_gen["avg_speed"],
            mode="lines+markers", name="Avg Speed",
            line=dict(color="#81C784", width=2), marker=dict(size=7)
        ))
        fig2.update_layout(
            title="Average Stats Across Generations",
            xaxis_title="Generation",
            yaxis_title="Average Stat Value",
            height=500,
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(df_gen, use_container_width=True)

        st.markdown("""
        **Interpretation:** The data shows a mild upward trend in average total stats
        across generations, suggesting **moderate power creep**. Generation 4 shows a
        notable spike, largely due to the introduction of many powerful legendaries and
        evolved forms of earlier Pokemon. However, the trend is not strictly linear --
        Game Freak balances new generations by introducing both strong and weak Pokemon.
        The increase in average Attack across generations is more pronounced than Speed,
        suggesting the franchise has leaned toward higher-damage Pokemon over time.
        """)
    else:
        st.info("No data available.")

    conn.close()


# ---------------------------------------------------------------------------
# Page: Database Schema
# ---------------------------------------------------------------------------

def page_schema():
    st.header("\U0001f5c4\ufe0f Database Schema & Info")

    conn = get_conn()

    st.subheader("Tables")
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

    st.subheader("Indexes")
    indexes = pd.read_sql_query("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL", conn)
    st.dataframe(indexes, use_container_width=True)

    st.subheader("Sample: pokemon (first 10 rows)")
    sample = pd.read_sql_query("SELECT * FROM pokemon LIMIT 10", conn)
    st.dataframe(sample, use_container_width=True)

    st.subheader("Sample: type_effectiveness (Fire matchups)")
    te = pd.read_sql_query("SELECT * FROM type_effectiveness WHERE attacking_type = 'Fire'", conn)
    st.dataframe(te, use_container_width=True)

    conn.close()


def page_battle_mechanics():
    st.header("📖 Battle Mechanics")
    st.markdown(
        """
        **Damage Formula:**
        ```
        base = ((2*50/5 + 2) * 60 * (A/D)) / 50 + 2
        damage = base * type_mult * rand(0.85, 1.0)
        ```

        Where:
        - **A** = max(Attack, Sp.Atk) of attacker
        - **D** = Defense or Sp.Def of defender (matching A)
        - **type_mult** = product of type effectiveness for attacker's Type1 vs defender's Type1 and Type2

        **Turn Order:** Higher Speed goes first. Ties broken randomly.

        **Type Effectiveness:**
        - x2.0 = Super effective!
        - x1.0 = Normal
        - x0.5 = Not very effective...
        - x0.0 = No effect (immune)
        """
    )

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Pokemon Battle Arena",
        page_icon="⚔️",
        layout="wide",
    )

    st.title("⚔️ Pokemon Battle Arena")
    st.caption("Big Data Homework 1 -- Task 3")

    # Initialize DB
    with st.spinner("Initializing database..."):
        init_database()

    # Navigation
    tab1, tab2, tab3, tab4 = st.tabs([
        "⚔️ Battle Arena",
        "📊 Analysis",
        "🗄️ Schema & Data",
        "📖 Battle Mechanics",
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
section[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem !important; }
[data-testid="stSidebarContent"] { padding-top: 0.5rem !important; }
</style>
""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## 🎮 Cheat Codes")
        for code, desc in CHEAT_DESCRIPTIONS.items():
            st.markdown(f"- `{code}`: {desc}")
if __name__ == "__main__":
    main()
