"""HydraDB writer for MemoryGraph.

Writes all extracted and processed data to the graph database.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

from db.hydra import HydraDB


def generate_int_id(unique_string: str) -> int:
    """Generate a deterministic integer ID from a string."""
    hash_bytes = hashlib.sha256(unique_string.encode()).digest()[:8]
    return int.from_bytes(hash_bytes, byteorder="big") % (10**9)


def write_to_hydradb(
    hydra: HydraDB,
    session: dict[str, Any],
    summary: dict[str, str] | None,
    facts: list[dict[str, Any]],
    supersessions: list[dict[str, str]],
    invalidations: list[dict[str, str]],
) -> dict[str, Any]:
    """Write all data to HydraDB."""
    session_id = session.get("session_id", "unknown")
    user_id = session.get("user_id", "unknown")
    started_at = session.get("started_at", datetime.now(timezone.utc).isoformat())
    messages = session.get("messages", [])

    nodes_created = 0
    edges_created = 0
    facts_written = 0

    # Build entity deduplication map
    entity_map: dict[str, int] = {}

    for fact in facts:
        entity_name = fact.get("entity_name", "")
        if entity_name and entity_name not in entity_map:
            entity_id = generate_int_id(f"entity:{user_id}:{entity_name}")
            entity_map[entity_name] = entity_id

    superseding_fact_ids = {str(sup.get("new_fact_id", "")) for sup in supersessions}
    facts_by_id = {str(fact.get("fact_id", "")): fact for fact in facts}

    user_cell_id = getattr(hydra, "get_user_cell_id", lambda u: "cell-0")(user_id) if hasattr(hydra, "get_user_cell_id") else "cell-0"
    if hasattr(hydra, "ensure_cell_exists"):
        hydra.ensure_cell_exists(user_cell_id)

    with hydra._driver.session() as db_session:
        # 1. Create Session node
        session_int_id = generate_int_id(f"session:{session_id}")
        anchor_id = session_int_id + 1000000
        db_session.run(
            "MERGE (s:Session {id: $session_int_id, session_id: $session_id, user_id: $user_id, started_at: $started_at, status: 'active'})-[:SESSION_ANCHOR]->(sa:SessionAnchor {id: $anchor_id})",
            session_int_id=session_int_id,
            session_id=session_id,
            user_id=user_id,
            started_at=started_at,
            anchor_id=anchor_id,
        )
        nodes_created += 2

        # 2. Create Message nodes + CONTAINS edges
        for i, msg in enumerate(messages):
            msg_id = f"{session_id}:msg:{i}"
            msg_int_id = generate_int_id(msg_id)
            msg_anchor_id = msg_int_id + 1000000
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            created_at = msg.get("created_at", started_at)

            db_session.run(
                "MERGE (m:Message {id: $msg_int_id, role: $role, content: $content, created_at: $created_at})-[:MESSAGE_ANCHOR]->(ma:MessageAnchor {id: $msg_anchor_id})",
                msg_int_id=msg_int_id,
                role=role,
                content=content,
                created_at=created_at,
                msg_anchor_id=msg_anchor_id,
            )
            nodes_created += 2

            db_session.run(
                "MERGE (s:Session {id: $session_int_id})-[:CONTAINS]->(m:Message {id: $msg_int_id})",
                session_int_id=session_int_id,
                msg_int_id=msg_int_id,
            )
            edges_created += 1

        # 3. Create Summary node + HAS_SUMMARY edge
        if summary:
            summary_id = summary.get("summary_id", "unknown")
            summary_int_id = generate_int_id(f"summary:{summary_id}")
            summary_anchor_id = summary_int_id + 1000000
            summary_content = summary.get("content", "")
            generated_at = summary.get("generated_at", started_at)

            db_session.run(
                "MERGE (sum:Summary {id: $summary_int_id, content: $content, created_at: $created_at})-[:SUMMARY_ANCHOR]->(sma:SummaryAnchor {id: $anchor_id})",
                summary_int_id=summary_int_id,
                content=summary_content,
                created_at=generated_at,
                anchor_id=summary_anchor_id,
            )
            nodes_created += 2

            db_session.run(
                "MERGE (s:Session {id: $session_int_id})-[:HAS_SUMMARY]->(sum:Summary {id: $summary_int_id})",
                session_int_id=session_int_id,
                summary_int_id=summary_int_id,
            )
            edges_created += 1

        # 4. Create Entity nodes
        for entity_name, entity_id in entity_map.items():
            entity_type = "person"
            entity_anchor_id = entity_id + 1000000

            db_session.run(
                "MERGE (e:Entity {id: $entity_id, user_id: $user_id, name: $name, type: $type})-[:ENTITY_ANCHOR]->(ea:EntityAnchor {id: $anchor_id})",
                entity_id=entity_id,
                user_id=user_id,
                name=entity_name,
                type=entity_type,
                anchor_id=entity_anchor_id,
            )
            nodes_created += 2

        # 5. Create Fact nodes + MENTIONS + OCCURRED_IN edges
        for fact in facts:
            fact_id = fact.get("fact_id", "unknown")
            if str(fact_id) in superseding_fact_ids:
                continue
            fact_int_id = generate_int_id(f"fact:{fact_id}")
            content = fact.get("content", "")
            confidence = fact.get("confidence", 0.5)
            entity_name = fact.get("entity_name", "")
            created_at = fact.get("created_at", started_at)

            entity_id = entity_map.get(entity_name)
            if not entity_id:
                continue

            # ✅ SET without RETURN — HydraDB compatible
            db_session.run(
                "MATCH (e:Entity {id: $entity_id}) SET e.name = $entity_name",
                entity_id=entity_id,
                entity_name=entity_name,
            )

            db_session.run(
                "MERGE (f:Fact {id: $fact_int_id, content: $content, confidence: $confidence, is_current: true, created_at: $created_at})-[:MENTIONS]->(e:Entity {id: $entity_id, user_id: $user_id, name: $entity_name})",
                fact_int_id=fact_int_id,
                content=content,
                confidence=confidence,
                created_at=created_at,
                entity_id=entity_id,
                user_id=user_id,
                entity_name=entity_name,
            )
            nodes_created += 1
            edges_created += 1
            facts_written += 1

            db_session.run(
                "MERGE (f:Fact {id: $fact_int_id})-[:OCCURRED_IN]->(s:Session {id: $session_int_id})",
                fact_int_id=fact_int_id,
                session_int_id=session_int_id,
            )
            edges_created += 1

        # 6. Create SUPERSEDES edges
        for sup in supersessions:
            new_fact_id = sup.get("new_fact_id", "")
            old_fact_id = sup.get("supersedes_fact_id", "")
            new_fact = facts_by_id.get(str(new_fact_id))
            if not new_fact:
                raise ValueError(f"Superseding fact {new_fact_id!r} was not found in the ingestion payload")

            new_fact_int_id = generate_int_id(f"fact:{new_fact_id}")
            old_fact_int_id = old_fact_id
            entity_name = new_fact.get("entity_name", "")
            entity_id = entity_map.get(entity_name)
            if not entity_id:
                raise ValueError(f"Superseding fact {new_fact_id!r} has no entity")

            with db_session.begin_transaction() as transaction:
                transaction.run(
                    "MERGE (f:Fact {id: $fact_int_id, content: $content, confidence: $confidence, is_current: true, created_at: $created_at})-[:MENTIONS]->(e:Entity {id: $entity_id, user_id: $user_id, name: $entity_name})",
                    fact_int_id=new_fact_int_id,
                    content=new_fact.get("content", ""),
                    confidence=new_fact.get("confidence", 0.5),
                    created_at=new_fact.get("created_at", started_at),
                    entity_id=entity_id,
                    user_id=user_id,
                    entity_name=entity_name,
                )
                transaction.run(
                    "MERGE (f:Fact {id: $fact_int_id})-[:OCCURRED_IN]->(s:Session {id: $session_int_id})",
                    fact_int_id=new_fact_int_id,
                    session_int_id=session_int_id,
                )
                # ✅ Simple MATCH then SET — no relationship pattern before write
                transaction.run(
                    "MATCH (f:Fact {id: $old_id}) SET f.is_current = false",
                    old_id=old_fact_int_id,
                )
                transaction.run(
                    "MATCH (f_new:Fact {id: $new_id}), (f_old:Fact {id: $old_id}) "
                    "MERGE (f_new)-[:SUPERSEDES]->(f_old)",
                    new_id=new_fact_int_id,
                    old_id=old_fact_int_id,
                )

            nodes_created += 1
            facts_written += 1
            edges_created += 3

        # 7. Invalidate stale facts
        for inv in invalidations:
            fact_id = inv.get("fact_id", "")
            reason = inv.get("reason", "expired")

            if isinstance(fact_id, int):
                fact_int_id = fact_id
            elif isinstance(fact_id, str) and fact_id.isdigit():
                fact_int_id = int(fact_id)
            else:
                fact_int_id = generate_int_id(f"fact:{fact_id}")

            with db_session.begin_transaction() as transaction:
                # ✅ Simple MATCH by id only — no relationship pattern before SET
                transaction.run(
                    "MATCH (f:Fact {id: $fact_int_id}) SET f.is_current = false",
                    fact_int_id=fact_int_id,
                )
                transaction.run(
                    "MATCH (f:Fact {id: $fact_int_id}), (s:Session {id: $session_int_id}) "
                    "MERGE (f)-[:INVALIDATED_BY {reason: $reason}]->(s)",
                    fact_int_id=fact_int_id,
                    reason=reason,
                    session_int_id=session_int_id,
                )
            edges_created += 1

    return {
        "session_id": session_id,
        "user_id": user_id,
        "cell_id": user_cell_id,
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "facts_written": facts_written,
        "supersessions_applied": len(supersessions),
        "invalidations_applied": len(invalidations),
    }


def main():
    """Test the writer with a full pipeline simulation."""
    import os
    from pathlib import Path

    from dotenv import load_dotenv
    from groq import Groq

    from pipeline.ingestion.extractor import extract_facts
    from pipeline.ingestion.summarizer import summarize_session

    env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
    load_dotenv(env_path)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in .env file")
        return

    client = Groq(api_key=api_key)
    hydra = HydraDB()
    hydra.connect()

    print("Testing HydraDB writer")
    print("=" * 50)

    try:
        with hydra._driver.session() as session:
            session.run("MATCH (n) DELETE n")
        print("Cleared database")

        sample_session = {
            "session_id": "session-001",
            "user_id": "alex-user",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [
                {"role": "user", "content": "Hi, I'm Alex and I live in Dhaka."},
                {"role": "assistant", "content": "Nice to meet you, Alex!"},
                {"role": "user", "content": "I work as a software engineer."},
                {"role": "assistant", "content": "That's great!"},
                {"role": "user", "content": "I have a cat named Pixel."},
                {"role": "assistant", "content": "Cats are wonderful!"},
            ],
        }

        print("\nStep 1: Extracting facts...")
        facts = extract_facts(client, sample_session)
        print(f"  Extracted {len(facts)} facts")

        print("\nStep 2: Generating summary...")
        summary = summarize_session(client, sample_session)
        print(f"  Summary: {summary['content'][:60]}...")

        print("\nStep 3: Writing to HydraDB...")
        write_result = write_to_hydradb(
            hydra=hydra,
            session=sample_session,
            summary=summary,
            facts=facts,
            supersessions=[],
            invalidations=[],
        )

        print(f"\nWrite summary:")
        print(f"  Session ID: {write_result['session_id']}")
        print(f"  Nodes created: {write_result['nodes_created']}")
        print(f"  Edges created: {write_result['edges_created']}")
        print(f"  Facts written: {write_result['facts_written']}")

        print("\nStep 4: Verifying data in HydraDB...")
        with hydra._driver.session() as session:
            result = session.run("MATCH (f:Fact) RETURN f.content")
            print("  Facts:")
            fact_count = 0
            for record in result:
                print(f"    - {record['f.content']}")
                fact_count += 1
            print(f"  Total facts: {fact_count}")

            result = session.run("MATCH (s:Summary) RETURN s.content")
            record = result.single()
            if record:
                print(f"  Summary: {record['s.content'][:60]}...")

            result = session.run("MATCH (s:Session) RETURN s.session_id, s.user_id")
            record = result.single()
            if record:
                print(f"  Session: {record['s.session_id']} (user: {record['s.user_id']})")

    finally:
        hydra.close()
        print("\nConnection closed")


if __name__ == "__main__":
    main()
