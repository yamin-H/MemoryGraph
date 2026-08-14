"""Fact invalidator for MemoryGraph.

Detects facts that have become stale due to time-bound conditions.
"""

import json
from datetime import datetime, timezone
from typing import Any

from groq import Groq

from db.hydra import HydraDB


SYSTEM_PROMPT = """You are a fact staleness detector. Your job is to identify facts that have become stale or expired due to time-bound conditions.

Time-bound facts that can become stale:
- "has a meeting tomorrow" - expires after the meeting time
- "is currently sick" - temporary state
- "is traveling this week" - expires after travel period
- "will be on vacation next week" - expires after vacation
- "is busy today" - expires at end of day

Permanent facts that do NOT become stale:
- "lives in Dhaka" - permanent location
- "works as a software engineer" - ongoing employment
- "has a cat named Pixel" - permanent relationship
- "name is Alex" - permanent attribute

Given a fact and the current timestamp, determine if the fact has expired.

Output must be valid JSON with this structure:
{
  "invalidations": [
    {
      "fact_content": "Alex has a meeting tomorrow",
      "is_stale": true,
      "reason": "time-bound fact has expired - meeting was scheduled for past date"
    }
  ]
}

If fact is not stale, set is_stale to false. If no facts are stale, return: {"invalidations": []}"""

USER_PROMPT_TEMPLATE = """Determine if these facts are stale given the current timestamp.

Current timestamp: {current_timestamp}

Facts to check:
{facts}

For each fact, determine if it has expired based on the current timestamp.
Return a JSON object with an "invalidations" array."""


def format_facts_for_prompt(facts: list[dict[str, Any]]) -> str:
    """Format facts for the prompt."""
    if not facts:
        return "None"
    lines = []
    for i, fact in enumerate(facts, 1):
        content = fact.get("content", "")
        created_at = fact.get("created_at", "unknown")
        lines.append(f"{i}. [{created_at}] {content}")
    return "\n".join(lines)


def detect_invalidations(
    client: Groq,
    hydra: HydraDB,
    current_session_id: str,
    model: str = "llama-3.1-8b-instant",
) -> list[dict[str, Any]]:
    """Detect facts that have become stale due to time-bound conditions.

    Args:
        client: Groq client instance
        hydra: HydraDB connection (must be connected)
        current_session_id: ID of the current session (for invalidation record)
        model: Groq model to use

    Returns:
        List of invalidation info dicts with fact_id, reason, invalidated_at_session
    """
    # Get all current facts from HydraDB
    current_facts = []
    with hydra._driver.session() as session:
        result = session.run(
            "MATCH (f:Fact {is_current: true}) RETURN f.id, f.content, f.created_at"
        )
        for record in result:
            current_facts.append({
                "fact_id": record["f.id"],
                "content": record["f.content"],
                "created_at": record["f.created_at"],
            })

    if not current_facts:
        return []

    current_timestamp = datetime.now(timezone.utc).isoformat()

    user_prompt = USER_PROMPT_TEMPLATE.format(
        current_timestamp=current_timestamp,
        facts=format_facts_for_prompt(current_facts),
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024,
        )

        content = response.choices[0].message.content
        if not content:
            return []

        result = json.loads(content)
        invalidations = result.get("invalidations", [])

        # Build invalidation list
        invalidation_results = []
        for invalidation in invalidations:
            if not invalidation.get("is_stale"):
                continue

            stale_content = invalidation.get("fact_content", "")
            if not stale_content:
                continue

            # Find matching fact ID
            fact_id = None
            for f in current_facts:
                if f["content"] == stale_content:
                    fact_id = f["fact_id"]
                    break

            if fact_id:
                # Mark fact as not current
                with hydra._driver.session() as session:
                    session.run(
                        "MATCH (f:Fact {id: $fact_id}) SET f.is_current = false",
                        fact_id=fact_id,
                    )

                invalidation_results.append({
                    "fact_id": fact_id,
                    "reason": invalidation.get("reason", "time-bound fact has expired"),
                    "invalidated_at_session": current_session_id,
                })

        return invalidation_results

    except json.JSONDecodeError:
        return []
    except Exception:
        return []


def main():
    """Test the fact invalidator."""
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    # Load .env file
    env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
    load_dotenv(env_path)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in .env file")
        return

    client = Groq(api_key=api_key)
    hydra = HydraDB()
    hydra.connect()

    print("Testing fact invalidator")
    print("=" * 50)

    try:
        # Clean up first
        with hydra._driver.session() as session:
            session.run("MATCH (n) DELETE n")
        print("Cleared database")

        # Insert a time-bound fact from 3 days ago
        # "Alex has a meeting tomorrow" - created 3 days ago, so the meeting is now in the past
        from datetime import timedelta

        three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()

        with hydra._driver.session() as session:
            session.run(
                "MERGE (f:Fact {id: 500, content: 'Alex has a meeting tomorrow', confidence: 0.9, is_current: true, created_at: $created_at})-[:MENTIONS]->(e:Entity {id: 5, name: 'Alex', type: 'person'})",
                created_at=three_days_ago,
            )
        print(f"Inserted old fact: 'Alex has a meeting tomorrow'")
        print(f"  Created at: {three_days_ago}")
        print()

        # Also insert a permanent fact that should NOT be invalidated
        with hydra._driver.session() as session:
            session.run(
                "MERGE (f:Fact {id: 501, content: 'Alex works as a software engineer', confidence: 0.95, is_current: true, created_at: $created_at})-[:MENTIONS]->(e:Entity {id: 5, name: 'Alex', type: 'person'})",
                created_at=three_days_ago,
            )
        print(f"Inserted permanent fact: 'Alex works as a software engineer'")
        print(f"  (This should NOT be invalidated)")
        print()

        # Detect invalidations
        invalidations = detect_invalidations(client, hydra, "session-test-001")

        print(f"Detected {len(invalidations)} invalidation(s):")
        for inv in invalidations:
            print(f"  Fact ID: {inv['fact_id']}")
            print(f"  Reason: {inv['reason']}")
            print(f"  Invalidated at: {inv['invalidated_at_session']}")
            print()

        # Verify facts status
        print("Verification - Facts status:")
        with hydra._driver.session() as session:
            result = session.run(
                "MATCH (f:Fact) RETURN f.id, f.content, f.is_current ORDER BY f.id"
            )
            for record in result:
                status = "CURRENT" if record["f.is_current"] else "INVALIDATED"
                print(f"  [{record['f.id']}] {record['f.content']} - {status}")

    finally:
        hydra.close()
        print()
        print("Connection closed")


if __name__ == "__main__":
    main()
