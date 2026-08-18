import os
import sys
sys.path.insert(0, r'd:\users\OMNIROUTE-TEST\memorygraph\apps\api')
from db.hydra import HydraDB
h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()
print("Connected!")
with h._driver.session() as s:
    try:
        s.run('CREATE (a:TestA {id: 1})-[:R1]->(b:TestB {id: 1})')
        print('1. CREATE a-R1-b: OK')
    except Exception as e:
        print('1. FAIL:', type(e).__name__, e)

    try:
        s.run('MATCH (a:TestA {id: 1}) CREATE (a)-[:R2]->(c:TestC {id: 1})')
        print('2. MATCH a CREATE a-R2-c: OK')
    except Exception as e:
        print('2. FAIL:', type(e).__name__, e)

    try:
        s.run('CREATE (d:TestD {id: 1})-[:ANCHOR]->(da:TestDAnchor {id: 1})')
        s.run('MATCH (a:TestA {id: 1}), (d:TestD {id: 1}) CREATE (a)-[:R4]->(d)')
        print('3. MATCH a, d CREATE a-R4-d: OK')
    except Exception as e:
        print('3. FAIL:', type(e).__name__, e)
        
    try:
        s.run('CREATE (e:TestE {id: 1})-[:ANCHOR]->(ea:TestEAnchor {id: 1})')
        s.run('MATCH (a:TestA {id: 1}), (e:TestE {id: 1}) MERGE (a)-[:R5]->(e)')
        print('4. MATCH a, e MERGE a-R5-e: OK')
    except Exception as e:
        print('4. FAIL:', type(e).__name__, e)
