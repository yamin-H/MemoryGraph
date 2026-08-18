import sys; sys.path.insert(0, 'd:/users/OMNIROUTE-TEST/memorygraph/apps/api')
from db.hydra import HydraDB
import random

h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()
s = h._driver.session()

rid = random.randint(100000, 900000)

print(f"Testing CREATE upsert behavior with id {rid}")

try:
    s.run("CREATE (s:TestS {id: $id})-[:C]->(m1:TestM {id: $m1})", id=rid, m1=rid+1)
    s.run("CREATE (s:TestS {id: $id})-[:C]->(m2:TestM {id: $m2})", id=rid, m2=rid+2)
    
    # Check if TestS was duplicated
    res = s.run("MATCH (s {id: $id}) RETURN count(s) as c", id=rid).single()
    print("Count of TestS:", res['c'])
except Exception as e:
    print("FAIL:", type(e).__name__, e)
