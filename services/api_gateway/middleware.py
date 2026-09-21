class GatewayContext:
    """
    Transport-independent request context.
    """

    def __init__(
        self,
        method,
        path,
        payload=None,
        headers=None,
        authenticated=False,
        trace_id=None,
        correlation_id=None,
    ):
        if not isinstance(method, str) or method == "":
            raise ValueError("method must be non-empty str")

        if not isinstance(path, str) or path == "":
            raise ValueError("path must be non-empty str")

        if payload is None:
            payload = {}

        if headers is None:
            headers = {}

        if not isinstance(payload, dict):
            raise TypeError("payload must be dict or None")

        if not isinstance(headers, dict):
            raise TypeError("headers must be dict or None")

        self.method = method.upper()
        self.path = path
        self.payload = dict(payload)
        self.headers = dict(headers)
        self.authenticated = bool(
            authenticated
        )
        self.trace_id = trace_id
        self.correlation_id = correlation_id
        self.route = None
        self.metadata = {}


class GatewayMiddleware:
    """
    Middleware base contract.
    """

    def before(self, context):
        return None

    def after(
        self,
        context,
        response,
    ):
        return response


class AuthenticationMiddleware(GatewayMiddleware):
    """
    Enforces route-level authentication without binding to any auth provider.
    """

    def before(self, context):
        route = context.route

        if (
            route is not None
            and route.auth_required
            and not context.authenticated
        ):
            return ProtocolError(
                code="UNAUTHENTICATED",
                message="Authentication is required for this route",
                details={
                    "path": context.path,
                    "method": context.method,
                },
                retryable=False,
            )

        return None


class PayloadLimitMiddleware(GatewayMiddleware):
    """
    Enforces approximate payload size using deterministic text-length estimation.

    Real byte-accurate HTTP body limits belong in runtime/networking later.
    """

    def before(self, context):
        route = context.route

        if (
            route is None
            or route.max_payload_bytes is None
        ):
            return None

        size = self._estimate(
            context.payload
        )

        if size > route.max_payload_bytes:
            return ProtocolError(
                code="PAYLOAD_TOO_LARGE",
                message="Request payload exceeds route limit",
                details={
                    "estimated_bytes": size,
                    "limit": route.max_payload_bytes,
                },
                retryable=False,
            )

        return None

    def _estimate(self, value):
        if value is None:
            return 4

        if value is True:
            return 4

        if value is False:
            return 5

        if isinstance(value, (int, float)):
            return len(
                str(value)
            )

        if isinstance(value, str):
            return len(
                value.encode("utf-8")
            )

        if isinstance(value, (bytes, bytearray)):
            return len(value)

        if isinstance(value, (list, tuple)):
            total = 2

            for item in value:
                total += self._estimate(
                    item
                )
                total += 1

            return total

        if isinstance(value, dict):
            total = 2

            for key in value:
                total += len(
                    str(key).encode("utf-8")
                )
                total += self._estimate(
                    value[key]
                )
                total += 2

            return total

        return len(
            str(value).encode("utf-8")
        )
