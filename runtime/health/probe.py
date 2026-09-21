class RuntimeProbeResult:
    STATUSES = (
        "healthy",
        "degraded",
        "unhealthy",
    )

    def __init__(
        self,
        name,
        status,
        ready,
        details=None,
        error=None,
    ):
        if not isinstance(
            name,
            str,
        ) or name == "":
            raise ValueError(
                "name must be non-empty str"
            )

        if status not in self.STATUSES:
            raise ValueError(
                "invalid runtime probe status"
            )

        if not isinstance(
            ready,
            bool,
        ):
            raise TypeError(
                "ready must be bool"
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

        if error is not None and not isinstance(
            error,
            str,
        ):
            raise TypeError(
                "error must be str or None"
            )

        self.name = name
        self.status = status
        self.ready = ready
        self.details = self._copy(
            details
        )
        self.error = error

    def to_dict(
        self,
    ):
        return {
            "name": self.name,
            "status": self.status,
            "ready": self.ready,
            "details": self._copy(
                self.details
            ),
            "error": self.error,
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
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value


class RuntimeProbe:
    def __init__(
        self,
        name,
        checker,
        required=True,
    ):
        if not isinstance(
            name,
            str,
        ) or name == "":
            raise ValueError(
                "name must be non-empty str"
            )

        if not callable(
            checker
        ):
            raise TypeError(
                "checker must be callable"
            )

        self.name = name
        self.checker = checker
        self.required = bool(
            required
        )

    def execute(
        self,
    ):
        try:
            value = self.checker()

        except BaseException as error:
            return RuntimeProbeResult(
                name=self.name,
                status="unhealthy",
                ready=False,
                details={},
                error=str(
                    error
                ),
            )

        if isinstance(
            value,
            RuntimeProbeResult,
        ):
            if value.name != self.name:
                raise ValueError(
                    "probe result name mismatch"
                )

            return value

        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "probe checker must return RuntimeProbeResult or dict"
            )

        return RuntimeProbeResult(
            name=self.name,
            status=value[
                "status"
            ],
            ready=bool(
                value[
                    "ready"
                ]
            ),
            details=value.get(
                "details",
                {},
            ),
            error=value.get(
                "error"
            ),
        )
