class RuntimeCLICommand:
    """
    Parsed CLI command independent of sys.argv.
    """

    def __init__(
        self,
        name,
        options=None,
        positionals=None,
    ):
        if not isinstance(
            name,
            str,
        ) or name == "":
            raise ValueError(
                "command name must be non-empty str"
            )

        if options is None:
            options = {}

        if positionals is None:
            positionals = []

        if not isinstance(
            options,
            dict,
        ):
            raise TypeError(
                "options must be dict or None"
            )

        if not isinstance(
            positionals,
            list,
        ):
            raise TypeError(
                "positionals must be list or None"
            )

        self.name = name
        self.options = dict(
            options
        )
        self.positionals = list(
            positionals
        )

    def option(
        self,
        name,
        default=None,
    ):
        return self.options.get(
            name,
            default,
        )

    def to_dict(
        self,
    ):
        return {
            "name": self.name,
            "options": dict(
                self.options
            ),
            "positionals": list(
                self.positionals
            ),
        }
