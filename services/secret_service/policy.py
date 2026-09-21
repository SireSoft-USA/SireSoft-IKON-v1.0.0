class SecretAccessPolicy:
    """
    Explicit allow-list policy.

    Admins can read, write, and change policy. Writers can rotate secret
    material. Readers can resolve secret material. The wildcard "*" grants
    the corresponding capability to every principal.
    """

    def __init__(
        self,
        readers=None,
        writers=None,
        admins=None,
    ):
        self.readers = self._normalize(
            readers
        )
        self.writers = self._normalize(
            writers
        )
        self.admins = self._normalize(
            admins
        )

    def can_read(
        self,
        principal_id,
    ):
        self._validate_principal(
            principal_id
        )

        return (
            self._contains(
                self.admins,
                principal_id,
            )
            or self._contains(
                self.readers,
                principal_id,
            )
        )

    def can_write(
        self,
        principal_id,
    ):
        self._validate_principal(
            principal_id
        )

        return (
            self._contains(
                self.admins,
                principal_id,
            )
            or self._contains(
                self.writers,
                principal_id,
            )
        )

    def can_admin(
        self,
        principal_id,
    ):
        self._validate_principal(
            principal_id
        )

        return self._contains(
            self.admins,
            principal_id,
        )

    def replace(
        self,
        readers=None,
        writers=None,
        admins=None,
    ):
        if readers is not None:
            self.readers = self._normalize(
                readers
            )

        if writers is not None:
            self.writers = self._normalize(
                writers
            )

        if admins is not None:
            self.admins = self._normalize(
                admins
            )

        if len(
            self.admins
        ) == 0:
            raise ValueError(
                "secret policy must retain at least one admin"
            )

        return self

    def public_dict(
        self,
    ):
        return {
            "readers": list(
                self.readers
            ),
            "writers": list(
                self.writers
            ),
            "admins": list(
                self.admins
            ),
        }

    @classmethod
    def from_dict(
        cls,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "secret policy state must be dict"
            )

        return cls(
            readers=value.get(
                "readers"
            ),
            writers=value.get(
                "writers"
            ),
            admins=value.get(
                "admins"
            ),
        )

    def _normalize(
        self,
        values,
    ):
        if values is None:
            return []

        if not isinstance(
            values,
            (list, tuple),
        ):
            raise TypeError(
                "policy principals must be list/tuple or None"
            )

        result = []

        for value in values:
            self._validate_principal(
                value
            )

            if value not in result:
                result.append(
                    value
                )

        return result

    def _validate_principal(
        self,
        principal_id,
    ):
        if not isinstance(
            principal_id,
            str,
        ) or principal_id == "":
            raise ValueError(
                "principal_id must be non-empty str"
            )

    def _contains(
        self,
        values,
        principal_id,
    ):
        return (
            "*"
            in values
            or principal_id
            in values
        )
