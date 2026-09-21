from pathlib import Path
import os


ROOT = Path(__file__).resolve().parents[1]


def enter_project_root():
    os.chdir(ROOT)
    return ROOT


def _exec_file(namespace, relative_path):
    path = ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(
            "Required SireLLM source file is missing: "
            + str(relative_path)
        )

    source = path.read_text(encoding="utf-8")
    exec(
        compile(
            source,
            str(relative_path),
            "exec",
        ),
        namespace,
    )


def _exec_group(namespace, base, filenames):
    for filename in filenames:
        _exec_file(
            namespace,
            base + filename,
        )


def _base_namespace():
    return {
        "__builtins__": __builtins__,
    }


def load_preprocessing_namespace():
    enter_project_root()
    ns = _base_namespace()

    groups = [
        (
            "libs/core/serialization/",
            [
                "binary_writer.py",
                "binary_reader.py",
                "checksum.py",
            ],
        ),
        (
            "libs/data/parsers/",
            [
                "json_parser.py",
                "jsonl_parser.py",
                "text_parser.py",
            ],
        ),
        (
            "libs/data/schema/",
            [
                "message.py",
                "conversation.py",
                "canonical_record.py",
                "validator.py",
            ],
        ),
        (
            "libs/data/adapters/",
            [
                "dailydialog_adapter.py",
                "dolly_adapter.py",
                "movie_corpus_adapter.py",
                "siresoft_adapter.py",
                "tinystories_adapter.py",
                "openassistant_adapter.py",
            ],
        ),
        (
            "libs/data/streaming/",
            [
                "writer.py",
            ],
        ),
        (
            "libs/nlp/normalization/",
            [
                "whitespace.py",
                "punctuation.py",
                "unicode_rules.py",
                "normalizer.py",
            ],
        ),
        (
            "libs/nlp/corpus/",
            [
                "document.py",
            ],
        ),
        (
            "libs/protocol/",
            [
                "error.py",
                "message.py",
                "request.py",
                "response.py",
                "validator.py",
                "codec.py",
            ],
        ),
        (
            "services/preprocessing_service/",
            [
                "dataset_loader.py",
                "canonical_normalizer.py",
                "canonical_writer.py",
                "pipeline.py",
                "service.py",
            ],
        ),
    ]

    for base, filenames in groups:
        _exec_group(ns, base, filenames)

    return ns


def load_tokenizer_namespace():
    enter_project_root()
    ns = _base_namespace()

    groups = [
        (
            "libs/core/serialization/",
            [
                "binary_writer.py",
                "binary_reader.py",
                "checksum.py",
            ],
        ),
        (
            "libs/nlp/tokenizer/",
            [
                "special_tokens.py",
                "byte_encoder.py",
                "pair_counter.py",
                "vocabulary.py",
                "bpe_trainer.py",
                "bpe_tokenizer.py",
            ],
        ),
        (
            "libs/protocol/",
            [
                "error.py",
                "message.py",
                "request.py",
                "response.py",
                "validator.py",
                "codec.py",
            ],
        ),
        (
            "services/tokenizer_service/",
            [
                "artifact.py",
                "state_codec.py",
                "manager.py",
                "service.py",
            ],
        ),
    ]

    for base, filenames in groups:
        _exec_group(ns, base, filenames)

    return ns


def load_training_namespace():
    enter_project_root()
    ns = _base_namespace()

    groups = [
        (
            "libs/core/math/",
            [
                "scalar.py",
                "random.py",
                "tensor.py",
            ],
        ),
        (
            "libs/core/autograd/",
            [
                "operation.py",
                "value.py",
                "graph.py",
                "backward.py",
            ],
        ),
        (
            "libs/core/serialization/",
            [
                "binary_writer.py",
                "binary_reader.py",
                "checksum.py",
            ],
        ),
        (
            "libs/neural/",
            [
                "parameter.py",
                "layer.py",
                "initializers.py",
                "activations.py",
                "linear.py",
                "embedding.py",
                "dropout.py",
                "layer_norm.py",
            ],
        ),
        (
            "libs/transformer/",
            [
                "positional_encoding.py",
                "rotary_embedding.py",
                "causal_mask.py",
                "attention.py",
                "multi_head_attention.py",
                "feed_forward.py",
                "transformer_block.py",
                "decoder.py",
                "language_model.py",
            ],
        ),
        (
            "libs/training/losses/",
            [
                "softmax.py",
                "cross_entropy.py",
            ],
        ),
        (
            "libs/training/optimizers/",
            [
                "sgd.py",
                "adamw.py",
            ],
        ),
        (
            "libs/training/schedules/",
            [
                "constant.py",
                "warmup.py",
                "cosine.py",
            ],
        ),
        (
            "libs/training/batching/",
            [
                "padding.py",
                "sequence_packer.py",
                "batch_builder.py",
            ],
        ),
        (
            "libs/training/",
            [
                "gradient_clipping.py",
                "trainer.py",
                "evaluator.py",
                "checkpoint.py",
            ],
        ),
        (
            "libs/protocol/",
            [
                "error.py",
                "message.py",
                "request.py",
                "response.py",
                "validator.py",
                "codec.py",
            ],
        ),
        (
            "services/training_service/",
            [
                "job.py",
                "factory.py",
                "manager.py",
                "service.py",
            ],
        ),
    ]

    for base, filenames in groups:
        _exec_group(ns, base, filenames)

    return ns


def load_retrieval_namespace():
    enter_project_root()
    ns = _base_namespace()

    groups = [
        (
            "libs/core/math/",
            [
                "scalar.py",
            ],
        ),
        (
            "libs/core/serialization/",
            [
                "binary_writer.py",
                "binary_reader.py",
                "checksum.py",
            ],
        ),
        (
            "libs/nlp/tokenizer/",
            [
                "special_tokens.py",
                "byte_encoder.py",
                "pair_counter.py",
                "vocabulary.py",
                "bpe_trainer.py",
                "bpe_tokenizer.py",
            ],
        ),
        (
            "services/tokenizer_service/",
            [
                "artifact.py",
                "state_codec.py",
                "manager.py",
                "service.py",
            ],
        ),
        (
            "libs/nlp/corpus/",
            [
                "document.py",
            ],
        ),
        (
            "libs/retrieval/chunking/",
            [
                "chunk.py",
                "boundaries.py",
                "document_chunker.py",
            ],
        ),
        (
            "libs/retrieval/embedding/",
            [
                "hash_features.py",
                "idf.py",
                "embedder.py",
            ],
        ),
        (
            "libs/retrieval/similarity/",
            [
                "dot_product.py",
                "cosine.py",
                "distance.py",
                "batch_similarity.py",
                "scorer.py",
            ],
        ),
        (
            "libs/retrieval/index/",
            [
                "entry.py",
                "flat_index.py",
                "persistence.py",
            ],
        ),
        (
            "libs/retrieval/ranking/",
            [
                "result.py",
                "dedup.py",
                "reranker.py",
                "mmr.py",
                "pipeline.py",
            ],
        ),
        (
            "services/retrieval_service/",
            [
                "document_store.py",
                "result.py",
                "persistence.py",
                "manager.py",
            ],
        ),
    ]

    for base, filenames in groups:
        _exec_group(ns, base, filenames)

    return ns


def load_inference_namespace():
    enter_project_root()
    ns = _base_namespace()

    groups = [
        (
            "libs/core/math/",
            [
                "scalar.py",
                "random.py",
                "tensor.py",
            ],
        ),
        (
            "libs/core/autograd/",
            [
                "operation.py",
                "value.py",
                "graph.py",
                "backward.py",
            ],
        ),
        (
            "libs/core/serialization/",
            [
                "binary_writer.py",
                "binary_reader.py",
                "checksum.py",
            ],
        ),
        (
            "libs/nlp/tokenizer/",
            [
                "special_tokens.py",
                "byte_encoder.py",
                "pair_counter.py",
                "vocabulary.py",
                "bpe_trainer.py",
                "bpe_tokenizer.py",
            ],
        ),
        (
            "services/tokenizer_service/",
            [
                "artifact.py",
                "state_codec.py",
                "manager.py",
                "service.py",
            ],
        ),
        (
            "libs/neural/",
            [
                "parameter.py",
                "layer.py",
                "initializers.py",
                "activations.py",
                "linear.py",
                "embedding.py",
                "dropout.py",
                "layer_norm.py",
            ],
        ),
        (
            "libs/transformer/",
            [
                "positional_encoding.py",
                "rotary_embedding.py",
                "causal_mask.py",
                "attention.py",
                "multi_head_attention.py",
                "feed_forward.py",
                "transformer_block.py",
                "decoder.py",
                "language_model.py",
            ],
        ),
        (
            "libs/training/",
            [
                "checkpoint.py",
            ],
        ),
        (
            "libs/inference/",
            [
                "logits_processor.py",
                "sampler.py",
                "generation_state.py",
                "kv_cache.py",
                "generator.py",
            ],
        ),
        (
            "services/model_registry/",
            [
                "model_version.py",
                "checkpoint_inspector.py",
                "registry.py",
            ],
        ),
        (
            "services/inference_service/",
            [
                "loader.py",
                "result.py",
                "runtime.py",
            ],
        ),
    ]

    for base, filenames in groups:
        _exec_group(ns, base, filenames)

    return ns


def load_rag_namespace():
    enter_project_root()
    ns = _base_namespace()

    groups = [
        (
            "libs/core/math/",
            [
                "scalar.py",
                "random.py",
                "tensor.py",
            ],
        ),
        (
            "libs/core/autograd/",
            [
                "operation.py",
                "value.py",
                "graph.py",
                "backward.py",
            ],
        ),
        (
            "libs/core/serialization/",
            [
                "binary_writer.py",
                "binary_reader.py",
                "checksum.py",
            ],
        ),
        (
            "libs/nlp/tokenizer/",
            [
                "special_tokens.py",
                "byte_encoder.py",
                "pair_counter.py",
                "vocabulary.py",
                "bpe_trainer.py",
                "bpe_tokenizer.py",
            ],
        ),
        (
            "services/tokenizer_service/",
            [
                "artifact.py",
                "state_codec.py",
                "manager.py",
                "service.py",
            ],
        ),
        (
            "libs/nlp/corpus/",
            [
                "document.py",
            ],
        ),
        (
            "libs/neural/",
            [
                "parameter.py",
                "layer.py",
                "initializers.py",
                "activations.py",
                "linear.py",
                "embedding.py",
                "dropout.py",
                "layer_norm.py",
            ],
        ),
        (
            "libs/transformer/",
            [
                "positional_encoding.py",
                "rotary_embedding.py",
                "causal_mask.py",
                "attention.py",
                "multi_head_attention.py",
                "feed_forward.py",
                "transformer_block.py",
                "decoder.py",
                "language_model.py",
            ],
        ),
        (
            "libs/training/",
            [
                "checkpoint.py",
            ],
        ),
        (
            "libs/inference/",
            [
                "logits_processor.py",
                "sampler.py",
                "generation_state.py",
                "kv_cache.py",
                "generator.py",
            ],
        ),
        (
            "libs/retrieval/chunking/",
            [
                "chunk.py",
                "boundaries.py",
                "document_chunker.py",
            ],
        ),
        (
            "libs/retrieval/embedding/",
            [
                "hash_features.py",
                "idf.py",
                "embedder.py",
            ],
        ),
        (
            "libs/retrieval/similarity/",
            [
                "dot_product.py",
                "cosine.py",
                "distance.py",
                "batch_similarity.py",
                "scorer.py",
            ],
        ),
        (
            "libs/retrieval/index/",
            [
                "entry.py",
                "flat_index.py",
                "persistence.py",
            ],
        ),
        (
            "libs/retrieval/ranking/",
            [
                "result.py",
                "dedup.py",
                "reranker.py",
                "mmr.py",
                "pipeline.py",
            ],
        ),
        (
            "libs/rag/",
            [
                "citation.py",
                "context_builder.py",
                "prompt_builder.py",
                "retriever.py",
                "result.py",
            ],
        ),
        (
            "libs/safety/",
            [
                "decision.py",
                "patterns.py",
                "input_guard.py",
                "context_guard.py",
                "output_guard.py",
                "engine.py",
            ],
        ),
        (
            "services/model_registry/",
            [
                "model_version.py",
                "checkpoint_inspector.py",
                "registry.py",
            ],
        ),
        (
            "services/inference_service/",
            [
                "loader.py",
                "result.py",
                "runtime.py",
            ],
        ),
        (
            "services/retrieval_service/",
            [
                "document_store.py",
                "result.py",
                "persistence.py",
                "manager.py",
            ],
        ),
        (
            "services/rag_service/",
            [
                "retrieval_bridge.py",
                "safety_view.py",
                "result.py",
                "orchestrator.py",
                "service.py",
            ],
        ),
    ]

    for base, filenames in groups:
        _exec_group(ns, base, filenames)

    return ns
