class RuntimeObservability:
    """
    Unified request observability over existing logging, metrics, tracing,
    and optional runtime-health components.

    Timestamps are explicit integer runtime ticks/seconds to match the tracing
    and metrics layers already used by SireLLM.
    """

    def __init__(
        self,
        logging_manager,
        metrics_manager,
        tracing_manager,
        health_manager=None,
    ):
        if not isinstance(logging_manager, LoggingManager):
            raise TypeError(
                "logging_manager must be LoggingManager"
            )

        if not isinstance(metrics_manager, MetricsManager):
            raise TypeError(
                "metrics_manager must be MetricsManager"
            )

        if not isinstance(tracing_manager, TracingManager):
            raise TypeError(
                "tracing_manager must be TracingManager"
            )

        if (
            health_manager is not None
            and not isinstance(
                health_manager,
                RuntimeHealthManager,
            )
        ):
            raise TypeError(
                "health_manager must be RuntimeHealthManager or None"
            )

        self.logging_manager = logging_manager
        self.metrics_manager = metrics_manager
        self.tracing_manager = tracing_manager
        self.health_manager = health_manager

        self._active_by_service = {}

        self.total_started = 0
        self.total_finished = 0
        self.total_success = 0
        self.total_error = 0
        self.total_exception = 0

        self._ensure_metrics()

    def begin_request(
        self,
        request,
        start_time,
    ):
        if not isinstance(request, ServiceRequest):
            raise TypeError(
                "request must be ServiceRequest"
            )

        self._validate_time(
            start_time,
            "start_time",
        )

        trace_id = (
            request.trace_id
            if request.trace_id is not None
            else (
                "trace-"
                + request.request_id
            )
        )

        started = self.tracing_manager.start_span(
            trace_id=trace_id,
            name=(
                request.service
                + "."
                + request.operation
            ),
            service_name=request.service,
            start_time=start_time,
            operation=request.operation,
            correlation_id=request.correlation_id,
            attributes={
                "request_id": request.request_id,
            },
        )

        span = started.get(
            "span"
        )

        span_id = (
            None
            if span is None
            else span[
                "span_id"
            ]
        )

        context = ObservationContext(
            request_id=request.request_id,
            service=request.service,
            operation=request.operation,
            trace_id=trace_id,
            correlation_id=request.correlation_id,
            start_time=start_time,
            span_id=span_id,
            sampled=bool(
                started[
                    "sampled"
                ]
            ),
        )

        self._active_by_service[
            request.service
        ] = (
            self._active_by_service.get(
                request.service,
                0,
            )
            + 1
        )

        self.metrics_manager.set_gauge(
            name="runtime_active_requests",
            value=self._active_by_service[
                request.service
            ],
            timestamp=start_time,
            labels={
                "service": request.service,
            },
        )

        self.logging_manager.info(
            message="service request started",
            timestamp=start_time,
            service=request.service,
            event="runtime.request_started",
            trace_id=trace_id,
            correlation_id=request.correlation_id,
            fields={
                "request_id": request.request_id,
                "operation": request.operation,
            },
        )

        self.total_started += 1

        return context

    def finish_response(
        self,
        context,
        response,
        end_time,
    ):
        if not isinstance(
            context,
            ObservationContext,
        ):
            raise TypeError(
                "context must be ObservationContext"
            )

        if not isinstance(
            response,
            ServiceResponse,
        ):
            raise TypeError(
                "response must be ServiceResponse"
            )

        self._validate_time(
            end_time,
            "end_time",
        )

        if response.request_id != context.request_id:
            raise ValueError(
                "response request_id does not match observation context"
            )

        if response.service != context.service:
            raise ValueError(
                "response service does not match observation context"
            )

        outcome = (
            "success"
            if response.success
            else "error"
        )

        error_type = None
        error_message = None

        if not response.success:
            error_type = response.error.code
            error_message = (
                response.error.message
            )

        self._finish(
            context=context,
            end_time=end_time,
            outcome=outcome,
            trace_status=(
                "ok"
                if response.success
                else "error"
            ),
            error_type=error_type,
            error_message=error_message,
        )

        if response.success:
            self.total_success += 1
        else:
            self.total_error += 1

        return context.to_dict()

    def finish_exception(
        self,
        context,
        error,
        end_time,
    ):
        if not isinstance(
            context,
            ObservationContext,
        ):
            raise TypeError(
                "context must be ObservationContext"
            )

        if not isinstance(
            error,
            BaseException,
        ):
            raise TypeError(
                "error must be BaseException"
            )

        self._validate_time(
            end_time,
            "end_time",
        )

        self._finish(
            context=context,
            end_time=end_time,
            outcome="exception",
            trace_status="error",
            error_type=(
                type(
                    error
                ).__name__
            ),
            error_message=str(error),
        )

        self.total_exception += 1

        return context.to_dict()

    def status(
        self,
    ):
        health = None

        if self.health_manager is not None:
            health = self.health_manager.check()

        return {
            "ready": True,
            "total_started": self.total_started,
            "total_finished": self.total_finished,
            "total_success": self.total_success,
            "total_error": self.total_error,
            "total_exception": self.total_exception,
            "active_by_service": dict(
                self._active_by_service
            ),
            "logging": self.logging_manager.status(),
            "metrics": self.metrics_manager.status(),
            "tracing": self.tracing_manager.status(),
            "health": health,
        }

    def _finish(
        self,
        context,
        end_time,
        outcome,
        trace_status,
        error_type=None,
        error_message=None,
    ):
        if context.finished:
            raise RuntimeError(
                "observation context already finished"
            )

        if end_time < context.start_time:
            raise ValueError(
                "end_time cannot precede start_time"
            )

        if (
            context.sampled
            and context.span_id is not None
        ):
            self.tracing_manager.finish_span(
                trace_id=context.trace_id,
                span_id=context.span_id,
                end_time=end_time,
                status=trace_status,
                error_type=error_type,
                error_message=error_message,
            )

        current = self._active_by_service.get(
            context.service,
            0,
        )

        if current <= 0:
            raise RuntimeError(
                "active request accounting underflow"
            )

        current -= 1

        self._active_by_service[
            context.service
        ] = current

        self.metrics_manager.set_gauge(
            name="runtime_active_requests",
            value=current,
            timestamp=end_time,
            labels={
                "service": context.service,
            },
        )

        self.metrics_manager.increment(
            name="runtime_requests_total",
            timestamp=end_time,
            amount=1,
            labels={
                "service": context.service,
                "operation": context.operation,
                "outcome": outcome,
            },
        )

        duration = (
            end_time
            - context.start_time
        )

        self.metrics_manager.observe(
            name="runtime_request_duration_seconds",
            value=float(
                duration
            ),
            timestamp=end_time,
            labels={
                "service": context.service,
                "operation": context.operation,
                "outcome": outcome,
            },
        )

        fields = {
            "request_id": context.request_id,
            "operation": context.operation,
            "outcome": outcome,
            "duration": duration,
        }

        if error_type is not None:
            fields[
                "error_type"
            ] = error_type

        self.logging_manager.log(
            level=(
                "INFO"
                if outcome == "success"
                else "ERROR"
            ),
            message="service request finished",
            timestamp=end_time,
            service=context.service,
            event="runtime.request_finished",
            trace_id=context.trace_id,
            correlation_id=context.correlation_id,
            fields=fields,
        )

        context.finish(
            outcome,
            end_time,
        )

        self.total_finished += 1

    def _ensure_metrics(
        self,
    ):
        registry = self.metrics_manager.registry

        try:
            registry.get_definition(
                "runtime_requests_total"
            )
        except KeyError:
            self.metrics_manager.define(
                name="runtime_requests_total",
                metric_type="counter",
                description=(
                    "Completed runtime service requests"
                ),
                label_names=[
                    "service",
                    "operation",
                    "outcome",
                ],
            )

        try:
            registry.get_definition(
                "runtime_active_requests"
            )
        except KeyError:
            self.metrics_manager.define(
                name="runtime_active_requests",
                metric_type="gauge",
                description=(
                    "Currently active runtime requests"
                ),
                label_names=[
                    "service",
                ],
            )

        try:
            registry.get_definition(
                "runtime_request_duration_seconds"
            )
        except KeyError:
            self.metrics_manager.define(
                name="runtime_request_duration_seconds",
                metric_type="histogram",
                description=(
                    "Runtime service request duration"
                ),
                unit="seconds",
                label_names=[
                    "service",
                    "operation",
                    "outcome",
                ],
                buckets=[
                    1.0,
                    2.0,
                    5.0,
                    10.0,
                    30.0,
                    60.0,
                    120.0,
                    300.0,
                ],
            )

    def _validate_time(
        self,
        value,
        field_name,
    ):
        if not isinstance(value, int) or value < 0:
            raise ValueError(
                field_name
                + " must be non-negative int"
            )
