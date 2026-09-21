class LabelSet:
    """
    Canonical metric label representation.

    Label names are validated against the metric definition and emitted in
    definition order, making series identity deterministic.
    """

    def __init__(
        self,
        label_names,
        values=None,
    ):
        if not isinstance(
            label_names,
            (list, tuple),
        ):
            raise TypeError(
                "label_names must be list/tuple"
            )

        normalized_names = []

        for name in label_names:
            if not isinstance(
                name,
                str,
            ) or name == "":
                raise ValueError(
                    "label names must be non-empty strings"
                )

            if name in normalized_names:
                raise ValueError(
                    "duplicate label name: "
                    + name
                )

            normalized_names.append(
                name
            )

        if values is None:
            values = {}

        if not isinstance(
            values,
            dict,
        ):
            raise TypeError(
                "label values must be dict or None"
            )

        for key in values:
            if key not in normalized_names:
                raise ValueError(
                    "unknown label: "
                    + str(
                        key
                    )
                )

        for name in normalized_names:
            if name not in values:
                raise ValueError(
                    "missing label: "
                    + name
                )

            value = values[
                name
            ]

            if not isinstance(
                value,
                (str, int, float, bool),
            ):
                raise TypeError(
                    "label values must be scalar"
                )

        self.label_names = (
            normalized_names
        )

        self.values = {
            name: self._normalize_value(
                values[
                    name
                ]
            )
            for name in self.label_names
        }

    def key(
        self,
    ):
        if len(
            self.label_names
        ) == 0:
            return ""

        parts = []

        for name in self.label_names:
            value = self.values[
                name
            ]

            parts.append(
                self._escape(
                    name
                )
                + "="
                + self._escape(
                    value
                )
            )

        return "|".join(
            parts
        )

    def to_dict(
        self,
    ):
        return {
            name: self.values[
                name
            ]
            for name in self.label_names
        }

    def _normalize_value(
        self,
        value,
    ):
        if value is True:
            return "true"

        if value is False:
            return "false"

        return str(
            value
        )

    def _escape(
        self,
        value,
    ):
        return (
            str(
                value
            )
            .replace(
                "\\",
                "\\\\",
            )
            .replace(
                "|",
                "\\|",
            )
            .replace(
                "=",
                "\\=",
            )
        )
