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
    s.run(f"MERGE (s:Session {{{session_props_cypher}}})-[:SESSION_ANCHOR]->(sa:SessionAnchor {{id: $aid}})", 
          id=rid1, sid_str="sess1", uid="user1", sat="2024-01-01T00:00:00", aid=aid1)
    print("SESSION_ANCHOR success")

with h._driver.session() as s:
    try:
        s.run("MERGE (s:Session {id: $id})-[:CONTAINS]->(m:Message {id: $mid})", 
              id=rid1, mid=mid)
        print("CONTAINS success")
    except Exception as e:
        print("CONTAINS fail:", type(e).__name__, e)

with h._driver.session() as s:
    try:
        res = s.run(f"MATCH (s:Session {{id: {rid1}}}) RETURN count(s) as c").single()
        print("Session count:", res['c'])
    except Exception as e:
        print("Count failed:", e)
