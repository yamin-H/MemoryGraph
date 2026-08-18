import random
import sys
sys.path.insert(0, 'd:/users/OMNIROUTE-TEST/memorygraph/apps/api')
from db.hydra import HydraDB
h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()

rid1 = random.randint(100000, 900000)
aid1 = rid1 + 100

query = "MERGE (s:TestS {id: $id, status: 'active'})-[:ANCHOR]->(sa:TestAnchor {id: $aid})"

print("First MERGE:")
with h._driver.session() as s:
    try:
        s.run(query, id=rid1, aid=aid1)
        print("Success 1")
    except Exception as e:
        print("Fail 1:", e)

print("Second MERGE (identical):")
with h._driver.session() as s:
    try:
        s.run(query, id=rid1, aid=aid1)
        print("Success 2")
    except Exception as e:
        print("Fail 2:", e)
