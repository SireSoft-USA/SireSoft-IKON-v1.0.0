class ConversationSession:
    """
    Deterministic conversation/session container.

    No wall-clock timestamps or UUIDs are generated in this core service. The
    caller supplies the session identity; runtime layers can add timestamps in
    metadata later.
    """

    VALID_STATUSES = (
        "open",
        "closed",
    )

    def __init__(
        self,
        session_id,
        Conversation,
        Message,
        title=None,
        metadata=None,
    ):
        if not isinstance(
            session_id,
            str,
        ) or session_id == "":
            raise ValueError(
                "session_id must be non-empty str"
            )

        if title is not None and not isinstance(
            title,
            str,
        ):
            raise TypeError(
                "title must be str or None"
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

        self.session_id = (
            session_id
        )

        self.Conversation = (
            Conversation
        )

        self.Message = (
            Message
        )

        self.title = title
        self.metadata = self._copy(
            metadata
        )

        self.status = "open"

        self.conversation = Conversation(
            conversation_id=session_id,
            title=title,
            metadata=self._copy(
                metadata
            ),
        )

    def append_message(
        self,
        role,
        content,
        metadata=None,
        name=None,
    ):
        self._require_open()

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        sequence = (
            self.conversation
            .message_count()
        )

        message_metadata = self._copy(
            metadata
        )

        message_metadata[
            "sequence"
        ] = sequence

        message = self.Message(
            role=role,
            content=content,
            name=name,
            metadata=(
                message_metadata
            ),
            source_index=sequence,
            raw=None,
        )

        self.conversation.add_message(
            message
        )

        return message

    def append_user(
        self,
        content,
        metadata=None,
    ):
        return self.append_message(
            "user",
            content,
            metadata=metadata,
        )

    def append_assistant(
        self,
        content,
        metadata=None,
    ):
        return self.append_message(
            "assistant",
            content,
            metadata=metadata,
        )

    def append_system(
        self,
        content,
        metadata=None,
    ):
        return self.append_message(
            "system",
            content,
            metadata=metadata,
        )

    def messages(
        self,
    ):
        return (
            self.conversation
            .messages()
        )

    def message_count(
        self,
    ):
        return (
            self.conversation
            .message_count()
        )

    def close(
        self,
    ):
        self.status = "closed"
        return self

    def reopen(
        self,
    ):
        self.status = "open"
        return self

    def update_metadata(
        self,
        values,
        replace=False,
    ):
        if not isinstance(
            values,
            dict,
        ):
            raise TypeError(
                "metadata update must be dict"
            )

        if replace:
            self.metadata = self._copy(
                values
            )
        else:
            for key in values:
                self.metadata[
                    key
                ] = self._copy(
                    values[
                        key
                    ]
                )

        self.conversation.metadata = (
            self._copy(
                self.metadata
            )
        )

        return self

    def to_dict(
        self,
        include_messages=True,
    ):
        result = {
            "session_id": (
                self.session_id
            ),
            "title": self.title,
            "status": self.status,
            "metadata": self._copy(
                self.metadata
            ),
            "message_count": (
                self.message_count()
            ),
        }

        if include_messages:
            result[
                "messages"
            ] = [
                self._message_dict(
                    message
                )
                for message
                in self.messages()
            ]

        return result

    def summary(
        self,
    ):
        return self.to_dict(
            include_messages=False
        )

    def _message_dict(
        self,
        message,
    ):
        return {
            "role": message.role,
            "content": message.content,
            "name": message.name,
            "metadata": self._copy(
                message.metadata
            ),
            "sequence": (
                message.source_index
            ),
        }

    def _require_open(
        self,
    ):
        if self.status != "open":
            raise RuntimeError(
                "conversation session is closed"
            )

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
