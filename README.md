<div align="center">

<img src=".github/assets/siresoft-ikon-banner.png" alt="SireSoft IKON — independent intelligence" width="100%" />

### SireSoft-IKON v1.0.0

**An independent language-model and retrieval-augmented AI platform, engineered from the ground up.**

[Overview](#overview) · [Architecture](#system-architecture) · [Workflows](#how-ikon-works) · [Getting started](#getting-started) · [Deployment](#production-deployment) · [Tests](#testing)

</div>

---

## Overview

**SireSoft-IKON** is SireSoft's modular AI application, combining a custom Transformer-based language model, a from-scratch tokenizer and training runtime, retrieval-augmented generation (RAG), a Django HTTP backend, and a React web interface.

Its model is trained and served using the project's own model/tokenizer and retrieval implementations, rather than delegating response generation to an external hosted LLM API. The architecture separates **model development**, **retrieval**, **inference**, and **web delivery** so each component can be tested and deployed independently.

| Layer | Implementation |
| :--- | :--- |
| Web application | React 19, TypeScript, Vite, CSS / Tailwind |
| HTTP backend | Django 5.2, Gunicorn (Linux), Nginx reverse proxy |
| Model | Custom Transformer, tokenizer, inference and training modules |
| Retrieval | Document preparation, chunking, embeddings, vector index and ranking |
| GPU training | Custom CUDA kernels; prebuilt Linux `sm_61` backend for the NVIDIA Quadro P5000 |
| Storage | Model checkpoints, tokenizer artifacts, retrieval indexes; optional Django database configuration |
| Quality | Unit, integration, HTTP contract, checkpoint/recovery and CUDA smoke tests |

> **Deployment status:** The source alone is not a trained model. Live inference requires a matching tokenizer, checkpoint, retrieval index, and — for custom CUDA use — its compiled Linux library and metadata.

## Highlights

- **From-scratch language model:** Custom neural-network/Transformer modules, tokenization, batching, training, sampling and checkpoint handling.
- **Retrieval-augmented responses:** Separate retrieval and generation components, with contextual answers and citation metadata when available.
- **Custom CUDA acceleration:** Native GPU kernels covering attention, embeddings, layer normalization, matrix operations, loss and optimizer operations.
- **Django web API:** Stable chat, generation, embedding, retrieval and health endpoints, with NDJSON chat responses.
- **React experience:** Chat interface, conversation history, appearance controls and export utilities.
- **Deployment flexibility:** Local development on Windows/Linux; Nginx and Gunicorn for a supervised Linux deployment.
- **Independent core:** The model/tokenizer/retrieval logic does not rely on third-party hosted LLM services.

## System architecture

The production request path follows SireSoft's standard stack: **Nginx → Django → application code → data/storage**. The browser UI is served by Nginx; API calls are proxied to Django.

```mermaid
flowchart LR
    User[Browser / React] --> Nginx[Nginx]
    Nginx -->|API requests| Django[Django / Gunicorn]
    Nginx -->|Static UI| User
    Django --> Core[IKON orchestration]
    Core --> Model[Custom tokenizer + Transformer]
    Core --> RAG[Retrieval / ranking]
    Model <--> Checkpoints[(Tokenizer + checkpoints)]
    RAG <--> Index[(Vector index)]
    Django -.-> Database[(Optional Django DB)]
    Core --> Django

    classDef blue fill:#edf4ff,stroke:#124bd9,color:#142b53;
    classDef storage fill:#f6f8fb,stroke:#8798b0,color:#243248;
    class User,Nginx,Django,Core,Model,RAG blue;
    class Checkpoints,Index,Database storage;
```

**Key boundaries:** Django manages HTTP and request validation; IKON's core handles generation and retrieval; model artifacts and vector indexes remain independent of Django's optional database.

## How IKON works

### 1. Data-to-model workflow

```mermaid
flowchart TD
    Data[DailyDialog · Dolly · Movie Corpus · TinyStories · OpenAssistant · SireSoft text]
    Data --> Prep[Preprocess + normalize datasets]
    Prep --> Tok[Train tokenizer]
    Tok --> Train[Train custom Transformer]
    Prep --> Chunks[Chunk + embed source text]
    Chunks --> Index[(Build retrieval index)]
    GPU[Precompiled CUDA backend / sm_61] -.->|GPU training on supported server| Train
    Train --> Checkpoint[(Save checkpoint + metrics)]
    Checkpoint --> Serve[IKON inference service]
    Index --> Serve
    classDef core fill:#edf4ff,stroke:#124bd9,color:#142b53;
    classDef artifact fill:#f6f8fb,stroke:#8293ac,color:#243248;
    class Data,Prep,Tok,Train,Chunks,Serve,GPU core;
    class Index,Checkpoint artifact;
```

The pipeline builds the tokenizer, trains the language model, saves checkpoints and training metrics, constructs the retrieval index, and verifies the required outputs.

### 2. Chat and RAG workflow

```mermaid
sequenceDiagram
    participant UI as React frontend
    participant API as Django API
    participant IKON as IKON core
    participant Search as Retrieval index
    participant LLM as Custom LLM
    UI->>API: POST /api/chat/stream
    API->>IKON: Validate and orchestrate request
    opt RAG enabled
        IKON->>Search: Retrieve relevant chunks
        Search-->>IKON: Context and source metadata
    end
    IKON->>LLM: Generate with prompt and optional context
    LLM-->>IKON: Generated text
    IKON-->>API: Response and optional citations
    API-->>UI: NDJSON meta / token / completion events
```

The frontend supports base-model and RAG modes. Chat events are delivered over a streaming HTTP response; the current implementation chunks the completed model reply rather than streaming GPU-generated tokens individually.

## Repository structure

```text
SireSoft-IKON-v1.0.0/
├── .github/workflows/       # CUDA build automation
├── .github/assets/          # README branding
├── configs/                 # Runtime and service configuration
├── deploy/                  # Gunicorn and Nginx examples
├── frontend/                # React / Vite application
│   ├── public/              # Frontend images and brand assets
│   └── src/                 # Components, state and API client
├── ikon_django/             # Django settings, URLs and API views
├── libs/                    # Model and data-processing implementation
│   ├── core/gpu/            # CUDA source and runtime backend
│   ├── neural/              # Layers and activations
│   ├── nlp/                 # Tokenizer and corpus utilities
│   ├── transformer/         # Transformer architecture
│   ├── training/            # Batching, optimizers, training
│   ├── inference/           # Model inference
│   ├── rag/                 # RAG orchestration support
│   └── retrieval/           # Embedding, search and ranking
├── model_store/             # Tokenizer/checkpoint code and artifact paths
├── runtime/                 # Bootstrapping, lifecycle and observability
├── services/                # Modular application services
├── tests/                   # Contracts and integration verification
├── tools/                   # Pipeline, CUDA, tokenizer and test CLIs
├── vector_store/            # Custom retrieval/index implementation
├── app.py                   # Launch Django + Vite in development
├── manage.py                # Django management commands
├── requirements.txt         # Python HTTP dependencies
└── run_pipeline.py          # One-command training pipeline
```

> Directories for local datasets, installed dependencies, build outputs and trained artifacts may be populated separately; they are not all included in source-only archives.

## Getting started

**Prerequisites:** Python 3.10+, Node.js and npm. An NVIDIA GPU is **not required** to develop the Django API or React interface.

### 1. Install dependencies

```bash
python -m venv .venv
# Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd frontend && npm ci && cd ..
```

### 2. Start the application

```powershell
# Windows PowerShell
$env:SIREIKON_DEBUG="1"
python app.py
```

```bash
# Linux development
export SIREIKON_DEBUG=1
python app.py
```

| Service | Development address |
| :--- | :--- |
| React web app | `http://localhost:5173` |
| Django API | `http://127.0.0.1:8000` |
| Health check | `http://127.0.0.1:8000/api/health` |

Alternatively, start Django with `python manage.py runserver 127.0.0.1:8000` and Vite with `cd frontend && npm run dev` in separate terminals.

### 3. Validate availability

```bash
python manage.py check
python tests/test_django_http.py
```

```bash
curl http://127.0.0.1:8000/api/health
```

A healthy HTTP response does **not** necessarily mean the trained model is loaded: check `model_ready` and `model_error` before testing real chat replies.

## One-command full application (React + Django + IKON model)

`app.py` now manages **both** services, keeping Django on a private local
listener and proxying `/api` through Vite. It loads the existing trained
checkpoint and retrieval index; it **never runs training**. On Linux it runs
one Gunicorn worker to avoid duplicate GPU/model allocations, and it shuts
down both processes on Ctrl+C or a disconnected SSH session.

```powershell
# Windows laptop (CPU fallback when no Linux CUDA is available)
python -m pip install -r requirements.txt
python app.py --device auto
```

```bash
# SireSoft Linux GPU server (only after the NVIDIA driver is healthy)
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py --gpu --require-model --api-port 8010 \
  --web-host 0.0.0.0 --public-host 10.0.2.22
```

**Open the single printed frontend link** (over the company VPN). For the
loopback-only secure default, use `ssh -N -L 5174:127.0.0.1:5173
siresoft@10.0.2.22` from Windows and browse `http://localhost:5174`.
General chat / RAG can be switched in the **Settings** panel. The launcher
waits for trained model readiness before printing the frontend link when the
artifacts exist.

- `--gpu` is strict: **no silent CPU fallback**. A failing `nvidia-smi`
  indicates a driver/host issue; the launcher cannot repair the OS driver.
- On a machine without a GPU, `--device auto` selects CPU with an explicit
  warning. `--check` reports artifact/GPU availability without launching.
- The current server checkpoint has a **64-token context window and ~58K
  parameters**. Short cited reference excerpts permit smoke-testing RAG, but
  responses will be short and may be incoherent; longer-context grounded
  answers require a more capable trained checkpoint.
- **Do not overwrite** production `.lbckpt`, `.sltok`, `.slretr`, or the Linux
  `libsireikon_cuda.so` when transferring this source archive.

### Verify a running app end to end

```bash
python tools/run_tests.py --quick --require-django
python tools/run_tests.py --require-django
# In a second terminal while app.py is running:
python tools/test_live_app.py --web-url http://127.0.0.1:5173 --require-gpu
```

`tools/test_live_app.py` exercises the real UI HTTP response, Django readiness,
general chat, RAG chat, and CUDA activity through the frontend API proxy. It
must run on the GPU server for a strict CUDA PASS; ordinary source tests can
run on Windows or Linux without the trained artifacts.

## HTTP API

| Method | Route | Purpose |
| :---: | :--- | :--- |
| GET | `/api/health` | Frontend health and model readiness |
| POST | `/api/chat/stream` | Frontend chat response (NDJSON) |
| GET | `/v1/health` | IKON runtime health |
| POST | `/v1/chat` | RAG-assisted model response |
| POST | `/v1/generate` | Base model generation |
| POST | `/v1/retrieve` | Retrieval index query |
| POST | `/v1/embed` | Text embedding |

The API is served by Django. Some model endpoints return **503** until their trained artifacts are available; that is separate from an HTTP-server startup problem.

## Training and CUDA

Production training defaults to **strict CUDA**: it requires the precompiled backend to work, rather than silently falling back to CPU.

```bash
# Build native CUDA source on a Linux/WSL development machine with CUDA 12.x:
python tools/build_cuda_backend.py --arch sm_61 --required

# On a server with the prebuilt Linux library and Quadro P5000:
python tools/cuda_status.py --arch sm_61
python tools/test_gpu_training.py --arch sm_61 --require-cuda
python run_pipeline.py
```

For development on a machine without NVIDIA hardware, run `python run_pipeline.py --device cpu` **only when the necessary local datasets are available**.

The server-side CUDA library and `libsireikon_cuda.build.json` must match the source; `nvcc` is needed for compilation only, not for loading a compatible prebuilt backend. See [GPU_RUN.md](GPU_RUN.md) and [REAL_RUN.md](REAL_RUN.md).


### One-command training and finalized model bundle

`python run_pipeline.py --profile p5000-512 --device cuda` runs the full
preprocessing, tokenizer, LLM training and SireSoft RAG-index pipeline. On
success, it verifies the trained weights/tokenizer/index **together** using the
real runtime and writes `model_store/manifests/ikon-p5000-512-bundle.json`
with SHA-256 checksums and paths. The serving model is one **complete**
`*.lbckpt` file; step and epoch checkpoints are whole-model recovery snapshots,
**not shards that require merging**. Original legacy artifacts are preserved.

`--start-app` optionally launches the React + Django frontend after the
verified model is ready. For the other training profiles and details, see
[MODEL_TRAINING.md](MODEL_TRAINING.md). Strict CUDA still requires a working
NVIDIA driver and a matching precompiled backend.

## Testing

```bash
python manage.py check
python tools/run_tests.py --quick --require-django
python tools/run_tests.py --require-django
```

The test runner covers component, frontend/API contract, Django HTTP, checkpoint and recovery, retrieval, and CUDA backend contract checks. The **strict GPU smoke test** must run on an NVIDIA GPU machine; it cannot be proven on a GPU-less laptop.

## Production deployment

```text
Client / VPN
   ↓
Nginx  (static React build + API reverse proxy)
   ↓
Django / Gunicorn  (one worker for current in-process model cache)
   ↓
IKON LLM + RAG  →  model artifacts / vector store
```

On Linux, install requirements, configure production `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS`, start Django with the configured Gunicorn entry point, and serve `frontend/dist/` behind Nginx. **Keep trained artifacts and the precompiled CUDA library when updating source code.**

Deployment examples are under [`deploy/`](deploy/); detailed guidance is in [DJANGO_DEPLOYMENT.md](DJANGO_DEPLOYMENT.md).

## License and ownership

**Proprietary software — © 2026 SireSoft. All rights reserved.**

This repository is intended for SireSoft and authorized collaborators. No permission to copy, modify, redistribute, or commercially use the software is granted by this README. Refer to SireSoft's applicable written licensing and ownership terms.

<div align="center">

---

<img src=".github/assets/siresoft-logo.jpeg" alt="SireSoft — Leader in Innovation" width="210" />

<sub>Engineered for SireSoft · SireSoft-IKON v1.0.0</sub>

</div>


## Larger-context training: Quadro P5000

The original checkpoint is a **58,240-parameter / 64-token** model. It is a valid
smoke-test artifact, **not** a capable general assistant. Changing the serving
limit cannot enlarge trained weights or guarantee coherent answers. This project
provides opt-in, isolated training profiles:

| Profile | Context | Width | Layers / heads | Vocabulary | Status |
|---|---:|---:|---:|---:|---|
| `legacy` | 64 | 32 | 2 / 4 | 512 | Existing checkpoint |
| `p5000-512` | 512 | 128 | 4 / 4 | 4096 | Train and benchmark |
| `p5000-1024` | 1024 | 192 | 4 / 6 | 4096 | Experimental; benchmark before full training |

Both P5000 profiles are **custom from-scratch models**, not pretrained models.
They require substantial, quality-controlled training data, hardware testing and
real conversational evaluations before they can answer broad questions reliably.
The Quadro P5000's nominal 16 GB VRAM does not guarantee these Python/CUDA
configurations fit at acceptable speed. Driver health (`nvidia-smi`) and smoke
tests must succeed first. Existing artifacts are never overwritten by profiles.

```bash
# Inspect resolved paths/parameters without training or touching the GPU:
python tools/run_pipeline.py --profile p5000-512 --dry-run

# Only after the CUDA driver is healthy and data are present:
python tools/run_pipeline.py --profile p5000-512 --device cuda --skip-preprocessing --fresh

# Activate the newly generated checkpoint, tokenizer and matching RAG index:
python app.py --model-profile p5000-512 --gpu --require-model \
  --api-port 8010 --web-host 0.0.0.0 --public-host 10.0.2.22

# Verify both general chat and RAG through the frontend proxy:
python tools/test_live_app.py --web-url http://127.0.0.1:5173 --require-gpu
```

Set `--records-per-dataset 0` (all available canonical records) only after
benchmarking a small run; full-dataset training may take substantial time.
For a different tokenizer you **must** rebuild the retrieval index with it;
profiles do this automatically. Do not rename old checkpoints to a new profile.
Read [MODEL_TRAINING.md](MODEL_TRAINING.md) for a safe rollout guide.
