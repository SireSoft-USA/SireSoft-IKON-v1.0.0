def default_event_bus_config():
    return EventBusConfig(
        max_history=10000,
        subscriptions=[
            EventSubscriptionConfig(
                subscription_id=(
                    "audit-events"
                ),
                topic="audit.",
                handler_key="audit",
                mode="prefix",
                enabled=False,
                required_handler=False,
                metadata={
                    "purpose": (
                        "optional global audit fan-out"
                    ),
                },
            ),
            EventSubscriptionConfig(
                subscription_id=(
                    "model-lifecycle"
                ),
                topic="model.",
                handler_key=(
                    "model_lifecycle"
                ),
                mode="prefix",
                enabled=False,
                required_handler=False,
            ),
            EventSubscriptionConfig(
                subscription_id=(
                    "training-lifecycle"
                ),
                topic="training.",
                handler_key=(
                    "training_lifecycle"
                ),
                mode="prefix",
                enabled=False,
                required_handler=False,
            ),
        ],
        metadata={
            "profile": "sirellm",
        },
    )
