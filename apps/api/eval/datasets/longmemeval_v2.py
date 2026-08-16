"""LongMemEval V2 dataset loader."""

import json
import random
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve


class LongMemEvalV2Dataset:
    """Loader for LongMemEval V2 dataset."""

    DATA_DIR = Path(__file__).resolve().parents[4] / "data"
    FILE_NAME = "longmemeval_v2.json"
    URL = "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json"

    def __init__(self):
        """Initialize the LongMemEval V2 dataset loader."""
        self.data: list[dict[str, Any]] = []
        self._loaded = False

    def _get_file_path(self) -> Path:
        """Resolve path to local or cleaned LongMemEval V2 dataset file."""
        p = self.DATA_DIR / self.FILE_NAME
        if not p.exists():
            # Check s_cleaned
            alt = self.DATA_DIR / "longmemeval_s_cleaned.json"
            if alt.exists():
                return alt
        return p

    def load(self) -> list[dict[str, Any]]:
        """Load and parse dataset."""
        if self._loaded:
            return self.data

        file_path = self._get_file_path()
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            urlretrieve(self.URL, str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception:
            try:
                file_path.unlink()
            except Exception:
                pass
            urlretrieve(self.URL, str(file_path))
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

        self.data = []
        for item in raw_data:
            q_id = item.get("id") or item.get("question_id", "")
            example = {
                "question_id": q_id,
                "question_type": item.get("question_type", "general"),
                "question": item.get("question", ""),
                "answer": item.get("answer", ""),
                "question_date": item.get("question_date", ""),
                "sessions": item.get("sessions", item.get("haystack_sessions", [])),
                "session_dates": item.get("haystack_dates", item.get("session_dates", [])),
                "session_ids": item.get("haystack_session_ids", item.get("session_ids", [])),
                "answer_session_ids": item.get("answer_session_ids", []),
                "is_abstention": str(q_id).endswith("_abs") or item.get("is_abstention", False),
            }
            self.data.append(example)

        self._loaded = True
        return self.data

    def sample(self, n: int, seed: int = 42) -> list[dict[str, Any]]:
        """Return n random examples."""
        if not self._loaded:
            self.load()
        if n >= len(self.data):
            return self.data.copy()
        rng = random.Random(seed)
        return rng.sample(self.data, n)

    def get_by_type(self, question_type: str) -> list[dict[str, Any]]:
        """Filter examples by question type."""
        if not self._loaded:
            self.load()
        return [ex for ex in self.data if ex.get("question_type") == question_type]
