class CosineSimilarity:
    """
    Cosine similarity:
        dot(a,b) / (||a|| * ||b||)

    zero_vector_score controls the mathematically undefined zero-vector case.
    """

    def __init__(self, zero_vector_score=0.0):
        if not isinstance(zero_vector_score, (int, float)):
            raise TypeError(
                "zero_vector_score must be numeric"
            )

        self.zero_vector_score = float(
            zero_vector_score
        )

    def score(self, left, right):
        left_values = self._vector(left)
        right_values = self._vector(right)

        if len(left_values) != len(right_values):
            raise ValueError(
                "vector dimensions must match"
            )

        dot = 0.0
        left_squared = 0.0
        right_squared = 0.0

        index = 0

        while index < len(left_values):
            left_value = left_values[index]
            right_value = right_values[index]

            dot += left_value * right_value
            left_squared += (
                left_value * left_value
            )
            right_squared += (
                right_value * right_value
            )

            index += 1

        if (
            left_squared == 0.0
            or right_squared == 0.0
        ):
            return self.zero_vector_score

        denominator = (
            sqrt(left_squared)
            * sqrt(right_squared)
        )

        return dot / denominator

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
