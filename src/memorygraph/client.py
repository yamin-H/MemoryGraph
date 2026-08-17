"""MemoryGraph Client: A drop-in temporal graph memory SDK for AI agents."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from typing import Any

from memorygraph.exceptions import ConnectionError, MemoryGraphError, QueryError
from memorygraph.models import MemoryResult, Message


class MemoryGraph:
    """The main entrypoint for the MemoryGraph temporal agent memory layer.

    Usage (API Mode):
        ```python
        from memorygraph import MemoryGraph

        memory = MemoryGraph(api_url="http://localhost:8000")
        memory.add_session(
            user_id="alex_123",
            messages=[
                {"role": "user", "content": "I moved from Rajshahi to Dhaka today."},
                {"role": "assistant", "content": "Congratulations on the move to Dhaka!"}
            ]
        )
        result = memory.query(user_id="alex_123", query="Where does the user live?")
        print(result.answer)  # "Alex lives in Dhaka."
        print(result.confidence)  # 0.98
        ```

    Usage (Direct HydraDB Bolt Mode):
        ```python
        memory = MemoryGraph(
            hydradb_url="bolt://localhost:7687",
            auth_token="local-development-token-32-bytes",
            groq_api_key="gsk_..."
        )
        ```
    """

    def __init__(
        self,
        api_url: str | None = None,
        hydradb_url: str | None = None,
        auth_token: str | None = None,
        groq_api_key: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Initialize the MemoryGraph client.

        Args:
            api_url: Base URL of the running MemoryGraph FastAPI backend (default: http://localhost:8000)
            hydradb_url: Direct HydraDB Neo4j Bolt connection URI (optional)
            auth_token: HydraDB authentication token / password (optional)
            groq_api_key: Groq LLM API Key for direct extraction (optional)
            timeout_seconds: HTTP / query timeout in seconds
        """
        self.api_url = (api_url or os.environ.get("MEMORYGRAPH_API_URL", "http://localhost:8000")).rstrip("/")
        self.hydradb_url = hydradb_url or os.environ.get("HYDRADB_URI")
        self.auth_token = auth_token or os.environ.get("HYDRADB_TOKEN", "local-development-token-32-bytes")
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        self.timeout = timeout_seconds
        self._direct_service = None

    def _http_request(self, method: str, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform a JSON HTTP request to the MemoryGraph API."""
        url = f"{self.api_url}{endpoint}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.getcode()
                raw = resp.read().decode("utf-8")
                if status >= 400:
                    raise QueryError(f"HTTP {status} from MemoryGraph API: {raw}")
                return json.loads(raw)
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Could not connect to MemoryGraph API at {url}. Ensure the backend is running. Details: {e}"
            ) from e
        except Exception as e:
            raise MemoryGraphError(f"API request failed: {e}") from e

    def add_session(
        self,
        user_id: str,
        messages: list[dict[str, Any] | Message],
        session_id: str | None = None,
        started_at: str | None = None,
    ) -> dict[str, Any]:
        """Ingest a multi-turn conversation session into the HydraDB temporal graph.

        Extracts entities and facts, computes temporal supersedence, and writes nodes/edges.

        Args:
            user_id: Unique user identifier
            messages: List of message dictionaries or Message objects
            session_id: Optional session identifier (auto-generated if omitted)
            started_at: Optional ISO 8601 start timestamp

        Returns:
            Dictionary with ingestion results and facts written
        """
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, Message):
                formatted_messages.append(msg.to_dict())
            elif isinstance(msg, dict):
                formatted_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "created_at": msg.get("created_at") or datetime.utcnow().isoformat() + "Z",
                })

        payload = {
            "session_id": session_id or f"session-{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "started_at": started_at or datetime.utcnow().isoformat() + "Z",
            "messages": formatted_messages,
        }

        return self._http_request("POST", "/ingest/session", payload)

    def add_sessions_batch(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Batch ingest multiple conversation sessions in chronological order."""
        return self._http_request("POST", "/ingest/batch", {"sessions": sessions})

    def query(self, user_id: str, query: str) -> MemoryResult:
        """Query the temporal knowledge graph for a user.

        Traverses active graph paths, evaluates supersedence, and handles honest abstention.

        Args:
            user_id: User identifier to scope memory search
            query: Natural language question

        Returns:
            MemoryResult with answer, confidence score, and abstention status
        """
        payload = {"question": query, "user_id": user_id}
        data = self._http_request("POST", "/query", payload)
        return MemoryResult.from_dict(data)

    def compare(self, user_id: str, query: str) -> dict[str, Any]:
        """Run a live side-by-side comparison between Vector RAG and MemoryGraph."""
        payload = {"question": query, "user_id": user_id}
        return self._http_request("POST", "/query/compare", payload)

    def inspect_abstention(self, user_id: str, query: str) -> dict[str, Any]:
        """Inspect the multi-stage reasoning trace for abstention and hallucination prevention."""
        payload = {"question": query, "user_id": user_id}
        return self._http_request("POST", "/query/abstention-inspect", payload)

    def get_entity_history(self, entity_name: str) -> dict[str, Any]:
        """Retrieve full historical, current, and invalidated facts for a specific entity."""
        return self._http_request("GET", f"/graph/entity/{entity_name}")

    def health(self) -> dict[str, Any]:
        """Check API and HydraDB cluster health."""
        return self._http_request("GET", "/health")
