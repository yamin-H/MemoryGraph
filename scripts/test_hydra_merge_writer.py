import random
import sys
sys.path.insert(0, 'd:/users/OMNIROUTE-TEST/memorygraph/apps/api')
from db.hydra import HydraDB
h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()

rid1 = random.randint(100000, 900000)
aid1 = rid1 + 100
mid = rid1 + 200

session_props_cypher = "id: $id, session_id: $sid_str, user_id: $uid, started_at: $sat, status: 'active'"

with h._driver.session() as s:
    try:
        s.run(f"MERGE (s:Session {{{session_props_cypher}}})-[:SESSION_ANCHOR]->(sa:SessionAnchor {{id: $aid}})", 
              id=rid1, sid_str="sess1", uid="user1", sat="2024-01-01T00:00:00", aid=aid1)
        print("Success 1 (Anchor)")
    except Exception as e:
        print("Fail 1:", e)

with h._driver.session() as s:
    try:
        s.run(f"MERGE (s:Session {{{session_props_cypher}}})-[:CONTAINS]->(m:Message {{id: $mid, role: 'user', content: 'hello', created_at: '2024'}})", 
              id=rid1, sid_str="sess1", uid="user1", sat="2024-01-01T00:00:00", mid=mid)
        print("Success 2 (Contains)")
    except Exception as e:
        print("Fail 2:", e)
