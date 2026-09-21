class RuntimeCLIParser:
    """
    Small deterministic parser for:
      run
      validate

    Long options use --name value or boolean --enable-signals.
    """

    BOOLEAN_OPTIONS = (
        "enable-signals",
    )

    VALUE_OPTIONS = (
        "storage-root",
        "workers",
        "queue-capacity",
        "wait-timeout",
        "namespace",
    )

    COMMANDS = (
        "run",
        "validate",
    )

    def parse(
        self,
        argv,
    ):
        if not isinstance(
            argv,
            (list, tuple),
        ):
            raise TypeError(
                "argv must be list/tuple"
            )

        args = list(
            argv
        )

        if len(
            args
        ) == 0:
            raise ValueError(
                "runtime command is required"
            )

        command_name = args[
            0
        ]

        if command_name not in self.COMMANDS:
            raise ValueError(
                "unknown runtime command: "
                + str(
                    command_name
                )
            )

        options = {}
        positionals = []

        index = 1

        while index < len(
            args
        ):
            token = args[
                index
            ]

            if not isinstance(
                token,
                str,
            ):
                raise TypeError(
                    "CLI arguments must be strings"
                )

            if not token.startswith(
                "--"
            ):
                positionals.append(
                    token
                )
                index += 1
                continue

            name = token[
                2:
            ]

            if name == "":
                raise ValueError(
                    "empty CLI option"
                )

            if name in self.BOOLEAN_OPTIONS:
                if name in options:
                    raise ValueError(
                        "duplicate CLI option: --"
                        + name
                    )

                options[
                    name
                ] = True
                index += 1
                continue

            if name not in self.VALUE_OPTIONS:
                raise ValueError(
                    "unknown CLI option: --"
                    + name
                )

            if (
                index + 1
                >= len(
                    args
                )
            ):
                raise ValueError(
                    "missing value for --"
                    + name
                )

            value = args[
                index + 1
            ]

            if (
                not isinstance(
                    value,
                    str,
                )
                or value.startswith(
                    "--"
                )
            ):
                raise ValueError(
                    "missing value for --"
                    + name
                )

            if name == "namespace":
                if name not in options:
                    options[
                        name
                    ] = []

                options[
                    name
                ].append(
                    value
                )

            else:
                if name in options:
                    raise ValueError(
                        "duplicate CLI option: --"
                        + name
                    )

                options[
                    name
                ] = value

            index += 2

        return RuntimeCLICommand(
            command_name,
            options=options,
            positionals=(
                positionals
            ),
        )
