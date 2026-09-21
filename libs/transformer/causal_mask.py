class CausalMask:
    """
    Autoregressive attention mask.

    A query at position q may attend only to keys <= q + prefix_length.
    prefix_length is useful when a future KV-cache supplies already-generated
    context before the current query block.
    """

    def __init__(self, prefix_length=0):
        if not isinstance(prefix_length, int) or prefix_length < 0:
            raise ValueError("prefix_length must be non-negative int")
        self.prefix_length = prefix_length

    def allows(self, query_index, key_index):
        return key_index <= query_index + self.prefix_length

    def matrix(self, query_length, key_length=None):
        if not isinstance(query_length, int) or query_length < 0:
            raise ValueError("query_length must be non-negative int")

        if key_length is None:
            key_length = query_length

        if not isinstance(key_length, int) or key_length < 0:
            raise ValueError("key_length must be non-negative int")

        rows = []
        query = 0

        while query < query_length:
            row = []
            key = 0

            while key < key_length:
                row.append(
                    1 if self.allows(query, key) else 0
                )
                key += 1

            rows.append(row)
            query += 1

        return rows
