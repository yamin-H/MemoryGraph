#!/usr/bin/env python3
"""
Initialize local HydraDB OSS storage for MemoryGraph.

Creates the directory layout required by the official HydraDB Docker image:
  hydradb-data/
    ├── store/          ← durable graph (LOCAL_PATH)
    ├── cache/          ← graph-node SSD cache
    └── auth-token      ← Bolt/HTTP auth token (GRAPH_AUTH_TOKEN_FILE)

Run this BEFORE `docker compose up` the first time.

Usage:
    python scripts/setup_hydradb.py
    python scripts/setup_hydradb.py --token "my-custom-token-at-least-32-chars!!"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HYDRADB_ROOT = PROJECT_ROOT / "hydradb-data"
DEFAULT_TOKEN = "local-development-token-32-bytes"

REQUIRED_DIRS = [
    HYDRADB_ROOT / "store",
    HYDRADB_ROOT / "cache",
    PROJECT_ROOT / "scripts" / "data",
]


def setup_hydradb(token: str = DEFAULT_TOKEN) -> Path:
    """Create HydraDB OSS local directories and auth token file."""
    if len(token.strip()) < 16:
        raise ValueError("HydraDB auth token must be at least 16 characters.")

    for directory in REQUIRED_DIRS:
        directory.mkdir(parents=True, exist_ok=True)

    token_file = HYDRADB_ROOT / "auth-token"
    token_file.write_text(token.strip() + "\n", encoding="utf-8")

    return token_file


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Prepare HydraDB OSS local storage for MemoryGraph",
    )
    parser.add_argument(
        "--token",
        default=DEFAULT_TOKEN,
        help=f"Bolt/HTTP auth token (default: {DEFAULT_TOKEN})",
    )
    args = parser.parse_args()

    print("Setting up HydraDB OSS local storage...")
    print(f"  Repository: {PROJECT_ROOT}")
    print(f"  Data root:    {HYDRADB_ROOT}")
    print()

    try:
        token_file = setup_hydradb(args.token)
    except ValueError as exc:
        print(f"  [ERROR] {exc}", file=sys.stderr)
        return 1

    for directory in REQUIRED_DIRS:
        print(f"  [OK] {directory}")

    print(f"  [OK] {token_file} (auth token written)")
    print()
    print("Next steps:")
    print("  1. docker compose pull hydradb")
    print("  2. docker compose up --build")
    print("  3. python scripts/verify_hydradb.py")
    print()
    print("HydraDB OSS image: ghcr.io/hydra-db/hydradb:latest")
    print("Upstream repo:     https://github.com/hydra-db/hydradb")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
