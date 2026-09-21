class PasswordRecord:
    def __init__(
        self,
        salt_hex,
        digest_hex,
        iterations,
        version=1,
    ):
        if not isinstance(
            salt_hex,
            str,
        ) or salt_hex == "":
            raise ValueError(
                "salt_hex must be non-empty str"
            )

        if not isinstance(
            digest_hex,
            str,
        ) or digest_hex == "":
            raise ValueError(
                "digest_hex must be non-empty str"
            )

        if (
            not isinstance(
                iterations,
                int,
            )
            or iterations <= 0
        ):
            raise ValueError(
                "iterations must be positive int"
            )

        self.salt_hex = salt_hex
        self.digest_hex = digest_hex
        self.iterations = iterations
        self.version = int(
            version
        )

    def to_private_dict(
        self,
    ):
        return {
            "salt_hex": (
                self.salt_hex
            ),
            "digest_hex": (
                self.digest_hex
            ),
            "iterations": (
                self.iterations
            ),
            "version": (
                self.version
            ),
        }


class UserAccount:
    VALID_STATUSES = (
        "active",
        "disabled",
        "locked",
    )

    def __init__(
        self,
        user_id,
        username,
        password_record,
        roles=None,
        metadata=None,
        status="active",
    ):
        if not isinstance(
            user_id,
            str,
        ) or user_id == "":
            raise ValueError(
                "user_id must be non-empty str"
            )

        if not isinstance(
            username,
            str,
        ) or username == "":
            raise ValueError(
                "username must be non-empty str"
            )

        if not isinstance(
            password_record,
            PasswordRecord,
        ):
            raise TypeError(
                "password_record must be PasswordRecord"
            )

        if roles is None:
            roles = [
                "user",
            ]

        if metadata is None:
            metadata = {}

        if not isinstance(
            roles,
            (list, tuple),
        ):
            raise TypeError(
                "roles must be list/tuple or None"
            )

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        if status not in self.VALID_STATUSES:
            raise ValueError(
                "invalid user status"
            )

        normalized_roles = []

        for role in roles:
            if not isinstance(
                role,
                str,
            ) or role == "":
                raise ValueError(
                    "role names must be non-empty strings"
                )

            if role not in normalized_roles:
                normalized_roles.append(
                    role
                )

        self.user_id = user_id
        self.username = username
        self.password_record = (
            password_record
        )
        self.roles = normalized_roles
        self.metadata = self._copy(
            metadata
        )
        self.status = status
        self.failed_attempts = 0
        self.credential_version = 1

    def active(
        self,
    ):
        return self.status == "active"

    def disable(
        self,
    ):
        self.status = "disabled"
        return self

    def enable(
        self,
    ):
        self.status = "active"
        self.failed_attempts = 0
        return self

    def lock(
        self,
    ):
        self.status = "locked"
        return self

    def public_dict(
        self,
    ):
        return {
            "user_id": (
                self.user_id
            ),
            "username": (
                self.username
            ),
            "roles": list(
                self.roles
            ),
            "metadata": self._copy(
                self.metadata
            ),
            "status": self.status,
            "failed_attempts": (
                self.failed_attempts
            ),
            "credential_version": (
                self.credential_version
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
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
