import sys; sys.path.insert(0, 'd:/users/OMNIROUTE-TEST/memorygraph/apps/api')
from db.hydra import HydraDB
h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()
s = h._driver.session()

import random
rid1 = random.randint(100000, 900000)
rid2 = random.randint(100000, 900000)

print("1. Creating node A and B via MERGE")
with h._driver.session() as s:
    s.run("MERGE (x:TestX {id: $id1})-[:ANCH]->(xa:TestXAnchor {id: $aid1})", id1=rid1, aid1=rid1+1)

with h._driver.session() as s:
    s.run("MERGE (y:TestY {id: $id2})-[:ANCH]->(ya:TestYAnchor {id: $aid2})", id2=rid2, aid2=rid2+1)

print("2. Linking node A and B via MERGE")
with h._driver.session() as s:
    s.run("MERGE (x:TestX {id: $id1})-[:RELS]->(y:TestY {id: $id2})", id1=rid1, id2=rid2)

print("3. Checking for duplicates")
with h._driver.session() as s:
    resX = s.run(f"MATCH (x {{id: {rid1}}}) RETURN count(x) as c").single()
    resY = s.run(f"MATCH (y {{id: {rid2}}}) RETURN count(y) as c").single()

print(f"TestX count: {resX['c']}")
print(f"TestY count: {resY['c']}")
