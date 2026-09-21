class LoadBalancer:
    """
    Protocol-aware internal service load balancer.

    It accepts ServiceRequest, selects a healthy service instance, invokes its
    handler, tracks load/health, and can retry on a different instance after a
    handler failure.

    Networking/service discovery are separate concerns; this class is the
    deterministic balancing core used by the later runtime layer.
    """

    def __init__(
        self,
        registry=None,
        strategy=None,
        max_attempts=2,
    ):
        if (
            not isinstance(max_attempts, int)
            or max_attempts <= 0
        ):
            raise ValueError(
                "max_attempts must be positive int"
            )

        self.registry = (
            ServiceRegistry()
            if registry is None
            else registry
        )

        self.strategy = (
            RoundRobinStrategy()
            if strategy is None
            else strategy
        )

        if not hasattr(
            self.strategy,
            "select",
        ):
            raise TypeError(
                "strategy must provide select()"
            )

        self.max_attempts = max_attempts

    def register(self, instance):
        self.registry.register(
            instance
        )
        return self

    def deregister(self, instance_id):
        return self.registry.deregister(
            instance_id
        )

    def select(
        self,
        service_name,
        excluded_ids=None,
    ):
        instances = self.registry.instances(
            service_name,
            available_only=False,
        )

        return self.strategy.select(
            service_name,
            instances,
            excluded_ids=excluded_ids,
        )

    def dispatch(self, request):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        instances = self.registry.instances(
            request.service,
            available_only=False,
        )

        if len(instances) == 0:
            return ServiceResponse.error_response(
                request,
                ProtocolError(
                    code="SERVICE_UNAVAILABLE",
                    message=(
                        "No instances are registered for service "
                        + request.service
                    ),
                    details={
                        "service": request.service,
                    },
                    retryable=True,
                ),
            )

        excluded = {}
        attempt = 0
        failures = []

        while attempt < self.max_attempts:
            instance = self.strategy.select(
                request.service,
                instances,
                excluded_ids=excluded,
            )

            if instance is None:
                break

            excluded[
                instance.instance_id
            ] = True

            attempt += 1
            instance.begin_request()

            try:
                response = instance.handler(
                    request
                )

                if not isinstance(
                    response,
                    ServiceResponse,
                ):
                    raise TypeError(
                        "service handler must return ServiceResponse"
                    )

                instance.finish_success()

                response.metadata[
                    "load_balancer_instance_id"
                ] = instance.instance_id

                response.metadata[
                    "load_balancer_attempt"
                ] = attempt

                return response

            except Exception as error:
                instance.finish_failure()

                failures.append({
                    "instance_id": instance.instance_id,
                    "error_type": type(
                        error
                    ).__name__,
                    "message": str(
                        error
                    ),
                })

        return ServiceResponse.error_response(
            request,
            ProtocolError(
                code="SERVICE_INSTANCE_FAILURE",
                message=(
                    "All attempted service instances failed or were unavailable"
                ),
                details={
                    "service": request.service,
                    "attempts": attempt,
                    "failures": failures,
                },
                retryable=True,
            ),
            metadata={
                "load_balancer_attempts": attempt,
            },
        )

    def health_snapshot(self):
        return self.registry.snapshot()
