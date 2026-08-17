"""Integrating MemoryGraph with an AI Agent or LangChain application."""

import sys
from pathlib import Path

# Add src to sys.path
src_dir = str(Path(__file__).resolve().parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from memorygraph import MemoryGraph


class AgentWithMemoryGraph:
    """Example AI Agent with native HydraDB temporal memory."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory = MemoryGraph(api_url="http://localhost:8000")

    def remember(self, user_message: str, assistant_response: str):
        """Store interaction turn into the HydraDB knowledge graph."""
        return self.memory.add_session(
            user_id=self.user_id,
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response},
            ],
        )

    def recall(self, question: str) -> str:
        """Recall verified, current facts with honest abstention."""
        result = self.memory.query(user_id=self.user_id, query=question)
        if result.abstained:
            return f"[Honest Abstention] {result.answer}"
        return f"[MemoryGraph Verified ({int(result.confidence * 100)}%)] {result.answer}"


def main():
    agent = AgentWithMemoryGraph(user_id="demo-agent-user")
    print("Agent initialized with MemoryGraph temporal layer.")
    print("Example recall response:", agent.recall("Where do I work?"))


if __name__ == "__main__":
    main()
