#!/usr/bin/env python3
"""
Initialize and verify the HydraDB local storage directory hierarchy.

Creates the required folder structure:
  hydradb-data/
    ├── data/
    ├── logs/
    ├── import/
    └── plugins/
  scripts/data/
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

HYDRADB_DIRS = [
    PROJECT_ROOT / "hydradb-data" / "data",
    PROJECT_ROOT / "hydradb-data" / "logs",
    PROJECT_ROOT / "hydradb-data" / "import",
    PROJECT_ROOT / "hydradb-data" / "plugins",
    PROJECT_ROOT / "scripts" / "data",
    PROJECT_ROOT.parent / "hydradb-data" / "data",
    PROJECT_ROOT.parent / "hydradb-data" / "logs",
    PROJECT_ROOT.parent / "hydradb-data" / "import",
    PROJECT_ROOT.parent / "hydradb-data" / "plugins",
]


def setup_directories() -> list[Path]:
    """Create all required data and storage directories automatically."""
    created = []
    for d in HYDRADB_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        created.append(d)
    return created


def main() -> None:
    """Main entrypoint for directory setup."""
    print("Setting up HydraDB directory structure...")
    dirs = setup_directories()
    for d in dirs:
        print(f"  [OK] Verified directory: {d}")
    print("HydraDB data structure initialized successfully.")


if __name__ == "__main__":
    main()
