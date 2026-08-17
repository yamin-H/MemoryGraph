"""Application configuration and environment validation."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


class Settings:
    """Strongly typed application settings for the backend."""

    def __init__(self) -> None:
        """Initialize settings from environment variables."""
        self.hydra_uri = os.environ.get("HYDRADB_URI", "neo4j://127.0.0.1:7687")
        self.hydra_token = os.environ.get("HYDRADB_TOKEN", "local-development-token-32-bytes")
        self.hydra_admin_url = os.environ.get("HYDRADB_ADMIN_URL", "http://127.0.0.1:9090")
        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        self.groq_api_key = os.environ.get("GROQ_API_KEY")
        self.groq_model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
        self.graph_namespace = os.environ.get("GRAPH_NAMESPACE", "default")
        self.graph_cell_id = os.environ.get("GRAPH_CELL_ID", "cell-0")

    def validate_required(self) -> None:
        """Raise if critical runtime settings are missing."""
        missing: list[str] = []
        if not self.hydra_uri:
            missing.append("HYDRADB_URI")
        if not self.hydra_token:
            missing.append("HYDRADB_TOKEN")
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


settings = Settings()
