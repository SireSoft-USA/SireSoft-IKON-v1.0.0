def default_load_balancer_config():
    services = (
        "inference_service",
        "retrieval_service",
        "rag_service",
        "guardrail_service",
        "conversation_service",
    )

    instances = []

    for service_name in services:
        stem = service_name.replace(
            "_service",
            "",
        )

        instances.append(
            LoadBalancerInstanceConfig(
                instance_id=(
                    stem + "-local-1"
                ),
                service_name=(
                    service_name
                ),
                handler_key=(
                    service_name
                ),
                max_consecutive_failures=3,
                healthy=True,
                accepting_requests=True,
                enabled=True,
                metadata={
                    "runtime": "local",
                },
            )
        )

    return LoadBalancerConfig(
        strategy="adaptive",
        max_attempts=2,
        instances=instances,
        require_service_redundancy=False,
        metadata={
            "profile": "sirellm",
        },
    )
