class ConversationChatResult:
    """
    Public result for one stateful chat turn.
    """

    def __init__(
        self,
        session_id,
        user_message,
        assistant_message,
        answer,
        history_window,
        rag_request_id,
    ):
        self.session_id = (
            session_id
        )

        self.user_message = (
            user_message
        )

        self.assistant_message = (
            assistant_message
        )

        self.answer = self._copy(
            answer
        )

        self.history_window = (
            history_window
        )

        self.rag_request_id = (
            rag_request_id
        )

    def to_dict(
        self,
    ):
        return {
            "session_id": (
                self.session_id
            ),
            "user_message": (
                self._message_dict(
                    self.user_message
                )
            ),
            "assistant_message": (
                None
                if self.assistant_message
                is None
                else self._message_dict(
                    self.assistant_message
                )
            ),
            "answer": self._copy(
                self.answer
            ),
            "history_window": (
                self.history_window
                .to_dict(
                    include_rendered=False
                )
            ),
            "rag_request_id": (
                self.rag_request_id
            ),
        }

    def _message_dict(
        self,
        message,
    ):
        return {
            "role": message.role,
            "content": message.content,
            "sequence": (
                message.source_index
            ),
            "metadata": self._copy(
                message.metadata
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
