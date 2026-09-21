class ConversationService:
    """
    Protocol-facing stateful conversation service.

    Supported operations:
      create_session
      list_sessions
      get_session
      delete_session
      close_session
      reopen_session
      update_metadata
      add_message
      context
      chat
    """

    def __init__(
        self,
        manager,
    ):
        if manager is None or not hasattr(
            manager,
            "create_session",
        ):
            raise TypeError(
                "manager must provide conversation operations"
            )

        self.manager = manager

    def handle(
        self,
        request,
    ):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        if request.service != (
            "conversation_service"
        ):
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = (
                request.operation
            )

            if operation == "create_session":
                session = (
                    self.manager
                    .create_session(
                        session_id=self._required(
                            request.payload,
                            "session_id",
                        ),
                        title=request.payload.get(
                            "title"
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                        system_message=request.payload.get(
                            "system_message"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "session": (
                            session.to_dict()
                        ),
                    },
                )

            if operation == "list_sessions":
                sessions = (
                    self.manager
                    .list_sessions()
                )

                return self._success(
                    request,
                    {
                        "sessions": sessions,
                        "count": len(
                            sessions
                        ),
                    },
                )

            if operation == "get_session":
                session = (
                    self.manager
                    .get(
                        self._required(
                            request.payload,
                            "session_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "session": (
                            session.to_dict()
                        ),
                    },
                )

            if operation == "delete_session":
                session = (
                    self.manager
                    .delete_session(
                        self._required(
                            request.payload,
                            "session_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "deleted_session_id": (
                            session.session_id
                        ),
                    },
                )

            if operation == "close_session":
                session = (
                    self.manager
                    .close_session(
                        self._required(
                            request.payload,
                            "session_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "session": (
                            session.summary()
                        ),
                    },
                )

            if operation == "reopen_session":
                session = (
                    self.manager
                    .reopen_session(
                        self._required(
                            request.payload,
                            "session_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "session": (
                            session.summary()
                        ),
                    },
                )

            if operation == "update_metadata":
                session = (
                    self.manager
                    .update_metadata(
                        session_id=self._required(
                            request.payload,
                            "session_id",
                        ),
                        metadata=self._required(
                            request.payload,
                            "metadata",
                        ),
                        replace=request.payload.get(
                            "replace",
                            False,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "session": (
                            session.summary()
                        ),
                    },
                )

            if operation == "add_message":
                message = (
                    self.manager
                    .add_message(
                        session_id=self._required(
                            request.payload,
                            "session_id",
                        ),
                        role=self._required(
                            request.payload,
                            "role",
                        ),
                        content=self._required(
                            request.payload,
                            "content",
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                        name=request.payload.get(
                            "name"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "message": {
                            "role": message.role,
                            "content": (
                                message.content
                            ),
                            "sequence": (
                                message.source_index
                            ),
                            "metadata": (
                                message.metadata
                            ),
                        },
                    },
                )

            if operation == "context":
                window = (
                    self.manager
                    .context(
                        session_id=self._required(
                            request.payload,
                            "session_id",
                        ),
                        max_tokens=request.payload.get(
                            "max_tokens"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "context": (
                            window.to_dict()
                        ),
                    },
                )

            if operation == "chat":
                result = (
                    self.manager
                    .chat(
                        session_id=self._required(
                            request.payload,
                            "session_id",
                        ),
                        user_text=self._required(
                            request.payload,
                            "text",
                        ),
                        rag_options=request.payload.get(
                            "rag_options"
                        ),
                        trace_id=(
                            request.trace_id
                        ),
                        correlation_id=(
                            request.request_id
                        ),
                        user_metadata=request.payload.get(
                            "metadata"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "chat": (
                            result.to_dict()
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                (
                    "Unsupported conversation service operation"
                ),
            )

        except KeyError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(
                    error
                ),
            )

        except DownstreamRAGError as error:
            return self._error(
                request,
                (
                    "DOWNSTREAM_"
                    + error.code
                ),
                error.message,
                retryable=(
                    error.retryable
                ),
            )

        except RuntimeError as error:
            return self._error(
                request,
                "CONFLICT",
                str(
                    error
                ),
            )

        except (
            ValueError,
            TypeError,
            IndexError,
        ) as error:
            return self._error(
                request,
                "INVALID_REQUEST",
                str(
                    error
                ),
            )

    def _required(
        self,
        payload,
        key,
    ):
        if key not in payload:
            raise ValueError(
                "payload requires "
                + key
            )

        return payload[
            key
        ]

    def _success(
        self,
        request,
        data,
    ):
        return (
            ServiceResponse
            .success_response(
                request,
                data=data,
            )
        )

    def _error(
        self,
        request,
        code,
        message,
        retryable=False,
    ):
        return (
            ServiceResponse
            .error_response(
                request,
                ProtocolError(
                    code=code,
                    message=message,
                    retryable=retryable,
                ),
            )
        )


def build_conversation_manager(
    tokenizer,
    rag_service,
    max_history_tokens=128,
):
    window_builder = (
        ConversationWindowBuilder(
            tokenizer=tokenizer,
            default_max_tokens=(
                max_history_tokens
            ),
        )
    )

    handoff = (
        RAGConversationHandoff(
            rag_service=rag_service,
            window_builder=(
                window_builder
            ),
            max_history_tokens=(
                max_history_tokens
            ),
        )
    )

    return ConversationManager(
        Conversation=Conversation,
        Message=Message,
        window_builder=(
            window_builder
        ),
        rag_handoff=handoff,
    )
