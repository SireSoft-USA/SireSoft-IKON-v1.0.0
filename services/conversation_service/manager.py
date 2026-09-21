class ConversationManager:
    """
    Owns chat sessions and coordinates stateful turns with rag_service.
    """

    def __init__(
        self,
        Conversation,
        Message,
        window_builder,
        rag_handoff,
    ):
        self.Conversation = (
            Conversation
        )

        self.Message = Message

        self.window_builder = (
            window_builder
        )

        self.rag_handoff = (
            rag_handoff
        )

        self._sessions = {}
        self._order = []

    def create_session(
        self,
        session_id,
        title=None,
        metadata=None,
        system_message=None,
    ):
        if session_id in self._sessions:
            raise ValueError(
                "conversation session already exists: "
                + str(
                    session_id
                )
            )

        session = (
            ConversationSession(
                session_id=session_id,
                Conversation=(
                    self.Conversation
                ),
                Message=self.Message,
                title=title,
                metadata=metadata,
            )
        )

        if system_message is not None:
            if not isinstance(
                system_message,
                str,
            ):
                raise TypeError(
                    "system_message must be str or None"
                )

            session.append_system(
                system_message,
                metadata={
                    "source": (
                        "session_create"
                    ),
                },
            )

        self._sessions[
            session_id
        ] = session

        self._order.append(
            session_id
        )

        return session

    def get(
        self,
        session_id,
    ):
        if session_id not in self._sessions:
            raise KeyError(
                "conversation session not found: "
                + str(
                    session_id
                )
            )

        return self._sessions[
            session_id
        ]

    def list_sessions(
        self,
    ):
        return [
            self._sessions[
                session_id
            ].summary()
            for session_id
            in self._order
        ]

    def delete_session(
        self,
        session_id,
    ):
        session = self.get(
            session_id
        )

        del self._sessions[
            session_id
        ]

        self._order = [
            existing
            for existing
            in self._order
            if existing
            != session_id
        ]

        return session

    def close_session(
        self,
        session_id,
    ):
        return self.get(
            session_id
        ).close()

    def reopen_session(
        self,
        session_id,
    ):
        return self.get(
            session_id
        ).reopen()

    def update_metadata(
        self,
        session_id,
        metadata,
        replace=False,
    ):
        return self.get(
            session_id
        ).update_metadata(
            metadata,
            replace=bool(
                replace
            ),
        )

    def add_message(
        self,
        session_id,
        role,
        content,
        metadata=None,
        name=None,
    ):
        return self.get(
            session_id
        ).append_message(
            role=role,
            content=content,
            metadata=metadata,
            name=name,
        )

    def context(
        self,
        session_id,
        max_tokens=None,
    ):
        return (
            self.window_builder
            .build(
                session=self.get(
                    session_id
                ),
                max_tokens=max_tokens,
                exclude_last=0,
            )
        )

    def chat(
        self,
        session_id,
        user_text,
        rag_options=None,
        trace_id=None,
        correlation_id=None,
        user_metadata=None,
    ):
        session = self.get(
            session_id
        )

        user_message = (
            session.append_user(
                user_text,
                metadata=(
                    user_metadata
                ),
            )
        )

        handoff = (
            self.rag_handoff
            .answer(
                session=session,
                current_user_message=(
                    user_text
                ),
                rag_options=(
                    rag_options
                ),
                trace_id=trace_id,
                correlation_id=(
                    correlation_id
                ),
            )
        )

        answer = handoff[
            "answer"
        ]

        assistant_message = None

        status = answer.get(
            "status"
        )

        if status == "ok":
            answer_text = answer.get(
                "answer_text",
                "",
            )

            if not isinstance(
                answer_text,
                str,
            ):
                raise TypeError(
                    "RAG answer_text must be str"
                )

            citation_ids = []

            citations = answer.get(
                "citations",
                [],
            )

            if isinstance(
                citations,
                list,
            ):
                for citation in citations:
                    if isinstance(
                        citation,
                        dict,
                    ):
                        citation_id = (
                            citation.get(
                                "citation_id"
                            )
                        )

                        if (
                            citation_id
                            is not None
                        ):
                            citation_ids.append(
                                citation_id
                            )

            assistant_message = (
                session
                .append_assistant(
                    answer_text,
                    metadata={
                        "source": (
                            "rag_service"
                        ),
                        "rag_request_id": (
                            handoff[
                                "rag_request_id"
                            ]
                        ),
                        "citation_ids": (
                            citation_ids
                        ),
                        "stop_reason": (
                            answer.get(
                                "stop_reason"
                            )
                        ),
                    },
                )
            )

        else:
            session.metadata[
                "last_blocked_phase"
            ] = answer.get(
                "blocked_phase"
            )

            session.conversation.metadata = (
                session._copy(
                    session.metadata
                )
            )

        return ConversationChatResult(
            session_id=session_id,
            user_message=user_message,
            assistant_message=(
                assistant_message
            ),
            answer=answer,
            history_window=handoff[
                "history_window"
            ],
            rag_request_id=handoff[
                "rag_request_id"
            ],
        )
