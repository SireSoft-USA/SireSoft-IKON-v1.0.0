class DatasetPreprocessingConfig:
    SUPPORTED_DATASETS = (
        "dailydialog",
        "dolly",
        "movie-corpus",
        "siresoft",
        "tinystories",
        "openassistant",
    )

    REQUIRED_ROLES = {
        "dailydialog": ("dialogues",),
        "dolly": ("instructions",),
        "movie-corpus": (
            "conversations",
            "utterances",
        ),
        "siresoft": ("knowledge",),
        "tinystories": ("stories",),
        "openassistant": ("messages",),
    }

    def __init__(
        self,
        dataset_id,
        sources=None,
        normalize=True,
        strict=True,
        output_path=None,
        enabled=True,
        metadata=None,
    ):
        if dataset_id not in self.SUPPORTED_DATASETS:
            raise ValueError(
                "unsupported dataset_id: "
                + str(dataset_id)
            )

        if sources is None:
            sources = {}

        if not isinstance(sources, dict):
            raise TypeError(
                "sources must be dict or None"
            )

        normalized_sources = {}

        for role in sources:
            path = sources[role]

            if not isinstance(role, str) or role == "":
                raise ValueError(
                    "source role must be non-empty str"
                )

            if not isinstance(path, str) or path == "":
                raise ValueError(
                    "source path must be non-empty str"
                )

            normalized_sources[role] = path

        if output_path is not None and (
            not isinstance(output_path, str)
            or output_path == ""
        ):
            raise ValueError(
                "output_path must be non-empty str or None"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.dataset_id = dataset_id
        self.sources = normalized_sources
        self.normalize = bool(normalize)
        self.strict = bool(strict)
        self.output_path = output_path
        self.enabled = bool(enabled)
        self.metadata = self._copy(metadata)

    def required_roles(self):
        return list(
            self.REQUIRED_ROLES[
                self.dataset_id
            ]
        )

    def to_dict(self):
        return {
            "dataset_id": self.dataset_id,
            "sources": dict(self.sources),
            "normalize": self.normalize,
            "strict": self.strict,
            "output_path": self.output_path,
            "enabled": self.enabled,
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(self, value):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, (list, tuple)):
            return [
                self._copy(item)
                for item in value
            ]

        return value
