import os
import sys
sys.path.insert(0, r'd:\users\OMNIROUTE-TEST\memorygraph\apps\api')
from db.hydra import HydraDB

h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()
print("Connected!")
with h._driver.session() as s:
    try:
        s.run('MERGE (a {id: 501})-[:HAS]->(b {id: 601})')
        s.run('MERGE (a {id: 501})-[:HAS]->(c {id: 701})')
        res = s.run('MATCH (a {id: 501}) RETURN count(a) as c').single()
        print('User count:', res['c'])
    except Exception as e:
        print('FAIL:', e)
