"""Service layer for HydraDB-backed memory operations."""

from __future__ import annotations

from typing import Any

from config import settings
from db.hydra import HydraDB


class MemoryService:
    """Central backend service for a HydraDB-powered memory graph."""

    def __init__(self, hydra: HydraDB | None = None):
        self.hydra = hydra or HydraDB(uri=settings.hydra_uri, auth_token=settings.hydra_token)

    def ingest_session(self, session: dict[str, Any]) -> dict[str, Any]:
        """Use the ingestion pipeline to store one session in HydraDB."""
        from pipeline.graph import run_pipeline

        session = dict(session)
        result = run_pipeline(session)
        if result.get("error"):
            raise RuntimeError(result["error"])
        return result.get("write_result", {})

    def ingest_batch(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ingest multiple sessions in order."""
        results: list[dict[str, Any]] = []
        for session in sessions:
            try:
                result = self.ingest_session(session)
                results.append({
                    "session_id": session.get("session_id"),
                    "write_result": result,
                    "success": True,
                })
            except Exception as exc:  # pragma: no cover - error path
                results.append({
                    "session_id": session.get("session_id"),
                    "error": str(exc),
                    "success": False,
                })
        return results

    def query_memory(self, question: str, user_id: str = "anonymous") -> dict[str, Any]:
        """Query the memory graph using the retrieval pipeline.

        User context is carried through the request, even though the underlying
        retrieval pipeline is currently a thin question->answer wrapper.
        """
        from pipeline.graph import run_retrieval

        try:
            result = run_retrieval(question)
        except Exception as exc:  # pragma: no cover - graph unavailable path
            return {
                "answer": "I don't have enough trusted memory to answer that yet.",
                "confidence": 0.0,
                "abstained": True,
                "abstention_reason": f"Memory backend unavailable: {exc}",
                "user_id": user_id,
            }

        answer = result.get("answer")
        if answer is None:
            answer = {
                "answer": "Unable to process query",
                "confidence": 0.0,
                "abstained": True,
                "abstention_reason": "Processing error",
                "user_id": user_id,
            }
        else:
            answer["user_id"] = user_id
        return answer

    def get_session_graph(self, session_id: str) -> dict[str, Any]:
        """Return the graph representation for a single session."""
        self.hydra.ensure_connected()
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        session_node_id: int | None = None

        with self.hydra._driver.session() as session:
            result = session.run(
                "MATCH (s:Session {session_id: $session_id}) RETURN s.id, s.session_id, s.user_id, s.started_at",
                session_id=session_id,
            )
            record = result.single()
            if record:
                session_node_id = record["s.id"]
                nodes.append({
                    "id": session_node_id,
                    "label": f"Session: {session_id}",
                    "type": "Session",
                    "data": {
                        "session_id": record["s.session_id"],
                        "user_id": record["s.user_id"],
                        "started_at": record["s.started_at"],
                    },
                })

            result = session.run(
                "MATCH (s:Session {session_id: $session_id})-[:CONTAINS]->(m:Message) "
                "RETURN m.id, m.role, m.content, m.created_at",
                session_id=session_id,
            )
            for record in result:
                node_id = record["m.id"]
                nodes.append({
                    "id": node_id,
                    "label": f"{record['m.role']}: {record['m.content'][:30]}...",
                    "type": "Message",
                    "data": {
                        "role": record["m.role"],
                        "content": record["m.content"],
                        "created_at": record["m.created_at"],
                    },
                })
                if session_node_id is not None:
                    edges.append({"source": session_node_id, "target": node_id, "type": "CONTAINS"})

            result = session.run(
                "MATCH (f:Fact)-[:OCCURRED_IN]->(s:Session {session_id: $session_id}) "
                "RETURN f.id, f.content, f.confidence, f.is_current",
                session_id=session_id,
            )
            for record in result:
                node_id = record["f.id"]
                nodes.append({
                    "id": node_id,
                    "label": record["f.content"][:40],
                    "type": "Fact",
                    "data": {
                        "content": record["f.content"],
                        "confidence": record["f.confidence"],
                        "is_current": record["f.is_current"],
                    },
                })
                if session_node_id is not None:
                    edges.append({"source": node_id, "target": session_node_id, "type": "OCCURRED_IN"})

        return {"nodes": nodes, "edges": edges}

    def get_entity_memory(self, entity_name: str, user_id: str | None = None) -> dict[str, Any]:
        """Return the full temporal memory state for an entity.

        This includes current facts, historical superseded facts, and invalidated
        facts, which are the core semantics for a memory graph that reasons over
        changing user context over time.
        """
        current_facts: list[dict[str, Any]] = []
        historical_facts: list[dict[str, Any]] = []
        invalidated_facts: list[dict[str, Any]] = []

        try:
            self.hydra.ensure_connected()
            with self.hydra._driver.session() as session:
                params = {"entity_name": entity_name}
                current_query = (
                    "MATCH (f:Fact {is_current: true})-[:MENTIONS]->(e:Entity {name: $entity_name}) "
                    "OPTIONAL MATCH (f)-[:OCCURRED_IN]->(s:Session) "
                )
                if user_id is not None:
                    current_query += "WHERE s.user_id = $user_id "
                    params["user_id"] = user_id
                current_query += "RETURN f.id, f.content, f.confidence, f.created_at, s.session_id"

                result = session.run(current_query, **params)
                for record in result:
                    current_facts.append({
                        "fact_id": record["f.id"],
                        "content": record["f.content"],
                        "confidence": record["f.confidence"],
                        "created_at": record["f.created_at"],
                        "session_id": record["s.session_id"],
                    })

                historical_query = (
                    "MATCH (f:Fact {is_current: false})-[:MENTIONS]->(e:Entity {name: $entity_name}) "
                    "MATCH (f)<-[:SUPERSEDES]-(newer:Fact) "
                    "OPTIONAL MATCH (f)-[:OCCURRED_IN]->(s:Session) "
                )
                if user_id is not None:
                    historical_query += "WHERE s.user_id = $user_id "
                historical_query += "RETURN f.id, f.content, f.confidence, f.created_at, s.session_id, newer.id as superseded_by"

                result = session.run(historical_query, **params)
                for record in result:
                    historical_facts.append({
                        "fact_id": record["f.id"],
                        "content": record["f.content"],
                        "confidence": record["f.confidence"],
                        "created_at": record["f.created_at"],
                        "session_id": record["s.session_id"],
                        "superseded_by": record["superseded_by"],
                    })

                invalidated_query = (
                    "MATCH (f:Fact)-[:INVALIDATED_BY]->(s:Session) "
                    "MATCH (f)-[:MENTIONS]->(e:Entity {name: $entity_name}) "
                )
                if user_id is not None:
                    invalidated_query += "WHERE s.user_id = $user_id "
                invalidated_query += "RETURN f.id, f.content, f.confidence, f.created_at, s.session_id, s.started_at AS invalidated_at"

                result = session.run(invalidated_query, **params)
                for record in result:
                    invalidated_facts.append({
                        "fact_id": record["f.id"],
                        "content": record["f.content"],
                        "confidence": record["f.confidence"],
                        "created_at": record["f.created_at"],
                        "session_id": record["s.session_id"],
                        "invalidated_at": record["invalidated_at"],
                    })
        except Exception as exc:  # pragma: no cover - graph unavailable path
            return {
                "entity_name": entity_name,
                "current_facts": current_facts,
                "historical_facts": historical_facts,
                "invalidated_facts": invalidated_facts,
                "total_facts": 0,
                "user_id": user_id,
                "status": "unavailable",
                "error": str(exc),
            }

        return {
            "entity_name": entity_name,
            "current_facts": current_facts,
            "historical_facts": historical_facts,
            "invalidated_facts": invalidated_facts,
            "total_facts": len(current_facts) + len(historical_facts) + len(invalidated_facts),
            "user_id": user_id,
            "status": "ok",
        }

    def get_entity_history(self, entity_name: str, user_id: str | None = None) -> dict[str, Any]:
        """Backward-compatible wrapper for the earlier entity-history API."""
        return self.get_entity_memory(entity_name=entity_name, user_id=user_id)
