"""BEAM dataset loader."""

import json
import random
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve


class BEAMDataset:
    """Loader for BEAM dataset."""

    DATA_DIR = Path(__file__).resolve().parents[4] / "data"
    LOCAL_FILE = DATA_DIR / "beam_100k.json"
    REPO_URL = "https://github.com/mohammadtavakoli78/BEAM/raw/main/data/beam.json"
    CACHE_DIR = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "data"
    CACHE_FILE = CACHE_DIR / "beam.json"

    def __init__(self):
        """Initialize the BEAM dataset loader."""
        self.data: list[dict[str, Any]] = []
        self._loaded = False

    def _get_file_path(self) -> Path:
        """Resolve path to local or cached BEAM dataset file."""
        if self.LOCAL_FILE.exists():
            return self.LOCAL_FILE
        if self.CACHE_FILE.exists():
            return self.CACHE_FILE
        # Download if neither exists
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            urlretrieve(self.REPO_URL, self.CACHE_FILE)
            return self.CACHE_FILE
        except Exception:
            return self.LOCAL_FILE

    def load(self) -> list[dict[str, Any]]:
        """Load and parse BEAM dataset into standard format."""
        if self._loaded:
            return self.data

        file_path = self._get_file_path()
        if not file_path.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            print(f"Error loading BEAM: {e}")
            return []

        # Parse into standard format
        self.data = []
        for item_idx, item in enumerate(raw_data):
            if "question" in item and "answer" in item:
                self.data.append({
                    "question_id": item.get("id") or item.get("question_id", f"beam-{item_idx:03d}"),
                    "sessions": item.get("context", item.get("sessions", [])),
                    "question": item.get("question", ""),
                    "answer": item.get("answer", ""),
                    "question_type": item.get("question_type", "temporal"),
                })
            elif "conversation_seed" in item and "chat" in item:
                conv_seed = item.get("conversation_seed", {})
                seed_id = conv_seed.get("id", item_idx + 1)
                theme = conv_seed.get("title") or conv_seed.get("theme", "Software Development")
                chat_sessions = item.get("chat", [])
                
                for s_idx, sess in enumerate(chat_sessions):
                    if isinstance(sess, list):
                        for t_idx in range(0, len(sess) - 1, 2):
                            user_turn = sess[t_idx]
                            asst_turn = sess[t_idx + 1] if t_idx + 1 < len(sess) else {}
                            if user_turn.get("role") == "user":
                                q_text = user_turn.get("content", "")
                                clean_q = q_text.split("->->")[0].strip() if "->->" in q_text else q_text.strip()
                                if clean_q:
                                    self.data.append({
                                        "question_id": f"beam_{seed_id}_{s_idx+1}_{t_idx+1}",
                                        "sessions": chat_sessions,
                                        "question": clean_q,
                                        "answer": asst_turn.get("content", theme)[:300],
                                        "question_type": user_turn.get("question_type") or "agentic-synthesis",
                                    })

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
