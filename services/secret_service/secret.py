class SecretVersion:
    STATES = (
        "active",
        "retired",
        "destroyed",
    )

    def __init__(
        self,
        version,
        value,
        created_at,
        created_by,
        metadata=None,
    ):
        if (
            not isinstance(
                version,
                int,
            )
            or version <= 0
        ):
            raise ValueError(
                "secret version must be positive int"
            )

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "secret value must be str"
            )

        if value == "":
            raise ValueError(
                "secret value must not be empty"
            )

        if (
            not isinstance(
                created_at,
                int,
            )
            or created_at < 0
        ):
            raise ValueError(
                "created_at must be non-negative int"
            )

        if not isinstance(
            created_by,
            str,
        ) or created_by == "":
            raise ValueError(
                "created_by must be non-empty str"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.version = version
        self._value = value
        self.created_at = created_at
        self.created_by = created_by
        self.metadata = self._copy(
            metadata
        )
        self.state = "active"

    def reveal(
        self,
    ):
        if self.state == "destroyed":
            raise RuntimeError(
                "secret version has been destroyed"
            )

        return self._value

    def retire(
        self,
    ):
        if self.state == "destroyed":
            raise RuntimeError(
                "destroyed secret version cannot be retired"
            )

        self.state = "retired"

        return self

    def destroy(
        self,
    ):
        self._value = None
        self.state = "destroyed"

        return self

    def public_dict(
        self,
    ):
        return {
            "version": self.version,
            "created_at": (
                self.created_at
            ),
            "created_by": (
                self.created_by
            ),
            "metadata": self._copy(
                self.metadata
            ),
            "state": self.state,
            "value": "[REDACTED]",
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


class SecretRecord:
    """
    In-memory versioned secret record.

    Secret material is intentionally excluded from public_dict() and from every
    export surface in this service.
    """

    def __init__(
        self,
        secret_id,
        value,
        created_at,
        created_by,
        policy,
        metadata=None,
    ):
        if not isinstance(
            secret_id,
            str,
        ) or secret_id == "":
            raise ValueError(
                "secret_id must be non-empty str"
            )

        if not isinstance(
            policy,
            SecretAccessPolicy,
        ):
            raise TypeError(
                "policy must be SecretAccessPolicy"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.secret_id = secret_id
        self.policy = policy
        self.metadata = self._copy(
            metadata
        )

        self.enabled = True
        self.destroyed = False
        self.access_count = 0
        self.rotation_count = 0

        self._versions = []
        self._current_version = None

        self.rotate(
            value=value,
            created_at=created_at,
            created_by=created_by,
            metadata={
                "initial": True,
            },
        )

        self.rotation_count = 0

    def rotate(
        self,
        value,
        created_at,
        created_by,
        metadata=None,
    ):
        if self.destroyed:
            raise RuntimeError(
                "destroyed secret cannot be rotated"
            )

        if self._current_version is not None:
            self._current_version.retire()

        version = SecretVersion(
            version=(
                len(
                    self._versions
                )
                + 1
            ),
            value=value,
            created_at=created_at,
            created_by=created_by,
            metadata=metadata,
        )

        self._versions.append(
            version
        )

        self._current_version = (
            version
        )

        self.rotation_count += 1

        return version

    def resolve(
        self,
        version=None,
    ):
        if self.destroyed:
            raise RuntimeError(
                "secret has been destroyed"
            )

        if not self.enabled:
            raise RuntimeError(
                "secret is disabled"
            )

        target = (
            self._current_version
            if version is None
            else self.get_version(
                version
            )
        )

        self.access_count += 1

        return target.reveal()

    def get_version(
        self,
        version,
    ):
        if (
            not isinstance(
                version,
                int,
            )
            or version <= 0
        ):
            raise ValueError(
                "version must be positive int"
            )

        for item in self._versions:
            if item.version == version:
                return item

        raise KeyError(
            "secret version not found: "
            + str(
                version
            )
        )

    def disable(
        self,
    ):
        if self.destroyed:
            raise RuntimeError(
                "destroyed secret cannot be disabled"
            )

        self.enabled = False

        return self

    def enable(
        self,
    ):
        if self.destroyed:
            raise RuntimeError(
                "destroyed secret cannot be enabled"
            )

        self.enabled = True

        return self

    def destroy(
        self,
    ):
        for version in self._versions:
            version.destroy()

        self._current_version = None
        self.enabled = False
        self.destroyed = True

        return self

    def public_dict(
        self,
    ):
        return {
            "secret_id": (
                self.secret_id
            ),
            "enabled": (
                self.enabled
            ),
            "destroyed": (
                self.destroyed
            ),
            "current_version": (
                None
                if self._current_version
                is None
                else self._current_version
                .version
            ),
            "version_count": len(
                self._versions
            ),
            "rotation_count": (
                self.rotation_count
            ),
            "access_count": (
                self.access_count
            ),
            "policy": (
                self.policy
                .public_dict()
            ),
            "metadata": self._copy(
                self.metadata
            ),
            "versions": [
                version.public_dict()
                for version
                in self._versions
            ],
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
