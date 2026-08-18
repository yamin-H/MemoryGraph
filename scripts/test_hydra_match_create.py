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
    print("1. Creating node A")
    s.run("CREATE (a:TestA {id: $id})-[:ANCHOR]->(aa:TestAAnchor {id: $aid})", id=rid1, aid=aid1)
    
    print("2. Linking node A and node C via MATCH + CREATE")
    try:
        s.run("MATCH (a:TestA {id: $id}) CREATE (a)-[:LINK3]->(c:TestC {id: $mid})", id=rid1, mid=mid)
        print("MATCH + CREATE success")
    except Exception as e:
        print("MATCH + CREATE fail:", type(e).__name__, e)
