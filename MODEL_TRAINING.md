# IKON model improvement and GPU training

## Why the old checkpoint cannot answer naturally

The existing real checkpoint is ~58K parameters, 512 vocabulary entries,
with 64 maximum sequence tokens. The output `s wort to mand` is a genuine
trained-model sample, but poor answer quality is expected at that scale.
A larger inference context cannot be retrofitted into this checkpoint simply
by editing `max_seq_len`: training and a compatible new checkpoint are needed.

## Profiles and artifact isolation

Use `python tools/run_pipeline.py --profile p5000-512 --dry-run` to inspect
configuration. Opt in to `p5000-1024` only after benchmarking memory and speed.
Each profile has its own tokenizer, checkpoint/progress/log and retrieval index.
The original artifacts remain untouched. Use `--profile legacy` for them.

The P5000 profiles are stepping stones, **not** equivalent to state-of-the-art
chat assistants; no from-scratch small model can answer every general question.
Use balanced conversational text (DailyDialog, Dolly, OpenAssistant, etc.)
for general chat, and curated SireSoft knowledge for RAG. Verify license and
quality of all datasets. More training helps only when the model/data/optimization
are adequate; evaluate held-out prompts before any production release.

## Safe GPU path

1. Verify `nvidia-smi` and `python tools/test_gpu_training.py --arch sm_61 --require-cuda`. If the driver fails, stop; do not reinstall it without server approval.
2. `python tools/run_pipeline.py --profile p5000-512 --dry-run`
3. `python tools/run_pipeline.py --profile p5000-512 --device cuda --skip-preprocessing --fresh` (new full training run, only with existing canonical datasets).
4. Check `*.lbckpt`, `*.sltok`, and `*.slretr` for this profile.
5. Run `python app.py --model-profile p5000-512 --gpu --require-model --api-port 8010 --web-host 0.0.0.0 --public-host 10.0.2.22`.
6. In a separate terminal, run `python tools/test_live_app.py --web-url http://127.0.0.1:5173 --require-gpu`.

Use a small dataset cap such as `--records-per-dataset 20 --epochs 1` first
to benchmark GPU memory, compute, checkpointing and generated output; this does
not create a well-trained conversational model. Then plan full training.
When switching from a small benchmark corpus to a larger corpus, use `--fresh`
to avoid resuming from an incompatible data schedule. Use `--skip-tokenizer`
only when intentionally reusing the exact same tokenizer. Never overwrite or
resume the original legacy checkpoint with a new architecture.

## Quality acceptance checks

- General chat: held-out multi-turn conversations; answer relevance, repetitions, hallucinations, instruction adherence.
- SireSoft RAG: independently verified company questions with source-supported answers, correct citations and explicit uncertainty for unknown questions.
- Isolation: general chat works without retrieval; RAG uses matching tokenizer and a newly built company index.
- Latency: benchmark generated tokens/s and peak VRAM on the actual server.
- Regression: `python tools/run_tests.py --require-django` and the live frontend integration check.

## Evaluate responses, not just HTTP 200

```bash
python tools/test_live_app.py --web-url http://127.0.0.1:5173 --require-gpu --min-context 512
python tools/evaluate_ikon.py --web-url http://127.0.0.1:5173
```

Review `model-quality-evaluation.json` manually. It deliberately reports
answers and citations without claiming a passing score for incoherent text.

## One-command complete build and saved model bundle

Run the repository entry point. It invokes the actual orchestrator at
`tools/run_pipeline.py` and completes **GPU preflight → dataset reconstruction →
preprocessing → tokenizer training → LLM training → RAG indexing → verification
→ saved bundle manifest**. No separate "merge trained pieces" step is necessary.

```bash
# First verify profile and output locations without training.
python run_pipeline.py --profile p5000-512 --dry-run

# Full GPU build. Does NOT overwrite the legacy 64-token model.
python run_pipeline.py --profile p5000-512 --device cuda

# Optional: launch the combined frontend + Django app after a verified build.
python run_pipeline.py --profile p5000-512 --device cuda --start-app
```

The **final serving checkpoint** is a complete snapshot of all trained weights:

```text
model_store/checkpoints/sirellm-p5000-512.lbckpt          # complete model
model_store/manifests/sirellm_tokenizer_p5000_512.sltok   # trained tokenizer
vector_store/indexes/siresoft-p5000-512.slretr            # saved RAG index
model_store/manifests/ikon-p5000-512-bundle.json           # validated bundle manifest
```

Files named `*-step-N.lbckpt` and `*-epoch-N.lbckpt` are **full model snapshots**
for progress tracking/recovery, not individual weight shards. They must **not**
be concatenated, averaged or merged. Training text is split into batches/windows
for optimization; those are not separately saved model components either.

The finalization step reloads the checkpoint, tokenizer and RAG index using the
real runtime (on CPU solely to validate deserialization and compatibility),
checks the checkpoint context window and index entries, then atomically saves a
JSON manifest containing paths, file sizes and SHA-256 digests. CUDA execution
is validated by a separate strict smoke test at the beginning of GPU training.
If any required file is missing or incompatible, the pipeline fails instead of
claiming successful completion.

Use `--fresh` only when deliberately starting a new model for the selected
profile. Automatic resume uses its corresponding `*-progress.lbckpt` snapshot.
The default profile is `p5000-512`; use `--profile legacy` explicitly to work
with the old 64-token architecture. GPU startup still requires a functioning
NVIDIA driver; source code cannot repair a driver failure.
