class MonitoringProbeConfig:
    def __init__(
        self,
        probe_id,
        service_name,
        operation="status",
        payload=None,
        required=True,
        readiness_path=None,
        enabled=True,
        metadata=None,
    ):
        if not isinstance(
            probe_id,
            str,
        ) or probe_id == "":
            raise ValueError(
                "probe_id must be non-empty str"
            )

        if not isinstance(
            service_name,
            str,
        ) or service_name == "":
            raise ValueError(
                "service_name must be non-empty str"
            )

        if not isinstance(
            operation,
            str,
        ) or operation == "":
            raise ValueError(
                "operation must be non-empty str"
            )

        if payload is None:
            payload = {}

        if metadata is None:
            metadata = {}

        if readiness_path is None:
            readiness_path = []

        if not isinstance(
            payload,
            dict,
        ):
            raise TypeError(
                "payload must be dict or None"
            )

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        if not isinstance(
            readiness_path,
            (list, tuple),
        ):
            raise TypeError(
                "readiness_path must be list/tuple or None"
            )

        normalized_path = []

        for key in readiness_path:
            if not isinstance(
                key,
                str,
            ) or key == "":
                raise ValueError(
                    "readiness_path entries must be non-empty str"
                )

            normalized_path.append(
                key
            )

        self.probe_id = probe_id
        self.service_name = (
            service_name
        )
        self.operation = operation
        self.payload = self._copy(
            payload
        )
        self.required = bool(
            required
        )
        self.readiness_path = (
            normalized_path
        )
        self.enabled = bool(
            enabled
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "probe_id": (
                self.probe_id
            ),
            "service_name": (
                self.service_name
            ),
            "operation": (
                self.operation
            ),
            "payload": self._copy(
                self.payload
            ),
            "required": (
                self.required
            ),
            "readiness_path": list(
                self.readiness_path
            ),
            "enabled": (
                self.enabled
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
