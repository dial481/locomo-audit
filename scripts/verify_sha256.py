#!/usr/bin/env python3
"""Verify locomo10.json matches the official SNAP Research dataset."""

import hashlib
import sys
from pathlib import Path

EXPECTED_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
DATA_PATH = Path(__file__).parent.parent / "data" / "locomo10.json"


def main():
    if not DATA_PATH.exists():
        print(f"FAIL: {DATA_PATH} not found")
        sys.exit(1)

    sha256 = hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()

    if sha256 == EXPECTED_SHA256:
        print(f"OK: SHA256 matches ({sha256})")
    else:
        print(f"FAIL: SHA256 mismatch")
        print(f"  Expected: {EXPECTED_SHA256}")
        print(f"  Got:      {sha256}")
        sys.exit(1)


if __name__ == "__main__":
    main()
