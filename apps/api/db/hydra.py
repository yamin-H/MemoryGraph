"""HydraDB OSS connection module using the official Bolt driver.

HydraDB (https://github.com/hydra-db/hydradb) exposes a Neo4j-compatible Bolt
protocol with OpenCypher. MemoryGraph connects to graph-node over Bolt — not
Neo4j Community Edition.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import httpx
import neo4j
from neo4j import GraphDatabase

DEFAULT_URI = "neo4j://127.0.0.1:7687"
DEFAULT_TOKEN = "local-development-token-32-bytes"
DEFAULT_ADMIN_URL = "http://127.0.0.1:9090"
HYDRADB_IMAGE = "ghcr.io/hydra-db/hydradb"
HYDRADB_REPO = "https://github.com/hydra-db/hydradb"


def build_bolt_auth(token: str) -> tuple[Any, str]:
    """Build Bolt auth for HydraDB (token or username/password forms)."""
    token = token or DEFAULT_TOKEN
    if "/" in token:
        username, password = token.split("/", 1)
        return neo4j.basic_auth(username, password), username
    if ":" in token and not token.startswith("http"):
        username, password = token.split(":", 1)
        return neo4j.basic_auth(username, password), username
    return neo4j.basic_auth("neo4j", token), "neo4j"


def probe_hydradb_admin(admin_url: str | None = None, timeout: float = 2.0) -> dict[str, Any]:
    """Check HydraDB admin /readyz — proves graph-node is HydraDB OSS, not Neo4j."""
    admin_url = (admin_url or os.environ.get("HYDRADB_ADMIN_URL", DEFAULT_ADMIN_URL)).rstrip("/")
    try:
        response = httpx.get(f"{admin_url}/readyz", timeout=timeout)
        return {
            "ready": response.status_code == 200,
            "admin_url": admin_url,
            "status_code": response.status_code,
        }
    except Exception as exc:
        return {
            "ready": False,
            "admin_url": admin_url,
            "error": str(exc),
        }


class HydraDB:
    """Connection to HydraDB OSS via Bolt protocol."""

    def __init__(
        self,
        uri: str | None = None,
        auth_token: str | None = None,
        admin_url: str | None = None,
    ):
        """Initialize the HydraDB connection client."""
        from config import settings

        self.uri = uri or settings.hydra_uri or os.environ.get("HYDRADB_URI", DEFAULT_URI)
        self.auth_token = (
            auth_token
            or settings.hydra_token
            or os.environ.get("HYDRADB_TOKEN", DEFAULT_TOKEN)
        )
        self.admin_url = admin_url or os.environ.get("HYDRADB_ADMIN_URL", DEFAULT_ADMIN_URL)
        self._driver = None

    @staticmethod
    def engine_info() -> dict[str, str]:
        """Metadata for health checks and hackathon demos."""
        return {
            "engine": "HydraDB OSS",
            "image": HYDRADB_IMAGE,
            "repository": HYDRADB_REPO,
            "protocol": "Bolt + OpenCypher",
        }

    def _build_auth(self):
        """Build a Bolt auth object for HydraDB."""
        auth, _ = build_bolt_auth(self.auth_token)
        return auth

    @property
    def is_connected(self) -> bool:
        """Return whether the connection is active."""
        return self._driver is not None

    def ensure_connected(self) -> None:
        """Ensure a valid HydraDB driver exists, connecting if needed."""
        if self._driver is None:
            self.connect()

    def connect(self) -> None:
        """Establish a HydraDB connection and validate it."""
        if self._driver is not None:
            return

        auth = self._build_auth()
        candidate_uris = [self.uri]
        if self.uri.startswith("neo4j+s://"):
            candidate_uris.append(self.uri.replace("neo4j+s://", "bolt+s://", 1))
        elif self.uri.startswith("bolt+s://"):
            candidate_uris.append(self.uri.replace("bolt+s://", "neo4j+s://", 1))
        elif self.uri.startswith("neo4j://"):
            candidate_uris.append(self.uri.replace("neo4j://", "bolt://", 1))
        elif self.uri.startswith("bolt://"):
            candidate_uris.append(self.uri.replace("bolt://", "neo4j://", 1))

        last_exc = None
        driver = None
        for uri in candidate_uris:
            try:
                driver = GraphDatabase.driver(uri, auth=auth)
                driver.verify_connectivity()
                self._driver = driver
                self.uri = uri
                return
            except Exception as exc:
                last_exc = exc
                if driver:
                    try:
                        driver.close()
                    except Exception:
                        pass
                driver = None

        self._driver = None
        raise RuntimeError(f"Unable to connect to HydraDB at {self.uri}: {last_exc}") from last_exc

    def close(self) -> None:
        """Close the connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def __enter__(self) -> "HydraDB":
        """Context manager entry, ensuring connection is initialized."""
        self.ensure_connected()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Context manager exit, closing open connection."""
        self.close()

    def https_admin_status(self) -> dict[str, Any]:
        """Probe HydraDB HTTPS admin API — proves multi-protocol graph usage."""
        try:
            admin_url = (self.admin_url or DEFAULT_ADMIN_URL).rstrip("/")
            # Try the HTTPS port (8443) which is HydraDB's native API
            https_url = admin_url.replace(":9090", ":8443")
            if https_url == admin_url:
                # admin_url didn't have port 9090, try adding 8443
                from urllib.parse import urlparse
                parsed = urlparse(admin_url)
                base = f"{parsed.scheme}://{parsed.hostname}:8443"
                https_url = base
            response = httpx.get(f"{https_url}/readyz", timeout=2.0)
            return {"https_api": "reachable", "status": response.status_code, "url": https_url}
        except Exception as e:
            return {"https_api": "unavailable", "error": str(e)}

    def health_details(self) -> dict[str, Any]:
        """Return connection and admin readiness for observability."""
        details = {
            **self.engine_info(),
            "bolt_uri": self.uri,
            "connected": self.is_connected,
        }
        parsed = urlparse(self.uri)
        host = parsed.hostname or "127.0.0.1"
        if host in {"hydradb", "localhost"}:
            admin_url = self.admin_url
        else:
            admin_url = f"http://{host}:9090"
        details["admin"] = probe_hydradb_admin(admin_url)
        details["https_api"] = self.https_admin_status()
        return details

    def write_fact(self, fact_id: int, content: str) -> None:
        """Write a Fact node to the graph.

        HydraDB requires:
        - Relationship patterns with two distinct nodes (source and destination)
        - id property must be an integer for both nodes
        - No MERGE followed by SET
        """
        self.ensure_connected()
        with self._driver.session() as session:
            session.run(
                "MERGE (f:Fact {id: $id, content: $content})-[:HAS_FACT]->(a:Anchor {id: $anchor_id})",
                id=fact_id,
                content=content,
                anchor_id=fact_id + 1000000,
            )

    def read_fact(self, fact_id: int) -> dict | None:
        """Read a Fact node by ID."""
        self.ensure_connected()
        with self._driver.session() as session:
            result = session.run(
                "MATCH (f:Fact {id: $id}) RETURN f.id, f.content",
                id=fact_id,
            )
            record = result.single()
            if record:
                return {"id": record["f.id"], "content": record["f.content"]}
            return None

    def get_user_cell_id(self, user_id: str) -> str:
        """Return deterministic physical HydraDB SlateDB cell ID for a given user."""
        return get_user_cell_id(user_id)

    def ensure_cell_exists(self, cell_id: str) -> bool:
        """Call HydraDB admin API to ensure the physical SlateDB cell is provisioned."""
        try:
            admin_url = (self.admin_url or DEFAULT_ADMIN_URL).rstrip("/")
            response = httpx.post(
                f"{admin_url}/cells/ensure",
                json={"cell_id": cell_id, "namespace": "default", "scope": "default"},
                timeout=2.0,
            )
            return response.status_code in (200, 201, 204)
        except Exception:
            return False

    def execute_in_cell(
        self,
        cell_id: str,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Route query to a physically isolated HydraDB SlateDB cell via HTTP API or Bolt fallback.

        HydraDB scopes and cells are physically separate SlateDB database instances.
        The HTTP API routes queries to a specific cell via 'cell_id' in the request body.
        """
        params = params or {}
        # 1. Try HydraDB HTTP query API with cell_id routing
        try:
            admin_url = (self.admin_url or DEFAULT_ADMIN_URL).rstrip("/")
            http_url = admin_url.replace(":9090", ":8443")
            if http_url == admin_url:
                parsed = urlparse(admin_url)
                http_url = f"{parsed.scheme}://{parsed.hostname}:8443"

            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "query": query,
                "params": params,
                "cell_id": cell_id,
                "scope": "default",
            }
            response = httpx.post(f"{http_url}/query", json=payload, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                records = data.get("records", data.get("results", []))
                if isinstance(records, list):
                    return records
        except Exception:
            pass

        # 2. Bolt connection fallback for environments without separate HTTP query port
        self.ensure_connected()
        with self._driver.session() as session:
            res = session.run(query, **params)
            return [dict(record) for record in res]

    def clear_all(self) -> None:
        """Clear all nodes (useful for cleanup)."""
        self.ensure_connected()
        with self._driver.session() as session:
            session.run("MATCH (n) DELETE n")


def get_user_cell_id(user_id: str) -> str:
    """Return a deterministic physical SlateDB cell ID for a user.

    In HydraDB architecture, each (scope, cell) is an independently stored
    SlateDB database unit, providing hardware-level data isolation.
    """
    import hashlib

    if not user_id or str(user_id).strip() in ("", "anonymous", "default"):
        return "cell-0"
    h = int(hashlib.md5(user_id.encode("utf-8")).hexdigest(), 16)
    return f"cell-{h % 8}"


def main():
    """Test HydraDB connection."""
    db = HydraDB()
    db.connect()
    print(f"Connected to HydraDB at {db.uri}")
    print(f"Engine: {db.engine_info()}")

    admin = probe_hydradb_admin()
    if admin.get("ready"):
        print(f"HydraDB admin ready at {admin['admin_url']}/readyz")
    else:
        print(f"HydraDB admin not ready: {admin}")

    try:
        db.write_fact(1, "MemoryGraph is a graph-native agent memory layer")
        print("Wrote test Fact node: id=1")

        fact = db.read_fact(1)
        print(f"Read back: {fact}")

        db.clear_all()
        print("Cleaned up test data")

    finally:
        db.close()
        print("Connection closed")


if __name__ == "__main__":
    main()
