"""Database operations for EtymoBot."""

import sqlite3
import time
import logging
from typing import List, Optional, Tuple
from contextlib import contextmanager
from .models import WordPair
from .config import Config

logger = logging.getLogger(__name__)


class EtymoBotDatabase:
    """Handles all database operations for EtymoBot."""

    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def connect(self) -> None:
        """Connect to the database and initialize tables."""
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,  # 30 second timeout for locks
                check_same_thread=False
            )
            # Enable foreign key constraints and WAL mode for better performance
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.conn.execute("PRAGMA synchronous = NORMAL")

            self.cursor = self.conn.cursor()
            self._init_tables()
            self._create_indexes()
            logger.info("Database connected and initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def close(self) -> None:
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None

    def _init_tables(self) -> None:
        """Initialize database tables."""
        # Root-word mappings cache
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS rootmap (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                root TEXT NOT NULL,
                word TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                UNIQUE(root, word)
            )
        """)

        # Posted pairs tracking
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS posted (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word1 TEXT NOT NULL,
                word2 TEXT NOT NULL,
                root TEXT NOT NULL,
                tweet_id TEXT NOT NULL,
                posted_at INTEGER NOT NULL,
                UNIQUE(word1, word2)
            )
        """)

        # Failed attempts tracking
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS failed_words (
                word TEXT PRIMARY KEY,
                failure_count INTEGER NOT NULL DEFAULT 1,
                last_failure INTEGER NOT NULL,
                CHECK(failure_count > 0)
            )
        """)

        self.conn.commit()

    def _create_indexes(self) -> None:
        """Create database indexes for performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_rootmap_root ON rootmap(root)",
            "CREATE INDEX IF NOT EXISTS idx_rootmap_word ON rootmap(word)",
            "CREATE INDEX IF NOT EXISTS idx_rootmap_created_at ON rootmap(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_posted_words ON posted(word1, word2)",
            "CREATE INDEX IF NOT EXISTS idx_posted_root ON posted(root)",
            "CREATE INDEX IF NOT EXISTS idx_posted_at ON posted(posted_at)",
            "CREATE INDEX IF NOT EXISTS idx_failed_words_count ON failed_words(failure_count)",
        ]

        for index_sql in indexes:
            try:
                self.cursor.execute(index_sql)
            except sqlite3.Error as e:
                logger.warning(f"Failed to create index: {e}")

        self.conn.commit()

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        try:
            yield self.cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Transaction failed, rolling back: {e}")
            raise

    def add_root_mapping(self, root: str, word: str) -> bool:
        """Add a root-word mapping to the cache."""
        try:
            with self.transaction():
                current_time = int(time.time())
                self.cursor.execute("""
                    INSERT OR IGNORE INTO rootmap (root, word, created_at)
                    VALUES (?, ?, ?)
                """, (root.lower().strip(), word.lower().strip(), current_time))
                return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to add root mapping {root}->{word}: {e}")
            return False

    def get_cache_size(self) -> int:
        """Get the current size of the root cache."""
        try:
            result = self.cursor.execute("SELECT COUNT(*) FROM rootmap").fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get cache size: {e}")
            return 0

    def get_roots_with_multiple_words(self, limit: int = 20) -> List[Tuple[str, int]]:
        """Get roots that have multiple words associated with them."""
        try:
            self.cursor.execute("""
                SELECT root, COUNT(*) as word_count
                FROM rootmap
                GROUP BY root
                HAVING word_count >= 2
                ORDER BY RANDOM()
                LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get roots with multiple words: {e}")
            return []

    def get_words_for_root(self, root: str) -> List[str]:
        """Get all words associated with a root."""
        try:
            self.cursor.execute("SELECT word FROM rootmap WHERE root = ?", (root.lower().strip(),))
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get words for root {root}: {e}")
            return []

    def is_pair_posted(self, word1: str, word2: str) -> bool:
        """Check if a word pair has already been posted."""
        try:
            # Normalize words
            w1, w2 = word1.lower().strip(), word2.lower().strip()
            self.cursor.execute("""
                SELECT 1 FROM posted
                WHERE (word1 = ? AND word2 = ?) OR (word1 = ? AND word2 = ?)
                LIMIT 1
            """, (w1, w2, w2, w1))
            return self.cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check if pair posted: {e}")
            return True  # Conservative: assume posted if check fails

    def record_posted_pair(self, pair: WordPair, tweet_id: str) -> bool:
        """Record a posted word pair."""
        try:
            with self.transaction():
                current_time = int(time.time())
                self.cursor.execute("""
                    INSERT INTO posted (word1, word2, root, tweet_id, posted_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (pair.word1, pair.word2, pair.root, tweet_id, current_time))
                return True
        except Exception as e:
            logger.error(f"Failed to record posted pair: {e}")
            return False

    def record_word_failure(self, word: str) -> None:
        """Record a word failure for future avoidance."""
        try:
            with self.transaction():
                current_time = int(time.time())
                normalized_word = word.lower().strip()
                self.cursor.execute("""
                    INSERT OR REPLACE INTO failed_words (word, failure_count, last_failure)
                    VALUES (?, COALESCE((SELECT failure_count FROM failed_words WHERE word = ?) + 1, 1), ?)
                """, (normalized_word, normalized_word, current_time))
        except Exception as e:
            logger.error(f"Failed to record word failure: {e}")

    def is_word_problematic(self, word: str) -> bool:
        """Check if a word has failed too many times recently."""
        try:
            normalized_word = word.lower().strip()
            self.cursor.execute(
                "SELECT failure_count FROM failed_words WHERE word = ? AND failure_count >= ?",
                (normalized_word, self.config.max_word_failures)
            )
            return self.cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check if word is problematic: {e}")
            return False

    def get_posts_in_hour_range(self, hour_start: int, hour_end: int) -> int:
        """Get number of posts in a specific hour range."""
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM posted
                WHERE posted_at >= ? AND posted_at < ?
            """, (hour_start, hour_end))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get posts in hour range: {e}")
            return 0

    def get_database_stats(self) -> dict:
        """Get comprehensive database statistics."""
        try:
            stats = {}

            # Cache statistics
            stats['cache_size'] = self.get_cache_size()

            # Root statistics
            result = self.cursor.execute("""
                SELECT COUNT(DISTINCT root) FROM rootmap
            """).fetchone()
            stats['unique_roots'] = result[0] if result else 0

            # Posted statistics
            result = self.cursor.execute("SELECT COUNT(*) FROM posted").fetchone()
            stats['total_posted'] = result[0] if result else 0

            # Failed words statistics
            result = self.cursor.execute("SELECT COUNT(*) FROM failed_words").fetchone()
            stats['failed_words'] = result[0] if result else 0

            # Recent activity (last 24 hours)
            recent_cutoff = int(time.time()) - 86400
            result = self.cursor.execute(
                "SELECT COUNT(*) FROM posted WHERE posted_at >= ?", (recent_cutoff,)
            ).fetchone()
            stats['posts_last_24h'] = result[0] if result else 0

            return stats
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    def cleanup_old_failures(self, days_old: int = 7) -> int:
        """Clean up old word failures to allow retry."""
        try:
            with self.transaction():
                cutoff_time = int(time.time()) - (days_old * 86400)
                self.cursor.execute(
                    "DELETE FROM failed_words WHERE last_failure < ?", (cutoff_time,)
                )
                return self.cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to cleanup old failures: {e}")
            return 0

    def commit(self) -> None:
        """Commit current transaction."""
        if self.conn:
            try:
                self.conn.commit()
            except Exception as e:
                logger.error(f"Failed to commit transaction: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
