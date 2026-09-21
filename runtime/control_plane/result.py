class ControlPlaneResult:
    """
    Internal result object used by RuntimeControlPlane before protocol wrapping.
    """

    def __init__(
        self,
        operation,
        data=None,
        changed=False,
    ):
        if not isinstance(
            operation,
            str,
        ) or operation == "":
            raise ValueError(
                "operation must be non-empty str"
            )

        if data is None:
            data = {}

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "data must be dict or None"
            )

        self.operation = operation
        self.data = self._copy(
            data
        )
        self.changed = bool(
            changed
        )

    def to_dict(
        self,
    ):
        return {
            "operation": (
                self.operation
            ),
            "changed": (
                self.changed
            ),
            "data": self._copy(
                self.data
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
