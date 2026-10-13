"""One-command complete SireSoft-IKON build: datasets -> tokenizer -> LLM -> RAG.

The worker in tools/run_pipeline.py performs every stage, writes the final
complete .lbckpt checkpoint, verifies it can be loaded with its tokenizer and
retrieval index, and saves a versioned bundle manifest. Intermediate epoch/step
checkpoints are full recoverable snapshots, not model shards to concatenate.

Example on the GPU server:
    python run_pipeline.py --profile p5000-512 --device cuda
Use --start-app to launch the UI after successful model verification.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from tools.run_pipeline import main

if __name__ == "__main__":
    main()
