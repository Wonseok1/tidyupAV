"""PostgreSQL DB 관리"""
import os
import json
import datetime
from typing import Optional
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

from .models import Actress, Video

# 프로젝트 루트의 .env 로드
load_dotenv(Path(__file__).parent.parent / ".env")


def get_conn() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = False
    return conn


def init_db():
    """테이블 초기화 (없으면 생성)"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS actresses (
                id          SERIAL PRIMARY KEY,
                javdb_id    TEXT    UNIQUE NOT NULL,
                name        TEXT    NOT NULL,
                name_ja     TEXT,
                name_en     TEXT,
                aliases     JSONB   DEFAULT '[]',
                avatar_url  TEXT,
                fetched_at  TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS videos (
                id           SERIAL PRIMARY KEY,
                code         TEXT    UNIQUE NOT NULL,
                javdb_id     TEXT    UNIQUE,
                title        TEXT,
                release_date DATE,
                duration     INTEGER,
                cover_url    TEXT,
                fetched_at   TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS actress_videos (
                actress_id  INTEGER NOT NULL REFERENCES actresses(id) ON DELETE CASCADE,
                video_id    INTEGER NOT NULL REFERENCES videos(id)    ON DELETE CASCADE,
                PRIMARY KEY (actress_id, video_id)
            );

            CREATE INDEX IF NOT EXISTS idx_videos_code     ON videos(code);
            CREATE INDEX IF NOT EXISTS idx_actresses_name  ON actresses(name);
            CREATE INDEX IF NOT EXISTS idx_actresses_javdb ON actresses(javdb_id);
            """)
        conn.commit()


# ── Actress CRUD ──────────────────────────────────────────────────────────────

def upsert_actress(conn, a: Actress) -> int:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO actresses (javdb_id, name, name_ja, name_en, aliases, avatar_url, fetched_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, NOW())
            ON CONFLICT (javdb_id) DO UPDATE SET
                name       = EXCLUDED.name,
                name_ja    = EXCLUDED.name_ja,
                name_en    = EXCLUDED.name_en,
                aliases    = EXCLUDED.aliases,
                avatar_url = EXCLUDED.avatar_url,
                fetched_at = NOW()
            RETURNING id
        """, (
            a.javdb_id,
            a.name,
            a.name_ja,
            a.name_en,
            json.dumps(a.aliases, ensure_ascii=False),
            a.avatar_url,
        ))
        row = cur.fetchone()
        conn.commit()
        return row["id"]


def get_actress_by_name(conn, name: str) -> Optional[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM actresses WHERE name=%s OR name_ja=%s OR name_en=%s",
            (name, name, name)
        )
        return cur.fetchone()


def search_actresses(conn, keyword: str) -> list:
    like = f"%{keyword}%"
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM actresses WHERE name ILIKE %s OR name_ja ILIKE %s OR name_en ILIKE %s OR aliases::text ILIKE %s",
            (like, like, like, like)
        )
        return cur.fetchall()


def list_actresses(conn) -> list:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT a.*, COUNT(av.video_id) AS video_count
            FROM actresses a
            LEFT JOIN actress_videos av ON av.actress_id = a.id
            GROUP BY a.id
            ORDER BY a.name
        """)
        return cur.fetchall()


# ── Video CRUD ────────────────────────────────────────────────────────────────

def upsert_video(conn, v: Video) -> int:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO videos (code, javdb_id, title, release_date, duration, cover_url, fetched_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (code) DO UPDATE SET
                javdb_id     = EXCLUDED.javdb_id,
                title        = EXCLUDED.title,
                release_date = EXCLUDED.release_date,
                duration     = EXCLUDED.duration,
                cover_url    = EXCLUDED.cover_url,
                fetched_at   = NOW()
            RETURNING id
        """, (
            v.code.upper(),
            v.javdb_id,
            v.title,
            v.release_date,
            v.duration,
            v.cover_url,
        ))
        row = cur.fetchone()
        conn.commit()
        return row["id"]


def link_actress_video(conn, actress_id: int, video_id: int):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO actress_videos (actress_id, video_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (actress_id, video_id))
        conn.commit()


def get_videos_by_actress(conn, actress_id: int) -> list:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT v.* FROM videos v
            JOIN actress_videos av ON av.video_id = v.id
            WHERE av.actress_id = %s
            ORDER BY v.release_date DESC NULLS LAST
        """, (actress_id,))
        return cur.fetchall()


def get_actress_video_count(conn, actress_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM actress_videos WHERE actress_id=%s",
            (actress_id,)
        )
        row = cur.fetchone()
        return row["cnt"] if row else 0
