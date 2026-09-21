class HostBindingRegistry:
    """
    Deterministic registry of configured local service bindings.
    """

    def __init__(
        self,
    ):
        self._bindings = {}
        self._order = []
        self._service_order = {}

    def add(
        self,
        binding,
    ):
        if not isinstance(
            binding,
            ServiceBinding,
        ):
            raise TypeError(
                "binding must be ServiceBinding"
            )

        if (
            binding.instance_id
            in self._bindings
        ):
            raise ValueError(
                "duplicate host instance_id: "
                + binding.instance_id
            )

        self._bindings[
            binding.instance_id
        ] = binding

        self._order.append(
            binding.instance_id
        )

        if (
            binding.service_name
            not in self._service_order
        ):
            self._service_order[
                binding.service_name
            ] = []

        self._service_order[
            binding.service_name
        ].append(
            binding.instance_id
        )

        return binding

    def get(
        self,
        instance_id,
    ):
        if (
            instance_id
            not in self._bindings
        ):
            raise KeyError(
                "host binding not found: "
                + str(
                    instance_id
                )
            )

        return self._bindings[
            instance_id
        ]

    def bindings(
        self,
    ):
        return [
            self._bindings[
                instance_id
            ]
            for instance_id
            in self._order
        ]

    def instances(
        self,
        service_name,
    ):
        if (
            service_name
            not in self._service_order
        ):
            return []

        return [
            self._bindings[
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
            self._service_order
            .keys()
        )

    def count(
        self,
    ):
        return len(
            self._order
        )
