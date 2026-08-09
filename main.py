#!/usr/bin/env python
import os
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from renewable_atlas.cli import main

if __name__ == "__main__":
    main()
