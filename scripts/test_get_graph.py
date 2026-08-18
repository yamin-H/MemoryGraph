import sys
sys.path.insert(0, 'd:/users/OMNIROUTE-TEST/memorygraph/apps/api')
from services.memory_service import MemoryService

svc = MemoryService()
svc.hydra.connect()
graph_data = svc.get_all_graph(user_id='alex')
print(f"Graph for 'alex': {len(graph_data.get('nodes', []))} nodes, {len(graph_data.get('edges', []))} edges")
if graph_data.get('nodes'):
    print("Sample node:", graph_data['nodes'][0])
