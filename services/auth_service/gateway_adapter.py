class GatewayTokenAuthenticationMiddleware:
    """
    API-gateway middleware adapter.

    Put this middleware before AuthenticationMiddleware. It validates a Bearer
    token, sets context.authenticated, and attaches a redacted principal to
    context.metadata. Missing/invalid tokens remain unauthenticated so the
    gateway's existing route-level AuthenticationMiddleware can enforce policy.
    """

    def __init__(
        self,
        auth_manager,
        now_provider,
        permission_by_route=None,
    ):
        if auth_manager is None or not hasattr(
            auth_manager,
            "verify_token",
        ):
            raise TypeError(
                "auth_manager must provide verify_token()"
            )

        if not callable(
            now_provider
        ):
            raise TypeError(
                "now_provider must be callable"
            )

        if permission_by_route is None:
            permission_by_route = {}

        if not isinstance(
            permission_by_route,
            dict,
        ):
            raise TypeError(
                "permission_by_route must be dict or None"
            )

        self.auth_manager = (
            auth_manager
        )

        self.now_provider = (
            now_provider
        )

        self.permission_by_route = dict(
            permission_by_route
        )

    def before(
        self,
        context,
    ):
        header = self._authorization_header(
            context.headers
        )

        if header is None:
            return None

        token = self._bearer_token(
            header
        )

        if token is None:
            context.metadata[
                "auth_error"
            ] = "INVALID_AUTHORIZATION_HEADER"

            return None

        try:
            principal = (
                self.auth_manager
                .verify_token(
                    token,
                    int(
                        self.now_provider()
                    ),
                )
            )

        except Exception as error:
            context.metadata[
                "auth_error"
            ] = type(
                error
            ).__name__

            return None

        permission = self._route_permission(
            context
        )

        if permission is not None:
            authorized = (
                self.auth_manager
                .authorize(
                    principal,
                    permission,
                )
            )

            if not authorized[
                "allowed"
            ]:
                return ProtocolError(
                    code="FORBIDDEN",
                    message=(
                        "Authenticated principal lacks route permission"
                    ),
                    details={
                        "permission": permission,
                    },
                    retryable=False,
                )

        context.authenticated = True

        context.metadata[
            "principal"
        ] = principal

        return None

    def after(
        self,
        context,
        response,
    ):
        return response

    def _authorization_header(
        self,
        headers,
    ):
        for key in headers:
            if str(
                key
            ).lower() == "authorization":
                return headers[
                    key
                ]

        return None

    def _bearer_token(
        self,
        header,
    ):
        if not isinstance(
            header,
            str,
        ):
            return None

        parts = header.strip().split(
            " ",
            1,
        )

        if len(parts) != 2:
            return None

        if parts[
            0
        ].lower() != "bearer":
            return None

        token = parts[
            1
        ].strip()

        if token == "":
            return None

        return token

    def _route_permission(
        self,
        context,
    ):
        key = (
            context.method
            + " "
            + context.path
        )

        return self.permission_by_route.get(
            key
        )
