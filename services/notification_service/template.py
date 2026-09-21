class NotificationTemplate:
    """
    Minimal deterministic template renderer.

    Placeholders use {{name}}. Missing variables are rejected instead of being
    silently replaced, which prevents partially rendered notifications.
    """

    def __init__(
        self,
        template_id,
        subject_template=None,
        body_template="",
        metadata=None,
    ):
        if not isinstance(
            template_id,
            str,
        ) or template_id == "":
            raise ValueError(
                "template_id must be non-empty str"
            )

        if (
            subject_template
            is not None
            and not isinstance(
                subject_template,
                str,
            )
        ):
            raise TypeError(
                "subject_template must be str or None"
            )

        if not isinstance(
            body_template,
            str,
        ):
            raise TypeError(
                "body_template must be str"
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

        self.template_id = (
            template_id
        )
        self.subject_template = (
            subject_template
        )
        self.body_template = (
            body_template
        )
        self.metadata = self._copy(
            metadata
        )

    def render(
        self,
        variables=None,
    ):
        if variables is None:
            variables = {}

        if not isinstance(
            variables,
            dict,
        ):
            raise TypeError(
                "variables must be dict or None"
            )

        subject = None

        if self.subject_template is not None:
            subject = self._render_text(
                self.subject_template,
                variables,
            )

        body = self._render_text(
            self.body_template,
            variables,
        )

        return {
            "subject": subject,
            "body": body,
        }

    def public_dict(
        self,
    ):
        return {
            "template_id": (
                self.template_id
            ),
            "subject_template": (
                self.subject_template
            ),
            "body_template": (
                self.body_template
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _render_text(
        self,
        text,
        variables,
    ):
        result = ""
        index = 0

        while index < len(
            text
        ):
            start = text.find(
                "{{",
                index,
            )

            if start < 0:
                result += text[
                    index:
                ]
                break

            result += text[
                index:start
            ]

            end = text.find(
                "}}",
                start + 2,
            )

            if end < 0:
                raise ValueError(
                    "unclosed template placeholder"
                )

            name = text[
                start + 2:
                end
            ].strip()

            if name == "":
                raise ValueError(
                    "empty template placeholder"
                )

            if name not in variables:
                raise KeyError(
                    "template variable missing: "
                    + name
                )

            value = variables[
                name
            ]

            if isinstance(
                value,
                (dict, list, tuple),
            ):
                raise TypeError(
                    "template values must be scalar"
                )

            result += str(
                value
            )

            index = (
                end
                + 2
            )

        return result

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
