class GatewayRouteConfig:
    """
    Serializable public-route configuration.

    Runtime GatewayRoute objects are created later by GatewayRouteConfigFactory.
    """

    def __init__(
        self,
        method,
        path,
        service,
        operation,
        auth_required=False,
        max_payload_bytes=None,
        tags=None,
        enabled=True,
        metadata=None,
    ):
        if not isinstance(
            method,
            str,
        ) or method.strip() == "":
            raise ValueError(
                "method must be non-empty str"
            )

        if not isinstance(
            path,
            str,
        ) or not path.startswith(
            "/"
        ):
            raise ValueError(
                "path must start with /"
            )

        if not isinstance(
            service,
            str,
        ) or service.strip() == "":
            raise ValueError(
                "service must be non-empty str"
            )

        if not isinstance(
            operation,
            str,
        ) or operation.strip() == "":
            raise ValueError(
                "operation must be non-empty str"
            )

        if max_payload_bytes is not None and (
            not isinstance(
                max_payload_bytes,
                int,
            )
            or max_payload_bytes <= 0
        ):
            raise ValueError(
                "max_payload_bytes must be positive int or None"
            )

        if tags is None:
            tags = []

        if not isinstance(
            tags,
            (list, tuple),
        ):
            raise TypeError(
                "tags must be list/tuple or None"
            )

        normalized_tags = []
        seen_tags = {}

        for tag in tags:
            if not isinstance(
                tag,
                str,
            ) or tag == "":
                raise ValueError(
                    "route tags must be non-empty strings"
                )

            if tag not in seen_tags:
                seen_tags[
                    tag
                ] = True
                normalized_tags.append(
                    tag
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

        self.method = method.upper()
        self.path = path
        self.service = service
        self.operation = operation
        self.auth_required = bool(
            auth_required
        )
        self.max_payload_bytes = (
            max_payload_bytes
        )
        self.tags = normalized_tags
        self.enabled = bool(
            enabled
        )
        self.metadata = self._copy(
            metadata
        )

    def key(
        self,
    ):
        return (
            self.method
            + " "
            + self.path
        )

    def to_dict(
        self,
    ):
        return {
            "method": self.method,
            "path": self.path,
            "service": self.service,
            "operation": self.operation,
            "auth_required": (
                self.auth_required
            ),
            "max_payload_bytes": (
                self.max_payload_bytes
            ),
            "tags": list(
                self.tags
            ),
            "enabled": self.enabled,
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
