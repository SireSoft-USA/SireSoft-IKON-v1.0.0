class EventBusConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            EventBusConfig,
        ):
            raise TypeError(
                "config must be EventBusConfig"
            )

        errors = []
        warnings = []

        enabled = (
            config
            .enabled_subscriptions()
        )

        if config.max_history < 10:
            warnings.append({
                "code": (
                    "VERY_SMALL_EVENT_HISTORY"
                ),
                "message": (
                    "Small event history may evict diagnostic events quickly"
                ),
            })

        signature_map = {}

        for item in enabled:
            key = (
                item.mode
                + "\x00"
                + item.topic
                + "\x00"
                + item.handler_key
            )

            if key in signature_map:
                warnings.append({
                    "code": (
                        "DUPLICATE_EVENT_DELIVERY_PATH"
                    ),
                    "subscription_ids": [
                        signature_map[
                            key
                        ],
                        item.subscription_id,
                    ],
                    "message": (
                        "Two enabled subscriptions route the same topic matcher to the same handler key"
                    ),
                })
            else:
                signature_map[
                    key
                ] = (
                    item.subscription_id
                )

            if (
                item.mode == "prefix"
                and item.topic == ""
            ):
                warnings.append({
                    "code": (
                        "GLOBAL_EVENT_SUBSCRIPTION"
                    ),
                    "subscription_id": (
                        item.subscription_id
                    ),
                    "message": (
                        "Empty prefix subscribes to every event topic"
                    ),
                })

        return {
            "valid": (
                len(
                    errors
                )
                == 0
            ),
            "error_count": len(
                errors
            ),
            "warning_count": len(
                warnings
            ),
            "errors": errors,
            "warnings": warnings,
            "enabled_subscription_count": (
                len(
                    enabled
                )
            ),
        }

    def require_valid(
        self,
        config,
    ):
        result = self.validate(
            config
        )

        if not result[
            "valid"
        ]:
            first = result[
                "errors"
            ][0]

            raise ValueError(
                first[
                    "code"
                ]
                + ": "
                + first[
                    "message"
                ]
            )

        return result
