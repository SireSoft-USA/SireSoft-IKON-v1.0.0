"""Versioned training/serving profiles. Profiles never overwrite the legacy artifacts.

The larger presets are *starting configurations*, not quality guarantees or measured
GPU capacity targets. Validate speed and peak memory before a full training run.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProfile:
    name: str
    sequence_length: int
    d_model: int
    layers: int
    heads: int
    d_ff: int
    batch_size: int
    epochs: int
    vocab_size: int
    records_per_dataset: int
    tokenizer_records_per_dataset: int
    max_new_tokens: int
    tokenizer: str
    checkpoint: str
    retrieval: str


PROFILES = {
    "legacy": ModelProfile(
        "legacy", 64, 32, 2, 4, 128, 4, 1, 512, 250, 2000, 8,
        "model_store/manifests/sirellm_tokenizer.sltok",
        "model_store/checkpoints/sirellm-v1.lbckpt",
        "vector_store/indexes/siresoft.slretr",
    ),
    # Conservative first step for this custom Python/CUDA runtime. Pascal P5000
    # has 16GB VRAM, but GPU usage cannot be predicted from VRAM alone.
    "p5000-512": ModelProfile(
        "p5000-512", 512, 128, 4, 4, 512, 1, 3, 4096, 2000, 5000, 96,
        "model_store/manifests/sirellm_tokenizer_p5000_512.sltok",
        "model_store/checkpoints/sirellm-p5000-512.lbckpt",
        "vector_store/indexes/siresoft-p5000-512.slretr",
    ),
    # Experimental: benchmark *before* committing to long training.
    "p5000-1024": ModelProfile(
        "p5000-1024", 1024, 192, 4, 6, 768, 1, 3, 4096, 2000, 5000, 160,
        "model_store/manifests/sirellm_tokenizer_p5000_1024.sltok",
        "model_store/checkpoints/sirellm-p5000-1024.lbckpt",
        "vector_store/indexes/siresoft-p5000-1024.slretr",
    ),
}


def get_profile(name):
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError("Unknown IKON model profile: " + str(name)) from exc


def artifact_paths(name):
    profile = get_profile(name)
    return {
        "tokenizer": profile.tokenizer,
        "checkpoint": profile.checkpoint,
        "retrieval index": profile.retrieval,
    }
