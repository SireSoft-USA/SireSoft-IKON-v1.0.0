class AuthConfig:
    """
    Authentication configuration intentionally excludes server secrets.

    Secret material is injected into AuthConfigFactory at composition time.
    """

    def __init__(
        self,
        roles,
        password_iterations=4096,
        min_password_length=8,
        max_failed_attempts=5,
        default_session_ttl_seconds=3600,
        permission_by_route=None,
        metadata=None,
    ):
        if not isinstance(
            roles,
            (list, tuple),
        ) or len(
            roles
        ) == 0:
            raise ValueError(
                "roles must be non-empty list/tuple"
            )

        for field_name, value in (
            (
                "password_iterations",
                password_iterations,
            ),
            (
                "min_password_length",
                min_password_length,
            ),
            (
                "max_failed_attempts",
                max_failed_attempts,
            ),
            (
                "default_session_ttl_seconds",
                default_session_ttl_seconds,
            ),
        ):
            if (
                not isinstance(
                    value,
                    int,
                )
                or value <= 0
            ):
                raise ValueError(
                    field_name
                    + " must be positive int"
                )

        normalized_roles = []
        seen_roles = {}

        for role in roles:
            if not isinstance(
                role,
                AuthRoleConfig,
            ):
                raise TypeError(
                    "roles entries must be AuthRoleConfig"
                )

            if role.role in seen_roles:
                raise ValueError(
                    "duplicate auth role: "
                    + role.role
                )

            seen_roles[
                role.role
            ] = True
            normalized_roles.append(
                role
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

        normalized_routes = {}

        for route_key in permission_by_route:
            permission = (
                permission_by_route[
                    route_key
                ]
            )

            if (
                not isinstance(
                    route_key,
                    str,
                )
                or route_key == ""
            ):
                raise ValueError(
                    "route permission keys must be non-empty strings"
                )

            if (
                not isinstance(
                    permission,
                    str,
                )
                or permission == ""
            ):
                raise ValueError(
                    "route permissions must be non-empty strings"
                )

            normalized_routes[
                route_key
            ] = permission

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.roles = normalized_roles
        self.password_iterations = (
            password_iterations
        )
        self.min_password_length = (
            min_password_length
        )
        self.max_failed_attempts = (
            max_failed_attempts
        )
        self.default_session_ttl_seconds = (
            default_session_ttl_seconds
        )
        self.permission_by_route = (
            normalized_routes
        )
        self.metadata = self._copy(
            metadata
        )

    def role_map(
        self,
    ):
        return {
            role.role: list(
                role.permissions
            )
            for role
            in self.roles
        }

    def to_dict(
        self,
    ):
        return {
            "roles": [
                role.to_dict()
                for role
                in self.roles
            ],
            "password_iterations": (
                self.password_iterations
            ),
            "min_password_length": (
                self.min_password_length
            ),
            "max_failed_attempts": (
                self.max_failed_attempts
            ),
            "default_session_ttl_seconds": (
                self.default_session_ttl_seconds
            ),
            "permission_by_route": dict(
                self.permission_by_route
            ),
            "metadata": self._copy(
                self.metadata
            ),
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
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
