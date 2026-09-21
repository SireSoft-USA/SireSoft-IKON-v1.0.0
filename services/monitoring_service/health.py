class ProbeResult:
    """
    Deterministic service-health result.

    No wall-clock latency/timestamps are fabricated in this core layer.
    Runtime/observability layers can add those measurements later.
    """

    VALID_STATUSES = (
        "healthy",
        "degraded",
        "unhealthy",
    )

    def __init__(
        self,
        probe_id,
        service_name,
        status,
        required,
        response_success=False,
        readiness=None,
        error_code=None,
        error_message=None,
        details=None,
    ):
        if not isinstance(probe_id, str) or probe_id == "":
            raise ValueError("probe_id must be non-empty str")

        if not isinstance(service_name, str) or service_name == "":
            raise ValueError("service_name must be non-empty str")

        if status not in self.VALID_STATUSES:
            raise ValueError("invalid probe status")

        if details is None:
            details = {}

        if not isinstance(details, dict):
            raise TypeError("details must be dict or None")

        self.probe_id = probe_id
        self.service_name = service_name
        self.status = status
        self.required = bool(required)
        self.response_success = bool(response_success)
        self.readiness = readiness
        self.error_code = error_code
        self.error_message = error_message
        self.details = self._copy(details)

    def healthy(self):
        return self.status == "healthy"

    def to_dict(self):
        return {
            "probe_id": self.probe_id,
            "service_name": self.service_name,
            "status": self.status,
            "required": self.required,
            "response_success": self.response_success,
            "readiness": self.readiness,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "details": self._copy(self.details),
        }

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._copy(value[key])

            return result

        if isinstance(value, list):
            return [
                self._copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._copy(item)
                for item in value
            ]

        return value
