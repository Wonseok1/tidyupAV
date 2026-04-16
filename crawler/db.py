"""SQLite DB 관리"""
import sqlite3
from pathlib import Path
from typing import Optional
from .models import Actress, Video

DB_PATH = Path(__file__).parent.parent / "data" / "javdb.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """테이블 초기화"""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS actresses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            javdb_id    TEXT    UNIQUE NOT NULL,
            name        TEXT    NOT NULL,
            name_ja     TEXT,
            name_en     TEXT,
            aliases     TEXT,           -- JSON array string
            avatar_url  TEXT,
            fetched_at  TEXT            -- ISO8601
        );

        CREATE TABLE IF NOT EXISTS videos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            code         TEXT    UNIQUE NOT NULL,
            javdb_id     TEXT    UNIQUE,
            title        TEXT,
            release_date TEXT,
            duration     INTEGER,
            cover_url    TEXT,
            fetched_at   TEXT
        );

        CREATE TABLE IF NOT EXISTS actress_videos (
            actress_id  INTEGER NOT NULL REFERENCES actresses(id) ON DELETE CASCADE,
            video_id    INTEGER NOT NULL REFERENCES videos(id)    ON DELETE CASCADE,
            PRIMARY KEY (actress_id, video_id)
        );

        CREATE INDEX IF NOT EXISTS idx_videos_code      ON videos(code);
        CREATE INDEX IF NOT EXISTS idx_actresses_name   ON actresses(name);
        CREATE INDEX IF NOT EXISTS idx_actresses_javdb  ON actresses(javdb_id);
        """)


# ── Actress CRUD ──────────────────────────────────────────────────────────────

def upsert_actress(conn: sqlite3.Connection, a: Actress) -> int:
    import json, datetime
    aliases_json = json.dumps(a.aliases, ensure_ascii=False)
    now = datetime.datetime.now().isoformat(timespec='seconds')
    cur = conn.execute("""
        INSERT INTO actresses (javdb_id, name, name_ja, name_en, aliases, avatar_url, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(javdb_id) DO UPDATE SET
            name       = excluded.name,
            name_ja    = excluded.name_ja,
            name_en    = excluded.name_en,
            aliases    = excluded.aliases,
            avatar_url = excluded.avatar_url,
            fetched_at = excluded.fetched_at
    """, (a.javdb_id, a.name, a.name_ja, a.name_en, aliases_json, a.avatar_url, now))
    conn.commit()
    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute("SELECT id FROM actresses WHERE javdb_id=?", (a.javdb_id,)).fetchone()
    return row['id']


def get_actress_by_name(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM actresses WHERE name=? OR name_ja=? OR name_en=?",
        (name, name, name)
    ).fetchone()


def search_actresses(conn: sqlite3.Connection, keyword: str) -> list[sqlite3.Row]:
    like = f"%{keyword}%"
    return conn.execute(
        "SELECT * FROM actresses WHERE name LIKE ? OR name_ja LIKE ? OR name_en LIKE ? OR aliases LIKE ?",
        (like, like, like, like)
    ).fetchall()


def list_actresses(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT a.*, COUNT(av.video_id) AS video_count "
        "FROM actresses a "
        "LEFT JOIN actress_videos av ON av.actress_id=a.id "
        "GROUP BY a.id ORDER BY a.name"
    ).fetchall()


# ── Video CRUD ────────────────────────────────────────────────────────────────

def upsert_video(conn: sqlite3.Connection, v: Video) -> int:
    import datetime
    now = datetime.datetime.now().isoformat(timespec='seconds')
    cur = conn.execute("""
        INSERT INTO videos (code, javdb_id, title, release_date, duration, cover_url, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            javdb_id     = excluded.javdb_id,
            title        = excluded.title,
            release_date = excluded.release_date,
            duration     = excluded.duration,
            cover_url    = excluded.cover_url,
            fetched_at   = excluded.fetched_at
    """, (v.code.upper(), v.javdb_id, v.title, v.release_date, v.duration, v.cover_url, now))
    conn.commit()
    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute("SELECT id FROM videos WHERE code=?", (v.code.upper(),)).fetchone()
    return row['id']


def link_actress_video(conn: sqlite3.Connection, actress_id: int, video_id: int):
    conn.execute("""
        INSERT OR IGNORE INTO actress_videos (actress_id, video_id) VALUES (?, ?)
    """, (actress_id, video_id))
    conn.commit()


def get_videos_by_actress(conn: sqlite3.Connection, actress_id: int) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT v.* FROM videos v
        JOIN actress_videos av ON av.video_id = v.id
        WHERE av.actress_id = ?
        ORDER BY v.release_date DESC NULLS LAST
    """, (actress_id,)).fetchall()


def get_actress_video_count(conn: sqlite3.Connection, actress_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM actress_videos WHERE actress_id=?", (actress_id,)
    ).fetchone()
    return row['cnt'] if row else 0
