"""Repository-root entry point for the SireSoft-IKON pipeline."""

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

runpy.run_path(str(TOOLS / "run_pipeline.py"), run_name="__main__")
