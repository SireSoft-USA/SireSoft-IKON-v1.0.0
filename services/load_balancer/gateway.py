class APIGateway:
    """
    Transport-independent API gateway core.

    Responsibilities:
      - route resolution
      - middleware execution
      - public request -> internal ServiceRequest translation
      - correlation/trace propagation
      - internal response -> public response normalization

    Actual sockets/HTTP parsing are intentionally deferred to runtime/networking.
    """

    def __init__(
        self,
        router=None,
        middleware=None,
        dispatcher=None,
        service_name="api_gateway",
    ):
        self.router = (
            GatewayRouter()
            if router is None
            else router
        )

        if middleware is None:
            middleware = [
                AuthenticationMiddleware(),
                PayloadLimitMiddleware(),
            ]

        self.middleware = list(
            middleware
        )

        self.dispatcher = dispatcher
        self.service_name = service_name
        self._request_sequence = 0

    def register_route(self, route):
        self.router.add(
            route
        )
        return self

    def handle(self, context):
        if not isinstance(
            context,
            GatewayContext,
        ):
            raise TypeError(
                "context must be GatewayContext"
            )

        route = self.router.resolve(
            context.method,
            context.path,
        )

        if route is None:
            return self._public_error(
                context,
                ProtocolError(
                    code="ROUTE_NOT_FOUND",
                    message="No gateway route matches request",
                    details={
                        "method": context.method,
                        "path": context.path,
                    },
                    retryable=False,
                ),
                status=404,
            )

        context.route = route

        for component in self.middleware:
            error = component.before(
                context
            )

            if error is not None:
                return self._public_error(
                    context,
                    error,
                    status=self._status_for_error(
                        error.code
                    ),
                )

        request = self._service_request(
            context,
            route,
        )

        if self.dispatcher is None:
            return self._public_error(
                context,
                ProtocolError(
                    code="DISPATCHER_UNAVAILABLE",
                    message="No internal service dispatcher is configured",
                    retryable=True,
                ),
                status=503,
            )

        response = self.dispatcher(
            request
        )

        if not isinstance(
            response,
            ServiceResponse,
        ):
            raise TypeError(
                "dispatcher must return ServiceResponse"
            )

        public_response = self._public_response(
            response
        )

        index = len(self.middleware) - 1

        while index >= 0:
            public_response = (
                self.middleware[index].after(
                    context,
                    public_response,
                )
            )

            index -= 1

        return public_response

    def _service_request(
        self,
        context,
        route,
    ):
        self._request_sequence += 1

        request_id = (
            "gw-"
            + str(
                self._request_sequence
            )
        )

        correlation_id = (
            context.correlation_id
            if context.correlation_id is not None
            else request_id
        )

        trace_id = (
            context.trace_id
            if context.trace_id is not None
            else correlation_id
        )

        return ServiceRequest(
            request_id=request_id,
            service=route.service,
            operation=route.operation,
            payload=context.payload,
            metadata={
                "gateway_path": context.path,
                "gateway_method": context.method,
                "headers": dict(
                    context.headers
                ),
            },
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

    def _public_response(
        self,
        response,
    ):
        if response.success:
            return {
                "status": 200,
                "ok": True,
                "data": dict(
                    response.data
                ),
                "error": None,
                "request_id": (
                    response.request_id
                ),
                "trace_id": (
                    response.trace_id
                ),
            }

        return {
            "status": self._status_for_error(
                response.error.code
            ),
            "ok": False,
            "data": {},
            "error": (
                response.error.to_dict()
            ),
            "request_id": (
                response.request_id
            ),
            "trace_id": (
                response.trace_id
            ),
        }

    def _public_error(
        self,
        context,
        error,
        status,
    ):
        return {
            "status": status,
            "ok": False,
            "data": {},
            "error": error.to_dict(),
            "request_id": None,
            "trace_id": (
                context.trace_id
            ),
        }

    def _status_for_error(
        self,
        code,
    ):
        mapping = {
            "ROUTE_NOT_FOUND": 404,
            "UNAUTHENTICATED": 401,
            "FORBIDDEN": 403,
            "PAYLOAD_TOO_LARGE": 413,
            "INVALID_REQUEST": 400,
            "NOT_FOUND": 404,
            "CONFLICT": 409,
            "RATE_LIMITED": 429,
            "DISPATCHER_UNAVAILABLE": 503,
            "SERVICE_UNAVAILABLE": 503,
        }

        return mapping.get(
            code,
            500,
        )
