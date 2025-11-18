"""Database manager for chat sessions and messages."""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import json

class DatabaseManager:
    """Manages SQLite database for chat sessions and messages."""

    def __init__(self, db_path: str = "frontend/database/chat_history.db"):
        """Initialize database manager."""
        self.db_path = db_path
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if sessions table exists and migrate if needed
            cursor.execute("PRAGMA table_info(sessions)")
            columns = [col[1] for col in cursor.fetchall()]

            # Migration: Add new columns if they don't exist
            if 'has_documents' not in columns:
                try:
                    cursor.execute("ALTER TABLE sessions ADD COLUMN has_documents BOOLEAN DEFAULT 0")
                except sqlite3.OperationalError:
                    pass  # Column already exists

            if 'vector_db_path' not in columns:
                try:
                    cursor.execute("ALTER TABLE sessions ADD COLUMN vector_db_path TEXT")
                except sqlite3.OperationalError:
                    pass  # Column already exists

            # Create sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    has_documents BOOLEAN DEFAULT 0,
                    vector_db_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)

            # Create documents table for tracking uploaded files
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)

            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id
                ON messages(session_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_updated
                ON sessions(updated_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_session
                ON documents(session_id)
            """)

            conn.commit()

    def create_session(self, session_id: str, title: str) -> Dict:
        """Create a new chat session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (session_id, title) VALUES (?, ?)",
                (session_id, title)
            )
            conn.commit()

            return {
                "session_id": session_id,
                "title": title,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a specific session by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

    def list_sessions(self, limit: int = 50) -> List[Dict]:
        """List all sessions ordered by last updated."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def update_session_title(self, session_id: str, title: str) -> bool:
        """Update session title."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                (title, session_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_session_timestamp(self, session_id: str) -> bool:
        """Update session timestamp (when new message is added)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Delete messages first
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            # Delete session
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    def add_message(self, session_id: str, role: str, content: str) -> Dict:
        """Add a message to a session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )
            message_id = cursor.lastrowid
            conn.commit()

            # Update session timestamp
            self.update_session_timestamp(session_id)

            return {
                "id": message_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }

    def get_messages(self, session_id: str) -> List[Dict]:
        """Get all messages for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,)
            )
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_session_with_messages(self, session_id: str) -> Optional[Dict]:
        """Get session with all its messages."""
        session = self.get_session(session_id)
        if not session:
            return None

        messages = self.get_messages(session_id)
        session['messages'] = messages
        return session

    def clear_all_data(self):
        """Clear all sessions and messages (for testing/reset)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents")
            cursor.execute("DELETE FROM messages")
            cursor.execute("DELETE FROM sessions")
            conn.commit()

    # ============= Document Management Methods =============

    def add_document(self, session_id: str, filename: str, file_path: str, file_size: int) -> Dict:
        """Add a document record to a session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO documents (session_id, filename, file_path, file_size) VALUES (?, ?, ?, ?)",
                (session_id, filename, file_path, file_size)
            )
            document_id = cursor.lastrowid
            conn.commit()

            # Update session timestamp
            self.update_session_timestamp(session_id)

            return {
                "id": document_id,
                "session_id": session_id,
                "filename": filename,
                "file_path": file_path,
                "file_size": file_size,
                "uploaded_at": datetime.now().isoformat()
            }

    def get_documents(self, session_id: str) -> List[Dict]:
        """Get all documents for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE session_id = ? ORDER BY uploaded_at ASC",
                (session_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_session_vector_db(self, session_id: str, vector_db_path: str) -> bool:
        """Update session with vector DB path."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET has_documents = 1, vector_db_path = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                (vector_db_path, session_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_session_vector_db_path(self, session_id: str) -> Optional[str]:
        """Get vector DB path for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT vector_db_path FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if row and row['vector_db_path']:
                return row['vector_db_path']
            return None
