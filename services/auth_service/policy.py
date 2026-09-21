class PermissionPolicy:
    """
    Transparent role/permission mapping.

    Permissions are simple strings such as:
      chat:use
      retrieval:search
      monitoring:read
      model:manage
    """

    DEFAULT_ROLES = {
        "user": [
            "chat:use",
        ],
        "developer": [
            "chat:use",
            "inference:use",
            "retrieval:search",
            "embedding:use",
        ],
        "operator": [
            "monitoring:read",
            "model:manage",
            "training:manage",
        ],
        "admin": [
            "*",
        ],
    }

    def __init__(
        self,
        roles=None,
    ):
        if roles is None:
            roles = self.DEFAULT_ROLES

        if not isinstance(
            roles,
            dict,
        ):
            raise TypeError(
                "roles must be dict or None"
            )

        self._roles = {}

        for role in roles:
            self.set_role(
                role,
                roles[
                    role
                ],
            )

    def set_role(
        self,
        role,
        permissions,
    ):
        if not isinstance(
            role,
            str,
        ) or role == "":
            raise ValueError(
                "role must be non-empty str"
            )

        if not isinstance(
            permissions,
            (list, tuple),
        ):
            raise TypeError(
                "permissions must be list/tuple"
            )

        normalized = []

        for permission in permissions:
            if not isinstance(
                permission,
                str,
            ) or permission == "":
                raise ValueError(
                    "permissions must be non-empty strings"
                )

            if permission not in normalized:
                normalized.append(
                    permission
                )

        self._roles[
            role
        ] = normalized

        return self

    def role_exists(
        self,
        role,
    ):
        return role in self._roles

    def permissions_for_roles(
        self,
        roles,
    ):
        result = []

        for role in roles:
            if role not in self._roles:
                continue

            for permission in self._roles[
                role
            ]:
                if permission not in result:
                    result.append(
                        permission
                    )

        return result

    def allowed(
        self,
        roles,
        permission,
    ):
        if not isinstance(
            permission,
            str,
        ) or permission == "":
            raise ValueError(
                "permission must be non-empty str"
            )

        permissions = self.permissions_for_roles(
            roles
        )

        return (
            "*"
            in permissions
            or permission
            in permissions
        )

    def to_dict(
        self,
    ):
        result = {}

        keys = list(
            self._roles.keys()
        )

        keys.sort()

        for role in keys:
            result[
                role
            ] = list(
                self._roles[
                    role
                ]
            )

        return result
