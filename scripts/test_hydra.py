import os
from dotenv import load_dotenv
load_dotenv()
from neo4j import GraphDatabase

d = GraphDatabase.driver(
    os.environ.get('HYDRADB_URI', 'neo4j://127.0.0.1:7687'),
    auth=('neo4j', os.environ.get('HYDRADB_TOKEN', 'local-development-token-32-bytes'))
)
s = d.session()

print("1. Creating nodes via CREATE (a)-[r]->(b)")
try:
    s.run("CREATE (s:Session {id: 999})-[:ANCHOR]->(sa:SessionAnchor {id: 9999})")
    print("  -> OK")
except Exception as e:
    print(f"  -> FAIL: {e}")

print("2. Creating nodes via MERGE (a)-[r]->(b)")
try:
    s.run("MERGE (s:Session {id: 999})-[:ANCHOR]->(sa:SessionAnchor {id: 9999})")
    print("  -> OK")
except Exception as e:
    print(f"  -> FAIL: {e}")

print("3. Matching one node and creating another")
try:
    s.run("MATCH (s:Session {id: 999}) CREATE (s)-[:CONTAINS]->(m:Message {id: 888})")
    print("  -> OK")
except Exception as e:
    print(f"  -> FAIL: {e}")

print("4. Matching two nodes and creating an edge")
try:
    s.run("CREATE (m:Message {id: 777})-[:ANCHOR]->(ma:MessageAnchor {id: 7777})")
    s.run("MATCH (s:Session {id: 999}), (m:Message {id: 777}) CREATE (s)-[:CONTAINS]->(m)")
    print("  -> OK")
except Exception as e:
    print(f"  -> FAIL: {e}")
