import json
import os
import sqlite3
from datetime import datetime, timezone

import config

_CONN = None


def _get_conn():
    global _CONN
    if _CONN is None:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        _CONN = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
        _CONN.execute("PRAGMA journal_mode=WAL")
        _init_schema(_CONN)
    return _CONN


def _init_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS players (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            mmr INTEGER NOT NULL DEFAULT 1000,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            team1 TEXT NOT NULL,
            team2 TEXT NOT NULL,
            score1 INTEGER,
            score2 INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            reported_by INTEGER,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            guild_id INTEGER PRIMARY KEY,
            ping_role_id INTEGER,
            queue_channel_id INTEGER,
            base_mmr INTEGER NOT NULL DEFAULT 1000,
            role_mmr TEXT NOT NULL DEFAULT '{}',
            queue_timeout INTEGER NOT NULL DEFAULT 45
        );

        CREATE TABLE IF NOT EXISTS rl_links (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            username TEXT NOT NULL,
            PRIMARY KEY (guild_id, user_id)
        );
        """
    )

    # Migrate older databases that lack the base_mmr column
    cols = [r[1] for r in conn.execute("PRAGMA table_info(settings)").fetchall()]
    if "base_mmr" not in cols:
        conn.execute("ALTER TABLE settings ADD COLUMN base_mmr INTEGER NOT NULL DEFAULT 1000")
    if "role_mmr" not in cols:
        conn.execute("ALTER TABLE settings ADD COLUMN role_mmr TEXT NOT NULL DEFAULT '{}'")
    if "queue_timeout" not in cols:
        conn.execute("ALTER TABLE settings ADD COLUMN queue_timeout INTEGER NOT NULL DEFAULT 45")

    conn.commit()


def _ensure_player(conn, guild_id, user_id):
    conn.execute(
        "INSERT OR IGNORE INTO players (guild_id, user_id, mmr) "
        "SELECT ?, ?, COALESCE((SELECT base_mmr FROM settings WHERE guild_id = ?), 1000)",
        (guild_id, user_id, guild_id),
    )


def _decode_teams(row):
    d = dict(row)
    d["team1"] = json.loads(d["team1"])
    d["team2"] = json.loads(d["team2"])
    return d


# ---- Players ---------------------------------------------------------


def get_player(guild_id, user_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM players WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ).fetchone()
    if row:
        p = dict(row)
        p["is_new"] = False
        return p
    base = get_base_mmr(guild_id)
    return {"guild_id": guild_id, "user_id": user_id, "mmr": base, "wins": 0, "losses": 0, "is_new": True}


def update_player(guild_id, user_id, *, mmr_new, won):
    conn = _get_conn()
    _ensure_player(conn, guild_id, user_id)
    if won:
        conn.execute(
            "UPDATE players SET mmr = ?, wins = wins + 1 WHERE guild_id = ? AND user_id = ?",
            (mmr_new, guild_id, user_id),
        )
    else:
        conn.execute(
            "UPDATE players SET mmr = ?, losses = losses + 1 WHERE guild_id = ? AND user_id = ?",
            (mmr_new, guild_id, user_id),
        )
    conn.commit()


def set_player_mmr(guild_id, user_id, mmr):
    conn = _get_conn()
    _ensure_player(conn, guild_id, user_id)
    conn.execute(
        "UPDATE players SET mmr = ? WHERE guild_id = ? AND user_id = ?",
        (mmr, guild_id, user_id),
    )
    conn.commit()


def set_all_players_mmr(guild_id, mmr):
    conn = _get_conn()
    conn.execute(
        "UPDATE players SET mmr = ? WHERE guild_id = ?",
        (mmr, guild_id),
    )
    conn.commit()


def leaderboard(guild_id, limit=10):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM players WHERE guild_id = ? ORDER BY mmr DESC LIMIT ?",
        (guild_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ---- Settings --------------------------------------------------------


def set_ping_role(guild_id, role_id):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO settings (guild_id, ping_role_id) VALUES (?, ?) "
        "ON CONFLICT(guild_id) DO UPDATE SET ping_role_id = excluded.ping_role_id",
        (guild_id, role_id),
    )
    conn.commit()


def get_ping_role(guild_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT ping_role_id FROM settings WHERE guild_id = ?", (guild_id,)
    ).fetchone()
    return row["ping_role_id"] if row else None


def set_queue_channel(guild_id, channel_id):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO settings (guild_id, queue_channel_id) VALUES (?, ?) "
        "ON CONFLICT(guild_id) DO UPDATE SET queue_channel_id = excluded.queue_channel_id",
        (guild_id, channel_id),
    )
    conn.commit()


def get_queue_channel(guild_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT queue_channel_id FROM settings WHERE guild_id = ?", (guild_id,)
    ).fetchone()
    return row["queue_channel_id"] if row else None


def set_queue_timeout(guild_id, minutes):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO settings (guild_id, queue_timeout) VALUES (?, ?) "
        "ON CONFLICT(guild_id) DO UPDATE SET queue_timeout = excluded.queue_timeout",
        (guild_id, minutes),
    )
    conn.commit()


def get_queue_timeout(guild_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT queue_timeout FROM settings WHERE guild_id = ?", (guild_id,)
    ).fetchone()
    return row["queue_timeout"] if row else 45


def set_base_mmr(guild_id, mmr):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO settings (guild_id, base_mmr) VALUES (?, ?) "
        "ON CONFLICT(guild_id) DO UPDATE SET base_mmr = excluded.base_mmr",
        (guild_id, mmr),
    )
    conn.commit()


def get_base_mmr(guild_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT base_mmr FROM settings WHERE guild_id = ?", (guild_id,)
    ).fetchone()
    return row["base_mmr"] if row else 1000


def set_role_mmr(guild_id, role_id, mmr):
    conn = _get_conn()
    row = conn.execute(
        "SELECT role_mmr FROM settings WHERE guild_id = ?", (guild_id,)
    ).fetchone()
    role_mmr = json.loads(row["role_mmr"]) if row and row["role_mmr"] else {}
    if mmr is None:
        role_mmr.pop(str(role_id), None)
    else:
        role_mmr[str(role_id)] = mmr
    conn.execute(
        "INSERT INTO settings (guild_id, role_mmr) VALUES (?, ?) "
        "ON CONFLICT(guild_id) DO UPDATE SET role_mmr = excluded.role_mmr",
        (guild_id, json.dumps(role_mmr)),
    )
    conn.commit()


def get_role_mmr_map(guild_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT role_mmr FROM settings WHERE guild_id = ?", (guild_id,)
    ).fetchone()
    if not row or not row["role_mmr"]:
        return {}
    return {int(k): v for k, v in json.loads(row["role_mmr"]).items()}


def get_effective_mmr(guild_id, role_ids):
    """Return the highest role-based MMR for a player's roles, or None."""
    role_map = get_role_mmr_map(guild_id)
    if not role_map:
        return None
    best = None
    for rid in role_ids:
        if rid in role_map:
            best = max(best, role_map[rid]) if best is not None else role_map[rid]
    return best


# ---- Matches ---------------------------------------------------------


def create_match(guild_id, team1_ids, team2_ids):
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO matches (guild_id, team1, team2, created_at) VALUES (?, ?, ?, ?)",
        (
            guild_id,
            json.dumps(team1_ids),
            json.dumps(team2_ids),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_pending_match_for_user(guild_id, user_id):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM matches WHERE guild_id = ? AND status = 'pending' ORDER BY id DESC",
        (guild_id,),
    ).fetchall()
    for row in rows:
        d = _decode_teams(row)
        if user_id in d["team1"] or user_id in d["team2"]:
            return d
    return None


def get_active_matches(guild_id):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM matches WHERE guild_id = ? AND status = 'pending' ORDER BY id DESC",
        (guild_id,),
    ).fetchall()
    return [_decode_teams(r) for r in rows]


def report_match(match_id, score1, score2, reported_by):
    conn = _get_conn()
    cur = conn.execute(
        "UPDATE matches SET score1 = ?, score2 = ?, status = 'reported', reported_by = ? "
        "WHERE id = ? AND status = 'pending'",
        (score1, score2, reported_by, match_id),
    )
    conn.commit()
    return cur.rowcount == 1


# ---- RL Tracker links -------------------------------------------------


def set_rl_link(guild_id, user_id, platform, username):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO rl_links (guild_id, user_id, platform, username) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(guild_id, user_id) DO UPDATE SET platform = excluded.platform, "
        "username = excluded.username",
        (guild_id, user_id, platform, username),
    )
    conn.commit()


def get_rl_link(guild_id, user_id):
    conn = _get_conn()
    row = conn.execute(
        "SELECT platform, username FROM rl_links WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id),
    ).fetchone()
    return dict(row) if row else None


def clear_rl_link(guild_id, user_id):
    conn = _get_conn()
    conn.execute(
        "DELETE FROM rl_links WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
    )
    conn.commit()
