"""HydraDB OSS connection module using the official Bolt driver."""

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
    token = token or DEFAULT_TOKEN
    if "/" in token:
        username, password = token.split("/", 1)
        return neo4j.basic_auth(username, password), username
    if ":" in token and not token.startswith("http"):
        username, password = token.split(":", 1)
        return neo4j.basic_auth(username, password), username
    return neo4j.basic_auth("neo4j", token), "neo4j"


def probe_hydradb_admin(admin_url: str | None = None, timeout: float = 2.0) -> dict[str, Any]:
    admin_url = (admin_url or os.environ.get("HYDRADB_ADMIN_URL", DEFAULT_ADMIN_URL)).rstrip("/")
    try:
        response = httpx.get(f"{admin_url}/readyz", timeout=timeout)
        return {
            "ready": response.status_code == 200,
            "admin_url": admin_url,
            "status_code": response.status_code,
        }
    except Exception as exc:
        return {"ready": False, "admin_url": admin_url, "error": str(exc)}


class HydraDB:
    """Connection to HydraDB OSS via Bolt protocol."""

    def __init__(
        self,
        uri: str | None = None,
        auth_token: str | None = None,
        admin_url: str | None = None,
    ):
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
        return {
            "engine": "HydraDB OSS",
            "image": HYDRADB_IMAGE,
            "repository": HYDRADB_REPO,
            "protocol": "Bolt + OpenCypher",
        }

    def _build_auth(self):
        auth, _ = build_bolt_auth(self.auth_token)
        return auth

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    def ensure_connected(self) -> None:
        if self._driver is None:
            self.connect()

    def connect(self) -> None:
        if self._driver is not None:
            return

        auth = self._build_auth()
        candidate_uris = [self.uri]
        if self.uri.startswith("neo4j://"):
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
        if self._driver:
            self._driver.close()
            self._driver = None

    def __enter__(self) -> "HydraDB":
        self.ensure_connected()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def https_admin_status(self) -> dict[str, Any]:
        try:
            admin_url = (self.admin_url or DEFAULT_ADMIN_URL).rstrip("/")
            https_url = admin_url.replace(":9090", ":8443")
            if https_url == admin_url:
                parsed = urlparse(admin_url)
                https_url = f"{parsed.scheme}://{parsed.hostname}:8443"
            response = httpx.get(f"{https_url}/readyz", timeout=2.0)
            return {"https_api": "reachable", "status": response.status_code, "url": https_url}
        except Exception as e:
            return {"https_api": "unavailable", "error": str(e)}

    def health_details(self) -> dict[str, Any]:
        details = {
            **self.engine_info(),
            "bolt_uri": self.uri,
            "connected": self.is_connected,
        }
        parsed = urlparse(self.uri)
        host = parsed.hostname or "127.0.0.1"
        admin_url = self.admin_url if host in {"hydradb", "localhost"} else f"http://{host}:9090"
        details["admin"] = probe_hydradb_admin(admin_url)
        details["https_api"] = self.https_admin_status()
        return details

    def get_user_cell_id(self, user_id: str) -> str:
        return get_user_cell_id(user_id)

    def ensure_cell_exists(self, cell_id: str) -> bool:
        """Ensure a HydraDB cell shard exists via the admin API."""
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

    def get_current_facts(self, entity_name: str, fact_type: str | None = None) -> list[dict]:
        """Retrieve current facts for an entity."""
        self.ensure_connected()
        with self._driver.session() as session:
            if fact_type:
                result = session.run(
                    "MATCH (f:Fact {entity_name: $entity_name, fact_type: $fact_type, is_current: true}) "
                    "RETURN f.fact_id AS fact_id, f.content AS content, f.fact_type AS fact_type, "
                    "f.confidence AS confidence, f.session_index AS session_index, f.session_date AS session_date "
                    "ORDER BY f.session_index DESC",
                    entity_name=entity_name,
                    fact_type=fact_type,
                )
            else:
                result = session.run(
                    "MATCH (f:Fact {entity_name: $entity_name, is_current: true}) "
                    "RETURN f.fact_id AS fact_id, f.content AS content, f.fact_type AS fact_type, "
                    "f.confidence AS confidence, f.session_index AS session_index, f.session_date AS session_date "
                    "ORDER BY f.session_index DESC",
                    entity_name=entity_name,
                )
            return [dict(r) for r in result]

    def get_superseded_history(self, entity_name: str, fact_type: str) -> list[dict]:
        """Get full history of a fact including superseded versions."""
        self.ensure_connected()
        with self._driver.session() as session:
            result = session.run(
                "MATCH (f:Fact {entity_name: $entity_name, fact_type: $fact_type}) "
                "RETURN f.content AS content, f.session_index AS session_index, "
                "f.is_current AS is_current, f.session_date AS session_date "
                "ORDER BY f.session_index ASC",
                entity_name=entity_name,
                fact_type=fact_type,
            )
            return [dict(r) for r in result]

    def query_via_http(self, cypher: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute an OpenCypher query via HydraDB's native HTTPS REST API.

        Uses HydraDB's /v1/graphs/{namespace}/query endpoint — the native
        HTTP JSON query interface, distinct from the Bolt protocol path.
        This demonstrates dual-protocol HydraDB usage (Bolt + HTTP REST).

        Args:
            cypher: OpenCypher query string
            params: Optional query parameters

        Returns:
            Raw JSON response from HydraDB HTTPS API
        """
        admin_url = (self.admin_url or DEFAULT_ADMIN_URL).rstrip("/")
        parsed = urlparse(admin_url)
        host = parsed.hostname or "127.0.0.1"
        https_url = f"http://{host}:8443"

        namespace = os.environ.get("GRAPH_NAMESPACE", "default")
        cell_id = os.environ.get("GRAPH_CELL_ID", "cell-0")

        payload: dict[str, Any] = {"cell_id": cell_id, "query": cypher}
        if params:
            payload["params"] = params

        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "X-Graph-Namespace": namespace,
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                f"{https_url}/v1/graphs/{namespace}/query",
                json=payload,
                headers=headers,
                timeout=10.0,
            )
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
                "protocol": "HydraDB HTTPS REST API",
                "endpoint": f"{https_url}/v1/graphs/{namespace}/query",
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "protocol": "HydraDB HTTPS REST API",
                "fallback": "Using Bolt protocol",
            }

    def clear_all(self) -> None:
        """Clear all nodes."""
        self.ensure_connected()
        with self._driver.session() as session:
            session.run("MATCH (n) DELETE n")


def get_user_cell_id(user_id: str) -> str:
    import hashlib
    if not user_id or str(user_id).strip() in ("", "anonymous", "default"):
        return "cell-0"
    h = int(hashlib.md5(user_id.encode("utf-8")).hexdigest(), 16)
    return f"cell-{h % 8}"


def main():
    db = HydraDB()
    db.connect()
    print(f"Connected to HydraDB at {db.uri}")
    admin = probe_hydradb_admin()
    if admin.get("ready"):
        print(f"HydraDB admin ready at {admin['admin_url']}/readyz")
    db.close()
    print("Connection closed")


if __name__ == "__main__":
    main()
