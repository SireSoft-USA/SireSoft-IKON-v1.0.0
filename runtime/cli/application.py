class RuntimeCLIApplication:
    """
    Command-level adapter over RuntimeSystemSpec + RuntimeEntrypoint.

    A binding_provider callback may inject the real application services into
    the composition root without coupling the CLI parser to service classes.
    """

    def __init__(
        self,
        time_provider,
        binding_provider=None,
        parser=None,
        entrypoint_factory=None,
    ):
        if not callable(
            time_provider
        ):
            raise TypeError(
                "time_provider must be callable"
            )

        if (
            binding_provider
            is not None
            and not callable(
                binding_provider
            )
        ):
            raise TypeError(
                "binding_provider must be callable or None"
            )

        self.time_provider = (
            time_provider
        )
        self.binding_provider = (
            binding_provider
        )

        self.parser = (
            RuntimeCLIParser()
            if parser is None
            else parser
        )

        self.entrypoint_factory = (
            RuntimeEntrypointFactory()
            if entrypoint_factory
            is None
            else entrypoint_factory
        )

        self.total_commands = 0

    def execute(
        self,
        argv,
    ):
        self.total_commands += 1

        try:
            command = self.parser.parse(
                argv
            )

            if len(
                command.positionals
            ) > 0:
                raise ValueError(
                    "unexpected positional arguments: "
                    + " ".join(
                        command.positionals
                    )
                )

            config = (
                RuntimeCLIConfig
                .from_command(
                    command
                )
            )

            bindings = []

            if self.binding_provider is not None:
                bindings = (
                    self.binding_provider()
                )

                if not isinstance(
                    bindings,
                    (list, tuple),
                ):
                    raise TypeError(
                        "binding_provider must return list/tuple"
                    )

            spec = RuntimeSystemSpec(
                storage_root=(
                    config.storage_root
                ),
                time_provider=(
                    self.time_provider
                ),
                worker_count=(
                    config.worker_count
                ),
                queue_capacity=(
                    config.queue_capacity
                ),
                storage_namespaces=(
                    config.storage_namespaces
                ),
                service_bindings=list(
                    bindings
                ),
                enable_signals=(
                    config.enable_signals
                ),
                metadata={
                    "launch_source": (
                        "runtime_cli"
                    ),
                },
            )

            if command.name == "validate":
                system = (
                    RuntimeCompositionBuilder()
                    .build(
                        spec
                    )
                )

                return {
                    "code": 0,
                    "ok": True,
                    "command": (
                        "validate"
                    ),
                    "config": (
                        config.to_dict()
                    ),
                    "components": (
                        system.components
                        .summary()
                    ),
                }

            if command.name == "run":
                entrypoint = (
                    self.entrypoint_factory
                    .create(
                        spec
                    )
                )

                status = entrypoint.run(
                    wait_timeout=(
                        config.wait_timeout
                    )
                )

                return {
                    "code": status.code,
                    "ok": status.ok(),
                    "command": "run",
                    "config": (
                        config.to_dict()
                    ),
                    "runtime": (
                        status.to_dict()
                    ),
                }

            raise ValueError(
                "unsupported command"
            )

        except (
            ValueError,
            TypeError,
            RuntimeError,
        ) as error:
            return {
                "code": 2,
                "ok": False,
                "command": None,
                "error": {
                    "type": (
                        type(
                            error
                        ).__name__
                    ),
                    "message": str(
                        error
                    ),
                },
            }

    def status(
        self,
    ):
        return {
            "total_commands": (
                self.total_commands
            ),
        }
