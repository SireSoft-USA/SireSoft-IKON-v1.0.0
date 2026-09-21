class MonitoringConfig:
    """
    Serializable monitoring topology.

    Service handlers are intentionally runtime dependencies and are never
    serialized into monitoring config.
    """

    def __init__(
        self,
        probes,
        attach_load_balancer=False,
        metadata=None,
    ):
        if not isinstance(
            probes,
            (list, tuple),
        ):
            raise TypeError(
                "probes must be list/tuple"
            )

        normalized = []
        seen = {}

        for probe in probes:
            if not isinstance(
                probe,
                MonitoringProbeConfig,
            ):
                raise TypeError(
                    "probe entries must be MonitoringProbeConfig"
                )

            if probe.probe_id in seen:
                raise ValueError(
                    "duplicate probe_id: "
                    + probe.probe_id
                )

            seen[
                probe.probe_id
            ] = True

            normalized.append(
                probe
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

        self.probes = normalized
        self.attach_load_balancer = bool(
            attach_load_balancer
        )
        self.metadata = self._copy(
            metadata
        )

    def enabled_probes(
        self,
    ):
        return [
            probe
            for probe
            in self.probes
            if probe.enabled
        ]

    def probe_map(
        self,
    ):
        return {
            probe.probe_id: probe
            for probe
            in self.probes
        }

    def to_dict(
        self,
    ):
        return {
            "probes": [
                probe.to_dict()
                for probe
                in self.probes
            ],
            "attach_load_balancer": (
                self.attach_load_balancer
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
