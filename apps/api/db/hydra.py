"""HydraDB connection module using Neo4j driver."""

from neo4j import GraphDatabase
import neo4j


class HydraDB:
    """Connection to HydraDB via Neo4j Bolt protocol."""

    def __init__(
        self,
        uri: str = "neo4j://127.0.0.1:7687",
        auth_token: str = "local-development-token-32-bytes",
    ):
        self.uri = uri
        self.auth_token = auth_token
        self._driver = None

    def connect(self) -> None:
        """Establish connection to HydraDB."""
        self._driver = GraphDatabase.driver(
            self.uri,
            auth=neo4j.bearer_auth(self.auth_token),
        )

    def close(self) -> None:
        """Close the connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def write_fact(self, fact_id: int, content: str) -> None:
        """Write a Fact node to the graph.

        HydraDB requires:
        - Relationship patterns with two distinct nodes (source and destination)
        - id property must be an integer for both nodes
        - No MERGE followed by SET
        """
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
