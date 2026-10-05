# SireSoft-IKON Real Execution

## Recommended full run

After activating the project virtual environment, run:

```bash
python run_pipeline.py
```

This is now the complete production-style artifact pipeline. It uses GPU-preferred `auto` device selection by default. A usable custom CUDA backend is selected automatically; if the backend is unavailable and cannot be built, the pipeline continues on CPU instead of terminating on an `nvcc` precheck. Use `python run_pipeline.py --device cuda` for strict GPU-only execution.

### Useful variants

CPU-only functional run:

```bash
python run_pipeline.py --device cpu
```

Continue an interrupted run automatically:

```bash
python run_pipeline.py
```

The pipeline detects `model_store/checkpoints/sirellm-v1-progress.lbckpt` and resumes the saved epoch/batch position.

Force a fresh run:

```bash
python run_pipeline.py --fresh
```

Run everything and start the FastAPI/React application after artifacts are ready:

```bash
python run_pipeline.py --start-app
```

### GPU readiness test

```bash
python tools/test_gpu_training.py --build-if-needed --arch sm_61
```

Strict GPU validation:

```bash
python tools/test_gpu_training.py --build-if-needed --arch sm_61 --require-cuda
```

### CPU-only checkpoint test

```bash
python tools/test_training_recovery.py
```

### Output artifacts

```text
model_store/manifests/sirellm_tokenizer.sltok
model_store/checkpoints/sirellm-v1.lbckpt
model_store/checkpoints/sirellm-v1-progress.lbckpt
model_store/checkpoints/sirellm-v1-training.jsonl
vector_store/indexes/siresoft.slretr
```
