class MonitoringService:
    """
    Protocol-facing health/monitoring service.

    Supported operations:
      health
      snapshot
      probe
      list_probes
      load_balancer
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            MonitoringManager()
            if manager is None
            else manager
        )

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

        if request.service != "monitoring_service":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = request.operation

            if operation == "health":
                result = self.manager.health(
                    run_probes=request.payload.get(
                        "run_probes",
                        True,
                    ),
                    trace_id=request.trace_id,
                )

                return self._success(
                    request,
                    {
                        "health": result,
                    },
                )

            if operation == "snapshot":
                result = self.manager.snapshot(
                    run_probes=request.payload.get(
                        "run_probes",
                        True,
                    ),
                    trace_id=request.trace_id,
                )

                return self._success(
                    request,
                    {
                        "snapshot": result,
                    },
                )

            if operation == "probe":
                result = self.manager.run_probe(
                    self._required(
                        request.payload,
                        "probe_id",
                    ),
                    trace_id=request.trace_id,
                )

                return self._success(
                    request,
                    {
                        "probe": (
                            result.to_dict()
                        ),
                    },
                )

            if operation == "list_probes":
                probes = self.manager.list_probes()

                return self._success(
                    request,
                    {
                        "probes": probes,
                        "count": len(
                            probes
                        ),
                    },
                )

            if operation == "load_balancer":
                return self._success(
                    request,
                    {
                        "load_balancer": (
                            self.manager
                            .load_balancer_status()
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                (
                    "Unsupported monitoring service operation"
                ),
            )

        except KeyError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(error),
            )

        except (
            ValueError,
            TypeError,
            IndexError,
        ) as error:
            return self._error(
                request,
                "INVALID_REQUEST",
                str(error),
            )

    def _required(
        self,
        payload,
        key,
    ):
        if key not in payload:
            raise ValueError(
                "payload requires "
                + key
            )

        return payload[
            key
        ]

    def _success(
        self,
        request,
        data,
    ):
        return (
            ServiceResponse
            .success_response(
                request,
                data=data,
            )
        )

    def _error(
        self,
        request,
        code,
        message,
    ):
        return (
            ServiceResponse
            .error_response(
                request,
                ProtocolError(
                    code=code,
                    message=message,
                    retryable=False,
                ),
            )
        )
