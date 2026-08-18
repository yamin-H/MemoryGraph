import sys
sys.path.insert(0, 'd:/users/OMNIROUTE-TEST/memorygraph/apps/api')
from db.hydra import HydraDB
from pipeline.ingestion.writer import write_to_hydradb

h = HydraDB('neo4j://127.0.0.1:7687', 'local-development-token-32-bytes')
h.connect()

session_data = {
    "session_id": "test-sess-99",
    "user_id": "alex",
    "started_at": "2024-01-01T00:00:00Z",
    "messages": [{"role": "user", "content": "Hello", "created_at": "2024-01-01T00:00:00Z"}]
}
facts = [
    {"fact_id": "fact-1", "content": "Alex works at TechCorp", "confidence": 0.9, "entity_name": "Alex", "created_at": "2024-01-01T00:00:00Z"},
    {"fact_id": "fact-2", "content": "Alex works at Google", "confidence": 0.95, "entity_name": "Alex", "created_at": "2024-01-01T00:00:00Z"}
]
supersessions = [
    {"new_fact_id": "fact-2", "supersedes_fact_id": "fact-1"}
]
invalidations = [
    {"fact_id": "fact-1", "reason": "superseded"}
]

print("Testing full write_to_hydradb with supersessions & invalidations...")
try:
    res = write_to_hydradb(
        hydra=h,
        session=session_data,
        summary={"summary_id": "sum-1", "content": "Test summary", "generated_at": "2024-01-01T00:00:00Z"},
        facts=facts,
        supersessions=supersessions,
        invalidations=invalidations
    )
    print("Result:", res)
    print("SUCCESS!")
except Exception as e:
    print("FAILED:", type(e), e)
