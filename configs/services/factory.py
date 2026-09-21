class ServiceBindingFactory:
    def build(self, catalog, handler_provider):
        if not isinstance(catalog, ServiceConfigCatalog):
            raise TypeError(
                "catalog must be ServiceConfigCatalog"
            )

        if not callable(handler_provider):
            raise TypeError(
                "handler_provider must be callable"
            )

        bindings = []

        for definition in catalog.definitions():
            for instance in definition.instances:
                handler = handler_provider(
                    definition.service_name,
                    instance.instance_id,
                )

                if not (
                    callable(handler)
                    or (
                        hasattr(handler, "handle")
                        and callable(handler.handle)
                    )
                ):
                    raise TypeError(
                        "handler_provider returned invalid handler for "
                        + instance.instance_id
                    )

                endpoint = instance.endpoint

                if (
                    endpoint is None
                    and definition.endpoint_template is not None
                ):
                    endpoint = (
                        definition.endpoint_template
                        .replace(
                            "{service}",
                            definition.service_name,
                        )
                        .replace(
                            "{instance}",
                            instance.instance_id,
                        )
                    )

                metadata = self._merge(
                    definition.metadata,
                    instance.metadata,
                )

                metadata[
                    "configured_service_name"
                ] = definition.service_name

                bindings.append(
                    ServiceBinding(
                        instance_id=instance.instance_id,
                        service_name=definition.service_name,
                        handler=handler,
                        endpoint=endpoint,
                        lease_seconds=definition.lease_seconds,
                        metadata=metadata,
                        max_consecutive_failures=(
                            definition.max_consecutive_failures
                        ),
                    )
                )

        return bindings

    def _merge(self, base, override):
        result = self._copy(base)

        for key in override:
            result[key] = self._copy(
                override[key]
            )

        return result

    def _copy(self, value):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, (list, tuple)):
            return [
                self._copy(item)
                for item in value
            ]

        return value
