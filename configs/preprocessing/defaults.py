def default_preprocessing_config():
    return PreprocessingConfig(
        datasets=[
            DatasetPreprocessingConfig(
                "dailydialog",
                sources={
                    "dialogues": (
                        "datasets/raw/dailydialog/dialogues.json"
                    ),
                    "ontology": (
                        "datasets/raw/dailydialog/ontology.json"
                    ),
                },
                output_path=(
                    "datasets/canonical/dailydialog.jsonl"
                ),
            ),
            DatasetPreprocessingConfig(
                "dolly",
                sources={
                    "instructions": (
                        "datasets/raw/dolly/databricks-dolly-15k.jsonl"
                    ),
                },
                output_path=(
                    "datasets/canonical/dolly.jsonl"
                ),
            ),
            DatasetPreprocessingConfig(
                "movie-corpus",
                sources={
                    "conversations": (
                        "datasets/raw/movie-corpus/conversations.json"
                    ),
                    "corpus": (
                        "datasets/raw/movie-corpus/corpus.json"
                    ),
                    "index": (
                        "datasets/raw/movie-corpus/index.json"
                    ),
                    "speakers": (
                        "datasets/raw/movie-corpus/speakers.json"
                    ),
                    "utterances": (
                        "datasets/raw/movie-corpus/utterances.json"
                    ),
                },
                output_path=(
                    "datasets/canonical/movie-corpus.jsonl"
                ),
            ),
            DatasetPreprocessingConfig(
                "siresoft",
                sources={
                    "knowledge": (
                        "datasets/raw/siresoft/siresoft.txt"
                    ),
                },
                output_path=(
                    "datasets/canonical/siresoft.jsonl"
                ),
            ),
            DatasetPreprocessingConfig(
                "tinystories",
                sources={
                    "stories": (
                        "datasets/raw/tinystories/TinyStories-train.txt"
                    ),
                },
                output_path=(
                    "datasets/canonical/tinystories.jsonl"
                ),
            ),
            DatasetPreprocessingConfig(
                "openassistant",
                sources={
                    "messages": (
                        "datasets/raw/openassistant/oasst1-ready.jsonl"
                    ),
                },
                output_path=(
                    "datasets/canonical/openassistant.jsonl"
                ),
            ),
        ],
        allow_default_sources=True,
        require_canonical_outputs=True,
        metadata={
            "raw_layer": "immutable",
            "canonical_layer": "loss-preserving",
            "dataset_count": 6,
        },
    )
