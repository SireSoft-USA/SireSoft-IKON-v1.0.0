class AuthConfigCodec:
    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(
        self,
        text,
    ):
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "auth config text must be str"
            )

        return self.from_dict(
            self.parser.parse(
                text
            )
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "auth config root must be object"
            )

        raw_roles = value.get(
            "roles"
        )

        if not isinstance(
            raw_roles,
            dict,
        ) or len(
            raw_roles
        ) == 0:
            raise ValueError(
                "roles must be non-empty object"
            )

        roles = []

        role_names = list(
            raw_roles.keys()
        )
        role_names.sort()

        for role_name in role_names:
            roles.append(
                AuthRoleConfig(
                    role=role_name,
                    permissions=(
                        raw_roles[
                            role_name
                        ]
                    ),
                )
            )

        return AuthConfig(
            roles=roles,
            password_iterations=value.get(
                "password_iterations",
                4096,
            ),
            min_password_length=value.get(
                "min_password_length",
                8,
            ),
            max_failed_attempts=value.get(
                "max_failed_attempts",
                5,
            ),
            default_session_ttl_seconds=(
                value.get(
                    "default_session_ttl_seconds",
                    3600,
                )
            ),
            permission_by_route=value.get(
                "permission_by_route",
                {},
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
