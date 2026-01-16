"""SQLite storage for embeddings.

Stores embedding vectors as JSON blobs in SQLite.
Uses cosine similarity for search operations.
"""

import json
import math
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class EmbeddingRecord:
    """A stored embedding with metadata."""

    id: str
    entity_type: str  # "concept", "outcome", "session"
    entity_id: str
    learner_id: str
    text: str  # Original text that was embedded
    embedding: list[float]
    created_at: datetime
    updated_at: datetime


EMBEDDING_SCHEMA = """
CREATE TABLE IF NOT EXISTS embeddings (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    learner_id TEXT NOT NULL,
    text TEXT NOT NULL,
    embedding JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_embeddings_entity ON embeddings(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_learner ON embeddings(learner_id, entity_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_unique ON embeddings(entity_type, entity_id);
"""


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


class EmbeddingStore:
    """SQLite storage for embeddings with similarity search."""

    def __init__(self, db_path: str | Path = ":memory:"):
        """Initialize the embedding store.

        Args:
            db_path: Path to SQLite database, or ":memory:" for in-memory.
        """
        self.db_path = str(db_path)
        self._is_memory = self.db_path == ":memory:"
        self._persistent_conn: Optional[sqlite3.Connection] = None

        if self._is_memory:
            self._persistent_conn = sqlite3.connect(":memory:")
            self._persistent_conn.row_factory = sqlite3.Row

        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with schema."""
        with self.connection() as conn:
            conn.executescript(EMBEDDING_SCHEMA)

    @contextmanager
    def connection(self):
        """Get a database connection."""
        if self._is_memory:
            yield self._persistent_conn
            self._persistent_conn.commit()
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def store(
        self,
        entity_type: str,
        entity_id: str,
        learner_id: str,
        text: str,
        embedding: list[float],
    ) -> EmbeddingRecord:
        """Store or update an embedding.

        Args:
            entity_type: Type of entity ("concept", "outcome", "session")
            entity_id: ID of the entity
            learner_id: ID of the learner
            text: Original text that was embedded
            embedding: The embedding vector

        Returns:
            The stored embedding record
        """
        now = datetime.utcnow()
        record_id = f"{entity_type}:{entity_id}"

        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO embeddings (id, entity_type, entity_id, learner_id, text, embedding, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                    text = excluded.text,
                    embedding = excluded.embedding,
                    updated_at = excluded.updated_at
                """,
                (
                    record_id,
                    entity_type,
                    entity_id,
                    learner_id,
                    text,
                    json.dumps(embedding),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )

        return EmbeddingRecord(
            id=record_id,
            entity_type=entity_type,
            entity_id=entity_id,
            learner_id=learner_id,
            text=text,
            embedding=embedding,
            created_at=now,
            updated_at=now,
        )

    def get(self, entity_type: str, entity_id: str) -> Optional[EmbeddingRecord]:
        """Get an embedding by entity type and ID."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM embeddings WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_record(row)

    def delete(self, entity_type: str, entity_id: str) -> bool:
        """Delete an embedding."""
        with self.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM embeddings WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            )
            return cursor.rowcount > 0

    def search_similar(
        self,
        query_embedding: list[float],
        learner_id: str,
        entity_type: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.5,
    ) -> list[tuple[EmbeddingRecord, float]]:
        """Find similar embeddings by cosine similarity.

        Args:
            query_embedding: The embedding to search for
            learner_id: Limit search to this learner's embeddings
            entity_type: Optional filter by entity type
            limit: Maximum number of results
            threshold: Minimum similarity score (0-1)

        Returns:
            List of (record, similarity_score) tuples, sorted by similarity
        """
        with self.connection() as conn:
            query = "SELECT * FROM embeddings WHERE learner_id = ?"
            params: list = [learner_id]

            if entity_type:
                query += " AND entity_type = ?"
                params.append(entity_type)

            rows = conn.execute(query, params).fetchall()

        results = []
        for row in rows:
            record = self._row_to_record(row)
            similarity = _cosine_similarity(query_embedding, record.embedding)
            if similarity >= threshold:
                results.append((record, similarity))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_all_for_learner(
        self, learner_id: str, entity_type: Optional[str] = None
    ) -> list[EmbeddingRecord]:
        """Get all embeddings for a learner."""
        with self.connection() as conn:
            query = "SELECT * FROM embeddings WHERE learner_id = ?"
            params: list = [learner_id]

            if entity_type:
                query += " AND entity_type = ?"
                params.append(entity_type)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> EmbeddingRecord:
        """Convert database row to EmbeddingRecord."""
        return EmbeddingRecord(
            id=row["id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            learner_id=row["learner_id"],
            text=row["text"],
            embedding=json.loads(row["embedding"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
