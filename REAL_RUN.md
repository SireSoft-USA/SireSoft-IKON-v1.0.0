# SireLLM — Real Execution Pipeline

These are production runner scripts, not tests.

Copy the contents of this ZIP into the root of your existing SireLLM project.
It adds files inside the existing `tools/` folder and does not replace your
model/service implementation.

Run every command from the project root.

## 1. Full real preprocessing

```powershell
python tools/preprocess_all.py
```

Outputs:

```text
datasets/canonical/dailydialog.jsonl
datasets/canonical/dolly.jsonl
datasets/canonical/movie-corpus.jsonl
datasets/canonical/siresoft.jsonl
datasets/canonical/tinystories.jsonl
datasets/canonical/openassistant.jsonl
```

To preprocess one source only:

```powershell
python tools/preprocess_all.py --datasets siresoft
```

## 2. Train the real tokenizer

Recommended first real run:

```powershell
python tools/train_tokenizer.py --records-per-dataset 2000 --vocab-size 512 --min-frequency 2
```

`--records-per-dataset 0` means use all canonical records.

Output:

```text
model_store/manifests/sirellm_tokenizer.sltok
```

## 3. Train the real language model

Recommended first real CPU run:

```powershell
python tools/train_model.py --records-per-dataset 250 --epochs 1 --batch-size 4 --sequence-length 64 --d-model 32 --layers 2 --heads 4 --d-ff 128 --learning-rate 0.001
```

This performs actual forward passes, backpropagation, AdamW updates,
learning-rate scheduling, validation, epoch tracking, and checkpoint writes.

Outputs:

```text
model_store/checkpoints/sirellm-v1-epoch-001.lbckpt
model_store/checkpoints/sirellm-v1.lbckpt
```

Resume from the saved checkpoint:

```powershell
python tools/train_model.py --records-per-dataset 250 --epochs 1 --batch-size 4 --sequence-length 64 --d-model 32 --layers 2 --heads 4 --d-ff 128 --learning-rate 0.001 --resume model_store/checkpoints/sirellm-v1.lbckpt
```

For all canonical records later:

```powershell
python tools/train_model.py --records-per-dataset 0 --epochs 1 --batch-size 4 --sequence-length 64 --d-model 32 --layers 2 --heads 4 --d-ff 128
```

## 4. Generate with the trained model

```powershell
python tools/generate_text.py "SireSoft builds" --max-new-tokens 32
```

This loads the real `.lbckpt` checkpoint and performs autoregressive
generation with the trained weights.

## 5. Build the SireSoft RAG index

```powershell
python tools/build_retrieval.py
```

Output:

```text
vector_store/indexes/siresoft.slretr
```

## 6. Train a RAG-capable context window

The compact RAG prompt plus retrieved context needs a larger context window
than the quick 64-token training run.

```powershell
python tools/train_model.py --records-per-dataset 250 --epochs 1 --batch-size 2 --sequence-length 256 --d-model 32 --layers 2 --heads 4 --d-ff 128 --learning-rate 0.001
```

The entire tensor/autograd/attention stack is handwritten Python, so this can
be slow on CPU. It is still real training, not a mock.

Then start real RAG chat:

```powershell
python tools/chat_rag.py
```

Or ask one question:

```powershell
python tools/chat_rag.py "What services does SireSoft provide?" --max-new-tokens 16
```

## 7. One-command artifact build

```powershell
python tools/run_real_pipeline.py --records-per-dataset 250 --tokenizer-records-per-dataset 2000 --epochs 1 --batch-size 4 --sequence-length 64
```

If canonical datasets already exist:

```powershell
python tools/run_real_pipeline.py --skip-preprocessing --records-per-dataset 250 --epochs 1
```

## Scaling

Start with a bounded real-data run first. Once it produces a checkpoint and
loss is moving, increase:

1. `--records-per-dataset`
2. `--epochs`
3. context length
4. model width/layers

Do not begin with every TinyStories/OpenAssistant record and a large model at
once. The model stack intentionally does not use PyTorch, TensorFlow, NumPy,
CUDA, external LLM APIs, or pretrained weights.
