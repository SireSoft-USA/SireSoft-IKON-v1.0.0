# SireSoft-IKON CUDA Build and GPU Deployment

The training server does **not** compile CUDA code. It only loads the precompiled
Linux shared library:

```text
libs/core/gpu/libsireikon_cuda.so
```

For the SireSoft Quadro P5000 deployment target, the backend is compiled for
Pascal compute capability `sm_61` with CUDA Toolkit 12.x.

## Recommended: build automatically in GitHub

Push the source to `main`:

```bash
git add .
git commit -m "fix: prebuild CUDA backend for GPU-only deployment"
git push origin main
```

The included workflow:

```text
.github/workflows/build-cuda-backend.yml
```

runs on GitHub's Linux runner, uses CUDA 12.4.1 `nvcc`, compiles the `sm_61`
backend, validates the exported CUDA API, writes build metadata, uploads the
binary as an Actions artifact, and commits these two files back to `main`:

```text
libs/core/gpu/libsireikon_cuda.so
libs/core/gpu/libsireikon_cuda.build.json
```

No physical NVIDIA GPU is required to compile the backend.

After the workflow is green, the repository will contain a second commit named
approximately:

```text
build: refresh precompiled CUDA backend (sm_61)
```

## Optional: compile manually on a development machine

Manual compilation is only for Linux x86_64 (including WSL) with CUDA Toolkit
12.x `nvcc` installed. A GPU is not required for compilation.

```bash
python tools/build_cuda_backend.py --arch sm_61 --required
```

The command produces both the `.so` and matching source-hash metadata. Commit
both:

```bash
git add -f libs/core/gpu/libsireikon_cuda.so \
  libs/core/gpu/libsireikon_cuda.build.json
git commit -m "build: refresh precompiled CUDA backend (sm_61)"
git push origin main
```

Do not build the deployment `.so` directly in native Windows. The server needs a
Linux x86_64 shared object, not a Windows DLL.

## GPU server: no nvcc, no CUDA Toolkit build step

On the server:

```bash
cd /home/siresoft/independant_chatbot
git pull origin main
source .venv/bin/activate
python tools/cuda_status.py --arch sm_61
python tools/test_gpu_training.py --arch sm_61 --require-cuda
python run_pipeline.py
```

`python run_pipeline.py` defaults to strict `cuda`. If the precompiled backend is
missing, stale, cannot load, or no CUDA GPU is usable, the pipeline stops before
full training. It does not silently fall back to CPU.

For a laptop without an NVIDIA GPU, explicitly use CPU mode:

```bash
python run_pipeline.py --device cpu
```

## What is checked before training

The runtime preflight verifies that:

- `libsireikon_cuda.so` exists;
- `libsireikon_cuda.build.json` exists;
- the metadata source SHA-256 matches the current `sireikon_cuda.cu`;
- the binary targets `sm_61` / Linux x86_64;
- the NVIDIA GPU can be activated through the native backend; and
- a miniature real training step exercises matmul, embedding, attention,
  LayerNorm, cross-entropy, and AdamW CUDA kernels.

The server never invokes `nvcc`.
