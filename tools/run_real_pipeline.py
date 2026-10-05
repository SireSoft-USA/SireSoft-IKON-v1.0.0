"""Backward-compatible entry point for the renamed pipeline.

Prefer: python tools/run_pipeline.py
"""

from run_pipeline import main


if __name__ == "__main__":
    main()
