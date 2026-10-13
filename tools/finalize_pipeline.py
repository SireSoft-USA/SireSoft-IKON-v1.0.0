"""Verify and publish one COMPLETE IKON model bundle after training.

An IKON checkpoint contains full weights, not one model shard per batch. The
bundle manifest identifies the three independent, version-matched artifacts:
trained LLM checkpoint, trained tokenizer and the persisted RAG index.

This command is intentionally a separate process so the just-finished training
process releases its model/GPU memory before verification. Verification loads
artifacts with the real production reader on CPU; CUDA training was already
verified separately by the strict training pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from real_runtime import ROOT, enter_project_root
from model_profiles import get_profile


def manifest_path(profile, root=ROOT):
    return Path(root) / "model_store" / "manifests" / f"ikon-{profile.name}-bundle.json"


def _file_info(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Artifact path escapes project directory: " + str(relative))
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError("Required artifact is missing or empty: " + str(path))

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def _verify_load(profile, root):
    # Called after the pipeline finishes in its own interpreter. No generation
    # or optimizer update is performed; the real model and retrieval loader are
    # used to catch corrupted/mismatched tokenizer, weights or indexes.
    if Path(root).resolve() != ROOT.resolve():
        raise ValueError("Real artifact loading only supports the project root")
    from chat_rag import build_stack

    args = SimpleNamespace(
        tokenizer=profile.tokenizer,
        checkpoint=profile.checkpoint,
        retrieval=profile.retrieval,
        device="cpu",
        cuda_device_index=0,
    )
    _, tokenizer_manager, inference, retrieval, _ = build_stack(args)
    model = inference.status().get("model") or {}
    retrieval_status = retrieval.status()
    actual_context = model.get("max_seq_len")
    if actual_context != profile.sequence_length:
        raise RuntimeError(
            f"Wrong model architecture: profile {profile.name} expects "
            f"{profile.sequence_length} tokens, loaded checkpoint supports {actual_context}."
        )
    if not inference.ready():
        raise RuntimeError("Checkpoint was loaded but inference is not ready")
    if retrieval_status.get("index_entries", 0) <= 0:
        raise RuntimeError("RAG index loaded with no searchable entries")
    # Build-stack itself loads the tokenizer; check it is usable, not just present.
    if not tokenizer_manager.tokenizer.encode("SireSoft"):
        raise RuntimeError("Tokenizer loaded but produced no tokens")
    return {
        "model": {
            "model_id": model.get("model_id"),
            "version": model.get("version"),
            "max_seq_len": actual_context,
            "parameter_count": model.get("parameter_count"),
            "vocab_size": model.get("vocab_size"),
        },
        "retrieval": {
            "documents": retrieval_status.get("documents"),
            "chunks": retrieval_status.get("chunks"),
            "index_entries": retrieval_status.get("index_entries"),
        },
    }


def publish_bundle(profile_name, root=ROOT, verify_load=True, loader=None):
    """Create a manifest ONLY after all three artifacts are present/loadable.

    `loader` is injectable solely for deterministic offline test fixtures.
    """
    root = Path(root).resolve()
    profile = get_profile(profile_name)
    artifacts = {
        "checkpoint": _file_info(root, profile.checkpoint),
        "tokenizer": _file_info(root, profile.tokenizer),
        "retrieval_index": _file_info(root, profile.retrieval),
    }
    loaded = None
    if verify_load:
        loaded = (loader or _verify_load)(profile, root)

    manifest = {
        "schema_version": 1,
        "kind": "siresoft-ikon-model-bundle",
        "profile": profile.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "context_window": profile.sequence_length,
        "artifacts": artifacts,
        "verified_load": bool(verify_load),
        "validation": loaded,
    }

    output = manifest_path(profile, root)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Only publish on success; a failed run must not leave a completed manifest.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent,
            prefix="." + output.name + ".", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(manifest, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return output, manifest


def main():
    parser = argparse.ArgumentParser(description="Verify and publish complete IKON model/tokenizer/RAG artifact bundle.")
    parser.add_argument("--profile", default="p5000-512", choices=("legacy", "p5000-512", "p5000-1024"))
    args = parser.parse_args()
    enter_project_root()
    output, manifest = publish_bundle(args.profile)
    print("IKON MODEL BUNDLE: VERIFIED AND SAVED")
    print("profile:", manifest["profile"])
    print("context tokens:", manifest["context_window"])
    for role, info in manifest["artifacts"].items():
        print(f"{role}: {info['path']} ({info['bytes']} bytes; sha256 {info['sha256'][:16]}...)")
    print("verified model:", manifest["validation"]["model"])
    print("verified retrieval:", manifest["validation"]["retrieval"])
    print("bundle manifest:", output)


if __name__ == "__main__":
    main()
