class ServiceDescriptor:
    """
    Discoverable service-instance metadata.

    Network transport is intentionally represented only as an endpoint string.
    The discovery core does not open sockets or assume an HTTP/RPC transport.
    """

    def __init__(
        self,
        instance_id,
        service_name,
        endpoint,
        registered_at,
        lease_seconds=60,
        metadata=None,
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

        if not isinstance(
            endpoint,
            str,
        ) or endpoint == "":
            raise ValueError(
                "endpoint must be non-empty str"
            )

        if (
            not isinstance(
                registered_at,
                int,
            )
            or registered_at < 0
        ):
            raise ValueError(
                "registered_at must be non-negative int"
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
        self.endpoint = endpoint
        self.registered_at = registered_at
        self.last_heartbeat = registered_at
        self.lease_seconds = lease_seconds
        self.metadata = self._copy(
            metadata
        )

        self.healthy = True
        self.enabled = True
        self.local_bound = False

    def stale(
        self,
        now,
    ):
        self._validate_now(
            now
        )

        return (
            int(now)
            >= (
                self.last_heartbeat
                + self.lease_seconds
            )
        )

    def available(
        self,
        now,
    ):
        return (
            self.enabled
            and self.healthy
            and not self.stale(
                now
            )
        )

    def heartbeat(
        self,
        now,
    ):
        self._validate_now(
            now
        )

        if now < self.last_heartbeat:
            raise ValueError(
                "heartbeat time cannot move backwards"
            )

        self.last_heartbeat = int(
            now
        )
        self.healthy = True

        return self

    def mark_healthy(
        self,
    ):
        self.healthy = True
        return self

    def mark_unhealthy(
        self,
    ):
        self.healthy = False
        return self

    def enable(
        self,
    ):
        self.enabled = True
        return self

    def disable(
        self,
    ):
        self.enabled = False
        return self

    def public_dict(
        self,
        now=None,
    ):
        available = None
        stale = None

        if now is not None:
            stale = self.stale(
                now
            )

            available = (
                self.available(
                    now
                )
            )

        return {
            "instance_id": (
                self.instance_id
            ),
            "service_name": (
                self.service_name
            ),
            "endpoint": self.endpoint,
            "registered_at": (
                self.registered_at
            ),
            "last_heartbeat": (
                self.last_heartbeat
            ),
            "lease_seconds": (
                self.lease_seconds
            ),
            "healthy": self.healthy,
            "enabled": self.enabled,
            "stale": stale,
            "available": available,
            "local_bound": (
                self.local_bound
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _validate_now(
        self,
        now,
    ):
        if not isinstance(
            now,
            int,
        ):
            raise TypeError(
                "now must be integer seconds"
            )

        if now < 0:
            raise ValueError(
                "now must be non-negative"
            )

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
