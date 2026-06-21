#!/usr/bin/env python3
"""Entry point for BadBuilder (Linux)."""
from badbuilder.builder import run

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nCancelled.")
