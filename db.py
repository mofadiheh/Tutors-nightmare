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
DB_PATH = "tutors_nightmare.db"

# Schema version for migrations
SCHEMA_VERSION = 3

# Conversation starter defaults
CONVERSATION_STARTER_TABLE = "conversation_starters"
REFRESH_LOG_TABLE = "conversation_starter_refresh_log"


async def get_db():
    """Get database connection"""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Initialize database tables and schema"""
    db = await get_db()
    
    try:
        # Create conversations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                primary_lang TEXT NOT NULL,
                secondary_lang TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'chat',
                created_at TEXT NOT NULL
            )
        """)
        
        # Create messages table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                lang TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        # Create index for faster message queries
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id, created_at)
        """)
        
        # Create message_translations table (cache for translations)
        # Store only the original text and its translation (no source/target language)
        # To support bidirectional lookup, we'll insert both directions when saving.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_translations (
                text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (text, translated_text)
            )
        """)
        # Conversation starters table
        await db.execute(f"""
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
        """)

        # Refresh log table for per-IP cooldown tracking
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {REFRESH_LOG_TABLE} (
                ip_address TEXT PRIMARY KEY,
                last_refresh_at TEXT NOT NULL
            )
        """)

        # Create schema_version table for migrations
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        
        # Check and set schema version (no migrations)
        cursor = await db.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = await cursor.fetchone()

        if row is None:
            # First time setup: insert current schema version
            await db.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, datetime.utcnow().isoformat())
            )
            print(f"✅ Database initialized with schema version {SCHEMA_VERSION}")
        else:
            current_version = row[0]
            if current_version < SCHEMA_VERSION:
                await db.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, datetime.utcnow().isoformat())
                )
                print(f"✅ Database migrated to schema version {SCHEMA_VERSION}")
            else:
                print(f"✅ Database ready (schema version {current_version})")
        
        await db.commit()
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise
    finally:
        await db.close()


async def create_conversation(
    conversation_id: str,
    primary_lang: str,
    secondary_lang: str,
    mode: str = "chat"
) -> bool:
    """Create a new conversation record"""
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO conversations (id, primary_lang, secondary_lang, mode, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, primary_lang, secondary_lang, mode, datetime.utcnow().isoformat())
        )
        await db.commit()
        return True
    except Exception as e:
        print(f"Error creating conversation: {e}")
        return False
    finally:
        await db.close()


async def get_conversation(conversation_id: str) -> Optional[Dict]:
    """Get conversation metadata by ID"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        await db.close()


async def insert_message(
    conversation_id: str,
    role: str,
    lang: str,
    text: str
) -> Optional[int]:
    """Insert a message into the database"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            INSERT INTO messages (conversation_id, role, lang, text, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, lang, text, datetime.utcnow().isoformat())
        )
        await db.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error inserting message: {e}")
        return None
    finally:
        await db.close()


async def get_messages(conversation_id: str, limit: int = 100) -> List[Dict]:
    """Get all messages for a conversation"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT conversation_id, role, lang, text, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (conversation_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def save_translation(message: str, translated_text: str) -> bool:
    """Save a translation to cache using the message text and translated text.

    To make the cache bidirectional we store both (original -> translated)
    and (translated -> original).
    """
    db = await get_db()
    try:
        now = datetime.utcnow().isoformat()
        # Insert original -> translation
        await db.execute(
            """
            INSERT OR REPLACE INTO message_translations (text, translated_text, created_at)
            VALUES (?, ?, ?)
            """,
            (message, translated_text, now)
        )
        # Insert reverse mapping translated -> original for bidirectional lookup
        await db.execute(
            """
            INSERT OR REPLACE INTO message_translations (text, translated_text, created_at)
            VALUES (?, ?, ?)
            """,
            (translated_text, message, now)
        )
        await db.commit()
        return True
    except Exception as e:
        print(f"Error saving translation: {e}")
        return False
    finally:
        await db.close()


async def get_translation(message: str) -> Optional[str]:
    """Get a cached translation for the given text (bidirectional lookup).

    Returns one matching translation if available, otherwise None.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT translated_text FROM message_translations WHERE text = ? LIMIT 1",
            (message,)
        )
        row = await cursor.fetchone()
        if row:
            return row[0]
        return None
    finally:
        await db.close()


async def conversation_exists(conversation_id: str) -> bool:
    """Check if a conversation exists"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT 1 FROM conversations WHERE id = ? LIMIT 1",
            (conversation_id,)
        )
        row = await cursor.fetchone()
        return row is not None
    finally:
        await db.close()


async def replace_conversation_starters(starters: List[Dict]) -> int:
    """Replace all conversation starters with the provided list."""
    db = await get_db()
    try:
        await db.execute("BEGIN")
        await db.execute(f"DELETE FROM {CONVERSATION_STARTER_TABLE}")
        for starter in starters:
            await db.execute(
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
                    starter.get("created_at", datetime.utcnow().isoformat()),
                ),
            )
        await db.commit()
        return len(starters)
    finally:
        await db.close()


async def get_conversation_starters() -> Tuple[List[Dict], Optional[str]]:
    """Return all conversation starters sorted by rank asc, created_at desc."""
    db = await get_db()
    try:
        cursor = await db.execute(
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
        await db.close()


async def get_conversation_starter_by_id(starter_id: str) -> Optional[Dict]:
    """Fetch a single conversation starter by ID."""
    db = await get_db()
    try:
        cursor = await db.execute(
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
        await db.close()


async def get_last_refresh_time(ip_address: str) -> Optional[datetime]:
    """Get last refresh timestamp for an IP."""
    db = await get_db()
    try:
        cursor = await db.execute(
            f"SELECT last_refresh_at FROM {REFRESH_LOG_TABLE} WHERE ip_address = ?",
            (ip_address,),
        )
        row = await cursor.fetchone()
        if row:
            return datetime.fromisoformat(row["last_refresh_at"])
        return None
    finally:
        await db.close()


async def update_refresh_time(ip_address: str) -> None:
    """Upsert refresh timestamp for an IP."""
    db = await get_db()
    try:
        await db.execute(
            f"""
            INSERT INTO {REFRESH_LOG_TABLE} (ip_address, last_refresh_at)
            VALUES (?, ?)
            ON CONFLICT(ip_address) DO UPDATE SET last_refresh_at = excluded.last_refresh_at
            """,
            (ip_address, datetime.utcnow().isoformat()),
        )
        await db.commit()
    finally:
        await db.close()
