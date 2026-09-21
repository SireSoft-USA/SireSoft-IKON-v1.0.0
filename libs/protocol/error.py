class ProtocolError:
    """
    Structured service/protocol error carried across microservice boundaries.
    """

    def __init__(
        self,
        code,
        message,
        details=None,
        retryable=False,
    ):
        if not isinstance(code, str) or code == "":
            raise ValueError("code must be non-empty str")

        if not isinstance(message, str) or message == "":
            raise ValueError("message must be non-empty str")

        if details is None:
            details = {}

        if not isinstance(details, dict):
            raise TypeError("details must be dict or None")

        self.code = code
        self.message = message
        self.details = self._deep_copy(details)
        self.retryable = bool(retryable)

    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "details": self._deep_copy(self.details),
            "retryable": self.retryable,
        }

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise TypeError("error payload must be dict")

        return cls(
            code=value["code"],
            message=value["message"],
            details=value.get("details", {}),
            retryable=value.get("retryable", False),
        )

    def _deep_copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._deep_copy(value[key])

            return result

        if isinstance(value, list):
            return [
                self._deep_copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._deep_copy(item)
                for item in value
            ]

        return value
