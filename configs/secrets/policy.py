class SecretPolicyConfig:
    """
    Serializable ACL configuration. No secret material is stored here.
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

    def to_dict(
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
            if not isinstance(
                value,
                str,
            ) or value == "":
                raise ValueError(
                    "policy principals must be non-empty strings"
                )

            if value not in result:
                result.append(
                    value
                )

        return result
