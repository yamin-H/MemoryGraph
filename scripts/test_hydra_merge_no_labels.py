import random
import sys
sys.path.insert(0, 'd:/users/OMNIROUTE-TEST/memorygraph/apps/api')
from db.hydra import HydraDB
h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()

rid1 = random.randint(100000, 900000)
rid2 = random.randint(100000, 900000)

with h._driver.session() as s:
    print("1. Creating nodes without labels via MERGE")
    s.run("MERGE (a {id: $id1})-[:ANCH1]->(aa {id: $aid1})", id1=rid1, aid1=rid1+1)
    s.run("MERGE (b {id: $id2})-[:ANCH2]->(bb {id: $aid2})", id2=rid2, aid2=rid2+1)

with h._driver.session() as s:
    print("2. Linking existing nodes without labels via MERGE")
    try:
        s.run("MERGE (a {id: $id1})-[:REL]->(b {id: $id2})", id1=rid1, id2=rid2)
        print("MERGE without labels SUCCESS!")
    except Exception as e:
        print("MERGE without labels FAIL:", type(e).__name__, e)
