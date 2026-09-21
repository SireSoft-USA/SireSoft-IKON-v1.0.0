class AuthService:
    """
    Protocol-facing authentication/authorization service.

    Supported operations:
      create_user
      get_user
      list_users
      authenticate
      verify_token
      revoke_token
      revoke_user_sessions
      change_password
      disable_user
      enable_user
      grant_role
      revoke_role
      authorize
      status
    """

    def __init__(
        self,
        manager,
    ):
        if manager is None or not hasattr(
            manager,
            "authenticate",
        ):
            raise TypeError(
                "manager must provide auth operations"
            )

        self.manager = manager

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

        if request.service != "auth_service":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = request.operation

            if operation == "create_user":
                user = self.manager.create_user(
                    user_id=self._required(
                        request.payload,
                        "user_id",
                    ),
                    username=self._required(
                        request.payload,
                        "username",
                    ),
                    password=self._required(
                        request.payload,
                        "password",
                    ),
                    roles=request.payload.get(
                        "roles"
                    ),
                    metadata=request.payload.get(
                        "metadata"
                    ),
                )

                return self._success(
                    request,
                    {
                        "user": (
                            user.public_dict()
                        ),
                    },
                )

            if operation == "get_user":
                user = self.manager.get_user(
                    self._required(
                        request.payload,
                        "user_id",
                    )
                )

                return self._success(
                    request,
                    {
                        "user": (
                            user.public_dict()
                        ),
                    },
                )

            if operation == "list_users":
                users = self.manager.list_users()

                return self._success(
                    request,
                    {
                        "users": users,
                        "count": len(
                            users
                        ),
                    },
                )

            if operation == "authenticate":
                result = self.manager.authenticate(
                    identifier=self._required(
                        request.payload,
                        "identifier",
                    ),
                    password=self._required(
                        request.payload,
                        "password",
                    ),
                    now=self._required(
                        request.payload,
                        "now",
                    ),
                    ttl_seconds=request.payload.get(
                        "ttl_seconds",
                        3600,
                    ),
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "verify_token":
                principal = (
                    self.manager
                    .verify_token(
                        token=self._required(
                            request.payload,
                            "token",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "principal": (
                            principal
                        ),
                    },
                )

            if operation == "revoke_token":
                session = (
                    self.manager
                    .revoke_token(
                        token=self._required(
                            request.payload,
                            "token",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "session": session,
                    },
                )

            if operation == "revoke_user_sessions":
                result = (
                    self.manager
                    .revoke_user_sessions(
                        self._required(
                            request.payload,
                            "user_id",
                        )
                    )
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "change_password":
                user = (
                    self.manager
                    .change_password(
                        user_id=self._required(
                            request.payload,
                            "user_id",
                        ),
                        current_password=self._required(
                            request.payload,
                            "current_password",
                        ),
                        new_password=self._required(
                            request.payload,
                            "new_password",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "user": user,
                    },
                )

            if operation == "disable_user":
                user = (
                    self.manager
                    .disable_user(
                        self._required(
                            request.payload,
                            "user_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "user": user,
                    },
                )

            if operation == "enable_user":
                user = (
                    self.manager
                    .enable_user(
                        self._required(
                            request.payload,
                            "user_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "user": user,
                    },
                )

            if operation == "grant_role":
                user = (
                    self.manager
                    .grant_role(
                        self._required(
                            request.payload,
                            "user_id",
                        ),
                        self._required(
                            request.payload,
                            "role",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "user": user,
                    },
                )

            if operation == "revoke_role":
                user = (
                    self.manager
                    .revoke_role(
                        self._required(
                            request.payload,
                            "user_id",
                        ),
                        self._required(
                            request.payload,
                            "role",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "user": user,
                    },
                )

            if operation == "authorize":
                result = (
                    self.manager
                    .authorize(
                        principal=self._required(
                            request.payload,
                            "principal",
                        ),
                        permission=self._required(
                            request.payload,
                            "permission",
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "authorization": (
                            result
                        ),
                    },
                )

            if operation == "status":
                return self._success(
                    request,
                    {
                        "status": (
                            self.manager
                            .status()
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                (
                    "Unsupported auth service operation"
                ),
            )

        except KeyError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(error),
            )

        except PermissionError as error:
            return self._error(
                request,
                "UNAUTHENTICATED",
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


def build_auth_manager(
    server_secret,
    password_iterations=4096,
):
    return AuthManager(
        server_secret=server_secret,
        password_iterations=(
            password_iterations
        ),
    )
