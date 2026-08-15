#!/usr/bin/env python3
"""Debug retrieval to understand why the graph queries return zero facts."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from apps.api.db.hydra import HydraDB
from apps.api.config import settings
from apps.api.pipeline.retrieval.traversal import traverse_for_question


def main():
    print("Debugging HydraDB retrieval...\n")
    print(f"URI: {settings.hydra_uri}")
    print(f"TOKEN: {settings.hydra_token}\n")

    db = HydraDB(uri=settings.hydra_uri, auth_token=settings.hydra_token)
    db.connect()

    try:
        with db._driver.session() as s:
            # 1. Count facts
            count_result = s.run("MATCH (f:Fact) RETURN count(f) as c").single()
            print(f"Total facts in DB: {count_result['c']}")

            # 2. Count entities
            entity_count = s.run("MATCH (e:Entity) RETURN count(e) as c").single()
            print(f"Total entities in DB: {entity_count['c']}")

            # 3. Show entities
            entities = s.run("MATCH (e:Entity) RETURN e.name as name").data()
            print(f"\nEntities: {[e['name'] for e in entities]}")

            # 4. Show facts
            facts = s.run("MATCH (f:Fact) WHERE f.is_current = true RETURN f.content as content").data()
            print(f"\nCurrent facts: {[f['content'] for f in facts if f['content']]}")

            # 5. Show mentions relationship
            mentions = s.run(
                "MATCH (f:Fact {is_current: true})-[:MENTIONS]->(e:Entity) "
                "RETURN f.content as content, e.name as entity_name"
            ).data()
            print(f"\nFacts with mentions: {mentions}")

            # 6. Now try traversal
            parsed = {"entity_name": "Alex", "question_type": "current_fact", "keywords": ["live", "location"]}
            result = traverse_for_question(db, parsed)
            print(f"\nTraversal result for Alex: {result}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
