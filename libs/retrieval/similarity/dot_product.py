class DotProduct:
    """
    Dense vector dot product with strict validation.
    """

    def score(self, left, right):
        left_values = self._vector(left)
        right_values = self._vector(right)

        if len(left_values) != len(right_values):
            raise ValueError(
                "vector dimensions must match"
            )

        total = 0.0
        index = 0

        while index < len(left_values):
            total += (
                left_values[index]
                * right_values[index]
            )
            index += 1

        return total

    def _vector(self, value):
        if hasattr(value, "vector"):
            value = value.vector

        if not isinstance(value, (list, tuple)):
            raise TypeError(
                "vector must be list/tuple or expose .vector"
            )

        result = []

        for item in value:
            if not isinstance(item, (int, float)):
                raise TypeError(
                    "vector elements must be numeric"
                )
            result.append(float(item))

        return result
