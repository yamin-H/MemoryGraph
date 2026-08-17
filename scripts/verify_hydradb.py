#!/usr/bin/env python3
"""
Verify HydraDB OSS is reachable and can round-trip a write over Bolt.

A listening port is not proof the node works — a round-tripped write is.
Matches the verification flow from https://github.com/hydra-db/hydradb

Usage:
    python scripts/verify_hydradb.py
    HYDRADB_URI=neo4j://127.0.0.1:7687 python scripts/verify_hydradb.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_URI = "neo4j://127.0.0.1:7687"
DEFAULT_TOKEN = "local-development-token-32-bytes"
DEFAULT_ADMIN_URL = "http://127.0.0.1:9090"
TEST_NODE_A = 9_900_001
TEST_NODE_B = 9_900_002


def verify(uri: str, token: str, admin_url: str) -> None:
    """Connect via Bolt driver and prove HydraDB admin + OpenCypher round-trip."""
    sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))
    from db.hydra import build_bolt_auth, probe_hydradb_admin
    from neo4j import GraphDatabase

    auth, _ = build_bolt_auth(token)

    print(f"Checking HydraDB admin at {admin_url}/readyz ...")
    admin = probe_hydradb_admin(admin_url)
    if admin.get("ready"):
        print("  [OK] HydraDB admin /readyz responded (OSS graph-node)")
    else:
        raise RuntimeError(
            "HydraDB admin not ready — ensure `docker compose up hydradb` is running, "
            f"not Neo4j Community. Details: {admin}"
        )

    print(f"Connecting to HydraDB Bolt at {uri} ...")
    driver = GraphDatabase.driver(uri, auth=auth)
    try:
        driver.verify_connectivity()
        print("  [OK] Bolt connectivity verified")

        with driver.session() as session:
            session.run(
                "CREATE (a {id: $a})-[:MEMORYGRAPH_VERIFY]->(b {id: $b})",
                a=TEST_NODE_A,
                b=TEST_NODE_B,
            )
            record = session.run(
                "MATCH (a {id: $a})-[:MEMORYGRAPH_VERIFY]->(b) RETURN b.id AS id",
                a=TEST_NODE_A,
            ).single()

            if record is None or record["id"] != TEST_NODE_B:
                raise RuntimeError("Write/read round-trip failed — unexpected query result")

            session.run("MATCH (n) WHERE n.id IN [$a, $b] DETACH DELETE n", a=TEST_NODE_A, b=TEST_NODE_B)

        print("  [OK] OpenCypher write + read round-trip succeeded")
        print()
        print("HydraDB OSS is ready for MemoryGraph.")
        print("Image: ghcr.io/hydra-db/hydradb:latest")
    finally:
        driver.close()


def main() -> int:
    """CLI entrypoint."""
    uri = os.environ.get("HYDRADB_URI", DEFAULT_URI)
    token = os.environ.get("HYDRADB_TOKEN", DEFAULT_TOKEN)
    admin_url = os.environ.get("HYDRADB_ADMIN_URL", DEFAULT_ADMIN_URL)

    try:
        verify(uri, token, admin_url)
        return 0
    except Exception as exc:
        print(f"  [FAIL] {exc}", file=sys.stderr)
        print()
        print("Troubleshooting:")
        print("  1. Run: python scripts/setup_hydradb.py")
        print("  2. Start HydraDB: docker compose up hydradb")
        print("  3. Wait for /readyz: curl http://127.0.0.1:9090/readyz")
        print("  4. Ensure HYDRADB_TOKEN matches hydradb-data/auth-token")
        print("  5. Do NOT use Neo4j Community (neo4j:5.x) — use ghcr.io/hydra-db/hydradb")
        print("  6. See docs/HYDRADB_SETUP.md")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
