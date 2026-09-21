class BPETokenizer:
    """
    Runtime byte-level BPE tokenizer.
    """

    def __init__(self, model, byte_encoder, special_tokens):
        self.model = model
        self.byte_encoder = byte_encoder
        self.special_tokens = special_tokens

        self._merge_ranks = {}
        self._merge_ids = {}

        rank = 0
        for left, right, new_id in self.model.merges:
            pair = (left, right)
            self._merge_ranks[pair] = rank
            self._merge_ids[pair] = new_id
            rank += 1

    def encode(self, text, add_bos=False, add_eos=False, allow_special=False):
        if not isinstance(text, str):
            raise TypeError("text must be str")

        result = []

        if add_bos:
            result.append(self.model.vocabulary.special_id("<BOS>"))

        if allow_special:
            pieces = self._split_special(text)
            for kind, value in pieces:
                if kind == "special":
                    result.append(self.model.vocabulary.special_id(value))
                else:
                    result.extend(self._encode_plain(value))
        else:
            result.extend(self._encode_plain(text))

        if add_eos:
            result.append(self.model.vocabulary.special_id("<EOS>"))

        return result

    def _encode_plain(self, text):
        tokens = self.byte_encoder.encode_text(text)

        if len(tokens) < 2 or len(self.model.merges) == 0:
            return tokens

        # Applying learned merges in training order is deterministic and
        # equivalent to rank-based greedy application for this learned list.
        for left, right, new_id in self.model.merges:
            tokens = self._replace_pair(tokens, left, right, new_id)

        return tokens

    def _replace_pair(self, tokens, left, right, new_id):
        out = []
        i = 0

        while i < len(tokens):
            if (
                i + 1 < len(tokens)
                and tokens[i] == left
                and tokens[i + 1] == right
            ):
                out.append(new_id)
                i += 2
            else:
                out.append(tokens[i])
                i += 1

        return out

    def _split_special(self, text):
        specials = self.special_tokens.all()
        result = []
        buffer = []
        i = 0

        while i < len(text):
            matched = None

            for token in specials:
                if text.startswith(token, i):
                    if matched is None or len(token) > len(matched):
                        matched = token

            if matched is not None:
                if buffer:
                    result.append(("text", "".join(buffer)))
                    buffer = []
                result.append(("special", matched))
                i += len(matched)
            else:
                buffer.append(text[i])
                i += 1

        if buffer:
            result.append(("text", "".join(buffer)))

        return result

    def decode(self, token_ids, skip_special=False):
        if not isinstance(token_ids, (list, tuple)):
            raise TypeError("token_ids must be list or tuple")

        pieces = []
        byte_buffer = []

        for token_id in token_ids:
            if self.model.vocabulary.is_special(token_id):
                if byte_buffer:
                    pieces.append(self.byte_encoder.decode_bytes(byte_buffer))
                    byte_buffer = []

                if not skip_special:
                    pieces.append(self.model.vocabulary.special_token(token_id))

            else:
                token_bytes = self.model.vocabulary.token_bytes(token_id)
                for value in token_bytes:
                    byte_buffer.append(value)

        if byte_buffer:
            pieces.append(self.byte_encoder.decode_bytes(byte_buffer))

        return "".join(pieces)

    def token_count(self, text):
        return len(self.encode(text))
