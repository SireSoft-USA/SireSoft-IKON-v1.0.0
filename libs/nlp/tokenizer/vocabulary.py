class Vocabulary:
    """
    Token vocabulary.

    Byte tokens occupy IDs 0..255. BPE merge tokens are appended after them.
    Special tokens are appended after training is complete.
    """

    def __init__(self):
        self._id_to_bytes = {}
        self._bytes_to_id = {}
        self._special_to_id = {}
        self._id_to_special = {}
        self._next_id = 0
        self._specials_finalized = False

        i = 0
        while i < 256:
            value = (i,)
            self._id_to_bytes[i] = value
            self._bytes_to_id[value] = i
            i += 1

        self._next_id = 256

    def add_merge_token(self, left_id, right_id):
        if self._specials_finalized:
            raise RuntimeError("cannot add merge token after special tokens are finalized")

        if left_id not in self._id_to_bytes or right_id not in self._id_to_bytes:
            raise KeyError("merge references unknown token")

        merged = self._id_to_bytes[left_id] + self._id_to_bytes[right_id]

        if merged in self._bytes_to_id:
            return self._bytes_to_id[merged]

        token_id = self._next_id
        self._next_id += 1
        self._id_to_bytes[token_id] = merged
        self._bytes_to_id[merged] = token_id
        return token_id

    def finalize_special_tokens(self, special_tokens):
        if self._specials_finalized:
            return

        for token in special_tokens:
            if token in self._special_to_id:
                continue
            token_id = self._next_id
            self._next_id += 1
            self._special_to_id[token] = token_id
            self._id_to_special[token_id] = token

        self._specials_finalized = True

    def token_bytes(self, token_id):
        if token_id not in self._id_to_bytes:
            raise KeyError("token is not a byte/BPE token")
        return self._id_to_bytes[token_id]

    def token_id_for_bytes(self, byte_tuple):
        return self._bytes_to_id.get(tuple(byte_tuple))

    def special_id(self, token):
        if token not in self._special_to_id:
            raise KeyError("unknown special token: " + token)
        return self._special_to_id[token]

    def special_token(self, token_id):
        return self._id_to_special.get(token_id)

    def is_special(self, token_id):
        return token_id in self._id_to_special

    def size(self):
        return self._next_id

    def normal_token_count(self):
        return len(self._id_to_bytes)

    def special_token_count(self):
        return len(self._special_to_id)

    def export_state(self):
        merges = {}
        for token_id in self._id_to_bytes:
            if token_id >= 256:
                merges[token_id] = list(self._id_to_bytes[token_id])

        return {
            "size": self.size(),
            "normal_token_count": self.normal_token_count(),
            "special_tokens": dict(self._special_to_id),
            "merge_token_bytes": merges,
        }
