"""Run the reproducible benchmark entry point from the repository root."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))
sys.path.insert(0, str(ROOT))

from eval.runner import main


if __name__ == "__main__":
    main()
