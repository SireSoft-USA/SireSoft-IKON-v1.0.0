class RuntimeControlService:
    """
    Protocol-facing runtime control service.

    Expected deployment boundary: expose only through authenticated/admin
    routes. This service itself does not duplicate the auth service.
    """

    TARGET = (
        "runtime_control"
    )

    def __init__(
        self,
        controller,
    ):
        if not isinstance(
            controller,
            RuntimeControlPlane,
        ):
            raise TypeError(
                "controller must be RuntimeControlPlane"
            )

        self.controller = controller
        self._reports = {}
        self._report_order = []

    def handle(
        self,
        request,
    ):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        if request.service != self.TARGET:
            return (
                ServiceResponse
                .error_response(
                    request,
                    ProtocolError(
                        code=(
                            "WRONG_SERVICE_TARGET"
                        ),
                        message=(
                            "Request does not target runtime_control"
                        ),
                        retryable=False,
                    ),
                )
            )

        try:
            operation = (
                request.operation
            )

            payload = (
                request.payload
                if request.payload
                is not None
                else {}
            )

            if operation == "status":
                result = (
                    self.controller
                    .status()
                )

            elif operation == "diagnostics":
                result = (
                    self.controller
                    .diagnostics(
                        captured_at=(
                            self._required_int(
                                payload,
                                "captured_at",
                            )
                        ),
                        log_limit=(
                            self._optional_positive_int(
                                payload,
                                "log_limit",
                                20,
                            )
                        ),
                        trace_limit=(
                            self._optional_positive_int(
                                payload,
                                "trace_limit",
                                20,
                            )
                        ),
                        extra=(
                            payload.get(
                                "extra"
                            )
                        ),
                    )
                )

                report = (
                    self.controller
                    .last_diagnostic_report
                )

                if report is None:
                    raise RuntimeError(
                        "diagnostic report was not retained by controller"
                    )

                self._store_report(
                    report
                )

            elif operation == "recovery_plan":
                report = (
                    self._get_report(
                        payload
                    )
                )

                result = (
                    self.controller
                    .recovery_plan(
                        report
                    )
                )

            elif operation == "recover":
                report = (
                    self._get_report(
                        payload
                    )
                )

                result = (
                    self.controller
                    .recover(
                        report,
                        dry_run=bool(
                            payload.get(
                                "dry_run",
                                True,
                            )
                        ),
                        allow_manual=bool(
                            payload.get(
                                "allow_manual",
                                False,
                            )
                        ),
                    )
                )

            elif operation == "begin_maintenance":
                result = (
                    self.controller
                    .begin_maintenance(
                        now=(
                            self._required_int(
                                payload,
                                "now",
                            )
                        ),
                        reason=(
                            payload.get(
                                "reason",
                                "maintenance",
                            )
                        ),
                    )
                )

            elif operation == "advance_maintenance":
                result = (
                    self.controller
                    .advance_maintenance(
                        now=(
                            self._required_int(
                                payload,
                                "now",
                            )
                        )
                    )
                )

            elif operation == "exit_maintenance":
                result = (
                    self.controller
                    .exit_maintenance(
                        now=(
                            self._required_int(
                                payload,
                                "now",
                            )
                        )
                    )
                )

            elif operation == "request_shutdown":
                reason = payload.get(
                    "reason"
                )

                if (
                    not isinstance(
                        reason,
                        str,
                    )
                    or reason == ""
                ):
                    raise ValueError(
                        "reason must be non-empty str"
                    )

                result = (
                    self.controller
                    .request_shutdown(
                        reason=reason,
                        metadata=(
                            payload.get(
                                "metadata"
                            )
                        ),
                    )
                )

            elif operation == "list_reports":
                result = ControlPlaneResult(
                    operation=(
                        "list_reports"
                    ),
                    data={
                        "report_ids": list(
                            self._report_order
                        ),
                    },
                    changed=False,
                )

            else:
                return (
                    ServiceResponse
                    .error_response(
                        request,
                        ProtocolError(
                            code=(
                                "UNKNOWN_OPERATION"
                            ),
                            message=(
                                "Unknown runtime_control operation"
                            ),
                            details={
                                "operation": (
                                    operation
                                ),
                            },
                            retryable=False,
                        ),
                    )
                )

            return (
                ServiceResponse
                .success_response(
                    request,
                    data=result.to_dict(),
                )
            )

        except (
            ValueError,
            TypeError,
            KeyError,
            RuntimeError,
        ) as error:
            return (
                ServiceResponse
                .error_response(
                    request,
                    ProtocolError(
                        code=(
                            "CONTROL_OPERATION_FAILED"
                        ),
                        message=str(
                            error
                        ),
                        retryable=False,
                    ),
                )
            )

    def _store_report(
        self,
        report,
    ):
        self._reports[
            report.report_id
        ] = report

        if (
            report.report_id
            not in self._report_order
        ):
            self._report_order.append(
                report.report_id
            )

    def _get_report(
        self,
        payload,
    ):
        report_id = payload.get(
            "report_id"
        )

        if (
            not isinstance(
                report_id,
                str,
            )
            or report_id == ""
        ):
            raise ValueError(
                "report_id must be non-empty str"
            )

        if report_id not in self._reports:
            raise KeyError(
                "runtime diagnostic report not found: "
                + report_id
            )

        return self._reports[
            report_id
        ]

    def _required_int(
        self,
        payload,
        key,
    ):
        if key not in payload:
            raise ValueError(
                key
                + " is required"
            )

        value = payload[
            key
        ]

        if (
            not isinstance(
                value,
                int,
            )
            or value < 0
        ):
            raise ValueError(
                key
                + " must be non-negative int"
            )

        return value

    def _optional_positive_int(
        self,
        payload,
        key,
        default,
    ):
        if key not in payload:
            return default

        value = payload[
            key
        ]

        if (
            not isinstance(
                value,
                int,
            )
            or value <= 0
        ):
            raise ValueError(
                key
                + " must be positive int"
            )

        return value
