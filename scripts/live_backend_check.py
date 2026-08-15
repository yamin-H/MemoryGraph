import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from apps.api.config import settings
from apps.api.db.hydra import HydraDB
from services.memory_service import MemoryService


def main() -> None:
    print("Starting live backend verification...")
    db = HydraDB()
    db.connect()

    try:
        with db._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

        fixture_path = ROOT / "tests" / "fixtures" / "sample_sessions.json"
        with fixture_path.open("r", encoding="utf-8") as handle:
            sessions = json.load(handle)["sessions"]
        sample = sessions[0]

        service = MemoryService()
        ingest_result = service.ingest_session(sample)
        print("INGEST_OK", ingest_result)

        query_result = service.query_memory("Where does Alex live?", user_id="alex")
        print("QUERY_OK", query_result)

        entity_result = service.get_entity_memory("Alex", user_id="alex")
        print("ENTITY_OK", entity_result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
