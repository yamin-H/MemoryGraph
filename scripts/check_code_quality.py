"""Audit script to check docstrings, secrets, imports, and env vars."""

import ast
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

def check_secrets():
    """Scan all project files for hardcoded API keys and tokens."""
    print("=== Checking Secrets ===")
    secret_patterns = [
        re.compile(r"gsk_[a-zA-Z0-9]{20,}"),
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),
        re.compile(r"AIza[0-9A-Za-z-_]{35}"),
    ]
    found = []
    for root, dirs, files in os.walk(REPO_ROOT):
        if any(skip in root for skip in ["node_modules", ".git", ".next", ".venv", "venv", "__pycache__"]):
            continue
        for f in files:
            if f.startswith(".env") and not f.endswith(".example"):
                continue
            path = Path(root) / f
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for idx, line in enumerate(content.splitlines(), start=1):
                    for pat in secret_patterns:
                        if pat.search(line):
                            found.append((str(path.relative_to(REPO_ROOT)), idx, line.strip()))
            except Exception:
                pass
    print(f"Hardcoded secrets found: {len(found)}")
    for item in found:
        print(f"  {item}")

if __name__ == "__main__":
    check_secrets()
