class GatewayRoute:
    """
    Public API route -> internal service/operation mapping.
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
    ):
        if not isinstance(method, str) or method.strip() == "":
            raise ValueError("method must be non-empty str")

        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError("path must start with /")

        if not isinstance(service, str) or service.strip() == "":
            raise ValueError("service must be non-empty str")

        if not isinstance(operation, str) or operation.strip() == "":
            raise ValueError("operation must be non-empty str")

        if max_payload_bytes is not None:
            if (
                not isinstance(max_payload_bytes, int)
                or max_payload_bytes <= 0
            ):
                raise ValueError(
                    "max_payload_bytes must be positive int or None"
                )

        if tags is None:
            tags = []

        if not isinstance(tags, (list, tuple)):
            raise TypeError("tags must be list/tuple or None")

        self.method = method.upper()
        self.path = path
        self.service = service
        self.operation = operation
        self.auth_required = bool(auth_required)
        self.max_payload_bytes = max_payload_bytes
        self.tags = list(tags)

    def key(self):
        return (
            self.method
            + " "
            + self.path
        )

    def to_dict(self):
        return {
            "method": self.method,
            "path": self.path,
            "service": self.service,
            "operation": self.operation,
            "auth_required": self.auth_required,
            "max_payload_bytes": self.max_payload_bytes,
            "tags": list(self.tags),
        }
