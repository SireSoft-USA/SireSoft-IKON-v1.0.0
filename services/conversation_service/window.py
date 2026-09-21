class ConversationWindow:
    """
    Whole-message context window.

    Messages are never cut in the middle merely to satisfy a token budget.
    """

    def __init__(
        self,
        messages,
        rendered,
        token_count,
        max_tokens,
        dropped_message_count,
    ):
        self.messages = list(
            messages
        )

        self.rendered = rendered

        self.token_count = int(
            token_count
        )

        self.max_tokens = int(
            max_tokens
        )

        self.dropped_message_count = int(
            dropped_message_count
        )

    def to_dict(
        self,
        include_rendered=True,
    ):
        result = {
            "messages": [
                self._message_dict(
                    message
                )
                for message
                in self.messages
            ],
            "message_count": len(
                self.messages
            ),
            "token_count": (
                self.token_count
            ),
            "max_tokens": (
                self.max_tokens
            ),
            "dropped_message_count": (
                self.dropped_message_count
            ),
            "start_sequence": (
                None
                if len(
                    self.messages
                ) == 0
                else self.messages[
                    0
                ].source_index
            ),
            "end_sequence": (
                None
                if len(
                    self.messages
                ) == 0
                else self.messages[
                    -1
                ].source_index
            ),
        }

        if include_rendered:
            result[
                "rendered"
            ] = self.rendered

        return result

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
        }


class ConversationWindowBuilder:
    """
    Builds the most recent contiguous whole-message tail that fits a token
    budget. If the newest candidate message alone cannot fit, no older message
    is inserted ahead of it; this keeps history chronologically coherent.
    """

    def __init__(
        self,
        tokenizer,
        default_max_tokens=256,
    ):
        if tokenizer is None or not hasattr(
            tokenizer,
            "encode",
        ):
            raise TypeError(
                "tokenizer must provide encode()"
            )

        if (
            not isinstance(
                default_max_tokens,
                int,
            )
            or default_max_tokens <= 0
        ):
            raise ValueError(
                "default_max_tokens must be positive int"
            )

        self.tokenizer = tokenizer
        self.default_max_tokens = (
            default_max_tokens
        )

    def build(
        self,
        session,
        max_tokens=None,
        exclude_last=0,
    ):
        if max_tokens is None:
            max_tokens = (
                self.default_max_tokens
            )

        if (
            not isinstance(
                max_tokens,
                int,
            )
            or max_tokens <= 0
        ):
            raise ValueError(
                "max_tokens must be positive int"
            )

        if (
            not isinstance(
                exclude_last,
                int,
            )
            or exclude_last < 0
        ):
            raise ValueError(
                "exclude_last must be non-negative int"
            )

        messages = session.messages()

        if exclude_last > len(
            messages
        ):
            exclude_last = len(
                messages
            )

        if exclude_last > 0:
            candidates = messages[
                :len(
                    messages
                )
                - exclude_last
            ]
        else:
            candidates = messages

        selected = []

        index = len(
            candidates
        ) - 1

        while index >= 0:
            trial = [
                candidates[
                    index
                ]
            ] + selected

            rendered = self.render(
                trial
            )

            count = len(
                self.tokenizer
                .encode(
                    rendered
                )
            )

            if count <= max_tokens:
                selected = trial
                index -= 1
                continue

            break

        rendered = self.render(
            selected
        )

        token_count = len(
            self.tokenizer
            .encode(
                rendered
            )
        ) if rendered != "" else 0

        return ConversationWindow(
            messages=selected,
            rendered=rendered,
            token_count=token_count,
            max_tokens=max_tokens,
            dropped_message_count=(
                len(
                    candidates
                )
                - len(
                    selected
                )
            ),
        )

    def render(
        self,
        messages,
    ):
        lines = []

        for message in messages:
            lines.append(
                self._role_label(
                    message.role
                )
                + ": "
                + message.content
            )

        return "\n".join(
            lines
        )

    def _role_label(
        self,
        role,
    ):
        if role == "system":
            return "SYSTEM"

        if role == "user":
            return "USER"

        if role == "assistant":
            return "ASSISTANT"

        if role == "tool":
            return "TOOL"

        return "UNKNOWN"
