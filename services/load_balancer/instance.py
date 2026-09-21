class ServiceInstance:
    """
    One registered service instance.

    Health is deterministic and local to the load-balancer core. Time-based
    probes/recovery belong in monitoring/runtime layers later.
    """

    def __init__(
        self,
        instance_id,
        service_name,
        handler,
        metadata=None,
        max_consecutive_failures=3,
    ):
        if not isinstance(instance_id, str) or instance_id == "":
            raise ValueError("instance_id must be non-empty str")

        if not isinstance(service_name, str) or service_name == "":
            raise ValueError("service_name must be non-empty str")

        if not callable(handler):
            raise TypeError("handler must be callable")

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        if (
            not isinstance(max_consecutive_failures, int)
            or max_consecutive_failures <= 0
        ):
            raise ValueError(
                "max_consecutive_failures must be positive int"
            )

        self.instance_id = instance_id
        self.service_name = service_name
        self.handler = handler
        self.metadata = dict(metadata)
        self.max_consecutive_failures = max_consecutive_failures

        self.healthy = True
        self.accepting_requests = True
        self.active_requests = 0
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.consecutive_failures = 0

    def available(self):
        return (
            self.healthy
            and self.accepting_requests
        )

    def begin_request(self):
        if not self.available():
            raise RuntimeError(
                "service instance is not available"
            )

        self.active_requests += 1
        self.total_requests += 1
        return self

    def finish_success(self):
        if self.active_requests <= 0:
            raise RuntimeError(
                "no active request to finish"
            )

        self.active_requests -= 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        return self

    def finish_failure(self):
        if self.active_requests <= 0:
            raise RuntimeError(
                "no active request to finish"
            )

        self.active_requests -= 1
        self.failed_requests += 1
        self.consecutive_failures += 1

        if (
            self.consecutive_failures
            >= self.max_consecutive_failures
        ):
            self.healthy = False

        return self

    def mark_healthy(self):
        self.healthy = True
        self.consecutive_failures = 0
        return self

    def mark_unhealthy(self):
        self.healthy = False
        return self

    def pause(self):
        self.accepting_requests = False
        return self

    def resume(self):
        self.accepting_requests = True
        return self

    def load_score(self):
        """
        Primary least-load score.

        Active request count is intentionally simple and deterministic. More
        advanced capacity weighting can be added later without changing the
        load-balancer contract.
        """
        return self.active_requests

    def stats(self):
        return {
            "instance_id": self.instance_id,
            "service_name": self.service_name,
            "healthy": self.healthy,
            "accepting_requests": self.accepting_requests,
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "consecutive_failures": self.consecutive_failures,
            "metadata": dict(self.metadata),
        }
