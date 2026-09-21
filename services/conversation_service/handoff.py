class DownstreamRAGError(Exception):
    def __init__(
        self,
        code,
        message,
        retryable=False,
    ):
        Exception.__init__(
            self,
            message
        )

        self.code = str(
            code
        )

        self.message = str(
            message
        )

        self.retryable = bool(
            retryable
        )


class RAGConversationHandoff:
    """
    Adapter from stateful conversation sessions to stateless rag_service.

    Retrieval/generation still belongs to rag_service. This adapter supplies a
    bounded recent history prefix so follow-up questions have conversational
    context without letting unbounded session history consume the model window.
    """

    def __init__(
        self,
        rag_service,
        window_builder,
        max_history_tokens=128,
    ):
        if rag_service is None or not hasattr(
            rag_service,
            "handle",
        ):
            raise TypeError(
                "rag_service must provide handle()"
            )

        if window_builder is None or not hasattr(
            window_builder,
            "build",
        ):
            raise TypeError(
                "window_builder must provide build()"
            )

        if (
            not isinstance(
                max_history_tokens,
                int,
            )
            or max_history_tokens <= 0
        ):
            raise ValueError(
                "max_history_tokens must be positive int"
            )

        self.rag_service = rag_service
        self.window_builder = (
            window_builder
        )
        self.max_history_tokens = (
            max_history_tokens
        )

        self._sequence = 0

    def answer(
        self,
        session,
        current_user_message,
        rag_options=None,
        trace_id=None,
        correlation_id=None,
    ):
        if rag_options is None:
            rag_options = {}

        if not isinstance(
            rag_options,
            dict,
        ):
            raise TypeError(
                "rag_options must be dict or None"
            )

        history = (
            self.window_builder
            .build(
                session=session,
                max_tokens=(
                    self.max_history_tokens
                ),
                exclude_last=1,
            )
        )

        query = self._query(
            history,
            current_user_message,
        )

        payload = self._copy(
            rag_options
        )

        payload[
            "query"
        ] = query

        self._sequence += 1

        request_id = (
            "conversation-rag-"
            + str(
                self._sequence
            )
        )

        request = ServiceRequest(
            request_id=request_id,
            service="rag_service",
            operation="answer",
            payload=payload,
            metadata={
                "session_id": (
                    session.session_id
                ),
                "conversation_service": (
                    True
                ),
            },
            correlation_id=(
                correlation_id
            ),
            trace_id=trace_id,
        )

        response = (
            self.rag_service
            .handle(
                request
            )
        )

        if not isinstance(
            response,
            ServiceResponse,
        ):
            raise TypeError(
                "rag_service returned non-ServiceResponse"
            )

        if not response.success:
            error = response.error

            raise DownstreamRAGError(
                code=(
                    "UNKNOWN"
                    if error is None
                    else error.code
                ),
                message=(
                    "RAG service failed"
                    if error is None
                    else error.message
                ),
                retryable=(
                    False
                    if error is None
                    else error.retryable
                ),
            )

        if "answer" not in response.data:
            raise ValueError(
                "rag_service response missing answer"
            )

        answer = response.data[
            "answer"
        ]

        if not isinstance(
            answer,
            dict,
        ):
            raise TypeError(
                "rag_service answer must be dict"
            )

        return {
            "answer": self._copy(
                answer
            ),
            "history_window": (
                history
            ),
            "rag_request_id": (
                request_id
            ),
        }

    def _query(
        self,
        history,
        current_user_message,
    ):
        if not isinstance(
            current_user_message,
            str,
        ):
            raise TypeError(
                "current_user_message must be str"
            )

        if history.rendered == "":
            return (
                current_user_message
            )

        return (
            "Conversation history:\n"
            + history.rendered
            + "\nCURRENT USER MESSAGE:\n"
            + current_user_message
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
