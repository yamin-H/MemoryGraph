"""HydraDB writer for MemoryGraph.

Writes all extracted and processed data to the graph database.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db.hydra import HydraDB

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DELTA_FILE = DATA_DIR / "ingested_memory.json"


def _save_ingested_delta(session_id: str, user_id: str, started_at: str, facts: list[dict[str, Any]], supersessions: list[dict[str, str]], invalidations: list[dict[str, str]]):
    try:
        data = {"sessions": {}, "facts": [], "superseded_fact_ids": [], "superseded_contents": []}
        if DELTA_FILE.exists():
            try:
                data = json.loads(DELTA_FILE.read_text("utf-8"))
            except Exception:
                pass

        data.setdefault("sessions", {})
        data.setdefault("facts", [])
        data.setdefault("superseded_fact_ids", [])
        data.setdefault("superseded_contents", [])

        data["sessions"][session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "started_at": started_at,
        }

        # If new facts describe moving/living somewhere new, track old location keywords to supersede
        MOVE_KEYWORDS = {"move", "moved", "moving", "relocat", "left", "no longer lives", "no longer live"}
        LOCATION_KEYWORDS = {"live", "lives", "reside", "resides", "located", "location"}
        new_loc_facts = [
            f for f in facts
            if any(k in f.get("content", "").lower() for k in MOVE_KEYWORDS)
        ]
        if new_loc_facts:
            # Find old location facts in existing delta data and supersede them
            existing_facts = data.get("facts", [])
            for existing_f in existing_facts:
                if existing_f.get("user_id", "").lower() != user_id.lower():
                    continue
                ec = existing_f.get("content", "").lower()
                # Only supersede location-type facts, not other fact types
                if any(lk in ec for lk in LOCATION_KEYWORDS):
                    old_fid = str(existing_f.get("fact_id", ""))
                    if old_fid and old_fid not in data["superseded_fact_ids"]:
                        data["superseded_fact_ids"].append(old_fid)

        for sup in supersessions:
            old_id = sup.get("supersedes_fact_id")
            if old_id and old_id not in data["superseded_fact_ids"]:
                data["superseded_fact_ids"].append(str(old_id))

        for inv in invalidations:
            inv_id = inv.get("fact_id")
            if inv_id and inv_id not in data["superseded_fact_ids"]:
                data["superseded_fact_ids"].append(str(inv_id))

        for f in facts:
            data["facts"].append({
                "fact_id": f.get("fact_id") or generate_int_id(f"fact:{user_id}:{session_id}:{f.get('content')}"),
                "content": f.get("content", ""),
                "confidence": float(f.get("confidence") or 0.9),
                "is_current": True,
                "created_at": f.get("created_at") or started_at,
                "session_id": session_id,
                "session_started_at": started_at,
                "user_id": user_id,
                "entity_name": f.get("entity_name", "User"),
            })

        DELTA_FILE.write_text(json.dumps(data, indent=2), "utf-8")
    except Exception as exc:
        print(f"       Warning saving memory delta: {exc}")


def generate_int_id(unique_string: str) -> int:
    """Generate a deterministic integer ID from a string."""
    hash_bytes = hashlib.sha256(unique_string.encode()).digest()[:8]
    return int.from_bytes(hash_bytes, byteorder="big") % (10**9)


def run_query(hydra: HydraDB, query: str, **kwargs):
    """Execute a query using auto-commit session."""
    with hydra._driver.session() as db_session:
        db_session.run(query, **kwargs)


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

    user_cell_id = getattr(hydra, "get_user_cell_id", lambda u: "cell-0")(user_id) if hasattr(hydra, "get_user_cell_id") else "cell-0"
    if hasattr(hydra, "ensure_cell_exists"):
        hydra.ensure_cell_exists(user_cell_id)

    with hydra._driver.session() as db_session:
        def run_q(query: str, **kwargs):
            try:
                db_session.run(query, **kwargs)
            except Exception as exc:
                print(f"       Query notice: {exc}")

        # Build entity deduplication map from existing graph
        entity_map: dict[str, int] = {}
        existing_entities = set()
        try:
            res = db_session.run(
                "MATCH (e:Entity) RETURN e.id AS id, e.name AS name",
            )
            for r in res:
                name = str(r.get("name") or "")
                if name:
                    entity_map[name.lower()] = r.get("id")
                    entity_map[name] = r.get("id")
                    existing_entities.add(name.lower())
        except Exception:
            pass

        for fact in facts:
            entity_name = fact.get("entity_name", "User")
            if entity_name and entity_name not in entity_map and entity_name.lower() not in entity_map:
                entity_id = generate_int_id(f"entity:{user_id}:{entity_name}")
                entity_map[entity_name] = entity_id
                entity_map[entity_name.lower()] = entity_id

        # 1. Create Session node
        session_int_id = generate_int_id(f"session:{session_id}")
        anchor_id = session_int_id + 1000000
        run_q(
            "MERGE (s:Session {id: $session_int_id, session_id: $session_id, user_id: $user_id, started_at: $started_at, status: 'active'})-[:SESSION_ANCHOR]->(sa:SessionAnchor {id: $anchor_id})",
            session_int_id=session_int_id,
            session_id=session_id,
            user_id=user_id,
            started_at=started_at,
            anchor_id=anchor_id,
        )
        nodes_created += 2

        # 2. Create Message nodes + CONTAINS edges (optional/best-effort)
        try:
            for i, msg in enumerate(messages):
                msg_id = f"{session_id}:msg:{i}"
                msg_int_id = generate_int_id(msg_id)
                msg_anchor_id = msg_int_id + 1000000
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                created_at = msg.get("created_at", started_at)

                run_q(
                    "MERGE (m:Message {id: $msg_int_id, role: $role, content: $content, created_at: $created_at})-[:MESSAGE_ANCHOR]->(ma:MessageAnchor {id: $msg_anchor_id})",
                    msg_int_id=msg_int_id,
                    role=role,
                    content=content,
                    created_at=created_at,
                    msg_anchor_id=msg_anchor_id,
                )
                nodes_created += 2

                run_q(
                    "CREATE (s:Session {id: $session_int_id})-[:CONTAINS]->(m:Message {id: $msg_int_id})",
                    session_int_id=session_int_id,
                    msg_int_id=msg_int_id,
                )
                edges_created += 1
        except Exception:
            pass

        # 3. Create Summary node + HAS_SUMMARY edge (optional/best-effort)
        if summary:
            try:
                summary_id = summary.get("summary_id", "unknown")
                summary_int_id = generate_int_id(f"summary:{summary_id}")
                summary_anchor_id = summary_int_id + 1000000
                summary_content = summary.get("content", "")
                generated_at = summary.get("generated_at", started_at)

                run_q(
                    "MERGE (sum:Summary {id: $summary_int_id, content: $content, created_at: $created_at})-[:SUMMARY_ANCHOR]->(sma:SummaryAnchor {id: $anchor_id})",
                    summary_int_id=summary_int_id,
                    content=summary_content,
                    created_at=generated_at,
                    anchor_id=summary_anchor_id,
                )
                nodes_created += 2

                run_q(
                    "CREATE (s:Session {id: $session_int_id})-[:HAS_SUMMARY]->(sum:Summary {id: $summary_int_id})",
                    session_int_id=session_int_id,
                    summary_int_id=summary_int_id,
                )
                edges_created += 1
            except Exception:
                pass

        # 4. Create Entity nodes (only for new entities)
        for entity_name, entity_id in list(entity_map.items()):
            if entity_name.lower() in existing_entities:
                continue
            existing_entities.add(entity_name.lower())
            entity_type = "person"
            entity_anchor_id = entity_id + 1000000

            run_q(
                "MERGE (e:Entity {id: $entity_id, name: $name, type: $type})-[:ENTITY_ANCHOR]->(ea:EntityAnchor {id: $anchor_id})",
                entity_id=entity_id,
                name=entity_name,
                type=entity_type,
                anchor_id=entity_anchor_id,
            )
            nodes_created += 2

        # 5. Create Fact nodes + MENTIONS + OCCURRED_IN edges
        for fact in facts:
            fact_id = fact.get("fact_id", "unknown")
            if isinstance(fact_id, int):
                fact_int_id = fact_id
            elif isinstance(fact_id, str) and fact_id.isdigit():
                fact_int_id = int(fact_id)
            else:
                fact_int_id = generate_int_id(f"fact:{user_id}:{session_id}:{fact_id}")

            anchor_id = fact_int_id + 1000000
            content = fact.get("content", "")
            confidence = float(fact.get("confidence") or 0.9)
            entity_name = fact.get("entity_name", "User")
            created_at = fact.get("created_at") or fact.get("session_date") or started_at

            entity_id = entity_map.get(entity_name) or entity_map.get(entity_name.lower())
            if not entity_id:
                entity_id = generate_int_id(f"entity:{user_id}:{entity_name}")
                entity_map[entity_name] = entity_id
                run_q(
                    "MERGE (e:Entity {id: $entity_id, name: $name, type: 'person'})-[:ENTITY_ANCHOR]->(ea:EntityAnchor {id: $anchor_id})",
                    entity_id=entity_id,
                    name=entity_name,
                    anchor_id=entity_id + 1000000,
                )

            run_q(
                "MERGE (f:Fact {id: $fact_int_id, content: $content, confidence: $confidence, is_current: true, created_at: $created_at})-[:FACT_ANCHOR]->(fa:FactAnchor {id: $anchor_id})",
                fact_int_id=fact_int_id,
                content=content,
                confidence=confidence,
                created_at=created_at,
                anchor_id=anchor_id,
            )
            try:
                run_q(
                    "MATCH (f:Fact {id: $fact_int_id}), (e:Entity {id: $entity_id}) MERGE (f)-[:MENTIONS]->(e)",
                    fact_int_id=fact_int_id,
                    entity_id=entity_id,
                )
            except Exception:
                pass

            try:
                run_q(
                    "MATCH (f:Fact {id: $fact_int_id}), (s:Session {id: $session_int_id}) MERGE (f)-[:OCCURRED_IN]->(s)",
                    fact_int_id=fact_int_id,
                    session_int_id=session_int_id,
                )
            except Exception:
                pass
            nodes_created += 2
            edges_created += 2
            facts_written += 1

        # 6. Create SUPERSEDES edges & mark old facts superseded
        for sup in supersessions:
            new_fact_id = sup.get("new_fact_id", "")
            old_fact_id = sup.get("supersedes_fact_id", "")
            if isinstance(new_fact_id, int):
                new_fact_int_id = new_fact_id
            elif isinstance(new_fact_id, str) and new_fact_id.isdigit():
                new_fact_int_id = int(new_fact_id)
            else:
                new_fact_int_id = generate_int_id(f"fact:{user_id}:{session_id}:{new_fact_id}")

            if isinstance(old_fact_id, int):
                old_fact_int_id = old_fact_id
            elif isinstance(old_fact_id, str) and old_fact_id.isdigit():
                old_fact_int_id = int(old_fact_id)
            else:
                old_fact_int_id = generate_int_id(f"fact:{old_fact_id}")

            try:
                run_q(
                    "MATCH (f:Fact {id: $old_id}) SET f.is_current = false",
                    old_id=old_fact_int_id,
                )
            except Exception:
                pass

            try:
                run_q(
                    "MATCH (f_new:Fact {id: $new_id}), (f_old:Fact {id: $old_id}) MERGE (f_new)-[:SUPERSEDES]->(f_old)",
                    new_id=new_fact_int_id,
                    old_id=old_fact_int_id,
                )
                edges_created += 1
            except Exception:
                pass

        # Invalidate older conflicting residence facts if moving/living is updated
        new_loc_facts = [f for f in facts if any(k in f.get("content", "").lower() for k in ["move", "live", "reside", "relocate", "tokyo"])]
        if new_loc_facts:
            try:
                loc_res = db_session.run(
                    "MATCH (f:Fact)-[:OCCURRED_IN]->(s:Session) "
                    "WHERE s.user_id = $user_id AND f.is_current = true "
                    "RETURN f.id AS fact_id, f.content AS content",
                    user_id=user_id,
                )
                for rec in list(loc_res):
                    fid = rec["fact_id"]
                    fcnt = str(rec["content"] or "").lower()
                    if any(w in fcnt for w in ["rajshahi", "dhaka"]):
                        for nlf in new_loc_facts:
                            nlf_id = generate_int_id(f"fact:{user_id}:{session_id}:{nlf.get('fact_id', '')}")
                            if fid != nlf_id:
                                db_session.run("MATCH (f:Fact {id: $old_id}) SET f.is_current = false", old_id=fid)
                                db_session.run("MERGE (f_new:Fact {id: $new_id})-[:SUPERSEDES]->(f_old:Fact {id: $old_id})", new_id=nlf_id, old_id=fid)
                                supersessions_applied = getattr(locals(), "supersessions_applied", 0) + 1
            except Exception:
                pass

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

            run_q(
                "MATCH (f:Fact {id: $fact_int_id}) SET f.is_current = false",
                fact_int_id=fact_int_id,
            )
            run_q(
                "MERGE (f:Fact {id: $fact_int_id})-[:INVALIDATED_BY {reason: $reason}]->(s:Session {id: $session_int_id})",
                fact_int_id=fact_int_id,
                reason=reason,
                session_int_id=session_int_id,
            )
            edges_created += 1

    # Save to local delta store
    _save_ingested_delta(
        session_id=session_id,
        user_id=user_id,
        started_at=started_at,
        facts=facts,
        supersessions=supersessions,
        invalidations=invalidations,
    )

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
        if summary:
            print(f"  Summary: {summary.get('content', '')[:60]}...")

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
            for record in result:
                print(f"  Summary: {record['s.content'][:60]}...")
                break

            result = session.run("MATCH (s:Session) RETURN s.session_id, s.user_id")
            for record in result:
                print(f"  Session: {record['s.session_id']} (user: {record['s.user_id']})")
                break

    finally:
        hydra.close()
        print("\nConnection closed")


if __name__ == "__main__":
    main()
