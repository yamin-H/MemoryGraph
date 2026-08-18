import sys
sys.path.insert(0, 'd:/users/OMNIROUTE-TEST/memorygraph/apps/api')
from db.hydra import HydraDB

h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()

def test_query(label, q, **kwargs):
    print(f"\n--- Testing {label} ---")
    print("Query:", q)
    print("Params:", kwargs)
    with h._driver.session() as s:
        try:
            s.run(q, **kwargs)
            print(">>> SUCCESS")
        except Exception as e:
            print(">>> FAILED:", type(e), e)

test_query("SET entity name", "MATCH (e:Entity {id: $entity_id}) SET e.name = $entity_name", entity_id=12345, entity_name="Alex")

test_query("MATCH SET fact is_current", "MATCH (f:Fact {id: $old_id}) SET f.is_current = false", old_id=12345)

test_query("2-node MATCH + MERGE", "MATCH (f_new:Fact {id: $new_id}), (f_old:Fact {id: $old_id}) MERGE (f_new)-[:SUPERSEDES]->(f_old)", new_id=111, old_id=222)

test_query("1-hop MERGE SUPERSEDES", "MERGE (f_new:Fact {id: $new_id})-[:SUPERSEDES]->(f_old:Fact {id: $old_id})", new_id=111, old_id=222)

test_query("1-hop MERGE INVALIDATED_BY", "MERGE (f:Fact {id: $fact_int_id})-[:INVALIDATED_BY {reason: $reason}]->(s:Session {id: $session_int_id})", fact_int_id=111, reason="expired", session_int_id=333)
