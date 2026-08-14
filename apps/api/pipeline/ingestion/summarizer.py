"""Session summarizer using Groq LLM.

Generates concise summaries of chat sessions for storage in the memory graph.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from groq import Groq


SYSTEM_PROMPT = """You are a conversation summarizer. Your job is to create a brief, informative summary of chat sessions.

Rules:
- Summarize in exactly 1-2 sentences
- Focus on key topics, decisions, and information shared
- Use third person (e.g., "Alex discussed..." not "We discussed...")
- Ignore greetings and small talk
- Be concise but informative

Output must be valid JSON with this structure:
{
  "summary": "Your 1-2 sentence summary here."
}"""

USER_PROMPT_TEMPLATE = """Summarize this conversation session.

Session ID: {session_id}
User ID: {user_id}
Started at: {started_at}

Messages:
{messages}

Return a JSON object with a "summary" field containing a 1-2 sentence summary."""


def format_messages(messages: list[dict[str, str]]) -> str:
    """Format messages for the prompt."""
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        lines.append(f"[{role.upper()}]: {content}")
    return "\n".join(lines)


def summarize_session(
    client: Groq,
    session: dict[str, Any],
    model: str = "llama-3.1-8b-instant",
) -> dict[str, str] | None:
    """Generate a summary of a chat session.

    Args:
        client: Groq client instance
        session: Session dict with session_id, user_id, started_at, and messages
        model: Groq model to use (default: llama-3.1-8b-instant)

    Returns:
        Summary dict with summary_id, session_id, content, and generated_at
        Returns None if summarization fails
    """
    session_id = session.get("session_id", "unknown")
    user_id = session.get("user_id", "unknown")
    started_at = session.get("started_at", "unknown")
    messages = session.get("messages", [])

    if not messages:
        return None

    user_prompt = USER_PROMPT_TEMPLATE.format(
        session_id=session_id,
        user_id=user_id,
        started_at=started_at,
        messages=format_messages(messages),
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=256,
        )

        content = response.choices[0].message.content
        if not content:
            return None

        result = json.loads(content)
        summary_text = result.get("summary", "")
        if not summary_text:
            return None

        return {
            "summary_id": str(uuid.uuid4()),
            "session_id": session_id,
            "content": summary_text,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except json.JSONDecodeError:
        return None
    except Exception:
        return None


def main():
    """Test the session summarizer with a sample session."""
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    # Load .env file
    env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
    load_dotenv(env_path)

    # Check for API key
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in .env file")
        print(f"Checked: {env_path}")
        return

    client = Groq(api_key=api_key)

    # Sample session (same as extractor test)
    session = {
        "session_id": "session-001",
        "user_id": "alex-user",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [
            {"role": "user", "content": "Hi, I'm Alex and I live in Dhaka."},
            {"role": "assistant", "content": "Nice to meet you, Alex! Dhaka is a vibrant city. How do you like living there?"},
            {"role": "user", "content": "I love it here. I work as a software engineer at a tech startup."},
            {"role": "assistant", "content": "That sounds exciting! What kind of projects are you working on?"},
            {"role": "user", "content": "We're building an AI-powered memory system. By the way, I have a cat named Pixel who keeps me company while coding."},
            {"role": "assistant", "content": "Pixel sounds like a great coding companion! Cats are wonderful pets."},
        ],
    }

    print("Summarizing session...")
    print(f"Session ID: {session['session_id']}")
    print(f"Messages: {len(session['messages'])}")
    print()

    summary = summarize_session(client, session)

    if summary:
        print("Generated summary:")
        print(f"  Summary ID: {summary['summary_id']}")
        print(f"  Session ID: {summary['session_id']}")
        print(f"  Content: {summary['content']}")
        print(f"  Generated at: {summary['generated_at']}")
    else:
        print("Failed to generate summary")


if __name__ == "__main__":
    main()
