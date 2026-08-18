"""Mem0 baseline using mem0ai library."""

import os
import time
from typing import Any


class Mem0Baseline:
    """Mem0 baseline using mem0 Memory class."""

    def __init__(self, groq_api_key: str | None = None):
        """Initialize the Mem0 baseline memory system."""
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        self._memory = None

    def _get_memory(self):
        """Get or create mem0 Memory instance."""
        if self._memory is None:
            try:
                from mem0 import Memory
                # Configure mem0 to use Groq
                config = {
                    "llm": {
                        "provider": "groq",
                        "config": {
                            "model": "llama-3.1-8b-instant",
                            "api_key": self.groq_api_key,
                        }
                    },
                    "embedder": {
                        "provider": "sentence_transformers",
                        "config": {
                            "model": "sentence-transformers/all-MiniLM-L6-v2",
                        }
                    },
                    "vector_store": {
                        "provider": "chroma",
                        "config": {
                            "collection_name": "mem0_baseline",
                            "path": "./scripts/data/mem0_chroma",
                        }
                    }
                }
                self._memory = Memory.from_config(config)
            except ImportError:
                print("Warning: mem0ai not installed. Install with: pip install mem0ai")
                self._memory = None
        return self._memory

    def add_sessions(self, sessions: list[dict[str, Any]]) -> None:
        """Add sessions to mem0."""
        memory = self._get_memory()
        if memory is None:
            return

        for session in sessions:
            user_id = session.get("user_id", "unknown")
            messages = session.get("messages", [])

            # Convert to mem0 format (list of messages)
            mem0_messages = []
            for msg in messages:
                mem0_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            if mem0_messages:
                memory.add(mem0_messages, user_id=user_id)

    def query(self, question: str, user_id: str) -> dict[str, Any]:
        """Query mem0 for answer."""
        start_time = time.time()
        memory = self._get_memory()

        if memory is None:
            return {
                "answer": "Mem0 not available (mem0ai not installed)",
                "confidence": 0.0,
                "abstained": True,
                "source_sessions": [],
                "latency_ms": int((time.time() - start_time) * 1000),
            }

        try:
            # Search for relevant memories
            results = memory.search(question, user_id=user_id, limit=5)

            if not results or not results.get("results"):
                return {
                    "answer": "I don't have that information.",
                    "confidence": 0.1,
                    "abstained": True,
                    "source_sessions": [],
                    "latency_ms": int((time.time() - start_time) * 1000),
                }

            # Get memories
            memories = results["results"]
            facts_context = "\n".join(f"- {m.get('memory', '')}" for m in memories)

            # Use mem0's built-in query or generate with Groq
            try:
                response = memory.query(question, user_id=user_id)
                answer = response.get("answer", "")
            except Exception:
                # Fallback to simple generation
                answer = facts_context

        except Exception as e:
            answer = f"Error: {str(e)}"

        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "answer": answer,
            "confidence": 0.7,
            "abstained": "don't know" in answer.lower() or "not in" in answer.lower() or "no information" in answer.lower(),
            "source_sessions": [],
            "latency_ms": latency_ms,
        }

    def clear(self) -> None:
        """Clear all memories."""
        memory = self._get_memory()
        if memory:
            try:
                # Mem0 doesn't have a simple clear, reset the instance
                self._memory = None
            except Exception:
                pass

    def close(self) -> None:
        """Close resources."""
        self.clear()


def main():
    """Test the baseline."""
    print("Testing Mem0Baseline...")
    baseline = Mem0Baseline()

    try:
        sessions = [
            {
                "session_id": "test-1",
                "user_id": "alex",
                "messages": [
                    {"role": "user", "content": "I'm Alex and I live in Dhaka. I work as a software engineer."},
                    {"role": "assistant", "content": "Nice to meet you Alex!"},
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
        baseline.close()
        print("Done")


if __name__ == "__main__":
    main()
