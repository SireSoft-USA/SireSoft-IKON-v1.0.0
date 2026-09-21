def default_datasets_config():
    """
    Finalized SireLLM raw dataset inventory.

    This mirrors the immutable raw layer and preserves every declared source,
    including auxiliary ontology/metadata files and the optional compressed
    OpenAssistant archive.
    """

    return DatasetsConfig(
        datasets=[
            DatasetDefinitionConfig(
                dataset_id="dailydialog",
                name="DailyDialog",
                description=(
                    "Multi-turn daily conversation dataset."
                ),
                sources=[
                    DatasetSourceConfig(
                        (
                            "datasets/raw/dailydialog/"
                            "dialogues.json"
                        ),
                        "json",
                        role="dialogues",
                    ),
                    DatasetSourceConfig(
                        (
                            "datasets/raw/dailydialog/"
                            "ontology.json"
                        ),
                        "json",
                        role="ontology",
                    ),
                ],
            ),
            DatasetDefinitionConfig(
                dataset_id="dolly",
                name="Databricks Dolly 15K",
                description=(
                    "Instruction-following dataset."
                ),
                sources=[
                    DatasetSourceConfig(
                        (
                            "datasets/raw/dolly/"
                            "databricks-dolly-15k.jsonl"
                        ),
                        "jsonl",
                        role="instructions",
                    ),
                ],
            ),
            DatasetDefinitionConfig(
                dataset_id="movie-corpus",
                name=(
                    "Cornell Movie Dialogs Corpus"
                ),
                description=(
                    "Movie dialogue corpus and relational metadata."
                ),
                sources=[
                    DatasetSourceConfig(
                        (
                            "datasets/raw/movie-corpus/"
                            "conversations.json"
                        ),
                        "json",
                        role="conversations",
                    ),
                    DatasetSourceConfig(
                        (
                            "datasets/raw/movie-corpus/"
                            "corpus.json"
                        ),
                        "json",
                        role="corpus",
                    ),
                    DatasetSourceConfig(
                        (
                            "datasets/raw/movie-corpus/"
                            "index.json"
                        ),
                        "json",
                        role="index",
                    ),
                    DatasetSourceConfig(
                        (
                            "datasets/raw/movie-corpus/"
                            "speakers.json"
                        ),
                        "json",
                        role="speakers",
                    ),
                    DatasetSourceConfig(
                        (
                            "datasets/raw/movie-corpus/"
                            "utterances.json"
                        ),
                        "json",
                        role="utterances",
                    ),
                ],
            ),
            DatasetDefinitionConfig(
                dataset_id="siresoft",
                name="SireSoft Knowledge",
                description=(
                    "SireSoft company knowledge used for retrieval grounding."
                ),
                metadata={
                    "rag_eligible": True,
                },
                sources=[
                    DatasetSourceConfig(
                        (
                            "datasets/raw/siresoft/"
                            "siresoft.txt"
                        ),
                        "text",
                        role="knowledge",
                    ),
                ],
            ),
            DatasetDefinitionConfig(
                dataset_id="tinystories",
                name="TinyStories",
                description=(
                    "Plain-text synthetic story corpus."
                ),
                sources=[
                    DatasetSourceConfig(
                        (
                            "datasets/raw/tinystories/"
                            "TinyStories-train.txt"
                        ),
                        "text",
                        role="stories",
                    ),
                ],
            ),
            DatasetDefinitionConfig(
                dataset_id="openassistant",
                name="OpenAssistant OASST1",
                description=(
                    "OpenAssistant message-tree dataset."
                ),
                sources=[
                    DatasetSourceConfig(
                        (
                            "datasets/raw/openassistant/source/"
                            "2023-04-12_oasst_ready.messages.jsonl.gz"
                        ),
                        "gzip",
                        role="archive",
                        required=False,
                        metadata={
                            "compressed_source": True,
                        },
                    ),
                    DatasetSourceConfig(
                        (
                            "datasets/raw/openassistant/"
                            "oasst1-ready.jsonl"
                        ),
                        "jsonl",
                        role="messages",
                        required=True,
                    ),
                ],
            ),
        ],
        enforce_global_source_uniqueness=True,
        capture_immutable_baselines=False,
        metadata={
            "raw_layer": "immutable",
            "dataset_count": 6,
        },
    )
