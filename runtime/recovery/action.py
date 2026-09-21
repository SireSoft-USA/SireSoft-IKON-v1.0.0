class RecoveryAction:
    def __init__(
        self,
        action_id,
        action_type,
        target,
        reason_code,
        automatic=False,
        parameters=None,
        metadata=None,
    ):
        for field_name, value in (
            ("action_id", action_id),
            ("action_type", action_type),
            ("target", target),
            ("reason_code", reason_code),
        ):
            if not isinstance(value, str) or value == "":
                raise ValueError(
                    field_name + " must be non-empty str"
                )

        if parameters is None:
            parameters = {}

        if metadata is None:
            metadata = {}

        if not isinstance(parameters, dict):
            raise TypeError("parameters must be dict or None")

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.action_id = action_id
        self.action_type = action_type
        self.target = target
        self.reason_code = reason_code
        self.automatic = bool(automatic)
        self.parameters = self._copy(parameters)
        self.metadata = self._copy(metadata)

        self.status = "planned"
        self.result = None
        self.error = None

    def mark_running(self):
        if self.status != "planned":
            raise RuntimeError(
                "recovery action must be planned before running"
            )

        self.status = "running"
        return self

    def mark_succeeded(
        self,
        result=None,
    ):
        if self.status != "running":
            raise RuntimeError(
                "recovery action must be running before success"
            )

        self.status = "succeeded"
        self.result = self._copy(result)
        self.error = None

        return self

    def mark_failed(
        self,
        error,
    ):
        if self.status != "running":
            raise RuntimeError(
                "recovery action must be running before failure"
            )

        self.status = "failed"
        self.error = str(error)

        return self

    def mark_skipped(
        self,
        reason,
    ):
        if self.status != "planned":
            raise RuntimeError(
                "only planned recovery action can be skipped"
            )

        self.status = "skipped"
        self.error = str(reason)

        return self

    def to_dict(self):
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target": self.target,
            "reason_code": self.reason_code,
            "automatic": self.automatic,
            "parameters": self._copy(self.parameters),
            "metadata": self._copy(self.metadata),
            "status": self.status,
            "result": self._copy(self.result),
            "error": self.error,
        }

    def _copy(
        self,
        value,
    ):
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
