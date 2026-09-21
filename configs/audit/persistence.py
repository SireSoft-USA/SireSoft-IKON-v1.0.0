class AuditPersistenceConfig:
    def __init__(
        self,
        state_path=None,
        load_state_on_start=False,
    ):
        if state_path is not None and (
            not isinstance(
                state_path,
                str,
            )
            or state_path == ""
        ):
            raise ValueError(
                "state_path must be non-empty str or None"
            )

        if (
            load_state_on_start
            and state_path is None
        ):
            raise ValueError(
                "load_state_on_start requires state_path"
            )

        self.state_path = state_path
        self.load_state_on_start = bool(
            load_state_on_start
        )

    def to_dict(
        self,
    ):
        return {
            "state_path": (
                self.state_path
            ),
            "load_state_on_start": (
                self.load_state_on_start
            ),
        }
