"""HydraDB connection module using Neo4j driver."""

from __future__ import annotations

from neo4j import GraphDatabase
import neo4j


class HydraDB:
    """Connection to HydraDB via Neo4j Bolt protocol."""

    def __init__(
        self,
        uri: str = "neo4j://127.0.0.1:7687",
        auth_token: str = "neo4j/password",
    ):
        """Initialize the HydraDB connection client."""
        self.uri = uri
        self.auth_token = auth_token or "neo4j/password"
        self._driver = None

    def _build_auth(self):
        """Build a Neo4j auth object that works for local HydraDB and managed services."""
        token = self.auth_token or "neo4j/password"
        if "/" in token:
            username, password = token.split("/", 1)
            return neo4j.basic_auth(username, password)
        return neo4j.basic_auth("neo4j", token)

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
        if self.uri.startswith("neo4j://"):
            candidate_uris.append(self.uri.replace("neo4j://", "bolt://", 1))
        elif self.uri.startswith("bolt://"):
            candidate_uris.append(self.uri.replace("bolt://", "neo4j://", 1))

        last_exc = None
        for uri in candidate_uris:
            try:
                driver = GraphDatabase.driver(
                    uri,
                    auth=auth,
                )
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

    def write_fact(self, fact_id: int, content: str) -> None:
        """Write a Fact node to the graph.

        HydraDB requires:
        - Relationship patterns with two distinct nodes (source and destination)
        - id property must be an integer for both nodes
        - No MERGE followed by SET
        """
        self.ensure_connected()
        with self._driver.session() as session:
            # Create two nodes with a relationship between them
            # Using fact_id for the primary node, and fact_id + 1000000 for the anchor
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

    def clear_all(self) -> None:
        """Clear all nodes (useful for cleanup)."""
        self.ensure_connected()
        with self._driver.session() as session:
            session.run("MATCH (n) DELETE n")


def main():
    """Test HydraDB connection."""
    db = HydraDB()
    db.connect()
    print(f"Connected to HydraDB at {db.uri}")

    try:
        # Write test fact
        db.write_fact(1, "MemoryGraph is a graph-native agent memory layer")
        print("Wrote test Fact node: id=1")

        # Read it back
        fact = db.read_fact(1)
        print(f"Read back: {fact}")

        # Cleanup
        db.clear_all()
        print("Cleaned up test data")

    finally:
        db.close()
        print("Connection closed")


if __name__ == "__main__":
    main()
