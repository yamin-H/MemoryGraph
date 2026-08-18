"""Long-context baseline - dump all sessions into LLM context."""

import os
import time
from typing import Any

from groq import Groq


class LongContextBaseline:
    """Long-context baseline using raw LLM context."""

    def __init__(self, groq_api_key: str | None = None, model: str = "llama-3.1-8b-instant"):
        """Initialize the long-context LLM baseline."""
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        self.model = model
        self._groq_client = None
        self._user_sessions: dict[str, list[dict[str, Any]]] = {}

    def _get_groq(self):
        """Get or create Groq client."""
        if self._groq_client is None and self.groq_api_key:
            self._groq_client = Groq(api_key=self.groq_api_key)
        return self._groq_client

    def add_sessions(self, sessions: list[dict[str, Any]]) -> None:
        """Store sessions by user_id."""
        for session in sessions:
            user_id = session.get("user_id", "unknown")
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = []
            self._user_sessions[user_id].append(session)

    def query(self, question: str, user_id: str) -> dict[str, Any]:
        """Query by dumping all user sessions into context."""
        start_time = time.time()
        groq = self._get_groq()

        sessions = self._user_sessions.get(user_id, [])
        if not sessions:
            return {
                "answer": "I don't have that information.",
                "confidence": 0.1,
                "abstained": True,
                "source_sessions": [],
                "latency_ms": int((time.time() - start_time) * 1000),
                "context_exceeded": False,
            }

        # Build context from all sessions
        context_parts = []
        total_chars = 0

        for session in sessions:
            session_id = session.get("session_id", "unknown")
            context_parts.append(f"=== Session {session_id} ===")
            for msg in session.get("messages", []):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                context_parts.append(f"{role}: {content}")
            total_chars += len(context_parts[-1])

        full_context = "\n".join(context_parts)

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        estimated_tokens = total_chars // 4
        context_window = 128000  # llama-3.3-70b context
        context_exceeded = estimated_tokens > context_window * 0.8

        if not groq:
            return {
                "answer": f"[No Groq client] Context: {full_context[:200]}...",
                "confidence": 0.0,
                "abstained": True,
                "source_sessions": [s.get("session_id") for s in sessions],
                "latency_ms": int((time.time() - start_time) * 1000),
                "context_exceeded": context_exceeded,
            }

        try:
            response = groq.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant with access to the user's full conversation history. Answer questions based only on the provided context. If the information is not in the context, say you don't know."
                    },
                    {
                        "role": "user",
                        "content": f"Conversation history:\n{full_context}\n\nQuestion: {question}\n\nAnswer concisely:"
                    },
                ],
                temperature=0.3,
                max_tokens=512,
            )
            answer = response.choices[0].message.content or "Unable to generate answer."

        except Exception as e:
            # Check if it's a context length error
            if "context" in str(e).lower() or "token" in str(e).lower():
                context_exceeded = True
            answer = f"Error: {str(e)}"

        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "answer": answer,
            "confidence": 0.8 if not context_exceeded else 0.3,
            "abstained": "don't know" in answer.lower() or "not in" in answer.lower() or "no information" in answer.lower(),
            "source_sessions": [s.get("session_id") for s in sessions],
            "latency_ms": latency_ms,
            "context_exceeded": context_exceeded,
            "estimated_tokens": estimated_tokens,
        }

    def clear(self) -> None:
        """Clear all stored sessions."""
        self._user_sessions.clear()

    def close(self) -> None:
        """Close resources."""
        self.clear()


def main():
    """Test the baseline."""
    print("Testing LongContextBaseline...")
    baseline = LongContextBaseline()

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
        print(f"Context exceeded: {result.get('context_exceeded')}")

    finally:
        baseline.close()
        print("Done")


if __name__ == "__main__":
    main()
