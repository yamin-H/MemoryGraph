import os
import sys
sys.path.insert(0, r'd:\users\OMNIROUTE-TEST\memorygraph\apps\api')
from db.hydra import HydraDB

h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()
print("Connected!")
with h._driver.session() as s:
    try:
        # Create standalone graph segment 1
        s.run('CREATE (a:TestA {id: $id1})-[:ANCHOR]->(aa:TestAAnchor {id: $id1})', id1=101)
        # Create standalone graph segment 2
        s.run('CREATE (b:TestB {id: $id2})-[:ANCHOR]->(bb:TestBAnchor {id: $id2})', id2=202)
        print('1. Setup OK')
    except Exception as e:
        print('1. Setup FAIL:', e)

    try:
        # Try to link them using MERGE
        s.run('MERGE (a:TestA {id: $id1})-[:LINK]->(b:TestB {id: $id2})', id1=101, id2=202)
        print('2. MERGE link: OK')
    except Exception as e:
        print('2. MERGE link FAIL:', type(e).__name__, e)
        
    try:
        # Try MATCH and CREATE
        s.run('MATCH (a:TestA {id: $id1}) CREATE (a)-[:LINK2]->(c:TestC {id: $id3})', id1=101, id3=303)
        print('3. MATCH CREATE: OK')
    except Exception as e:
        print('3. MATCH CREATE FAIL:', type(e).__name__, e)
