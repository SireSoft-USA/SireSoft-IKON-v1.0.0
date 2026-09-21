class ServiceRegistry:
    """
    Deterministic service-instance registry preserving registration order.
    """

    def __init__(self):
        self._instances = {}
        self._service_order = {}
        self._instance_to_service = {}

    def register(self, instance):
        if not isinstance(instance, ServiceInstance):
            raise TypeError(
                "instance must be ServiceInstance"
            )

        if instance.instance_id in self._instance_to_service:
            raise ValueError(
                "duplicate instance_id: "
                + instance.instance_id
            )

        service = instance.service_name

        if service not in self._instances:
            self._instances[service] = {}
            self._service_order[service] = []

        self._instances[service][
            instance.instance_id
        ] = instance

        self._service_order[service].append(
            instance.instance_id
        )

        self._instance_to_service[
            instance.instance_id
        ] = service

        return self

    def deregister(self, instance_id):
        if not isinstance(instance_id, str):
            raise TypeError(
                "instance_id must be str"
            )

        if instance_id not in self._instance_to_service:
            raise KeyError(
                "instance not registered: "
                + instance_id
            )

        service = self._instance_to_service.pop(
            instance_id
        )

        instance = self._instances[
            service
        ].pop(
            instance_id
        )

        new_order = []

        for existing_id in self._service_order[
            service
        ]:
            if existing_id != instance_id:
                new_order.append(
                    existing_id
                )

        self._service_order[
            service
        ] = new_order

        if len(new_order) == 0:
            del self._instances[
                service
            ]
            del self._service_order[
                service
            ]

        return instance

    def get(self, instance_id):
        if instance_id not in self._instance_to_service:
            raise KeyError(
                "instance not registered: "
                + str(instance_id)
            )

        service = self._instance_to_service[
            instance_id
        ]

        return self._instances[
            service
        ][instance_id]

    def instances(
        self,
        service_name,
        available_only=False,
    ):
        if not isinstance(service_name, str):
            raise TypeError(
                "service_name must be str"
            )

        if service_name not in self._instances:
            return []

        result = []

        for instance_id in self._service_order[
            service_name
        ]:
            instance = self._instances[
                service_name
            ][instance_id]

            if (
                not available_only
                or instance.available()
            ):
                result.append(
                    instance
                )

        return result

    def services(self):
        return list(
            self._service_order.keys()
        )

    def count(
        self,
        service_name=None,
        available_only=False,
    ):
        if service_name is not None:
            return len(
                self.instances(
                    service_name,
                    available_only=available_only,
                )
            )

        total = 0

        for service in self.services():
            total += len(
                self.instances(
                    service,
                    available_only=available_only,
                )
            )

        return total

    def mark_healthy(self, instance_id):
        return self.get(
            instance_id
        ).mark_healthy()

    def mark_unhealthy(self, instance_id):
        return self.get(
            instance_id
        ).mark_unhealthy()

    def snapshot(self):
        result = {}

        for service in self.services():
            result[service] = [
                instance.stats()
                for instance in self.instances(
                    service
                )
            ]

        return result
