"""LongMemEval dataset loader."""

import json
import random
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve


class LongMemEvalDataset:
    """Loader for LongMemEval dataset."""

    DATA_DIR = Path(__file__).resolve().parents[4] / "data"

    FILES = {
        "oracle": "longmemeval_oracle.json",
        "s": "longmemeval_s_cleaned.json",
        "m": "longmemeval_m_cleaned.json",
    }

    URLS = {
        "oracle": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_oracle.json",
        "s": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json",
        "m": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_m_cleaned.json",
    }

    def __init__(self, split: str = "oracle"):
        """Initialize the LongMemEval dataset loader."""
        if split not in self.FILES:
            split = "oracle"
        self.split = split
        self.data: list[dict[str, Any]] = []
        self._loaded = False

    def _get_file_path(self) -> Path:
        """Resolve file path for the given dataset split."""
        return self.DATA_DIR / self.FILES[self.split]

    def load(self) -> list[dict[str, Any]]:
        """Load and parse dataset."""
        if self._loaded:
            return self.data

        file_path = self._get_file_path()
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            urlretrieve(self.URLS[self.split], str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception:
            try:
                file_path.unlink()
            except Exception:
                pass
            urlretrieve(self.URLS[self.split], str(file_path))
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