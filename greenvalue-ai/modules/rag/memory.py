"""
SQLite User Memory
Author: GreenValue AI Team
Purpose: Persistent storage for user preferences and query history.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("greenvalue-rag")


class SQLiteMemory:
    """
    SQLite-based user memory for RAG personalization.
    - User profiles and preferences
    - Query history for context
    - Analysis learning (feedback loop)
    """
    
    def __init__(self, db_path: str = "/app/data/user_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                property_preferences TEXT DEFAULT 'residential',
                sustainability_focus TEXT DEFAULT 'moderate',
                analysis_count INTEGER DEFAULT 0,
                created_at TEXT,
                last_active TEXT
            )
        ''')
        
        # Query history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                query TEXT,
                query_type TEXT,
                category TEXT,
                response_quality INTEGER,
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Feedback table for learning
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id INTEGER,
                helpful BOOLEAN,
                feedback_text TEXT,
                timestamp TEXT,
                FOREIGN KEY (query_id) REFERENCES query_history(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Memory database initialized: {self.db_path}")
    
    def get_user_profile(self, user_id: str = "default") -> Dict:
        """Get or create user profile."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO users (user_id, created_at, last_active)
                VALUES (?, ?, ?)
            ''', (user_id, now, now))
            conn.commit()
            row = (user_id, 'residential', 'moderate', 0, now, now)
        
        conn.close()
        
        return {
            "user_id": row[0],
            "property_preferences": row[1],
            "sustainability_focus": row[2],
            "analysis_count": row[3],
            "created_at": row[4],
            "last_active": row[5],
        }
    
    def update_preference(self, user_id: str, key: str, value: str):
        """Update a user preference."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Ensure user exists
        self.get_user_profile(user_id)
        
        valid_keys = ["property_preferences", "sustainability_focus"]
        if key not in valid_keys:
            logger.warning(f"Invalid preference key: {key}")
            return
        
        cursor.execute(f'''
            UPDATE users SET {key} = ?, last_active = ? WHERE user_id = ?
        ''', (value, datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
    
    def log_query(
        self,
        user_id: str,
        query: str,
        query_type: str,
        category: str = None
    ) -> int:
        """Log a query for history."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO query_history (user_id, query, query_type, category, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, query, query_type, category, datetime.now().isoformat()))
        
        # Update analysis count
        cursor.execute('''
            UPDATE users SET analysis_count = analysis_count + 1, last_active = ?
            WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        
        conn.commit()
        query_id = cursor.lastrowid
        conn.close()
        
        return query_id
    
    def add_feedback(self, query_id: int, helpful: bool, feedback_text: str = None):
        """Add feedback for a query."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback (query_id, helpful, feedback_text, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (query_id, helpful, feedback_text, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_recent_queries(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get recent queries for context."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT query, query_type, category, timestamp
            FROM query_history
            WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "query": r[0],
                "query_type": r[1],
                "category": r[2],
                "timestamp": r[3],
            }
            for r in rows
        ]
    
    def get_personalization_context(self, user_id: str) -> str:
        """Get formatted personalization context for prompts."""
        profile = self.get_user_profile(user_id)
        recent = self.get_recent_queries(user_id, limit=3)
        
        ctx = f"""
<user_profile>
👤 USER PROFILE:
• Property Focus: {profile['property_preferences'].upper()}
• Sustainability: {profile['sustainability_focus'].upper()}
• Total Analyses: {profile['analysis_count']}
</user_profile>
"""
        
        if recent:
            ctx += "\n<recent_queries>\n📜 RECENT QUERIES:\n"
            for q in recent:
                ctx += f"  • {q['query'][:50]}... ({q['query_type']})\n"
            ctx += "</recent_queries>\n"
        
        return ctx
    
    def get_query_stats(self, user_id: str) -> Dict:
        """Get query statistics for a user."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT query_type, COUNT(*) as count
            FROM query_history
            WHERE user_id = ?
            GROUP BY query_type
        ''', (user_id,))
        
        type_counts = {r[0]: r[1] for r in cursor.fetchall()}
        
        cursor.execute('''
            SELECT category, COUNT(*) as count
            FROM query_history
            WHERE user_id = ? AND category IS NOT NULL
            GROUP BY category
        ''', (user_id,))
        
        category_counts = {r[0]: r[1] for r in cursor.fetchall()}
        
        conn.close()
        
        return {
            "by_type": type_counts,
            "by_category": category_counts,
        }
