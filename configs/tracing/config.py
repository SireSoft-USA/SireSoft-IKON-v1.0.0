class TracingConfig:
    """
    Tracing-service deployment configuration.

    Runtime dependencies such as MetricsManager and EventBus are injected by
    TracingConfigFactory rather than serialized into this configuration.
    """

    def __init__(
        self,
        sampler=None,
        persistence_path=None,
        attach_metrics=True,
        publish_events=False,
        metadata=None,
    ):
        if sampler is None:
            sampler = (
                TraceSamplerConfig()
            )

        if not isinstance(
            sampler,
            TraceSamplerConfig,
        ):
            raise TypeError(
                "sampler must be TraceSamplerConfig or None"
            )

        if persistence_path is not None and (
            not isinstance(
                persistence_path,
                str,
            )
            or persistence_path == ""
        ):
            raise ValueError(
                "persistence_path must be non-empty str or None"
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

        self.sampler = sampler
        self.persistence_path = (
            persistence_path
        )
        self.attach_metrics = bool(
            attach_metrics
        )
        self.publish_events = bool(
            publish_events
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "sampler": (
                self.sampler.to_dict()
            ),
            "persistence_path": (
                self.persistence_path
            ),
            "attach_metrics": (
                self.attach_metrics
            ),
            "publish_events": (
                self.publish_events
            ),
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
