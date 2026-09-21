class GatewayRouteConfigFactory:
    """
    Converts enabled GatewayRouteConfig records into runtime GatewayRoute
    contracts used by the API gateway/server layers.
    """

    def build(
        self,
        catalog,
        service_catalog=None,
        require_valid=True,
    ):
        if not isinstance(
            catalog,
            GatewayConfigCatalog,
        ):
            raise TypeError(
                "catalog must be GatewayConfigCatalog"
            )

        validator = (
            GatewayConfigValidator()
        )

        if require_valid:
            validator.require_valid(
                catalog,
                service_catalog=(
                    service_catalog
                ),
            )

        routes = []

        for configured in catalog.routes(
            enabled_only=True
        ):
            routes.append(
                GatewayRoute(
                    method=(
                        configured.method
                    ),
                    path=(
                        configured.path
                    ),
                    service=(
                        configured.service
                    ),
                    operation=(
                        configured.operation
                    ),
                    auth_required=(
                        configured
                        .auth_required
                    ),
                    max_payload_bytes=(
                        configured
                        .max_payload_bytes
                    ),
                    tags=(
                        configured.tags
                    ),
                )
            )

        return routes
