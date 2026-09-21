class ProcessSpec:
    """
    Declarative child-process configuration for SireLLM runtime services.
    """

    RESTART_POLICIES = (
        "never",
        "on_failure",
        "always",
    )

    def __init__(
        self,
        name,
        command,
        cwd=None,
        env=None,
        restart_policy="never",
        max_restarts=0,
        graceful_timeout_seconds=3.0,
        metadata=None,
    ):
        if not isinstance(
            name,
            str,
        ) or name == "":
            raise ValueError(
                "name must be non-empty str"
            )

        if not isinstance(
            command,
            (list, tuple),
        ) or len(
            command
        ) == 0:
            raise ValueError(
                "command must be non-empty list/tuple"
            )

        normalized_command = []

        for part in command:
            if not isinstance(
                part,
                str,
            ) or part == "":
                raise ValueError(
                    "command elements must be non-empty strings"
                )

            normalized_command.append(
                part
            )

        if cwd is not None and not isinstance(
            cwd,
            str,
        ):
            raise TypeError(
                "cwd must be str or None"
            )

        if env is None:
            env = {}

        if not isinstance(
            env,
            dict,
        ):
            raise TypeError(
                "env must be dict or None"
            )

        normalized_env = {}

        for key in env:
            value = env[
                key
            ]

            if not isinstance(
                key,
                str,
            ) or key == "":
                raise ValueError(
                    "environment keys must be non-empty strings"
                )

            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    "environment values must be strings"
                )

            normalized_env[
                key
            ] = value

        if restart_policy not in self.RESTART_POLICIES:
            raise ValueError(
                "invalid restart_policy"
            )

        if (
            not isinstance(
                max_restarts,
                int,
            )
            or max_restarts < 0
        ):
            raise ValueError(
                "max_restarts must be non-negative int"
            )

        if (
            not isinstance(
                graceful_timeout_seconds,
                (int, float),
            )
            or graceful_timeout_seconds <= 0
        ):
            raise ValueError(
                "graceful_timeout_seconds must be positive"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.name = name
        self.command = (
            normalized_command
        )
        self.cwd = cwd
        self.env = (
            normalized_env
        )
        self.restart_policy = (
            restart_policy
        )
        self.max_restarts = (
            max_restarts
        )
        self.graceful_timeout_seconds = float(
            graceful_timeout_seconds
        )
        self.metadata = self._copy(
            metadata
        )

    def should_restart(
        self,
        exit_code,
        restart_count,
    ):
        if (
            not isinstance(
                restart_count,
                int,
            )
            or restart_count < 0
        ):
            raise ValueError(
                "restart_count must be non-negative int"
            )

        if restart_count >= self.max_restarts:
            return False

        if self.restart_policy == "never":
            return False

        if self.restart_policy == "always":
            return True

        return (
            exit_code is not None
            and exit_code != 0
        )

    def public_dict(
        self,
    ):
        return {
            "name": self.name,
            "command": list(
                self.command
            ),
            "cwd": self.cwd,
            "env_keys": sorted(
                self.env.keys()
            ),
            "restart_policy": (
                self.restart_policy
            ),
            "max_restarts": (
                self.max_restarts
            ),
            "graceful_timeout_seconds": (
                self.graceful_timeout_seconds
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
