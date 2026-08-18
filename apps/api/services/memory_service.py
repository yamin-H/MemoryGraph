"""Service layer for HydraDB-backed memory operations."""

from __future__ import annotations

from typing import Any

from config import settings
from db.hydra import HydraDB


class MemoryService:
    """Central backend service for a HydraDB-powered memory graph."""

    def __init__(self, hydra: HydraDB | None = None):
        """Initialize the memory service with a configured HydraDB client."""
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

        The retrieval pipeline receives the user ID and restricts graph matches
        to that user's sessions.
        """
        from pipeline.graph import run_retrieval

        try:
            result = run_retrieval(question, user_id=user_id)
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

    def get_session_graph(self, session_id: str, user_id: str = "anonymous") -> dict[str, Any]:
        """Return the graph representation for a single session."""
        self.hydra.ensure_connected()
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        session_node_id: int | None = None

        with self.hydra._driver.session() as session:
            result = session.run(
                "MATCH (s:Session {session_id: $session_id, user_id: $user_id}) RETURN s.id, s.session_id, s.user_id, s.started_at",
                session_id=session_id,
                user_id=user_id,
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
                "MATCH (s:Session {session_id: $session_id, user_id: $user_id})-[:CONTAINS]->(m:Message) "
                "RETURN m.id, m.role, m.content, m.created_at",
                session_id=session_id,
                user_id=user_id,
            )
            for record in result:
                node_id = record["m.id"]
                role = record.get("m.role") or "msg"
                content = record.get("m.content") or ""
                nodes.append({
                    "id": node_id,
                    "label": f"{role}: {content[:30]}..." if content else f"{role}: message",
                    "type": "Message",
                    "data": {
                        "role": role,
                        "content": content,
                        "created_at": record.get("m.created_at", ""),
                    },
                })
                if session_node_id is not None:
                    edges.append({"source": session_node_id, "target": node_id, "type": "CONTAINS"})

            result = session.run(
                "MATCH (f:Fact)-[:OCCURRED_IN]->(s:Session {session_id: $session_id, user_id: $user_id}) "
                "RETURN f.id, f.content, f.confidence, f.is_current",
                session_id=session_id,
                user_id=user_id,
            )
            for record in result:
                node_id = record["f.id"]
                content = record.get("f.content") or ""
                nodes.append({
                    "id": node_id,
                    "label": content[:40] if content else f"Fact #{node_id}",
                    "type": "Fact",
                    "data": {
                        "content": content,
                        "confidence": record.get("f.confidence", 0.5),
                        "is_current": record.get("f.is_current", True),
                    },
                })
                if session_node_id is not None:
                    edges.append({"source": node_id, "target": session_node_id, "type": "OCCURRED_IN"})

        return {"nodes": nodes, "edges": edges}

    def get_all_graph(self, user_id: str = "anonymous") -> dict[str, Any]:
        """Return the full graph across all sessions and entities."""
        self.hydra.ensure_connected()
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        seen_nodes: set[int] = set()

        with self.hydra._driver.session() as session:
            # Sessions
            result = session.run(
                "MATCH (s:Session {user_id: $user_id}) RETURN s.id, s.session_id, s.user_id, s.started_at, s.status",
                user_id=user_id,
            )
            for record in result:
                node_id = record["s.id"]
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)
                nodes.append({
                    "id": node_id,
                    "label": f"Session: {record.get('s.session_id', node_id)}",
                    "type": "Session",
                    "data": {
                        "session_id": record.get("s.session_id"),
                        "user_id": record.get("s.user_id"),
                        "started_at": record.get("s.started_at"),
                        "status": record.get("s.status"),
                    },
                })

            # Messages + CONTAINS edges
            result = session.run(
                "MATCH (s:Session {user_id: $user_id})-[:CONTAINS]->(m:Message) "
                "RETURN s.id, m.id, m.role, m.content, m.created_at",
                user_id=user_id,
            )
            for record in result:
                msg_id = record["m.id"]
                if msg_id not in seen_nodes:
                    seen_nodes.add(msg_id)
                    role = record.get("m.role") or "msg"
                    content = record.get("m.content") or ""
                    nodes.append({
                        "id": msg_id,
                        "label": f"{role}: {content[:30]}..." if content else f"{role}: message",
                        "type": "Message",
                        "data": {
                            "role": role,
                            "content": content,
                            "created_at": record.get("m.created_at", ""),
                        },
                    })
                edges.append({
                    "source": record["s.id"],
                    "target": msg_id,
                    "type": "CONTAINS",
                })

            # Facts + OCCURRED_IN edges + Supersedence links
            result = session.run(
                "MATCH (f:Fact)-[:OCCURRED_IN]->(s:Session {user_id: $user_id}) "
                "OPTIONAL MATCH (newer:Fact)-[:SUPERSEDES]->(f) "
                "RETURN f.id AS id, f.content AS content, f.confidence AS confidence, "
                "f.is_current AS is_current, f.created_at AS created_at, s.id AS session_node_id, "
                "s.session_id AS session_id, newer.id AS superseded_by_id, newer.content AS superseded_by",
                user_id=user_id,
            )
            for record in result:
                fact_id = record["id"] or f"fact-{len(seen_nodes)}"
                if fact_id not in seen_nodes:
                    seen_nodes.add(fact_id)
                    content = record.get("content") or ""
                    is_current = record.get("is_current")
                    if is_current is None:
                        is_current = record.get("superseded_by") is None
                    nodes.append({
                        "id": fact_id,
                        "label": content[:40] if content else f"Fact #{fact_id}",
                        "type": "Fact",
                        "data": {
                            "content": content,
                            "confidence": record.get("confidence", 0.85),
                            "is_current": is_current,
                            "created_at": record.get("created_at", ""),
                            "session_id": record.get("session_id", ""),
                            "superseded_by": record.get("superseded_by"),
                            "superseded_by_id": record.get("superseded_by_id"),
                        },
                    })
                if record.get("session_node_id"):
                    edges.append({
                        "source": fact_id,
                        "target": record["session_node_id"],
                        "type": "OCCURRED_IN",
                    })

            # Entities
            result = session.run(
                "MATCH (e:Entity {user_id: $user_id}) RETURN e.id AS id, e.name AS name, e.type AS type",
                user_id=user_id,
            )
            for record in result:
                entity_id = record["id"] or f"entity-{len(seen_nodes)}"
                if entity_id not in seen_nodes:
                    seen_nodes.add(entity_id)
                    name = record.get("name") or f"Entity #{entity_id}"
                    nodes.append({
                        "id": entity_id,
                        "label": name,
                        "type": "Entity",
                        "data": {
                            "name": name,
                            "type": record.get("type", "entity"),
                        },
                    })

            # Summaries + HAS_SUMMARY edges
            result = session.run(
                "MATCH (s:Session {user_id: $user_id})-[:HAS_SUMMARY]->(sum:Summary) "
                "RETURN s.id, sum.id, sum.content, sum.created_at",
                user_id=user_id,
            )
            for record in result:
                sum_id = record["sum.id"]
                if sum_id not in seen_nodes:
                    seen_nodes.add(sum_id)
                    content = record.get("sum.content") or ""
                    nodes.append({
                        "id": sum_id,
                        "label": content[:40] if content else f"Summary #{sum_id}",
                        "type": "Summary",
                        "data": {
                            "content": content,
                            "created_at": record.get("sum.created_at", ""),
                        },
                    })
                edges.append({
                    "source": record["s.id"],
                    "target": sum_id,
                    "type": "HAS_SUMMARY",
                })

            # MENTIONS edges (Fact -> Entity)
            result = session.run(
                "MATCH (f:Fact)-[:MENTIONS]->(e:Entity {user_id: $user_id}) RETURN f.id, e.id",
                user_id=user_id,
            )
            for record in result:
                edges.append({
                    "source": record["f.id"],
                    "target": record["e.id"],
                    "type": "MENTIONS",
                })

            # SUPERSEDES edges (Fact -> Fact)
            result = session.run(
                "MATCH (f1:Fact)-[:SUPERSEDES]->(f2:Fact) RETURN f1.id, f2.id",
                user_id=user_id,
            )
            for record in result:
                edges.append({
                    "source": record["f1.id"],
                    "target": record["f2.id"],
                    "type": "SUPERSEDES",
                })

            # INVALIDATED_BY edges (Fact -> Session)
            result = session.run(
                "MATCH (f:Fact)-[:INVALIDATED_BY]->(s:Session {user_id: $user_id}) "
                "RETURN f.id, s.id",
                user_id=user_id,
            )
            for record in result:
                edges.append({
                    "source": record["f.id"],
                    "target": record["s.id"],
                    "type": "INVALIDATED_BY",
                })

        user_cell_id = getattr(self.hydra, "get_user_cell_id", lambda u: "cell-0")(user_id) if hasattr(self.hydra, "get_user_cell_id") else "cell-0"
        return {"nodes": nodes, "edges": edges, "user_id": user_id, "cell_id": user_cell_id}


    def get_entity_memory(self, entity_name: str, user_id: str = "anonymous") -> dict[str, Any]:
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
                params = {"entity_name": entity_name, "user_id": user_id}
                current_query = (
                    "MATCH (f:Fact)-[:MENTIONS]->(e:Entity {name: $entity_name, user_id: $user_id}) "
                    "MATCH (f)-[:OCCURRED_IN]->(s:Session {user_id: $user_id}) "
                    "WHERE NOT (f)<-[:SUPERSEDES*1..]-(newer_f:Fact) "
                    "AND NOT (f)-[:INVALIDATED_BY]->(inv:Session) "
                )
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
                    "MATCH (newer:Fact)-[:SUPERSEDES*1..]->(f:Fact)-[:MENTIONS]->"
                    "(e:Entity {name: $entity_name, user_id: $user_id}) "
                    "MATCH (f)-[:OCCURRED_IN]->(s:Session {user_id: $user_id}) "
                )
                historical_query += "RETURN DISTINCT f.id, f.content, f.confidence, f.created_at, s.session_id, newer.id as superseded_by"

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
                    "MATCH (f:Fact)-[:INVALIDATED_BY]->(s:Session {user_id: $user_id}) "
                    "MATCH (f)-[:MENTIONS]->(e:Entity {name: $entity_name, user_id: $user_id}) "
                )
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

    def get_entity_history(self, entity_name: str, user_id: str = "anonymous") -> dict[str, Any]:
        """Backward-compatible wrapper for the earlier entity-history API."""
        return self.get_entity_memory(entity_name=entity_name, user_id=user_id)

    def get_recent_sessions(self, user_id: str = "anonymous", limit: int = 50) -> list[dict[str, Any]]:
        """Return list of recent sessions stored in HydraDB."""
        sessions: list[dict[str, Any]] = []
        try:
            self.hydra.ensure_connected()
            with self.hydra._driver.session() as session:
                query = (
                    "MATCH (s:Session {user_id: $user_id}) "
                    "OPTIONAL MATCH (s)-[:HAS_SUMMARY]->(sum:Summary) "
                    "OPTIONAL MATCH (f:Fact)-[:OCCURRED_IN]->(s) "
                    "RETURN s.session_id AS session_id, s.user_id AS user_id, "
                    "s.started_at AS started_at, sum.content AS summary, "
                    "count(DISTINCT f) AS fact_count "
                    "ORDER BY s.started_at DESC LIMIT $limit"
                )
                result = session.run(query, user_id=user_id, limit=limit)
                for record in result:
                    sessions.append({
                        "id": record["session_id"],
                        "user_id": record["user_id"],
                        "date": record["started_at"] or "2024-01-01T00:00:00Z",
                        "summary": record["summary"],
                        "factCount": record["fact_count"] or 0,
                    })
        except Exception:
            pass
        return sessions

    def compare_query(self, question: str, user_id: str = "anonymous") -> dict[str, Any]:
        """Execute real side-by-side comparison between Vector RAG and MemoryGraph.

        Runs both pipelines live against ingested knowledge:
        1. MemoryGraph: OpenCypher traversal, temporal filtering, SUPERSEDES resolution, honest abstention.
        2. Vector RAG: Unstructured semantic similarity retrieval (Cosine/TF-IDF) over all historical facts without graph temporal knowledge, followed by LLM synthesis.
        """
        import math
        import re
        import time
        from groq import Groq

        # --- 1. RUN MEMORYGRAPH PIPELINE ---
        mg_start = time.time()
        mg_result = self.query_memory(question, user_id=user_id)
        mg_latency = int((time.time() - mg_start) * 1000)

        # Retrieve active & superseded facts from HydraDB for diagnostic
        active_facts: list[dict[str, Any]] = []
        superseded_facts: list[dict[str, Any]] = []
        all_raw_facts: list[dict[str, Any]] = []

        try:
            self.hydra.ensure_connected()
            with self.hydra._driver.session() as session:
                query_facts = (
                    "MATCH (f:Fact) "
                    "OPTIONAL MATCH (f)-[:OCCURRED_IN]->(s:Session) "
                    "OPTIONAL MATCH (newer:Fact)-[:SUPERSEDES]->(f) "
                    "RETURN f.content AS content, f.is_current AS is_current, "
                    "f.confidence AS confidence, f.created_at AS created_at, "
                    "s.session_id AS session_id, newer.content AS superseded_by"
                )
                res = session.run(query_facts)
                for record in res:
                    item = {
                        "content": record["content"] or "",
                        "is_current": record["is_current"] if record["is_current"] is not None else True,
                        "confidence": record["confidence"] or 0.8,
                        "created_at": record["created_at"] or "",
                        "session_id": record["session_id"] or "session_1",
                        "superseded_by": record["superseded_by"],
                    }
                    all_raw_facts.append(item)
                    if item["is_current"]:
                        active_facts.append(item)
                    else:
                        superseded_facts.append(item)
        except Exception:
            pass

        # Return an honest comparison result when the graph contains no facts.
        if not all_raw_facts:
            return {
                "question": question,
                "user_id": user_id,
                "winner": "none",
                "diff_explanation": "No facts are stored in the memory graph. Ingest a session before running a comparison.",
                "memorygraph": {
                    "answer": mg_result.get("answer", "I don't have that information."),
                    "confidence": mg_result.get("confidence", 0.0),
                    "abstained": True,
                    "latency_ms": mg_latency,
                    "facts_examined": 0,
                    "source_sessions": [],
                    "active_facts": [],
                    "superseded_facts_filtered": [],
                    "opencypher_query": None,
                },
                "vector_rag": {
                    "answer": "No facts are available for vector retrieval.",
                    "confidence": 0.0,
                    "abstained": True,
                    "latency_ms": 0,
                    "retrieved_chunks": [],
                    "failure_mode": "no_facts_in_graph",
                    "retrieval_method": "Unavailable until sessions are ingested",
                },
            }

        # --- 2. RUN REAL VECTOR RAG PIPELINE (TfidfVectorizer + Cosine Similarity) ---
        vec_start = time.time()

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        fact_corpus = [fact["content"] for fact in all_raw_facts]
        scored_chunks = []

        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            corpus_vectors = vectorizer.fit_transform(fact_corpus)
            query_vector = vectorizer.transform([question])
            cosine_scores = cosine_similarity(query_vector, corpus_vectors)[0]

            for idx, fact in enumerate(all_raw_facts):
                sim = float(cosine_scores[idx])
                scored_chunks.append({
                    "content": fact["content"],
                    "similarity_score": round(sim, 4),
                    "session_id": fact.get("session_id", "session-unknown"),
                    "is_outdated": not fact.get("is_current", True),
                    "created_at": fact.get("created_at", ""),
                    "superseded_by": fact.get("superseded_by"),
                })
        except Exception:
            # Fallback if corpus vocabulary is completely empty
            for fact in all_raw_facts:
                scored_chunks.append({
                    "content": fact["content"],
                    "similarity_score": 0.0,
                    "session_id": fact.get("session_id", "session-unknown"),
                    "is_outdated": not fact.get("is_current", True),
                    "created_at": fact.get("created_at", ""),
                    "superseded_by": fact.get("superseded_by"),
                })

        # Rank by cosine vector similarity (top 3)
        scored_chunks.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_vector_chunks = scored_chunks[:3]

        # Check if vector retrieved contradictory / outdated facts
        has_outdated_in_top = any(c["is_outdated"] for c in top_vector_chunks if c["similarity_score"] > 0.15)
        max_sim = top_vector_chunks[0]["similarity_score"] if top_vector_chunks else 0.0

        # Synthesize Vector RAG Answer with Groq (or algorithmic fallback)
        vector_answer = ""
        groq_api_key = settings.groq_api_key
        if max_sim < 0.10:
            vector_answer = "I don't have enough information in the vector database to answer that question."
            vector_abstained = True
            vector_failure_mode = "none"
        else:
            vector_abstained = False
            context_text = "\n".join([f"- [Sim: {c['similarity_score'] * 100:.1f}%] {c['content']}" for c in top_vector_chunks])

            if groq_api_key:
                try:
                    groq_client = Groq(api_key=groq_api_key)
                    prompt = (
                        f"You are an AI assistant answering based ONLY on the following retrieved semantic chunks:\n"
                        f"{context_text}\n\n"
                        f"Question: {question}\n"
                        f"Answer concisely. If the chunks contain contradictory or multiple statements, mention what the chunks state:"
                    )
                    chat_resp = groq_client.chat.completions.create(
                        model=settings.groq_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                        max_tokens=150,
                    )
                    vector_answer = chat_resp.choices[0].message.content.strip()
                except Exception:
                    pass

            if not vector_answer:
                if has_outdated_in_top:
                    vector_answer = f"Based on retrieved vector contexts, conflicting statements were found: {context_text}"
                else:
                    vector_answer = top_vector_chunks[0]["content"]

            if has_outdated_in_top:
                vector_failure_mode = "retrieved_conflicting_temporal_facts"
            else:
                vector_failure_mode = "none"

        vec_latency = int((time.time() - vec_start) * 1000)

        # --- 3. SYNTHESIZE DYNAMIC COMPARISON VERDICT ---
        mg_abstained = mg_result.get("abstained", False)
        mg_answer = mg_result.get("answer", "")
        mg_conf = mg_result.get("confidence", 0.0)

        # Dynamic winner calculation based on real evaluation criteria:
        # 1. Temporal contradiction: Vector retrieved superseded/stale facts while MemoryGraph filtered them
        if has_outdated_in_top and not mg_abstained and mg_conf > 0.4:
            winner = "memorygraph"
            diff_explanation = (
                "Vector RAG retrieved superseded/outdated historical facts because cosine similarity treats all documents identically regardless of temporal invalidation. "
                "MemoryGraph traversed the HydraDB graph, applied [:SUPERSEDES] edge resolution, and returned only current facts."
            )
        # 2. Both abstained due to missing information
        elif vector_abstained and mg_abstained:
            winner = "tie"
            diff_explanation = (
                "Both systems correctly recognized insufficient evidence in the knowledge base and abstained from hallucinating."
            )
        # 3. Vector found high similarity while MemoryGraph had no matching entity/fact
        elif not vector_abstained and max_sim >= 0.5 and mg_abstained:
            winner = "vector_rag"
            diff_explanation = (
                f"Vector RAG matched relevant text chunks with {max_sim:.2f} cosine similarity and synthesized a valid response, whereas MemoryGraph abstained due to graph traversal constraints."
            )
        # 4. MemoryGraph found clear graph evidence while Vector similarity was too weak
        elif not mg_abstained and mg_conf >= 0.6 and vector_abstained:
            winner = "memorygraph"
            diff_explanation = (
                f"MemoryGraph resolved connected entity relations with high confidence ({int(mg_conf * 100)}%), whereas Vector RAG semantic similarity fell below the retrieval threshold."
            )
        # 5. Both answered: compare latency, confidence, and accuracy
        elif not vector_abstained and not mg_abstained:
            if abs(mg_conf - max_sim) <= 0.15:
                winner = "tie"
                diff_explanation = (
                    "Both systems successfully retrieved relevant knowledge and generated answers with comparable confidence."
                )
            elif mg_conf > max_sim:
                winner = "memorygraph"
                diff_explanation = (
                    f"MemoryGraph provided structured graph provenance with higher calibrated confidence ({int(mg_conf * 100)}% vs {int(max_sim * 100)}% vector similarity)."
                )
            else:
                winner = "vector_rag"
                diff_explanation = (
                    f"Vector RAG retrieved high-scoring semantic context ({int(max_sim * 100)}% similarity) exceeding graph confidence ({int(mg_conf * 100)}%)."
                )
        else:
            winner = "tie"
            diff_explanation = "Both systems produced comparable outcomes for this query."

        opencypher_snippet = (
            "MATCH (e:Entity {name: $entity})\n"
            "MATCH (f:Fact {is_current: true})-[:MENTIONS]->(e)\n"
            "OPTIONAL MATCH (newer:Fact)-[:SUPERSEDES]->(f)\n"
            "WHERE newer IS NULL\n"
            "RETURN f.content, f.confidence, f.created_at"
        )

        return {
            "question": question,
            "user_id": user_id,
            "winner": winner,
            "diff_explanation": diff_explanation,
            "memorygraph": {
                "answer": mg_answer,
                "confidence": mg_conf,
                "abstained": mg_abstained,
                "latency_ms": mg_latency,
                "facts_examined": mg_result.get("facts_examined", len(active_facts)),
                "source_sessions": mg_result.get("source_sessions", []),
                "active_facts": [f["content"] for f in active_facts[:3]],
                "superseded_facts_filtered": [
                    {"content": f["content"], "superseded_by": f.get("superseded_by")}
                    for f in superseded_facts
                ],
                "opencypher_query": opencypher_snippet,
            },
            "vector_rag": {
                "answer": vector_answer,
                "confidence": max_sim if not vector_abstained else 0.15,
                "abstained": vector_abstained,
                "latency_ms": vec_latency,
                "retrieved_chunks": top_vector_chunks,
                "failure_mode": vector_failure_mode,
                "retrieval_method": "Cosine Semantic Similarity (Top-K = 3)",
            },
        }

    def inspect_abstention(self, question: str, user_id: str = "anonymous") -> dict[str, Any]:
        """Provide genuine multi-stage reasoning trace for abstention & hallucination prevention.

        Uses the real retrieval pipeline:
        1. Dynamic Question & Entity Parsing
        2. HydraDB Graph Entity Index & Subgraph Verification
        3. Real OpenCypher Traversal & Temporal Ranking
        4. Graph Evidence Aggregation & Calibrated Confidence Scoring (threshold = 0.35)
        5. First-class Honest Abstention Enforcement vs Ungrounded Synthesis Contrast
        """
        import os
        import time
        from groq import Groq
        from config import settings
        from pipeline.retrieval.parser import parse_question, _fallback_parse_question
        from pipeline.retrieval.traversal import traverse_for_question, get_confidence_evidence
        from pipeline.retrieval.ranker import rank_facts_by_time
        from pipeline.retrieval.abstention import check_abstention
        from pipeline.retrieval.confidence import calculate_confidence, enforce_confidence_threshold, CONFIDENCE_THRESHOLD

        start_time = time.time()
        self.hydra.ensure_connected()

        # Step 1: Parse question dynamically using LLM or rule-based fallback
        groq_api_key = settings.groq_api_key or os.environ.get("GROQ_API_KEY")
        parsed_question = None
        if groq_api_key and not groq_api_key.startswith("gsk_mock_") and groq_api_key.strip():
            try:
                groq_client = Groq(api_key=groq_api_key)
                parsed_question = parse_question(groq_client, question)
            except Exception:
                parsed_question = _fallback_parse_question(question)
        else:
            parsed_question = _fallback_parse_question(question)

        extracted_entity_name = parsed_question.get("entity_name")
        keywords = parsed_question.get("keywords", [])
        question_type = parsed_question.get("question_type", "current_fact")

        # Step 2: Check entity presence in user-scoped HydraDB knowledge graph
        extracted_entities = []
        in_graph = False
        entity_type = "Entity"

        if extracted_entity_name:
            with self.hydra._driver.session() as db_session:
                res = db_session.run(
                    "MATCH (e:Entity {user_id: $user_id}) "
                    "WHERE toLower(e.name) = toLower($name) "
                    "RETURN e.name AS name, e.type AS type LIMIT 1",
                    user_id=user_id,
                    name=extracted_entity_name,
                )
                record = res.single()
                if record:
                    in_graph = True
                    entity_type = record.get("type") or "Entity"
                    extracted_entity_name = record.get("name") or extracted_entity_name

            extracted_entities.append({
                "entity": extracted_entity_name,
                "type": entity_type,
                "in_graph": in_graph,
                "status": "Verified in HydraDB Entity Index" if in_graph else "MISSING from Knowledge Graph",
            })
        else:
            # Check if keywords match any known entities
            with self.hydra._driver.session() as db_session:
                res = db_session.run(
                    "MATCH (e:Entity {user_id: $user_id}) RETURN e.name AS name, e.type AS type LIMIT 5",
                    user_id=user_id,
                )
                for record in res:
                    name = record.get("name", "")
                    if name.lower() in question.lower():
                        in_graph = True
                        extracted_entities.append({
                            "entity": name,
                            "type": record.get("type") or "Entity",
                            "in_graph": True,
                            "status": "Verified in HydraDB Entity Index",
                        })

            if not extracted_entities:
                extracted_entities.append({
                    "entity": "Unknown Subject",
                    "type": "Unindexed Entity",
                    "in_graph": False,
                    "status": "MISSING from Knowledge Graph",
                })

        # Step 3: Real OpenCypher Traversal & Ranking
        retrieved_facts = traverse_for_question(self.hydra, parsed_question, user_id=user_id)
        ranked_facts = rank_facts_by_time(retrieved_facts)
        raw_abstention = check_abstention(ranked_facts, parsed_question)

        facts_to_use = raw_abstention.get("facts_to_use", [])

        # Step 4: Real Graph Evidence Aggregation & Confidence Calculation
        graph_evidence = {}
        if facts_to_use:
            graph_evidence = get_confidence_evidence(self.hydra, facts_to_use, user_id)

        confidence_result = calculate_confidence(
            facts_to_use,
            raw_abstention,
            parsed_question,
            graph_evidence=graph_evidence,
        )
        final_abstention = enforce_confidence_threshold(raw_abstention, confidence_result)

        final_score = confidence_result.get("score", 0.0)
        abstention_triggered = final_abstention.get("should_abstain", False)
        abstention_reason = final_abstention.get("abstention_reason") or "Verified against active knowledge graph."

        # Compute accurate confidence breakdown metrics from actual graph evidence
        entity_coverage = 1.0 if in_graph else (0.3 if facts_to_use else 0.0)
        evidence_rows = [graph_evidence.get(str(f.get("fact_id")), {}) for f in facts_to_use]
        evidence_backed = [r for r in evidence_rows if r]
        avg_support = (sum(r.get("supporting_facts", 0) for r in evidence_backed) / len(evidence_backed)) if evidence_backed else 0.0
        relation_density = min(round(avg_support / 3.0, 2), 1.0) if facts_to_use else 0.0
        temporal_recency = 0.90 if any(f.get("is_current") for f in facts_to_use) else 0.10

        confidence_breakdown = {
            "entity_coverage": round(entity_coverage, 2),
            "relation_density": round(relation_density, 2),
            "temporal_recency": round(temporal_recency, 2),
            "final_confidence": final_score,
            "threshold": CONFIDENCE_THRESHOLD,
        }

        # Step 5: Answer synthesis & Hallucination simulation contrast
        related_facts = [f.get("content", "") for f in (facts_to_use or retrieved_facts)[:3]]

        if abstention_triggered:
            verified_answer = f"I do not have recorded memory to answer this question accurately. ({abstention_reason})"
            # Real dynamic hallucination simulation for ungrounded LLMs
            if groq_api_key and not groq_api_key.startswith("gsk_mock_") and groq_api_key.strip():
                try:
                    groq_client = Groq(api_key=groq_api_key)
                    sim_prompt = (
                        f"Provide a brief, confident, plausible but fabricated 1-sentence answer to: '{question}'. "
                        f"Act as a naive AI that hallucinates instead of saying 'I don't know'."
                    )
                    sim_resp = groq_client.chat.completions.create(
                        model=settings.groq_model,
                        messages=[{"role": "user", "content": sim_prompt}],
                        temperature=0.7,
                        max_tokens=60,
                    )
                    hallucination_simulation = sim_resp.choices[0].message.content.strip()
                except Exception:
                    hallucination_simulation = f"A naive model would hallucinate plausible assertions regarding '{question}' without graph grounding."
            else:
                hallucination_simulation = f"A naive model without graph grounding would fabricate plausible assumptions for '{question}'."
        else:
            if facts_to_use:
                top_fact = facts_to_use[0].get("content", "")
                verified_answer = f"{top_fact}."
            else:
                verified_answer = "Verified factual record retrieved from active memory graph."
            hallucination_simulation = verified_answer

        # Construct inspected OpenCypher query
        target_name = extracted_entity_name or "Entity"
        opencypher_inspection = (
            f"// HydraDB OpenCypher: Scoped Temporal Traversal & Lineage\n"
            f"MATCH (f:Fact)-[:OCCURRED_IN]->(s:Session {{user_id: '{user_id}'}})\n"
            f"MATCH (f)-[:MENTIONS]->(e:Entity {{user_id: '{user_id}'}})\n"
            f"WHERE toLower(e.name) = toLower('{target_name}')\n"
            f"  AND NOT (f)<-[:SUPERSEDES*1..]-(newer_f:Fact)\n"
            f"  AND NOT (f)-[:INVALIDATED_BY]->(inv:Session)\n"
            f"RETURN f.id, f.content, f.confidence, f.created_at\n"
            f"ORDER BY f.created_at DESC"
        )

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "question": question,
            "user_id": user_id,
            "latency_ms": latency_ms,
            "extracted_entities": extracted_entities,
            "subgraph_nodes_found": len(retrieved_facts),
            "confidence_breakdown": confidence_breakdown,
            "graph_evidence": graph_evidence,
            "abstention_triggered": abstention_triggered,
            "abstention_reason": abstention_reason,
            "verified_answer": verified_answer,
            "hallucination_simulation": hallucination_simulation,
            "related_facts_in_graph": related_facts,
            "opencypher_inspection": opencypher_inspection,
        }
