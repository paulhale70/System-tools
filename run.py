#!/usr/bin/env python3
"""System Resource Monitor - Entry point."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from system_monitor.app import main

if __name__ == "__main__":
    main()
