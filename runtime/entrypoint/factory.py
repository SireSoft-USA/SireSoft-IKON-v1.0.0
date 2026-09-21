class RuntimeEntrypointFactory:
    """
    Small composition boundary used by executable launchers.
    """

    def __init__(
        self,
        composition_builder=None,
    ):
        self.composition_builder = (
            RuntimeCompositionBuilder()
            if composition_builder is None
            else composition_builder
        )

    def create(
        self,
        spec,
    ):
        if not isinstance(
            spec,
            RuntimeSystemSpec,
        ):
            raise TypeError(
                "spec must be RuntimeSystemSpec"
            )

        system = (
            self.composition_builder
            .build(
                spec
            )
        )

        return RuntimeEntrypoint(
            system
        )
