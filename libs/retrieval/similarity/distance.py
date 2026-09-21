class EuclideanDistance:
    """
    L2 distance. Smaller is better.
    """

    def distance(self, left, right):
        left_values = self._vector(left)
        right_values = self._vector(right)

        if len(left_values) != len(right_values):
            raise ValueError(
                "vector dimensions must match"
            )

        total = 0.0
        index = 0

        while index < len(left_values):
            delta = (
                left_values[index]
                - right_values[index]
            )

            total += delta * delta
            index += 1

        return sqrt(total)

    def similarity(self, left, right):
        """
        Bounded transform useful when callers need a larger-is-better score.
        """
        return 1.0 / (
            1.0 + self.distance(left, right)
        )

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


class ManhattanDistance:
    """
    L1 / Manhattan distance. Smaller is better.
    """

    def distance(self, left, right):
        left_values = self._vector(left)
        right_values = self._vector(right)

        if len(left_values) != len(right_values):
            raise ValueError(
                "vector dimensions must match"
            )

        total = 0.0
        index = 0

        while index < len(left_values):
            delta = (
                left_values[index]
                - right_values[index]
            )

            if delta < 0.0:
                delta = -delta

            total += delta
            index += 1

        return total

    def similarity(self, left, right):
        return 1.0 / (
            1.0 + self.distance(left, right)
        )

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
