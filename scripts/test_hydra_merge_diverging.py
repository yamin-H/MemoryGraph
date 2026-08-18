import random
import sys
sys.path.insert(0, 'd:/users/OMNIROUTE-TEST/memorygraph/apps/api')
from db.hydra import HydraDB
h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()

rid1 = random.randint(100000, 900000)
aid1 = rid1 + 100
mid = rid1 + 200

with h._driver.session() as s:
    try:
        s.run("MERGE (s:TestS {id: $id, status: 'active'})-[:ANCHOR]->(sa:TestAnchor {id: $aid})", id=rid1, aid=aid1)
        print("Success 1 (Anchor)")
    except Exception as e:
        print("Fail 1:", e)

with h._driver.session() as s:
    try:
        s.run("MERGE (s:TestS {id: $id, status: 'active'})-[:CONTAINS]->(m:TestM {id: $mid})", id=rid1, mid=mid)
        print("Success 2 (Contains)")
    except Exception as e:
        print("Fail 2:", e)
