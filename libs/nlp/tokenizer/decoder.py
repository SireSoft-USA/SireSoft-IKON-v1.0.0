class TokenDecoder:
    """
    Thin decoding facade used by inference code.

    Kept separate from BPETokenizer so generation/inference can depend on a
    decode-only interface when needed.
    """

    def __init__(self, tokenizer):
        if tokenizer is None or not hasattr(tokenizer, "decode"):
            raise TypeError("tokenizer must provide decode()")
        self.tokenizer = tokenizer

    def decode(self, token_ids, skip_special=False):
        return self.tokenizer.decode(
            token_ids,
            skip_special=skip_special,
        )

    def decode_one(self, token_id, skip_special=False):
        return self.decode([token_id], skip_special=skip_special)
