import random
import sys
sys.path.insert(0, 'd:/users/OMNIROUTE-TEST/memorygraph/apps/api')
from db.hydra import HydraDB
h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()

rid1 = random.randint(100000, 900000)
aid1 = rid1 + 100
mid = rid1 + 200
maid = mid + 1000

session_props_cypher = "id: $id, session_id: $sid_str, user_id: $uid, started_at: $sat, status: 'active'"

with h._driver.session() as s:
    print("Testing sequence...")
    s.run(f"MERGE (s:Session {{{session_props_cypher}}})-[:SESSION_ANCHOR]->(sa:SessionAnchor {{id: $aid}})", 
          id=rid1, sid_str="sess1", uid="user1", sat="2024-01-01T00:00:00", aid=aid1)
    
    try:
        s.run(f"MERGE (s:Session {{{session_props_cypher}}})-[:CONTAINS]->(m:Message {{id: $mid, role: 'user', content: 'hello', created_at: '2024'}})", 
              id=rid1, sid_str="sess1", uid="user1", sat="2024-01-01T00:00:00", mid=mid)
        print("CONTAINS success")
    except Exception as e:
        print("CONTAINS fail:", type(e).__name__, e)

    try:
        s.run("MERGE (m:Message {id: $mid, role: 'user', content: 'hello', created_at: '2024'})-[:MESSAGE_ANCHOR]->(ma:MessageAnchor {id: $maid})", 
              mid=mid, maid=maid)
        print("MESSAGE_ANCHOR success")
    except Exception as e:
        print("MESSAGE_ANCHOR fail:", type(e).__name__, e)
