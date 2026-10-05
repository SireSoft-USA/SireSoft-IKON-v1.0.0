# SireSoft-IKON Real Execution

## Production GPU run

The deployment pipeline is GPU-only by default:

```bash
python run_pipeline.py
```

The server does not compile CUDA code. It requires the precompiled
`libs/core/gpu/libsireikon_cuda.so` produced by GitHub Actions (or by the manual
Linux CUDA 12.x build command) and matching `.build.json` metadata.

Before a full run, verify the runtime once:

```bash
python tools/cuda_status.py --arch sm_61
python tools/test_gpu_training.py --arch sm_61 --require-cuda
```

If either the binary, metadata, NVIDIA GPU, or CUDA runtime activation is not
usable, strict CUDA mode stops before full training instead of falling back to
CPU.

## Useful variants

CPU-only development/laptop run:

```bash
python run_pipeline.py --device cpu
```

Continue an interrupted GPU run automatically:

```bash
python run_pipeline.py
```

Force a fresh GPU run:

```bash
python run_pipeline.py --fresh
```

Run everything and start the application after artifacts are ready:

```bash
python run_pipeline.py --start-app
```

## Build the CUDA backend (development/CI only)

Recommended: push to `main` and let `.github/workflows/build-cuda-backend.yml`
build and commit the Linux `sm_61` backend automatically.

Manual Linux/WSL CUDA 12.x build:

```bash
python tools/build_cuda_backend.py --arch sm_61 --required
```

The production server does not need `nvcc` or a CUDA Toolkit installation.

## CPU-only checkpoint test

```bash
python tools/test_training_recovery.py
```

## Output artifacts

```text
model_store/manifests/sirellm_tokenizer.sltok
model_store/checkpoints/sirellm-v1.lbckpt
model_store/checkpoints/sirellm-v1-progress.lbckpt
model_store/checkpoints/sirellm-v1-training.jsonl
vector_store/indexes/siresoft.slretr
```

See `GPU_RUN.md` for the full build/deploy flow.
