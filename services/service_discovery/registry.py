class DiscoveryRegistry:
    """
    Deterministic service-discovery registry preserving registration order.
    """

    def __init__(
        self,
    ):
        self._descriptors = {}
        self._service_order = {}
        self._instance_to_service = {}

    def register(
        self,
        descriptor,
    ):
        if not isinstance(
            descriptor,
            ServiceDescriptor,
        ):
            raise TypeError(
                "descriptor must be ServiceDescriptor"
            )

        if descriptor.instance_id in self._instance_to_service:
            raise ValueError(
                "duplicate discovery instance_id: "
                + descriptor.instance_id
            )

        service_name = (
            descriptor.service_name
        )

        if service_name not in self._descriptors:
            self._descriptors[
                service_name
            ] = {}

            self._service_order[
                service_name
            ] = []

        self._descriptors[
            service_name
        ][
            descriptor.instance_id
        ] = descriptor

        self._service_order[
            service_name
        ].append(
            descriptor.instance_id
        )

        self._instance_to_service[
            descriptor.instance_id
        ] = service_name

        return descriptor

    def deregister(
        self,
        instance_id,
    ):
        descriptor = self.get(
            instance_id
        )

        service_name = (
            descriptor.service_name
        )

        del self._descriptors[
            service_name
        ][
            instance_id
        ]

        del self._instance_to_service[
            instance_id
        ]

        self._service_order[
            service_name
        ] = [
            existing
            for existing
            in self._service_order[
                service_name
            ]
            if existing != instance_id
        ]

        if len(
            self._service_order[
                service_name
            ]
        ) == 0:
            del self._service_order[
                service_name
            ]

            del self._descriptors[
                service_name
            ]

        return descriptor

    def get(
        self,
        instance_id,
    ):
        if instance_id not in self._instance_to_service:
            raise KeyError(
                "discovery instance not found: "
                + str(
                    instance_id
                )
            )

        service_name = (
            self._instance_to_service[
                instance_id
            ]
        )

        return self._descriptors[
            service_name
        ][
            instance_id
        ]

    def instances(
        self,
        service_name,
    ):
        if not isinstance(
            service_name,
            str,
        ):
            raise TypeError(
                "service_name must be str"
            )

        if service_name not in self._descriptors:
            return []

        return [
            self._descriptors[
                service_name
            ][
                instance_id
            ]
            for instance_id
            in self._service_order[
                service_name
            ]
        ]

    def services(
        self,
    ):
        return list(
            self._service_order.keys()
        )

    def count(
        self,
        service_name=None,
    ):
        if service_name is not None:
            return len(
                self.instances(
                    service_name
                )
            )

        total = 0

        for name in self.services():
            total += len(
                self.instances(
                    name
                )
            )

        return total
