"""Full ingestion and retrieval pipelines using LangGraph.

Wires together all pipeline steps into cohesive workflows.
"""

import os
import time
from pathlib import Path
from typing import Any, TypedDict
from dotenv import load_dotenv

from groq import Groq
from langgraph.graph import StateGraph, END

from db.hydra import HydraDB
from pipeline.ingestion.extractor import extract_facts
from pipeline.ingestion.summarizer import summarize_session
from pipeline.ingestion.supersession import detect_supersession
from pipeline.ingestion.invalidator import detect_invalidations
from pipeline.ingestion.writer import write_to_hydradb
from pipeline.retrieval.parser import parse_question
from pipeline.retrieval.traversal import traverse_for_question
from pipeline.retrieval.ranker import rank_facts_by_time
from pipeline.retrieval.abstention import check_abstention
from pipeline.retrieval.confidence import calculate_confidence


# Load environment
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)


class PipelineState(TypedDict):
    """State carried through the pipeline."""

    # Input
    session: dict[str, Any]

    # Processing results
    facts: list[dict[str, Any]]
    summary: dict[str, str] | None
    supersessions: list[dict[str, str]]
    invalidations: list[dict[str, str]]

    # Output
    write_result: dict[str, Any] | None

    # Error handling
    error: str | None
    failed_step: str | None


def with_retry(func, *args, max_retries: int = 2, **kwargs):
    """Execute a function with retry logic."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                print(f"    Retry {attempt + 1}/{max_retries}...")
                continue
    raise last_error


def load_session_node(state: PipelineState) -> dict[str, Any]:
    """Node: Load and validate session data."""
    print("  [1/8] Loading session...")

    session = state.get("session")
    if not session:
        return {"error": "No session provided", "failed_step": "load_session"}

    session_id = session.get("session_id", "unknown")
    messages = session.get("messages", [])
    print(f"       Session ID: {session_id}, Messages: {len(messages)}")

    return {}


def extract_facts_node(state: PipelineState) -> dict[str, Any]:
    """Node: Extract facts from session using Groq."""
    print("  [2/8] Extracting facts...")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"error": "GROQ_API_KEY not set", "failed_step": "extract_facts"}

    client = Groq(api_key=api_key)
    session = state["session"]

    try:
        facts = with_retry(extract_facts, client, session)
        print(f"       Extracted {len(facts)} facts")
        return {"facts": facts}
    except Exception as e:
        return {"error": str(e), "failed_step": "extract_facts"}


def summarize_session_node(state: PipelineState) -> dict[str, Any]:
    """Node: Generate session summary using Groq."""
    print("  [3/8] Summarizing session...")

    api_key = os.environ.get("GROQ_API_KEY")
    client = Groq(api_key=api_key)
    session = state["session"]

    try:
        summary = with_retry(summarize_session, client, session)
        if summary:
            print(f"       Summary: {summary['content'][:50]}...")
        return {"summary": summary}
    except Exception as e:
        return {"error": str(e), "failed_step": "summarize_session"}


def resolve_entities_node(state: PipelineState) -> dict[str, Any]:
    """Node: Resolve and deduplicate entities."""
    print("  [4/8] Resolving entities...")

    facts = state.get("facts", [])
    # Entity resolution is already handled in writer
    # This node is a placeholder for future enhancement
    print(f"       {len(facts)} facts to process")

    return {}


def detect_supersessions_node(state: PipelineState) -> dict[str, Any]:
    """Node: Detect facts that should be superseded."""
    print("  [5/8] Detecting supersessions...")

    api_key = os.environ.get("GROQ_API_KEY")
    client = Groq(api_key=api_key)
    facts = state.get("facts", [])

    hydra = HydraDB()
    try:
        hydra.connect()
        supersessions = detect_supersession(client, hydra, facts)
        print(f"       Found {len(supersessions)} supersessions")
        return {"supersessions": supersessions}
    except Exception as e:
        return {"error": str(e), "failed_step": "detect_supersessions"}
    finally:
        hydra.close()


def detect_invalidations_node(state: PipelineState) -> dict[str, Any]:
    """Node: Detect stale time-bound facts."""
    print("  [6/8] Detecting invalidations...")

    api_key = os.environ.get("GROQ_API_KEY")
    client = Groq(api_key=api_key)
    session = state["session"]
    session_id = session.get("session_id", "unknown")

    hydra = HydraDB()
    try:
        hydra.connect()
        invalidations = detect_invalidations(client, hydra, session_id)
        print(f"       Found {len(invalidations)} invalidations")
        return {"invalidations": invalidations}
    except Exception as e:
        return {"error": str(e), "failed_step": "detect_invalidations"}
    finally:
        hydra.close()


def write_to_hydradb_node(state: PipelineState) -> dict[str, Any]:
    """Node: Write all data to HydraDB."""
    print("  [7/8] Writing to HydraDB...")

    hydra = HydraDB()
    try:
        hydra.connect()
        result = write_to_hydradb(
            hydra=hydra,
            session=state["session"],
            summary=state.get("summary"),
            facts=state.get("facts", []),
            supersessions=state.get("supersessions", []),
            invalidations=state.get("invalidations", []),
        )
        print(f"       Nodes: {result['nodes_created']}, Edges: {result['edges_created']}")
        return {"write_result": result}
    except Exception as e:
        return {"error": str(e), "failed_step": "write_to_hydradb"}
    finally:
        hydra.close()


def confirm_ingestion_node(state: PipelineState) -> dict[str, Any]:
    """Node: Confirm ingestion completed successfully."""
    print("  [8/8] Confirming ingestion...")

    write_result = state.get("write_result")
    if not write_result:
        return {"error": "No write result", "failed_step": "confirm_ingestion"}

    print(f"       Session: {write_result['session_id']}")
    print(f"       Facts written: {write_result['facts_written']}")

    return {}


def check_error(state: PipelineState) -> str:
    """Route to END if there's an error, otherwise continue."""
    if state.get("error"):
        return "end"
    return "continue"


def build_pipeline() -> StateGraph:
    """Build the ingestion pipeline graph."""

    # Create the graph
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("load_session", load_session_node)
    graph.add_node("extract_facts", extract_facts_node)
    graph.add_node("summarize_session", summarize_session_node)
    graph.add_node("resolve_entities", resolve_entities_node)
    graph.add_node("detect_supersessions", detect_supersessions_node)
    graph.add_node("detect_invalidations", detect_invalidations_node)
    graph.add_node("write_to_hydradb", write_to_hydradb_node)
    graph.add_node("confirm_ingestion", confirm_ingestion_node)

    # Add edges
    graph.set_entry_point("load_session")

    graph.add_conditional_edges(
        "load_session",
        check_error,
        {"end": END, "continue": "extract_facts"},
    )

    graph.add_conditional_edges(
        "extract_facts",
        check_error,
        {"end": END, "continue": "summarize_session"},
    )

    graph.add_conditional_edges(
        "summarize_session",
        check_error,
        {"end": END, "continue": "resolve_entities"},
    )

    graph.add_edge("resolve_entities", "detect_supersessions")

    graph.add_conditional_edges(
        "detect_supersessions",
        check_error,
        {"end": END, "continue": "detect_invalidations"},
    )

    graph.add_conditional_edges(
        "detect_invalidations",
        check_error,
        {"end": END, "continue": "write_to_hydradb"},
    )

    graph.add_conditional_edges(
        "write_to_hydradb",
        check_error,
        {"end": END, "continue": "confirm_ingestion"},
    )

    graph.add_edge("confirm_ingestion", END)

    return graph


def run_pipeline(session: dict[str, Any]) -> dict[str, Any]:
    """Run the full ingestion pipeline.

    Args:
        session: Session dict with session_id, user_id, started_at, messages

    Returns:
        Final state with write_result or error information
    """
    print("=" * 60)
    print("Starting MemoryGraph Ingestion Pipeline")
    print("=" * 60)

    graph = build_pipeline()
    app = graph.compile()

    initial_state: PipelineState = {
        "session": session,
        "facts": [],
        "summary": None,
        "supersessions": [],
        "invalidations": [],
        "write_result": None,
        "error": None,
        "failed_step": None,
    }

    final_state = app.invoke(initial_state)

    print("=" * 60)
    if final_state.get("error"):
        print(f"Pipeline FAILED at step: {final_state.get('failed_step')}")
        print(f"Error: {final_state.get('error')}")
    else:
        print("Pipeline completed successfully!")
        write_result = final_state.get("write_result", {})
        print(f"Session: {write_result.get('session_id')}")
        print(f"Nodes created: {write_result.get('nodes_created')}")
        print(f"Edges created: {write_result.get('edges_created')}")
        print(f"Facts written: {write_result.get('facts_written')}")
        print(f"Supersessions: {write_result.get('supersessions_applied')}")
        print(f"Invalidations: {write_result.get('invalidations_applied')}")
    print("=" * 60)

    return final_state


# =============================================================================
# RETRIEVAL PIPELINE
# =============================================================================


class RetrievalState(TypedDict):
    """State carried through the retrieval pipeline."""

    # Input
    question: str

    # Processing results
    parsed_question: dict[str, Any]
    retrieved_facts: list[dict[str, Any]]
    ranked_facts: list[dict[str, Any]]
    abstention_result: dict[str, Any]
    confidence_result: dict[str, Any]

    # Output
    answer: dict[str, Any] | None

    # Error handling
    error: str | None
    failed_step: str | None


def parse_question_node(state: RetrievalState) -> dict[str, Any]:
    """Node: Parse natural language question."""
    print("  [1/6] Parsing question...")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"error": "GROQ_API_KEY not set", "failed_step": "parse_question"}

    client = Groq(api_key=api_key)
    question = state["question"]

    try:
        parsed = with_retry(parse_question, client, question)
        print(f"       Entity: {parsed.get('entity_name')}, Type: {parsed.get('question_type')}")
        return {"parsed_question": parsed}
    except Exception as e:
        return {"error": str(e), "failed_step": "parse_question"}


def graph_traversal_node(state: RetrievalState) -> dict[str, Any]:
    """Node: Traverse graph to retrieve relevant facts."""
    print("  [2/6] Traversing graph...")

    hydra = HydraDB()
    try:
        hydra.connect()
        facts = traverse_for_question(hydra, state["parsed_question"])
        print(f"       Retrieved {len(facts)} facts")
        return {"retrieved_facts": facts}
    except Exception as e:
        return {"error": str(e), "failed_step": "graph_traversal"}
    finally:
        hydra.close()


def rank_by_time_node(state: RetrievalState) -> dict[str, Any]:
    """Node: Rank facts chronologically and detect conflicts."""
    print("  [3/6] Ranking facts...")

    facts = state.get("retrieved_facts", [])
    ranked = rank_facts_by_time(facts)

    conflicts = sum(1 for f in ranked if f.get("has_conflict"))
    print(f"       Ranked {len(ranked)} facts, {conflicts} conflicts")

    return {"ranked_facts": ranked}


def abstention_check_node(state: RetrievalState) -> dict[str, Any]:
    """Node: Check if we should abstain from answering."""
    print("  [4/6] Checking abstention...")

    result = check_abstention(
        state.get("ranked_facts", []),
        state["parsed_question"],
    )

    if result["should_abstain"]:
        print(f"       ABSTAIN: {result['abstention_reason']}")
    else:
        print(f"       Proceeding with {len(result['facts_to_use'])} facts")

    return {"abstention_result": result}


def score_confidence_node(state: RetrievalState) -> dict[str, Any]:
    """Node: Calculate confidence score for the answer."""
    print("  [5/6] Scoring confidence...")

    result = calculate_confidence(
        state["abstention_result"].get("facts_to_use", []),
        state["abstention_result"],
        state["parsed_question"],
    )

    print(f"       Score: {result['score']}")

    return {"confidence_result": result}


def generate_answer_node(state: RetrievalState) -> dict[str, Any]:
    """Node: Generate final answer using Groq."""
    print("  [6/6] Generating answer...")

    api_key = os.environ.get("GROQ_API_KEY")
    client = Groq(api_key=api_key)

    question = state["question"]
    facts = state["abstention_result"].get("facts_to_use", [])
    abstention = state["abstention_result"]
    confidence = state["confidence_result"]

    start_time = time.time()

    # Build context from facts
    if abstention["should_abstain"]:
        answer_text = f"I don't have that information. {abstention['abstention_reason']}."
        source_sessions = []
        superseded_facts = []
    else:
        # Use Groq to generate answer from facts
        facts_context = "\n".join(f"- {f['content']}" for f in facts)

        system_prompt = """You are a helpful assistant answering questions based on retrieved facts.
Answer concisely and accurately based only on the provided facts.
If the facts don't fully answer the question, say so."""

        user_prompt = f"""Question: {question}

Available facts:
{facts_context}

Provide a concise answer based on these facts."""

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=256,
            )
            answer_text = response.choices[0].message.content or "Unable to generate answer."
        except Exception as e:
            answer_text = f"Error generating answer: {str(e)}"

        source_sessions = list(set(f.get("session_id") for f in facts if f.get("session_id")))
        superseded_facts = [f for f in facts if f.get("superseded_by")]

    query_time_ms = int((time.time() - start_time) * 1000)

    answer_result = {
        "answer": answer_text,
        "confidence": confidence["score"],
        "abstained": abstention["should_abstain"],
        "abstention_reason": abstention.get("abstention_reason"),
        "source_sessions": source_sessions,
        "superseded_facts": [{"fact_id": f["fact_id"], "content": f["content"]} for f in superseded_facts],
        "reasoning": confidence["reasoning"],
        "query_time_ms": query_time_ms,
        "facts_examined": len(state.get("retrieved_facts", [])),
        "groq_tokens_used": 0,  # Would need to track from API response
    }

    print(f"       Answer: {answer_text[:50]}...")

    return {"answer": answer_result}


def check_retrieval_error(state: RetrievalState) -> str:
    """Route to END if there's an error, otherwise continue."""
    if state.get("error"):
        return "end"
    return "continue"


def build_retrieval_pipeline() -> StateGraph:
    """Build the retrieval pipeline graph."""

    graph = StateGraph(RetrievalState)

    # Add nodes
    graph.add_node("parse_question", parse_question_node)
    graph.add_node("graph_traversal", graph_traversal_node)
    graph.add_node("rank_by_time", rank_by_time_node)
    graph.add_node("abstention_check", abstention_check_node)
    graph.add_node("score_confidence", score_confidence_node)
    graph.add_node("generate_answer", generate_answer_node)

    # Add edges
    graph.set_entry_point("parse_question")

    graph.add_conditional_edges(
        "parse_question",
        check_retrieval_error,
        {"end": END, "continue": "graph_traversal"},
    )

    graph.add_conditional_edges(
        "graph_traversal",
        check_retrieval_error,
        {"end": END, "continue": "rank_by_time"},
    )

    graph.add_edge("rank_by_time", "abstention_check")

    graph.add_edge("abstention_check", "score_confidence")

    graph.add_edge("score_confidence", "generate_answer")

    graph.add_edge("generate_answer", END)

    return graph


def run_retrieval(question: str) -> dict[str, Any]:
    """Run the full retrieval pipeline.

    Args:
        question: Natural language question

    Returns:
        Final state with answer or error information
    """
    print("=" * 60)
    print("Starting MemoryGraph Retrieval Pipeline")
    print("=" * 60)

    graph = build_retrieval_pipeline()
    app = graph.compile()

    initial_state: RetrievalState = {
        "question": question,
        "parsed_question": {},
        "retrieved_facts": [],
        "ranked_facts": [],
        "abstention_result": {},
        "confidence_result": {},
        "answer": None,
        "error": None,
        "failed_step": None,
    }

    final_state = app.invoke(initial_state)

    print("=" * 60)
    if final_state.get("error"):
        print(f"Pipeline FAILED at step: {final_state.get('failed_step')}")
        print(f"Error: {final_state.get('error')}")
    else:
        answer = final_state.get("answer", {})
        print(f"Answer: {answer.get('answer')}")
        print(f"Confidence: {answer.get('confidence')}")
        print(f"Abstained: {answer.get('abstained')}")
        print(f"Source sessions: {answer.get('source_sessions')}")
        print(f"Query time: {answer.get('query_time_ms')}ms")
    print("=" * 60)

    return final_state


def main():
    """Test the full pipelines."""
    # Sample session
    sample_session = {
        "session_id": "session-test-001",
        "user_id": "alex-user",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [
            {"role": "user", "content": "Hi, I'm Alex and I live in Dhaka."},
            {"role": "assistant", "content": "Nice to meet you, Alex! Dhaka is a vibrant city."},
            {"role": "user", "content": "I love it here. I work as a software engineer at a tech startup."},
            {"role": "assistant", "content": "That sounds exciting!"},
            {"role": "user", "content": "We're building an AI-powered memory system. I have a cat named Pixel who keeps me company while coding."},
            {"role": "assistant", "content": "Pixel sounds like a great coding companion!"},
        ],
    }

    # Run ingestion
    print("\n" + "=" * 60)
    print("STEP 1: INGESTION")
    print("=" * 60)
    ingestion_result = run_pipeline(sample_session)

    if ingestion_result.get("error"):
        print(f"Ingestion failed: {ingestion_result['error']}")
        return

    # Test retrieval with valid question
    print("\n" + "=" * 60)
    print("STEP 2: RETRIEVAL - Valid Question")
    print("=" * 60)
    retrieval_result = run_retrieval("Where does Alex live?")

    # Test retrieval with question about absent information
    print("\n" + "=" * 60)
    print("STEP 3: RETRIEVAL - Absent Information")
    print("=" * 60)
    retrieval_result2 = run_retrieval("What is Alex's dog's name?")


if __name__ == "__main__":
    main()
