class GatewayRateLimitMiddleware:
    """
    API-gateway token-bucket middleware.

    Resolution order for the logical caller key:
      1. authenticated principal user_id from context.metadata
      2. configured client-id header
      3. literal "anonymous"

    The middleware deliberately does not infer IP addresses because transport
    parsing belongs to the runtime/network layer.
    """

    def __init__(
        self,
        rate_limit_manager,
        now_provider,
        policy_by_route=None,
        default_policy_id=None,
        client_id_header="x-client-id",
    ):
        if rate_limit_manager is None or not hasattr(
            rate_limit_manager,
            "consume",
        ):
            raise TypeError(
                "rate_limit_manager must provide consume()"
            )

        if not callable(
            now_provider
        ):
            raise TypeError(
                "now_provider must be callable"
            )

        if policy_by_route is None:
            policy_by_route = {}

        if not isinstance(
            policy_by_route,
            dict,
        ):
            raise TypeError(
                "policy_by_route must be dict or None"
            )

        if (
            default_policy_id
            is not None
            and not isinstance(
                default_policy_id,
                str,
            )
        ):
            raise TypeError(
                "default_policy_id must be str or None"
            )

        self.rate_limit_manager = (
            rate_limit_manager
        )

        self.now_provider = (
            now_provider
        )

        self.policy_by_route = dict(
            policy_by_route
        )

        self.default_policy_id = (
            default_policy_id
        )

        self.client_id_header = (
            str(
                client_id_header
            ).lower()
        )

    def before(
        self,
        context,
    ):
        policy_id = (
            self._policy_id(
                context
            )
        )

        if policy_id is None:
            return None

        key = self._key(
            context
        )

        try:
            result = (
                self.rate_limit_manager
                .consume(
                    policy_id=policy_id,
                    key=key,
                    now=int(
                        self.now_provider()
                    ),
                )
            )

        except Exception as error:
            return ProtocolError(
                code="INVALID_REQUEST",
                message=(
                    "Rate-limit middleware configuration failed"
                ),
                details={
                    "policy_id": (
                        policy_id
                    ),
                    "error_type": (
                        type(
                            error
                        ).__name__
                    ),
                },
                retryable=False,
            )

        context.metadata[
            "rate_limit"
        ] = result

        if not result[
            "allowed"
        ]:
            return ProtocolError(
                code="RATE_LIMITED",
                message=(
                    "Request rate limit exceeded"
                ),
                details={
                    "policy_id": (
                        policy_id
                    ),
                    "key": key,
                    "remaining_tokens": (
                        result[
                            "remaining_tokens"
                        ]
                    ),
                    "retry_after_seconds": (
                        result[
                            "retry_after_seconds"
                        ]
                    ),
                },
                retryable=True,
            )

        return None

    def after(
        self,
        context,
        response,
    ):
        if (
            "rate_limit"
            in context.metadata
            and isinstance(
                response,
                dict,
            )
        ):
            output = dict(
                response
            )

            output[
                "rate_limit"
            ] = dict(
                context.metadata[
                    "rate_limit"
                ]
            )

            return output

        return response

    def _policy_id(
        self,
        context,
    ):
        route_key = (
            context.method
            + " "
            + context.path
        )

        if route_key in self.policy_by_route:
            return self.policy_by_route[
                route_key
            ]

        return self.default_policy_id

    def _key(
        self,
        context,
    ):
        principal = context.metadata.get(
            "principal"
        )

        if isinstance(
            principal,
            dict,
        ):
            user_id = principal.get(
                "user_id"
            )

            if (
                isinstance(
                    user_id,
                    str,
                )
                and user_id != ""
            ):
                return (
                    "user:"
                    + user_id
                )

        for header_name in context.headers:
            if (
                str(
                    header_name
                ).lower()
                == self.client_id_header
            ):
                value = str(
                    context.headers[
                        header_name
                    ]
                ).strip()

                if value != "":
                    return (
                        "client:"
                        + value
                    )

        return "anonymous"
