#!/usr/bin/env python3
"""
Console demo runner for the interactive DesignAgent.

Run this from the project root directory.
"""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "skyknit"
sys.path.insert(0, str(src_path))

from console_demo import main  # noqa: E402

if __name__ == "__main__":
    main()
