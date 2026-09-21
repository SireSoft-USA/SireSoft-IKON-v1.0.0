class ServiceBinding:
    """
    Declarative local service-instance binding for the runtime host.

    The handler may be a callable(request) or an object exposing handle().
    """

    def __init__(
        self,
        instance_id,
        service_name,
        handler,
        endpoint=None,
        lease_seconds=60,
        metadata=None,
        max_consecutive_failures=3,
    ):
        if not isinstance(
            instance_id,
            str,
        ) or instance_id == "":
            raise ValueError(
                "instance_id must be non-empty str"
            )

        if not isinstance(
            service_name,
            str,
        ) or service_name == "":
            raise ValueError(
                "service_name must be non-empty str"
            )

        resolved = None

        if callable(
            handler
        ):
            resolved = handler

        elif (
            hasattr(
                handler,
                "handle",
            )
            and callable(
                handler.handle
            )
        ):
            resolved = (
                handler.handle
            )

        else:
            raise TypeError(
                "handler must be callable or expose handle()"
            )

        if endpoint is None:
            endpoint = (
                "local://"
                + service_name
                + "/"
                + instance_id
            )

        if not isinstance(
            endpoint,
            str,
        ) or endpoint == "":
            raise ValueError(
                "endpoint must be non-empty str"
            )

        if (
            not isinstance(
                lease_seconds,
                int,
            )
            or lease_seconds <= 0
        ):
            raise ValueError(
                "lease_seconds must be positive int"
            )

        if (
            not isinstance(
                max_consecutive_failures,
                int,
            )
            or max_consecutive_failures <= 0
        ):
            raise ValueError(
                "max_consecutive_failures must be positive int"
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

        self.instance_id = instance_id
        self.service_name = service_name
        self.handler = resolved
        self.endpoint = endpoint
        self.lease_seconds = lease_seconds
        self.metadata = self._copy(
            metadata
        )
        self.max_consecutive_failures = (
            max_consecutive_failures
        )

    def public_dict(
        self,
    ):
        return {
            "instance_id": (
                self.instance_id
            ),
            "service_name": (
                self.service_name
            ),
            "endpoint": (
                self.endpoint
            ),
            "lease_seconds": (
                self.lease_seconds
            ),
            "max_consecutive_failures": (
                self.max_consecutive_failures
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
