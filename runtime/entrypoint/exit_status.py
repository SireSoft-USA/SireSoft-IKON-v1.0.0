class RuntimeExitStatus:
    """
    Stable entrypoint result that can be mapped directly to a process exit code.
    """

    EXIT_OK = 0
    EXIT_STARTUP_FAILED = 10
    EXIT_RUNTIME_FAILED = 20
    EXIT_WAIT_TIMEOUT = 30
    EXIT_SHUTDOWN_FAILED = 40

    def __init__(
        self,
        code,
        reason,
        started=False,
        stopped=False,
        details=None,
    ):
        if not isinstance(
            code,
            int,
        ) or code < 0:
            raise ValueError(
                "code must be non-negative int"
            )

        if not isinstance(
            reason,
            str,
        ) or reason == "":
            raise ValueError(
                "reason must be non-empty str"
            )

        if details is None:
            details = {}

        if not isinstance(
            details,
            dict,
        ):
            raise TypeError(
                "details must be dict or None"
            )

        self.code = code
        self.reason = reason
        self.started = bool(
            started
        )
        self.stopped = bool(
            stopped
        )
        self.details = self._copy(
            details
        )

    def ok(
        self,
    ):
        return self.code == self.EXIT_OK

    def to_dict(
        self,
    ):
        return {
            "code": self.code,
            "reason": self.reason,
            "ok": self.ok(),
            "started": self.started,
            "stopped": self.stopped,
            "details": self._copy(
                self.details
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
