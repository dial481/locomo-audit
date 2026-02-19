#!/usr/bin/env python3
"""Verify third-party files match their official upstream sources.

Checks:
  - locomo10.json: SNAP Research LoCoMo dataset
  - prompts.yaml:  EverMemOS evaluation pipeline judge prompts
"""

import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

FILES = [
    {
        "path": REPO_ROOT / "data" / "locomo10.json",
        "sha256": "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4",
        "source": "snap-research/locomo/data/locomo10.json",
    },
    {
        "path": REPO_ROOT / "evaluation" / "config" / "prompts.yaml",
        "sha256": "ba4f668e72c3fba74a58b8ee56064568fb9c6aae1441e4f0f7a8f5edba498ee9",
        "source": "EverMemOS evaluation pipeline (llm_judge prompts)",
    },
]


def main():
    failed = False
    for entry in FILES:
        path = entry["path"]
        name = path.name
        if not path.exists():
            print(f"FAIL: {name} not found at {path}")
            failed = True
            continue

        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha256 == entry["sha256"]:
            print(f"OK:   {name} — SHA256 matches ({sha256[:16]}...)")
        else:
            print(f"FAIL: {name} — SHA256 mismatch")
            print(f"  Expected: {entry['sha256']}")
            print(f"  Got:      {sha256}")
            print(f"  Source:   {entry['source']}")
            failed = True

    if failed:
        sys.exit(1)
    print(f"\nAll {len(FILES)} files verified.")


if __name__ == "__main__":
    main()
