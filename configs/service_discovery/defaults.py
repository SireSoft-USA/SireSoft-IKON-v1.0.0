def default_service_discovery_config():
    """
    Local runtime discovery topology for SireLLM's core request path.
    """

    names = [
        "inference_service",
        "retrieval_service",
        "rag_service",
        "guardrail_service",
        "conversation_service",
    ]

    instances = []

    for name in names:
        instance_id = (
            name
            .replace(
                "_service",
                "",
            )
            + "-local-1"
        )

        instances.append(
            DiscoveryInstanceConfig(
                instance_id=instance_id,
                service_name=name,
                endpoint=(
                    "local://"
                    + name
                    + "/"
                    + instance_id
                ),
                lease_seconds=60,
                local_handler_key=name,
                max_consecutive_failures=3,
                enabled=True,
                metadata={
                    "runtime": "local",
                },
            )
        )

    return ServiceDiscoveryConfig(
        instances=instances,
        attach_load_balancer=True,
        metadata={
            "profile": "sirellm",
        },
    )
