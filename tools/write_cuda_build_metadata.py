"""Write metadata for a precompiled SireSoft-IKON CUDA backend."""

import argparse
import json
import platform
from datetime import datetime, timezone

from cuda_status import CUDA_LIBRARY, CUDA_METADATA, CUDA_SOURCE, sha256_file
from real_runtime import enter_project_root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arch", default="sm_61")
    parser.add_argument("--toolkit", required=True)
    parser.add_argument("--builder", default="local")
    parser.add_argument("--target", default="linux-x86_64")
    args = parser.parse_args()

    enter_project_root()
    if not CUDA_SOURCE.is_file():
        raise SystemExit("CUDA source is missing: " + str(CUDA_SOURCE))
    if not CUDA_LIBRARY.is_file() or CUDA_LIBRARY.stat().st_size == 0:
        raise SystemExit("CUDA library is missing: " + str(CUDA_LIBRARY))

    metadata = {
        "schema": 1,
        "architecture": args.arch,
        "cuda_toolkit": args.toolkit,
        "target": args.target,
        "builder": args.builder,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": sha256_file(CUDA_SOURCE),
        "library_sha256": sha256_file(CUDA_LIBRARY),
        "build_host": platform.platform(),
    }
    CUDA_METADATA.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Wrote:", CUDA_METADATA)
    print("source sha256:", metadata["source_sha256"])
    print("library sha256:", metadata["library_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
