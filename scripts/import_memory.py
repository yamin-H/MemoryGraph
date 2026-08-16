#!/usr/bin/env python3
"""
Import MemoryGraph data from JSON to HydraDB.

Reads export file and recreates all nodes and edges in correct order.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Path setup
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

load_dotenv(PROJECT_ROOT / ".env")

from apps.api.db.hydra import HydraDB


def generate_int_id(unique_string: str) -> int:
    """Generate a deterministic integer ID from a string (matches writer.py)."""
    hash_bytes = hashlib.sha256(unique_string.encode()).digest()[:8]
    return int.from_bytes(hash_bytes, byteorder="big") % (10**9)


def get_hydra() -> HydraDB:
    """Create HydraDB instance from environment configuration."""
    from apps.api.config import settings
    return HydraDB(uri=settings.hydra_uri, auth_token=settings.hydra_token)


def confirm_clear():
    """Ask user to confirm before clearing database."""
    print("⚠️  This will DELETE ALL EXISTING DATA in HydraDB.")
    response = input("Type 'yes' to confirm clearing the database: ")
    return response.strip().lower() == "yes"


def import_memory(input_file: str | None = None, force: bool = False) -> dict:
    """Import MemoryGraph data from JSON into HydraDB."""
    if input_file is None:
        input_file = str(PROJECT_ROOT / "scripts" / "data" / "memory_export.json")

    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Export file not found: {input_path}")

    print(f"Loading export from {input_path}...")
    export_data = json.loads(input_path.read_text())

    stats = export_data.get("stats", {})
    nodes = export_data.get("nodes", {})
    edges = export_data.get("edges", {})

    print(f"Export stats:")
    print(f"  Sessions: {stats.get('sessions', 0)}")
    print(f"  Facts: {stats.get('facts', 0)}")
    print(f"  Entities: {stats.get('entities', 0)}")
    print(f"  Messages: {len(nodes.get('messages', []))}")
    print(f"  Summaries: {len(nodes.get('summaries', []))}")

    hydra = get_hydra()
    hydra.connect()

    try:
        with hydra._driver.session() as session:
            # Clear database if requested
            if force or confirm_clear():
                print("\nClearing existing database...")
                session.run("MATCH ()-[r]-() DELETE r")
                session.run("MATCH (n) DELETE n")
                print("Database cleared.")
            else:
                print("Import cancelled.")
                return {"cancelled": True}

            # Import nodes in correct order
            print("\nImporting nodes...")

            # 1. Sessions
            print("  1/5: Sessions...")
            for s in nodes.get("sessions", []):
                session_id_str = s.get("session_id", "")
                if not session_id_str:
                    continue
                session_int_id = generate_int_id(f"session:{session_id_str}")
                anchor_id = session_int_id + 1000000
                session.run("""
                    MERGE (s:Session {id: $session_int_id, session_id: $session_id,
                           user_id: $user_id, started_at: $started_at, status: $status})
                    MERGE (a:SessionAnchor {id: $anchor_id})
                    MERGE (s)-[:SESSION_ANCHOR]->(a)
                """, session_int_id=session_int_id, session_id=session_id_str,
                   user_id=s.get("user_id", ""), started_at=s.get("started_at", ""), status=s.get("status", "active"),
                   anchor_id=anchor_id)

            # 2. Entities
            print("  2/5: Entities...")
            for e in nodes.get("entities", []):
                entity_name = e.get("name", "")
                if not entity_name:
                    continue
                entity_int_id = generate_int_id(f"entity:{entity_name}")
                anchor_id = entity_int_id + 1000000
                session.run("""
                    MERGE (e:Entity {id: $entity_id, name: $name, type: $type})
                    MERGE (a:EntityAnchor {id: $anchor_id})
                    MERGE (e)-[:ENTITY_ANCHOR]->(a)
                """, entity_id=entity_int_id, name=entity_name, type=e.get("type", "concept"),
                   anchor_id=anchor_id)

            # 3. Messages
            print("  3/5: Messages...")
            for m in nodes.get("messages", []):
                msg_id_str = m.get("msg_id", "")
                role = m.get("role", "")
                content = m.get("content", "")
                if not msg_id_str or role is None or content is None:
                    continue
                msg_int_id = generate_int_id(f"message:{msg_id_str}")
                anchor_id = msg_int_id + 1000000
                session.run("""
                    MERGE (m:Message {id: $msg_int_id, role: $role, content: $content, created_at: $created_at})
                    MERGE (a:MessageAnchor {id: $anchor_id})
                    MERGE (m)-[:MESSAGE_ANCHOR]->(a)
                """, msg_int_id=msg_int_id, role=role, content=content,
                   created_at=m.get("created_at", ""), anchor_id=anchor_id)

            # 4. Summaries
            print("  4/5: Summaries...")
            for s in nodes.get("summaries", []):
                summary_id_str = s.get("summary_id", "")
                content = s.get("content", "")
                if not summary_id_str or content is None:
                    continue
                summary_int_id = generate_int_id(f"summary:{summary_id_str}")
                anchor_id = summary_int_id + 1000000
                session.run("""
                    MERGE (sum:Summary {id: $summary_int_id, content: $content, created_at: $created_at})
                    MERGE (a:SummaryAnchor {id: $anchor_id})
                    MERGE (sum)-[:SUMMARY_ANCHOR]->(a)
                """, summary_int_id=summary_int_id, content=content,
                   created_at=s.get("created_at", ""), anchor_id=anchor_id)

            # 5. Facts
            print("  5/5: Facts...")
            for f in nodes.get("facts", []):
                fact_id_str = f.get("fact_id", "")
                content = f.get("content", "")
                if not fact_id_str or content is None:
                    continue
                fact_int_id = generate_int_id(f"fact:{fact_id_str}")
                anchor_id = fact_int_id + 1000000
                session.run("""
                    MERGE (f:Fact {id: $fact_int_id, content: $content, confidence: $confidence,
                           is_current: $is_current, created_at: $created_at})
                    MERGE (a:FactAnchor {id: $anchor_id})
                    MERGE (f)-[:FACT_ANCHOR]->(a)
                """, fact_int_id=fact_int_id, content=content,
                   confidence=f.get("confidence", 0.5),
                   is_current=f.get("is_current", True),
                   created_at=f.get("created_at", ""), anchor_id=anchor_id)

            print("Nodes imported. Now importing edges...")

            # Import edges - need to convert string IDs to int IDs
            edge_counts = {}

            # CONTAINS (Session -> Message)
            print("  CONTAINS...")
            count = 0
            for e in edges.get("contains", []):
                session_id_str = e.get("session_id", "")
                message_id_str = e.get("message_id", "")
                if not session_id_str or not message_id_str:
                    continue
                session_int_id = generate_int_id(f"session:{session_id_str}")
                message_int_id = generate_int_id(f"message:{message_id_str}")
                session.run("""
                    MATCH (s:Session {id: $session_id}), (m:Message {id: $message_id})
                    MERGE (s)-[:CONTAINS]->(m)
                """, session_id=session_int_id, message_id=message_int_id)
                count += 1
            edge_counts["contains"] = count
            print(f"    {count} edges")

            # HAS_SUMMARY (Session -> Summary)
            print("  HAS_SUMMARY...")
            count = 0
            for e in edges.get("has_summary", []):
                session_id_str = e.get("session_id", "")
                summary_id_str = e.get("summary_id", "")
                if not session_id_str or not summary_id_str:
                    continue
                session_int_id = generate_int_id(f"session:{session_id_str}")
                summary_int_id = generate_int_id(f"summary:{summary_id_str}")
                session.run("""
                    MATCH (s:Session {id: $session_id}), (sum:Summary {id: $summary_id})
                    MERGE (s)-[:HAS_SUMMARY]->(sum)
                """, session_id=session_int_id, summary_id=summary_int_id)
                count += 1
            edge_counts["has_summary"] = count
            print(f"    {count} edges")

            # MENTIONS (Fact -> Entity)
            print("  MENTIONS...")
            count = 0
            for e in edges.get("mentions", []):
                session.run("""
                    MATCH (f:Fact {id: $fact_id}), (e:Entity {id: $entity_id})
                    MERGE (f)-[:MENTIONS]->(e)
                """, fact_id=e["fact_id"], entity_id=e["entity_id"])
                count += 1
            edge_counts["mentions"] = count
            print(f"    {count} edges")

            # OCCURRED_IN (Fact -> Session)
            print("  OCCURRED_IN...")
            count = 0
            for e in edges.get("occurred_in", []):
                session.run("""
                    MATCH (f:Fact {id: $fact_id}), (s:Session {id: $session_id})
                    MERGE (f)-[:OCCURRED_IN]->(s)
                """, fact_id=e["fact_id"], session_id=e["session_id"])
                count += 1
            edge_counts["occurred_in"] = count
            print(f"    {count} edges")

            # SUPERSEDES (Fact -> Fact)
            print("  SUPERSEDES...")
            count = 0
            for e in edges.get("supersedes", []):
                session.run("""
                    MATCH (f1:Fact {id: $new_fact_id}), (f2:Fact {id: $old_fact_id})
                    MERGE (f1)-[:SUPERSEDES]->(f2)
                """, new_fact_id=e["new_fact_id"], old_fact_id=e["old_fact_id"])
                count += 1
            edge_counts["supersedes"] = count
            print(f"    {count} edges")

            # INVALIDATED_BY (Fact -> Session)
            print("  INVALIDATED_BY...")
            count = 0
            for e in edges.get("invalidated_by", []):
                session.run("""
                    MATCH (f:Fact {id: $fact_id}), (s:Session {id: $session_id})
                    MERGE (f)-[:INVALIDATED_BY {reason: $reason}]->(s)
                """, fact_id=e["fact_id"], session_id=e["session_id"], reason=e.get("reason", "expired"))
                count += 1
            edge_counts["invalidated_by"] = count
            print(f"    {count} edges")

            # Verify import
            print("\nVerifying import...")
            verify_counts = {}
            for label in ["Session", "Message", "Summary", "Entity", "Fact"]:
                result = session.run(f"MATCH (n:{label}) RETURN count(n) as c")
                verify_counts[label.lower() + "s"] = result.single()["c"]

            print("\nImport complete!")
            print(f"  Sessions: {verify_counts.get('sessions', 0)}")
            print(f"  Messages: {verify_counts.get('messages', 0)}")
            print(f"  Summaries: {verify_counts.get('summaries', 0)}")
            print(f"  Entities: {verify_counts.get('entities', 0)}")
            print(f"  Facts: {verify_counts.get('facts', 0)}")
            print(f"  Total edges: {sum(edge_counts.values())}")

            return {
                "imported": verify_counts,
                "edges": edge_counts,
                "original_stats": stats,
            }

    finally:
        hydra.close()


def main():
    """CLI entrypoint to restore MemoryGraph nodes and relationships from JSON."""
    import argparse
    parser = argparse.ArgumentParser(description="Import MemoryGraph into HydraDB")
    parser.add_argument("--input", "-i", help="Input file path")
    parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    import_memory(args.input, args.force)


if __name__ == "__main__":
    main()