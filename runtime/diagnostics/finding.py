class DiagnosticFinding:
    SEVERITIES = (
        "info",
        "warning",
        "critical",
    )

    def __init__(
        self,
        code,
        severity,
        message,
        component,
        details=None,
    ):
        for field_name, value in (
            ("code", code),
            ("message", message),
            ("component", component),
        ):
            if not isinstance(value, str) or value == "":
                raise ValueError(
                    field_name + " must be non-empty str"
                )

        if severity not in self.SEVERITIES:
            raise ValueError("invalid finding severity")

        if details is None:
            details = {}

        if not isinstance(details, dict):
            raise TypeError("details must be dict or None")

        self.code = code
        self.severity = severity
        self.message = message
        self.component = component
        self.details = self._copy(details)

    def to_dict(
        self,
    ):
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "component": self.component,
            "details": self._copy(self.details),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, (list, tuple)):
            return [
                self._copy(item)
                for item in value
            ]

        return value
