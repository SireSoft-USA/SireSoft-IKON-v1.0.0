class ShutdownSignalEvent:
    """
    Immutable description of one shutdown request.
    """

    def __init__(
        self,
        reason,
        signal_name=None,
        signal_number=None,
        request_sequence=1,
        metadata=None,
    ):
        if not isinstance(
            reason,
            str,
        ) or reason == "":
            raise ValueError(
                "reason must be non-empty str"
            )

        if signal_name is not None and (
            not isinstance(
                signal_name,
                str,
            )
            or signal_name == ""
        ):
            raise ValueError(
                "signal_name must be non-empty str or None"
            )

        if signal_number is not None and not isinstance(
            signal_number,
            int,
        ):
            raise TypeError(
                "signal_number must be int or None"
            )

        if (
            not isinstance(
                request_sequence,
                int,
            )
            or request_sequence <= 0
        ):
            raise ValueError(
                "request_sequence must be positive int"
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

        self.reason = reason
        self.signal_name = signal_name
        self.signal_number = signal_number
        self.request_sequence = request_sequence
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "reason": self.reason,
            "signal_name": (
                self.signal_name
            ),
            "signal_number": (
                self.signal_number
            ),
            "request_sequence": (
                self.request_sequence
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(value, dict):
            return {
                key: self._copy(
                    value[key]
                )
                for key in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(item)
                for item in value
            ]

        return value
