"""Vector baseline using pgvector + PostgreSQL."""

import os
import time
import uuid
from typing import Any

import psycopg
from groq import Groq
from sentence_transformers import SentenceTransformer


class VectorBaseline:
    """Vector similarity baseline using pgvector."""

    def __init__(self, postgres_url: str | None = None, groq_api_key: str | None = None):
        self.postgres_url = postgres_url or os.environ.get("POSTGRES_URL", "postgresql://localhost:5432/memorygraph_baseline")
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        self._conn = None
        self._encoder = None
        self._groq_client = None

    def _get_connection(self):
        """Get or create PostgreSQL connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self.postgres_url)
            self._conn.autocommit = True
            self._init_db()
        return self._conn

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id UUID PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR(384),
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_facts_embedding ON facts USING hnsw (embedding vector_cosine_ops)")

    def _get_encoder(self):
        """Get or create sentence transformer encoder."""
        if self._encoder is None:
            self._encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return self._encoder

    def _get_groq(self):
        """Get or create Groq client."""
        if self._groq_client is None and self.groq_api_key:
            self._groq_client = Groq(api_key=self.groq_api_key)
        return self._groq_client

    def add_sessions(self, sessions: list[dict[str, Any]]) -> None:
        """Add sessions by extracting facts and storing embeddings."""
        conn = self._get_connection()
        encoder = self._get_encoder()

        for session in sessions:
            user_id = session.get("user_id", "unknown")
            session_id = session.get("session_id", str(uuid.uuid4()))
            messages = session.get("messages", [])

            # Extract facts from user messages
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if content.strip():
                        # Simple fact extraction - split by sentences
                        sentences = [s.strip() for s in content.split(".") if s.strip()]
                        for sentence in sentences:
                            if len(sentence) > 10:  # Filter very short
                                embedding = encoder.encode(sentence).tolist()
                                fact_id = uuid.uuid4()

                                with conn.cursor() as cur:
                                    cur.execute(
                                        "INSERT INTO facts (id, user_id, content, embedding, session_id) VALUES (%s, %s, %s, %s, %s)",
                                        (fact_id, user_id, sentence, embedding, session_id)
                                    )

    def query(self, question: str, user_id: str) -> dict[str, Any]:
        """Query using vector similarity search."""
        start_time = time.time()
        encoder = self._get_encoder()
        groq = self._get_groq()

        # Embed question
        question_embedding = encoder.encode(question).tolist()

        conn = self._get_connection()
        with conn.cursor() as cur:
            # Find top-5 similar facts for this user
            cur.execute("""
                SELECT content, 1 - (embedding <=> %s::vector) as similarity
                FROM facts
                WHERE user_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT 5
            """, (question_embedding, user_id, question_embedding))

            results = cur.fetchall()

        if not results:
            return {
                "answer": "I don't have that information.",
                "confidence": 0.1,
                "abstained": True,
                "source_sessions": [],
                "latency_ms": int((time.time() - start_time) * 1000),
            }

        # Get top facts
        facts_context = "\n".join(f"- {row[0]}" for row in results)

        # Generate answer using Groq
        if groq:
            try:
                response = groq.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "Answer based only on the provided facts. If facts don't answer, say you don't know."},
                        {"role": "user", "content": f"Question: {question}\n\nFacts:\n{facts_context}\n\nAnswer concisely:"},
                    ],
                    temperature=0.3,
                    max_tokens=256,
                )
                answer = response.choices[0].message.content or "Unable to generate answer."
            except Exception:
                answer = facts_context  # Fallback
        else:
            answer = facts_context

        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "answer": answer,
            "confidence": 0.7,
            "abstained": False,
            "source_sessions": list(set(r[2] for r in results if len(r) > 2)),
            "latency_ms": latency_ms,
        }

    def clear(self) -> None:
        """Clear all facts."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM facts")

    def close(self) -> None:
        """Close connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None


def main():
    """Test the baseline."""
    print("Testing VectorBaseline...")
    baseline = VectorBaseline()

    try:
        # Add sample sessions
        sessions = [
            {
                "session_id": "test-1",
                "user_id": "alex",
                "messages": [
                    {"role": "user", "content": "I'm Alex and I live in Dhaka. I work as a software engineer."},
                    {"role": "assistant", "content": "Nice!"},
                ],
            }
        ]

        print("Adding sessions...")
        baseline.add_sessions(sessions)

        print("Querying...")
        result = baseline.query("Where does Alex live?", "alex")
        print(f"Answer: {result['answer']}")
        print(f"Latency: {result['latency_ms']}ms")

    finally:
        baseline.clear()
        baseline.close()
        print("Done")


if __name__ == "__main__":
    main()