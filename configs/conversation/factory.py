class ConversationConfigFactory:
    """
    Builds the real stateful conversation manager/service and centralizes
    defaults for new sessions.
    """

    def build_manager(
        self,
        config,
        tokenizer,
        rag_service,
    ):
        if not isinstance(
            config,
            ConversationConfig,
        ):
            raise TypeError(
                "config must be ConversationConfig"
            )

        ConversationConfigValidator().require_valid(
            config
        )

        window_builder = (
            ConversationWindowBuilder(
                tokenizer=tokenizer,
                default_max_tokens=(
                    config
                    .window
                    .context_max_tokens
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
                    config
                    .window
                    .rag_history_tokens
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

    def build_service(
        self,
        config,
        tokenizer,
        rag_service,
    ):
        return ConversationService(
            self.build_manager(
                config,
                tokenizer,
                rag_service,
            )
        )

    def create_session(
        self,
        manager,
        config,
        session_id,
        title=None,
        metadata=None,
        system_message=None,
    ):
        if not isinstance(
            manager,
            ConversationManager,
        ):
            raise TypeError(
                "manager must be ConversationManager"
            )

        if not isinstance(
            config,
            ConversationConfig,
        ):
            raise TypeError(
                "config must be ConversationConfig"
            )

        merged_metadata = self._copy(
            config
            .defaults
            .metadata
        )

        if metadata is not None:
            if not isinstance(
                metadata,
                dict,
            ):
                raise TypeError(
                    "metadata must be dict or None"
                )

            for key in metadata:
                merged_metadata[
                    key
                ] = self._copy(
                    metadata[
                        key
                    ]
                )

        effective_title = title

        if (
            effective_title is None
            and config
            .defaults
            .title_prefix
            is not None
        ):
            effective_title = (
                config
                .defaults
                .title_prefix
                + " "
                + session_id
            )

        effective_system = (
            config
            .defaults
            .system_message
            if system_message is None
            else system_message
        )

        return manager.create_session(
            session_id=session_id,
            title=effective_title,
            metadata=(
                merged_metadata
            ),
            system_message=(
                effective_system
            ),
        )

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
