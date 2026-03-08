"""
SQLite persistence for custom agents.

Stores custom agents so they survive server restarts.
Built-in agents are always loaded from code — only custom agents go to DB.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# DB file lives next to the backend package
_DB_DIR = Path(__file__).resolve().parent.parent  # backend/
_DB_PATH = _DB_DIR / "quorum_agents.db"


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode for concurrency."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the agents table if it doesn't exist."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS custom_agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                label TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                personality TEXT NOT NULL DEFAULT '',
                speaking_style TEXT NOT NULL DEFAULT '',
                tone TEXT NOT NULL DEFAULT 'neutral',
                expertise TEXT NOT NULL DEFAULT '[]',
                voice TEXT NOT NULL DEFAULT 'Aoede',
                avatar_url TEXT NOT NULL DEFAULT '',
                background_theme TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        logger.info("Agent DB initialized at %s", _DB_PATH)
    finally:
        conn.close()


def save_agent(
    agent_id: str,
    name: str,
    role: str,
    label: str,
    description: str,
    personality: str,
    speaking_style: str,
    tone: str,
    expertise: list[str],
    voice: str,
    avatar_url: str = "",
    background_theme: str = "",
) -> None:
    """Insert or replace a custom agent in the DB."""
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO custom_agents
                (id, name, role, label, description, personality, speaking_style,
                 tone, expertise, voice, avatar_url, background_theme)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent_id, name, role, label, description, personality,
                speaking_style, tone, json.dumps(expertise), voice,
                avatar_url, background_theme,
            ),
        )
        conn.commit()
        logger.info("Saved agent %s (%s) to DB", name, agent_id)
    finally:
        conn.close()


def load_all_agents() -> list[dict]:
    """Load all custom agents from the DB. Returns list of dicts."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM custom_agents ORDER BY created_at").fetchall()
        agents = []
        for row in rows:
            agents.append({
                "id": row["id"],
                "name": row["name"],
                "role": row["role"],
                "label": row["label"],
                "description": row["description"],
                "personality": row["personality"],
                "speaking_style": row["speaking_style"],
                "tone": row["tone"],
                "expertise": json.loads(row["expertise"]),
                "voice": row["voice"],
                "avatar_url": row["avatar_url"],
                "background_theme": row["background_theme"],
            })
        logger.info("Loaded %d custom agents from DB", len(agents))
        return agents
    finally:
        conn.close()


def delete_agent(agent_id: str) -> bool:
    """Delete a custom agent from the DB. Returns True if found."""
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM custom_agents WHERE id = ?", (agent_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info("Deleted agent %s from DB", agent_id)
        return deleted
    finally:
        conn.close()


def agent_exists(agent_id: str) -> bool:
    """Check if a custom agent exists in the DB."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM custom_agents WHERE id = ?", (agent_id,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()
