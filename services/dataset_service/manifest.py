class DatasetSource:
    """
    One immutable raw-source declaration.

    format:
      json
      jsonl
      text
      gzip
    """

    VALID_FORMATS = (
        "json",
        "jsonl",
        "text",
        "gzip",
    )

    def __init__(
        self,
        path,
        source_format,
        role="data",
        required=True,
        metadata=None,
    ):
        if not isinstance(path, str) or path == "":
            raise ValueError("path must be non-empty str")

        if source_format not in self.VALID_FORMATS:
            raise ValueError("unsupported dataset source format")

        if not isinstance(role, str) or role == "":
            raise ValueError("role must be non-empty str")

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.path = path
        self.source_format = source_format
        self.role = role
        self.required = bool(required)
        self.metadata = self._copy(metadata)

    def to_dict(self):
        return {
            "path": self.path,
            "format": self.source_format,
            "role": self.role,
            "required": self.required,
            "metadata": self._copy(self.metadata),
        }

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise TypeError("source definition must be dict")

        return cls(
            path=value["path"],
            source_format=value["format"],
            role=value.get("role", "data"),
            required=value.get("required", True),
            metadata=value.get("metadata", {}),
        )

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._copy(value[key])

            return result

        if isinstance(value, list):
            return [
                self._copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._copy(item)
                for item in value
            ]

        return value


class DatasetManifest:
    """
    Immutable declaration of one raw dataset family.
    """

    def __init__(
        self,
        dataset_id,
        name,
        sources,
        description="",
        metadata=None,
    ):
        if not isinstance(dataset_id, str) or dataset_id == "":
            raise ValueError("dataset_id must be non-empty str")

        if not isinstance(name, str) or name == "":
            raise ValueError("name must be non-empty str")

        if not isinstance(description, str):
            raise TypeError("description must be str")

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        source_list = list(sources)

        if len(source_list) == 0:
            raise ValueError("manifest requires at least one source")

        seen_paths = {}

        for source in source_list:
            if not isinstance(source, DatasetSource):
                raise TypeError("sources must contain DatasetSource")

            if source.path in seen_paths:
                raise ValueError(
                    "duplicate source path in manifest: "
                    + source.path
                )

            seen_paths[source.path] = True

        self.dataset_id = dataset_id
        self.name = name
        self.sources = source_list
        self.description = description
        self.metadata = self._copy(metadata)

    def required_sources(self):
        return [
            source
            for source in self.sources
            if source.required
        ]

    def to_dict(self):
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "metadata": self._copy(self.metadata),
            "sources": [
                source.to_dict()
                for source in self.sources
            ],
        }

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise TypeError("manifest must be dict")

        return cls(
            dataset_id=value["dataset_id"],
            name=value["name"],
            description=value.get("description", ""),
            metadata=value.get("metadata", {}),
            sources=[
                DatasetSource.from_dict(
                    source
                )
                for source in value["sources"]
            ],
        )

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._copy(value[key])

            return result

        if isinstance(value, list):
            return [
                self._copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._copy(item)
                for item in value
            ]

        return value


def default_dataset_manifests():
    """
    SireLLM's finalized six raw dataset families.
    """

    return [
        DatasetManifest(
            dataset_id="dailydialog",
            name="DailyDialog",
            description="Multi-turn daily conversation dataset.",
            sources=[
                DatasetSource(
                    "datasets/raw/dailydialog/dialogues.json",
                    "json",
                    role="dialogues",
                ),
                DatasetSource(
                    "datasets/raw/dailydialog/ontology.json",
                    "json",
                    role="ontology",
                ),
            ],
        ),
        DatasetManifest(
            dataset_id="dolly",
            name="Databricks Dolly 15K",
            description="Instruction-following dataset.",
            sources=[
                DatasetSource(
                    "datasets/raw/dolly/databricks-dolly-15k.jsonl",
                    "jsonl",
                    role="instructions",
                ),
            ],
        ),
        DatasetManifest(
            dataset_id="movie-corpus",
            name="Cornell Movie Dialogs Corpus",
            description="Movie dialogue corpus and relational metadata.",
            sources=[
                DatasetSource(
                    "datasets/raw/movie-corpus/conversations.json",
                    "json",
                    role="conversations",
                ),
                DatasetSource(
                    "datasets/raw/movie-corpus/corpus.json",
                    "json",
                    role="corpus",
                ),
                DatasetSource(
                    "datasets/raw/movie-corpus/index.json",
                    "json",
                    role="index",
                ),
                DatasetSource(
                    "datasets/raw/movie-corpus/speakers.json",
                    "json",
                    role="speakers",
                ),
                DatasetSource(
                    "datasets/raw/movie-corpus/utterances.json",
                    "json",
                    role="utterances",
                ),
            ],
        ),
        DatasetManifest(
            dataset_id="siresoft",
            name="SireSoft Knowledge",
            description="SireSoft company knowledge used for retrieval grounding.",
            sources=[
                DatasetSource(
                    "datasets/raw/siresoft/siresoft.txt",
                    "text",
                    role="knowledge",
                ),
            ],
            metadata={
                "rag_eligible": True,
            },
        ),
        DatasetManifest(
            dataset_id="tinystories",
            name="TinyStories",
            description="Plain-text synthetic story corpus.",
            sources=[
                DatasetSource(
                    "datasets/raw/tinystories/TinyStories-train.txt",
                    "text",
                    role="stories",
                ),
            ],
        ),
        DatasetManifest(
            dataset_id="openassistant",
            name="OpenAssistant OASST1",
            description="OpenAssistant message-tree dataset.",
            sources=[
                DatasetSource(
                    "datasets/raw/openassistant/source/2023-04-12_oasst_ready.messages.jsonl.gz",
                    "gzip",
                    role="archive",
                    required=False,
                    metadata={
                        "compressed_source": True,
                    },
                ),
                DatasetSource(
                    "datasets/raw/openassistant/oasst1-ready.jsonl",
                    "jsonl",
                    role="messages",
                    required=True,
                ),
            ],
        ),
    ]
