"""BEAM dataset loader."""

import json
import random
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve


class BEAMDataset:
    """Loader for BEAM dataset."""

    REPO_URL = "https://github.com/mohammadtavakoli78/BEAM/raw/main/data/beam.json"
    CACHE_DIR = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "data"
    CACHE_FILE = CACHE_DIR / "beam.json"

    def __init__(self):
        self.data: list[dict[str, Any]] = []
        self._loaded = False

    def _download(self) -> Path:
        """Download dataset if not cached."""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

        if not self.CACHE_FILE.exists():
            print(f"Downloading BEAM from {self.REPO_URL}...")
            try:
                urlretrieve(self.REPO_URL, self.CACHE_FILE)
                print(f"Downloaded to {self.CACHE_FILE}")
            except Exception as e:
                print(f"Download failed: {e}")
                self.CACHE_FILE.write_text("[]")
                raise
        else:
            print(f"Using cached BEAM at {self.CACHE_FILE}")

        return self.CACHE_FILE

    def load(self) -> list[dict[str, Any]]:
        """Load and parse BEAM dataset into standard format."""
        if self._loaded:
            return self.data

        cache_file = self._download()

        try:
            with open(cache_file) as f:
                raw_data = json.load(f)
        except json.JSONDecodeError:
            print("Warning: Cache file corrupted, re-downloading...")
            cache_file.unlink(missing_ok=True)
            cache_file = self._download()
            with open(cache_file) as f:
                raw_data = json.load(f)

        # Parse into standard format
        # BEAM format may differ, adapt as needed
        self.data = []
        for item in raw_data:
            # BEAM typically has: question, answer, context (sessions), question_type
            sessions = item.get("context", item.get("sessions", []))
            example = {
                "question_id": item.get("id", f"beam-{len(self.data):03d}"),
                "sessions": sessions,
                "question": item.get("question", ""),
                "answer": item.get("answer", ""),
                "question_type": item.get("question_type", "temporal"),
            }
            self.data.append(example)

        self._loaded = True
        print(f"Loaded {len(self.data)} examples from BEAM")
        return self.data

    def sample(self, n: int, seed: int = 42) -> list[dict[str, Any]]:
        """Return n random examples."""
        if not self._loaded:
            self.load()

        if n >= len(self.data):
            return self.data.copy()

        random.seed(seed)
        return random.sample(self.data, n)

    def get_by_type(self, question_type: str) -> list[dict[str, Any]]:
        """Get all examples of a specific question type."""
        if not self._loaded:
            self.load()
        return [ex for ex in self.data if ex["question_type"] == question_type]


def main():
    """Test the loader."""
    dataset = BEAMDataset()
    examples = dataset.load()
    print(f"\nTotal examples: {len(examples)}")

    from collections import Counter
    types = Counter(ex["question_type"] for ex in examples)
    print(f"Question types: {dict(types)}")

    sample = dataset.sample(3)
    print(f"\nSample of 3:")
    for ex in sample:
        print(f"  ID: {ex['question_id']}")
        print(f"  Type: {ex['question_type']}")
        print(f"  Q: {ex['question']}")
        print(f"  A: {ex['answer'][:60]}...")
        print(f"  Sessions: {len(ex['sessions'])}")
        print()


if __name__ == "__main__":
    main()