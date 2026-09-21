class AuthRoleConfig:
    def __init__(
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
        seen = {}

        for permission in permissions:
            if (
                not isinstance(
                    permission,
                    str,
                )
                or permission == ""
            ):
                raise ValueError(
                    "permissions must be non-empty strings"
                )

            if permission not in seen:
                seen[
                    permission
                ] = True
                normalized.append(
                    permission
                )

        self.role = role
        self.permissions = normalized

    def to_dict(
        self,
    ):
        return {
            "role": self.role,
            "permissions": list(
                self.permissions
            ),
        }
