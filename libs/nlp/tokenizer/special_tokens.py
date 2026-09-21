class SpecialTokens:
    """
    Canonical special-token registry for SireLLM.

    IDs are assigned by Vocabulary after byte/BPE tokens so the tokenizer can
    grow without colliding with the 0..255 byte vocabulary.
    """

    DEFAULTS = (
        "<BOS>",
        "<EOS>",
        "<PAD>",
        "<UNK>",
        "<SYSTEM>",
        "<USER>",
        "<ASSISTANT>",
        "<CONTEXT>",
        "<DOCUMENT>",
    )

    def __init__(self, tokens=None):
        if tokens is None:
            tokens = list(self.DEFAULTS)

        if not isinstance(tokens, (list, tuple)):
            raise TypeError("tokens must be list or tuple")

        self._tokens = []
        seen = {}

        for token in tokens:
            if not isinstance(token, str) or token == "":
                raise ValueError("special token must be non-empty str")
            if token in seen:
                raise ValueError("duplicate special token: " + token)
            seen[token] = True
            self._tokens.append(token)

    def all(self):
        return list(self._tokens)

    def contains(self, token):
        return token in self._tokens

    def count(self):
        return len(self._tokens)
