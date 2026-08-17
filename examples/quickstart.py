"""MemoryGraph Python SDK Quickstart.

Demonstrates 3-line drop-in agent memory integration with HydraDB.
"""

import sys
from pathlib import Path

# Add src to sys.path for local running
src_dir = str(Path(__file__).resolve().parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from memorygraph import MemoryGraph


def main():
    print("=" * 60)
    print("MemoryGraph Python SDK: 3-Line Drop-in Quickstart")
    print("=" * 60)

    # Step 1: Initialize client
    memory = MemoryGraph(api_url="http://localhost:8000")

    user_id = "alex-101"

    # Step 2: Add conversation sessions
    print("\n1. Ingesting multi-turn conversation session...")
    try:
        res = memory.add_session(
            user_id=user_id,
            session_id="session-001",
            messages=[
                {"role": "user", "content": "Hi! I am Alex. I currently live in Rajshahi and work as a software engineer."},
                {"role": "assistant", "content": "Great to meet you Alex!"},
            ],
        )
        print("   [OK] Session #1 ingested into HydraDB.")
    except Exception as e:
        print(f"   [INFO] API server status: {e}")

    # Step 3: Add updating session (Supersedes location)
    print("\n2. Ingesting update session (Alex moves to Dhaka)...")
    try:
        memory.add_session(
            user_id=user_id,
            session_id="session-002",
            messages=[
                {"role": "user", "content": "Big news! I just moved to Dhaka this week and have a new cat named Pixel."},
                {"role": "assistant", "content": "Congratulations on the move to Dhaka and the new cat!"},
            ],
        )
        print("   [OK] Session #2 ingested. SUPERSEDES edge created in HydraDB.")
    except Exception as e:
        print(f"   [INFO] Ingestion status: {e}")

    # Step 4: Query MemoryGraph
    print("\n3. Querying current memory state...")
    try:
        result = memory.query(user_id=user_id, query="Where does Alex live?")
        print(f"\n   Question: 'Where does Alex live?'")
        print(f"   Answer:     {result.answer}")
        print(f"   Confidence: {int(result.confidence * 100)}%")
        print(f"   Abstained:  {result.abstained}")
        print(f"   Latency:    {result.query_time_ms} ms")
    except Exception as e:
        print(f"   [INFO] Query response: {e}")

    # Step 5: Test Honest Abstention
    print("\n4. Testing Honest Abstention on trick query...")
    try:
        trick_result = memory.query(user_id=user_id, query="What is the name of Alex's pet dog?")
        print(f"\n   Question: 'What is the name of Alex's pet dog?'")
        print(f"   Answer:     {trick_result.answer}")
        print(f"   Abstained:  {trick_result.abstained}")
        print(f"   Confidence: {int(trick_result.confidence * 100)}%")
    except Exception as e:
        print(f"   [INFO] Trick query response: {e}")

    print("\n" + "=" * 60)
    print("MemoryGraph SDK execution complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
