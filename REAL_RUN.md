# SireSoft-IKON Real Execution

## Recommended full run

After activating the project virtual environment, run:

```bash
python tools/run_real_pipeline.py
```

This is now the complete production-style artifact pipeline. It targets CUDA by default and handles custom CUDA verification, TinyStories reconstruction, preprocessing, tokenizer training, real model training, live progress visualization, periodic resumable checkpoints, retrieval index construction and final artifact verification.

### Useful variants

CPU-only functional run:

```bash
python tools/run_real_pipeline.py --device cpu
```

Continue an interrupted run automatically:

```bash
python tools/run_real_pipeline.py
```

The pipeline detects `model_store/checkpoints/sirellm-v1-progress.lbckpt` and resumes the saved epoch/batch position.

Force a fresh run:

```bash
python tools/run_real_pipeline.py --fresh
```

Run everything and start the FastAPI/React application after artifacts are ready:

```bash
python tools/run_real_pipeline.py --start-app
```

### GPU readiness test

```bash
python tools/test_gpu_training.py --build-if-needed --arch sm_61
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
