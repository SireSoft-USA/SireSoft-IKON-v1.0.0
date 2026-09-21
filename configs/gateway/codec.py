class GatewayConfigCodec:
    """
    Decodes gateway route configuration through the handwritten JSON parser.
    """

    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(
        self,
        text,
    ):
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "gateway config text must be str"
            )

        return self.from_dict(
            self.parser.parse(
                text
            )
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "gateway config root must be object"
            )

        raw_routes = value.get(
            "routes"
        )

        if not isinstance(
            raw_routes,
            list,
        ):
            raise ValueError(
                "routes must be list"
            )

        catalog = (
            GatewayConfigCatalog()
        )

        for raw in raw_routes:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "gateway route entry must be object"
                )

            catalog.add(
                GatewayRouteConfig(
                    method=raw.get(
                        "method"
                    ),
                    path=raw.get(
                        "path"
                    ),
                    service=raw.get(
                        "service"
                    ),
                    operation=raw.get(
                        "operation"
                    ),
                    auth_required=raw.get(
                        "auth_required",
                        False,
                    ),
                    max_payload_bytes=(
                        raw.get(
                            "max_payload_bytes"
                        )
                    ),
                    tags=raw.get(
                        "tags",
                        [],
                    ),
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return catalog
