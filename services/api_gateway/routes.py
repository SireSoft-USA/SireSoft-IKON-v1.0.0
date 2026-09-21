def default_gateway_routes():
    """
    Initial public SireLLM API surface.

    These are contracts only; their target services are built in later folders.
    """
    return [
        GatewayRoute(
            "POST",
            "/v1/chat",
            "rag_service",
            "answer",
            auth_required=False,
            max_payload_bytes=65536,
            tags=["chat", "rag"],
        ),
        GatewayRoute(
            "POST",
            "/v1/generate",
            "inference_service",
            "generate",
            auth_required=True,
            max_payload_bytes=65536,
            tags=["inference"],
        ),
        GatewayRoute(
            "POST",
            "/v1/retrieve",
            "retrieval_service",
            "search",
            auth_required=True,
            max_payload_bytes=65536,
            tags=["retrieval"],
        ),
        GatewayRoute(
            "POST",
            "/v1/embed",
            "embedding_service",
            "embed",
            auth_required=True,
            max_payload_bytes=65536,
            tags=["embedding"],
        ),
        GatewayRoute(
            "GET",
            "/v1/health",
            "monitoring_service",
            "health",
            auth_required=False,
            max_payload_bytes=1024,
            tags=["health"],
        ),
    ]


def build_default_router():
    router = GatewayRouter()

    for route in default_gateway_routes():
        router.add(
            route
        )

    return router
