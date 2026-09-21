class ServiceConfigCatalog:
    def __init__(self):
        self._definitions = {}
        self._order = []

    def add(self, definition):
        if not isinstance(definition, ServiceDefinition):
            raise TypeError("definition must be ServiceDefinition")

        name = definition.service_name

        if name in self._definitions:
            raise ValueError(
                "duplicate service definition: " + name
            )

        self._definitions[name] = definition
        self._order.append(name)

        return definition

    def get(self, service_name):
        if service_name not in self._definitions:
            raise KeyError(
                "service definition not found: "
                + str(service_name)
            )

        return self._definitions[service_name]

    def services(self):
        return list(self._order)

    def definitions(self):
        return [
            self._definitions[name]
            for name in self._order
        ]

    def instance_count(self):
        total = 0

        for definition in self.definitions():
            total += len(definition.instances)

        return total

    def to_dict(self):
        return {
            "service_count": len(self._order),
            "instance_count": self.instance_count(),
            "services": [
                definition.to_dict()
                for definition in self.definitions()
            ],
        }
