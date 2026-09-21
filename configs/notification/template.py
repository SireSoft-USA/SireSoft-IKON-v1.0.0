class NotificationTemplateConfig:
    def __init__(
        self,
        template_id,
        body_template,
        subject_template=None,
        enabled=True,
        metadata=None,
    ):
        if (
            not isinstance(
                template_id,
                str,
            )
            or template_id == ""
        ):
            raise ValueError(
                "template_id must be non-empty str"
            )

        if not isinstance(
            body_template,
            str,
        ):
            raise TypeError(
                "body_template must be str"
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
        self.body_template = (
            body_template
        )
        self.subject_template = (
            subject_template
        )
        self.enabled = bool(
            enabled
        )
        self.metadata = self._copy(
            metadata
        )

    def to_dict(
        self,
    ):
        return {
            "template_id": (
                self.template_id
            ),
            "body_template": (
                self.body_template
            ),
            "subject_template": (
                self.subject_template
            ),
            "enabled": (
                self.enabled
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
            return {
                key: self._copy(
                    value[
                        key
                    ]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
