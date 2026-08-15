#!/usr/bin/env python3
"""
Export MemoryGraph data from HydraDB to JSON.

Exports the entire graph including all nodes and edges.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Path setup
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

load_dotenv(PROJECT_ROOT / ".env")

from apps.api.db.hydra import HydraDB


def get_hydra() -> HydraDB:
    """Create HydraDB instance from environment."""
    uri = os.environ.get("HYDRADB_URI", "neo4j://127.0.0.1:7687")
    token = os.environ.get("HYDRADB_TOKEN", "local-development-token-32-bytes")
    return HydraDB(uri=uri, auth_token=token)


def export_memory(output_file: str | None = None) -> dict:
    """Export all MemoryGraph data to JSON."""
    if output_file is None:
        output_file = str(PROJECT_ROOT / "scripts" / "data" / "memory_export.json")

    hydra = get_hydra()
    hydra.connect()

    try:
        with hydra._driver.session() as session:
            # Export all node types
            print("Exporting nodes...")

            # Sessions
            result = session.run("""
                MATCH (s:Session)
                RETURN s.session_id as session_id, s.user_id as user_id,
                       s.started_at as started_at, s.status as status
            """)
            sessions = [dict(r) for r in result]
            print(f"  Sessions: {len(sessions)}")

            # Messages
            result = session.run("""
                MATCH (m:Message)
                RETURN m.id as msg_id, m.role as role, m.content as content,
                       m.created_at as created_at
            """)
            messages = [dict(r) for r in result]
            print(f"  Messages: {len(messages)}")

            # Summaries
            result = session.run("""
                MATCH (s:Summary)
                RETURN s.id as summary_id, s.content as content, s.created_at as created_at
            """)
            summaries = [dict(r) for r in result]
            print(f"  Summaries: {len(summaries)}")

            # Entities
            result = session.run("""
                MATCH (e:Entity)
                RETURN e.id as entity_id, e.name as name, e.type as type
            """)
            entities = [dict(r) for r in result]
            print(f"  Entities: {len(entities)}")

            # Facts
            result = session.run("""
                MATCH (f:Fact)
                RETURN f.id as fact_id, f.content as content, f.confidence as confidence,
                       f.is_current as is_current, f.created_at as created_at
            """)
            facts = [dict(r) for r in result]
            print(f"  Facts: {len(facts)}")

            # Export edges
            print("Exporting edges...")

            # CONTAINS (Session -> Message)
            result = session.run("""
                MATCH (s:Session)-[:CONTAINS]->(m:Message)
                RETURN s.id as session_id, m.id as message_id
            """)
            contains = [dict(r) for r in result]
            print(f"  CONTAINS: {len(contains)}")

            # HAS_SUMMARY (Session -> Summary)
            result = session.run("""
                MATCH (s:Session)-[:HAS_SUMMARY]->(sum:Summary)
                RETURN s.id as session_id, sum.id as summary_id
            """)
            has_summary = [dict(r) for r in result]
            print(f"  HAS_SUMMARY: {len(has_summary)}")

            # MENTIONS (Fact -> Entity)
            result = session.run("""
                MATCH (f:Fact)-[:MENTIONS]->(e:Entity)
                RETURN f.id as fact_id, e.id as entity_id
            """)
            mentions = [dict(r) for r in result]
            print(f"  MENTIONS: {len(mentions)}")

            # OCCURRED_IN (Fact -> Session)
            result = session.run("""
                MATCH (f:Fact)-[:OCCURRED_IN]->(s:Session)
                RETURN f.id as fact_id, s.id as session_id
            """)
            occurred_in = [dict(r) for r in result]
            print(f"  OCCURRED_IN: {len(occurred_in)}")

            # SUPERSEDES (Fact -> Fact)
            result = session.run("""
                MATCH (f1:Fact)-[:SUPERSEDES]->(f2:Fact)
                RETURN f1.id as new_fact_id, f2.id as old_fact_id
            """)
            supersedes = [dict(r) for r in result]
            print(f"  SUPERSEDES: {len(supersedes)}")

            # INVALIDATED_BY (Fact -> Session)
            result = session.run("""
                MATCH (f:Fact)-[r:INVALIDATED_BY]->(s:Session)
                RETURN f.id as fact_id, s.id as session_id, r.reason as reason
            """)
            invalidated_by = [dict(r) for r in result]
            print(f"  INVALIDATED_BY: {len(invalidated_by)}")

            # Build export structure
            export_data = {
                "exported_at": datetime.now().isoformat() + "Z",
                "stats": {
                    "sessions": len(sessions),
                    "facts": len(facts),
                    "entities": len(entities),
                    "supersessions": len(supersedes),
                    "invalidations": len(invalidated_by),
                },
                "nodes": {
                    "sessions": sessions,
                    "messages": messages,
                    "summaries": summaries,
                    "facts": facts,
                    "entities": entities,
                },
                "edges": {
                    "contains": contains,
                    "has_summary": has_summary,
                    "mentions": mentions,
                    "occurred_in": occurred_in,
                    "supersedes": supersedes,
                    "invalidated_by": invalidated_by,
                }
            }

            # Write to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(export_data, indent=2))

            print(f"\nExport complete!")
            print(f"  File: {output_path}")
            print(f"  Sessions: {len(sessions)}")
            print(f"  Facts: {len(facts)}")
            print(f"  Entities: {len(entities)}")
            print(f"  Messages: {len(messages)}")
            print(f"  Summaries: {len(summaries)}")
            print(f"  Total edges: {len(contains) + len(has_summary) + len(mentions) + len(occurred_in) + len(supersedes) + len(invalidated_by)}")

            return export_data

    finally:
        hydra.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Export MemoryGraph from HydraDB")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    export_memory(args.output)


if __name__ == "__main__":
    main()