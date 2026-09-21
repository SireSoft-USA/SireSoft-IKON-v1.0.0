class ServiceProbe:
    """
    Active protocol-aware health probe for one service handler.

    readiness_path optionally points into successful response.data, for example:
      ["status", "ready"]
    A successful response with readiness=False is degraded rather than unhealthy.
    """

    def __init__(
        self,
        probe_id,
        service_name,
        handler,
        operation="status",
        payload=None,
        required=True,
        readiness_path=None,
        metadata=None,
    ):
        if not isinstance(probe_id, str) or probe_id == "":
            raise ValueError("probe_id must be non-empty str")

        if not isinstance(service_name, str) or service_name == "":
            raise ValueError("service_name must be non-empty str")

        if not callable(handler):
            raise TypeError("handler must be callable")

        if not isinstance(operation, str) or operation == "":
            raise ValueError("operation must be non-empty str")

        if payload is None:
            payload = {}

        if metadata is None:
            metadata = {}

        if not isinstance(payload, dict):
            raise TypeError("payload must be dict or None")

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        if readiness_path is None:
            readiness_path = []

        if not isinstance(
            readiness_path,
            (list, tuple),
        ):
            raise TypeError(
                "readiness_path must be list/tuple or None"
            )

        for key in readiness_path:
            if not isinstance(key, str) or key == "":
                raise ValueError(
                    "readiness_path entries must be non-empty strings"
                )

        self.probe_id = probe_id
        self.service_name = service_name
        self.handler = handler
        self.operation = operation
        self.payload = self._copy(payload)
        self.required = bool(required)
        self.readiness_path = list(readiness_path)
        self.metadata = self._copy(metadata)

    def execute(
        self,
        request_id,
        trace_id=None,
    ):
        request = ServiceRequest(
            request_id=request_id,
            service=self.service_name,
            operation=self.operation,
            payload=self._copy(self.payload),
            metadata={
                "monitoring_probe_id": self.probe_id,
            },
            trace_id=trace_id,
        )

        try:
            response = self.handler(
                request
            )

        except Exception as error:
            return ProbeResult(
                probe_id=self.probe_id,
                service_name=self.service_name,
                status="unhealthy",
                required=self.required,
                response_success=False,
                readiness=None,
                error_code=(
                    type(error).__name__
                ),
                error_message=str(error),
                details={
                    "probe_operation": self.operation,
                    "handler_exception": True,
                },
            )

        if not isinstance(
            response,
            ServiceResponse,
        ):
            return ProbeResult(
                probe_id=self.probe_id,
                service_name=self.service_name,
                status="unhealthy",
                required=self.required,
                response_success=False,
                readiness=None,
                error_code="INVALID_PROBE_RESPONSE",
                error_message=(
                    "probe handler did not return ServiceResponse"
                ),
                details={
                    "probe_operation": self.operation,
                },
            )

        if not response.success:
            error = response.error

            return ProbeResult(
                probe_id=self.probe_id,
                service_name=self.service_name,
                status="unhealthy",
                required=self.required,
                response_success=False,
                readiness=None,
                error_code=(
                    None
                    if error is None
                    else error.code
                ),
                error_message=(
                    None
                    if error is None
                    else error.message
                ),
                details={
                    "probe_operation": self.operation,
                    "response_metadata": (
                        self._copy(
                            response.metadata
                        )
                    ),
                },
            )

        readiness = None
        status = "healthy"

        if len(self.readiness_path) > 0:
            found, readiness = self._read_path(
                response.data,
                self.readiness_path,
            )

            if not found:
                status = "degraded"
                readiness = None

            elif readiness is not True:
                status = "degraded"

        return ProbeResult(
            probe_id=self.probe_id,
            service_name=self.service_name,
            status=status,
            required=self.required,
            response_success=True,
            readiness=readiness,
            details={
                "probe_operation": self.operation,
                "response_metadata": self._copy(
                    response.metadata
                ),
            },
        )

    def summary(self):
        return {
            "probe_id": self.probe_id,
            "service_name": self.service_name,
            "operation": self.operation,
            "required": self.required,
            "readiness_path": list(
                self.readiness_path
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _read_path(
        self,
        value,
        path,
    ):
        current = value

        for key in path:
            if not isinstance(
                current,
                dict,
            ):
                return (
                    False,
                    None,
                )

            if key not in current:
                return (
                    False,
                    None,
                )

            current = current[
                key
            ]

        return (
            True,
            current,
        )

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
