"""
Database module for Language-Learning Chatbot
SQLite database with async support (aiosqlite)
"""

import aiosqlite
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Database file path
DB_PATH = os.getenv("DB_PATH", "tutors_nightmare.db")

# Schema version for migrations
SCHEMA_VERSION = 4

# Conversation starter defaults
CONVERSATION_STARTER_TABLE = "conversation_starters"
REFRESH_LOG_TABLE = "conversation_starter_refresh_log"
BETA_INVITE_KEY = "global_invite_code_hash"


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat()


async def get_db():
    """Get database connection"""
    db_conn = await aiosqlite.connect(DB_PATH)
    db_conn.row_factory = aiosqlite.Row
    return db_conn


async def _table_has_column(db_conn: aiosqlite.Connection, table_name: str, column_name: str) -> bool:
    cursor = await db_conn.execute(f"PRAGMA table_info({table_name})")
    rows = await cursor.fetchall()
    for row in rows:
        if row["name"] == column_name:
            return True
    return False


async def init_db():
    """Initialize database tables and schema."""
    db_conn = await get_db()

    try:
        # Create conversations table
        await db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                primary_lang TEXT NOT NULL,
                secondary_lang TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'chat',
                created_at TEXT NOT NULL
            )
            """
        )

        # Migration: add user_id to conversations if missing
        if not await _table_has_column(db_conn, "conversations", "user_id"):
            await db_conn.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")

        await db_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_user_created
            ON conversations(user_id, created_at)
            """
        )

        # Create messages table
        await db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                lang TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
            """
        )

        # Create index for faster message queries
        await db_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages(conversation_id, created_at)
            """
        )

        # Create message_translations table (cache for translations)
        await db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_translations (
                text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (text, translated_text)
            )
            """
        )

        # Conversation starters table
        await db_conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CONVERSATION_STARTER_TABLE} (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                opener TEXT NOT NULL,
                source_url TEXT,
                subreddit TEXT,
                rank INTEGER NOT NULL DEFAULT 0,
                metadata TEXT,
                generated_by TEXT NOT NULL DEFAULT 'reddit_llm',
                created_at TEXT NOT NULL
            )
            """
        )

        # Refresh log table for per-IP cooldown tracking
        await db_conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {REFRESH_LOG_TABLE} (
                ip_address TEXT PRIMARY KEY,
                last_refresh_at TEXT NOT NULL
            )
            """
        )

        # Users table for beta access
        await db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                preferred_primary_lang TEXT,
                preferred_secondary_lang TEXT,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            )
            """
        )

        # Auth sessions table
        await db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        await db_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
            ON auth_sessions(user_id, expires_at)
            """
        )

        # Beta settings table
        await db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS beta_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Create schema_version table for migrations
        await db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )

        cursor = await db_conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = await cursor.fetchone()

        if row is None:
            await db_conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, _utcnow_iso()),
            )
            print(f"✅ Database initialized with schema version {SCHEMA_VERSION}")
        else:
            current_version = row[0]
            if current_version < SCHEMA_VERSION:
                await db_conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, _utcnow_iso()),
                )
                print(f"✅ Database migrated to schema version {SCHEMA_VERSION}")
            else:
                print(f"✅ Database ready (schema version {current_version})")

        await db_conn.commit()

    except Exception as exc:
        print(f"❌ Error initializing database: {exc}")
        raise
    finally:
        await db_conn.close()


async def create_user(user_id: str, username: str, password_hash: str, display_name: str) -> bool:
    """Create a new user account."""
    db_conn = await get_db()
    now = _utcnow_iso()
    try:
        await db_conn.execute(
            """
            INSERT INTO users (
                id, username, password_hash, display_name,
                preferred_primary_lang, preferred_secondary_lang,
                created_at, last_seen_at
            ) VALUES (?, ?, ?, ?, NULL, NULL, ?, ?)
            """,
            (user_id, username, password_hash, display_name, now, now),
        )
        await db_conn.commit()
        return True
    except Exception as exc:
        print(f"Error creating user: {exc}")
        return False
    finally:
        await db_conn.close()


async def get_user_by_username(username: str) -> Optional[Dict]:
    """Fetch a user by normalized username."""
    db_conn = await get_db()
    try:
        cursor = await db_conn.execute(
            "SELECT * FROM users WHERE username = ? LIMIT 1",
            (username,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        await db_conn.close()


async def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Fetch a user by id."""
    db_conn = await get_db()
    try:
        cursor = await db_conn.execute(
            "SELECT * FROM users WHERE id = ? LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        await db_conn.close()


async def update_user_profile(
    user_id: str,
    display_name: Optional[str] = None,
    preferred_primary_lang: Optional[str] = None,
    preferred_secondary_lang: Optional[str] = None,
) -> bool:
    """Update mutable user profile fields."""
    updates = []
    values = []

    if display_name is not None:
        updates.append("display_name = ?")
        values.append(display_name)
    if preferred_primary_lang is not None:
        updates.append("preferred_primary_lang = ?")
        values.append(preferred_primary_lang)
    if preferred_secondary_lang is not None:
        updates.append("preferred_secondary_lang = ?")
        values.append(preferred_secondary_lang)

    if not updates:
        return True

    db_conn = await get_db()
    try:
        values.append(user_id)
        await db_conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            tuple(values),
        )
        await db_conn.commit()
        return True
    except Exception as exc:
        print(f"Error updating user profile: {exc}")
        return False
    finally:
        await db_conn.close()


async def touch_user(user_id: str) -> None:
    """Update user's last seen timestamp."""
    db_conn = await get_db()
    try:
        await db_conn.execute(
            "UPDATE users SET last_seen_at = ? WHERE id = ?",
            (_utcnow_iso(), user_id),
        )
        await db_conn.commit()
    finally:
        await db_conn.close()


async def create_auth_session(
    session_id: str,
    user_id: str,
    token_hash: str,
    expires_at: str,
    ip_address: str,
    user_agent: str,
) -> bool:
    """Create a new auth session."""
    db_conn = await get_db()
    try:
        await db_conn.execute(
            """
            INSERT INTO auth_sessions (
                id, user_id, token_hash, created_at, expires_at,
                revoked_at, ip_address, user_agent
            ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (session_id, user_id, token_hash, _utcnow_iso(), expires_at, ip_address, user_agent),
        )
        await db_conn.commit()
        return True
    except Exception as exc:
        print(f"Error creating auth session: {exc}")
        return False
    finally:
        await db_conn.close()


async def get_active_session_by_token_hash(token_hash: str) -> Optional[Dict]:
    """Fetch active (non-revoked, non-expired) session and user data."""
    db_conn = await get_db()
    now = _utcnow_iso()
    try:
        cursor = await db_conn.execute(
            """
            SELECT
                s.id AS session_id,
                s.user_id,
                s.token_hash,
                s.expires_at,
                s.ip_address,
                s.user_agent,
                u.username,
                u.display_name,
                u.preferred_primary_lang,
                u.preferred_secondary_lang,
                u.created_at,
                u.last_seen_at
            FROM auth_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
              AND s.revoked_at IS NULL
              AND s.expires_at > ?
            LIMIT 1
            """,
            (token_hash, now),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        await db_conn.close()


async def extend_auth_session(token_hash: str, expires_at: str) -> None:
    """Extend session expiry for rolling sessions."""
    db_conn = await get_db()
    try:
        await db_conn.execute(
            """
            UPDATE auth_sessions
            SET expires_at = ?
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (expires_at, token_hash),
        )
        await db_conn.commit()
    finally:
        await db_conn.close()


async def revoke_auth_session(token_hash: str) -> None:
    """Revoke a session by token hash."""
    db_conn = await get_db()
    try:
        await db_conn.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = ?
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (_utcnow_iso(), token_hash),
        )
        await db_conn.commit()
    finally:
        await db_conn.close()


async def set_beta_setting(key: str, value: str) -> None:
    """Upsert a beta setting value."""
    db_conn = await get_db()
    now = _utcnow_iso()
    try:
        await db_conn.execute(
            """
            INSERT INTO beta_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, now),
        )
        await db_conn.commit()
    finally:
        await db_conn.close()


async def get_beta_setting(key: str) -> Optional[Dict]:
    """Fetch a beta setting record by key."""
    db_conn = await get_db()
    try:
        cursor = await db_conn.execute(
            "SELECT key, value, updated_at FROM beta_settings WHERE key = ? LIMIT 1",
            (key,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        await db_conn.close()


async def get_beta_invite_code_hash() -> Optional[str]:
    """Return hashed global invite code if configured."""
    record = await get_beta_setting(BETA_INVITE_KEY)
    if not record:
        return None
    return record["value"]


async def set_beta_invite_code_hash(code_hash: str) -> None:
    """Store global invite code hash."""
    await set_beta_setting(BETA_INVITE_KEY, code_hash)


async def get_beta_invite_status() -> Dict:
    """Return whether invite code is configured and when it changed."""
    record = await get_beta_setting(BETA_INVITE_KEY)
    if not record:
        return {"configured": False, "updated_at": None}
    return {"configured": True, "updated_at": record["updated_at"]}


async def create_conversation(
    conversation_id: str,
    primary_lang: str,
    secondary_lang: str,
    mode: str = "chat",
    user_id: Optional[str] = None,
) -> bool:
    """Create a new conversation record."""
    db_conn = await get_db()
    try:
        await db_conn.execute(
            """
            INSERT INTO conversations (id, primary_lang, secondary_lang, mode, created_at, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, primary_lang, secondary_lang, mode, _utcnow_iso(), user_id),
        )
        await db_conn.commit()
        return True
    except Exception as exc:
        print(f"Error creating conversation: {exc}")
        return False
    finally:
        await db_conn.close()


async def get_conversation(conversation_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
    """Get conversation metadata by ID, optionally scoped to user."""
    db_conn = await get_db()
    try:
        if user_id is None:
            cursor = await db_conn.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            )
        else:
            cursor = await db_conn.execute(
                "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id),
            )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        await db_conn.close()


async def insert_message(conversation_id: str, role: str, lang: str, text: str) -> Optional[int]:
    """Insert a message into the database."""
    db_conn = await get_db()
    try:
        cursor = await db_conn.execute(
            """
            INSERT INTO messages (conversation_id, role, lang, text, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, lang, text, _utcnow_iso()),
        )
        await db_conn.commit()
        return cursor.lastrowid
    except Exception as exc:
        print(f"Error inserting message: {exc}")
        return None
    finally:
        await db_conn.close()


async def get_messages(conversation_id: str, limit: int = 100) -> List[Dict]:
    """Get all messages for a conversation."""
    db_conn = await get_db()
    try:
        cursor = await db_conn.execute(
            """
            SELECT id, conversation_id, role, lang, text, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (conversation_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db_conn.close()


async def save_translation(message: str, translated_text: str) -> bool:
    """Save a translation to cache.

    To make the cache bidirectional we store both (original -> translated)
    and (translated -> original).
    """
    db_conn = await get_db()
    now = _utcnow_iso()
    try:
        await db_conn.execute(
            """
            INSERT OR REPLACE INTO message_translations (text, translated_text, created_at)
            VALUES (?, ?, ?)
            """,
            (message, translated_text, now),
        )
        await db_conn.execute(
            """
            INSERT OR REPLACE INTO message_translations (text, translated_text, created_at)
            VALUES (?, ?, ?)
            """,
            (translated_text, message, now),
        )
        await db_conn.commit()
        return True
    except Exception as exc:
        print(f"Error saving translation: {exc}")
        return False
    finally:
        await db_conn.close()


async def get_translation(message: str) -> Optional[str]:
    """Get a cached translation for the given text (bidirectional lookup)."""
    db_conn = await get_db()
    try:
        cursor = await db_conn.execute(
            "SELECT translated_text FROM message_translations WHERE text = ? LIMIT 1",
            (message,),
        )
        row = await cursor.fetchone()
        if row:
            return row[0]
        return None
    finally:
        await db_conn.close()


async def conversation_exists(conversation_id: str, user_id: Optional[str] = None) -> bool:
    """Check if a conversation exists, optionally scoped to user."""
    db_conn = await get_db()
    try:
        if user_id is None:
            cursor = await db_conn.execute(
                "SELECT 1 FROM conversations WHERE id = ? LIMIT 1",
                (conversation_id,),
            )
        else:
            cursor = await db_conn.execute(
                "SELECT 1 FROM conversations WHERE id = ? AND user_id = ? LIMIT 1",
                (conversation_id, user_id),
            )
        row = await cursor.fetchone()
        return row is not None
    finally:
        await db_conn.close()


async def replace_conversation_starters(starters: List[Dict]) -> int:
    """Replace all conversation starters with the provided list."""
    db_conn = await get_db()
    try:
        await db_conn.execute("BEGIN")
        await db_conn.execute(f"DELETE FROM {CONVERSATION_STARTER_TABLE}")
        for starter in starters:
            await db_conn.execute(
                f"""
                INSERT INTO {CONVERSATION_STARTER_TABLE}
                    (id, title, opener, source_url, subreddit, rank, metadata, generated_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    starter["id"],
                    starter["title"],
                    starter["opener"],
                    starter.get("source_url"),
                    starter.get("subreddit"),
                    starter.get("rank", 0),
                    json.dumps(starter.get("metadata", {})),
                    starter.get("generated_by", "reddit_llm"),
                    starter.get("created_at", _utcnow_iso()),
                ),
            )
        await db_conn.commit()
        return len(starters)
    finally:
        await db_conn.close()


async def get_conversation_starters() -> Tuple[List[Dict], Optional[str]]:
    """Return all conversation starters sorted by rank asc, created_at desc."""
    db_conn = await get_db()
    try:
        cursor = await db_conn.execute(
            f"""
            SELECT id, title, opener, source_url, subreddit, rank, metadata, created_at
            FROM {CONVERSATION_STARTER_TABLE}
            ORDER BY rank ASC, created_at DESC
            """
        )
        rows = await cursor.fetchall()
        starters = []
        latest_time = None
        for row in rows:
            starters.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "opener": row["opener"],
                    "source_url": row["source_url"],
                    "subreddit": row["subreddit"],
                    "rank": row["rank"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "created_at": row["created_at"],
                }
            )
            if latest_time is None or row["created_at"] > latest_time:
                latest_time = row["created_at"]
        return starters, latest_time
    finally:
        await db_conn.close()


async def get_conversation_starter_by_id(starter_id: str) -> Optional[Dict]:
    """Fetch a single conversation starter by ID."""
    db_conn = await get_db()
    try:
        cursor = await db_conn.execute(
            f"""
            SELECT id, title, opener, source_url, subreddit, rank, metadata, created_at
            FROM {CONVERSATION_STARTER_TABLE}
            WHERE id = ?
            LIMIT 1
            """,
            (starter_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "opener": row["opener"],
            "source_url": row["source_url"],
            "subreddit": row["subreddit"],
            "rank": row["rank"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "created_at": row["created_at"],
        }
    finally:
        await db_conn.close()


async def get_last_refresh_time(ip_address: str) -> Optional[datetime]:
    """Get last refresh timestamp for an IP."""
    db_conn = await get_db()
    try:
        cursor = await db_conn.execute(
            f"SELECT last_refresh_at FROM {REFRESH_LOG_TABLE} WHERE ip_address = ?",
            (ip_address,),
        )
        row = await cursor.fetchone()
        if row:
            return datetime.fromisoformat(row["last_refresh_at"])
        return None
    finally:
        await db_conn.close()


async def update_refresh_time(ip_address: str) -> None:
    """Upsert refresh timestamp for an IP."""
    db_conn = await get_db()
    try:
        await db_conn.execute(
            f"""
            INSERT INTO {REFRESH_LOG_TABLE} (ip_address, last_refresh_at)
            VALUES (?, ?)
            ON CONFLICT(ip_address) DO UPDATE SET last_refresh_at = excluded.last_refresh_at
            """,
            (ip_address, _utcnow_iso()),
        )
        await db_conn.commit()
    finally:
        await db_conn.close()
