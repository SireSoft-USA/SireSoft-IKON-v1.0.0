class ModelVersionConfig:
    """
    Declarative model-registry bootstrap entry.

    Checkpoint contents remain authoritative for architecture/parameter metadata;
    config metadata is only deployment/bootstrap metadata.
    """

    def __init__(
        self,
        model_id,
        version,
        checkpoint_path,
        stage=False,
        promote=False,
        verify=False,
        enabled=True,
        metadata=None,
    ):
        for field_name, value in (
            ("model_id", model_id),
            ("version", version),
            ("checkpoint_path", checkpoint_path),
        ):
            if not isinstance(
                value,
                str,
            ) or value == "":
                raise ValueError(
                    field_name
                    + " must be non-empty str"
                )

        if (
            promote
            and not enabled
        ):
            raise ValueError(
                "disabled version cannot be promoted"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.model_id = model_id
        self.version = version
        self.checkpoint_path = (
            checkpoint_path
        )
        self.stage = bool(
            stage
            or promote
        )
        self.promote = bool(
            promote
        )
        self.verify = bool(
            verify
        )
        self.enabled = bool(
            enabled
        )
        self.metadata = self._copy(
            metadata
        )

    def key(
        self,
    ):
        return (
            self.model_id
            + "@"
            + self.version
        )

    def to_dict(
        self,
    ):
        return {
            "model_id": self.model_id,
            "version": self.version,
            "checkpoint_path": (
                self.checkpoint_path
            ),
            "stage": self.stage,
            "promote": self.promote,
            "verify": self.verify,
            "enabled": self.enabled,
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._copy(
                    value[
                        key
                    ]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
