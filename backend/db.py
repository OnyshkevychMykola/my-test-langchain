"""
SQLite: users → conversations → messages.
Context window: last N messages per conversation for LLM history.
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent / "medical_assistant.db"


def _utc_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id TEXT UNIQUE NOT NULL,
                email TEXT,
                name TEXT,
                avatar_url TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS refresh_tokens (
                jti TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
        """)


# --- Users ---

def user_get_by_google_id(google_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, google_id, email, name, avatar_url, created_at FROM users WHERE google_id = ?",
            (google_id,),
        ).fetchone()
    return dict(row) if row else None


def user_get_by_id(user_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, google_id, email, name, avatar_url, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def user_create(google_id: str, email: Optional[str] = None, name: Optional[str] = None, avatar_url: Optional[str] = None) -> dict:
    now = _utc_now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (google_id, email, name, avatar_url, created_at) VALUES (?, ?, ?, ?, ?)",
            (google_id, email or "", name or "", avatar_url or "", now),
        )
        uid = cur.lastrowid
    return {"id": uid, "google_id": google_id, "email": email, "name": name, "avatar_url": avatar_url, "created_at": now}


def user_get_or_create(google_id: str, email: Optional[str] = None, name: Optional[str] = None, avatar_url: Optional[str] = None) -> dict:
    u = user_get_by_google_id(google_id)
    if u:
        return u
    return user_create(google_id, email, name, avatar_url)


# --- Conversations ---

def conversation_create(user_id: int, title: Optional[str] = None, allow_if_empty_exists: bool = False) -> Optional[dict]:
    """
    Create a new conversation. If allow_if_empty_exists is False and user already
    has a conversation with 0 messages, returns None (caller should use the existing empty one).
    """
    if not allow_if_empty_exists:
        existing = conversation_find_empty(user_id)
        if existing:
            return None
    now = _utc_now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, title or "Нова розмова", now, now),
        )
        cid = cur.lastrowid
    return {"id": cid, "user_id": user_id, "title": title or "Нова розмова", "created_at": now, "updated_at": now}


def conversation_list(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def conversation_find_empty(user_id: int) -> Optional[dict]:
    """Return one conversation that has zero messages (for "no duplicate empty" rule)."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT c.id, c.user_id, c.title, c.created_at, c.updated_at
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            WHERE c.user_id = ?
            GROUP BY c.id
            HAVING COUNT(m.id) = 0
            ORDER BY c.id DESC
            LIMIT 1
        """, (user_id,)).fetchone()
    return dict(row) if row else None


def conversation_get(conversation_id: int, user_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def conversation_update_title(conversation_id: int, user_id: int, title: str) -> None:
    now = _utc_now()
    with get_conn() as conn:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (title, now, conversation_id, user_id),
        )


def conversation_update_updated_at(conversation_id: int) -> None:
    now = _utc_now()
    with get_conn() as conn:
        conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))


def conversation_delete(conversation_id: int, user_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id))
        return cur.rowcount > 0


# --- Messages (with context window) ---

CONTEXT_WINDOW_SIZE = 20  # last N messages to load as history for LLM


def message_add(conversation_id: int, role: str, content: str) -> dict:
    now = _utc_now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, now),
        )
        mid = cur.lastrowid
    conversation_update_updated_at(conversation_id)
    return {"id": mid, "conversation_id": conversation_id, "role": role, "content": content, "created_at": now}


def messages_list(conversation_id: int, user_id: int, limit: Optional[int] = None) -> list[dict]:
    """All messages of the conversation (for UI). Optionally limit for pagination."""
    with get_conn() as conn:
        # Ensure conversation belongs to user
        conv = conn.execute("SELECT id FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)).fetchone()
        if not conv:
            return []
        sql = "SELECT id, conversation_id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        rows = conn.execute(sql, (conversation_id,)).fetchall()
    return [dict(r) for r in rows]


def messages_last_n_for_context(conversation_id: int, n: int = CONTEXT_WINDOW_SIZE) -> list[dict]:
    """Last N messages for LLM context (no user check; call only after verifying conversation access)."""
    with get_conn() as conn:
        # Subquery: get last N ids, then order by id ASC for chronological history
        rows = conn.execute("""
            SELECT id, conversation_id, role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (conversation_id, n)).fetchall()
    # Reverse so oldest first (chronological for LLM)
    return [dict(r) for r in reversed(rows)]

def refresh_token_store(jti: str, user_id: int, expires_at: str) -> None:
    now = _utc_now()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO refresh_tokens (jti, user_id, expires_at, created_at, revoked) VALUES (?, ?, ?, ?, 0)",
            (jti, user_id, expires_at, now),
        )


def refresh_token_is_valid(jti: str) -> bool:
    """Return True only if the token exists, is not revoked, and has not expired."""
    now = _utc_now()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT jti FROM refresh_tokens WHERE jti = ? AND revoked = 0 AND expires_at > ?",
            (jti, now),
        ).fetchone()
    return row is not None


def refresh_token_revoke(jti: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE refresh_tokens SET revoked = 1 WHERE jti = ?", (jti,))


def refresh_tokens_revoke_all_for_user(user_id: int) -> None:
    """Revoke every active refresh token for a user (logout from all devices)."""
    with get_conn() as conn:
        conn.execute("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ? AND revoked = 0", (user_id,))


def refresh_tokens_cleanup_expired() -> int:
    """Delete expired tokens to keep the table small. Returns number of rows removed."""
    now = _utc_now()
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM refresh_tokens WHERE expires_at <= ?", (now,))
        return cur.rowcount
