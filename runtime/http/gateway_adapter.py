class HTTPGatewayAdapter:
    """
    Converts parsed HTTPRequest objects into GatewayContext and gateway output
    into HTTPResponse.

    Authentication is not inferred from headers. A caller may provide a
    context_enricher(request) callback that returns trusted transport metadata,
    e.g. {"authenticated": True}.
    """

    def __init__(
        self,
        gateway,
        json_codec=None,
        context_enricher=None,
    ):
        if not isinstance(
            gateway,
            APIGateway,
        ):
            raise TypeError(
                "gateway must be APIGateway"
            )

        if (
            context_enricher
            is not None
            and not callable(
                context_enricher
            )
        ):
            raise TypeError(
                "context_enricher must be callable or None"
            )

        self.gateway = gateway
        self.json_codec = (
            RuntimeJSONCodec()
            if json_codec is None
            else json_codec
        )
        self.context_enricher = (
            context_enricher
        )

    def handle(
        self,
        request,
    ):
        if not isinstance(
            request,
            HTTPRequest,
        ):
            raise TypeError(
                "request must be HTTPRequest"
            )

        path = self._path_only(
            request.target
        )

        payload = self._payload(
            request
        )

        trusted = {}

        if self.context_enricher is not None:
            trusted = (
                self.context_enricher(
                    request
                )
            )

            if trusted is None:
                trusted = {}

            if not isinstance(
                trusted,
                dict,
            ):
                raise TypeError(
                    "context_enricher must return dict or None"
                )

        trace_id = (
            trusted.get(
                "trace_id"
            )
            if "trace_id"
            in trusted
            else request.header(
                "x-trace-id"
            )
        )

        correlation_id = (
            trusted.get(
                "correlation_id"
            )
            if "correlation_id"
            in trusted
            else request.header(
                "x-correlation-id"
            )
        )

        context = GatewayContext(
            method=request.method,
            path=path,
            payload=payload,
            headers=dict(
                request.headers
            ),
            authenticated=bool(
                trusted.get(
                    "authenticated",
                    False,
                )
            ),
            trace_id=trace_id,
            correlation_id=(
                correlation_id
            ),
        )

        public = (
            self.gateway.handle(
                context
            )
        )

        response_body = (
            self.json_codec
            .encode(
                public
            )
        )

        return HTTPResponse(
            status_code=public[
                "status"
            ],
            body=response_body,
            headers={
                "content-type": (
                    "application/json; charset=utf-8"
                ),
                "x-content-type-options": (
                    "nosniff"
                ),
            },
        )

    def error_response(
        self,
        status,
        code,
        message,
    ):
        public = {
            "status": status,
            "ok": False,
            "data": {},
            "error": {
                "code": code,
                "message": message,
                "details": {},
                "retryable": False,
            },
            "request_id": None,
            "trace_id": None,
        }

        return HTTPResponse(
            status_code=status,
            body=self.json_codec.encode(
                public
            ),
            headers={
                "content-type": (
                    "application/json; charset=utf-8"
                ),
                "x-content-type-options": (
                    "nosniff"
                ),
            },
        )

    def _payload(
        self,
        request,
    ):
        if len(
            request.body
        ) == 0:
            return {}

        content_type = (
            request.header(
                "content-type",
                "",
            )
        )

        media_type = (
            content_type
            .split(
                ";",
                1,
            )[
                0
            ]
            .strip()
            .lower()
        )

        if media_type != "application/json":
            raise ValueError(
                "HTTP API request body must use application/json"
            )

        value = (
            self.json_codec
            .decode(
                request.body
            )
        )

        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "HTTP API JSON payload must be an object"
            )

        return value

    def _path_only(
        self,
        target,
    ):
        index = target.find(
            "?"
        )

        if index < 0:
            return target

        path = target[
            :index
        ]

        if path == "":
            return "/"

        return path
