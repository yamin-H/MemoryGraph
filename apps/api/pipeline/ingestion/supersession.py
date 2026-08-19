"""Supersession detector for MemoryGraph.

Detects when new facts contradict existing facts and should supersede them.
"""

import json
from typing import Any

from groq import Groq

from db.hydra import HydraDB


SYSTEM_PROMPT = """You are a fact contradiction detector. Your job is to identify when new facts contradict existing facts.

A contradiction occurs when:
- Same entity has conflicting attribute values (e.g., different locations, jobs)
- New information directly negates old information
- An update replaces previous knowledge

NOT a contradiction:
- Additional details about same entity (lives in Dhaka + works as engineer)
- Related but compatible facts
- Different entities with similar attributes

Output must be valid JSON with this structure:
{
  "contradictions": [
    {
      "entity_name": "Alex",
      "attribute": "location",
      "old_fact_content": "Alex lives in Rajshahi",
      "new_fact_content": "Alex lives in Dhaka",
      "reason": "location updated",
      "is_contradiction": true
    }
  ]
}

If no contradictions found, return: {"contradictions": []}"""

USER_PROMPT_TEMPLATE = """Compare these new facts against existing facts.

Existing facts:
{existing_facts}

New facts:
{new_facts}

For each potential contradiction, determine if the new fact should supersede the old fact.
Return a JSON object with a "contradictions" array."""


def format_facts_for_prompt(facts: list[dict[str, Any]]) -> str:
    """Format facts for the prompt."""
    if not facts:
        return "None"
    lines = []
    for i, fact in enumerate(facts, 1):
        content = fact.get("content", "")
        entity = fact.get("entity_name", "unknown")
        lines.append(f"{i}. [{entity}] {content}")
    return "\n".join(lines)


def detect_supersession(
    client: Groq,
    hydra: HydraDB,
    new_facts: list[dict[str, Any]],
    user_id: str,
    model: str = "openai/gpt-oss-20b",
) -> list[dict[str, Any]]:
    return _detect_supersession_impl(client, hydra, new_facts, user_id, model)

detect_supersessions = detect_supersession

def _detect_supersession_impl(
    client: Groq,
    hydra: HydraDB,
    new_facts: list[dict[str, Any]],
    user_id: str,
    model: str = "openai/gpt-oss-20b",
) -> list[dict[str, Any]]:
    """Detect facts that should be superseded by new facts.

    Args:
        client: Groq client instance
        hydra: HydraDB connection (must be connected)
        new_facts: List of new facts to check for contradictions
        user_id: Owner of the facts being ingested
        model: Groq model to use

    Returns:
        List of supersession info dicts with new_fact_id, supersedes_fact_id, reason
    """
    if not new_facts:
        return []

    # Get all current facts for the entities mentioned in new facts
    existing_facts = []
    for new_fact in new_facts:
        entity_name = new_fact.get("entity_name")
        if entity_name:
            # Query facts for this entity
            with hydra._driver.session() as session:
                result = session.run(
                    "MATCH (f:Fact {is_current: true})-[:MENTIONS]->"
                    "(e:Entity {name: $name, user_id: $user_id}) "
                    "RETURN f.id, f.content, f.is_current",
                    name=entity_name,
                    user_id=user_id,
                )
                for record in result:
                    existing_facts.append({
                        "fact_id": record["f.id"],
                        "content": record["f.content"],
                        "entity_name": entity_name,
                    })

    if not existing_facts:
        return []

    # Use LLM to detect contradictions
    user_prompt = USER_PROMPT_TEMPLATE.format(
        existing_facts=format_facts_for_prompt(existing_facts),
        new_facts=format_facts_for_prompt(new_facts),
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
    except Exception:
        try:
            response = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1024,
            )
        except Exception:
            return []

        content = response.choices[0].message.content
        if not content:
            return []

        result = json.loads(content)
        contradictions = result.get("contradictions", [])

        # Build supersession list
        supersessions = []
        for contradiction in contradictions:
            if not contradiction.get("is_contradiction"):
                continue

            old_content = contradiction.get("old_fact_content", "")
            new_content = contradiction.get("new_fact_content", "")

            # Find matching fact IDs
            old_fact_id = None
            new_fact_id = None

            for ef in existing_facts:
                if ef["content"] == old_content:
                    old_fact_id = ef["fact_id"]
                    break

            for nf in new_facts:
                if nf["content"] == new_content:
                    new_fact_id = nf["fact_id"]
                    break

            if old_fact_id and new_fact_id:
                # The writer atomically creates the replacement fact, marks this
                # fact stale, and creates the lineage edge in one transaction.
                supersessions.append({
                    "new_fact_id": new_fact_id,
                    "supersedes_fact_id": old_fact_id,
                    "reason": contradiction.get("reason", "contradiction detected"),
                })

        return supersessions

    except json.JSONDecodeError:
        return []
    except Exception:
        return []


def main():
    """Test the supersession detector."""
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

    print("Testing supersession detector")
    print("=" * 50)

    try:
        # Clean up first
        with hydra._driver.session() as session:
            session.run("MATCH (n) DELETE n")
        print("Cleared database")

        # Insert old fact: Alex lives in Rajshahi
        # HydraDB requires MERGE with relationship pattern - create fact linked to entity
        with hydra._driver.session() as session:
            # Create fact linked to entity via MENTIONS relationship
            session.run(
                "MERGE (f:Fact {id: 100, content: 'Alex lives in Rajshahi', confidence: 0.9, is_current: true, created_at: '2024-01-10T10:00:00Z'})-[:MENTIONS]->(e:Entity {id: 1, name: 'Alex', type: 'person'})"
            )
        print("Inserted old fact: 'Alex lives in Rajshahi'")

        # New fact: Alex lives in Dhaka
        new_facts = [
            {
                "fact_id": "200",
                "content": "Alex lives in Dhaka",
                "entity_name": "Alex",
                "entity_type": "person",
                "confidence": 0.95,
                "session_id": "session-002",
            }
        ]
        print(f"New fact to check: 'Alex lives in Dhaka'")
        print()

        # Detect supersession
        supersessions = detect_supersession(client, hydra, new_facts, user_id="alex-user")

        print(f"Detected {len(supersessions)} supersession(s):")
        for s in supersessions:
            print(f"  New fact: {s['new_fact_id']}")
            print(f"  Supersedes: {s['supersedes_fact_id']}")
            print(f"  Reason: {s['reason']}")
            print()

        # Verify old fact is no longer current
        with hydra._driver.session() as session:
            result = session.run(
                "MATCH (f:Fact {id: 100}) RETURN f.content, f.is_current"
            )
            record = result.single()
            if record:
                print(f"Verification - Old fact status:")
                print(f"  Content: {record['f.content']}")
                print(f"  Is current: {record['f.is_current']}")

    finally:
        hydra.close()
        print()
        print("Connection closed")


if __name__ == "__main__":
    main()
